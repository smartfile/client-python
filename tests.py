# -*- coding: utf-8 -*-

import os
import filecmp
import urlparse
import unittest
import threading

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from smartfile import API
from smartfile.exceptions import SmartFileResponseException


class MockHTTPServer(threading.Thread, HTTPServer):
    allow_reuse_address = True

    def __init__(self, handler, address='127.0.0.1', port=10080):
        HTTPServer.__init__(self, (address, port), handler)
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def run(self):
        self.serve_forever()


class MockHTTPRequestHandler(BaseHTTPRequestHandler):
    class MockRequest(object):
        def __init__(self, method, path, query=None, data=None):
            self.method = method
            self.path = path
            self.query = query
            self.data = data

    def __init__(self, *args, **kwargs):
        super(MockHTTPRequestHandler, self).__init__(*args, **kwargs)
        self.requests = []

    def record(self, method, path, query=None, data=None):
        self.requests.append(MockHTTPRequestHandler.MockRequest(method, path,
                             query=query, data=data))

    def clear(self):
        del self.requests[:]

    def parse_and_record(self, method):
        urlp = urlparse.urlparse(self.path)
        query, data = urlparse.parse_qs(urlp.query), None
        if method == 'POST':
            l = int(self.headers['Content-Length'])
            data = urlparse.parse_qs(self.rfile.read(l))
        self.record(method, urlp.path, query=query, data=data)
        return query, data

    def do_GET(self):
        query, post = self.parse_and_record('GET')
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("Hello World!")


class MockServerTestCase(unittest.TestCase):
    class TestHandler(MockHTTPRequestHandler):
        pass

    def setUp(self):
        self.server = MockHTTPServer(self.TestHandler)

    def tearDown(self):
        self.server.shutdown()

    def getClient(self):
        return API.KeyClient(url='http://%s:%s/' % (self.server.server_name,
                             self.server.server_port))


class URLGenerationTestCase(MockServerTestCase):
    "Tests that validate 'auto-generated' URLs."
    def test_with_path(self):
        client = self.getClient()
        client.path.data.get('/the/file/path')
        r = self.server.requests
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].method, 'GET')
        self.assertEqual(r[0].path, '/path/data/the/file/path')
