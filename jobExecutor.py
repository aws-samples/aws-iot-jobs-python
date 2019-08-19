'''
 /*
  * Copyright 2019 Amazon.com, Inc. and its affiliates. All Rights Reserved.
  *
  * Licensed under the MIT License. See the LICENSE accompanying this file
  * for the specific language governing permissions and limitations under
  * the License.
  */
 '''
import base64
import boto3
import datetime
import docker
import fnmatch
import json
import os
import platform
import requests
import subprocess
import time

def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def stringToBool(str):
    if str in ['true', 'True']:
        return True
    else: 
        return False

class JobExecutor(object):

    def __init__(self, config, deviceShadowHandler):

        self.ACCESS_KEY = None
        self.SECRET_KEY = None
        self.SESSION_TOKEN = None
        self.session = None

        self.thingName = config.thingName
        self.certificatePath = config.certificatePath
        self.privateKeyPath = config.privateKeyPath
        self.rootCaPath = config.rootCAPath
        self.credentialsEndpoint = config.credentialsEndpoint
        self.roleAlias = config.roleAlias
        self.region = config.region

        self.deviceShadowHandler = deviceShadowHandler
        
    def formatResults(self, resultArray, didSucceed):
        
        results = {}
        processedCount = 0
        
        for result in resultArray:
            results[f'command{processedCount}'] = str(result)
            processedCount = processedCount + 1
            
        results['didSucceed'] = didSucceed
            
        return results

    def downloadFiles(self, execution):

        results = []
        didSucceed = True

        for fileOperation in execution['jobDocument']['files']:

            # if the destination file already exists, create a rollback version
            exists = os.path.isfile(fileOperation['destination'])

            if exists:
                os.rename(fileOperation['destination'], fileOperation['destination'] + '.old')

            results.append(subprocess.run(["curl", "--output", fileOperation['destination'], fileOperation['url']], shell=False, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE))

        return self.formatResults(results, didSucceed)

    def rollbackFiles(self, execution):

        results = []
        didSucceed = True

        for fileOperation in execution['jobDocument']['files']:

            # check to see if rollback file exists
            exists = os.path.isfile(fileOperation['destination'] + '.old')

            # if required rollback file does not exist, return failure immediately
            if not exists and fileOperation['required'] == True:
                errorMessage = 'Unable to roll back file' + fileOperation['destination'] + '.'
                results.append({'fileOperation': fileOperation, 'stderr': errorMessage.encode('ascii')})
                didSucceed = False
            
            elif exists:
                os.rename(fileOperation['destination'] + '.old', fileOperation['destination'])
                successMessage = 'Rolled back file' + fileOperation['destination'] + '.'
                results.append({'fileOperation': fileOperation, 'stdout': successMessage.encode('ascii')})

        return self.formatResults(results, didSucceed)

    def executeJob(self, execution):

        operations = {
            'container-logs': self.uploadContainerLogs,
            'download-files': self.downloadFiles,
            'install-packages': self.installPackages,
            'list-containers': self.listContainers,
            'pip-install': self.pipInstall,
            'pip-list': self.pipList,
            'pip-uninstall': self.pipUninstall,
            'pull-container-images': self.pullContainerImages,
            'reboot': self.reboot,
            'rollback-files': self.rollbackFiles,
            'run-commands': self.runCommands,
            'start-containers': self.runContainers,
            'stop-containers': self.stopContainers,
            'uninstall-packages': self.uninstallPackages,
            'upload-files': self.uploadS3Files
        }

        # Get the function from switcher dictionary
        func = operations.get(execution['jobDocument']['operation'], self.notSupportedHandler)
        
        try:
            # Execute the function
            return func(execution)
        except Exception as e:
            results = [{'error':e}]
            return self.formatResults(results, didSucceed=False)

    def getTemporaryCredentials(self):

        url = 'https://' + self.credentialsEndpoint + \
              '/role-aliases/' + self.roleAlias + '/credentials'

        headers = {
            'x-amzn-iot-thingname': self.thingName,
        }

        response = requests.get(
            url,
            headers=headers,
            verify=self.rootCaPath,
            cert=(
                self.certificatePath,
                self.privateKeyPath
            )
        )

        json_response = json.loads(response.content)

        self.ACCESS_KEY = json_response['credentials']['accessKeyId']
        self.SECRET_KEY = json_response['credentials']['secretAccessKey']
        self.SESSION_TOKEN = json_response['credentials']['sessionToken']

        session = boto3.Session(
            aws_access_key_id=self.ACCESS_KEY,
            aws_secret_access_key=self.SECRET_KEY,
            aws_session_token=self.SESSION_TOKEN,
        )

        # print(session.get_credentials().access_key)
        # print(session.get_credentials().secret_key)

        return session

    def notSupportedHandler(self, execution):

        errorMessage = 'Operation \'' + execution['jobDocument']['operation'] + '\' is currently not supported on this device.'
        print(errorMessage)
        return subprocess.CompletedProcess(args=[],returncode=1,stderr=errorMessage.encode('ascii'))

    def reboot(self, execution):

        results = []
        didSucceed = True

        systems = {
            'Darwin': ["sudo", "shutdown", "-r", "+1"],
            'Linux': ["sudo", "shutdown", "-r", "+1"]
        }

        # Get the function from switcher dictionary
        commands = systems.get(platform.system())
        if commands is None:
            self.notSupportedHandler(execution)
        else:
            # Execute the function
            print('reboot!')
            results.append(subprocess.run(commands, shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            return self.formatResults(results, didSucceed)

    def runCommands(self, execution):

        results = []
        didSucceed = True

        for cmd in execution['jobDocument']['commands']:
           
            result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            results.append(result)
            
            if result.stderr and result.stderr is not None:
                didSucceed = False

        return self.formatResults(results, didSucceed)

    def uploadS3Files(self, execution):

        results = []
        didSucceed = True

        session = self.getTemporaryCredentials()

        s3_client = session.client('s3')

        for source in execution['jobDocument']['sources']:

            filePath = None
            key = None

            filePath = source['filename']

            if 'prefix' in source:
                key = source['prefix'] + '/' + filePath
            else:
                key = filePath

            s3_client.upload_file(filePath, source['bucket'], key)

            successMessage = 'Uploaded ' + filePath + ' to ' + source['bucket']
            results.append(successMessage)

        return self.formatResults(results, didSucceed)

# PACKAGE MANAGER

    def installPackages(self, execution):

        systems = {
            'Darwin': ["brew", "install"],
            # 'Linux': ["sudo", "apt-get", "install", "-y"], # not for Amazon Linux
            'Linux': ["sudo", "yum", "-y", "install"]
        }

        results = []
        didSucceed = True

        # Get the function from switcher dictionary
        commands = systems.get(platform.system())
        if commands is None:
            return self.notSupportedHandler(execution)
        else:
            for package in execution['jobDocument']['packages']:

                pkgCommands = commands.copy()
                pkgCommands.append(package['name'])

                result = subprocess.run(pkgCommands, shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                results.append(result)

                if result.stderr and result.stderr is not None:
                    didSucceed = False

            return self.formatResults(results, didSucceed)

    def uninstallPackages(self, execution):

        systems = {
            'Darwin': ["brew", "uninstall"],
            # 'Linux': ["sudo", "apt-get", "install", "-y"], # not for Amazon Linux
            'Linux': ["sudo", "yum", "-y", "erase"]
        }

        results = []
        didSucceed = True

        # Get the function from switcher dictionary
        commands = systems.get(platform.system())
        if commands is None:
            return self.notSupportedHandler(execution)
        else:
            for package in execution['jobDocument']['packages']:

                pkgCommands = commands.copy()
                pkgCommands.append(package['name'])

                result = subprocess.run(pkgCommands, shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                results.append(result)

                if result.stderr and result.stderr is not None:
                    didSucceed = False

            return self.formatResults(results, didSucceed)
            
# PIP

    def pipList(self, execution):
    
        systems = {
            'Darwin': ["pip3", "list"],
            'Linux': ["pip3", "list"]
        }

        # Get the function from switcher dictionary
        commands = systems.get(platform.system())
        if commands is None:
            return self.notSupportedHandler(execution)
        else:
            result = subprocess.run(commands, shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            pkgList = result.stdout
            pkgs = filter(None, pkgList.split(b'\n'))
            packageList = []
            results = []
            didSucceed = True
            
            cnt = 0
            
            for pkg in pkgs:
                
                cnt = cnt + 1
                
                if cnt < 3:
                    continue
                
                pkgSplit = pkg.decode().split()
                p = {"name": pkgSplit[0], "version": pkgSplit[1]}

                packageList.append(p)

            JSONPayload = '{"state":{"reported":{"packages":' + json.dumps(packageList) + '}}}'
            self.deviceShadowHandler.shadowUpdate(JSONPayload, customShadowCallback_Update, 5)

            return self.formatResults(results, didSucceed)
                
    def pipInstall(self, execution):

        systems = {
            'Darwin': ["pip3", "install", "--user"],
            'Linux': ["pip3", "install", "--user"]
        }
    
        results = []
        didSucceed = True
    
        # Get the function from switcher dictionary
        commands = systems.get(platform.system())
        if commands is None:
            return self.notSupportedHandler(execution)
        else:
            for package in execution['jobDocument']['packages']:
    
                pkgCommands = commands.copy()
                pkgCommands.append(package['name'])
    
                result = subprocess.run(pkgCommands, shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                results.append(result)
    
                if result.stderr and result.stderr is not None:
                    didSucceed = False
    
            return self.formatResults(results, didSucceed)
            
    def pipUninstall(self, execution):

        systems = {
            'Darwin': ["pip3", "uninstall", "-y"],
            'Linux': ["pip3", "uninstall", "-y"]
        }
    
        results = []
        didSucceed = True
    
        # Get the function from switcher dictionary
        commands = systems.get(platform.system())
        if commands is None:
            return self.notSupportedHandler(execution)
        else:
            for package in execution['jobDocument']['packages']:
    
                pkgCommands = commands.copy()
                pkgCommands.append(package['name'])
    
                result = subprocess.run(pkgCommands, shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                results.append(result)
    
                if result.stderr and result.stderr is not None:
                    didSucceed = False
    
            return self.formatResults(results, didSucceed)

# CONTAINERS

    def listContainers(self, execution):
        client = docker.from_env()
        containers = client.containers.list()

        containerList = []
        didSucceed = True

        for container in containers:
            print(container.short_id + ', ' + container.name + ', ' + container.status + ', ' + container.image.attrs['RepoTags'][0])

            containerList.append(
                {
                    'short_id': container.short_id,
                    'name': container.name,
                    'status': container.status,
                    'repoTag': container.image.attrs['RepoTags'][0]
                })

        JSONPayload = '{"state":{"reported":{"containers":' + json.dumps(containerList) + '}}}'
        self.deviceShadowHandler.shadowUpdate(JSONPayload, customShadowCallback_Update, 5)

        return self.formatResults(containerList, didSucceed)

    def pullContainerImages(self, execution):

        results = []
        didSucceed = True

        session = self.getTemporaryCredentials()

        ecr_client = session.client('ecr')

        response = ecr_client.get_authorization_token()

        token = response['authorizationData'][0]['authorizationToken']

        tokenString = base64.b64decode(token).decode().split(':')[1]

        result = subprocess.run(["docker","login","-u","AWS","-p",tokenString,"661133080262.dkr.ecr.us-east-1.amazonaws.com"], shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        results.append(result)

        if result.stderr and result.stderr is not None:
            didSucceed = False

        for image in execution['jobDocument']['images']:

            result = subprocess.run(["docker","pull",image['url'] + ':' + image['version']], shell=False, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            results.append(result)

            if result.stderr and result.stderr is not None:
                didSucceed = False

        return self.formatResults(containerList, didSucceed)

    def runContainers(self, execution):

        results = []
        didSucceed = True

        for image in execution['jobDocument']['images']:

            client = docker.from_env()
            client.containers.run(image['name'] + ':' + image['version'], detach=True)

        return self.formatResults(results, didSucceed)

    def stopContainers(self, execution):

        results = []
        didSucceed = True

        for container in execution['jobDocument']['containers']:

            client = docker.from_env()
            container = client.containers.get(container)
            container.stop()

        return self.formatResults(results, didSucceed)

    def uploadContainerLogs(self, execution):

        results = []
        didSucceed = True

        session = self.getTemporaryCredentials()

        s3_client = session.client('s3')

        for container in execution['jobDocument']['containers']:

            key = None

            if 'prefix' in container:
                key = container['prefix']

            key += str(time.time()) + '_' + container['id'] + '.log'
            bucket = container['bucket']

            client = docker.from_env()
            container = client.containers.get(container['id'])
            s3_client.put_object(Body=container.logs(), Bucket=bucket, Key=key)

        return self.formatResults(results, didSucceed)

def customShadowCallback_Update(payload, responseStatus, token):
    # payload is a JSON string ready to be parsed using json.loads(...)
    # in both Py2.x and Py3.x
    if responseStatus == "timeout":
        print("Update request " + token + " time out!")
    if responseStatus == "accepted":
        payloadDict = json.loads(payload)
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Update request with token: " + token + " accepted!")
        print(payload)
        print("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
    if responseStatus == "rejected":
        print("Update request " + token + " rejected!")
