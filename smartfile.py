#!/usr/bin/python

import requests, optparse, datetime, pprint
import httplib, urllib, urlparse, base64, simplejson, simplexml, hmac
try:
    from hashlib.sha import sha
except ImportError:
    from sha import new as sha

# The default API url.
API_URL = 'http://app.smartfile.com/api/1'

FORMATS = {
    'json': ('application/json', simplejson.dumps, simplejson.loads),
    'xml': ('text/xml', simplexml.dumps, simplexml.loads),
}

METHOD_SUCCESS_CODES = {
    'GET':      200,
    'POST':     201,
    'PUT':      200,
    'DELETE':   204,
}

# A simple Exception class that can handle the HTTP
# status.
class SmartFileException(Exception):
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
            'name':         fullname,
            'username':     username,
            'password':     password,
            'email':        email,
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
            self.mime, self.serialize, self.deserialize = FORMATS.get(format)
        except KeyError:
            raise Exception('Invalid data format %s' % format)
        self.format = format
        self.user = UserClient(self)

    def http_request(self, method, uri, data=None, headers=None):
        # Find the requests library function for this HTTP method.
        request = getattr(requests, method.lower(), None)
        if not callable(request):
            raise ("Invalid method")
        headers = headers or {}
        data = data or {}
        url = self.url + uri
        # Sign the outbound request.
        mac = hmac.new(self.password, '%s %s\n' % (method.upper(), url), sha)
        mac.update('%s\n' % headers.setdefault('Content-Type', 'application/x-www-form-urlencoded'))
        mac.update('%s\n' % headers.setdefault('Date', datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')))
        for key in sorted(data.keys()):
            mac.update('%s=%s\n' % (key, data.get(key)))
        sig = base64.b64encode(mac.digest())
        headers['Authorization'] = 'SmartFile %s: %s' % (self.key, sig)
        # tell the server what encoding we desire.
        headers['Accepts'] = self.format
        data = self.serialize(data)
        # Perform the request.
        r = request(url, data=data, headers=headers)
        # Try to deserialize the response
        content = r.content
        try:
            content = self.deserialize(content)
        except:
            pass
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
    parser.add_option("-d", "--debug", action='store_true', help="API password to use for call.")

    (options, args) = parser.parse_args()

    if not options.key:
        parser.error('You must provide an API key.')
    if not options.password:
        parser.error('You must provide an API password.')

    if options.debug:
        import pdb; pdb.set_trace()

    c = Client(options.url, options.key, options.password)

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
