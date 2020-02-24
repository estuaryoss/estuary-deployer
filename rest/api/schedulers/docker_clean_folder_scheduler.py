import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from rest.api.constants.env_constants import EnvConstants
from rest.utils.docker_utils import DockerUtils


class DockerCleanFolderScheduler:

    def __init__(self, path=EnvConstants.DEPLOY_PATH, poll_interval=120, delete_period=60):
        self.poll_interval = poll_interval
        self.delete_period = delete_period
        self.path = path
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(DockerUtils.folder_clean_up, IntervalTrigger(seconds=self.poll_interval),
                               args=[self.path, self.delete_period])
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
