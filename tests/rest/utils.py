import errno
import os
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
