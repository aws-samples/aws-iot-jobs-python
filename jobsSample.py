'''
 /*
  * Copyright 2019 Amazon.com, Inc. and its affiliates. All Rights Reserved.
  *
  * Licensed under the MIT License. See the LICENSE accompanying this file
  * for the specific language governing permissions and limitations under
  * the License.
  */
 '''
from AWSIoTPythonSDK.MQTTLib import DROP_OLDEST
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTThingJobsClient
from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionTopicType
from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionTopicReplyType
from AWSIoTPythonSDK.core.jobs.thingJobManager import jobExecutionStatus
from jobExecutor import JobExecutor

import threading
import logging
import time
import datetime
import argparse
import json


class Config:
    thingName = None
    clientId = None
    topic = None
    mode = None
    message = None
    host = None
    rootCAPath = None
    certificatePath = None
    privateKeyPath = None
    useWebsocket = False
    credentialsEndpoint = None
    region = None
    port = 8883
    roleAlias = None


class JobsMessageProcessor(object):
    def __init__(self, awsIoTMQTTThingJobsClient, clientToken, jobExecutor):
        #keep track of this to correlate request/responses
        self.clientToken = clientToken
        self.awsIoTMQTTThingJobsClient = awsIoTMQTTThingJobsClient
        self.done = False
        self.jobsStarted = 0
        self.jobsSucceeded = 0
        self.jobsRejected = 0
        self._setupCallbacks(self.awsIoTMQTTThingJobsClient)
        self.jobExecutor = jobExecutor

    def _setupCallbacks(self, awsIoTMQTTThingJobsClient):
        self.awsIoTMQTTThingJobsClient.createJobSubscription(
            self.newJobReceived, jobExecutionTopicType.JOB_NOTIFY_NEXT_TOPIC)
        self.awsIoTMQTTThingJobsClient.createJobSubscription(
            self.startNextJobSuccessfullyInProgress, jobExecutionTopicType.JOB_START_NEXT_TOPIC, jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE)
        self.awsIoTMQTTThingJobsClient.createJobSubscription(
            self.startNextRejected, jobExecutionTopicType.JOB_START_NEXT_TOPIC, jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE)

        # '+' indicates a wildcard for jobId in the following subscriptions
        self.awsIoTMQTTThingJobsClient.createJobSubscription(
            self.updateJobSuccessful, jobExecutionTopicType.JOB_UPDATE_TOPIC, jobExecutionTopicReplyType.JOB_ACCEPTED_REPLY_TYPE, '+')
        self.awsIoTMQTTThingJobsClient.createJobSubscription(
            self.updateJobRejected, jobExecutionTopicType.JOB_UPDATE_TOPIC, jobExecutionTopicReplyType.JOB_REJECTED_REPLY_TYPE, '+')

    #call back on successful job updates
    def startNextJobSuccessfullyInProgress(self, client, userdata, message):
        payload = json.loads(message.payload.decode('utf-8'))
        if 'execution' in payload:
            self.jobsStarted += 1
            execution = payload['execution']
            result = self.executeJob(execution)
            result['HandledBy'] = 'ClientToken: {}'.format(self.clientToken)

            if result['didSucceed'] == True:

                threading.Thread(target=self.awsIoTMQTTThingJobsClient.sendJobsUpdate, kwargs={
                                 'jobId': execution['jobId'], 'status': jobExecutionStatus.JOB_EXECUTION_SUCCEEDED, 'statusDetails': result, 'expectedVersion': execution['versionNumber'], 'executionNumber': execution['executionNumber']}).start()

            else:

                threading.Thread(target=self.awsIoTMQTTThingJobsClient.sendJobsUpdate, kwargs={
                                 'jobId': execution['jobId'], 'status': jobExecutionStatus.JOB_EXECUTION_FAILED, 'statusDetails': result, 'expectedVersion': execution['versionNumber'], 'executionNumber': execution['executionNumber']}).start()

        else:
            print('Start next saw no execution: ' +
                  message.payload.decode('utf-8'))
            self.done = True

    def executeJob(self, execution):
        print('Executing job ID, version, number: {}, {}, {}'.format(
            execution['jobId'], execution['versionNumber'], execution['executionNumber']))
        print('With jobDocument: ' + json.dumps(execution['jobDocument']))

        return self.jobExecutor.executeJob(execution)

    def newJobReceived(self, client, userdata, message):
        payload = json.loads(message.payload.decode('utf-8'))
        if 'execution' in payload:
            self._attemptStartNextJob()
        else:
            print('Notify next saw no execution')
            self.done = True

    def processJobs(self):
        self.done = False
        self._attemptStartNextJob()

    def startNextRejected(self, client, userdata, message):
        print('Start next rejected:' + message.payload.decode('utf-8'))
        self.jobsRejected += 1

    def updateJobSuccessful(self, client, userdata, message):
        self.jobsSucceeded += 1

    def updateJobRejected(self, client, userdata, message):
        self.jobsRejected += 1

    def _attemptStartNextJob(self):
        statusDetails = {'StartedBy': 'ClientToken: {} on {}'.format(
            self.clientToken, datetime.datetime.now().isoformat())}
        threading.Thread(target=self.awsIoTMQTTThingJobsClient.sendJobsStartNext, kwargs={
                         'statusDetails': statusDetails}).start()

    def isDone(self):
        return self.done

    def getStats(self):
        stats = {}
        stats['jobsStarted'] = self.jobsStarted
        stats['jobsSucceeded'] = self.jobsSucceeded
        stats['jobsRejected'] = self.jobsRejected
        return stats


