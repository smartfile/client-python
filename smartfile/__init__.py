import re
import os
import requests
import time
import urllib
import urlparse

from netrc import netrc

from requests.exceptions import RequestException

from smartfile.errors import APIError
from smartfile.errors import RequestError
from smartfile.errors import ResponseError


API_URL = 'https://app.smartfile.com/'
API_VER = '2.0'

THROTTLE = re.compile('^.*; next=([\d\.]+) sec$')
HTTP_USER_AGENT = 'SmartFile Python API client v1.0'


def is_valid_token(value):
    "Validates a Basic or OAuth authentication token."
    if not value:
        return False
    if len(value) != 30:
        return False
    if not isinstance(value, unicode):
        return False
    return True


class Endpoint(object):
    """A placeholder that remembers the namespace the user accesses."""
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

    def __getattr__(self, name):
        return Endpoint(self, name)

    def _request(self, method, id=None, **kwargs):
        """Assembles the path, locates the API client on the endpoint stack,
        and asks it to make the API call."""
        path, obj = [], self
        # Walk down the stack until we encounter the Client instance, this is
        # located at the bottom.
        while not isinstance(obj, Client):
            # Insert each "name" from the stack into our path. This will
            # preserve their order (insert vs. append).
            path.insert(0, obj.name)
            # grab the next item on the stack, then iterate.
            obj = obj.parent
        # If we received an ID, append it to the path.
        if id:
            path.append(str(id))
        # obj is now our API client. path contains all the names (url
        # fragments) and the optional ID.
        return obj._request(method, path, **kwargs)

