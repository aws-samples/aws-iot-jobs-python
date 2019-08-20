echo cleaning up in $REGION

# deactivate certificate
aws iot update-certificate --region $REGION --certificate-id $(cat config.json | jq -r '.certificateId') --new-status INACTIVE

# detach thing principal
aws iot detach-thing-principal --region $REGION --thing-name $(cat config.json | jq -r '.thingName') --principal $(cat config.json | jq -r '.certificateArn')

# detach IoT policy
aws iot detach-policy --region $REGION --policy-name $(cat config.json | jq -r '.thingName')_Policy --target $(cat config.json | jq -r '.certificateArn')

# delete certificate
aws iot delete-certificate --region $REGION --certificate-id $(cat config.json | jq -r '.certificateId')

# delete thing
aws iot delete-thing --region $REGION --thing-name $(cat config.json | jq -r '.thingName')

# delete IoT policy
aws iot delete-policy --region $REGION --policy-name $(cat config.json | jq -r '.thingName')_Policy

# detach IAM policy
aws iam detach-role-policy --region $REGION --role-name aws-iot-jobs-python-role --policy-arn $(cat config.json | jq -r '.iamPolicyArn')

# delete IAM policy
aws iam delete-policy --region $REGION --policy-arn  $(cat config.json | jq -r '.iamPolicyArn')

# delete IAM role
aws iam delete-role --region $REGION --role-name aws-iot-jobs-python-role

# delete role alias
aws iot delete-role-alias --region $REGION --role-alias aws-iot-jobs-python

echo Done!