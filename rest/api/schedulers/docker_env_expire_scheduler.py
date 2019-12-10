import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fluent import sender

from rest.api.apiresponsehelpers.constants import Constants
from rest.api.logginghelpers.message_dumper import MessageDumper
from rest.utils.docker_utils import DockerUtils
from rest.utils.fluentd_utils import FluentdUtils


class DockerEnvExpireScheduler:

    def __init__(self, fluentd_utils=FluentdUtils(sender.FluentSender('estuary', host='127.0.0.1',
                                                                      port=24224)),
                 path=Constants.DEPLOY_FOLDER_PATH,
                 poll_interval=120, env_expire_in=1440):
        self.fluentd_utils = fluentd_utils
        self.fluentd_tag = 'DockerEnvExpireScheduler'
        self.poll_interval = poll_interval
        self.env_expire_in = env_expire_in
        self.path = path
        self.message_dumper = MessageDumper()
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(DockerUtils.env_clean_up, IntervalTrigger(seconds=self.poll_interval),
                               args=[self.fluentd_utils, self.path, self.env_expire_in])
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        self.fluentd_utils.debug(self.fluentd_tag,
                                 self.message_dumper.dump_message("Starting docker env expire scheduler"))
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    def stop(self):
        self.fluentd_utils.debug(self.fluentd_tag,
                                 self.message_dumper.dump_message("Stopping docker env expire scheduler"))
        self.scheduler.shutdown(wait=False)
