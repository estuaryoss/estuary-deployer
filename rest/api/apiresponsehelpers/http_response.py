import datetime

from about import properties


class HttpResponse:

    @staticmethod
    def success(code, description, message):
        return {
            "message": message,
            "description": description,
            "code": code,
            "time": str(datetime.datetime.now()),
            "name": properties["name"],
            "version": properties["version"]
        }

    @staticmethod
    def failure(code, description, message, stacktrace):
        return {
            "message": message,
            "description": description,
            "code": code,
            "stacktrace": stacktrace,
            "time": str(datetime.datetime.now()),
            "name": properties["name"],
            "version": properties["version"]
        }
