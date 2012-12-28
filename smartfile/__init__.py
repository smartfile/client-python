import re
import os
import requests
import time
import urllib
import urlparse
import optparse
import pprint

from oauthlib.oauth1 import SIGNATURE_PLAINTEXT

from requests.exceptions import RequestException
from requests_oauthlib import OAuth1

from os.path import basename
from os.path import dirname

from smartfile.errors import APIError
from smartfile.errors import RequestError
from smartfile.errors import ResponseError


API_URL = 'https://app.smartfile.com/'
API_VER = '2.0'

THROTTLE = re.compile('^next=([^ ]+) sec$')
HTTP_USER_AGENT = 'SmartFile Python API client v1.0'


class Connection(object):
    "Manages the HTTP portion of the API."
    def __init__(self, url=None, version=None, throttle_wait=True, **kwargs):
        "Collects everything needed to access the API, url, key, password."
        self.base_url = url or os.environ.get('SMARTFILE_API_URL', API_URL)
        self.base_ver = version or os.environ.get('SMARTFILE_API_VER', API_VER)
        self.throttle_wait = throttle_wait
        self._session = requests.session()
        self._session.auth = self.get_auth(**kwargs)

    def get_password_auth(self, **kwargs):
        key = kwargs.get('key')
        password = kwargs.get('password')
        if key is None:
            key = os.environ.get('SMARTFILE_API_KEY')
        if password is None:
            password = os.environ.get('SMARTFILE_API_PASSWORD')
        if key is None or password is None:
            raise APIError('Please provide an API key and password. Use '
                           'arguments or environment variables.')
        return key, password

    def get_oauth_auth(self, **kwargs):
        # Get the client token.
        client_token = kwargs.get('client_token')
        client_secret = kwargs.get('client_secret')
        if client_token is None:
            client_token = os.environ.get('SMARTFILE_CLIENT_TOKEN')
        if client_secret is None:
            client_secret = os.environ.get('SMARTFILE_CLIENT_SECRET')
        if not client_token or not client_secret:
            raise APIError('You must provide a client_token and client_secret '
                            'for OAuth.')
        # Get the access token:
        access_token = kwargs.get('access_token')
        access_secret = kwargs.get('access_secret')
        if access_token is None:
            access_token = os.environ.get('SMARTFILE_ACCESS_TOKEN')
        if access_secret is None:
            access_secret = os.environ.get('SMARTFILE_ACCESS_SECRET')
        if not access_token or not access_secret:
            raise APIError('You must provide an access_token and access_secret '
                           'for OAuth.')
        return OAuth1(unicode(client_token),
                      client_secret=unicode(client_secret),
                      resource_owner_key=unicode(access_token),
                      resource_owner_secret=unicode(access_secret),
                      signature_method=SIGNATURE_PLAINTEXT)

    def get_auth(self, **kwargs):
        "Sets up authentication."
        try:
            return self.get_oauth_auth(**kwargs)
        except APIError:
            pass
        try:
            return self.get_password_auth(**kwargs)
        except APIError:
            pass
        raise APIError('You must provide authentication information. '
                       'Either API key and password or oauth keys.')

    def get_url(self, components, *args, **kwargs):
        "Concatenate the base_url, URL components and then merge in arguments."
        # Remove any leading or trailing slashes from URL components.
        components = [unicode(x).strip('/') for x in components]
        kwargs = dict([(k, unicode(v).strip('/')) for k, v in kwargs.items()])
        # Inject the base URL and API version as the first items. Strip any
        # trailing '/'.
        components = [
            'api',
            self.base_ver,
        ] + components
        # Join all the components into one uniform URL (containing format
        # strings).
        url = '/'.join(components).replace('//', '/')
        url = '/'.join((self.base_url.rstrip('/'), url))
        # Use string formatting to merge the arguments into the URL.
        url = url.format(**kwargs)
        if not url.endswith('/'):
            url += '/'
        return url

    def _request(self, request, url, **kwargs):
        """Performs a single HTTP request, raises an exception for >=400
        status. All kwargs are passed to the requests library."""
        kwargs.setdefault('headers', {}).setdefault('User-Agent', HTTP_USER_AGENT)
        try:
            response = request(url, **kwargs)
        except RequestException, e:
            raise RequestError(e)
        else:
            if response.status_code >= 400:
                raise ResponseError(response)
        return response

    def request(self, method, url, **kwargs):
        """Performs the HTTP request and handles the response. It may retry the
        request under certain circumstances. All kwargs are passed to 
        Connection._request()."""
        request = getattr(self._session, method, None)
        if not callable(request):
            raise RequestError('Invalid method %s' % method)
        trys, retrys = 0, 3
        while True:
            if trys == retrys:
                raise RequestError('Could not complete request after %s trys.' % trys)
            trys += 1
            try:
                return self._request(request, url, **kwargs)
            except ResponseError, e:
                if self.throttle_wait and e.status_code == 503:
                    m = THROTTLE.match(e.response.headers['x-throttle'])
                    if m:
                        wait = float(m.group(1))
                        time.sleep(wait)
                        continue
                raise


