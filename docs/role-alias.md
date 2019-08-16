# Create a role alias

## Prerequisites

An IAM role ARN is required to create a role alias.  You can use an ARN from an existing role, or create a new role.

**Create a new role**

We will create a new role that has full access to a specific S3 bucket.

*Create a new S3 bucket*
```
aws s3 mb s3://<YOUR_BUCKET_NAME>
```

*Create a new IAM Role*
```
aws iam create-role --role-name <YOUR_ROLE_NAME> --assume-role-policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"credentials.iot.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}"
```
