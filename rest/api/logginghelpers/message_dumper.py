import json
from json import JSONDecodeError


class MessageDumper:

    def __init__(self):
        self.response_headers = {}

    def set_header(self, name, value):
        self.response_headers[name] = value

    def get_header(self, name):
        return self.response_headers.get(name)

    def get_headers(self):
        return self.response_headers

    def dump(self, request):
        headers = dict(request.headers)
        for key in self.response_headers:
            headers[key] = self.response_headers.get(key)

        try:
            body = json.loads(request.get_data())
            body["message"] = json.dumps(body.get("message"))  # can be anything, so it will break elasticsearch things
        except (JSONDecodeError, AttributeError, RuntimeError):
            body = {"message": "NA"}

        return {
            "headers": headers,
            "body": body
        }

    def dump_message(self, message):
        return {
            "headers": {},
            "body": {"message": json.dumps(message)}
        }
