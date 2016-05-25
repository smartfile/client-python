import os
import unittest
from cStringIO import StringIO

from smartfile import BasicClient

API_KEY = os.environ.get("API_KEY")
API_PASSWORD = os.environ.get("API_PASSWORD")
TESTFN = "testfn"

if API_KEY is None:
    raise RuntimeError("API_KEY is required")

if API_PASSWORD is None:
    raise RuntimeError("API_PASSWORD is required")


class CustomOperationsTestCase(unittest.TestCase):

    def setUp(self):
        self.api = BasicClient(API_KEY, API_PASSWORD)

    def test_upload_and_download(self):
        # Upload a file, download it, make sure the downloaded version
        # has the same content.
        file_contents = "hello there"
        f = StringIO(file_contents)
        f.seek(0)
        self.api.upload(TESTFN, f)
        r = self.api.download(TESTFN)
        self.assertEqual(r.data, file_contents)
