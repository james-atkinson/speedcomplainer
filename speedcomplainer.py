from __future__ import print_function
import os
import sys
import time
from datetime import datetime
import signal
import re
import threading
import twitter
import json
import random
import subprocess
from logger import Logger

shutdown_flag = False

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def main(filename, argv):
    print("======================================")
    print(" Starting Speed Complainer!           ")
    print(" Lets get noisy!                      ")
    print("======================================")

    global shutdown_flag
    signal.signal(signal.SIGINT, shutdown_handler)

    monitor = Monitor()

    while not shutdown_flag:
        try:

            monitor.run()

            for i in range(0, 5):
                if shutdown_flag:
                    break
                time.sleep(1)

        except Exception as e:
            print('Error: {0}'.format(e))
            sys.exit(1)

    sys.exit()


def shutdown_handler(signo, stack_frame):
    global shutdown_flag
    print('Got shutdown signal ({0}: {1}).'.format(signo, stack_frame))
    shutdown_flag = True


def read_json(file_path):
    try:
        with open(file_path) as f:
            return json.load(f)
    except IOError as e:
        print("Unable to open json file: ./config.json")
        print("Exception {0}".format(e))
        sys.exit(1)
    except ValueError as e:
        print("Invalid JSON")
        print("Exception {0}".format(e))
        sys.exit(1)


class Monitor(object):
    def __init__(self):
        self.last_ping_check = None
        self.last_speed_test = None

    def run(self):
        if self.last_ping_check in None \
                or (datetime.now() - self.last_ping_check).total_seconds() >= 60:
            self.run_ping_test()
            self.last_ping_check = datetime.now()

        if self.last_speed_test is None \
                or (datetime.now() - self.last_speed_test).total_seconds() >= 3600:
            self.run_speed_test()
            self.last_speed_test = datetime.now()

    @staticmethod
    def run_ping_test():
        ping_thread = PingTest()
        ping_thread.start()

    @staticmethod
    def run_speed_test():
        speed_thread = SpeedTest()
        speed_thread.start()


class PingTest(threading.Thread):
    def __init__(self, num_pings=3, ping_timeout=2, max_wait_time=6):
        super(PingTest, self).__init__()
        self.num_pings = num_pings
        self.ping_timeout = ping_timeout
        self.max_wait_time = max_wait_time
        self.config = read_json('./config.json')
        self.logger = Logger(self.config['log']['type'],
                             {'filename': self.config['log']['files']['ping']})

    def run(self):
        ping_results = self.do_ping_test()
        self.log_ping_results(ping_results)

    def do_ping_test(self):
        response = os.system("ping -c {0} -W {1} -w {2} 8.8.8.8 > /dev/null 2>&1".
                             format(self.num_pings,
                                    (self.ping_timeout * 1000), self.max_wait_time))
        return {
            'date': datetime.now(),
            'success': 1 if response == 0 else 0
        }

    def log_ping_results(self, ping_results):
        self.logger.log([ping_results['date'].strftime(DATE_FORMAT),
                         str(ping_results['success'])])


class SpeedTest(threading.Thread):
    def __init__(self):
        super(SpeedTest, self).__init__()
        self.config = read_json('./config.json')
        self.logger = Logger(self.config['log']['type'],
                             {'filename': self.config['log']['files']['speed']})

    def run(self):
        speed_test_results = self.do_speed_test()
        self.log_speed_test_results(speed_test_results)
        self.tweet_results(speed_test_results)

    @staticmethod
    def do_speed_test():
        # Find speedtest-cli and run test
        cli_path = subprocess.check_output('which speedtest-cli', shell=True)
        result = os.popen("{0} --simple".format(cli_path.rstrip())).read()
        if 'Cannot' in result:
            return {'date': datetime.now(), 'uploadResult': 0, 'downloadResult': 0, 'ping': 0}

        # Result:
        # Ping: 529.084 ms
        # Download: 0.52 Mbit/s
        # Upload: 1.79 Mbit/s

        ping_result, download_result, upload_result = result.split('\n')

        # RegEx Pattern
        pattern = "\d+\.\d+"

        ping_result = float(re.search(pattern, ping_result).group())
        download_result = float(re.search(pattern, download_result).group())
        upload_result = float(re.search(pattern, upload_result).group())

        return {
                'date': datetime.now(),
                'uploadResult': upload_result,
                'downloadResult': download_result,
                'ping': ping_result
        }

    def log_speed_test_results(self, speed_test_results):
        self.logger.log([speed_test_results['date'].strftime(DATE_FORMAT),
                         str(speed_test_results['uploadResult']),
                         str(speed_test_results['downloadResult']),
                         str(speed_test_results['ping'])])

    def tweet_results(self, speed_test_results):
        threshold_messages = self.config['tweetThresholds']
        message = None
        for (threshold, messages) in threshold_messages.items():
            threshold = float(threshold)
            if speed_test_results['downloadResult'] < threshold:
                # ToDo - Change Replace to String or Jinja Template
                message = messages[random.randint(0, len(messages) - 1)].\
                    replace('{tweetTo}', self.config['tweetTo']).\
                    replace('{internetSpeed}', self.config['internetSpeed']).\
                    replace('{downloadResult}', str(speed_test_results['downloadResult']))

        if message:
            api = twitter.Api(consumer_key=self.config['twitter']['twitterConsumerKey'],
                              consumer_secret=self.config['twitter']['twitterConsumerSecret'],
                              access_token_key=self.config['twitter']['twitterToken'],
                              access_token_secret=self.config['twitter']['twitterTokenSecret']
                              )
            if api:
                # ToDo - Do something with the status
                status = api.PostUpdate(message)
                print("Status {0}".format(status))


class DaemonApp(object):
    def __init__(self, pid_file_path, stdout_path='/dev/null', stderr_path='/dev/null'):
        self.stdin_path = '/dev/null'
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.pidfile_path = pid_file_path
        self.pidfile_timeout = 1

    @staticmethod
    def run():
        main(__file__, sys.argv[1:])


if __name__ == '__main__':
    main(__file__, sys.argv[1:])

    working_directory = os.path.basename(os.path.realpath(__file__))
    stdout_path = '/dev/null'
    stderr_path = '/dev/null'
    file_name, file_ext = os.path.split(os.path.realpath(__file__))
    pid_file_path = os.path.join(working_directory, os.path.basename(file_name) + '.pid')
    from daemon import runner
    dRunner = runner.DaemonRunner(DaemonApp(pid_file_path, stdout_path, stderr_path))
    dRunner.daemon_context.working_directory = working_directory
    dRunner.daemon_context.umask = 0o002
    dRunner.daemon_context.signal_map = {signal.SIGTERM: 'terminate', signal.SIGUP: 'terminate'}
    dRunner.do_action()
