import errno
import os
import subprocess
from pathlib import Path

from tests.rest.constants import Constants


class Utils:

    def create_dir(self, path, permissions=0o755):
        if not os.path.exists(path):
            os.makedirs(path, permissions)

    def write_to_file(self, file, content=""):
        with open(file, 'w') as f:
            f.write(content)

    def read_file(self, file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        with open(file, 'r') as f:
            return f.read()

    def docker_up(self, file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        result = subprocess.Popen(["docker-compose", "-f", f"{file}", "up", "-d"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_down(self, file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        result = subprocess.Popen(["docker-compose", "-f", f"{file}", "down", "-v"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_start(self, file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        result = subprocess.Popen(["docker-compose", "-f", f"{file}", "start"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_stop(self, file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        result = subprocess.Popen(["docker-compose", "-f", f"{file}", "stop"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_ps(self, id):
        file_path = Path(Constants.DOCKER_PATH + f"{id}/{id}")
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        result = subprocess.Popen(["docker", "ps", "--filter", f"name={id}"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_exec(self, container_id, command):
        container_exec_cmd = ["docker", "exec", f"{container_id}"]
        container_exec_cmd.extend(command)
        result = subprocess.Popen(container_exec_cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_exec_detached(self, container_id, command):
        container_exec_cmd = ["docker", "exec", "-d", f"{container_id}"]
        container_exec_cmd.extend(command)
        result = subprocess.Popen(container_exec_cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def docker_stats(self, command):
        container_exec_cmd = r'''docker stats --no-stream''' + command
        # container_exec_cmd.extend(command)
        result = subprocess.Popen(container_exec_cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def get_hostname_fqdn(self):
        result = subprocess.Popen(["hostname", "--fqdn"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]
