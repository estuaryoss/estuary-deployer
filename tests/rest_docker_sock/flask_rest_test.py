#!/usr/bin/env python3
import unittest

import requests
from parameterized import parameterized

from rest.api.constants.api_constants import ApiConstants
from rest.api.responsehelpers.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    server = "http://localhost:8080/docker"

    expected_version = "4.1.0"

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart(self, template, variables):
        response = requests.post(self.server + f"/deployments/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(ApiConstants.DOCKER_DAEMON_NOT_RUNNING))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiConstants.DOCKER_DAEMON_NOT_RUNNING)
        self.assertIsNotNone(body.get('timestamp'))


if __name__ == '__main__':
    unittest.main()
