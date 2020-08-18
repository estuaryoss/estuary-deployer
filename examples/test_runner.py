import json

import py_eureka_client.eureka_client as eureka_client

from rest.api.responsehelpers.error_codes import ErrorCodes
from rest.api.responsehelpers.http_response import HttpResponse
from tests.rest_docker.constants import Constants


class EurekaClient:

    def __init__(self, host):
        self.host = host

    def get_apps(self):
        apps_list = []
        print(f"Getting apps from eureka server {self.host} ... \n")
        for app in eureka_client.get_applications(eureka_server=f"{self.host}").applications:
            for instance in app.up_instances:
                # print(instance.app)
                apps_list.append({"ip": str(instance.ipAddr),
                                  "port": str(instance.port.port),
                                  "app": str(instance.app.lower()),
                                  "homePageUrl": str(instance.homePageUrl),
                                  "healthCheckUrl": str(instance.healthCheckUrl),
                                  "statusPageUrl": str(instance.statusPageUrl)})
        return apps_list


if __name__ == '__main__':
    # step 1 - get all services registered in eureka
    apps_list = EurekaClient("http://192.168.100.12:8080/eureka/v2").get_apps()
    http = HttpResponse()
    print(json.dumps(
        http.response(Constants.SUCCESS, ErrorCodes.HTTP_CODE.get(Constants.SUCCESS), apps_list)))

    # step 2 - start deploying your test envs on them (until no more ram available to use). Use multi thread
    # TODO

    # step 3 - spread the tests across all env obtained at step 2. Use multi thread
    # TODO
