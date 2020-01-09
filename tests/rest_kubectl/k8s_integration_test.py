#!/usr/bin/env python3
import time
import unittest

import requests
from parameterized import parameterized

from tests.rest_kubectl.constants import Constants
from tests.rest_kubectl.error_codes import ErrorCodes


class FlaskServerTestCase(unittest.TestCase):
    home = "http://localhost:8080/kubectl"

    expected_version = "4.0.1"
    inputs_deployment_path = "tests/rest_kubectl/inputs"
    # inputs_deployment_path = "inputs"
    templates_deployment_path = "inputs/templates" #os.environ.get('TEMPLATES_DIR'))
    sleep_after_deploy_start = 10

    @classmethod
    def setUpClass(cls):
        k8s_context = "kind-kind"
        # with open(f"{cls.inputs_deployment_path}/config.yml", closefd=True) as f:
        #     payload = f.read()
        #
        # headers = {'Content-Type': 'text/plain',
        #            'File-Path': "/root/.kube/config"}
        # here i upload the kubectl config
        # requests.post(f"{FlaskServerTestCase.home}/uploadfile", data=payload, headers=headers)
        # here i use context kind-kind
        requests.post(f"{FlaskServerTestCase.home}/command", data=f"kubectl config use-context {k8s_context}")

        with open(f"{cls.inputs_deployment_path}/k8snamespace.json", closefd=True) as f:
            payload = f.read()

        # here i deploy production namespace
        requests.post(f"{FlaskServerTestCase.home}/deployments", data=payload)
        requests.post(f"{cls.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
        time.sleep(60)

    def setUp(self):
        headers = {}
        active_deployments = self.get_deployment_info("k8s-app=alpine", "default")
        for deployment in active_deployments:
            headers["K8s-Namespace"] = deployment.get('namespace')
            requests.delete(self.home + f"/deployments/{deployment.get('name')}",
                         headers=headers)
        active_deployments = self.get_deployment_info("k8s-app=alpine", "production")
        for deployment in active_deployments:
            headers["K8s-Namespace"] = deployment.get('namespace')
            requests.delete(self.home + f"/deployments/{deployment.get('name')}",
                         headers=headers)

    def test_deploy_start_p(self):
        with open(f"{self.inputs_deployment_path}/k8sdeployment_alpine_up.yml", closefd=True) as f:
            payload = f.read()

        response = requests.post(f"{self.home}/deployments", data=payload)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_n(self):
        payload = "whatever invalid dummy yml k8s"

        response = requests.post(f"{self.home}/deployments", data=payload)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_env_p(self):
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
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
        response = requests.post(f"{self.home}/deployments/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_from_server_p(self):
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
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
        response = requests.post(f"{self.home}/deployments/{template}/{variables}")
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.DEPLOY_START_FAILURE))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.DEPLOY_START_FAILURE)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_status_no_deployment_with_this_name_p(self):
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        headers = {
            "K8s-namespace": "default",
            "Label-Selector": "k8s-app=alpine"
        }
        response = requests.get(f"{self.home}/deployments/dummy", headers=headers)
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
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        headers = {
            "K8s-namespace": "default",
            "Label-Selector": "k8s-app=alpine"
        }
        response = requests.get(f"{self.home}/deployments/{deployment}", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        # self.assertEqual(len(body.get('message')), 1)
        self.assertIn(deployment, body.get('message')[0].get('name'))
        self.assertEqual(body.get('message')[0].get('namespace'), "default")
        self.assertIn(deployment, body.get('message')[0].get('pod'))
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_logs_default_namespace_p(self):
        deployment = "alpine"
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        time.sleep(self.sleep_after_deploy_start)
        message = self.get_deployment_info("k8s-app=alpine", "default")
        response = requests.get(f"{self.home}/deployments/logs/{message[0].get('name')}",
                                headers={"K8s-Namespace": "default"})
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
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_prod_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        time.sleep(self.sleep_after_deploy_start)
        message = self.get_deployment_info("k8s-app=alpine", "production")
        response = requests.get(f"{self.home}/deployments/logs/{message[0].get('name')}",
                                headers={"K8s-Namespace": "production"})
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
        headers = {"K8s-namespace": "default"}
        response = requests.get(f"{self.home}/deployments/logs/{deployment}", headers=headers)
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
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        time.sleep(self.sleep_after_deploy_start)
        response = requests.delete(f"{self.home}/deployments/{deployment}", headers=headers)
        body = response.json()
        time.sleep(self.sleep_after_deploy_start)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(body.get('message')), 0)
        self.assertEqual(body.get('description'),
                         ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.SUCCESS)
        self.assertIsNotNone(body.get('time'))
        headers = {'K8s-Namespace': 'default', "Label-Selector": "k8s-app=alpine"}
        response = requests.get(f"{self.home}/deployments", headers=headers)
        self.assertIn("Terminating", response.json().get('message')[0].get('pod'))

    def test_deploy_stop_production_namespace_p(self):
        deployment = "alpine"
        headers = {'K8s-Namespace': 'production'}
        response = requests.post(f"{self.home}/deployments/k8sdeployment_alpine_prod_up.yml/variables.yml")
        self.assertEqual(response.status_code, 200)
        response = requests.delete(f"{self.home}/deployments/{deployment}", headers=headers)
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
        response = requests.delete(f"{self.home}/deployments/{deployment}", headers=headers)
        body = response.json()
        self.assertEqual(response.status_code, 404)
        self.assertIn(deployment, body.get('message'))
        self.assertIn(deployment, body.get('description'))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertEqual(body.get('code'), Constants.KUBERNETES_SERVER_ERROR)
        self.assertIsNotNone(body.get('time'))

    def test_deploy_start_using_execute_command_p(self):
        payload = f"kubectl apply -f {self.templates_deployment_path}/k8sdeployment_alpine_prod_up.yml --insecure-skip-tls-verify"

        response = requests.post(f"{self.home}/command", data=payload)
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.get('message').get('command').get(payload).get('details').get('code'), 0)
        self.assertEqual(body.get('description'), ErrorCodes.HTTP_CODE.get(Constants.SUCCESS))
        self.assertEqual(body.get('version'), self.expected_version)
        self.assertIsNotNone(body.get('time'))

    @staticmethod
    def get_deployment_info(label_selector, namespace):
        headers = {
            "K8s-namespace": f"{namespace}",
            "Label-Selector": f"{label_selector}"

        }
        response = requests.get(f"{FlaskServerTestCase.home}/deployments", headers=headers)
        return response.json().get('message')


if __name__ == '__main__':
    unittest.main()
