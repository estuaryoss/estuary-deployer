import time
import unittest

import requests
from parameterized import parameterized


class EnvExpireSchedulerTestCase(unittest.TestCase):
    server = "http://localhost:8081/docker"
    time_deployment_up = 5

    @parameterized.expand([
        ("alpine.yml", "variables.yml")
    ])
    def test_env_clean_up(self, template, variables):
        response = requests.post(self.server + f"/deployments/{template}/{variables}")
        self.assertEqual(response.status_code, 200)
        time.sleep(self.time_deployment_up)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 1)
        time.sleep(80)
        response = requests.get(self.server + "/deployments")
        self.assertEqual(len(response.json().get('description')), 0)


if __name__ == '__main__':
    unittest.main()
