# -*- coding: utf-8 -*-

import os
import json
import zlib
import random
import hashlib
import urlparse
import unittest
import tempfile
import threading

from collections import deque

from StringIO import StringIO

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from smartfile import BasicClient
from smartfile import OAuthClient
from smartfile.sync import table
from smartfile.sync import delta
from smartfile.sync import patch
from smartfile.sync import RollingChecksum
from smartfile.sync import SRC
from smartfile.sync import DST
from smartfile.sync import BS
from smartfile.errors import APIError
from smartfile.errors import RequestError

API_KEY = '8g1aq1UF2QfZTG47yEVhVLAFqyfDdp'
API_PASSWORD = '3II3UFD3pBAwy3Rbz8mVWBhJTA2Gvd'
CLIENT_TOKEN = '8oWot4KrppJDzfokDsHNJrND0Ay13s'
CLIENT_SECRET = '0I7BV6Bm3Rgfk73LL68vBp0u23KcKr'
ACCESS_TOKEN = 'hIlkipZNmwIJ28HQtQRcbGuXBePQp5'
ACCESS_SECRET = 'Scen1dwmVtWhjLpJfnilrfdc5OZWCJ'


class TestHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    A simple handler that logs requests for examination.
    """
    class TestRequest(object):
        def __init__(self, method, path, query=None, data=None):
            self.method = method
            self.path = path
            self.query = query
            self.data = data

    def __init__(self, *args, **kwargs):
        self.verbose = kwargs.pop('verbose', False)
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def record(self, method, path, query=None, data=None):
        self.server.requests.append(TestHTTPRequestHandler.TestRequest(method,
                                    path, query=query, data=data))

    def respond(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("Hello World!")

    def parse_and_record(self, method):
        urlp = urlparse.urlparse(self.path)
        query, data = urlparse.parse_qs(urlp.query), None
        if method == 'POST':
            l = int(self.headers['Content-Length'])
            data = urlparse.parse_qs(self.rfile.read(l))
        self.record(method, urlp.path, query=query, data=data)
        self.respond()

    def log_message(self, *args, **kwargs):
        if self.verbose:
            BaseHTTPRequestHandler.log_message(self, *args, **kwargs)

    def do_GET(self):
        self.parse_and_record('GET')

    def do_PUT(self):
        self.parse_and_record('PUT')

    def do_POST(self):
        self.parse_and_record('POST')

    def do_DELETE(self):
        self.parse_and_record('DELETE')


class TestHTTPServer(threading.Thread, HTTPServer):
    """
    A simple server that logs requests for examination. Provides some basic
    assertions that should aid in test development.
    """
    allow_reuse_address = True

    def __init__(self, address='127.0.0.1', port=0, handler=TestHTTPRequestHandler):
        HTTPServer.__init__(self, (address, port), handler)
        threading.Thread.__init__(self)
        self.requests = []
        self.setDaemon(True)
        self.start()

    def run(self):
        self.serve_forever()


class TestServerTestCase(unittest.TestCase):
    """
    Test case that starts our test HTTP server.
    """
    def setUp(self):
        self.server = TestHTTPServer()

    def tearDown(self):
        self.server.shutdown()

    def assertRequestCount(self, num=1):
        requests = len(self.server.requests)
        if requests > num:
            raise AssertionError('More than %s request performed: %s' % (num,
                                 requests))
        elif requests < num:
            raise AssertionError('Less than %s request performed' % num)

    def assertMethod(self, method):
        try:
            request = self.server.requests[0]
        except IndexError:
            raise AssertionError('Cannot assert method without request')
        if request.method != method:
            raise AssertionError('%s is not %s method' % (method,
                                 request.method))

    def assertPath(self, path):
        try:
            request = self.server.requests[0]
        except IndexError:
            raise AssertionError('Cannot assert path without request')
        if request.path != path:
            raise AssertionError('"%s" is not equal to "%s"' % (path,
                                 request.path))


class BasicTestCase(TestServerTestCase):
    def getClient(self, **kwargs):
        kwargs.setdefault('key', API_KEY)
        kwargs.setdefault('password', API_PASSWORD)
        kwargs.setdefault('url', 'http://127.0.0.1:%s/' %
                          self.server.server_port)
        return BasicClient(**kwargs)


class OAuthTestCase(TestServerTestCase):
    def getClient(self, **kwargs):
        kwargs.setdefault('client_token', CLIENT_TOKEN)
        kwargs.setdefault('client_secret', CLIENT_SECRET)
        kwargs.setdefault('access_token', ACCESS_TOKEN)
        kwargs.setdefault('access_secret', ACCESS_SECRET)
        kwargs.setdefault('url', 'http://127.0.0.1:%s/' %
                          self.server.server_port)
        return OAuthClient(**kwargs)


class UrlGenerationTestCase(object):
    "Tests that validate 'auto-generated' URLs."
    def test_with_path_id(self):
        client = self.getClient()
        client.get('/path/data', '/the/file/path')
        self.assertMethod('GET')
        self.assertPath('/api/{0}/path/data/the/file/path/'.format(
            client.version))

    def test_with_int_id(self):
        client = self.getClient()
        client.get('/access/user', 42)
        self.assertMethod('GET')
        self.assertPath('/api/{0}/access/user/42/'.format(client.version))

    def test_with_version(self):
        client = self.getClient(version='3.1')
        client.get('/ping')
        self.assertMethod('GET')
        self.assertPath('/api/{0}/ping/'.format(client.version))


class MethodTestCase(object):
    "Tests the HTTP methods used by CRUD methods."
    def test_call_is_GET(self):
        client = self.getClient()
        client('/user', 'bobafett')
        self.assertMethod('GET')

    def test_post_is_POST(self):
        client = self.getClient()
        client.post('/user', username='bobafett', email='bobafett@example.com')
        self.assertMethod('POST')

    def test_get_is_GET(self):
        client = self.getClient()
        client.get('/user', 'bobafett')
        self.assertMethod('GET')

    def test_put_is_PUT(self):
        client = self.getClient()
        client.put('/user', 'bobafett', full_name='Boba Fett')
        self.assertMethod('PUT')

    def test_delete_is_DELETE(self):
        client = self.getClient()
        client.delete('/user', 'bobafett')
        self.assertMethod('DELETE')


class DownloadTestCase(object):
    def test_file_response(self):
        client = self.getClient()
        r = client.get('/user')
        self.assertTrue(hasattr(r, 'read'), 'File-like object not returned.')
        self.assertEqual(r.read(), 'Hello World!')


class UploadTestCase(object):
    def test_file_upload(self):
        client = self.getClient()
        fd, t = tempfile.mkstemp()
        os.close(fd)
        try:
            client.post('/path/data', 'foobar.png', file=file(t))
        except Exception, e:
            self.fail('POSTing a file failed. %s' % e)
        finally:
            try:
                os.unlink(t)
            except:
                pass


class BasicEnvironTestCase(BasicTestCase):
    "Tests that the API client reads settings from ENV."
    def setUp(self):
        super(BasicEnvironTestCase, self).setUp()
        os.environ['SMARTFILE_API_KEY'] = API_KEY
        os.environ['SMARTFILE_API_PASSWORD'] = API_KEY

    def tearDown(self):
        super(BasicEnvironTestCase, self).tearDown()
        del os.environ['SMARTFILE_API_KEY']
        del os.environ['SMARTFILE_API_PASSWORD']

    def test_read_from_env(self):
        # Blank out the credentials, the client should read them from the
        # environment variables.
        client = self.getClient(key=None, password=None)
        client.get('/ping')
        self.assertMethod('GET')
        self.assertPath('/api/{0}/ping/'.format(client.version))


class OAuthEnvironTestCase(OAuthTestCase):
    "Tests that the API client reads settings from ENV."
    def setUp(self):
        super(OAuthEnvironTestCase, self).setUp()
        os.environ['SMARTFILE_CLIENT_TOKEN'] = CLIENT_TOKEN
        os.environ['SMARTFILE_CLIENT_SECRET'] = CLIENT_SECRET
        os.environ['SMARTFILE_ACCESS_TOKEN'] = ACCESS_TOKEN
        os.environ['SMARTFILE_ACCESS_SECRET'] = ACCESS_SECRET

    def tearDown(self):
        super(OAuthEnvironTestCase, self).tearDown()
        del os.environ['SMARTFILE_CLIENT_TOKEN']
        del os.environ['SMARTFILE_CLIENT_SECRET']
        del os.environ['SMARTFILE_ACCESS_TOKEN']
        del os.environ['SMARTFILE_ACCESS_SECRET']

    def test_read_from_env(self):
        # Blank out the credentials, the client should read them from the
        # environment variables.
        client = self.getClient(client_token=None, client_secret=None)
        client.get('/ping')
        self.assertMethod('GET')
        self.assertPath('/api/{0}/ping/'.format(client.version))


class BasicClientTestCase(DownloadTestCase, UploadTestCase, MethodTestCase,
                          UrlGenerationTestCase, BasicTestCase):
    def test_blank_credentials(self):
        self.assertRaises(APIError, self.getClient, key='', password='')

    def test_netrc(self):
        fd, t = tempfile.mkstemp()
        try:
            try:
                address = self.server.server_address
                if isinstance(address, tuple):
                    address, port = address
                else:
                    port = self.server.server_port
                netrc = "machine 127.0.0.1:%s\n  login %s\n  password %s" % (
                        port, API_KEY, API_PASSWORD)
                os.write(fd, netrc)
            finally:
                os.close(fd)
            client = self.getClient(key=None, password=None, netrcfile=t)
            client.get('/ping')
            self.assertMethod('GET')
            self.assertPath('/api/{0}/ping/'.format(client.version))
        finally:
            try:
                os.unlink(t)
            except:
                pass


class OAuthClientTestCase(DownloadTestCase, UploadTestCase, MethodTestCase,
                          UrlGenerationTestCase, OAuthTestCase):
    def test_blank_client_token(self):
        self.assertRaises(APIError, self.getClient, client_token='', client_secret='')

    def test_blank_access_token(self):
        client = self.getClient(access_token='', access_secret='')
        self.assertRaises(APIError, client.get, '/ping')


class HTTPThrottleRequestHandler(TestHTTPRequestHandler):
    def respond(self):
        self.send_response(503)
        self.send_header("X-Throttle", "throttled; next=0.01 sec")
        self.end_headers()
        self.wfile.write("Request Throttled!")


class ThrottleTestCase(object):
    def setUp(self):
        self.server = TestHTTPServer(handler=HTTPThrottleRequestHandler)

    def test_throttle_GET(self):
        client = self.getClient()
        self.assertRaises(RequestError, client.get, '/ping')
        self.assertRequestCount(3)


class BasicThrottleTestCase(ThrottleTestCase, BasicTestCase):
    pass


class OAuthThrottleTestCase(ThrottleTestCase, OAuthTestCase):
    pass


class HTTPJSONRequestHandler(TestHTTPRequestHandler):
    def respond(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({ 'foo': 'bar' }))


class JSONTestCase(object):
    def setUp(self):
        self.server = TestHTTPServer(handler=HTTPJSONRequestHandler)

    def test_throttle_GET(self):
        client = self.getClient()
        r = client.get('/user')
        self.assertMethod('GET')
        self.assertEqual(r, { 'foo': 'bar' })


class BasicJSONTestCase(JSONTestCase, BasicTestCase):
    pass


class OAuthJSONTestCase(JSONTestCase, OAuthTestCase):
    pass


# TODO: Test with missing oauthlib...
# Must invoke an ImportError when smartfile tries to import it. Then the test
# case should verify that the correct exception (NotImplementedError) is raised
# when OAuth is used...
#
# http://stackoverflow.com/questions/2481511/mocking-importerror-in-python


class SyncTableTestCase(unittest.TestCase):
    def setUp(self):
        "Create a buffer containing random data."
        self.rand = StringIO(os.urandom(1024**2))

    def test_block_size_default(self):
        "Ensure default block_size works."
        blocks = table(self.rand)
        self.assertEqual(len(blocks), self.rand.tell()/BS)

    def test_block_size_1024(self):
        "Ensure the proper number of blocks are produced."
        blocks = table(self.rand, block_size=1024)
        self.assertEqual(len(blocks), 1024)

    def test_block_size_2048(self):
        "Ensure the proper number of blocks are produced."
        blocks = table(self.rand, block_size=2048)
        self.assertEqual(len(blocks), 512)

    def test_blocks(self):
        "Ensure the block checksums are correct."
        blocks = table(self.rand)
        self.rand.seek(0)
        while True:
            block = self.rand.read(BS)
            if not block:
                break
            match = blocks.get(RollingChecksum(block).digest())
            self.assertIsNotNone(match)
            self.assertIn(hashlib.md5(block).hexdigest(), match)


class SyncDeltaTestCase(unittest.TestCase):
    def setUp(self):
        self.rand1 = StringIO(os.urandom(1024**2))
        self.rand2 = StringIO(os.urandom(1024**2))

    def test_identical(self):
        "Ensure two files with ALL matching blocks are handled."
        blocks = table(self.rand1)
        ranges, blob = delta(self.rand1, blocks)
        # No non-matching blocks
        self.assertEqual(blob.tell(), 0)
        # All blocks should be collapsed into a single range
        self.assertEqual(len(ranges), 1)

    def test_different(self):
        "Ensure two files with NO matching blocks are handled."
        blocks = table(self.rand1)
        ranges, blob = delta(self.rand2, blocks)
        # Blob should contain the entire source file
        self.assertEqual(blob.tell(), self.rand1.tell())
        # There should be one range representing the entire source file
        self.assertEqual(len(ranges), 1)

    def test_mixed(self):
        "Ensure two files with some overlapping blocks are handled."
        # Make sure first and last blocks match.
        matching = [0, 1024]
        # Pick 510 additional random blocks to make identical (half).
        for i in xrange(510):
            while True:
                block_num = random.randint(0, 1024)
                if block_num not in matching:
                    break
            matching.append(block_num)
        # Copy our matching blocks from SRC to DST
        for block_num in matching:
            self.rand1.seek(block_num*1024)
            self.rand2.seek(block_num*1024)
            self.rand2.write(self.rand1.read(1024))
        # Continue as normal.
        blocks = table(self.rand1, block_size=1024)
        ranges, blob = delta(self.rand2, blocks, block_size=1024)
        self.assertLess(blob.tell(), self.rand1.tell() / 2 + 4096)
        for i, (direction, offset, length) in enumerate(ranges):
            if direction == DST:
                # If the block matches, we should find it's offset / block_size
                # in matching:
                block_num = offset / 1024
                self.assertIn(block_num, matching)
            # Since blocks are combined, there are not many other assertions we
            # can make.


class SyncPatchTestCase(unittest.TestCase):
    def setUp(self):
        self.rand1 = StringIO(os.urandom(1024**2))
        self.rand2 = StringIO(os.urandom(1024**2))

    def test_1024(self):
        "Ensure a block_size of 1024 works."
        blocks = table(self.rand1, block_size=1024)
        ranges, blob = delta(self.rand2, blocks, block_size=1024)
        out = patch(self.rand1, ranges, blob)
        self.assertEqual(hashlib.md5(out.read()).digest(),
                         hashlib.md5(self.rand2.getvalue()).digest())

    def test_2048(self):
        "Ensure a block_size of 2048 works."
        blocks = table(self.rand1, block_size=2048)
        ranges, blob = delta(self.rand2, blocks, block_size=2048)
        out = patch(self.rand1, ranges, blob)
        self.assertEqual(hashlib.md5(out.read()).digest(),
                         hashlib.md5(self.rand2.getvalue()).digest())

    def test_2001(self):
        "Ensure an odd block size works."
        blocks = table(self.rand1, block_size=2001)
        ranges, blob = delta(self.rand2, blocks, block_size=2001)
        out = patch(self.rand1, ranges, blob)
        self.assertEqual(hashlib.md5(out.read()).digest(),
                         hashlib.md5(self.rand2.getvalue()).digest())

    def test_identical(self):
        "Ensure patching a file that is identical works."
        blocks = table(self.rand1, block_size=2048)
        ranges, blob = delta(self.rand1, blocks, block_size=1024)
        out = patch(self.rand1, ranges, blob)
        self.assertEqual(hashlib.md5(out.read()).digest(),
                         hashlib.md5(self.rand1.getvalue()).digest())


# Original functions, I converted to a class and optimized.
# http://code.activestate.com/recipes/577518-rsync-algorithm/
def weakchecksum(data):
    a = b = 0
    l = len(data)
    for i in range(l):
        a += ord(data[i])
        b += (l - i)*ord(data[i])
    return (b << 16) | a, a, b


def rollingchecksum(removed, new, a, b, blocksize=4096):
    a -= ord(removed) - ord(new)
    b -= ord(removed) * blocksize - a
    return (b << 16) | a, a, b


class SyncChecksumTestCase(unittest.TestCase):
    def test_single(self):
        "Ensure our checksum on a static buffer is true to the original."
        for i in xrange(100):
            data = os.urandom(32)
            self.assertEqual(RollingChecksum(data).digest(), weakchecksum(data)[0])

    def test_rolling(self):
        "Ensure our rolling checksum is true to the original."
        data = deque(os.urandom(32))
        sum1 = RollingChecksum(data, block_size=32)
        sum2, a, b = weakchecksum(data)
        for i in xrange(100):
            next = os.urandom(1)
            data.append(next)
            last = data.popleft()
            sum1.roll(last, next)
            sum2, a, b = rollingchecksum(last, next, a, b, blocksize=32)
            self.assertEqual(sum1.digest(), sum2)

    def test_equality(self):
        """Ensure that a rolling checksum created on a buffer is equal to the
        one created when rolling over that buffer."""
        data = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        # Create a checksum of bytes 10 -20
        sum1 = RollingChecksum(data[10:20], block_size=10)
        # Create a checksum of bytes 0 - 10
        sum2 = RollingChecksum(data[:10], block_size=10)
        # Roll the second checksum over the buffer until reaching bytes 10-20.
        for i in xrange(10):
            sum2.roll(data[i], data[10+i])
        # Sums should now be equal.
        self.assertEqual(sum1.digest(), sum2.digest())


if __name__ == '__main__':
    unittest.main()
