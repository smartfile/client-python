A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

SmartFile API client.

Usage
-----

The main class in this library is API. It presents a taxonomy of the SmartFile
API that closely resembles the API url structure. You can create an instance
of the API object, then access any API functions using that taxonomy.

.. code:: python

    >>> import pprint
    >>> from smartfile import API
    >>> api = API(key='**********', password='**********')
    >>> pprint.pprint(api.path.tree.read('/'))
    {u'acl': {u'list': True, u'read': True, u'remove': True, u'write': True},
     u'attributes': {},
     u'extension': u'',
     u'id': 7,
     u'isdir': True,
     u'isfile': False,
     u'items': 322,
     u'mime': u'application/x-directory',
     u'name': u'',
     u'owner': None,
     u'path': u'/',
     u'size': 4612524,
     u'tags': [],
     u'time': u'2012-12-19T15:24:37',
     u'url': u'https://app.smartfile.com/api/2/path/7/'}

Instead of providing credentials in code, for shell scripts or other frameworks
you can provide credentials via the environment.

::

    $ export SMARTFILE_API_KEY="**********"
    $ export SMARTFILE_API_PASSWORD="**********"

.. code:: python

    >>> from smartfile import API
    >>> api = API()
    >>> api.path.operations.move('/source/path', '/destination/path')

You can also deal directly with specific endpoints, this is useful if you are
only going to deal with say, paths, and don't want to type the full namespace
for each API call.

.. code:: python

    >>> from smartfile import PathTree
    >>> api = PathTree(key='**********', password='**********')
    >>> pprint.pprint(api.read('/'))
    {u'acl': {u'list': True, u'read': True, u'remove': True, u'write': True},
     u'attributes': {},
     u'extension': u'',
     u'id': 7,
     u'isdir': True,
     u'isfile': False,
     u'items': 322,
     u'mime': u'application/x-directory',
     u'name': u'',
     u'owner': None,
     u'path': u'/',
     u'size': 4612524,
     u'tags': [],
     u'time': u'2012-12-19T15:24:37',
     u'url': u'https://app.smartfile.com/api/2/path/7/'}

Uploading and downloading files is supported, and deals with file paths or
file-like objects. Care is taken to stream data to and from the server, so
at no point are large files completely loaded into memory. Using file-like
objects allows for streaming to/from any source.

.. code:: python

    >>> from StringIO import StringIO
    >>> from smartfile import PathData
    >>> api = PathData(key='**********', password='**********')
    >>> api.upload('/path/within/smartfile.jpg', '/local/path.jpg')
    >>> sio = StringIO()
    >>> api.download('/path/within/smartfile.jpg', sio)
    >>> sio.seek(0)
    >>> api.upload('/you/should/use/copy/instead.txt', sio)

Operations are long-running jobs that are not executed within the time frame
of an API call. For such operations, a task is created, and the API can be used
to poll the status of the task. Tasks provide a convenience function wait()
that will block until the tasks completes. An optional timeout allows wait() to
return before completion.

.. code:: python

    >>> from smartfile import API
    >>> api = API(key='**********', password='**********')
    >>> task = api.path.operations.remove('/')  # <- rm -rf /
    >>> status = task.wait(timeout=5)
    >>> while status['result']['status'] not in ('FAILURE', 'SUCCESS'):
    >>>     # ...Do some other stuff...
    >>>     status = task.wait(timeout=5)

Operations that use tasks are.

* api.path.operations.remove()
* api.path.operations.copy()
* api.path.operations.move()

Some operations complete immediately.

* api.path.operations.mkdir()
* api.path.operations.rename()

You never create tasks directly, they are always created automatically in
response to an operation.

.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
