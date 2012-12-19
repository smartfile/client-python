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

::

    >>> import pprint
    >>> from smartfile import API
    >>> api = API(key='**********', password='**********')
    >>> >>> pprint.pprint(api.path.tree.read('/'))
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
     u'url': u'http://localhost:8000/api/2/path/7/'}




.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