def getConfig():

        config = Config()

        with open('config.json') as configFile:
            jsonConfig = json.load(configFile)
            config.thingName = jsonConfig['thingName']
            config.clientId = config.thingName
            config.topic = config.thingName
            config.mode = 'both'
            config.message = 'Hello World'
            config.host = jsonConfig['endpoint']

            config.rootCAPath = jsonConfig['rootCaPath']

            config.certificatePath = jsonConfig['deviceCertificatePath']

            config.privateKeyPath = jsonConfig['privateKeyPath']

            config.credentialsEndpoint = jsonConfig['credentialsEndpoint']
            config.region = jsonConfig['region']
            config.roleAlias = jsonConfig['roleAlias']

            useWebsocket = jsonConfig['useWebsocket']
            config.useWebsocket = useWebsocket == 'true'
            config.port = int(jsonConfig['port'])

        return config


def getDefaultEnv(jsonConfig):

    for env in jsonConfig['environments']:
        if env['default']:
            return env


def getDefaultRegion(jsonEnvConfig):

    for region in jsonEnvConfig['regions']:
        if region['default']:
            return region


# Read in command-line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-j", "--config", action="store",
                    dest="configPath", help="JSON config file")
parser.add_argument("-n", "--thingName", action="store", dest="thingName",
                    help="Your AWS IoT ThingName to process jobs for")
parser.add_argument("-e", "--endpoint", action="store",
                    dest="host", help="Your AWS IoT custom endpoint")
parser.add_argument("-r", "--rootCA", action="store",
                    dest="rootCAPath", help="Root CA file path")
parser.add_argument("-c", "--cert", action="store",
                    dest="certificatePath", help="Certificate file path")
parser.add_argument("-k", "--key", action="store",
                    dest="privateKeyPath", help="Private key file path")
parser.add_argument("-p", "--port", action="store",
                    dest="port", type=int, help="Port number override")
parser.add_argument("-a", "--roleAlias", action="store",
                    dest="roleAlias", help="Role alias for device")
parser.add_argument("-m", "--region", action="store",
                    dest="region", default="us-east-1", help="Region")
