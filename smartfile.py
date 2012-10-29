#!/usr/bin/python

import base64
import datetime
import hmac
import httplib
import optparse
import pprint
import requests
import simplejson
import simplexml

from urlparse import urlparse
from urllib import urlencode
try:
    from hashlib.sha import sha
    from hashlib.md5 import md5
except ImportError:
    from sha import new as sha
    from md5 import new as md5
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

# The default API url.
API_URL = 'http://app.smartfile.com/api/1'

FORMATS = {
    'json': ('application/json', simplejson.dumps, simplejson.loads),
    'xml': ('application/xml', simplexml.dumps, simplexml.loads),
}

METHOD_SUCCESS_CODES = {
    'GET': httplib.OK,
    'POST': httplib.CREATED,
    'PUT': httplib.OK,
    'DELETE': httplib.NO_CONTENT,
}


class SmartFileException(Exception):
    """ A simple Exception class that can handle the HTTP status. """
    def __init__(self, status, message):
        super(SmartFileException, self).__init__(message)
        self.status = status


class UserClient(object):
    uri = '/user/'

    def __init__(self, client):
        self.client = client

    def schema(self):
        return self.client.http_request('GET', self.uri + 'schema/')

    def create(self, username, fullname, password, email, **kwargs):
        data = {
            'name': fullname,
            'username': username,
            'password': password,
            'email': email,
        }
        data.update(kwargs)
        self.client.http_request('POST', self.uri + username, data)

    def delete(self, username):
        self.client.http_request('DELETE', self.uri + username)


class Client(object):
    def __init__(self, url, key, password, format='json'):
        self.url = url
        self.key = key
        self.password = password
        try:
            self.mime_type, self.serialize, self.deserialize = FORMATS.get(format)
        except KeyError:
            raise Exception('Invalid data format %s' % format)
        self.format = format
        self.user = UserClient(self)

    def http_request(self, method, uri, data={}, headers={}):
        request = getattr(requests, method.lower(), None)
        if request is None:
            raise Exception('Invalid HTTP method %s' % method)
        # Create full URL
        url = self.url + uri
        # Don't modify the headers
        headers = headers.copy()
        if method != 'GET':
            data = self.serialize(data)
            # Calculate MD5 sum for content of request.
            content_md5 = base64.b64encode(md5(data).digest())
        else:
            content_md5 = ''
        url_parts = urlparse(url)
        # Sign the outbound request.
        mac = hmac.new(self.password, '%s %s\n' % (method.upper(), url_parts.path), sha)
        mac.update('%s\n' % headers.setdefault('Content-MD5', content_md5))
        mac.update('%s\n' % headers.setdefault('Content-Type', self.mime_type))
        mac.update('%s\n' % headers.setdefault('Date', datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')))
        namevalues = []
        # Extract querystring values from url (if any).
        if url_parts.query:
            qs = parse_qs(url_parts.query)
            for key, values in qs.items():
                for value in values:
                    namevalues.append('%s=%s\n' % (key, value))
        # For a GET request, data will be passed via the querystring.
        if method == 'GET':
            for key, value in data.items():
                namevalues.append('%s=%s\n' % (key, value))
            data = urlencode(data)
        # If there are any querystring values, sign them.
        if namevalues:
            map(mac.update, sorted(namevalues))
        else:
            # Otherwise sign a blank line where querystring data would be.
            mac.update('\n')
        sig = base64.b64encode(mac.digest())
        headers.update({
            # Authorization header to authenticate to the API.
            'Authorization': 'SmartFile %s: %s' % (self.key, sig),
            # tell the server what encoding we desire.
            'Accept': self.mime_type,
        })
        # Perform the request.
        r = request(url, data=data, headers=headers)
        # Try to deserialize the response
        content = self.deserialize(r.content)
        # Each HTTP method indicates success differently.
        if r.status_code == METHOD_SUCCESS_CODES.get(method.upper()):
            return content
        # The request was unsuccessful, raise an exception with
        # the error message provided.
        try:
            content = content.get('message', content)
        except AttributeError:
            pass
        raise SmartFileException(r.status_code, content)


# This function makes the User add API call. It uses the http_request
# function to handle the transport. Additional API calls could be supported
# simply by writing additional wrappers that create the data dict and
# use http_request to do the grunt work.
def delete_user(username):
    http_request('/users/delete/{0}/'.format(username), {}, 'DELETE')


def main():
    parser = optparse.OptionParser(prog="smartfile", description="SmartFile API client and sample program.")
    parser.add_option("-u", "--url", help="API url to use for call.", default=API_URL)
    parser.add_option("-k", "--key", help="API key to use for call.")
    parser.add_option("-p", "--password", help="API password to use for call.")
    parser.add_option("-f", "--format", help="Data serialization format.", default='json')
    parser.add_option("-d", "--debug", action='store_true', help="API password to use for call.")

    (options, args) = parser.parse_args()

    if not options.key:
        parser.error('You must provide an API key.')
    if not options.password:
        parser.error('You must provide an API password.')

    if options.debug:
        import pdb; pdb.set_trace()

    c = Client(options.url, options.key, options.password, format=options.format)

    pprint.pprint(c.user.schema())

    # Ask the user for the required parameters. These will be
    # passed to the API via an HTTP POST request.
    #fullname = raw_input("Please enter a full name: ")
    #username = raw_input("Please enter a username: ")
    #password = raw_input("Please enter a password: ")
    #email = raw_input("Please enter an email address: ")
    #c.user.create(username, fullname, password, email)

if __name__ == '__main__':
    # Start things off in main()
    main()
