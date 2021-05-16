from rest.api.constants.env_constants import EnvConstants
from rest.api.constants.env_init import EnvInit
from rest.api.schedulers.base_scheduler import BaseScheduler
from rest.utils.docker_utils import DockerUtils


class DockerCleanFolderScheduler(BaseScheduler):

    def __init__(self, path=EnvInit.init.get(EnvConstants.DEPLOY_PATH), poll_interval=120, delete_period=60):
        """Deployments folder clean up."""
        super().__init__(fluentd_utils=None, method=DockerUtils.folder_clean_up, poll_interval=poll_interval,
                         args=[path, delete_period])

    def start(self):
        super().start()

    def stop(self):
        super().stop()
