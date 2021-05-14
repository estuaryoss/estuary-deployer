#!/usr/bin/env python3
import unittest

import requests
from parameterized import parameterized

from rest.api.constants.api_code import ApiCode
from rest.api.responsehelpers.error_message import ErrorMessage


class FlaskServerTestCase(unittest.TestCase):
    server = "http://localhost:8080/docker"

    expected_version = "4.2.3"

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart(self, template, variables):
        response = requests.post(self.server + f"/deployments/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.DOCKER_DAEMON_NOT_RUNNING.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.DOCKER_DAEMON_NOT_RUNNING.value)
        self.assertIsNotNone(body.get('timestamp'))


if __name__ == '__main__':
    unittest.main()
