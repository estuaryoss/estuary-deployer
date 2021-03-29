#!/usr/bin/env python3
import os
import unittest

from py_eureka_client import eureka_client


class EurekaClient:
    def __init__(self, host):
        self.host = host

    def get_apps(self):
        apps_list = []
        print(f"Getting apps from eureka server {self.host} ... \n")
        for app in eureka_client.get_applications(eureka_server=f"{self.host}").applications:
            for instance in app.up_instances:
                # print(instance.app)
                apps_list.append(instance)
        return apps_list


class FlaskServerEurekaTestCase(unittest.TestCase):

    def test_eureka_registration(self):
        app_append_label = f"{os.environ.get('APP_APPEND_LABEL')}"
        up_services = EurekaClient("http://localhost:8080/eureka/v2").get_apps()
        self.assertEqual(len(up_services), 1)  # 1 instance registered
        # print(up_services[0].app)
        self.assertEqual(up_services[0].app, f"estuary-deployer{app_append_label}".upper())  # 1 instance registered
        self.assertEqual(up_services[0].ipAddr, f"estuary-deployer")  # 1 instance registered


if __name__ == '__main__':
    unittest.main()
