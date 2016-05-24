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
        self.uploaddata = None
    
    def get_data(self):
        self.uploaddata = self.api.get("/path/info/myfile.txt")
        return self.uploaddata
        
    def upload(self):
        data = open(self.txtfile, "rb")
        newfile = ('myfile.txt', data)
        self.api.upload(newfile)
        self.assertEquals(self.get_data()['size'], os.path.getsize(self.txtfile))
        
    def download(self): 
        f = self.api.download("myfile.txt")
        self.assertEquals(f.readlines(), open(self.txtfile, "rb").readlines())
    
    def move(self):
        self.api.move('myfile.txt', '/newFolder/')
        
    def delete(self):
        self.api.delete("/newFolder/myfile.txt")
        self.assertRaises(Exception, BasicClient.delete) 
        
    def test_upload_download_move_delete_clean_up(self):
        self.upload()
        self.download()
        self.move()
        self.delete()