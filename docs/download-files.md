# download-files

## What it does

Downloads a designated list of files to specifc file paths on the device

## Details

To execute this job, use the following JSON as an example:
```
{
    "operation":"download-files",
    "files": [
        {
            "destination": "./app-files",
            "url": "https://s3.amazonaws.com/pubz/cvm.yml"
        }
    ]
}
```

The *operation* key must have a value of '*download-files*'.

Each file object in the *files* array must have:
* a *destination* key - the local path on the device where files will be downloaded
* a *url* key - the target file URL that will be downloaded to the local path