#    def post(self, **kwargs):
#        return self._request('post', data=kwargs)

    def __call__(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get(self, id=None, **kwargs):
        return self._request('get', id=id, data=kwargs)

    def put(self, id=None, **kwargs):
        return self._request('put', id=id, data=kwargs)

    def post(self, id=None, **kwargs):
        return self._request('post', id=id, data=kwargs)

    def delete(self, id=None, **kwargs):
        return self._request('delete', id=id, data=kwargs)


class Client(Endpoint):
    """Base API client, handles communication, retry, versioning etc."""
    def __init__(self, url=None, version=API_VER, throttle_wait=True):
        if url is None:
            url = os.environ.get('SMARTFILE_API_URL')
        if url is None:
            url = API_URL
        self.url = url
        self.version = version
        self.throttle_wait = throttle_wait

    def _do_request(self, request, url, **kwargs):
        "Actually makes the HTTP request."
        kwargs.setdefault('headers', {}).setdefault('User-Agent', HTTP_USER_AGENT)
        try:
            response = request(url, stream=True, **kwargs)
        except RequestException, e:
            raise RequestError(e)
        else:
            if response.status_code >= 400:
                raise ResponseError(response)
        # Try to return the response in the most useful fashion given it's type.
        if response.headers.get('content-type') == 'application/json':
            try:
                # Try to decode as JSON
                return response.json()
            except ValueError:
                # If that fails, return the text.
                return response.text
        else:
            # This might be a file, so return it.
            return response.raw

    def _request(self, method, path, **kwargs):
        "Handles retrying failed requests and error handling."
        request = getattr(requests, method, None)
        if not callable(request):
            raise RequestError('Invalid method %s' % method)
        # Find files, separate them out to correct kwarg for requests.
        data, files = kwargs.get('data'), {}
        for name, value in data.items():
            if hasattr(value, 'read'):
                files[name] = data.pop(name)
        if files:
            kwargs.setdefault('files', {}).update(files)
        # Join fragments into a URL
        path = ['api', self.version] + path
        path = '/'.join(path)
        if not path.endswith('/'):
            path += '/'
        while '//' in path:
            path = path.replace('//', '/')
        url = self.url + path
        # Now try the request, if we get throttled, sleep and try again.
        trys, retrys = 0, 3
        while True:
            if trys == retrys:
                raise RequestError('Could not complete request after %s trys.' % trys)
            trys += 1
            try:
                return self._do_request(request, url, **kwargs)
            except ResponseError, e:
                if self.throttle_wait and e.status_code == 503:
                    m = THROTTLE.match(e.response.headers.get('x-throttle', ''))
                    if m:
                        time.sleep(float(m.group(1)))
                        continue
                # Failed for a reason other than throttling.
                raise


class BasicClient(Client):
    """API client that uses a key and password. Layers a simple form of
    authentication on the base Client."""
    def __init__(self, key=None, password=None, **kwargs):
        netrcfile = kwargs.pop('netrcfile', None)
        super(BasicClient, self).__init__(**kwargs)
        if key is None:
            key = os.environ.get('SMARTFILE_API_KEY')
        if password is None:
            password = os.environ.get('SMARTFILE_API_PASSWORD')
        if key is None or password is None:
            try:
                rc = netrc(netrcfile)
            except:
                pass
            else:
                urlp = urlparse.urlparse(self.url)
                auth = rc.authenticators(urlp.netloc)
                if not auth is None:
                    if key is None:
                        key = auth[0]
                    if key is None:
                        key = auth[1]
                    if password is None:
                        password = auth[2]
        if not key is None:
            key = unicode(key)
        if not password is None:
            password = unicode(password)
        if not is_valid_token(key) or not is_valid_token(password):
            raise APIError('Please provide an API key and password. Use '
                           'arguments or environment variables.')
        self.key = key
        self.password = password

    def _request(self, *args, **kwargs):
        # Add the token authentication
        kwargs['auth'] = (self.key, self.password)
        return super(BasicClient, self)._request(*args, **kwargs)


try:
    from requests_oauthlib import OAuth1
    from oauthlib.oauth1 import SIGNATURE_PLAINTEXT

    #*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~
    #                OAuth, if available.
    #*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~

    class OAuthToken(object):
        "Internal representation of an OAuth (token, secret) tuple."
        def __init__(self, token=None, secret=None):
            if not token is None:
                token = unicode(token)
            self.token = token
            if not secret is None:
                secret = unicode(secret)
            self.secret = secret

        def __iter__(self):
            yield self.token
            yield self.secret
            raise StopIteration()

        def __getitem__(self, index):
            return (self.token, self.secret)[index]

        def is_valid(self):
            return (is_valid_token(self.token) and
                    is_valid_token(self.secret))

    class OAuthClient(Client):
        """API client that uses OAuth tokens. Layers a more complex form of
        authentication useful for 3rd party access on top of the base Client."""
        def __init__(self, client_token=None, client_secret=None, access_token=None,
                     access_secret=None, **kwargs):
            if client_token is None:
                client_token = os.environ.get('SMARTFILE_CLIENT_TOKEN')
            if client_secret is None:
                client_secret = os.environ.get('SMARTFILE_CLIENT_SECRET')
            if access_token is None:
                access_token = os.environ.get('SMARTFILE_ACCESS_TOKEN')
            if access_secret is None:
                access_secret = os.environ.get('SMARTFILE_ACCESS_SECRET')
            self.__client = OAuthToken(client_token, client_secret)
            if not self.__client.is_valid():
                raise APIError('You must provide a client_token and client_secret '
                               'for OAuth.')
            self.__access = OAuthToken(access_token, access_secret)
            super(OAuthClient, self).__init__(**kwargs)

        def _request(self, *args, **kwargs):
            if not self.__access.is_valid():
                raise APIError('You must obtain an access token before making API '
                               'calls.')
            # Add the OAuth parameters.
            kwargs['auth'] = OAuth1(self.__client.token,
                                    client_secret=self.__client.secret,
                                    resource_owner_key=self.__access.token,
                                    resource_owner_secret=self.__access.secret,
                                    signature_method=SIGNATURE_PLAINTEXT)
            return super(OAuthClient, self)._request(*args, **kwargs)

        def get_request_token(self, callback=None):
            "The first step of the OAuth workflow."
            if callback:
                callback = unicode(callback)
            oauth = OAuth1(self.__client.token,
                           client_secret=self.__client.secret,
                           callback_uri=callback,
                           signature_method=SIGNATURE_PLAINTEXT)
            r = requests.post(urlparse.urljoin(self.url, 'oauth/request_token/'), auth=oauth)
            credentials = urlparse.parse_qs(r.text)
            self.__request = OAuthToken(credentials.get('oauth_token')[0],
                                        credentials.get('oauth_token_secret')[0])
            return self.__request

        def get_authorization_url(self, request=None):
            "The second step of the OAuth workflow."
            if request is None:
                if not self.__request.is_valid():
                    raise APIError('You must obtain a request token to request '
                                   'and access token. Use get_request_token() '
                                   'first.')
                request = self.__request
            url = urlparse.urljoin(self.url, 'oauth/authorize/')
            return url + '?' + urllib.urlencode(dict(oauth_token=request.token))

        def get_access_token(self, request=None, verifier=None):
            """The final step of the OAuth workflow. After this the client can make
            API calls."""
            if verifier:
                verifier = unicode(verifier)
            if request is None:
                if not self.__request.is_valid():
                    raise APIError('You must obtain a request token to request '
                                   'and access token. Use get_request_token() '
                                   'first.')
                request = self.__request
            oauth = OAuth1(self.__client.token,
                           client_secret=self.__client.secret,
                           resource_owner_key=request.token,
                           resource_owner_secret=request.secret,
                           verifier=unicode(verifier),
                           signature_method=SIGNATURE_PLAINTEXT)
            r = requests.post(urlparse.urljoin(self.url, 'oauth/access_token/'), auth=oauth)
            credentials = urlparse.parse_qs(r.text)
            self.__access = OAuthToken(credentials.get('oauth_token')[0],
                                     credentials.get('oauth_token_secret')[0])
            return self.__access


except ImportError:
    #*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~
    #              OAuth, if not available.
    #*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~

    # Instead of a class, define this as a function, thus when a user tries to
    # "instantiate" it, they receive an exception.
    def OAuthClient(*args, **kwargs):
        raise NotImplementedError('You must install oauthlib and '
                                  'requests_oauthlib to use the OAuthClient. '
                                  'Try "pip install requests_oauthlib" to '
                                  'install both.')
