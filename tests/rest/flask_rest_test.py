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

from tests.rest.constants import Constants
from tests.rest.error_codes import ErrorCodes
from tests.rest.utils import Utils


class FlaskServerTestCase(unittest.TestCase):
    # server = "http://localhost:8080"
    server = os.environ.get('SERVER')

    expected_version = "1.0.0"

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

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), "estuary-deployer-service")
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
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

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_deploystartenv_payload_n(self, template, variables):
        payload = {'DATABASE': 'dummy'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deploystartenv/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_deploystartenv_p(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deploystartenv/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{body.get('message')}")

    @parameterized.expand([
        ("doesnotexists.yml", "variables.yml"),
        ("mysql56.yml", "doesnnotexists.yml")
    ])
    def test_deploystartenv_n(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deploystartenv/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart_p(self, template, variables):
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{body.get('message')}")

    @parameterized.expand([
        ("doesnotexists.yml", "variables.yml"),
        ("mysql56.yml", "doesnnotexists.yml")
    ])
    def test_deploystart_n(self, template, variables):
        headers = {'Content-type': 'application/json'}

        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deployreplay_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        container_id = response.json().get("message");
        self.assertEqual(response.status_code, 200)
        body = response.json()
        response = requests.get(self.server + f"/deploystop/{body.get('message')}")
        self.assertEqual(response.status_code, 200)

        response = requests.get(self.server + f"/deployreplay/{container_id}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{container_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deployreplay_n(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        self.assertEqual(response.status_code, 200)
        deploystart_body = response.json()
        compose_id = deploystart_body.get('message')

        response = requests.get(self.server + f"/deployreplay/{compose_id}")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE) % compose_id)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_REPLAY_FAILURE_STILL_ACTIVE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{deploystart_body.get('message')}")

    def test_deployreplay_id_not_created_n(self):
        response = requests.get(self.server + f"/deployreplay/dummy_string")

        self.assertEqual(response.status_code, 404)

        body = response.json()
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_REPLAY_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_REPLAY_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystatus_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        self.assertEqual(response.status_code, 200)
        deploystart_body = response.json()

        response = requests.get(self.server + f"/deploystatus/{deploystart_body.get('message')}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(len(body.get('message')), 1)  # 1 container should be up and running
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{deploystart_body.get('message')}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystatus_n(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        self.assertEqual(response.status_code, 200)
        deploystart_body = response.json()

        response = requests.get(self.server + f"/deploystatus/dummy")

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STATUS_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_STATUS_FAILURE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{deploystart_body.get('message')}")

    def test_getdeployerfile_p(self):
        payload = {"file": "/etc/hostname"}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/getdeployerfile", data=json.dumps(payload),
                                 headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.text), 0)

    def test_getdeployerfile_n(self):
        payload = {"file": "/etc/dummy"}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/getdeployerfile", data=json.dumps(payload),
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_ESTUARY_DEPLOYER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_getdeployerfile_missing_param_n(self):
        payload = {}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/getdeployerfile", data=json.dumps(payload),
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MISSING_PARAMETER_POST)
        self.assertIsNotNone(body.get('time'))

    def test_deploystop_n(self):
        headers = {'Content-type': 'application/json'}

        response = requests.get(self.server + f"/deploystop/dummy", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_STOP_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_STOP_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystop_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        self.assertEqual(response.status_code, 200)
        deploystart_body = response.json()

        response = requests.get(self.server + f"/deploystop/{deploystart_body.get('message')}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(len(body.get('message')), 0)  # 0 containers should be up and running
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_file_from_client_p(self):
        with open("tests/rest/input/alpine.yml", closefd=True) as f:
            payload = f.read();
        headers = {'Content-type': 'text/plain'}

        response = requests.post(self.server + f"/deploystart", data=payload,
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{body.get('message')}")

    def test_deploy_start_file_from_client_n(self):
        payload = "dummy_yml_will_not_work\n"
        headers = {'Content-type': 'text/plain'}

        response = requests.post(self.server + f"/deploystart", data=payload,
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_teststart_get_p(self, template, variables):
        with open("tests/rest/input/start.sh", closefd=True) as f:
            payload = f.read();
        headers = {'Content-type': 'text/plain'}

        response = requests.get(self.server + f"/deploystart/{template}/{variables}")

        container_id = response.json().get("message")
        framework_container_service_name = "alpine"
        keyword_is_test_finished = "finished"
        sleep_time = 10
        self.assertEqual(response.status_code, 200)
        response = requests.post(self.server + f"/teststart/{container_id}/{framework_container_service_name}",
                                 data=payload,
                                 headers=headers)
        self.assertEqual(response.status_code, 200)
        response = requests.get(
            self.server + f"/istestfinished/{container_id}/{framework_container_service_name}/{keyword_is_test_finished}",
            headers=headers)
        body = response.json()
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('message'), False)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        time.sleep(sleep_time)
        response = requests.get(
            self.server + f"/istestfinished/{container_id}/{framework_container_service_name}/{keyword_is_test_finished}",
            headers=headers)
        body = response.json()
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('message'), True)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        time.sleep(sleep_time)
        requests.get(self.server + f"/deploystop/{container_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_istestfinished_get_n(self, template, variables):
        headers = {'Content-type': 'text/plain'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        env_id = response.json().get("message")
        framework_container_service_name = "dummy"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"
        keyword_is_test_finished = "finished"

        response = requests.get(
            self.server + f"/istestfinished/{env_id}/{framework_container_service_name}/{keyword_is_test_finished}",
            headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
            "/tmp/is_test_finished", container_id))
        self.assertEqual(body.get('message'), False)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_istestfinished_post_n(self, template, variables):
        payload = {'file': '/tmp/is_test_finished'}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "dummy"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"
        keyword_is_test_finished = "finished"

        response = requests.post(
            self.server + f"/istestfinished/{env_id}/{framework_container_service_name}/{keyword_is_test_finished}",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                             "/tmp/is_test_finished", container_id))
        self.assertEqual(body.get('message'), False)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_teststart_get__invalid_container_sn_n(self, template, variables):
        with open("tests/rest/input/start.sh", closefd=True) as f:
            payload = f.read();
        headers = {'Content-type': 'text/plain'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        env_id = response.json().get("message")
        framework_container_service_name = "dummy"
        self.assertEqual(response.status_code, 200)

        response = requests.post(self.server + f"/teststart/{env_id}/{framework_container_service_name}",
                                 data=payload,
                                 headers=headers)

        body = response.json()
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.TEST_START_FAILURE) % ("/tmp/start.sh", container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.TEST_START_FAILURE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    def test_teststart_get_invalid_env_id_n(self):
        with open("tests/rest/input/start.sh", closefd=True) as f:
            payload = f.read();
        headers = {'Content-type': 'text/plain'}
        env_id = "dummy"
        framework_container_service_name = "alpine"

        response = requests.post(self.server + f"/teststart/dummy/{framework_container_service_name}",
                                 data=payload,
                                 headers=headers)

        body = response.json()
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.TEST_START_FAILURE) % ("/tmp/start.sh", container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.TEST_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_teststart_post_p(self, template, variables):
        with open("tests/rest/input/start.sh", closefd=True) as f:
            payload = f.read();
        headers = {'Content-type': 'text/plain'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        container_id = response.json().get("message")
        framework_container_service_name = "alpine"
        keyword_is_test_finished = "finished"
        sleep_time = 10
        self.assertEqual(response.status_code, 200)

        response = requests.post(self.server + f"/teststart/{container_id}/{framework_container_service_name}",
                                 data=payload,
                                 headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = {'file': '/tmp/is_test_finished'}
        response = requests.post(
            self.server + f"/istestfinished/{container_id}/{framework_container_service_name}/{keyword_is_test_finished}",
            headers=headers, data=json.dumps(payload))
        body = response.json()
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('message'), False)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        time.sleep(sleep_time)
        response = requests.post(
            self.server + f"/istestfinished/{container_id}/{framework_container_service_name}/{keyword_is_test_finished}",
            headers=headers, data=json.dumps(payload))
        body = response.json()
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('message'), True)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        time.sleep(sleep_time)
        requests.get(self.server + f"/deploystop/{container_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_n(self, template, variables):
        container_file = "/etc/alabalaportocala"
        payload = {'file': container_file}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        self.assertEqual(response.status_code, 404)
        print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                             container_file, container_id))
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
            container_file, container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_missing_file_n(self, template, variables):
        container_file = "/etc/hostname"
        payload = {
            'file_other': container_file}  # or just no payload will return the same message: missing param in post
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        self.assertEqual(response.status_code, 404)
        print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MISSING_PARAMETER_POST)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_is_folder_n(self, template, variables):
        container_file = "/etc"
        payload = {'file': container_file}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        self.assertEqual(response.status_code, 404)
        print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                             container_file, container_id))
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
            container_file, container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_p(self, template, variables):
        container_file = "/etc/hostname"
        payload = {'file': container_file}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(body) > 0)
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfolder_n(self, template, variables):
        container_folder = "/alabalaportocala"
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfolder/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                             container_folder, container_id))
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
            container_folder, container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfolder_missing_folder_n(self, template, variables):
        container_folder = "/alabalaportocala"
        payload = {'folder_other': container_folder}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfolder/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "folder")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MISSING_PARAMETER_POST)
        self.assertIsNotNone(body.get('time'))
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_p(self, template, variables):
        container_folder = "/etc"
        utils = Utils()
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"

        response = requests.post(
            self.server + f"/getcontainerfolder/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(body) > 0)
        utils.write_to_file("./response.zip", response.content)
        self.assertTrue(zipfile.is_zipfile("response.zip"))
        with zipfile.ZipFile('response.zip', 'w') as responsezip:
            self.assertTrue(responsezip.testzip() is None)
        requests.get(self.server + f"/deploystop/{env_id}")

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_max_deploy_memory_p(self, template, variables):
        max_mem_procent = "4"
        payload = {'DATABASE': 'mysql56', 'MAX_DEPLOY_MEMORY': max_mem_procent}
        headers = {'Content-type': 'application/json'}
        env_list = []
        for i in list(range(50)):
            response = requests.post(self.server + f"/deploystartenv/{template}/{variables}", data=json.dumps(payload),
                                     headers=headers)
            if response.status_code == 200:
                env_list.append(response.json().get("message"))
            else:
                break  # here max memory is met

        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOY_MEMORY_REACHED) % max_mem_procent)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MAX_DEPLOY_MEMORY_REACHED)
        self.assertIsNotNone(body.get('time'))
        for value in env_list:
            requests.get(self.server + f"/deploystop/{value}")


if __name__ == '__main__':
    unittest.main()
