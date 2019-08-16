# start-containers

## Prerequisites

Docker must be installed on the device, as well as the [Docker SDK for Python](https://pypi.org/project/docker/)

## What it does

Starts a list of specified containers on device using Docker

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "start-containers",
    "images": [
        {
            "name": "bfirsh/reticulate-splines",
            "version": "latest"
        }
    ]
}
```

The *operation* key must have a value of '*start-containers*'.

Each object in the *image* array must have:
* a *name* key - the name of the container to be started
* a *version* key - the version of the container to be started
