.. figure:: https://travis-ci.org/smartfile/client-python.png
   :alt: Travis CI Status
   :target: https://travis-ci.org/smartfile/client-python

A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

SmartFile API client.

Usage
-----

This library includes two API clients. Each one represents one of the supported
authentication methods. `BasicClient` is used for HTTP Basic authentication,
using an API key and password. OAuthClient is used for OAuth authentication,
using tokens.

Both clients provide a thin wrapper around an HTTP library, taking care of some
of the mundane details for you. The intended use of this library is to refer to
the API documentation to discover the API endpoint you wish to call, then use
the client library to invoke this call.

Some of the details this library takes care of are.

* Encoding and decoding of parameters and return values. You deal with Python
  types only.
* URLs, using the API version, endpoint, and object ID, the URL is created for
  you.
* Authentication. Provide the credentials that you obtained from SmartFile,
  and plug them into this library. It will take care of the details.

Three methods are supported for providing API credentials.

1. Environment variables.

::

    $ export SMARTFILE_API_KEY=**********
    $ export SMARTFILE_API_PASSWORD=**********

.. code:: python

    >>> from smartfile import BasicClient
    >>> # Credentials are read automatically from environment
    >>> api = BasicClient()
    >>> api.get('/ping')

2. `netrc
<http://man.cx/netrc%284%29>`_ file (not supported with OAuth).

::

    machine app.smartfile.com
      login **********
      password **********

.. code:: python

    >>> from smartfile import BasicClient
    >>> # Credentials are read automatically from netrc
    >>> api = BasicClient()
    >>> api.get('/ping')

3. Parameters when instantiating the client.

.. code:: python

    >>> from smartfile import BasicClient
    >>> api = BasicClient('**********', '**********')
    >>> api.get('/ping')

Once you instantiate a client, you can use the get/put/post/delete methods
to make the corresponding HTTP requests to the API. There is also a shortcut
for using the GET method, which is to simply invoke the client.

.. code:: python

    >>> from smartfile import BasicClient
    >>> api = BasicClient('**********', '**********')
    >>> api.get('/ping')
    >>> # The following is equivalent...
    >>> api('/ping')

Some endpoints accept an ID, this might be a numeric value, a path, or name,
depending on the object type. For example, a user's id is their unique
`username`. For a file path, the id is it's full path.

.. code:: python

    >>> import pprint
    >>> from smartfile import BasicClient
    >>> api = BasicClient('**********', '**********')
    >>> # For this endpoint, the id is '/'
    >>> pprint.pprint(api.get('/path/info', '/'))
    {u'acl': {u'list': True, u'read': True, u'remove': True, u'write': True},
     u'attributes': {},
     u'extension': u'',
     u'id': 7,
     u'isdir': True,
     u'isfile': False,
     u'items': 348,
     u'mime': u'application/x-directory',
     u'name': u'',
     u'owner': None,
     u'path': u'/',
     u'size': 220429838,
     u'tags': [],
     u'time': u'2013-02-23T22:49:30',
     u'url': u'http://localhost:8000/api/2/path/info/'}

Uploading and downloading files is supported.

To upload a file, pass either a file-like object or a tuple of (filename,
file-like) as a kwarg.

.. code:: python

    >>> from StringIO import StringIO
    >>> data = StringIO('StringIO instance has no .name attribute!')
    >>> from smartfile import BasicClient
    >>> api = BasicClient()
    >>> api.post('/path/data/', file=('foobar.png', data))
    >>> # Or use a file-like object with a name attribute
    >>> api.post('/path/data/', file=file('foobar.png', 'rb'))

Downloading is automatic, if the Content-Type header indicates content other
than the expected JSON return value, then a file-like object is returned.

.. code:: python

    >>> import shutil
    >>> from smartfile import BasicClient
    >>> api = BasicClient()
    >>> f = api.get('/path/data/', 'foobar.png')
    >>> with file('foobar.png', 'wb') as o:
    >>>     shutil.copyfileobj(f, o)

Operations are long-running jobs that are not executed within the time frame
of an API call. For such operations, a task is created, and the API can be used
to poll the status of the task.

.. code:: python

    >>> from smartfile import BasicClient
    >>> api = BasicClient()
    >>> t = api.post('/path/oper/move/', src='/foobar.png', dst='/images/foobar.png')
    >>> while True:
    >>>     s = api.get('/task', t['uuid'])
    >>>     if s['status'] == 'SUCCESS':
    >>>         break

.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
