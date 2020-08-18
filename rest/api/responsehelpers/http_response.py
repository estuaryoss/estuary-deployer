import datetime

from flask import request

from about import properties


class HttpResponse:

    @staticmethod
    def response(code, message, description):
        return {
            "code": code,
            "message": message,
            "description": description,
            "timestamp": str(datetime.datetime.now()),
            "path": request.full_path,
            "name": properties["name"],
            "version": properties["version"]
        }
