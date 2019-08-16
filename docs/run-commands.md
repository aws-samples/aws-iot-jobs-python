# run-commands

To execute this job, use the following JSON as an example:
```
{
    "operation": "run-commands",
    "commands": [
        ["ls", "-al"],
        "pwd",
        ["whoami"]
    ]
}
```

The *operation* key must have a value of '*run-commands*'.

Each element in the *command* array is a string or an array of strings that will execute in a separate terminal process