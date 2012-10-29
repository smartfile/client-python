#!/usr/bin/python

import os
import sys
import httplib
import base64
import simplejson
import hmac
import optparse
import datetime
import pprint
from urllib import urlencode
from urlparse import urlparse
from functools import wraps
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

# The default API url.
API_URL = 'https://app.smartfile.com/api/2/'
BLOCK_SIZE = 1024 ** 2
METHOD_SUCCESS_CODES = {
    'GET':      httplib.OK,
    'POST':     httplib.CREATED,
    'PUT':      httplib.OK,
    'DELETE':   httplib.NO_CONTENT,
}


def get_content_length(f):
    "Get length of the 'file', could be a string or file-like object."
    pos = 0
    if callable(getattr(f, 'tell', None)):
        pos = f.tell()
    if callable(getattr(f, 'fileno', None)):
        return max(0, os.fstat(f.fileno()).st_size - pos)
    if callable(getattr(f, '__len__', None)):
        return len(f)


def clonedocs(fromdoc):
    "Clones docstrings from another function."
    @wraps
    def wrapped(todoc):
        todoc.__doc__ = fromdoc.__doc__
    return wrapped


# A simple Exception class that to differentiate API errors from general
# Python errors.
class SmartFileException(Exception):
    pass


# A simple Exception class that can handle the HTTP status.
class SmartFileHttpException(SmartFileException):
    def __init__(self, status, message):
        super(SmartFileHttpException, self).__init__(message)
        self.status = status


class Client(object):
    "Base API client that performs HTTP communication."

    def __init__(self, key, password, url=API_URL):
        self.key = key
        self.password = password
        self.url = url

    def http_request(self, method, path=None, data={}, headers={}):
        method = method.upper()
        if method not in METHOD_SUCCESS_CODES:
            raise Exception('Invalid HTTP method %s' % method)
        # Create full URL
        url = self.url
        if path:
            url = os.path.join(url, path)
        if method == 'POST':
            url += '?format=json'
        else:
            data['format'] = 'json'
        # Don't modify the headers
        headers = headers.copy()
        raise SmartFileException(r.status_code, content)

    def serialize(self, data):
        return simplejson.dumps(data)

    def deserialize(self, data):
        return simplejson.loads(data)


class UserClient(Client):
    "API client for performing user operations."

    def list(self):
        "Lists users."
        return self.deserialize(self.http_request('GET'))

    def create(self, username, email=None, root=None, password=None):
        "Creates a user."
        self.http_request('PUT', path=username)

    def update(self, username, email=None, root=None, password=None):
        "Updates a user."
        self.http_request('POST', path=username)

    def delete(self, username):
        "Deletes a user."
        self.http_request('DELETE', path=username)


# Shortcut functions for user actions.


@clonedocs(UserClient.list)
def user_list(key, password, *args, **kwargs):
    return UserClient(key, password).list(*args, **kwargs)


@clonedocs(UserClient.create)
def user_create(key, password, *args, **kwargs):
    UserClient(key, password).create(*args, **kwargs)


@clonedocs(UserClient.update)
def user_update(key, password, *args, **kwargs):
    UserClient(key, password).update(*args, **kwargs)


@clonedocs(UserClient.delete)
def user_delete(key, password, *args, **kwargs):
    UserClient(key, password).delete(*args, **kwargs)


class TaskClient(Client):
    "API client for polling running tasks."
    def __init__(self):
        self.task = None

    def start(self, method, path, *args, **kwargs):
        if self.task:
            raise ValueError('Task already started')
        self.task = self.deserialize(self.http_request(method, path, *args, **kwargs))

    def status(self):
        if self.task:
            raise ValueError('Task should be started with start() before retrieving status')
        return self.deserialize(self.http_request('GET', 'task/%s/' % self.task.id))


class PathClient(Client):
    "API client for performing path operations."

    def list(self, path='/'):
        "Lists paths in given path."
        return self.deserialize(self.http_request('GET', path=path))

    def create(self, path):
        "Creates a directory."
        self.http_request('PUT', path=path)

    def delete(self, path):
        "Deletes a directory."
        task = self.deserialize(self.http_request('POST', path='oper/remove%s' % path))
        return Task(task)

    def upload(self, path, f, cb=None, bs=BLOCK_SIZE):
        "Uploads data to a path."
        opened = False
        if isinstance(f, basestring):
            opened, f = True, file(f, 'rb')
        try:
            # Perform the HTTP download. Call cb after each block, so the caller
            # can track progress.
            length = get_content_length(f)
        finally:
            if opened:
                f.close()
        return self.deserialize()

    def download(self, path, f):
        "Downloads data from a path."
        opened = False
        if isinstance(f, basestring):
            opened, f = True, file(f, 'wb')
        try:
            # Perform the HTTP upload. Call cb after each block, so the caller
            # can track progress.
            pass
        finally:
            if opened:
                f.close()


