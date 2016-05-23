import os
import unittest

from smartfile import BasicClient

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
        self.txtfile = self.current_dir + "resources/myfile.txt"
  
    def test_upload_download(self):
        data = open(self.txtfile, "rb")
        newfile = ('myfile.txt', data)
        self.api.upload(newfile)

        f = self.api.download("myfile.txt")
        self.assertEquals(f.readlines(), open(self.txtfile, "rb").readlines())
    
    def test_move(self):
        self.api.move('README.rst', '/newFolder/')