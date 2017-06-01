import os
import re
import shutil
import time
import urllib

from netrc import netrc
try:
    import urlparse
    # Fixed pyflakes warning...
    urlparse
except ImportError:
    from urllib import parse as urlparse

import requests
from requests.exceptions import RequestException

from smartfile.errors import APIError
from smartfile.errors import RequestError
from smartfile.errors import ResponseError


__version__ = '2.19'
__major__ = __version__.split('.')[0]

API_URL = 'https://app.smartfile.com/'

THROTTLE_PATTERN = re.compile('^.*; next=([\d\.]+) sec$')
HTTP_USER_AGENT = 'SmartFile Python API client v{0}'.format(__version__)


def clean_tokens(*args):
    if not all(map(bool, args)):
        raise ValueError("not provided")
    args = list(map(lambda x: x.strip(), args))
    for i, arg in enumerate(args):
        if len(arg) < 30:
            raise ValueError("too short")
        args[i] = arg
    return args


class Client(object):
    """Base API client, handles communication, retry, versioning etc."""
    def __init__(self, url=None, version=__major__, throttle_wait=True):
        self.url = url or os.environ.get('SMARTFILE_API_URL') or API_URL
        self.version = version
        self.throttle_wait = throttle_wait

    def _do_request(self, request, url, **kwargs):
        "Actually makes the HTTP request."
        try:
            response = request(url, stream=True, **kwargs)
        except RequestException as e:
            raise RequestError(e)
        else:
            if response.status_code >= 400:
                raise ResponseError(response)
        # Try to return the response in the most useful fashion given it's
        # type.
        if response.headers.get('content-type') == 'application/json':
            try:
                # Try to decode as JSON
                return response.json()
            except (TypeError, ValueError):
                # If that fails, return the text.
                return response.text
        else:
            # This might be a file, so return it.
            return response.raw

    def _request(self, method, endpoint, id=None, **kwargs):
        "Handles retrying failed requests and error handling."
        request = getattr(requests, method, None)
        if not callable(request):
            raise RequestError('Invalid method %s' % method)
        # Find files, separate them out to correct kwarg for requests.
        data = kwargs.get('data')
        if data:
            files = {}
            for name, value in list(data.items()):
                # Value might be a file-like object (with a read method), or it
                # might be a (filename, file-like) tuple.
                if hasattr(value, 'read') or isinstance(value, tuple):
                    files[name] = data.pop(name)
            if files:
                kwargs.setdefault('files', {}).update(files)
        path = ['api', self.version, endpoint]
        # If we received an ID, append it to the path.
        if id:
            path.append(str(id))
        # Join fragments into a URL
        path = '/'.join(path)
        if not path.endswith('/'):
            path += '/'
        while '//' in path:
            path = path.replace('//', '/')
        url = self.url + path
        # Add our user agent.
        kwargs.setdefault('headers', {}).setdefault('User-Agent',
                                                    HTTP_USER_AGENT)
        # Now try the request, if we get throttled, sleep and try again.
        trys, retrys = 0, 3
        while True:
            if trys == retrys:
                raise RequestError('Could not complete request after %s trys.'
                                   % trys)
            trys += 1
            try:
                return self._do_request(request, url, **kwargs)
            except ResponseError as e:
                if self.throttle_wait and e.status_code == 503:
                    m = THROTTLE_PATTERN.match(
                        e.response.headers.get('x-throttle', ''))
                    if m:
                        time.sleep(float(m.group(1)))
                        continue
                # Failed for a reason other than throttling.
                raise

    def __call__(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get(self, endpoint, id=None, **kwargs):
        return self._request('get', endpoint, id=id, params=kwargs)

    def put(self, endpoint, id=None, **kwargs):
        return self._request('put', endpoint, id=id, data=kwargs)

    def post(self, endpoint, id=None, **kwargs):
        return self._request('post', endpoint, id=id, data=kwargs)

    def delete(self, endpoint, id=None, **kwargs):
        return self._request('delete', endpoint, id=id, data=kwargs)

    def remove(self, deletefile):
        try:
            return self.post('/path/oper/remove', path=deletefile)
        except KeyError:
            raise Exception("Destination file does not exist")

    def upload(self, filename, fileobj):
        if filename.endswith('/'):
            filename = filename[:-1]
        arg = (filename, fileobj)
        return self.post('/path/data/', file=arg)

    def download(self, file_to_be_downloaded):
        """ file_to_be_downloaded is a file-like object that has already
        been uploaded, you cannot download folders """
        # download uses shutil.copyfileobj to download, which copies
        # the data in chunks
        o = open(file_to_be_downloaded, 'wb')
        return shutil.copyfileobj(self.get('/path/data/',
                                  file_to_be_downloaded), o)

    def move(self, src_path, dst_path):
        # check destination folder for / at end
        if not src_path.endswith("/"):
            src_path = src_path + "/"
        # check destination folder for / at begining
        if not src_path.startswith("/"):
            src_path = "/" + src_path
        # check destination folder for / at end
        if not dst_path.endswith("/"):
            dst_path = dst_path + "/"
        # check destination folder for / at begining
        if not dst_path.startswith("/"):
            dst_path = "/" + dst_path
        return self.post('/path/oper/move/', src=src_path, dst=dst_path)


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
                if auth is not None:
                    if key is None:
                        key = auth[0]
                    if key is None:
                        key = auth[1]
                    if password is None:
                        password = auth[2]
        try:
            self.key, self.password = clean_tokens(key, password)
        except ValueError:
            raise APIError('Please provide an API key and password. Use '
                           'arguments or environment variables.')

    def _do_request(self, *args, **kwargs):
        # Add the token authentication
        kwargs['auth'] = (self.key, self.password)
        return super(BasicClient, self)._do_request(*args, **kwargs)


try:
    from requests_oauthlib import OAuth1
    from oauthlib.oauth1 import SIGNATURE_PLAINTEXT

    # OAuth, if available.

    class OAuthToken(object):
        "Internal representation of an OAuth (token, secret) tuple."
        def __init__(self, token=None, secret=None):
            self.token = token
            self.secret = secret

        def __iter__(self):
            yield self.token
            yield self.secret
            raise StopIteration()

        def __getitem__(self, index):
            return (self.token, self.secret)[index]

        def is_valid(self):
            try:
                clean_tokens(self.token, self.secret)
                return True
            except ValueError:
                return False

    class OAuthClient(Client):
        """API client that uses OAuth tokens. Layers a more complex
        form of authentication useful for 3rd party access on top of
        the base Client."""
        def __init__(self, client_token=None, client_secret=None,
                     access_token=None, access_secret=None, **kwargs):
            if client_token is None:
                client_token = os.environ.get('SMARTFILE_CLIENT_TOKEN')
            if client_secret is None:
                client_secret = os.environ.get('SMARTFILE_CLIENT_SECRET')
            if access_token is None:
                access_token = os.environ.get('SMARTFILE_ACCESS_TOKEN')
            if access_secret is None:
                access_secret = os.environ.get('SMARTFILE_ACCESS_SECRET')
            self._client = OAuthToken(client_token, client_secret)
            if not self._client.is_valid():
                raise APIError('You must provide a client_token'
                               'and client_secret for OAuth.')
            self._access = OAuthToken(access_token, access_secret)
            super(OAuthClient, self).__init__(**kwargs)

        def _do_request(self, *args, **kwargs):
            if not self._access.is_valid():
                raise APIError('You must obtain an access token'
                               'before making API calls.')
            # Add the OAuth parameters.
            kwargs['auth'] = OAuth1(self._client.token,
                                    client_secret=self._client.secret,
                                    resource_owner_key=self._access.token,
                                    resource_owner_secret=self._access.secret,
                                    signature_method=SIGNATURE_PLAINTEXT)
            return super(OAuthClient, self)._do_request(*args, **kwargs)

        def get_request_token(self, callback=None):
            "The first step of the OAuth workflow."
            oauth = OAuth1(self._client.token,
                           client_secret=self._client.secret,
                           callback_uri=callback,
                           signature_method=SIGNATURE_PLAINTEXT)
            r = requests.post(urlparse.urljoin(
                self.url, 'oauth/request_token/'), auth=oauth)
            credentials = urlparse.parse_qs(r.text)
            self.__request = OAuthToken(credentials.get('oauth_token')[0],
                                        credentials.get(
                                        'oauth_token_secret')[0])
            return self.__request

        def get_authorization_url(self, request=None):
            "The second step of the OAuth workflow."
            if request is None:
                if not self.__request.is_valid():
                    raise APIError('You must obtain a request token to'
                                   'request and access token. Use'
                                   'get_request_token() first.')
                request = self.__request
            url = urlparse.urljoin(self.url, 'oauth/authorize/')
            return url + '?' + urllib.urlencode(
                dict(oauth_token=request.token))

        def get_access_token(self, request=None, verifier=None):
            """The final step of the OAuth workflow. After this the client
            can make API calls."""
            if request is None:
                if not self.__request.is_valid():
                    raise APIError('You must obtain a request token to request '
                                   'and access token. Use get_request_token() '
                                   'first.')
                request = self.__request
            oauth = OAuth1(self._client.token,
                           client_secret=self._client.secret,
                           resource_owner_key=request.token,
                           resource_owner_secret=request.secret,
                           verifier=verifier,
                           signature_method=SIGNATURE_PLAINTEXT)
            r = requests.post(urlparse.urljoin(
                self.url, 'oauth/access_token/'), auth=oauth)
            credentials = urlparse.parse_qs(r.text)
            self._access = OAuthToken(credentials.get('oauth_token')[0],
                                      credentials.get('oauth_token_secret')[0])
            return self._access


except ImportError:
    # OAuth, if not available.

    # Instead of a class, define this as a function, thus when a user tries to
    # "instantiate" it, they receive an exception.
    def OAuthClient(*args, **kwargs):
        raise NotImplementedError('You must install oauthlib and '
                                  'requests_oauthlib to use the OAuthClient. '
                                  'Try "pip install requests_oauthlib" to '
                                  'install both.')
