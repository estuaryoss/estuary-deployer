#!/usr/bin/env python3
import time
import unittest

from parameterized import parameterized
import requests

from tests.rest_kubectl.constants import Constants
from tests.rest_kubectl.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    home = "http://localhost:8080/kubectl"

    expected_version = "4.0.0"
    sleep_before_deployment_down = 5
    # input_deployment_path ="tests/rest_kubectl/input"
    input_deployment_path = "input"

    @classmethod
    def setUpClass(cls):
        with open(f"{cls.input_deployment_path}/config.yml", closefd=True) as f:
            payload = f.read()

        headers = {'Content-Type': 'text/plain',
                   'File-Path': "/root/.kube/config"}
        response = requests.post(f"{FlaskServerTestCase.home}/uploadfile", data=payload, headers=headers)
        # here i upload the kubectl config

        with open("input/k8snamespace.json", closefd=True) as f:
            payload = f.read()

        response = requests.post(f"{FlaskServerTestCase.home}/deploystart", data=payload, headers=headers)
        # here i deploy production namespace

    def setUp(self):
        headers = {}
        active_deployments = self.get_deployment_info()
        for deployment in active_deployments:
            headers["K8s-Namespace"] = deployment.get('namespace')
            requests.get(self.home + f"/deploystop/{deployment.get('name')}",
                         headers=headers)
        time.sleep(self.sleep_before_deployment_down)

    def test_deploy_start_p(self):
        with open(f"{self.input_deployment_path}/k8sdeployment_alpine_up.yml", closefd=True) as f:
            payload = f.read()

        response = requests.post(f"{self.home}/deploystart", data=payload)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_n(self):
        payload = "whatever invalid dummy yml k8s"

        response = requests.post(f"{self.home}/deploystart", data=payload)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_env_p(self):
        response = requests.post(f"{self.home}/deploystartenv/k8sdeployment_alpine_up.yml/variables.yml")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("whatever.yml", "variables.yml"),
        ("k8sdeployment_alpine_up.yml", "whatever.yml"),
        ("alpine.yml", "variables.yml"),
    ])
    def test_deploy_start_env_n(self, template, variables):
        response = requests.post(f"{self.home}/deploystartenv/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_from_server_p(self):
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_up.yml/variables.yml")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    @parameterized.expand([
        ("whatever.yml", "variables.yml"),
        ("k8sdeployment_alpine_up.yml", "whatever.yml"),
        ("alpine.yml", "variables.yml"),
    ])
    def test_deploy_start_from_server_n(self, template, variables):
        response = requests.get(f"{self.home}/deploystart/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_status_no_deployment_with_this_name_p(self):
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploystatus/dummy")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 0)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_status_p(self):
        deployment = "alpine"
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploystatus/{deployment}")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 1)
        self.assertEqual(body.get('message')[0].get('name'), deployment)
        self.assertEqual(body.get('message')[0].get('namespace'), "default")
        self.assertIn(deployment, body.get('message')[0].get('deployment'))
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_logs_default_namespace_p(self):
        deployment = "alpine"
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploylogs/{deployment}")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn(deployment, body.get('message'))
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_logs_production_namespace_p(self):
        deployment = "alpine"
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_prod_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploylogs/{deployment}")
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIn(deployment, body.get('message'))
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_logs_no_deployment_with_this_name_n(self):
        deployment = "whateverinvalid"
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_prod_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploylogs/{deployment}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('message'),
                         ErrorCodes.HTTP_CODE.get(Constants.GET_LOGS_FAILED) % deployment)
        self.assertGreater(body.get('description').get('code'), 0)
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.GET_LOGS_FAILED)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_stop_default_namespace_p(self):
        deployment = "alpine"
        headers = {'K8s-Namespace': 'default'}
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploystop/{deployment}", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 0)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_stop_production_namespace_p(self):
        deployment = "alpine"
        headers = {'K8s-Namespace': 'production'}
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_prod_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploystop/{deployment}", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 0)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_stop_no_deployment_with_this_name_n(self):
        deployment = "whateverinvalid"
        headers = {'K8s-Namespace': 'default'}
        response = requests.get(f"{self.home}/deploystart/k8sdeployment_alpine_prod_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.get(f"{self.home}/deploystop/{deployment}", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertIn(deployment, body.get('message'))
        self.assertIn(deployment, body.get('description'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.KUBERNETES_SERVER_ERROR)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_using_execute_command_p(self):
        payload = "kubectl apply -f /data/k8sdeployment_alpine_prod_up.yml --insecure-skip-tls-verify"

        response = requests.post(f"{self.home}/executecommand", data=payload)
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message').get('command').get(payload).get('details').get('code'), 0)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertIsNotNone(body.get('time'))
        self.assertEqual(len(self.get_deployment_info()), 1)

    def test_deploy_start_using_execute_command_no_certificate_n(self):
        payload = "kubectl apply -f /data/k8sdeployment_alpine_prod_up.yml"

        response = requests.post(f"{self.home}/executecommand", data=payload)
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertGreater(body.get('message').get('command').get(payload).get('details').get('code'), 0)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertIsNotNone(body.get('time'))
        self.assertEqual(len(self.get_deployment_info()), 0)

    @staticmethod
    def get_deployment_info():
        response = requests.get(f"{FlaskServerTestCase.home}/getdeploymentinfo")
        return response.json().get('message')


if __name__ == '__main__':
    unittest.main()
