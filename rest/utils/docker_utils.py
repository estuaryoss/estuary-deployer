import datetime
import errno
import os
import shutil
from pathlib import Path

from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployments
from rest.api.apiresponsehelpers.constants import Constants
from rest.utils.cmd_utils import CmdUtils
from rest.utils.io_utils import IOUtils


class DockerUtils:

    @staticmethod
    def docker_up(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "pull", "&&", "docker-compose", "-f", f"{file}", "up", "-d"])

    @staticmethod
    def docker_down(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "-f", f"{file}", "down", "-v"])

    @staticmethod
    def docker_start(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "-f", f"{file}", "start"])

    @staticmethod
    def docker_stop(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "-f", f"{file}", "stop"])

    @staticmethod
    def docker_logs(file):
        file_path = Path(f"{file}")
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(
            ["docker-compose", "-f", f"{file}", "logs", "-t", f"--tail={Constants.DOCKER_LOGS_LINES}"])

    @staticmethod
    def docker_ps(id):
        file_path = Path(Constants.DOCKER_PATH + f"{id}/{id}")
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker", "ps", "--filter", f"name={id}"])

    @staticmethod
    def docker_exec(container_id, command):
        container_exec_cmd = ["docker", "exec", f"{container_id}"]
        container_exec_cmd.extend(command)
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def docker_network_prune():
        container_exec_cmd = ["docker", "network", "prune", "-f"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def docker_network_connect(deployer_net, container):
        container_exec_cmd = ["docker", "network", "connect", f"{deployer_net}", f"{container}"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def docker_network_disconnect(deployer_net, container):
        container_exec_cmd = ["docker", "network", "disconnect", f"{deployer_net}", f"{container}"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def docker_volume_prune():
        container_exec_cmd = ["docker", "volume", "prune", "-f"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def docker_cp(compose_id, service_name, file_or_folder):
        container_id = f"{compose_id}_{service_name}_1"
        command = rf''' {container_id}:{file_or_folder} /tmp/{compose_id}'''
        container_exec_cmd = r'''docker cp ''' + command
        return CmdUtils.run_cmd_shell_true(container_exec_cmd)

    @staticmethod
    def docker_exec_detached(container_id, command):
        container_exec_cmd = ["docker", "exec", "-d", f"{container_id}"]
        container_exec_cmd.extend(command)
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def docker_stats(command):
        container_exec_cmd = r'''docker stats --no-stream ''' + command
        return CmdUtils.run_cmd_shell_true(container_exec_cmd)

    @staticmethod
    def docker_clean_up():
        DockerUtils.docker_network_prune()
        DockerUtils.docker_volume_prune()

    @staticmethod
    def get_hostname_fqdn():
        return CmdUtils.run_cmd(["hostname", "--fqdn"])

    @staticmethod
    def get_active_deployments():
        active_deployments = []
        full_deployments_list = IOUtils.get_list_dir(f"{Constants.DOCKER_PATH}")
        for item in full_deployments_list:
            try:
                container_list = DockerUtils.docker_ps(item)[0].split("\n")[1:-1]
                if len(container_list) > 0:
                    active_deployments.append(ActiveDeployments.active_deployment(item.strip(), container_list))
            except:
                pass
        return active_deployments

    @staticmethod
    def tmp_folder_clean_up():
        active_deployments = []
        active_deployments_objects = DockerUtils.get_active_deployments()
        for item in active_deployments_objects:
            active_deployments.append(item.get('id'))
        full_deployments_list = map(lambda x: x.strip(),IOUtils.get_list_dir(f"{Constants.DOCKER_PATH}"))
        for item in full_deployments_list:
            if item not in active_deployments and (datetime.datetime.now() - datetime.datetime.fromtimestamp(
                    os.path.getmtime(f"{Constants.DOCKER_PATH}{item}"))) > datetime.timedelta(hours=1):
                shutil.rmtree(f"{Constants.DOCKER_PATH}{item}")
