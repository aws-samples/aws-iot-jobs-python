# list-containers

## Prerequisites

Docker must be installed on the device, as well as the [Docker SDK for Python](https://pypi.org/project/docker/)

## What it does

Lists Docker containers installed currently running on device, and reports results to device shadow

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "list-containers"
}
```

The *operation* key must have a value of '*list-containers*'.

