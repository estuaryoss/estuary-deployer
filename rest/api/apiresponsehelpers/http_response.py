import datetime

from about import properties


class HttpResponse:

    @staticmethod
    def response(code, message, description):
        return {
            "code": code,
            "message": message,
            "description": description,
            "time": str(datetime.datetime.now()),
            "name": properties["name"],
            "version": properties["version"]
        }
