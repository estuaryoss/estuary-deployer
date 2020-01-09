#!/usr/bin/env python3
import os
import unittest

import requests
from parameterized import parameterized

from tests.rest_docker_sock.constants import Constants
from tests.rest_docker_sock.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    server = "http://localhost:8080/docker"

    expected_version = "4.0.1"

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart(self, template, variables):
        response = requests.post(self.server + f"/deployments/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.DOCKER_DAEMON_NOT_RUNNING))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DOCKER_DAEMON_NOT_RUNNING)
        self.assertIsNotNone(body.get('time'))


if __name__ == '__main__':
    unittest.main()
