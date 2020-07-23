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
            body["description"] = json.dumps(
                body.get("description"))  # can be anything, so it will break elasticsearch things
        except:
            body = {"message": str(request.get_data())}

        return {
            "headers": headers,
            "body": body
        }

    def dump_message(self, message):
        return {
            "headers": {},
            "body": {"message": json.dumps(message)}
        }
