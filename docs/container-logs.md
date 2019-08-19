# container-logs

## What it does

Uploads logs specific to docker container, and uploads to S3 bucket

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "container-logs",
    "containers": [
        {
            "id": "<CONTAINER-ID>",
            "bucket": "<S3-BUCKET>",
            "prefix": "logs/"
        }
    ]
}
```

The *operation* key must have a value of '*container-logs*'.
