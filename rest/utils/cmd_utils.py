import subprocess


class CmdUtils:

    @staticmethod
    def run_cmd_detached(command):
        subprocess.Popen(command, stdout=None,
                         stderr=None, shell=True)

    @staticmethod
    def run_cmd(command):
        p = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        [out, err] = p.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]

    @staticmethod
    def run_cmd_shell_true(command):
        p = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True)

        [out, err] = p.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]