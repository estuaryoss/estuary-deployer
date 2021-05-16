from fluent import sender

from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.schedulers.base_scheduler import BaseScheduler
from rest.service.fluentd import Fluentd
from rest.utils.docker_utils import DockerUtils


class DockerEnvExpireScheduler(BaseScheduler):

    def __init__(self, fluentd_utils=Fluentd(sender.FluentSender('estuary', host='127.0.0.1',
                                                                 port=24224)),
                 path=EnvInit.init.get(EnvConstants.DEPLOY_PATH), poll_interval=1200, env_expire_in=1440):
        """Docker env expire scheduler."""
        super().__init__(fluentd_utils=fluentd_utils, method=DockerUtils.env_clean_up, poll_interval=poll_interval,
                         args=[fluentd_utils, path, env_expire_in])

    def start(self):
        super().log(fluentd_tag="DockerEnvExpireScheduler", message="Starting docker env expire scheduler")
        super().start()

    def stop(self):
        super().log(fluentd_tag="DockerEnvExpireScheduler", message="Stopping docker env expire scheduler")
        super().stop()
