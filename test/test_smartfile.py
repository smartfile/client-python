import os
import unittest

from smartfile import BasicClient
from smartfile.errors import ResponseError

API_KEY = os.environ.get("API_KEY")
API_PASSWORD = os.environ.get("API_PASSWORD")

if API_KEY is None:
    raise RuntimeError("API_KEY is required")

if API_PASSWORD is None:
    raise RuntimeError("API_PASSWORD is required")


class CustomOperationsTestCase(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.realpath(__file__)) + "/"
        self.api = BasicClient(API_KEY, API_PASSWORD)
        self.txtfile = self.current_dir + "myfile.txt"
        self.uploaddata = None

    def get_data(self):
        self.uploaddata = self.api.get("/path/info/myfile.txt")
        return self.uploaddata

    def upload(self):
        data = open(self.txtfile, "rb")
        self.api.upload(self.txtfile, data)
        self.assertEquals(self.get_data()['size'],
                          os.path.getsize(self.txtfile))

    def download(self):
        self.api.download("myfile.txt")
        self.assertEquals(os.path.getsize(self.txtfile),
                          self.get_data()['size'])

    def move(self):
        self.api.move('myfile.txt', '/newFolder/')

    def remove(self):
        self.api.remove("/newFolder/myfile.txt")
        with self.assertRaises(ResponseError):
            self.api.remove("/newFolder/myfile.txt")

    def test_upload_download_move_delete(self):
        self.upload()
        self.download()
        self.move()
        self.delete()
