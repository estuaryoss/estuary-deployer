from rest.api.schedulers.base_scheduler import BaseScheduler
from rest.utils.docker_utils import DockerUtils


class DockerScheduler(BaseScheduler):

    def __init__(self, poll_interval=120):
        """Networks and volumes cycle"""
        super().__init__(fluentd_utils=None, method=DockerUtils.clean_up, poll_interval=poll_interval, args=[])

    def start(self):
        super().start()

    def stop(self):
        super().stop()
