import atexit
import logging
from abc import ABC, abstractmethod

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from rest.api.loghelpers.message_dumper import MessageDumper


class BaseScheduler(ABC):

    def __init__(self, fluentd_utils, method, poll_interval, args):
        "Base scheduler"
        self.fluentd_utils = fluentd_utils
        self.message_dumper = MessageDumper()
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(method, IntervalTrigger(seconds=poll_interval), args=args)
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def log(self, fluentd_tag, message):
        self.fluentd_utils.emit(tag=fluentd_tag, msg=self.message_dumper.dump_message(message=message))

    @abstractmethod
    def start(self):
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    @abstractmethod
    def stop(self):
        self.scheduler.shutdown(wait=False)
