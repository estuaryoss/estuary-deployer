from rest.api.constants.env_init import EnvInit
from rest.api.schedulers.base_scheduler import BaseScheduler
from rest.utils.docker_utils import DockerUtils


class DockerEnvExpireScheduler(BaseScheduler):

    def __init__(self, fluentd_utils=None, path=EnvInit.DEPLOY_PATH,
                 poll_interval=1200, env_expire_in=1440):
        super().__init__(fluentd_utils=fluentd_utils, method=DockerUtils.env_clean_up, poll_interval=poll_interval,
                         args=[fluentd_utils, path, env_expire_in])

    def start(self):
        super().log(fluentd_tag="DockerEnvExpireScheduler", message="Starting docker env expire scheduler")
        super().start()

    def stop(self):
        super().log(fluentd_tag="DockerEnvExpireScheduler", message="Stopping docker env expire scheduler")
        super().stop()
