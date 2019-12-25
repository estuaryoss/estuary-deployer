import errno
import os
import re
from pathlib import Path

from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployment
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.utils.cmd_utils import CmdUtils
from rest.utils.env_creation import EnvCreation


class KubectlUtils(EnvCreation):

    @staticmethod
    def up(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["kubectl", "apply", "-f", file, "--insecure-skip-tls-verify"])

    @staticmethod
    def down(deployment, namespace):
        return CmdUtils.run_cmd(
            ["kubectl", "-n", namespace, "delete", "deployment", deployment, "--insecure-skip-tls-verify"])

    @staticmethod
    def logs(pod, namespace):
        return CmdUtils.run_cmd(
            ["kubectl", "-n", namespace, "logs", pod, "--insecure-skip-tls-verify"])

    @staticmethod
    def get_active_pods(label_selector, namespace):
        active_pods = []
        status = CmdUtils.run_cmd(
            ["kubectl", "get", "pods", "-n", namespace, "-l", label_selector, "--insecure-skip-tls-verify"])
        active_pods_list = status.get('out').split('\n')[1:-1]
        for i in range(0, len(active_pods_list)):
            active_pods_list[i] = ' '.join(active_pods_list[i].split())
            active_pods.append(ActiveDeployment.k8s_pod(f'{namespace}',
                                                        f'{active_pods_list[i].split()[0]}',
                                                        active_pods_list[i]))
        return active_pods

    @staticmethod
    def get_active_deployments():
        active_deployments = []
        status = CmdUtils.run_cmd(["kubectl", "get", "deployments", "--all-namespaces", "--insecure-skip-tls-verify"])
        active_deployments_list = status.get('out').split('\n')[1:-1]
        for i in range(0, len(active_deployments_list)):
            active_deployments_list[i] = ' '.join(active_deployments_list[i].split())
            active_deployments.append(ActiveDeployment.k8s_deployment(f'{active_deployments_list[i].split()[0]}',
                                                                      f'{active_deployments_list[i].split()[1]}',
                                                                      active_deployments_list[i]))
        return active_deployments

    @staticmethod
    def get_active_pod(pod, label_selector, namespace):
        active_pods = []
        active_pods_list = KubectlUtils.get_active_pods(label_selector, namespace)
        for i in range(0, len(active_pods_list)):
            if pod in active_pods_list[i].get('pod'):
                active_pods.append(active_pods_list[i])

        return active_pods

    @staticmethod
    def env_clean_up(fluentd_utils, env_expire_in=1440):  # 1 day
        fluentd_tag = "k8s_env_clean_up"
        message_dumper = MessageDumper()
        env_expire_in_hours = env_expire_in / 60
        active_deployments = KubectlUtils.get_active_deployments()
        for item in active_deployments:
            up_time = item.get('deployment').split()[-1]
            pattern = r'^((\d+)h)$'
            match = re.search(pattern, up_time)
            if match:
                hours_uptime = int(match.group(2))
                if hours_uptime >= env_expire_in_hours:
                    result = KubectlUtils.down(item.get('name'), item.get('namespace'))
                    fluentd_utils.debug(fluentd_tag,
                                        message_dumper.dump_message(
                                            {"action": f"{fluentd_tag}", "out": result.get('out'),
                                             "err": result.get('err')}))
