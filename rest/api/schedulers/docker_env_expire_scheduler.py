import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from rest.api.apiresponsehelpers.constants import Constants
from rest.utils.docker_utils import DockerUtils


class DockerEnvExpireScheduler:

    def __init__(self, path=Constants.DEPLOY_FOLDER_PATH, poll_interval=120, env_expire_in=1440):
        self.interval = poll_interval
        self.env_expire_in = env_expire_in
        self.path = path
        self.scheduler = BackgroundScheduler(daemon=False)
        self.scheduler.add_job(DockerUtils.env_clean_up, args=[self.path, self.env_expire_in], trigger='interval',
                               seconds=self.interval)
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        print("Starting docker env expire scheduler ... \n")
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()

    def stop(self):
        print("Stopping docker env expire scheduler ... \n")
        self.scheduler.shutdown(wait=False)