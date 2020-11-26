#!/usr/bin/env python3
import os
import time
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
    server = "{}/docker".format(server_base)
    # server = "http://" + os.environ.get('SERVER')
    input_path = f"tests/rest_docker/input"
    # input_path = "input"
    expected_version = "4.2.0"
    sleep_after_env_up = 6
    sleep_after_env_down = 6

    def setUp(self):
        active_deployments = self.get_deployment_info()
        for item in active_deployments:
            requests.delete(self.server + f"/deployments/{item}")
        time.sleep(self.sleep_after_env_down)

    def get_deployment_info(self):
        response = requests.get(self.server + "/deployments")
        body = response.json()
        active_deployments_objects = body.get('description')
        active_deployments = [item.get('id') for item in active_deployments_objects]

        return active_deployments

    def get_deployment_info_object(self):
        response = requests.get(self.server + "/deployments")

        return response.json().get('description')

    def test_env_endpoint(self):
        response = requests.get(self.server + "/env")

        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(body.get('description')), 7)
        self.assertIn("/variables", body.get('description')["VARS_DIR"])
        # self.assertIn("/data", body.get('description')["TEMPLATES_DIR"])
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("FOO1", "BAR10"),
        ("FOO2", "BAR20")
    ])
    @unittest.skipIf(str(os.environ.get('TEST_ENV')) == "centos", "Skip on Centos docker")
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
        payload = {"a": "b", "FOO1": "BAR1"}
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

        body = json.loads(response.text)
        headers = response.headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'), "pong")
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))
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
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(len(headers.get('X-Request-ID')), 16)

    @unittest.skipIf(os.environ.get('TEMPLATES_DIR') == "inputs/templates", "Skip on VM")
    @unittest.skipIf(os.environ.get('TEST_ENV') == "centos", "Skip on centos bin")
    def test_swagger_endpoint(self):
        response = requests.get(self.server_base + "/api/docs/")

        body = response.text
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body.find("html") >= 0)

    @unittest.skipIf(os.environ.get('TEMPLATES_DIR') == "inputs/templates", "Skip on VM")
    @unittest.skipIf(os.environ.get('TEST_ENV') == "centos", "Skip on centos bin")
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
    def test_rendwithenv_endpoint(self, template, variables):
        payload = {'DATABASE': 'mysql56', 'IMAGE': 'latest'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/render/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)

        body = yaml.safe_load(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get("services")), 2)
        self.assertEqual(int(body.get("version")), 3)

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_deploystartenv_payload_n(self, template, variables):
        payload = {'DATABASE': 'dummy'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deployments/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)

        body = yaml.safe_load(response.text)
        headers = response.headers
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.DEPLOY_START_FAILURE.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(len(headers.get('X-Request-ID')), 16)

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_deploystartenv_p(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deployments/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        time.sleep(self.sleep_after_env_up)
        body = response.json()
        self.assertEqual(len(self.get_deployment_info()), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("doesnotexists.yml", "variables.yml"),
        ("mysql56.yml", "doesnnotexists.yml")
    ])
    def test_deploystartenv_n(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deployments/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.DEPLOY_START_FAILURE.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart_p(self, template, variables):
        response = requests.post(self.server + f"/deployments/{template}/{variables}")
        time.sleep(self.sleep_after_env_up)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.get_deployment_info()), 1)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("doesnotexists.yml", "variables.yml"),
        ("mysql56.yml", "doesnnotexists.yml")
    ])
    def test_deploystart_n(self, template, variables):
        headers = {'Content-type': 'application/json'}

        response = requests.post(self.server + f"/deployments/{template}/{variables}", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_START_FAILURE.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.DEPLOY_START_FAILURE.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystatus_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deployments/{template}/{variables}", headers=headers)
        time.sleep(self.sleep_after_env_up)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.get_deployment_info()), 1)
        compose_id = response.json().get('description')
        response = requests.get(self.server + f"/deployments/{compose_id}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(len(body.get('description').get('containers')), 1)  # 1 container should be up and running
        self.assertEqual(body.get('description').get('id'), compose_id)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine2containers.yml", "variables.yml")
    ])
    def test_deploystatus_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deployments/{template}/{variables}", headers=headers)
        time.sleep(self.sleep_after_env_up)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        compose_id = body.get('description')
        self.assertEqual(len(self.get_deployment_info()), 1)
        response = requests.get(self.server + f"/deployments/{compose_id}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(len(body.get('description').get('containers')), 2)  # 2 containers should be up and running
        self.assertEqual(body.get('description').get('id'), compose_id)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystatus_n(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deployments/{template}/{variables}", headers=headers)
        time.sleep(self.sleep_after_env_up)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.get_deployment_info()), 1)
        deploystart_body = response.json()
        id = "dummy"

        response = requests.get(self.server + f"/deployments/{id}")
        # for dummy interogation the list of containers is empty
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(len(body.get('description').get('containers')), 0)
        self.assertEqual(body.get('description').get('id'), id)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))
        requests.delete(self.server + f"/deployments/{deploystart_body.get('description')}")

    def test_getfile_p(self):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/etc/hostname'
        }

        response = requests.get(self.server + f"/file", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.text), 0)

    def test_getfile_n(self):
        headers = {
            'Content-type': 'application/json',
            'File-Path': '/ec/dummy'
        }

        response = requests.get(self.server + f"/file", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.GET_FILE_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.GET_FILE_FAILURE)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    def test_getfile_missing_param_n(self):
        header_key = 'File-Path'
        headers = {'Content-type': 'application/json'}

        response = requests.get(self.server + f"/file", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.HTTP_HEADER_NOT_PROVIDED.value) % header_key)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.HTTP_HEADER_NOT_PROVIDED.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    def test_deploystop_n(self):
        headers = {'Content-type': 'application/json'}

        response = requests.delete(self.server + f"/deployments/dummy", headers=headers)

        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'), ErrorMessage.HTTP_CODE.get(ApiCode.DEPLOY_STOP_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.DEPLOY_STOP_FAILURE)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystop_p(self, template, variables):
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deployments/{template}/{variables}", headers=headers)
        time.sleep(self.sleep_after_env_up)
        self.assertEqual(response.status_code, 200)
        deploystart_body = response.json()

        response = requests.delete(self.server + f"/deployments/{deploystart_body.get('description')}")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(len(body.get('description')), 0)  # 0 containers should be up and running
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    def test_deploy_start_file_from_client_p(self):
        with open(f"{self.input_path}/alpine.yml", closefd=True) as f:
            payload = f.read()
        headers = {'Content-type': 'text/plain'}

        response = requests.post(self.server + f"/deployments", data=payload,
                                 headers=headers)
        time.sleep(self.sleep_after_env_up)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.get_deployment_info()), 1)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    def test_deploy_start_file_from_client_n(self):
        payload = "dummy_yml_will_not_work \n alabalaportocala"
        headers = {'Content-type': 'text/plain'}
        # it will respond with 200 because it is async now. However later checks can reveal that no containers are up for this env_id
        response = requests.post(self.server + f"/deployments", data=payload,
                                 headers=headers)
        body = response.json()
        env_id = body.get('description')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))
        active_deployments = self.get_deployment_info()
        self.assertTrue(env_id not in active_deployments)

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_get_logs_p(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deployments/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        time.sleep(self.sleep_after_env_up)
        self.assertEqual(response.status_code, 200)
        env_id = response.json().get("description")

        response = requests.get(self.server + f"/deployments/logs/{env_id}")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.SUCCESS.value))
        self.assertGreater(len(body.get("description")), 15)  # at least 15
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("mysql56.yml", "variables.yml")
    ])
    def test_get_logs_id_not_found_n(self, template, variables):
        payload = {'DATABASE': 'mysql56'}
        headers = {'Content-type': 'application/json'}
        response = requests.post(self.server + f"/deployments/{template}/{variables}", data=json.dumps(payload),
                                 headers=headers)
        self.assertEqual(response.status_code, 200)
        dummy_env_id = response.json().get("message") + "dummy"

        response = requests.get(self.server + f"/deployments/logs/{dummy_env_id}")
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.GET_LOGS_FAILED) % dummy_env_id)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.GET_LOGS_FAILED)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_getdeploymentinfo_p(self, template, variables):
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 0)
        response = requests.post(self.server + f"/deployments/{template}/{variables}")
        time.sleep(self.sleep_after_env_up)
        compose_id = response.json().get('description')
        self.assertEqual(response.status_code, 200)

        response = requests.get(self.server + "/deployments")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().get('description')), 1)
        self.assertEqual(response.json().get('description')[0].get('id'), compose_id)
        self.assertEqual(len(response.json().get('description')[0].get('containers')), 1)

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystart_max_deployments_p(self, template, variables):
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 0)
        for i in range(0, int(os.environ.get('MAX_DEPLOYMENTS'))):
            response = requests.post(self.server + f"/deployments/{template}/{variables}")
            time.sleep(self.sleep_after_env_up)
            self.assertEqual(response.status_code, 200)
        time.sleep(3)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), int(os.environ.get('MAX_DEPLOYMENTS')))

        response = requests.post(self.server + f"/deployments/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                             'MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.MAX_DEPLOYMENTS_REACHED)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_deploystartenv_max_deployments_p(self, template, variables):
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 0)
        for i in range(0, int(os.environ.get('MAX_DEPLOYMENTS'))):
            response = requests.post(self.server + f"/deployments/{template}/{variables}")
            self.assertEqual(response.status_code, 200)
            time.sleep(self.sleep_after_env_up)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), int(os.environ.get('MAX_DEPLOYMENTS')))

        response = requests.post(self.server + f"/deployments/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                             'MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.MAX_DEPLOYMENTS_REACHED)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertIsNotNone(body.get('timestamp'))

    def test_deploystartpostfromfile_max_deployments_p(self):
        with open(f"{self.input_path}/alpine.yml", closefd=True) as f:
            payload = f.read()
        headers = {'Content-type': 'text/plain'}

        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 0)
        for i in range(0, int(os.environ.get('MAX_DEPLOYMENTS'))):
            response = requests.post(self.server + f"/deployments", data=payload, headers=headers)
            time.sleep(self.sleep_after_env_up)
            self.assertEqual(response.status_code, 200)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), int(os.environ.get('MAX_DEPLOYMENTS')))

        response = requests.post(self.server + f"/deployments", data=payload, headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body.get('message'),
                         ErrorMessage.HTTP_CODE.get(ApiCode.MAX_DEPLOYMENTS_REACHED) % os.environ.get(
                             'MAX_DEPLOYMENTS'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.MAX_DEPLOYMENTS_REACHED)
        self.assertIsNotNone(body.get('timestamp'))
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
    def test_uploadfile_header_not_provided_n(self, payload):
        headers = {'Content-type': 'application/json'}
        mandatory_header_key = 'File-Path'

        response = requests.put(
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
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        ""
    ])
    def test_uploadfile_empty_body_n(self, payload):
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
        self.assertIsNotNone(body.get('timestamp'))

    @parameterized.expand([
        "{\"file\": \"/tmp/config.properties\", \"content\": \"ip=10.0.0.1\\nrequest_sec=100\\nthreads=10\\ntype=dual\"}"
    ])
    def test_uploadfile_p(self, payload):
        headers = {
            'Content-type': 'application/json',
            'File-Path': 'config.properties'
        }

        response = requests.post(
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

    def test_executecommand_rm_allowed(self):
        command = "rm -rf /tmp"

        response = requests.post(
            self.server + f"/command",
            data=command)

        body = response.json()
        print(dump.dump_all(response))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(body.get('description'), dict)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))
        self.assertEqual(body.get('path'), "/docker/command?")

    def test_executecommand_both_valid_are_executed(self):
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
        self.assertEqual(len(body.get('description').get("commands")), 2)
        self.assertEqual(body.get('description').get("commands").get(commands[1]).get('details').get('code'), 0)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), ApiCode.SUCCESS.value)
        self.assertIsNotNone(body.get('timestamp'))

    def test_executecommand_timeout_from_client_n(self):
        command = "sleep 20"

        try:
            requests.post(
                self.server + f"/command",
                data=command, timeout=2)
        except Exception as e:
            self.assertIsInstance(e, requests.exceptions.ReadTimeout)


if __name__ == '__main__':
    unittest.main()
