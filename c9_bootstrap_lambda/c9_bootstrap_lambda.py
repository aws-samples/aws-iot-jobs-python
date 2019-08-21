from __future__ import print_function
from crhelper import CfnResource
import boto3
import logging
import json
import os
import time
import traceback

logger = logging.getLogger(__name__)

# Initialise the helper, all inputs are optional, this example shows the defaults
helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

THING_NAME = 'test-job-device'
POLICY_NAME = THING_NAME + '_Policy'

try:
    ## Init code goes here
    logger.setLevel(logging.INFO)
    pass
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info("Got Create")
    # Optionally return an ID that will be used for the resource PhysicalResourceId, 
    # if None is returned an ID will be generated. If a poll_create function is defined 
    # return value is placed into the poll event as event['CrHelperData']['PhysicalResourceId']
    
    # Open AWS clients
    ec2 = boto3.client('ec2')

    # Get the InstanceId of the Cloud9 IDE
    instance = ec2.describe_instances(Filters=[{'Name': 'tag:Name','Values': ['aws-cloud9-'+event['ResourceProperties']['StackName']+'-'+event['ResourceProperties']['EnvironmentId']]}])['Reservations'][0]['Instances'][0]
    logger.info('instance: {}'.format(instance))

    # Create the IamInstanceProfile request object
    iam_instance_profile = {
        'Arn': event['ResourceProperties']['LabIdeInstanceProfileArn'],
        'Name': event['ResourceProperties']['LabIdeInstanceProfileName']
    }
    logger.info('iam_instance_profile: {}'.format(iam_instance_profile))

    # Wait for Instance to become ready before adding Role
    instance_state = instance['State']['Name']
    logger.info('instance_state: {}'.format(instance_state))
    while instance_state != 'running':
        time.sleep(5)
        instance_state = ec2.describe_instances(InstanceIds=[instance['InstanceId']])
        logger.info('instance_state: {}'.format(instance_state))

    # attach instance profile
    response = ec2.associate_iam_instance_profile(IamInstanceProfile=iam_instance_profile, InstanceId=instance['InstanceId'])
    logger.info('response - associate_iam_instance_profile: {}'.format(response))
    r_ec2 = boto3.resource('ec2')

    # attach additional security group
    associated_sg_ids = [sg['GroupId'] for sg in r_ec2.Instance(instance['InstanceId']).security_groups]
    logger.info("associated_sg_ids: {}".format(associated_sg_ids))

    associated_sg_ids.append(event['ResourceProperties']['SecurityGroupId'])
    logger.info("associated_sg_ids - modified: {}".format(associated_sg_ids))

    response = r_ec2.Instance(instance['InstanceId']).modify_attribute(Groups=associated_sg_ids)
    logger.info('response - modify_attribute security group: {}'.format(response))

    tmp_file_bashrc = '/tmp/bashrc'
    logger.info('creating file: {}'.format(tmp_file_bashrc))
    f = open(tmp_file_bashrc, 'w')
    for v in ['ARN_IOT_PROVISIONING_ROLE', 'ARN_LAMBDA_ROLE', 'IOT_POLICY', 'REGION', 'S3_BUCKET', 'ARN_DEVICE_ROLE']:
        f.write('export {}={}\n'.format(v, event['ResourceProperties'][v]))
    f.close()

    logger.info('uploading file: {} to s3 bucket: {}'.format(tmp_file_bashrc, event['ResourceProperties']['S3_BUCKET']))
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file(tmp_file_bashrc, event['ResourceProperties']['S3_BUCKET'], 'cloud9/bootstrap/bashrc')
    time.sleep(2)

    ssm = boto3.client('ssm')
    commands = ['#!/bin/bash', 'cd /tmp',
                'aws s3 cp s3://' + event['ResourceProperties']['S3_BUCKET'] + '/cloud9/bootstrap/bashrc .',
                'cat bashrc >> /home/ec2-user/.bashrc',
                'wget -O c9-user-data.sh https://raw.githubusercontent.com/aws-samples/aws-iot-jobs-python/master/c9-user-data.sh',
                'chmod +x c9-user-data.sh',
                './c9-user-data.sh']
    logger.info('commands: {}'.format(commands))

    ping_status = 'Offline'
    ping_status_tries = 0
    ping_status_sleep = 10
    function_timeout = 600
    ping_status_max_tries = int(function_timeout*0.8/ping_status_sleep)
    logger.info("ping_status_max_tries: {}".format(ping_status_max_tries))

    while ping_status != 'Online':
        time.sleep(ping_status_sleep)
        ping_status_tries += 1
        logger.info('ping_status_tries: {}'.format(ping_status_tries))

        response = ssm.describe_instance_information(
            Filters=[{'Key': 'InstanceIds', 'Values': [ instance['InstanceId'] ] }])
        logger.info('response - describe_instance_information: {}'.format(response))
        if 'InstanceInformationList' in response and len(response['InstanceInformationList']) > 0:
            ping_status = response['InstanceInformationList'][0]['PingStatus']
            logger.info('ping_status: {}'.format(ping_status))
        elif ping_status_tries > ping_status_max_tries:
            raise Exception('SSM ping status not online for instance {} after {} attempts'.format(instance['InstanceId'], ping_status_tries))


    logger.info("ping_status_tries: {}".format(ping_status_tries))

    response = ssm.send_command(
        InstanceIds=[ instance['InstanceId'] ],
        DocumentName='AWS-RunShellScript',
        Parameters={
            'commands': commands,
            'workingDirectory': ['/tmp']
        },
        OutputS3BucketName=event['ResourceProperties']['S3_BUCKET'],
        OutputS3KeyPrefix='cloud9/bootstrap/run-command/',
    )
    logger.info('response - send_command: {}'.format(response))

    # To add response data update the helper.Data dict
    # If poll is enabled data is placed into poll event as event['CrHelperData']
    helper.Data.update({"Success": "Started bootstrapping for instance: "+instance["InstanceId"]})
    return "CustomResourcePhysicalID"


@helper.delete
def delete(event, context):
    logger.info("Got Delete")
    # Delete never returns anything. Should not fail if the underlying resources are already deleted. Desired state.

    # Empty Bucket before CloudFormation deletes it
    session = boto3.Session()
    s3 = session.resource(service_name='s3')

    bucket = s3.Bucket(event['ResourceProperties']['S3_BUCKET'])
    bucket.object_versions.delete()

    logger.info('Bucket '+event['ResourceProperties']['S3_BUCKET']+' objects/versions deleted.')

    iot = boto3.client('iot')

    principals_response = iot.list_thing_principals(thingName=THING_NAME)

    for principal in principals_response['principals']:

        certificateId = principal.split('/')[1]

        iot.detach_thing_principal(thingName=THING_NAME, principal=principal)
        iot.detach_policy(policyName=POLICY_NAME, target=principal)
        iot.update_certificate(certificateId=certificateId,newStatus='INACTIVE')
        iot.delete_certificate(certificateId=certificateId,forceDelete=True)

    iot.delete_policy(policyName=POLICY_NAME)
    iot.delete_thing(thingName=THING_NAME)
    iot.delete_role_alias(roleAlias='aws-iot-jobs-python')

def lambda_handler(event, context):
    helper(event, context)