class Endpoint(object):
    fragments = ()

    def __init__(self, connection=None, **kwargs):
        "Use the provided connection, or create one."
        self.conn = connection or Connection(**kwargs)

    def _request(self, method, keys={}, **kwargs):
        """Does the actual API request. It strips off the keys kwargs and uses
        that to generate the URL to the object. All other kwargs are passed to
        Connection.request()."""
        url = self.conn.get_url(self.fragments, **keys)
        return self.conn.request(method, url, **kwargs)

    def _create(self, **kwargs):
        return self._request('post', **kwargs)

    def _read(self, **kwargs):
        return self._request('get', **kwargs)

    def _update(self, **kwargs):
        return self._request('post', **kwargs)

    def _delete(self, **kwargs):
        return self._request('delete', **kwargs)

    def create(self, *args, **kwargs):
        "This method is not supported by the endpoint."
        raise NotImplementedError('Endpoint does not support this method.')

    def read(self, *args, **kwargs):
        "This method is not supported by the endpoint."
        raise NotImplementedError('Endpoint does not support this method.')

    def update(self, *args, **kwargs):
        "This method is not supported by the endpoint."
        raise NotImplementedError('Endpoint does not support this method.')

    def delete(self, *args, **kwargs):
        "This method is not supported by the endpoint."
        raise NotImplementedError('Endpoint does not support this method.')


class OAuth(object):
    def __init__(self, url=API_URL, client_token=None, client_secret=None):
        self.url = url
        if client_token is None:
            client_token = os.environ.get('SMARTFILE_CLIENT_TOKEN')
        if client_secret is None:
            client_secret = os.environ.get('SMARTFILE_CLIENT_SECRET')
        self.client_token = unicode(client_token)
        self.client_secret = unicode(client_secret)

    def get_request_token(self, callback=None):
        oauth = OAuth1(self.client_token, client_secret=self.client_secret,
                       callback_uri=unicode(callback),
                       signature_method=SIGNATURE_PLAINTEXT)
        r = requests.post(urlparse.urljoin(self.url, 'oauth/request_token/'), auth=oauth)
        credentials = urlparse.parse_qs(r.text)
        return credentials.get('oauth_token')[0], credentials.get('oauth_token_secret')[0]

    def get_authorization_url(self, request_token):
        url = urlparse.urljoin(self.url, 'oauth/authorize/')
        return url + '?' + urllib.urlencode(dict(oauth_token=request_token))

    def get_access_token(self, request_token, request_secret, verifier):
        oauth = OAuth1(self.client_token, client_secret=self.client_secret,
                       resource_owner_key=unicode(request_token),
                       resource_owner_secret=unicode(request_secret),
                       verifier=unicode(verifier),
                       signature_method=SIGNATURE_PLAINTEXT)
        r = requests.post(urlparse.urljoin(self.url, 'oauth/access_token/'), auth=oauth)
        credentials = urlparse.parse_qs(r.text)
        return credentials.get('oauth_token')[0], credentials.get('oauth_token_secret')[0]


class PathTree(Endpoint):
    "Returns path information using a file system like structure."
    fragments = ('path', 'tree', '{path}')

    def read(self, path='/', children=False, **kwargs):
        # The 'keys' argument is used by Connection.get_url() for generating
        # the URL for the object we are interested in.
        kwargs['keys'] = {
            # Strip leading slashes.
            'path': path,
        }
        if children:
            # The 'params' argument will be used by requests to generate the
            # querystring.
            kwargs['params'] = { 'children': children }
        return self._read(**kwargs).json()


