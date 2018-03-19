import datetime
import os
import os_help
import surveillance_config as config

class LogWriter:
    """ For writing events to a log file """
    
    def __init__(self):
        self.log_file = None
    
    def log(self, file_path, time, what):
        if (self.log_file == None or
            self.log_file.name != file_path):
            os_help.ignore_exist(os.makedirs, os.path.dirname(file_path))
            self.log_file = open(file_path, 'a')
        
        timestamp = time.strftime(config.date_time_format)
        self.log_file.write(
            timestamp + ", " + what + "\n")
        self.log_file.flush()

