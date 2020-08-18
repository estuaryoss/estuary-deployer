import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from rest.api.constants.env_init import EnvInit
from rest.api.loghelpers.message_dumper import MessageDumper
from rest.utils.kubectl_utils import KubectlUtils


class KubectlEnvExpireScheduler:

    def __init__(self, fluentd_utils, path=EnvInit.DEPLOY_PATH, poll_interval=120, env_expire_in=1440):
        self.fluentd_utils = fluentd_utils
        self.fluentd_tag = 'KubectlEnvExpireScheduler'
        self.poll_interval = poll_interval
        self.env_expire_in = env_expire_in
        self.path = path
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(KubectlUtils.env_clean_up, IntervalTrigger(seconds=self.poll_interval),
                               args=[self.fluentd_utils, self.env_expire_in])
        self.message_dumper = MessageDumper()
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        self.fluentd_utils.emit(tag=self.fluentd_tag,
                                 msg=self.message_dumper.dump_message("Starting k8s env expire scheduler"))
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    def stop(self):
        self.fluentd_utils.emit(tag=self.fluentd_tag,
                                 msg=self.message_dumper.dump_message("Stopping k8s env expire scheduler"))
        self.scheduler.shutdown(wait=False)
