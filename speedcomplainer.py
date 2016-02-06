import os
import sys
import time
from datetime import datetime
import daemon
import signal
import threading
import twitter
import json
import random
from twilio.rest import TwilioRestClient
from logger import Logger

shutdownFlag = False

def main(filename, argv):
    print("======================================")
    print(" Starting Speed Complainer!           ")
    print(" Lets get noisy!                      ")
    print("======================================")

    global shutdownFlag
    signal.signal(signal.SIGINT, shutdownHandler)

    monitor = Monitor()
    while not shutdownFlag:
        try:

            monitor.run()

            for i in range(0, 5):
                if shutdownFlag:
                    break
                time.sleep(1)

        except Exception as e:
            print('Error: %s' % e)
            sys.exit(1)

    sys.exit()

def shutdownHandler(signo, stack_frame):
    global shutdownFlag
    print('Got shutdown signal (%s: %s).' % (signo, stack_frame))
    shutdownFlag = True

class Monitor():
    def __init__(self):
        self.lastPingCheck = None
        self.lastSpeedTest = None

    def run(self):
        if not self.lastPingCheck or (datetime.now() - self.lastPingCheck).total_seconds() >= 60:
            self.runPingTest()
            self.lastPingCheck = datetime.now()

        if not self.lastSpeedTest or (datetime.now() - self.lastSpeedTest).total_seconds() >= 3600:
            self.runSpeedTest()
            self.lastSpeedTest = datetime.now()

    def runPingTest(self):
        pingThread = PingTest()
        pingThread.start()

    def runSpeedTest(self):
        speedThread = SpeedTest()
        speedThread.start()

class PingTest(threading.Thread):
    def __init__(self, numPings=3, pingTimeout=2, maxWaitTime=6):
        super(PingTest, self).__init__()
        self.numPings = numPings
        self.pingTimeout = pingTimeout
        self.maxWaitTime = maxWaitTime
        self.config = json.load(open('./config.json'))
        self.logger = Logger(self.config['log']['type'], { 'filename': self.config['log']['files']['ping'] })

    def run(self):
        pingResults = self.doPingTest()
        self.logPingResults(pingResults)

    def doPingTest(self):
        response = os.system("ping -c %s -W %s -w %s 8.8.8.8 > /dev/null 2>&1" % (self.numPings, (self.pingTimeout * 1000), self.maxWaitTime))
        success = 0
        if response == 0:
            success = 1
        return { 'date': datetime.now(), 'success': success }

    def logPingResults(self, pingResults):
        self.logger.log([ pingResults['date'].strftime('%Y-%m-%d %H:%M:%S'), str(pingResults['success'])])


class SpeedTest(threading.Thread):
    def __init__(self):
        super(SpeedTest, self).__init__()
        self.config = json.load(open('config.json'))
        self.logger = Logger(self.config['log']['type'], { 'filename': self.config['log']['files']['speed'] })

    def run(self):
        speedTestResults = self.doSpeedTest()
        self.logSpeedTestResults(speedTestResults)
        self.smsResults(speedTestResults)
        self.tweetResults(speedTestResults)

    def doSpeedTest(self):
        # Run a speed test
        result = os.popen("speedtest_cli.py --simple").read()
        if 'Cannot' in result:
            return { 'date': datetime.now(), 'uploadResult': 0, 'downloadResult': 0, 'ping': 0 }

        # Result:
        # Ping: 529.084 ms
        # Download: 0.52 Mbit/s
        # Upload: 1.79 Mbit/s

        resultSet = result.split('\n')
        pingResult = resultSet[0]
        downloadResult = resultSet[1]
        uploadResult = resultSet[2]

        pingResult = float(pingResult.replace('Ping: ', '').replace(' ms', ''))
        downloadResult = float(downloadResult.replace('Download: ', '').replace(' Mbit/s', ''))
        uploadResult = float(uploadResult.replace('Upload: ', '').replace(' Mbit/s', ''))

        return { 'date': datetime.now(), 'uploadResult': uploadResult, 'downloadResult': downloadResult, 'ping': pingResult }

    def logSpeedTestResults(self, speedTestResults):
        self.logger.log([ speedTestResults['date'].strftime('%Y-%m-%d %H:%M:%S'), str(speedTestResults['uploadResult']), str(speedTestResults['downloadResult']), str(speedTestResults['ping']) ])

    def tweetResults(self, speedTestResults):
        print("Tweeting results.")
        thresholdMessages = self.config['tweetThresholds']
        message = None
        for (threshold, messages) in thresholdMessages.items():
            threshold = float(threshold)
            if speedTestResults['downloadResult'] < threshold:
                message = messages[random.randint(0, len(messages) - 1)].replace('{tweetTo}', self.config['tweetTo']).replace('{internetSpeed}', self.config['internetSpeed']).replace('{downloadResult}', str(speedTestResults['downloadResult']))

        if message:
            api = twitter.Api(consumer_key=self.config['twitter']['twitterConsumerKey'],
                            consumer_secret=self.config['twitter']['twitterConsumerSecret'],
                            access_token_key=self.config['twitter']['twitterToken'],
                            access_token_secret=self.config['twitter']['twitterTokenSecret'])

            if api:
                status = api.PostUpdate(message)

    def smsResults(self, speedTestResults):
        print("Sending results via SMS.")
        thresholdMessages = self.config['smsThresholds']
        message = None
        for (threshold, messages) in thresholdMessages.items():
            threshold = float(threshold)
            if speedTestResults['downloadResult'] < threshold:
                message = messages[0].replace('{internetSpeed}', self.config['internetSpeed']).replace('{downloadResult}', str(speedTestResults['downloadResult']))

        if message:
            account = self.config['twilio']['account']
            token = self.config['twilio']['token']

            client = TwilioRestClient(account, token)

            client.messages.create(
                to=self.config['smsTo'],
                from_=self.config['smsFrom'],
                body=message
            )

class DaemonApp():
    def __init__(self, pidFilePath, stdout_path='/dev/null', stderr_path='/dev/null'):
        self.stdin_path = '/dev/null'
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.pidfile_path = pidFilePath
        self.pidfile_timeout = 1

    def run(self):
        main(__file__, sys.argv[1:])

if __name__ == '__main__':
    main(__file__, sys.argv[1:])

    workingDirectory = os.path.basename(os.path.realpath(__file__))
    stdout_path = '/dev/null'
    stderr_path = '/dev/null'
    fileName, fileExt = os.path.split(os.path.realpath(__file__))
    pidFilePath = os.path.join(workingDirectory, os.path.basename(fileName) + '.pid')
    from daemon import runner
    dRunner = runner.DaemonRunner(DaemonApp(pidFilePath, stdout_path, stderr_path))
    dRunner.daemon_context.working_directory = workingDirectory
    dRunner.daemon_context.umask = 0o002
    dRunner.daemon_context.signal_map = { signal.SIGTERM: 'terminate', signal.SIGUP: 'terminate' }
    dRunner.do_action()
