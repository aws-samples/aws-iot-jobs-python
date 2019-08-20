# pip-uninstall

## What it does

Uninstalls a list of specific packages onto device using pip package manager

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "uninstall-packages",
    "packages": [
        {
            "name": "crhelper"
        }
    ]
}
```

The *operation* key must have a value of '*pip-uninstall*'.

Each file object in the *packages* array must have:
* a *name* key - the name of the package to be uninstalled
