import requests


class RestService:
    def __init__(self):
        pass

    def get(self, url):
        return requests.get(url, timeout=2)