class PathData(Endpoint):
    "Allows access to a path's data."
    fragments = ('path', '{id}', 'data')

    def __init__(self, *args, **kwargs):
        super(PathData, self).__init__(*args, **kwargs)
        # As a convenience, we allow reading/writing data by path, since the
        # API requires a path id for reading, we will internally use a PathTree
        # endpoint to look them up.
        self.tree = PathTree(*args, **kwargs)

    def _get_kwargs(self, path):
        info = self.tree.read(path=path)
        return {
            'keys': {
                'id': info['id'],
            }
        }

    def download(self, path, dst, chunk_size=16 * 1024):
        "Downloads to a file-like object or path."
        kwargs = self._get_kwargs(path)
        r = self._read(**kwargs)
        if not callable(getattr(dst, 'write', None)):
            openfile, dst = True, file(dst, 'wb')
        else:
            openfile = False
        try:
            for chunk in r.iter_content(chunk_size):
                dst.write(chunk)
        finally:
            # If we opened it, we close it.
            if openfile:
                dst.close()

    def upload(self, path, src):
        "Uploads from a file-like object or path."
        if not callable(getattr(src, 'read', None)):
            openfile, src = True, file(src, 'rb')
        else:
            openfile = False
        parent = dirname(path)
        kwargs = self._get_kwargs(parent)
        kwargs['files'] = {
            basename(path): src,
        }
        try:
            self._create(**kwargs)
        finally:
            if openfile:
                src.close()


class PathOper(Endpoint):
    """API endpoint for dealing with path operations. Some path operations
    create a task, which is a long-running job that can be polled to monitor
    it's status."""
    fragments = ('path', 'oper', '{operation}')

    def _create(self, operation, **kwargs):
        kwargs.update({
            'keys': {
                'operation': operation,
            },
        })
        return self._request('post', **kwargs)

    def _create_task(self, operation, **kwargs):
        # Tell requests to follow redirects after POST, the operation API will
        # redirect if the operation is long-running (and creates a task).
        kwargs['allow_redirects'] = True
        return Task(self._create('remove', **kwargs).json(), connection=self.conn)

    def remove(self, path, **kwargs):
        kwargs['data'] = {
            'path': path,
        }
        return self._create_task('remove', **kwargs)

    def copy(self, src, dst, **kwargs):
        kwargs['data'] = {
            'src': src,
            'dst': dst,
        }
        return self._create_task('copy', **kwargs)

    def move(self, src, dst, **kwargs):
        kwargs['data'] = {
            'src': src,
            'dst': dst,
        }
        return self._create_task('move', **kwargs)

    def mkdir(self, path, **kwargs):
        # TODO: this is really ugly, this endpoint uses PUT, and requires
        # the path to create in the URL. This is the only one like this AFAIK.
        kwargs.update({
            'keys': {
                # TODO: fix this, we are bastardizing the URL creation. Either
                # it is too inflexible, or this endpoint should conform.
                'operation': 'create' + path,
            },
        })
        return self._request('put', **kwargs)

    def rename(self, path, **kwargs):
        kwargs['data'] = {
            'src': src,
            'dst': dst,
        }
        self._create('create', **kwargs)


class Task(Endpoint):
    """An endpoint for dealing with long-running tasks. This endpoint provides
    a convenience function wait() that will wait for completion. It is not like
    other endpoints in that users don't create tasks directly, but they are
    created in response to operations performed at other endpoints."""
    fragments = ('task', '{uuid}')

    def __init__(self, task, **kwargs):
        super(Task, self).__init__(**kwargs)
        self.task = task

    def _get_kwargs(self):
        return {
            'keys': {
                'uuid': self.task['uuid'],
            },
        }

    def read(self):
        kwargs = self._get_kwargs()
        return self._read(**kwargs).json()

    def delete(self):
        kwargs = self._get_kwargs()
        self._delete(**kwargs)

    def wait(self, timeout=None):
        "Wait for the task's completion. By default waits forever."
        kwargs = self._get_kwargs()
        start = time.time()
        while True:
            info = self._read(**kwargs).json()
            if (timeout is not None and
                time.time() - start >= timeout):
                break
            if info['result']['status'] in ('SUCCESS', 'FAILURE'):
                break
            time.sleep(1)
        return info


