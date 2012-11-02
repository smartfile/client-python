import requests
import time

from os.path import basename
from os.path import dirname
from urlparse import urljoin


class _BaseAPI(object):
    """ Base class for specific API endpoints (i.e., user, path). """
    _baseurl = 'http://localhost:8000/api/2/'

    def __init__(self, api_key, api_pass, session=None, **kwargs):
        # Re-use existing session if provided.
        self._session = session or requests.session(auth=(api_key, api_pass))

    def _gen_url(self, uri_args=(), baseurl=None):
        """ Join segments onto URL to call API. """
        if baseurl:
            url = baseurl
        else:
            url = urljoin(self._baseurl, self._api_uri)

        # Concatenate the additional path components.
        for arg in uri_args:
            if arg != '/':
                sep = '' if url.endswith('/') else '/'
                url = '{0}{1}{2}'.format(url, sep, arg)

        return url

    def _create(self, data=None, *args, **kwargs):
        """ The C in CRUD. """
        url = self._gen_url(args, baseurl=kwargs.pop('baseurl', None))
        return self._session.post(url, data=data, **kwargs)

    def _read(self, *args, **kwargs):
        """ The R in CRUD. """
        url = self._gen_url(args, baseurl=kwargs.pop('baseurl', None))
        return self._session.get(url, **kwargs)

    def _update(self, data=None, *args, **kwargs):
        """ The U in CRUD. """
        url = self._gen_url(args, baseurl=kwargs.pop('baseurl', None))
        if data is not None:
            kwargs['data'] = data
        return self._session.post(url, **kwargs)

    def _delete(self, *args, **kwargs):
        """ The D in CRUD. """
        url = self._gen_url(args, baseurl=kwargs.pop('baseurl', None))
        return self._session.delete(url, **kwargs)


class UserAPI(_BaseAPI):
    """ User API. """
    _api_uri = 'user/'

    @property
    def create(self):
        return self._create

    @property
    def list(self):
        return self._read

    @property
    def update(self):
        return self._update

    @property
    def delete(self):
        return self._delete


class PathOperAPI(_BaseAPI):
    """ Path Oper API. """
    _api_uri = 'path/oper/'

    def remove(self, path):
        """ Create task to remove file system object(s). """
        return super(PathOperAPI, self)._create({'path': path}, 'remove/')

    def poll(self, url, checks=5, check_timeout=2):
        """
        Poll a URL until a non-200 response or the result of operation is
        SUCCESS.  Check a few times with a sleep between each check.
        """
        while checks > 0:
            response = self._session.get(url)
            if (response.status_code != 200 or
                response.json['result']['status'] == 'SUCCESS'):
                break
            checks -= 1
            time.sleep(check_timeout)

        return response


class PathTreeAPI(_BaseAPI):
    """ Path Tree API. """
    _api_uri = 'path/tree/'

    def list(self, path='/', children=False, *args, **kwargs):
        if children:
            kwargs['params'] = {'children': True}
        return super(PathTreeAPI, self)._read(path, *args, **kwargs)


class PathAPI(_BaseAPI):
    """ Path API. """
    _api_uri = 'path/'
    _api_uri_ext = 'data/'

    def __init__(self, *args, **kwargs):
        super(PathAPI, self).__init__(*args, **kwargs)
        kwargs['session'] = self._session
        self._path_oper_api = PathOperAPI(*args, **kwargs)
        self._path_tree_api = PathTreeAPI(*args, **kwargs)

    def _get_file_data(self, id, data=False):
        """ Get data of file using ID of file. """
        args = (id, self._api_uri_ext) if data else (id, )
        return super(PathAPI, self)._read(*args)

    @property
    def list(self):
        """ Shortcut to Path Tree API list(). """
        return self._path_tree_api.list

    def remove(self, path):
        """ Remove the file and poll awhile for it to finish. """
        response = self._path_oper_api.remove(path)
        if response.status_code == 200:
            response = self._path_oper_api.poll(response.json['url'])
        return response

    def download(self, dst, src):
        # Get file ID and download file in chunks.
        tree = self.list(src)
        response = self._get_file_data(tree.json['id'], True)
        if response.status_code == 200:
            with open(dst, 'wb') as dst_file:
                for chunk in response.iter_content(16 * 1024):
                    dst_file.write(chunk)

        return response

    def upload(self, dst, src):
        # Get directory ID.
        dst_dir = dirname(dst)
        tree = self._path_tree_api.list(dst_dir)

        # Upload file.
        files = {'file': (basename(dst), open(src, 'rb'))}
        return super(PathAPI, self)._create(
            None, self._api_uri_ext, baseurl=tree.json['url'], files=files)


class API(object):
    """
    This class provides a single interface to the various segments of the
    SmartFile API.
    """
    _session = None

    def __init__(self, api_key, api_pass):
        self._api_key = api_key
        self._api_pass = api_pass

    def _get_api(self, attr, cls):
        api = getattr(self, attr, None)
        if api is None:
            api = cls(self._api_key, self._api_pass, session=self._session)
            setattr(self, attr, api)
            if self._session is None:
                self._session = getattr(self, attr)._session
        return api

    @property
    def path(self):
        return self._get_api('_api_path_obj', PathAPI)

    @property
    def path_oper(self):
        return self._get_api('_api_path_oper_obj', PathOperAPI)

    @property
    def path_tree(self):
        return self._get_api('_api_path_tree_obj', PathTreeAPI)

    @property
    def user(self):
        return self._get_api('_api_user_obj', UserAPI)
