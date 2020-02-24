import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from rest.utils.docker_utils import DockerUtils


class DockerScheduler:

    def __init__(self, poll_interval=120):
        self.poll_interval = poll_interval
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(DockerUtils.clean_up, IntervalTrigger(seconds=self.poll_interval))
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        print("Starting docker cleanup scheduler ... \n")
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    def stop(self):
        print("Stopping docker cleanup scheduler ... \n")
        atexit.unregister(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.shutdown(wait=False)
