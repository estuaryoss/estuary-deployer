import errno
import os
import shutil
import subprocess
from pathlib import Path


class Utils:

    def create_dir(self, path, permissions=0o755):
        if not os.path.exists(path):
            os.makedirs(path, permissions)

    def write_to_file(self, file, content=""):
        with open(file, 'wb') as f:
            f.write(content)

    def read_file(self, file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        with open(file, 'r') as f:
            return f.read()

    def zip_file(self, name, path):
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        shutil.make_archive(f"/tmp/{name}", 'zip', f"{path}")

    def get_hostname_fqdn(self):
        result = subprocess.Popen(["hostname", "--fqdn"], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    def run_cmd(self, command):
        result = subprocess.Popen(command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        out, err = result.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]
