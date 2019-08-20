# upload-files

## What it does

Uploads files to S3 bucket

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "upload-files",
    "sources": [
        {
        "bucket": "<BUCKET-NAME>",
        "filename": "<FILE-PATH>",
        "prefix": "<PREFIX-STRING>"
        }
    ]
}
```

The *operation* key must have a value of '*upload-files*'.

Each file object in the *packages* array must have:
* a *bucket* key - the name of the S3 bucket
* a *filename* key - the full path of the file to be uploaded