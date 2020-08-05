from rest.api.schedulers.docker_clean_folder_scheduler import DockerCleanFolderScheduler
from rest.api.schedulers.docker_env_expire_scheduler import DockerEnvExpireScheduler
from rest.api.schedulers.docker_scheduler import DockerScheduler
from rest.api.schedulers.kubectl_env_expire_scheduler import KubectlEnvExpireScheduler
from rest.api.views.docker_view import DockerView
from rest.api.views.kubectl_view import KubectlView


class SchedulerAggregator:
    def __init__(self, env_expire_in):
        self.env_expire_in = env_expire_in

    def start(self):
        DockerScheduler().start()
        DockerEnvExpireScheduler(fluentd_utils=DockerView.fluentd_utils,
                                 poll_interval=1200,
                                 env_expire_in=self.env_expire_in).start()  # minutes
        DockerCleanFolderScheduler().start()
        KubectlEnvExpireScheduler(fluentd_utils=KubectlView.fluentd_utils,
                                  env_expire_in=self.env_expire_in).start()
