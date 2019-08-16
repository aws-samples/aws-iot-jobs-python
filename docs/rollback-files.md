# rollback-files

To execute this job, use the following JSON as an example:
```
{
    "operation":"rollback-files",
    "files": [
        {
            "destination": "./app-files/cvm.yml"
        }
    ]
}
```

The *operation* key must have a value of '*download-files*'.

Each file object in the *files* array must have:
* a *destination* key - the local file path on the device where a rollback will be performed - if there is an existing file of the same name with the .old suffix
