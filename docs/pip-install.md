# pip-install

## What it does

Installs a list of specific packages onto device using pip package manager

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation": "pip-install",
    "packages": [
        {
            "name": "crhelper",
            "version": "latest"
        }
    ]
}
```

The *operation* key must have a value of '*pip-install*'.

Each file object in the *packages* array must have:
* a *name* key - the name of the package to be installed
* a *version* key - the version of the package to be installed
