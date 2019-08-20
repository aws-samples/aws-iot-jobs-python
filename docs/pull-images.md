# pull-images

## Prerequisites

Docker must be installed on the device, as well as the [Docker SDK for Python](https://pypi.org/project/docker/)

## What it does

Retrieves temporary credentials, and pulls Docker docker images from Elastic Container Repository (ECR)

## Details

To execute this job, use the following JSON as an example:
```
"operation": "pull-container-images",
    "images": [
        {
            "ecr_repository": "<ECR-REPOSITORY>",
            "image": "bfirsh/reticulate-splines",
            "version": "latest"
        }
    ]
```

The *operation* key must have a value of '*pull-container-images*'.

