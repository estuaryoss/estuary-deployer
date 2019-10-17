import errno
import os
from pathlib import Path

from rest.utils.cmd_utils import CmdUtils
from rest.utils.env_creation import EnvCreation


class KubectlUtils(EnvCreation):

    @staticmethod
    def up(file):
        file_path = Path(file)
        if not file_path.is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        return CmdUtils.run_cmd(["kubectl", "apply", "-f", f"{file}"])