parser.add_argument("-x", "--credentialsEndpoint", action="store",
                    dest="credentialsEndpoint", help="IoT Credentials endpoint")
parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,
                    help="Use MQTT over WebSocket")
parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicJobsSampleClient",
                    help="Targeted client id")

config = None
args = parser.parse_args()

if args.configPath:
    config = getConfig()
else:
    config = Config()

    config.host = args.host
    config.rootCAPath = args.rootCAPath
    config.certificatePath = args.certificatePath
    config.privateKeyPath = args.privateKeyPath
    config.port = args.port
    config.useWebsocket = args.useWebsocket
    config.clientId = args.clientId
    config.thingName = args.thingName
    config.region = args.region
    config.credentialsEndpoint = args.credentialsEndpoint
    config.roleAlias = args.roleAlias

# print(config.host)
# print(config.rootCAPath)
# print(config.certificatePath)
# print(config.privateKeyPath)
# print(config.port)
# print(config.useWebsocket)
# print(config.clientId)
# print(config.thingName)
# print(config.region)
# print(config.credentialsEndpoint)
# print(config.roleAlias)

if config.useWebsocket and config.certificatePath and config.privateKeyPath:
    parser.error(
        "X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
    exit(2)

if not config.useWebsocket and (not config.certificatePath or not config.privateKeyPath):
    parser.error("Missing credentials for authentication.")
    exit(2)

# Port defaults
if config.useWebsocket and not config.port:  # When no port override for WebSocket, default to 443
    port = 443
# When no port override for non-WebSocket, default to 8883
if not config.useWebsocket and not config.port:
    port = 8883

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTClient
myAWSIoTMQTTClient = None
if config.useWebsocket:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(config.clientId, useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint(config.host, config.port)
    myAWSIoTMQTTClient.configureCredentials(config.rootCAPath)
else:
    myAWSIoTMQTTClient = AWSIoTMQTTClient(config.clientId)
    myAWSIoTMQTTClient.configureEndpoint(config.host, config.port)
    myAWSIoTMQTTClient.configureCredentials(
        config.rootCAPath, config.privateKeyPath, config.certificatePath)

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(10)  # 5 sec

jobsClient = AWSIoTMQTTThingJobsClient(
    config.clientId, config.thingName, QoS=1, awsIoTMQTTClient=myAWSIoTMQTTClient)

# Init AWSIoTMQTTShadowClient
myAWSIoTMQTTShadowClient = None
if config.useWebsocket:
    myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(
        config.clientId, useWebsocket=True)
    myAWSIoTMQTTShadowClient.configureEndpoint(config.host, config.port)
    myAWSIoTMQTTShadowClient.configureCredentials(config.rootCAPath)
else:
    myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(config.clientId)
    myAWSIoTMQTTShadowClient.configureEndpoint(config.host, config.port)
    myAWSIoTMQTTShadowClient.configureCredentials(
        config.rootCAPath, config.privateKeyPath, config.certificatePath)

# AWSIoTMQTTShadowClient configuration
myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
MQTTClient = myAWSIoTMQTTShadowClient.getMQTTConnection()
MQTTClient.configureOfflinePublishQueueing(5, DROP_OLDEST)
# Connect to AWS IoT Shadow
myAWSIoTMQTTShadowClient.connect()

# Create a deviceShadow with persistent subscription
deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(
    config.thingName, True)

print('Connecting to MQTT server and setting up callbacks...')
jobsClient.connect()
jobExecutor = JobExecutor(config, deviceShadowHandler)
jobsMsgProc = JobsMessageProcessor(jobsClient, config.clientId, jobExecutor)

print('Starting to process jobs...')
while True:
    jobsMsgProc.processJobs()
    while not jobsMsgProc.isDone():
        time.sleep(2)
    time.sleep(10)

print('Done processing jobs')
print('Stats: ' + json.dumps(jobsMsgProc.getStats()))

jobsClient.disconnect()
