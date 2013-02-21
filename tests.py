# -*- coding: utf-8 -*-

import os
import filecmp
import urlparse
import unittest
import threading

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from smartfile import KeyClient


class TestHTTPServer(threading.Thread, HTTPServer):
    allow_reuse_address = True

    def __init__(self, address='127.0.0.1'):
        HTTPServer.__init__(self, (address, 0), TestHTTPRequestHandler)
        threading.Thread.__init__(self)
        self.requests = []
        self.setDaemon(True)
        self.start()

    def run(self):
        self.serve_forever()

    def assertOneRequest(self):
        requests = len(self.requests)
        if requests > 1:
            raise AssertionError('More than 1 request performed: %s' % requests)
        elif requests < 1:
            raise AssertionError('Less than 1 request performed')

    def assertMethod(self, method):
        try:
            request = self.requests[0]
        except IndexError:
            raise AssertionError('Cannot assert method without request')
        if request.method != method:
            raise AssertionError('%s is not %s method' % (method,
                                 request.method))

    def assertPath(self, path):
        try:
            request = self.requests[0]
        except IndexError:
            raise AssertionError('Cannot assert path without request')
        if request.path != path:
            raise AssertionError('"%s" is not equal to "%s"' % (path,
                                 request.path))


class TestHTTPRequestHandler(BaseHTTPRequestHandler):
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

    def parse_and_record(self, method):
        urlp = urlparse.urlparse(self.path)
        query, data = urlparse.parse_qs(urlp.query), None
        if method == 'POST':
            l = int(self.headers['Content-Length'])
            data = urlparse.parse_qs(self.rfile.read(l))
        self.record(method, urlp.path, query=query, data=data)
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("Hello World!")

    def log_message(self, *args, **kwargs):
        if self.verbose:
            BaseHTTPRequestHandler.log_message(self, *args, **kwargs)

    def do_GET(self):
        self.parse_and_record('GET')

    def do_POST(self):
        self.parse_and_record('POST')

    def do_DELETE(self):
        self.parse_and_record('DELETE')


class TestServerTestCase(unittest.TestCase):
    def setUp(self):
        self.server = TestHTTPServer()

    def tearDown(self):
        self.server.shutdown()

    def getClient(self):
        return KeyClient('foo', 'bar', url='http://%s:%s/' % (
                         self.server.server_name, self.server.server_port))


class UrlGenerationTestCase(TestServerTestCase):
    "Tests that validate 'auto-generated' URLs."
    def test_with_path_id(self):
        client = self.getClient()
        client.path.data.read('/the/file/path')
        self.server.assertMethod('GET')
        self.server.assertPath('/api/2.0/path/data/the/file/path')

    def test_with_int_id(self):
        client = self.getClient()
        client.access.user.read(42)
        self.server.assertMethod('GET')
        self.server.assertPath('/api/2.0/access/user/42')


class MethodTestCase(TestServerTestCase):
    "Tests the HTTP methods used by CRUD methods."
    def test_create_is_POST(self):
        client = self.getClient()
        client.user.create(username='bobafett', email='bobafett@kamino.edu')
        self.server.assertMethod('POST')

    def test_read_is_GET(self):
        client = self.getClient()
        client.user.read('bobafett')
        self.server.assertMethod('GET')

    def test_update_is_POST(self):
        client = self.getClient()
        client.user.update('bobafett', full_name='Boba Fett')
        self.server.assertMethod('POST')

    def test_delete_is_DELETE(self):
        client = self.getClient()
        client.user.delete('bobafett')
        self.server.assertMethod('DELETE')


if __name__ == '__main__':
    unittest.main()
