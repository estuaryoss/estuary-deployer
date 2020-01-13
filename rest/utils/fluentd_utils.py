import datetime
import os
import platform

from about import properties


class FluentdUtils:

    def __init__(self, logger):
        self.logger = logger

    def debug(self, tag, msg):
        message = self.log("DEBUG", msg)
        response = self.emit(tag, message)
        return {"emit": response,
                "message": message}

    def info(self, tag, msg):
        message = self.log("INFO", msg)
        response = self.emit(tag, message)
        return {"emit": response,
                "message": message}

    def warn(self, tag, msg):
        message = self.log("WARN", msg)
        response = self.emit(tag, message)
        return {"emit": response,
                "message": message}

    def error(self, tag, msg):
        message = self.log("ERROR", msg)
        response = self.emit(tag, message)
        return {"emit": response,
                "message": message}

    def fatal(self, tag, msg):
        message = self.log("FATAL", msg)
        response = self.emit(tag, message)
        return {"emit": response,
                "message": message}

    def log(self, level_code, msg):
        return {
            "name": properties.get('name'),
            "port": os.environ.get('PORT') if os.environ.get('PORT') else properties.get('port'),
            "version": properties.get('version'),
            "uname": list(platform.uname()),
            "python": platform.python_version(),
            "pid": os.getpid(),
            "level_code": level_code,
            "msg": msg,
            "timestamp": str(datetime.datetime.now()),
        }

    def emit(self, tag, msg):
        if os.environ.get('FLUENTD_IP_PORT'):
            return str(self.logger.emit(tag, msg)).lower()

        return "fluentd logging not enabled"
