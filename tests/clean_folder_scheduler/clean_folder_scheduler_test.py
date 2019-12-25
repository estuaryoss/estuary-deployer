import time
import unittest

from rest.api.schedulers.docker_clean_folder_scheduler import DockerCleanFolderScheduler
from rest.utils.io_utils import IOUtils


class CleanFolderSchedulerTestCase(unittest.TestCase):

    def setUp(self):
        self.path = "./tmp/"
        self.clean_folder_scheduler = DockerCleanFolderScheduler(self.path, 10, 1)

    def test_folder_clean_up(self):
        utils = IOUtils()
        self.assertEqual(len(utils.get_list_dir(self.path)), 0)
        for i in range(1, 3):
            utils.create_dir(self.path + str(i))
            utils.write_to_file(self.path + str(i) + "/" + str(i), "whatever")
        self.assertEqual(len(utils.get_list_dir(self.path)), 2)
        self.clean_folder_scheduler.start()
        time.sleep(70)
        self.assertEqual(len(utils.get_list_dir(self.path)), 0)

    def tearDown(self):
        self.clean_folder_scheduler.stop()


if __name__ == '__main__':
    unittest.main()
