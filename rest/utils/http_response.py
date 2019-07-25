import datetime

from about import properties


class HttpResponse:

    def success(self, code, description, message):
        return {
            "message": message,
            "description": description,
            "code": code,
            "time": datetime.datetime.now(),
            "version": properties["version"]
        }

    def failure(self, code, description, message, stacktrace):
        return {
            "message": message,
            "description": description,
            "code": code,
            "stacktrace": stacktrace,
            "time": datetime.datetime.now(),
            "version": properties["version"]
        }
