#!/usr/bin/python

import httplib, urllib, urlparse, base64, simplejson

# These constants are needed to access the API.
API_URL = 'http://app.smartfile.com/api/1'
API_KEY = 'api-key'
API_PWD = 'api-password'

# A simple Exception class that can handle the HTTP
# status.
class SmartFileException(Exception):
    def __init__(self, status, message):
        super(SmartFileException, self).__init__(message)
        self.status = status

# This function does the bulk of the work by performing
# the HTTP request and raising an exception for any HTTP
# status code that does not signify success for the operation.
def http_request(uri, data, method):
    url = '%s%s' % (API_URL, uri)
    url_parts = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(url_parts.netloc)
    conn.putrequest(method, url_parts.path)
    conn.connect()
    conn.putheader('Content-Type', 'application/x-www-form-urlencoded')
    conn.putheader('User-Agent', 'Python SmartFile API Sample Client')
    auth = base64.encodestring('%s:%s' % (API_KEY, API_PWD)).strip()
    conn.putheader('Authorization', 'Basic %s' % auth)
    if method == 'POST':
        payload_length = 0
        payload = []
        for key, value in data.items():
            item = '%s=%s' % (key, urllib.quote(value))
            payload.append(item)
            payload_length += len(item)
        # account for & between items.
        payload_length += len(payload) - 1
        conn.putheader('Content-Length', payload_length)
        conn.endheaders()
        conn.send('&'.join(payload))
    else:
        conn.endheaders()
    resp = conn.getresponse()

    if (method == 'GET' and resp.status == 200) or \
        (method == 'POST' and resp.status == 201) or \
        (method == 'PUT' and resp.status == 200) or \
        (method == 'DELETE' and resp.status == 204):
        return
    message = resp.read()
    try:
        json = simplejson.loads(message)
        message = json.get('message')
    except:
        pass
    raise SmartFileException(resp.status, message)

# This function makes the User add API call. It uses the http_request
# function to handle the transport. Additional API calls could be supported
# simply by writing additional wrappers that create the data dict and
# use http_request to do the grunt work.
def create_user(fullname, username, password, email):
    data = {
        'name':         fullname,
        'username':     username,
        'password':     password,
        'email':        email,
    }
    http_request('/users/add/', data, 'POST')

# This function makes the User add API call. It uses the http_request
# function to handle the transport. Additional API calls could be supported
# simply by writing additional wrappers that create the data dict and
# use http_request to do the grunt work.
def delete_user(username):
    http_request('/users/delete/{0}/'.format(username), {}, 'DELETE')

def main():
    # Ask the user for the required parameters. These will be
    # passed to the API via an HTTP POST request.
    fullname = raw_input("Please enter a full name: ")
    username = raw_input("Please enter a username: ")
    password = raw_input("Please enter a password: ")
    email = raw_input("Please enter an email address: ")
    try:
        # Try to create the new user...
        create_user(fullname, username, password, email)
        print 'Successfully created user %s.' % username
    except Exception, e:
        # Print the error message from the server on failure.
        print 'Error creating user %s: %s' % (username, str(e))

if __name__ == '__main__':
    # Start things off in main()
    main()
