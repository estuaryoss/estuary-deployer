import datetime
import os
import platform

from about import properties
from rest.utils.env_startup import EnvStartup


class Fluentd:

    def __init__(self, logger):
        self.logger = logger

    def emit(self, tag, msg, level="DEBUG"):
        message = self.__enrich_message(level_code=level, msg=msg)
        response = self.__emit(tag, message)
        return {"emit": response,
                "message": message}

    @staticmethod
    def __enrich_message(level_code, msg):
        return {
            "name": properties.get('name'),
            "port": EnvStartup.get_instance().get("port"),
            "version": properties.get('version'),
            "uname": list(platform.uname()),
            "python": platform.python_version(),
            "pid": os.getpid(),
            "level_code": level_code,
            "msg": msg,
            "timestamp": str(datetime.datetime.now()),
        }

    def __emit(self, tag, msg):
        if EnvStartup.get_instance().get("fluentd_ip_port"):
            return str(self.logger.emit(tag, msg)).lower()

        return "fluentd logging not enabled"
