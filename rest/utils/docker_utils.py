import datetime
import errno
import os
import shutil
from pathlib import Path

from rest.api.apiresponsehelpers.active_deployments_response import ActiveDeployments
from rest.api.apiresponsehelpers.constants import Constants
from rest.utils.cmd_utils import CmdUtils
from rest.utils.env_creation import EnvCreation
from rest.utils.io_utils import IOUtils


class DockerUtils(EnvCreation):

    @staticmethod
    def up(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "pull", "&&", "docker-compose", "-f", f"{file}", "up", "-d"])

    @staticmethod
    def down(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "-f", f"{file}", "down", "-v"])

    @staticmethod
    def start(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "-f", f"{file}", "start"])

    @staticmethod
    def stop(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["docker-compose", "-f", f"{file}", "stop"])

    @staticmethod
    def logs(file):
        file_path = Path(f"{file}")
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(
            ["docker-compose", "-f", f"{file}", "logs", "-t", f"--tail={Constants.DOCKER_LOGS_LINES}"])

    @staticmethod
    def ps(id):
        return CmdUtils.run_cmd(["docker", "ps", "--filter", f"name={id}"])

    @staticmethod
    def exec(container_id, command):
        container_exec_cmd = ["docker", "exec", f"{container_id}"]
        container_exec_cmd.extend(command)
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def network_prune():
        container_exec_cmd = ["docker", "network", "prune", "-f"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def network_connect(deployer_net, container):
        container_exec_cmd = ["docker", "network", "connect", f"{deployer_net}", f"{container}"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def network_disconnect(deployer_net, container):
        container_exec_cmd = ["docker", "network", "disconnect", f"{deployer_net}", f"{container}"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def volume_prune():
        container_exec_cmd = ["docker", "volume", "prune", "-f"]
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def cp(compose_id, service_name, file_or_folder):
        container_id = f"{compose_id}_{service_name}_1"
        command = rf''' {container_id}:{file_or_folder} /tmp/{compose_id}'''
        container_exec_cmd = r'''docker cp ''' + command
        return CmdUtils.run_cmd_shell_true(container_exec_cmd)

    @staticmethod
    def exec_detached(container_id, command):
        container_exec_cmd = ["docker", "exec", "-d", f"{container_id}"]
        container_exec_cmd.extend(command)
        return CmdUtils.run_cmd(container_exec_cmd)

    @staticmethod
    def stats(command):
        container_exec_cmd = r'''docker stats --no-stream ''' + command
        return CmdUtils.run_cmd_shell_true(container_exec_cmd)

    @staticmethod
    def clean_up():
        DockerUtils.network_prune()
        DockerUtils.volume_prune()

    @staticmethod
    def get_hostname_fqdn():
        return CmdUtils.run_cmd(["hostname", "--fqdn"])

    @staticmethod
    def get_active_deployments():
        active_deployments = []
        full_deployments_list = IOUtils.get_list_dir(f"{Constants.DEPLOY_FOLDER_PATH}")
        for item in full_deployments_list:
            container_list = DockerUtils.ps(item).get('out').split("\n")[1:-1]
            for container in container_list:
                if item in container:
                    active_deployments.append(ActiveDeployments.docker_deployment(item.strip(), container_list))

        return active_deployments

    @staticmethod
    def folder_clean_up(path=Constants.DEPLOY_FOLDER_PATH, delete_period=60):
        active_deployments = []
        active_deployments_objects = DockerUtils.get_active_deployments()
        for item in active_deployments_objects:
            active_deployments.append(item.get('id'))
        full_deployments_list = map(lambda x: x.rstrip(), IOUtils.get_list_dir(f"{path}"))
        for item in full_deployments_list:
            if item not in active_deployments and (datetime.datetime.now() - datetime.datetime.fromtimestamp(
                    os.path.getmtime(f"{path}{item}"))) > datetime.timedelta(minutes=delete_period):
                shutil.rmtree(f"{path}{item}")

    @staticmethod
    def env_clean_up(path=Constants.DEPLOY_FOLDER_PATH, env_expire_in=1440):  # 1 day
        active_deployments = []
        active_deployments_objects = DockerUtils.get_active_deployments()
        for item in active_deployments_objects:
            active_deployments.append(item.get('id'))
        for item in active_deployments:
            if (datetime.datetime.now() - datetime.datetime.fromtimestamp(
                    os.path.getmtime(f"{path}{item}"))) > datetime.timedelta(minutes=env_expire_in):
                DockerUtils.down(f"{path}{item}/{item}")
