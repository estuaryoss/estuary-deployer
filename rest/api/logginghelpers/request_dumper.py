import json


class RequestDumper:

    def set_correlation_id(self, correlation_id):
        self.correlation_id = correlation_id

    def get_correlation_id(self):
        return self.correlation_id

    def dump(self, request):
        headers = dict(request.headers)
        headers["Correlation-Id"] = self.correlation_id

        try:
            body = json.loads(request.get_data())
        except Exception as e:
            body = "NA"

        return {
            "headers": headers,
            "data": body
        }
