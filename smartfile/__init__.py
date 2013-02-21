import re
import os
import requests
import time
import urllib
import urlparse

from requests.exceptions import RequestException

from smartfile.errors import APIError
from smartfile.errors import RequestError
from smartfile.errors import ResponseError


API_URL = 'https://app.smartfile.com/'
API_VER = '2.0'

THROTTLE = re.compile('^.*; next=([\d\.]+) sec$')
HTTP_USER_AGENT = 'SmartFile Python API client v1.0'


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
        while not isinstance(obj, Client):
            path.append(obj.name)
            obj = obj.parent
        if id:
            path.append(id)
        # obj is now our API client. path contains all the names (url
        # fragments).
        obj._request(method, path, **kwargs)

    def create(self, **kwargs):
        self._request('post', data=kwargs)

    def read(self, id, **kwargs):
        self._request('get', id=id, data=kwargs)

    def update(self, id, **kwargs):
        self._request('post', id=id, data=kwargs)

    def delete(self, id, **kwargs):
        self._request('delete', id=id, data=kwargs)


class Client(Endpoint):
    """Base API client, handles communication, retry, versioning etc."""
    def __init__(self, url=API_URL, version=API_VER, throttle_wait=True):
        self.url = url
        self.version = version
        self.throttle_wait = throttle_wait

    def _do_request(self, request, url, **kwargs):
        "Actually makes the HTTP request."
        kwargs.setdefault('headers', {}).setdefault('User-Agent', HTTP_USER_AGENT)
        try:
            response = request(url, **kwargs)
        except RequestException, e:
            raise RequestError(e)
        else:
            if response.status_code >= 400:
                raise ResponseError(response)
        return response

    def _request(self, method, path, **kwargs):
        "Handles retrying failed requests and error handling."
        request = getattr(requests, method, None)
        if not callable(request):
            raise RequestError('Invalid method %s' % method)
        # Join fragments into a URL
        fragments = [self.url, 'api', self.version] + path
        url = '/'.join(fragments)
        if not url.endswith('/'):
            url += '/'
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
                    m = THROTTLE.match(e.response.headers['x-throttle'])
                    if m:
                        time.sleep(float(m.group(1)))
                        continue
                # Failed for a reason other than throttling.
                raise


class KeyClient(Client):
    """API client that uses a key and password. Layers a simple form of
    authentication on the base Client."""
    def __init__(self, key=None, password=None, **kwargs):
        if key is None:
            key = os.environ.get('SMARTFILE_API_KEY')
        if password is None:
            password = os.environ.get('SMARTFILE_API_PASSWORD')
        if key is None or password is None:
            raise APIError('Please provide an API key and password. Use '
                           'arguments or environment variables.')
        self.key = key
        self.password = password
        super(KeyClient, self).__init__(**kwargs)

    def _request(self, *args, **kwargs):
        # Add the token authentication
        kwargs['auth'] = (self.key, self.password)
        return super(KeyClient, self)._request(*args, **kwargs)


try:
    from requests_oauthlib import OAuth1
    from oauthlib.oauth1 import SIGNATURE_PLAINTEXT

    #*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~
    #                OAuth, if available.
    #*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~

    class OAuthToken(object):
        "Internal representation of an OAuth (token, secret) tuple."
        def __init__(self, token, secret):
            self.token = unicode(token)
            self.secret = unicode(secret)

        def __iter__(self):
            yield self.token
            yield self.secret
            raise StopIteration()

        def __getitem__(self, index):
            return (self.token, self.secret)[index]

    class OAuthClient(Client):
        """API client that uses OAuth tokens. Layers a more complex form of
        authentication useful for 3rd party access on top of the base Client."""
        def __init__(self, client_token=None, client_secret=None, access_token=None,
                     access_secret=None, **kwargs):
            if client_token is None:
                client_token = os.environ.get('SMARTFILE_CLIENT_TOKEN')
            if client_secret is None:
                client_secret = os.environ.get('SMARTFILE_CLIENT_SECRET')
            if not client_token or not client_secret:
                raise APIError('You must provide a client_token and client_secret '
                               'for OAuth.')
            if access_token is None:
                access_token = os.environ.get('SMARTFILE_ACCESS_TOKEN')
            if access_secret is None:
                access_secret = os.environ.get('SMARTFILE_ACCESS_SECRET')
            self.client = OAuthToken(client_token, client_secret)
            if access_token and access_secret:
                self.access = OAuthToken(access_token, access_secret)
            else:
                self.access = None
            super(OAuthClient, self).__init__(**kwargs)

        def _request(self, method, path, id, **kwargs):
            if self.access is None:
                raise APIError('You must obtain an access token before making API '
                               'calls.')
            # Add the OAuth parameters.
            kwargs['auth'] = OAuth1(self.client.token,
                                    client_secret=self.client.secret,
                                    resource_owner_key=self.access.token,
                                    resource_owner_secret=self.access.secret,
                                    signature_method=SIGNATURE_PLAINTEXT)
            return super(OAuthClient, self)._request(method, path, id, **kwargs)

        def get_request_token(self, callback=None):
            "The first step of the OAuth workflow."
            if callback:
                callback = unicode(callback)
            oauth = OAuth1(self.client.token, client_secret=self.client.secret,
                           callback_uri=callback,
                           signature_method=SIGNATURE_PLAINTEXT)
            r = requests.post(urlparse.urljoin(self.url, 'oauth/request_token/'), auth=oauth)
            credentials = urlparse.parse_qs(r.text)
            return OAuthToken(credentials.get('oauth_token')[0],
                              credentials.get('oauth_token_secret')[0])

        def get_authorization_url(self, request):
            "The second step of the OAuth workflow."
            url = urlparse.urljoin(self.url, 'oauth/authorize/')
            return url + '?' + urllib.urlencode(dict(oauth_token=request.token))

        def get_access_token(self, request, verifier=None):
            """The final step of the OAuth workflow. After this the client can make
            API calls."""
            if verifier:
                verifier = unicode(verifier)
            oauth = OAuth1(self.client.token, client_secret=self.client.secret,
                           resource_owner_key=request.token,
                           resource_owner_secret=request.secret,
                           verifier=unicode(verifier),
                           signature_method=SIGNATURE_PLAINTEXT)
            r = requests.post(urlparse.urljoin(self.url, 'oauth/access_token/'), auth=oauth)
            credentials = urlparse.parse_qs(r.text)
            self.access = OAuthToken(credentials.get('oauth_token')[0],
                                     credentials.get('oauth_token_secret')[0])


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
