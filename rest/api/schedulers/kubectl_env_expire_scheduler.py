import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from rest.api.apiresponsehelpers.constants import Constants
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.utils.kubectl_utils import KubectlUtils


class KubectlEnvExpireScheduler:

    def __init__(self, fluentd_utils, path=Constants.DEPLOY_FOLDER_PATH, poll_interval=120, env_expire_in=1440):
        self.fluentd_utils = fluentd_utils
        self.fluentd_tag = 'KubectlEnvExpireScheduler'
        self.interval = poll_interval
        self.env_expire_in = env_expire_in
        self.path = path
        self.scheduler = BackgroundScheduler(daemon=False)
        self.scheduler.add_job(KubectlUtils.env_clean_up, args=[self.fluentd_utils, self.env_expire_in],
                               trigger='interval',
                               seconds=self.interval)
        self.message_dumper = MessageDumper()
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        self.fluentd_utils.debug(self.fluentd_tag,
                                 self.message_dumper.dump_message("Starting k8s env expire scheduler"))
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    def stop(self):
        self.fluentd_utils.debug(self.fluentd_tag,
                                 self.message_dumper.dump_message("Stopping k8s env expire scheduler"))
        self.scheduler.shutdown(wait=False)
