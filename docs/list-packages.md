# list-packages

## What it does

Lists packages installed on device using package manager (apt-get, brew, etc), and reports results to device shadow

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "list-packages"
}
```

The *operation* key must have a value of '*list-packages*'.
