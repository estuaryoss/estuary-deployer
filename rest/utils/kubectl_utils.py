import errno
import os
import re
from pathlib import Path

from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployments
from rest.utils.cmd_utils import CmdUtils
from rest.utils.env_creation import EnvCreation


class KubectlUtils(EnvCreation):

    @staticmethod
    def up(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["kubectl", "apply", "-f", f"{file}", "--insecure-skip-tls-verify"])

    @staticmethod
    def down(deployment, namespace):
        return CmdUtils.run_cmd(
            ["kubectl", "-n", f"{namespace}", "delete", "deployment", f"{deployment}", "--insecure-skip-tls-verify"])

    @staticmethod
    def logs(deployment, namespace):
        return CmdUtils.run_cmd(
            ["kubectl", "-n", f"{namespace}", "logs", f"{deployment}", "--insecure-skip-tls-verify"])

    @staticmethod
    def get_active_deployments():
        active_deployments = []
        status = CmdUtils.run_cmd(["kubectl", "get", "deployments", "--all-namespaces", "--insecure-skip-tls-verify"])
        active_deployments_list = status.get('out').split('\n')[1:-1]
        for i in range(0, len(active_deployments_list)):
            active_deployments_list[i] = ' '.join(active_deployments_list[i].split())
            active_deployments.append(ActiveDeployments.k8s_deployment(f'{active_deployments_list[i].split()[0]}',
                                                                       f'{active_deployments_list[i].split()[1]}',
                                                                       active_deployments_list[i]))
        return active_deployments

    @staticmethod
    def get_active_deployment(deployment):
        active_deployments = []
        active_deployments_list = KubectlUtils.get_active_deployments()
        for i in range(0, len(active_deployments_list)):
            if deployment in active_deployments_list[i].get('deployment'):
                active_deployments.append(active_deployments_list[i])

        return active_deployments

    @staticmethod
    def env_clean_up(fluentd_utils, env_expire_in=1440):  # 1 day
        fluentd_tag = "env_clean_up"
        env_expire_in_hours = env_expire_in / 60
        active_deployments = KubectlUtils.get_active_deployments()
        for item in active_deployments:
            up_time = item.get('deployment').split()[-1]
            pattern = r'^((\d+)h)$'
            match = re.search(pattern, up_time)
            if match.group(2):
                hours_uptime = int(match.group(2))
                if hours_uptime >= env_expire_in_hours:
                    result = KubectlUtils.down(item.get('name'), item.get('namespace'))
                    fluentd_utils.emit(fluentd_tag, {
                        "msg": {"action": "k8s_env_clean_up", "out": result.get('out'), "err": result.get('err')}})
