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

from tests.rest_docker.constants import Constants
from tests.rest_docker.error_codes import ErrorCodes
from tests.rest_docker.utils import Utils


class FlaskServerTestCase(unittest.TestCase):
    server = "http://localhost:8080/docker"
    # server = "http://" + os.environ.get('SERVER')

    expected_version = "3.0.0"
    sleep_before_container_up = 5

    def setUp(self):
        time.sleep(self.sleep_before_container_up)
        active_deployments = self.get_deployment_info()
        for item in active_deployments:
            requests.get(self.server + f"/deploystop/{item}")

    def get_deployment_info(self):
        active_deployments = []
        response = requests.get(self.server + "/getdeploymentinfo")
        body = response.json()
        active_deployments_objects = body.get('message')
        for item in active_deployments_objects:
            active_deployments.append(item.get('id'))

        return active_deployments

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
        time.sleep(self.sleep_before_container_up)
        body = yaml.load(response.text, Loader=yaml.Loader)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

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
        time.sleep(self.sleep_before_container_up)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

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
    def test_deploystatus_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        compose_id = response.json().get('message')
        response = requests.get(self.server + f"/deploystatus/{compose_id}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(len(body.get('message').get('containers')), 1)  # 1 container should be up and running
        self.assertEqual(body.get('message').get('id'), compose_id)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystatus_n(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}", headers=headers)
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        deploystart_body = response.json()
        id = "dummy"

        response = requests.get(self.server + f"/deploystatus/{id}")
        #for dummy interogation the list of containers is empty
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(len(body.get('message').get('containers')), 0)
        self.assertEqual(body.get('message').get('id'), id)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
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
        time.sleep(self.sleep_before_container_up)
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
        with open("tests/rest_docker/input/alpine.yml", closefd=True) as f:
            payload = f.read()
        headers = {'Content-type': 'text/plain'}

        response = requests.post(self.server + f"/deploystart", data=payload,
                                 headers=headers)
        time.sleep(self.sleep_before_container_up)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_file_from_client_n(self):
        payload = "dummy_yml_will_not_work \n alabalaportocala"
        headers = {'Content-type': 'text/plain'}
        # it will respond with 200 because it is async now. However later checks can reveal that no containers are up for this env_id
        response = requests.post(self.server + f"/deploystart", data=payload,
                                 headers=headers)
        body = response.json()
        env_id = body.get('message')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        active_deployments = self.get_deployment_info()
        self.assertTrue(env_id not in active_deployments)

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_n(self, template, variables):
        container_file = "/etc/alabalaportocala"
        payload = {'file': container_file}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        self.assertEqual(response.status_code, 404)
        # print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
                             container_file, container_id))
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE) % (
            container_file, container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_missing_file_n(self, template, variables):
        container_file = "/etc/hostname"
        payload = {
            'file_other': container_file}  # or just no payload will return the same message: missing param in post
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        self.assertEqual(response.status_code, 404)
        # print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MISSING_PARAMETER_POST) % "file")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MISSING_PARAMETER_POST)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_is_folder_n(self, template, variables):
        container_file = "/etc"
        payload = {'file': container_file}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"
        container_id = f"{env_id}" + "_" + f"{framework_container_service_name}" + "_" + "1"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        self.assertEqual(response.status_code, 404)
        # print(dump.dump_all(response))
        body = response.json()
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
                             container_file, container_id))
        self.assertEqual(body.get('message'), ErrorCodes.HTTP_CODE.get(Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR) % (
            container_file, container_id))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_CONTAINER_FILE_FAILURE_IS_DIR)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfile_p(self, template, variables):
        container_file = "/etc/hostname"
        payload = {'file': container_file}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        framework_container_service_name = "alpine"

        response = requests.post(
            self.server + f"/getcontainerfile/{env_id}/{framework_container_service_name}",
            data=json.dumps(payload), headers=headers)

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(body) > 0)

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfolder_n(self, template, variables):
        container_folder = "/alabalaportocala"
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
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

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfolder_missing_folder_n(self, template, variables):
        container_folder = "/alabalaportocala"
        payload = {'folder_other': container_folder}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
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

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getcontainerfolder_p(self, template, variables):
        container_folder = "/etc"
        utils = Utils()
        payload = {'folder': container_folder}
        headers = {'Content-type': 'application/json'}
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
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

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_get_logs_p(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deploystartenv/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        time.sleep(self.sleep_before_container_up)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")

        response = requests.get(self.server + f"/deploylogs/{env_id}")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertGreater(len(body.get("message")), 15)  # at least 15
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_get_logs_id_not_found_n(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deploystartenv/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("message")
        dummy_env_id = response.json().get("message") + "dummy"

        response = requests.get(self.server + f"/deploylogs/{dummy_env_id}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % dummy_env_id)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_LOGS_FAILED)
        self.assertIsNotNone(body.get('time'))

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

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getdeploymentinfo_p(self, template, variables):
        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), 0)
        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        time.sleep(self.sleep_before_container_up)
        compose_id = response.json().get('message')
        self.assertEqual(response.status_code, 200)

        response = requests.get(self.server + "/getdeploymentinfo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().get('message')), 1)
        self.assertEqual(response.json().get('message')[0].get('id'), compose_id)
        self.assertEqual(len(response.json().get('message')[0].get('containers')), 1)

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart_max_deployments_p(self, template, variables):
        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), 0)
        for i in range(0, int(os.environ.get('MAX_DEPLOYMENTS'))):
            response = requests.get(self.server + f"/deploystart/{template}/{variables}")
            time.sleep(self.sleep_before_container_up)
            self.assertEqual(response.status_code, 200)
        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), int(os.environ.get('MAX_DEPLOYMENTS')))

        response = requests.get(self.server + f"/deploystart/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                             'MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('stacktrace'),
                         "Active deployments: %s" % os.environ.get('MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MAX_DEPLOYMENTS_REACHED)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystartenv_max_deployments_p(self, template, variables):
        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), 0)
        for i in range(0, int(os.environ.get('MAX_DEPLOYMENTS'))):
            response = requests.post(self.server + f"/deploystartenv/{template}/{variables}")
            self.assertEqual(response.status_code, 200)
            time.sleep(self.sleep_before_container_up)
        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), int(os.environ.get('MAX_DEPLOYMENTS')))

        response = requests.post(self.server + f"/deploystartenv/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                             'MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('stacktrace'),
                         "Active deployments: %s" % os.environ.get('MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MAX_DEPLOYMENTS_REACHED)
        self.assertIsNotNone(body.get('time'))

    def test_deploystartpostfromfile_max_deployments_p(self):
        with open("tests/rest_docker/input/alpine.yml", closefd=True) as f:
            payload = f.read()
        headers = {'Content-type': 'text/plain'}

        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), 0)
        for i in range(0, int(os.environ.get('MAX_DEPLOYMENTS'))):
            response = requests.post(self.server + f"/deploystart", data=payload, headers=headers)
            time.sleep(self.sleep_before_container_up)
            self.assertEqual(response.status_code, 200)
        response = requests.get(self.server + "/getdeploymentinfo")
        self.assertEqual(len(response.json().get('message')), int(os.environ.get('MAX_DEPLOYMENTS')))

        response = requests.post(self.server + f"/deploystart", data=payload, headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                             'MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('stacktrace'),
                         "Active deployments: %s" % os.environ.get('MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.MAX_DEPLOYMENTS_REACHED)
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