class Container(object):
    """Caches and makes available endpoints from a convenient location. All
    endpoints will share the same Connection."""
    endpoints = {}

    def __init__(self, connection=None, **kwargs):
        self.conn = connection or Connection(**kwargs)
        self.cache = {}

    def __getattr__(self, attr):
        try:
            cls = self.endpoints[attr]
        except KeyError:
            raise APIError('Invalid API endpoint %s' % attr)
        if cls not in self.cache:
            self.cache[cls] = cls(connection=self.conn)
        return self.cache[cls]


class PathAPI(Container):
    "A container for path related Endpoints."
    endpoints = {
        'tree': PathTree,
        'data': PathData,
        'operations': PathOper,
    }


class UserAccess(Endpoint):
    fragments = ('access', 'user', )


class PathAccess(Endpoint):
    fragments = ('access', 'path', )


class GroupAccess(Endpoint):
    fragments = ('access', 'group', )


class AccessAPI(Container):
    endpoints = {
        'user': UserAccess,
        'path': PathAccess,
        'group': GroupAccess,
    }


class UserQuota(Endpoint):
    fragments = ('quota', 'user', )


class SiteQuota(Endpoint):
    fragments = ('quota', 'site', )


class QuotaAPI(Container):
    endpoints = {
        'user': UserQuota,
        'site': SiteQuota,
    }


class Ping(Endpoint):
    """Returns a simple value. Useful to test connectivity. This endpoint is
    anonymous."""
    fragments = ('ping', )

    def read(self):
        return self._read().json()


class WhoAmI(Endpoint):
    """Echos information about the current user/site. Useful to test
    authentication."""
    fragments = ('whoami', )

    def read(self):
        return self._read().json()


class Link(Endpoint):
    fragments = ('link', )


class User(Endpoint):
    fragments = ('user', )


class Site(Endpoint):
    fragments = ('site', )


class Role(Endpoint):
    fragments = ('role', )


class API(Container):
    """The main API tree. It branches out to Endpoints and Containers. It acts
    as a namespace for the API."""
    endpoints = {
        # Sub-Collections of Endpoints:
        'path': PathAPI,
        'access': AccessAPI,
        'quota': QuotaAPI,

        # Endpoints:
        'ping': Ping,
        'whoami': WhoAmI,
        'link': Link,
        'user': User,
        'site': Site,
        'role': Role,
    }


def main():
    parser = optparse.OptionParser(prog="smartfile", description="CLI harness for SmartFile.")
    parser.add_option("-t", "--client-token", help="Your SmartFile client token.")
    parser.add_option("-s", "--client-secret", help="Your SmartFile client secret.")
    parser.add_option("-a", "--access-token", help="Your SmartFile access token (if you previously obtained one.")
    parser.add_option("-b", "--access-secret", help="Your SmartFile access secret (if you previously obtained one.")

    (options, args) = parser.parse_args()

    if not options.client_token or not options.client_secret:
        parser.error('You need to provide a client token and secret. If you '
                     'don\'t have one, register for one.\n'
                     'http://app.smartfile.com/oauth/register/')
    if not options.access_token or not options.access_secret:
        print 'You need an access token, let\s get one...'
        oa = OAuth(client_token=options.client_token, client_secret=options.client_secret)
        token = oa.get_request_token()
        url = oa.get_authorization_url(request_token=token[0])
        print 'Authorize the application at the following URL. Type in the verifier and hit <enter>.'
        print url
        try:
            import webbrowser
            print 'Opening URL in your default browser...'
            webbrowser.open(url)
        except:
            pass
        verifier = raw_input()
        print 'Now, we will try to obtain an access token.'
        access_token, access_secret = oa.get_access_token(request_token=token[0],
            request_secret=token[1], verifier=verfier)
        print 'Access Token:', access_token
        print 'Access Secret:', access_secret
    else:
        access_token, access_secret = options.access_token, options.access_secret
    api = API(client_token=options.client_token, client_secret=options.client_secret,
              access_token=access_token, access_secret=access_secret)
    pprint.pprint(api.whoami.read())


if __name__ == '__main__':
    main()
