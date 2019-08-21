#!/bin/bash -v
date

echo LANG=en_US.utf-8 >> /etc/environment
echo LC_ALL=en_US.UTF-8 >> /etc/environment

. /home/ec2-user/.bashrc

echo '=== INSTALL SOFTWARE ==='
yum -y remove aws-cli
yum -y install jq python36
PATH=$PATH:/usr/local/bin
curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
pip3 install boto3
pip3 install awscli
pip3 install AWSIoTPythonSDK
pip3 install docker

echo '=== CONFIGURE awscli and setting ENVIRONMENT VARS ==='
echo "complete -C '/usr/local/bin/aws_completer' aws" >> /home/ec2-user/.bashrc
IOT_ENDPOINT_OLD=$(aws iot describe-endpoint --region $REGION | jq -r '.endpointAddress')
IOT_ENDPOINT=$(aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS | jq -r '.endpointAddress')
IOT_ENDPOINT_CP=$(aws iot describe-endpoint --region $REGION --endpoint-type iot:CredentialProvider | jq -r '.endpointAddress')
echo "export IOT_ENDPOINT_OLD=$IOT_ENDPOINT_OLD" >> /home/ec2-user/.bashrc
echo "export IOT_ENDPOINT=$IOT_ENDPOINT" >> /home/ec2-user/.bashrc
echo "export IOT_ENDPOINT_CP=$IOT_ENDPOINT_CP" >> /home/ec2-user/.bashrc
echo 'PATH=$PATH:/usr/local/bin' >> /home/ec2-user/.bashrc
echo 'export PATH' >> /home/ec2-user/.bashrc

cd /home/ec2-user/environment/ 

git clone https://github.com/aws-samples/aws-iot-jobs-python
cd /home/ec2-user/environment/aws-iot-jobs-python

THING_NAME=test-job-device
aws iot create-thing --thing-name $THING_NAME --region $REGION
IOT_THING_ARN=$(aws iot describe-thing --region $REGION --thing-name $THING_NAME | jq -r '.thingArn')
aws iot create-keys-and-certificate --region $REGION --set-as-active --public-key-outfile $THING_NAME.public.key --private-key-outfile $THING_NAME.private.key --certificate-pem-outfile $THING_NAME.certificate.pem > /tmp/create_cert_and_keys_response
cat /tmp/create_cert_and_keys_response
CERTIFICATE_ARN=$(jq -r ".certificateArn" /tmp/create_cert_and_keys_response)
CERTIFICATE_ID=$(jq -r ".certificateId" /tmp/create_cert_and_keys_response)
echo $CERTIFICATE_ARN
echo $CERTIFICATE_ID
POLICY_NAME=${THING_NAME}_Policy
aws iot create-policy --region $REGION --policy-name $POLICY_NAME --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action": "iot:*","Resource":"*"}]}'
aws iot attach-policy --policy-name $POLICY_NAME --target $CERTIFICATE_ARN --region $REGION
aws iot attach-thing-principal --thing-name $THING_NAME --principal $CERTIFICATE_ARN --region $REGION
aws iot describe-endpoint --endpoint-type iot:Data-ATS

aws iot create-role-alias --role-alias aws-iot-jobs-python --role-arn $ARN_DEVICE_ROLE --credential-duration-seconds 3600 --region $REGION

cat config.json | jq --arg region "$REGION" --arg thing_arn "$IOT_THING_ARN" --arg endpoint "$IOT_ENDPOINT" --arg endpoint_cp "$IOT_ENDPOINT_CP" --arg s3_bucket "$S3_BUCKET" '.endpoint = $endpoint | .thingArn = $thing_arn | .credentialsEndpoint = $endpoint_cp | .s3Bucket = $s3_bucket | .region = $region | .thingName = "test-job-device" | .rootCaPath = "./AmazonRootCA1.pem" | .deviceCertificatePath = "./test-job-device.certificate.pem" | .privateKeyPath = "./test-job-device.private.key"' > config.tmp.json && mv config.tmp.json config.json
cat ./jobs/container-logs.json | jq --arg s3_bucket "$S3_BUCKET" '.containers[0].bucket = $s3_bucket' > ./jobs/container-logs.tmp.json && mv ./jobs/container-logs.tmp.json ./jobs/container-logs.json
cat ./jobs/upload-files.json | jq --arg s3_bucket "$S3_BUCKET" '.sources[0].bucket = $s3_bucket' > ./jobs/upload-files.tmp.json && mv ./jobs/upload-files.tmp.json ./jobs/upload-files.json

cd /home/ec2-user/environment/

sudo chown -R ec2-user .