# Shortcut functions for path actions.


@clonedocs(PathClient.list)
def path_list(key, password, *args, **kwargs):
    return PathClient(key, password).list(*args, **kwargs)


@clonedocs(PathClient.create)
def path_create(key, password, *args, **kwargs):
    PathClient(key, password).create(*args, **kwargs)


@clonedocs(PathClient.delete)
def path_delete(key, password, *args, **kwargs):
    PathClient(key, password).delete(*args, **kwargs)


@clonedocs(PathClient.upload)
def path_upload(key, password, *args, **kwargs):
    PathClient(key, password).upload(*args, **kwargs)


@clonedocs(PathClient.download)
def path_download(key, password, *args, **kwargs):
    PathClient(key, password).download(*args, **kwargs)


# A CLI tool for interacting with the API.


def main():
    def prompt(name, allow_none=True):
        "Prompt the user for a value, if they hit enter, return None."
        prompt = 'Please enter a %s' % name
        if allow_none:
            prompt += ', or <enter> to skip'
        prompt += ': '
        value = raw_input(prompt)
        if value == '':
            value = None
        return value


    def make_progress(direction):
        @wraps
        def wrapped(total, complete):
            percent = complete / total * 100
            print direction, '%s%%' % percent
        return wrapped


    parser = optparse.OptionParser(prog="smartfile", description="SmartFile API client and sample program.")
    parser.add_option("-u", "--api-url", help="Specify the API url, if omitted, the default is used.")
    parser.add_option("-k", "--api-key", help="API key to use for call.")
    parser.add_option("-p", "--api-password", help="API password to use for call.")
    parser.add_option("-d", "--debug", action='store_true', help="Enable debugging.")

    parser.add_option('-N', '--user-create', help='Create a new user.')
    parser.add_option('-S', '--user-update', help='Update a user.')
    parser.add_option('-X', '--user-delete', help='Delete a user.')
    parser.add_option('-e', '--user-email', help='Email address for creating/updating a user.')
    parser.add_option('-f', '--user-fullname', help='Full name for creating/updating a user.')
    parser.add_option('-A', '--user-password', help='Password for creating/updating a user.')

    parser.add_option('-U', '--file-upload', help='Upload a file to SmartFile.')
    parser.add_option('-D', '--file-download', help='Download a file from SmartFile.')
    parser.add_option('-E', '--file-delete', help='Delete a file from SmartFile')
    parser.add_option('-P', '--file-path', help='The local path for uploading/downloading. Use - for stdin, stdout. '
                                           'Only needed if path is different than the remote path.')

    (options, args) = parser.parse_args()

    if options.api_url:
        api_url = options.api_url
    else:
        api_url = os.environ.get('SMARTFILE_API_URL', API_URL)

    if options.api_key:
        api_key = options.api_key
    else:
        api_key = os.environ.get('SMARTFILE_API_KEY', None)
    if not api_key:
        parser.error('You must provide an API key, use the --api-key argument or SMARTFILE_API_KEY environment variable.')

    if options.api_password:
        api_password = options.api_password
    else:
        api_password = os.environ.get('SMARTFILE_API_PASSWORD', None)
    if not api_password:
        parser.error('You must provide an API password, use the --api-password argument or SMARTFILE_API_PASSWORD environment variable.')

    if options.user_create or options.user_update:
        if options.user_create:
            username = options.user_create
        else:
            username = options.user_update
        kwargs = {
            'username': username,
        }
        if options.user_fullname:
            kwargs['fullname'] = options.user_fullname
        if options.user_email:
            kwargs['email'] = options.user_email
        if options.user_password:
            kwargs['password'] = options.user_password
        c = UserClient(api_key, api_password, url=api_url)
        if options.user_create:
            c.create(**kwargs)
        else:
            c.update(**kwargs)

    if options.user_delete:
        UserClient(api_key, api_password, url=api_url).delete(options.user_delete)

    if options.file_upload:
        if not options.file_path:
            f = options.file_upload
        elif options.path == '-':
            # TODO, need to read this in, so we can determine
            # the length (Content-Length).
            f = sys.stdin
        else:
            f = options.file_path
        PathClient(api_key, api_password, url=api_url).upload(options.upload, f, cb=make_progress('Upload'))

    if options.file_download:
        if not options.file_path:
            f = options.file_download
        elif options.path == '-':
            opened, f = False, sys.stdout
        else:
            f = options.file_path
        PathClient(api_key, api_password, url=api_url).download(options.download, f, cb=make_progress('Download'))

    if options.file_delete:
        PathClient(api_key, api_password, url=api_url).delete(options.delete)

    pprint.pprint(r)


if __name__ == '__main__':
    # Start things off in main()
    main()
