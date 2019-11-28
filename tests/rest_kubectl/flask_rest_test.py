#!/usr/bin/env python3
import unittest

import requests
import yaml
from flask import json
from parameterized import parameterized
from requests_toolbelt.utils import dump

from tests.rest_docker.constants import Constants
from tests.rest_docker.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    server = "http://localhost:8080/kubectl"

    expected_version = "4.0.0"
    sleep_before_container_up = 5

    def test_env_endpoint(self):
        response = requests.get(self.server + "/env")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 7)
        self.assertEqual(body.get('message')["VARS_DIR"], "/variables")
        self.assertEqual(body.get('message')["TEMPLATES_DIR"], "/data")
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_ping_endpoint(self):
        response = requests.get(self.server + "/ping")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), "pong")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_about_endpoint(self):
        response = requests.get(self.server + "/about")
        name = "estuary-deployer"

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), name)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('name'), name)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_swagger_endpoint(self):
        response = requests.get(self.server + "/api/docs")

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body.find("html") >= 0)

    def test_swagger_yml_endpoint(self):
        response = requests.get(self.server + "/swagger/swagger.yml")

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 200)
        # self.assertTrue(len(body.get('paths')) == 14)

    @parameterized.expand([
        ("json.j2", "json.json"),
        ("yml.j2", "yml.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        response = requests.get(self.server + f"/rend/{template}/{variables}", Loader=yaml.Loader)

        body = yaml.load(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body), 3)

    @parameterized.expand([
        ("json.j2", "doesnotexists.json"),
        ("yml.j2", "doesnotexists.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        expected = f"Exception([Errno 2] No such file or directory: \'/variables/{variables}\')"

        response = requests.get(self.server + f"/rend/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(expected, body.get("message"))

    @parameterized.expand([
        ("doesnotexists.j2", "json.json"),
        ("doesnotexists.j2", "yml.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        expected = f"Exception({template})"

        response = requests.get(self.server + f"/rend/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(expected, body.get("message"))

    @parameterized.expand([
        ("standalone.yml", "variables.yml")
    ])
    def test_rendwithenv_endpoint(self, template, variables):
        payload = {'DATABASE': 'mysql56', 'IMAGE': 'latest'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/rendwithenv/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get("services")), 2)
        self.assertEqual(int(body.get("version")), 3)

    def test_getdeployerfile_p(self):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/etc/hostname'
        }

        response = requests.post(self.server + f"/getfile", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.text), 0)

    def test_getdeployerfile_n(self):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/etc/dummy'
        }

        response = requests.post(self.server + f"/getfile", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_FILE_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_getdeployerfile_missing_param_n(self):
        header_key = 'File-Path'
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/getfile", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.HTTP_HEADER_NOT_PROVIDED) % header_key)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.HTTP_HEADER_NOT_PROVIDED)
        self.assertIsNotNone(body.get('time'))

    def test_getenv_endpoint_p(self):
        env_var = "VARS_DIR"
        response = requests.get(self.server + f"/getenv/{env_var}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertIsNotNone(body.get('message'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_getenv_endpoint_n(self):
        env_var = "alabalaportocala"
        response = requests.get(self.server + f"/getenv/{env_var}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_ENV_VAR_FAILURE) % env_var.upper())
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_ENV_VAR_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "{\"file\": \"/dummy/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadfile_n(self, payload):
        headers = {'Content-type': 'application/json'}
        mandatory_header_key = 'File-Path'

        response = requests.post(
            self.server + f"/uploadfile",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.HTTP_HEADER_NOT_PROVIDED) % mandatory_header_key)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.HTTP_HEADER_NOT_PROVIDED)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ""
    ])
    def test_uploadfile_n(self, payload):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/tmp/config.properties'
        }

        response = requests.post(
            self.server + f"/uploadfile",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.EMPTY_REQUEST_BODY_PROVIDED))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.EMPTY_REQUEST_BODY_PROVIDED)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "{\"file\": \"/tmp/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadfile_p(self, payload):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/tmp/config.properties'
        }

        response = requests.post(
            self.server + f"/uploadfile",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_executecommand_n(self):
        command = "dir"  # not working on linux

        response = requests.post(
            self.server + f"/executecommand",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertNotEqual(body.get('message').get('command').get(command).get('details').get('code'), 0)
        self.assertEqual(body.get('message').get('command').get(command).get('details').get('out'), "")
        self.assertNotEqual(body.get('message').get('command').get(command).get('details').get('err'), "")
        self.assertGreater(body.get('message').get('command').get(command).get('details').get('pid'), 0)
        self.assertIsInstance(body.get('message').get('command').get(command).get('details').get('args'), list)
        self.assertIsNotNone(body.get('time'))

    def test_executecommand_p(self):
        command = "cat /etc/hostname"

        response = requests.post(
            self.server + f"/executecommand",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertEqual(body.get('message').get('command').get(command).get('details').get('code'), 0)
        self.assertNotEqual(body.get('message').get('command').get(command).get('details').get('out'), "")
        self.assertEqual(body.get('message').get('command').get(command).get('details').get('err'), "")
        self.assertGreater(body.get('message').get('command').get(command).get('details').get('pid'), 0)
        self.assertIsInstance(body.get('message').get('command').get(command).get('details').get('args'), list)
        self.assertIsNotNone(body.get('time'))

    def test_executecommand_rm_not_allowed_n(self):
        command = "rm -rf /tmp"

        response = requests.post(
            self.server + f"/executecommand",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.EXEC_COMMAND_NOT_ALLOWED) % command)
        self.assertEqual(body.get('message'),
                         ErrorCodes.HTTP_CODE.get(Constants.EXEC_COMMAND_NOT_ALLOWED) % command)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.EXEC_COMMAND_NOT_ALLOWED)
        self.assertIsNotNone(body.get('time'))

    def test_executecommand_timeout_from_client_n(self):
        command = "sleep 20"

        try:
            response = requests.post(
                self.server + f"/executecommand",
                data=command, timeout=2)
        except Exception as e:
            self.assertIsInstance(e, requests.exceptions.ReadTimeout)


if __name__ == '__main__':
    unittest.main()
