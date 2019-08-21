import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from rest.utils.utils import Utils


class DockerScheduler:
    scheduler = BackgroundScheduler(daemon=False)
    interval = 120

    def __init__(self):
        self.scheduler.add_job(Utils().docker_clean_up, trigger='interval', seconds=self.interval)
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        print("Starting docker cleanup scheduler ... \n")
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()
