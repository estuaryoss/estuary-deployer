#!/usr/bin/env python3
import time
import unittest

import requests
from flask import json
from requests_toolbelt.utils import dump

from tests.rest_testrunner_integration.constants import Constants
from tests.rest_testrunner_integration.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    server_discovery = "http://localhost:8080/docker/container"
    server = "http://localhost:8080/docker"
    script_path = "tests/rest_discovery_integration/input"
    # script_path = "input"
    discovery_expected_version = "4.0.1"
    testrunner_expected_version = "4.0.1"
    cleanup_count_safe = 5
    compose_id = ""

    @classmethod
    def setUpClass(cls):

        with open(f"{cls.script_path}/alpinetestrunner.yml", closefd=True) as f:
            payload = f.read()

        headers = {'Content-type': 'text/plain'}
        requests.post(f"{FlaskServerTestCase.server}/deploystart", data=payload, headers=headers)
        with open(f"{cls.script_path}/alpinediscovery.yml", closefd=True) as f:
            payload = f.read()
        headers = {'Content-type': 'text/plain'}
        requests.post(f"{FlaskServerTestCase.server}/deploystart", data=payload, headers=headers)

        # print(dump.dump_all(response))
        time.sleep(60)  # wait until the env is up and running, including image download and container boot
        for item in cls.get_deployment_info():
            response = requests.get(f"{FlaskServerTestCase.server}/containernetconnect/{item.get('id')}")
            if "discovery" in item.get('containers')[0]:
                cls.compose_id = item.get('id')
                print("Docker compose env_id: " + cls.compose_id)
                print("Docker net connect response: " + json.dumps(response.json()))

    @classmethod
    def tearDownClass(cls):
        deployment_list = cls.get_deployment_info()
        # for item in deployment_list:
        #     requests.get(f"{FlaskServerTestCase.server}/deploystop/{item.get('id')}")

    @staticmethod
    def get_deployment_info():
        active_deployments = []
        response = requests.get(f"{FlaskServerTestCase.server}/getdeploymentinfo")
        print(dump.dump_all(response))
        return response.json().get('message')

    def test_about_endpoint_discovery_p(self):
        response = requests.get(self.server_discovery + f"/{self.compose_id}/about")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), "estuary-discovery")
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.discovery_expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_about_endpoint_discovery_broadcast_to_testrunner_p(self):
        response = requests.get(self.server_discovery + f"/{self.compose_id}/testrunner/about")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message')[0].get('message'), "estuary-testrunner")
        self.assertEqual(body.get('message')[0].get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('message')[0].get('version'), self.testrunner_expected_version)
        self.assertEqual(body.get('message')[0].get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('message')[0].get('time'))


if __name__ == '__main__':
    unittest.main()