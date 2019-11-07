import subprocess


class CmdUtils:

    @staticmethod
    def run_cmd_detached(command):
        subprocess.Popen(command, stdout=None,
                         stderr=None, shell=True)

    @staticmethod
    def run_cmd(command):
        lines_to_slice = 100
        p = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        [out, err] = p.communicate()
        return {
            "out": "\n".join(out.decode('utf-8').split("\n")[-lines_to_slice:]),
            "err": "\n".join(err.decode('utf-8').split("\n")[-lines_to_slice:]),
            "code": p.returncode,
            "pid": p.pid,
            "args": p.args
        }

    @staticmethod
    def run_cmd_shell_true(command):
        p = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True)

        [out, err] = p.communicate()
        return [out.decode('utf-8'), err.decode('utf-8')]
