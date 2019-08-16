# install-packages

## What it does

Installs a list of specific packages onto device using package manager (apt-get, brew, etc)

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "install-packages",
    "packages": [
        {
            "name": "jq",
            "version": "latest"
        }
    ]
}
```

The *operation* key must have a value of '*install-packages*'.

Each file object in the *packages* array must have:
* a *name* key - the name of the package to be installed
* a *version* key - the version of the package to be installed
