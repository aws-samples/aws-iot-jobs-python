# uninstall-packages

## What it does

Uninstalls a list of specific packages onto device using package manager (apt-get, brew, etc)

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "uninstall-packages",
    "packages": [
        {
            "name": "jq"
        }
    ]
}
```

The *operation* key must have a value of '*uninstall-packages*'.

Each file object in the *packages* array must have:
* a *name* key - the name of the package to be uninstalled
