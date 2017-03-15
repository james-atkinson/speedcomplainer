
class Logger(object):
    def __init__(self, type, config):
        if type == 'csv':
            self.logger = CsvLogger(config['filename'])

    def log(self, log_items):
        self.logger.log(log_items)


class CsvLogger(object):
    def __init__(self, filename):
        self.filename = filename

    def log(self, log_items):
        with open(self.filename, "a") as logfile:
            logfile.write("{0}\n".format(','.join(log_items)))
