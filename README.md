# aws-iot-jobs-python

This code sample demonstrates how a user can create/handle custom AWS IoT jobs in Python.

## License Summary

This sample code is made available under the MIT-0 license. See the LICENSE file.

## Setup

<details>
  <summary>Cloud9 IDE</summary>
  
  ### Choose a region for deployment
  
| Region  | Template |
| ------------- | ------------- |
| **ap-northeast-1** (Tokyo)  | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-ap-northeast-1.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |
| **ap-southeast-1** (Singapore)  | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-ap-southeast-1.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |
| **eu-central-1** (Frankfurt)  | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-eu-central-1.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |
| **eu-west-1** (Ireland)  | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-eu-west-1.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |
| **us-east-1** (N Virginia)  | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-us-east-1.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |
| **us-east-2** (Ohio) | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-us-east-2.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |
| **us-west-2** (Oregon)  | [![Launch Stack](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=aws-iot-jobs-python&templateURL=https://jonslo-aws-samples-us-west-2.s3.amazonaws.com/aws-iot-jobs-python/aws-iot-jobs-python.yaml)  |

### Configure and launch stack

![](https://media.giphy.com/media/WSr73iUNou0yx5ZdXU/giphy.gif)

### Launch Cloud9 IDE

Click the Cloud9 IDE link:
![Stack Output](docs/img/stackOutput.png)

</details>

<details>
  <summary>Manual</summary>

  ### Compatible regions ###
  See the [AWS Region Table](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/) for the current list of regions for AWS IoT Core and AWS IoT Device Management.

  ### Required tools ###
  * Linux/macOS (this solution has not been tested on Windows)
  * Python 3.6 or newer
  * [awscli](https://aws.amazon.com/cli/)
  * [jq](https://stedolan.github.io/jq/)
  
  ### Setup thing, certificate, and policy ###

  ```
  # make sure you are in aws-iot-jobs-python directory
  cd ./aws-iot-jobs-python

  # assigning your region to a shell variable makes the next steps easier
  REGION=<set AWS region>

  # save IoT endpoints to variables
  IOT_ENDPOINT=$(aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS | jq -r '.endpointAddress')
  IOT_ENDPOINT_CP=$(aws iot describe-endpoint --region $REGION --endpoint-type iot:CredentialProvider | jq -r '.endpointAddress')

  # assigning your thing name to a shell variable makes the next steps easier
  THING_NAME=test-job-device
  
  # create a thing in the thing registry
  aws iot create-thing --thing-name $THING_NAME --region $REGION
  IOT_THING_ARN=$(aws iot describe-thing --region $REGION --thing-name $THING_NAME | jq -r '.thingArn')

  # create key and certificate for your device and active the device
  aws iot create-keys-and-certificate --region $REGION --set-as-active --public-key-outfile $THING_NAME.public.key --private-key-outfile $THING_NAME.private.key --certificate-pem-outfile $THING_NAME.certificate.pem > /tmp/create_cert_and_keys_response

  # look at the output from the previous command
  cat /tmp/create_cert_and_keys_response

  # output values from the previous call needed in further steps
  CERTIFICATE_ARN=$(jq -r ".certificateArn" /tmp/create_cert_and_keys_response)
  CERTIFICATE_ID=$(jq -r ".certificateId" /tmp/create_cert_and_keys_response)
  echo $CERTIFICATE_ARN
  echo $CERTIFICATE_ID

  # create an IoT policy
  POLICY_NAME=${THING_NAME}_Policy
  aws iot create-policy --region $REGION --policy-name $POLICY_NAME --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action": "iot:*","Resource":"*"}]}'

  # attach the policy to your certificate
  aws iot attach-policy --policy-name $POLICY_NAME --target $CERTIFICATE_ARN --region $REGION

  # attach the certificate to your thing
  aws iot attach-thing-principal --thing-name $THING_NAME --principal $CERTIFICATE_ARN --region $REGION

  # get AWS IoT endpoint
  aws iot describe-endpoint --endpoint-type iot:Data-ATS

  # create a S3 Bucket for uploading
  BUCKET=<Enter a bucket name>
  aws s3 mb s3://$BUCKET

  # create IAM policy to access bucket
  IAM_POLICY_ARN=$(aws iam create-policy --policy-name aws-iot-jobs-python-policy --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":[\"s3:*\"],\"Resource\":[\"arn:aws:s3:::$BUCKET\",\"arn:aws:s3:::$BUCKET/*\"],\"Effect\":\"Allow\"}]}" | jq -r '.Policy.Arn')

  # create IAM role for device role alias
  IAM_ROLE_ARN=$(aws iam create-role --role-name aws-iot-jobs-python-role --assume-role-policy-document "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"credentials.iot.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}" | jq -r '.Role.Arn')

  # attach IAM role policy
  aws iam attach-role-policy --role-name aws-iot-jobs-python-role --policy-arn $IAM_POLICY_ARN

  # create role alias
  aws iot create-role-alias --role-alias aws-iot-jobs-python --role-arn $IAM_ROLE_ARN

  # setup config.json with jq (you may need to adjust depending on where you stored your certificate/keys)
  cat config.json | jq --arg region "$REGION" --arg thing_arn "$IOT_THING_ARN" --arg endpoint "$IOT_ENDPOINT" --arg endpoint_cp "$IOT_ENDPOINT_CP" '.endpoint = $endpoint | .thingArn = $thing_arn | .credentialsEndpoint = $endpoint_cp | .region = $region | .thingName = "test-job-device" | .rootCaPath = "./AmazonRootCA1.pem" | .deviceCertificatePath = "../test-job-device.certificate.pem" | .privateKeyPath = "../test-job-device.private.key"' > config.tmp.json && mv config.tmp.json config.json
  ```

</details>

## Start job agent

In one terminal tab/window, run the following command:
```
cd aws-iot-jobs-python
python3 jobsSample.py -j ./config.json
```

![](https://media.giphy.com/media/MAisXSUrEGunu4ikBd/giphy.gif)

<details>
  <summary>config.json</summary>

```
{
    "thingName": "<THING-NAME>",
    "thingArn": "<THING-ARN>",
    "region": "<REGION>",
    "deviceCertificatePath": "",
    "privateKeyPath": "",
    "rootCaPath": "",
    "endpoint": "<ENDPOINT>",
    "credentialsEndpoint": "<CREDENTIAL-ENDPOINT-PREFIX>",
    "roleAlias": "<ROLE-ALIAS>",
    "useWebsocket": "false",
    "port": 8883,
    "s3Bucket": "<BUCKET-NAME>
}
```

| Key  | Description |
| ------------- | ------------- |
| thingName | provides identifier for thing; used as MQTT client ID |
| thingArn | Amazon Resource Name for thing |
| region | AWS region thing resides in |
| deviceCertificatePath | Path of device X.509 certificate |
| privateKeyPath | Path of device private key |
| rootCaPath | Path of Amazon CA certificate |
| endpoint | MQTT broker endpoint (in AWS IoT Core) |
| credentialsEndpoint | credentials endpoint (in AWS IoT Core) used to retrieve temporary credentials |
| roleAlias | used to retrieve temporary credentials with credentials endpoint |
| useWebsocket | determines if WS should be used |
| port | MQTT port |
| s3Bucket | used for uploading files |

</details>

<details>
  <summary>jobsSample.py</summary>

### About
Based on [jobsSample.py](https://github.com/aws/aws-iot-device-sdk-python/blob/master/samples/jobs/jobsSample.py) from [aws-iot-device-sdk-python](https://github.com/aws/aws-iot-device-sdk-python).  Modified to include jobExecutor, which handles the execution of specific job documents.

</details>

<details>
  <summary>jobExecutor.py</summary>

### About
Module referenced by [jobsSample.py](jobsSample.py) to handle specific job documents.  Can be modified to handle your custom jobs!

</details>

## Create jobs

In a separate terminal tab/window, run the following command:
```
cd aws-iot-jobs-python
JOB_ID=$(uuidgen)
aws iot create-job --job-id $JOB_ID --targets $(cat config.json | jq -r '.thingArn') --document file://jobs/pip-list.json
```

![](docs/img/createJob.png)

<details>
  <summary>Documentation</summary>

### Example job definitions
You can use the [JSON job documents](jobs/) to schedule a new job execution. You can find more info on each job type here:

#### Basic
* [download-files.json](docs/download-files.md)
* [install-packages.json](docs/install-packages.md)
* [pip-install.json](docs/pip-install.md)
* [pip-list.json](docs/pip-list.md)
* [pip-uninstall.json](docs/pip-uninstall.md)
* [rollback-files.json](docs/rollback-files.md)
* [run-commands.json](docs/run-commands.md)
* [uninstall-packages.json](docs/uninstall-packages.md)
#### Advanced
* [container-logs.json](docs/container-logs.md)
* [list-containers.json](docs/list-containers.md)
* [reboot.json](docs/reboot.md)
* [start-containers.json](docs/start-containers.md)
* [stop-containers.json](docs/stop-containers.md)
* [upload-files.json](docs/upload-files.md)
  
</details>

<details>
  <summary>Job Targets</summary>

### Summary
For the --targets parameter, you can use:
* An IoT Thing Arn
* An IoT Things Group Arn
* A local JSON file [targeting IoT Thing(s)](etc/target-thing.json), [targeting Things Group Arn(s)](etc/target-group.json), or targeting a combination of both!

#### Targeting a IoT Thing/Things Group Arn inline
```
aws iot create-job --targets {THING_OR_THINGS_GROUP_ARN} --document file://jobs/{JSON_JOB_DOCUMENT} --job-id $(uuidgen)
```

#### Targeting with a JSON file
```
aws iot create-job --targets file://etc/target-thing.json --document file://jobs/{JSON_JOB_DOCUMENT} --job-id $(uuidgen)
```

</details>

## Evaluate job status/execution

Execute the following to retrieve status details for your job:
```
aws iot describe-job --job-id $JOB_ID
```

![](docs/img/describeJob.png)

Execute the following to retrieve specific job execution details for your thing:
```
aws iot describe-job-execution --job-id $JOB_ID --thing-name $(cat config.json | jq -r '.thingName')
```

![](docs/img/describeJobExecution.png)

After executing the pip-list job, notice that the device's shadow has been updated in AWS Management Console:

![](docs/img/shadow.png)

Or via CLI:

```
aws iot-data get-thing-shadow --thing-name $(cat config.json | jq -r '.thingName') shadow.txt
cat shadow.txt
```

## Clean up

Go to CloudFormation, and delete the 'aws-iot-jobs-python' stack.

![](docs/img/cleanUp.png)