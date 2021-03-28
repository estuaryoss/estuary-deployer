#!/usr/bin/env python3
import os
import unittest

import requests
import yaml
from flask import json
from parameterized import parameterized
from requests_toolbelt.utils import dump

from rest.api.constants.api_code import ApiCode
from rest.api.responsehelpers.error_message import ErrorMessage


class FlaskServerTestCase(unittest.TestCase):
    server_base = "http://localhost:8080"
    server = "{}/kubectl".format(server_base)

    expected_version = "4.2.1"
    sleep_before_container_up = 5

    def test_env_endpoint(self):
        response = requests.get(self.server + "/env")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(body.get('description')), 7)
        self.assertIn("/variables", body.get('description')["VARS_DIR"])
        # self.assertEqual(body.get('message')["TEMPLATES_DIR"], "/data")
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("FOO1", "BAR10")
    ])
    def test_env_load_from_props(self, env_var, expected_value):
        response = requests.get(self.server + "/env/" + env_var)

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get("message"), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('description'), expected_value)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('path'))

    def test_setenv_endpoint_jsonwithvalues_p(self):
        payload = {"a": "b", "FOO2": "BAR1"}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + "/env", data=json.dumps(payload),
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), payload)
        self.assertEqual(body.get("message"), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('path'))

    def test_ping_endpoint(self):
        response = requests.get(self.server + "/ping")

        body = response.json()
        headers = response.headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), "pong")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(body.get('path'), "/kubectl/ping?")
        self.assertEqual(len(headers.get('X-Request-ID')), 16)

    def test_ping_endpoint_xid_set_by_client(self):
        xid = 'whatever'
        headers = {'X-Request-ID': xid}
        response = requests.get(self.server + "/ping", headers=headers)

        body = json.loads(response.text)
        headers = response.headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), "pong")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(headers.get('X-Request-ID'), xid)

    def test_about_endpoint(self):
        response = requests.get(self.server + "/about")
        name = "estuary-deployer"

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(body.get('description'), dict)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('name'), name)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_about_endpoint_unauthorized(self):
        headers = {'Token': "invalidtoken"}
        response = requests.get(self.server + "/about", headers=headers)
        service_name = "estuary-deployer"
        body = response.json()
        headers = response.headers
        self.assertEqual(response.status_code, 401)
        self.assertEqual(body.get('description'), "Invalid Token")
        self.assertEqual(body.get('name'), service_name)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.UNAUTHORIZED.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.UNAUTHORIZED.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(len(headers.get('X-Request-ID')), 16)

    @unittest.skipIf(os.environ.get('TEMPLATES_DIR') == "inputs/templates", "Skip on VM")
    def test_swagger_endpoint(self):
        response = requests.get(self.server_base + "/api/docs/")

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body.find("html") >= 0)

    @unittest.skipIf(os.environ.get('TEMPLATES_DIR') == "inputs/templates", "Skip on VM")
    def test_swagger_endpoint_swagger_still_accesible(self):
        headers = {'Token': 'whateverinvalid'}
        response = requests.get(self.server_base + "/api/docs/", headers=headers)

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body.find("html") >= 0)

    def test_swagger_yml_endpoint(self):
        response = requests.get(self.server + "/swagger/swagger.yml")

        self.assertEqual(response.status_code, 200)

    def test_swagger_yml_swagger_still_accesible(self):
        headers = {'Token': 'whateverinvalid'}
        response = requests.get(self.server + "/swagger/swagger.yml", headers=headers)

        self.assertEqual(response.status_code, 200)

    @parameterized.expand([
        ("json.j2", "json.json"),
        ("yml.j2", "yml.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        response = requests.get(self.server + f"/render/{template}/{variables}", Loader=yaml.Loader)

        body = yaml.safe_load(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body), 3)

    @parameterized.expand([
        ("json.j2", "doesnotexists.json"),
        ("yml.j2", "doesnotexists.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        expected = f"Exception([Errno 2] No such file or directory:"

        response = requests.get(self.server + f"/render/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertIn(expected, body.get("description"))

    @parameterized.expand([
        ("doesnotexists.j2", "json.json"),
        ("doesnotexists.j2", "yml.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        expected = f"Exception({template})"

        response = requests.get(self.server + f"/render/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(expected, body.get("description"))

    @parameterized.expand([
        ("standalone.yml", "variables.yml")
    ])
    @unittest.skipIf(os.environ.get('TEMPLATES_DIR') == "inputs/templates", "Skip on VM")
    def test_rendwithenv_endpoint(self, template, variables):
        payload = {'DATABASE': 'mysql56', 'IMAGE': 'latest'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/render/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)

        print(dump.dump_all(response))
        body = yaml.safe_load(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get("services")), 2)
        self.assertEqual(int(body.get("version")), 3)

    def test_getdeployerfile_p(self):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/etc/hostname'
        }

        response = requests.get(self.server + f"/file", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.text), 0)

    def test_getdeployerfile_n(self):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/etc/dummy'
        }

        response = requests.get(self.server + f"/file", headers=headers)
        body = response.json()
        headers = response.headers
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.GET_FILE_FAILURE.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.GET_FILE_FAILURE.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(len(headers.get('X-Request-ID')), 16)

    def test_getdeployerfile_missing_param_n(self):
        header_key = 'File-Path'
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/file", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.HTTP_HEADER_NOT_PROVIDED.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_getenv_endpoint_p(self):
        env_var = "VARS_DIR"
        response = requests.get(self.server + f"/env/{env_var}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertIsNotNone(body.get('description'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_getenv_endpoint_n(self):
        env_var = "alabalaportocala"
        response = requests.get(self.server + f"/env/{env_var}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('description'), None)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        "{\"file\": \"/dummy/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadfile_n(self, payload):
        headers = {'Content-type': 'application/json'}
        mandatory_header_key = 'File-Path'

        response = requests.post(
            self.server + f"/file",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % mandatory_header_key)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.HTTP_HEADER_NOT_PROVIDED.value)
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ""
    ])
    def test_uploadfile_n(self, payload):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/tmp/config.properties'
        }

        response = requests.post(
            self.server + f"/file",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.EMPTY_REQUEST_BODY_PROVIDED.value)
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        "{\"file\": \"/tmp/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadfile_p(self, payload):
        headers = {
            'Content-type': 'application/json',
            'File-Path': 'config.properties'
        }

        response = requests.put(
            self.server + f"/file",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_executecommand_n(self):
        command = "abracadabra"  # not working on linux

        response = requests.post(
            self.server + f"/command",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertNotEqual(body.get('description').get('commands').get(command).get('details').get('code'), 0)
        self.assertEqual(body.get('description').get('commands').get(command).get('details').get('out'), "")
        self.assertNotEqual(body.get('description').get('commands').get(command).get('details').get('err'), "")
        self.assertGreater(body.get('description').get('commands').get(command).get('details').get('pid'), 0)
        self.assertIsInstance(body.get('description').get('commands').get(command).get('details').get('args'), list)
        self.assertIsNotNone(body.get('timestamp'))

    def test_executecommand_p(self):
        command = "cat /etc/hostname"

        response = requests.post(
            self.server + f"/command",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertEqual(body.get('description').get('commands').get(command).get('details').get('code'), 0)
        self.assertNotEqual(body.get('description').get('commands').get(command).get('details').get('out'), "")
        self.assertEqual(body.get('description').get('commands').get(command).get('details').get('err'), "")
        self.assertGreater(body.get('description').get('commands').get(command).get('details').get('pid'), 0)
        self.assertIsInstance(body.get('description').get('commands').get(command).get('details').get('args'), list)
        self.assertIsNotNone(body.get('timestamp'))

    def test_executecommand_rm_allowed_p(self):
        command = "rm -rf /tmp"

        response = requests.post(
            self.server + f"/command",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertIsInstance(body.get('description'), dict)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_both_valid_are_executed(self):
        command = "rm -rf /tmp\nls -lrt"
        commands = command.split("\n")

        response = requests.post(
            self.server + f"/command",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(len(body.get('description').get("commands")), 2)  # only 1 cmd is executed
        self.assertEqual(body.get('description').get("commands").get(commands[1]).get('details').get('code'), 0)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_executecommand_timeout_from_client_n(self):
        command = "sleep 20"

        try:
            requests.post(self.server + f"/command", data=command, timeout=2)
        except Exception as e:
            self.assertIsInstance(e, requests.exceptions.ReadTimeout)


if __name__ == '__main__':
    unittest.main()
