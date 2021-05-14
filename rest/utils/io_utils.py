import errno
import json
import os
import shutil
from pathlib import Path


class IOUtils:

    @staticmethod
    def create_dir(path, permissions=0o755):
        if not os.path.exists(path):
            os.makedirs(path, permissions)

    @staticmethod
    def get_list_dir(path):
        dir_list = []
        file_path = Path(path)
        if file_path.exists():
            dir_list = [directory for directory in list(os.listdir(path)) if
                        os.path.isdir(path + "/{}".format(directory))]

        return dir_list

    @staticmethod
    def write_to_file(file, content=""):
        with open(file, 'w') as f:
            f.write(content)

    @staticmethod
    def write_to_file_dict(file, content={}):
        with open(file, 'w') as f:
            f.write(json.dumps(content))

    @staticmethod
    def write_to_file_binary(file, content=""):
        with open(file, 'wb') as f:
            f.write(content)

    @staticmethod
    def read_file(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        with open(file, 'r') as f:
            return f.read()

    @staticmethod
    def zip_file(id, path):
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        shutil.make_archive(f"/tmp/{id}", 'zip', f"/tmp/{id}")

    @staticmethod
    def does_file_exist(file):
        return Path(file).exists()

    @staticmethod
    def remove_file(file):
        file_path = Path(file)
        file_path.unlink()

    @staticmethod
    def remove_directory(dir):
        shutil.rmtree(dir)
