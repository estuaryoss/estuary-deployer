#!/usr/bin/env python3
import time
import unittest

import requests
from flask import json
from requests_toolbelt.utils import dump

from tests.rest_agent_integration.constants import Constants
from tests.rest_agent_integration.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    server_agent = "http://localhost:8080/docker/container"
    server = "http://localhost:8080/docker"
    script_path = "tests/rest_agent_integration/input"
    # script_path = "input"
    cleanup_count_safe = 5
    compose_id = ""

    @classmethod
    def setUpClass(cls):
        with open(f"{cls.script_path}/agent.yml", closefd=True) as f:
            payload = f.read()

        headers = {'Content-type': 'text/plain'}
        requests.post(f"{FlaskServerTestCase.server}/command",
                      data="docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_TOKEN", headers=headers)
        requests.post(f"{FlaskServerTestCase.server}/deployments", data=payload, headers=headers)
        # print(dump.dump_all(response))
        time.sleep(60)  # wait until the env is up and running, including image download and container boot
        cls.compose_id = cls.get_deployment_info()[0]
        print("Docker compose env_id: " + cls.compose_id)
        response = requests.post(f"{FlaskServerTestCase.server}/deployments/network/{cls.compose_id}")
        # print(dump.dump_all(response))
        print("Docker net connect response: " + json.dumps(response.json()))

    def setUp(self):
        self.compose_id = self.get_deployment_info()[0]
        for i in range(0, self.cleanup_count_safe):
            requests.delete(self.server + f"/container/{self.compose_id}" + "/commanddetached")

    @classmethod
    def tearDownClass(cls):
        deployment_list = cls.get_deployment_info()
        for item in deployment_list:
            requests.delete(f"{FlaskServerTestCase.server}/deployments/{item}")

    @staticmethod
    def get_deployment_info():
        active_deployments = []
        response = requests.get(f"{FlaskServerTestCase.server}/deployments")
        print(dump.dump_all(response))
        body = response.json()
        active_deployments_objects = body.get('description')
        for item in active_deployments_objects:
            active_deployments.append(item.get('id'))

        return active_deployments

    def test_about_endpoint(self):
        response = requests.get(self.server_agent + f"/{self.compose_id}" + "/about")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(body.get('description'), dict)
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('timestamp'))


if __name__ == '__main__':
    unittest.main()
