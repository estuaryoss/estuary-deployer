#!/usr/bin/env python3
import os
import time
import unittest
import zipfile

import requests
import yaml
from flask import json
from parameterized import parameterized
from requests_toolbelt.utils import dump

from tests.rest_testrunner_integration.constants import Constants
from tests.rest_testrunner_integration.error_codes import ErrorCodes
from tests.rest_testrunner_integration.utils import Utils


class FlaskServerTestCase(unittest.TestCase):
    server = "http://localhost:8080"
    # server = "http://" + os.environ.get('SERVER')

    expected_version = "1.0.0"
    cleanup_count_safe = 5
    compose_id = ""

    @classmethod
    def setUpClass(cls):
        with open("tests/rest_testrunner_integration/input/alpinetestrunner.yml", closefd=True) as f:
            payload = f.read()

        headers = {'Content-type': 'text/plain'}
        response = requests.post(f"{FlaskServerTestCase.server}/deploystart", data=payload, headers=headers)
        # print(dump.dump_all(response))
        time.sleep(60)  # wait until the env is up and running, including image download and container boot
        compose_id = cls.get_deployment_info()[0]
        print("Docker compose env_id: " + compose_id)
        response = requests.get(f"{FlaskServerTestCase.server}/testrunnernetconnect/{compose_id}")
        # print(dump.dump_all(response))
        print("Docker net connect response: " + json.dumps(response.json()))

    def setUp(self):
        self.compose_id = self.get_deployment_info()[0]
        for i in range(0, self.cleanup_count_safe):
            requests.get(self.server + f"/testrunner/{self.compose_id}" + "/teststop")

    @staticmethod
    def get_deployment_info():
        active_deployments = []
        response = requests.get(f"{FlaskServerTestCase.server}/getdeploymentinfo")
        # print(dump.dump_all(response))
        body = response.json()
        active_deployments_objects = body.get('message')
        for item in active_deployments_objects:
            active_deployments.append(item.get('id'))

        return active_deployments

    def test_env_endpoint(self):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/env")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 7)
        self.assertIsNotNone(body.get('message')["VARS_DIR"])
        self.assertIsNotNone(body.get('message')["TEMPLATES_DIR"])
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_ping_endpoint(self):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/ping")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), "pong")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_getenv_endpoint_p(self):
        env_var = "VARS_DIR"
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/getenv/{env_var}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertIsNotNone(body.get('message'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_getenv_endpoint_n(self):
        env_var = "alabalaportocala"
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/getenv/{env_var}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_ENV_VAR_FAILURE) % env_var.upper())
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_ENV_VAR_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_about_endpoint(self):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/about")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), "estuary-testrunner")
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @unittest.skipIf(os.environ.get('TEMPLATES_DIR'),
                     "inputs/templates")  # when service runs on VM only this is skipped
    def test_swagger_endpoint(self):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/api/docs")

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body.find("html") >= 0)

    def test_swagger_yml_endpoint(self):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/swagger/swagger.yml")

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 200)
        # self.assertTrue(len(body.get('paths')) == 14)

    @parameterized.expand([
        ("json.j2", "json.json"),
        ("yml.j2", "yml.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/rend/{template}/{variables}",
                                Loader=yaml.Loader)

        body = yaml.load(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body), 3)

    @parameterized.expand([
        ("json.j2", "doesnotexists.json"),
        ("yml.j2", "doesnotexists.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        # expected = f"Exception([Errno 2] No such file or directory: \'/variables/{variables}\')"
        expected = f"Exception([Errno 2] No such file or directory:"

        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/rend/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        # self.assertEqual(expected, body.get("message"))
        self.assertIn(expected, body.get("message"))

    @parameterized.expand([
        ("doesnotexists.j2", "json.json"),
        ("doesnotexists.j2", "yml.yml")
    ])
    def test_rend_endpoint(self, template, variables):
        expected = f"Exception({template})"

        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/rend/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(expected, body.get("message"))

    @parameterized.expand([
        ("standalone.yml", "variables.yml")
    ])
    def test_rendwithenv_endpoint(self, template, variables):
        payload = {'DATABASE': 'mysql56', 'IMAGE': 'latest'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/rendwithenv/{template}/{variables}",
            data=json.dumps(payload),
            headers=headers)

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get("services")), 2)
        self.assertEqual(int(body.get("version")), 3)

    def test_getresultsfile_p(self):
        payload = {"file": "/etc/hostname"}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfile",
                                 data=json.dumps(payload),
                                 headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.text), 0)

    def test_getresultsfile_n(self):
        payload = {"file": "/etc/dummy"}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfile",
                                 data=json.dumps(payload),
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_ESTUARY_TESTRUNNER_FILE_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_ESTUARY_TESTRUNNER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_getcontainerfolder_file_param_missing_n(self):
        container_file = "/etc/dummy"
        payload = {'dummy': container_file}
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfile",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MISSING_PARAMETER_POST)
        self.assertIsNotNone(body.get('time'))

    def test_getcontainerfolder_p(self):
        container_folder = "/tmp"
        utils = Utils()
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfolder",
            data=json.dumps(payload), headers=headers)

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(body) > 0)
        utils.write_to_file("./response.zip", response.content)
        self.assertTrue(zipfile.is_zipfile("response.zip"))
        with zipfile.ZipFile('response.zip', 'w') as responsezip:
            self.assertTrue(responsezip.testzip() is None)

    def test_getcontainerfolder_n(self):
        container_folder = "/etc/hostname"
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfolder",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.FOLDER_ZIP_FAILURE) % container_folder)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.FOLDER_ZIP_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_getcontainerfolder_folder_not_found_n(self):
        container_folder = "/dummy"
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfolder",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_ESTUARY_TESTRUNNER_FILE_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_ESTUARY_TESTRUNNER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_getcontainerfolder_folder_param_missing_n(self):
        container_folder = "/dummy"
        payload = {'dummy': container_folder}
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/getresultsfolder",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "folder")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MISSING_PARAMETER_POST)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "sleep 1 \n sleep 2 \n sleep 3", "mvn -h", "alabalaportocala"
    ])
    def test_teststart_p(self, payload):
        test_id = "106"
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=payload, headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('message'), test_id)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "", "  "
    ])
    def test_teststart_missing_payload_n(self, payload):
        test_id = "105"
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=payload, headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.EMPTY_REQUEST_BODY_PROVIDED))
        self.assertEqual(body.get('message'),
                         ErrorCodes.HTTP_CODE.get(Constants.EMPTY_REQUEST_BODY_PROVIDED))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.EMPTY_REQUEST_BODY_PROVIDED)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "3"
    ])
    def test_gettestid_p(self, payload):
        test_id = "104"
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=f"sleep {payload}", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)

        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestid")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)
        time.sleep(int(payload) + 2)
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestid")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)

    def test_gettestid_no_test_running_p(self):
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestid")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), "none")
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "4"
    ])
    def test_gettestinfo_p(self, payload):
        test_id = "103"
        data_payload = f" sleep {payload} \n invalid_command"
        commands = list(map(lambda x: x.strip(), data_payload.split("\n")))
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=f"{data_payload}", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)

        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestinfo")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message').get('id'), test_id)
        self.assertEqual(body.get('message').get('started'), "true")
        self.assertEqual(body.get('message').get('finished'), "false")
        for value in commands:
            self.assertEqual(body.get('message').get("commands").get(value).get("status"), "scheduled")
            self.assertEqual(body.get('message').get("commands").get(value).get("error"), "")
        time.sleep(int(payload) - 2)
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestinfo")
        body = response.json()
        self.assertEqual(body.get('message').get("commands").get(commands[0]).get("status"), "in progress")
        self.assertEqual(body.get('message').get("commands").get(commands[0]).get("error"), "")
        time.sleep(int(payload) + 2)
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestinfo")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message').get('id'), test_id)
        self.assertEqual(body.get('message').get('started'), "false")
        self.assertEqual(body.get('message').get('finished'), "true")
        self.assertGreaterEqual(len(body.get('message').get('processes')), 2)
        self.assertEqual(body.get('message').get("commands").get(commands[0]).get("status"), "finished")
        self.assertEqual(body.get('message').get("commands").get(commands[0]).get("error"), "")
        self.assertEqual(body.get('message').get("commands").get(commands[1]).get("status"), "finished")
        self.assertIn("invalid_command: not found\n", body.get('message').get("commands").get(commands[1]).get("error"))

    @parameterized.expand([
        "3"
    ])
    def test_gettestinfo_repeated_should_return_always_200_p(self, payload):
        test_id = "102"
        data_payload = f"sleep {payload} \n sleep {payload}"
        repetitions = 100
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=f"{data_payload}", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)
        start = time.time()
        for i in range(1, repetitions):
            response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestinfo")
            self.assertEqual(response.status_code, 200)
        end = time.time()
        print(f"made {repetitions} gettestinfo repetitions in {end - start} s")

    def test_gettestinfo_rm_commands_200_p(self):
        test_id = "101"
        data_payload = f"rm -rf /etc \n ls -lrt \n colrm doesnotmatter"
        commands = list(map(lambda x: x.strip(), data_payload.split("\n")))
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=f"{data_payload}", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)
        time.sleep(1)
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + f"/gettestinfo")
        body = response.json()
        self.assertEqual(len(body.get('message').get("commands")), len(commands) - 1)
        self.assertEqual(body.get('message').get("commands").get(commands[1]).get("status"), "finished")
        self.assertEqual(body.get('message').get("commands").get(commands[1]).get("error"), "")
        self.assertEqual(body.get('message').get("commands").get(commands[2]).get("status"), "finished")

    def test_teststop_p(self):
        test_id = "100"
        data_payload = f"sleep 7 \n sleep 3600 \n sleep 3601"
        commands = list(map(lambda x: x.strip(), data_payload.split("\n")))
        headers = {'Content-type': 'text/plain'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/teststart/{test_id}",
            data=f"{data_payload}", headers=headers)
        print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), test_id)
        time.sleep(2)
        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/gettestinfo")
        body = response.json()
        self.assertEqual(body.get('message').get("id"), f"{test_id}")
        self.assertEqual(body.get('message').get("started"), "true")
        self.assertEqual(body.get('message').get("finished"), "false")
        self.assertEqual(body.get('message').get("commands").get(commands[0]).get("status"), "in progress")
        self.assertEqual(body.get('message').get("commands").get(commands[1]).get("status"), "scheduled")
        self.assertEqual(body.get('message').get("commands").get(commands[2]).get("status"), "scheduled")
        # for every command sent initially send a stop request
        for i in range(0, len(commands)):
            response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/teststop")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body.get('message'), test_id)

        response = requests.get(self.server + f"/testrunner/{self.compose_id}" + "/gettestinfo")
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        # self.assertEqual(body.get('message').get("finished"), "true")
        self.assertEqual(body.get('message').get("id"), f"{test_id}")
        # self.assertEqual(body.get('message').get("started"), "false")

    @parameterized.expand([
        "{\"file\": \"/tmp/config.properties\"}",
        "{\"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}",
        "{\"file\": \"/dummy/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadtestconfig_n(self, payload):
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/uploadtestconfig",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.UPLOAD_TEST_CONFIG_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.UPLOAD_TEST_CONFIG_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        "{\"file\": \"/tmp/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadtestconfig_p(self, payload):
        headers = {'Content-type': 'application/json'}

        response = requests.post(
            self.server + f"/testrunner/{self.compose_id}" + f"/uploadtestconfig",
            data=payload, headers=headers)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

if __name__ == '__main__':
    unittest.main()
