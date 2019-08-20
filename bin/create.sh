echo cleaning up in $REGION
echo using bucket $S3_BUCKET

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
aws iot describe-endpoint --endpoint-type --region $REGION iot:Data-ATS

# create a S3 Bucket for uploading
aws s3 mb --region $REGION s3://$S3_BUCKET

# create IAM policy to access bucket
IAM_POLICY_ARN=$(aws iam create-policy --region $REGION --policy-name aws-iot-jobs-python-policy --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":[\"s3:*\"],\"Resource\":[\"arn:aws:s3:::$S3_BUCKET\",\"arn:aws:s3:::$S3_BUCKET/*\"],\"Effect\":\"Allow\"}]}" | jq -r '.Policy.Arn')

# create IAM role for device role alias
IAM_ROLE_ARN=$(aws iam create-role --region $REGION --role-name aws-iot-jobs-python-role --assume-role-policy-document "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"credentials.iot.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}" | jq -r '.Role.Arn')

# attach IAM role policy
aws iam attach-role-policy --region $REGION --role-name aws-iot-jobs-python-role --policy-arn $IAM_POLICY_ARN

# create role alias
aws iot create-role-alias --region $REGION --role-alias aws-iot-jobs-python --role-arn $IAM_ROLE_ARN

# setup config.json with jq (you may need to adjust depending on where you stored your certificate/keys)
cat config.json | jq --arg region "$REGION" --arg thing_arn "$IOT_THING_ARN" --arg endpoint "$IOT_ENDPOINT" --arg endpoint_cp "$IOT_ENDPOINT_CP" --arg s3_bucket "$S3_BUCKET" --arg iam_policy_arn "$IAM_POLICY_ARN" --arg iam_role_arn "$IAM_ROLE_ARN" --arg certificate_arn "$CERTIFICATE_ARN" --arg certificate_id "$CERTIFICATE_ID" '.endpoint = $endpoint | .thingArn = $thing_arn | .credentialsEndpoint = $endpoint_cp | .s3Bucket = $s3_bucket | .region = $region | .thingName = "test-job-device" | .rootCaPath = "./AmazonRootCA1.pem" | .deviceCertificatePath = "./test-job-device.certificate.pem" | .privateKeyPath = "./test-job-device.private.key" | .iamPolicyArn = $iam_policy_arn | .iamRoleArn = $iam_role_arn | .certificateArn = $certificate_arn | .certificateId = $certificate_id'  > config.tmp.json && mv config.tmp.json config.json

# configure job files
cat ./jobs/container-logs.json | jq --arg s3_bucket "$S3_BUCKET" '.containers[0].bucket = $s3_bucket' > ./jobs/container-logs.tmp.json && mv ./jobs/container-logs.tmp.json ./jobs/container-logs.json
cat ./jobs/upload-files.json | jq --arg s3_bucket "$S3_BUCKET" '.sources[0].bucket = $s3_bucket' > ./jobs/upload-files.tmp.json && mv ./jobs/upload-files.tmp.json ./jobs/upload-files.json
