# stop-containers

## Prerequisites

Docker must be installed on the device, as well as the [Docker SDK for Python](https://pypi.org/project/docker/)

## What it does

Stops a list of specified containers on device using Docker

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "stop-containers",
    "containers": [
        "97a13d5571"
    ]
}
```

The *operation* key must have a value of '*stop-containers*'.

Each element in the *image* array must be an string identifier of a container running in Docker
