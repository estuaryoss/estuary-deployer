import time
import unittest

import requests
from parameterized import parameterized

from rest.api.constants.env_constants import EnvConstants
from rest.api.schedulers.docker_env_expire_scheduler import DockerEnvExpireScheduler


class EnvExpireSchedulerTestCase(unittest.TestCase):
    server = "http://localhost:8080/docker"

    def setUp(self):
        self.path = f"{EnvConstants.DEPLOY_PATH}"
        self.env_expire_scheduler = DockerEnvExpireScheduler(path=self.path, poll_interval=10, env_expire_in=1)

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_env_clean_up(self, template, variables):
        response = requests.post(self.server + f"/deployments/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        time.sleep(5)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 1)
        self.env_expire_scheduler.start()
        time.sleep(80)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 0)

    def tearDown(self):
        self.env_expire_scheduler.stop()


if __name__ == '__main__':
    unittest.main()
