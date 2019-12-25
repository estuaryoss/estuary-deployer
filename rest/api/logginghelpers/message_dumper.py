import json
from json import JSONDecodeError


class MessageDumper:

    def set_correlation_id(self, correlation_id):
        self.correlation_id = correlation_id

    def get_correlation_id(self):
        return self.correlation_id

    def dump(self, request):
        headers = dict(request.headers)
        headers["Correlation-Id"] = self.correlation_id

        try:
            body = json.loads(request.get_data())
            body["message"] = json.dumps(body.get("message"))
        except JSONDecodeError:
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
