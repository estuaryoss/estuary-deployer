import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from rest.api.apiresponsehelpers.constants import Constants
from rest.utils.docker_utils import DockerUtils


class CleanFolderScheduler:

    def __init__(self, path=Constants.DOCKER_PATH, poll_interval=120, delete_period=60):
        self.interval = poll_interval
        self.delete_period = delete_period
        self.path = path
        self.scheduler = BackgroundScheduler(daemon=False)
        self.scheduler.add_job(DockerUtils.folder_clean_up, args=[self.path,self.delete_period], trigger='interval', seconds=self.interval)
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        print("Starting tmp folder cleaning scheduler ... \n")
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    def stop(self):
        print("Stopping tmp folder cleaning scheduler ... \n")
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.shutdown(wait=False)