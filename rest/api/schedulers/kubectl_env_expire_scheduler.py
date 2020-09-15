from rest.api.schedulers.base_scheduler import BaseScheduler
from rest.utils.kubectl_utils import KubectlUtils


class KubectlEnvExpireScheduler(BaseScheduler):

    def __init__(self, fluentd_utils=None, poll_interval=1200, env_expire_in=1440):
        """K8s deployments env expire scheduler."""
        super().__init__(fluentd_utils=fluentd_utils, method=KubectlUtils.env_clean_up, poll_interval=poll_interval,
                         args=[fluentd_utils, env_expire_in])

    def start(self):
        super().log(fluentd_tag="KubectlEnvExpireScheduler", message="Starting docker env expire scheduler")
        super().start()

    def stop(self):
        super().log(fluentd_tag="KubectlEnvExpireScheduler", message="Stopping docker env expire scheduler")
        super().stop()
