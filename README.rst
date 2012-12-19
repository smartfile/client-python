A `SmartFile`_ Open Source project. `Read more`_ about how SmartFile
uses and contributes to Open Source software.

.. figure:: http://www.smartfile.com/images/logo.jpg
   :alt: SmartFile

Introduction
------------

SmartFile API client.

Usage
-----

To use the library, simply pass a filename to the ``.get()`` module
function. A second optional argument ``default`` can provide a string to
be returned in case of error. This way, if you are not concerned with
exceptions, you can simply ignore them by providing a default. This is
like how the ``dict.get()`` method works.

::

    > import smartfile
    > smartfile.create_user(username='btimby')

.. _SmartFile: http://www.smartfile.com/
.. _Read more: http://www.smartfile.com/open-source.html
