.. figure:: https://travis-ci.org/smartfile/client-python.png
   :alt: Travis CI Status
   :target: https://travis-ci.org/smartfile/client-python

A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Summary
------------

This library includes two API clients. Each one represents one of the supported
authentication methods. ``BasicClient`` is used for HTTP Basic authentication,
using an API key and password. ``OAuthClient`` is used for OAuth (version 1) authentication,
using tokens, which will require user interaction to complete authentication with the API.

Both clients provide a thin wrapper around an HTTP library, taking care of some
of the mundane details for you. The intended use of this library is to refer to
the API documentation to discover the API endpoint you wish to call, then use
the client library to invoke this call.

SmartFile API information is available at the
`SmartFile developer site <https://app.smartfile.com/api/>`_.

Installation
------------

You can install via ``pip``.

::

    $ pip install smartfile

Or via source code / GitHub.

::

    $ git clone https://github.com/smartfile/client-python.git smartfile
    $ cd smartfile
    $ python setup.py install

More information is available at `GitHub <https://github.com/smartfile/client-python>`_
and `PyPI <https://pypi.python.org/pypi/smartfile/>`_.

Usage
-----

Choose between Basic and OAuth authentication methods, then continue to use the SmartFile API.

Some of the details this library takes care of are:

* Encoding and decoding of parameters and return values. You deal with Python
  types only.
* URLs, using the API version, endpoint, and object ID, the URL is created for
  you.
* Authentication. Provide your API credentials to this library, it will take
  care of the details.

Basic Authentication
--------------------

Three methods are supported for providing API credentials using basic authentication.

1. Parameters when instantiating the client.

   .. code:: python

       >>> from smartfile import BasicClient
       >>> api = BasicClient('**********', '**********')
       >>> api.get('/ping')

2. Environment variables.

   Export your credentials via your environment.

   ::

       $ export SMARTFILE_API_KEY=**********
       $ export SMARTFILE_API_PASSWORD=**********

   And then you can use the client without providing any credentials in your
   code.

   .. code:: python

       >>> from smartfile import BasicClient
       >>> # Credentials are read automatically from environment
       >>> api = BasicClient()
       >>> api.get('/ping')

3. `netrc <http://man.cx/netrc%284%29>`_ file (not supported with OAuth).

   You can place the following into ``~/.netrc``:

   ::

       machine app.smartfile.com
         login **********
         password **********

   And then you can use the client without providing any credentials in your
   code.

   .. code:: python

       >>> from smartfile import BasicClient
       >>> # Credentials are read automatically from netrc
       >>> api = BasicClient()
       >>> api.get('/ping')

   You can override the default netrc file location, using the optional
   ``netrcfile`` kwarg.

   .. code:: python

       >>> from smartfile import BasicClient
       >>> # Credentials are read automatically from netrc
       >>> api = BasicClient(netrcfile='/etc/smartfile.keys')
       >>> api.get('/ping')


OAuth Authentication
--------------------

Authentication using OAuth authentication is bit more complicated, as it involves tokens and secrets.

.. code:: python

    >>> from smartfile import OAuthClient
    >>> api = OAuthClient('**********', '**********')
    >>> # Be sure to only call each method once for each OAuth login
    >>> 
    >>> # This is the first step with the client, which should be left alone
    >>> api.get_request_token()
    >>> # Redirect users to the following URL:
    >>> print "In your browser, go to: " + api.get_authorization_url()
    >>> # This example uses raw_input to get the verification from the console:
    >>> client_verification = raw_input("What was the verification? :")
    >>> api.get_access_token(None, client_verification)
    >>> api.get('/ping')

Calling endpoints
-----------------

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
``username``. For a file path, the id is it's full path.

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

File transfers
--------------

Uploading and downloading files is supported.

To upload a file, pass either a file-like object or a tuple of
``(filename, file-like)`` as a kwarg.

.. code:: python

    >>> from StringIO import StringIO
    >>> data = StringIO('StringIO instance has no .name attribute!')
    >>> from smartfile import BasicClient
    >>> api = BasicClient()
    >>> api.post('/path/data/', file=('foobar.png', data))
    >>> # Or use a file-like object with a name attribute
    >>> api.post('/path/data/', file=file('foobar.png', 'rb'))

Downloading is automatic, if the ``'Content-Type'`` header indicates
content other than the expected JSON return value, then a file-like object is
returned.

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
