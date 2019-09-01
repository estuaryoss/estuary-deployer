import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from rest.utils.utils import Utils


class TmpFolderScheduler:
    scheduler = BackgroundScheduler(daemon=False)
    interval = 120

    def __init__(self):
        self.scheduler.add_job(Utils().tmp_folder_clean_up, trigger='interval', seconds=self.interval)
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.INFO)

    def start(self):
        print("Starting tmp folder cleaning scheduler ... \n")
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler.start()
