
class Logger(object):
    def __init__(self, type, config):
        if type == 'csv':
            self.logger = CsvLogger(config['filename'])

    def log(self, logItems):
        self.logger.log(logItems)

class CsvLogger(object):
    def __init__(self, filename):
        self.filename = filename

    def log(self, logItems):
        with open(self.filename, "w+") as logfile:
            logfile.write("%s\n" % ','.join(logItems))