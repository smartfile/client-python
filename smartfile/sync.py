import os

try:
    import librsync
except ImportError:
    raise ImportError('python-librsync is required for sync capabilities. '
                      'Install it using `pip install python-librsync`.')


class BaseFile(object):
    """
    Base class for files being synchronized.
    """
    def __init__(self, path):
        self.path = path


class LocalFile(BaseFile):
    """
    Represents a local file that is being synchronized. Uses librsync to
    perform the steps of the rsync algorithm.
    """
    def signature(self, block_size=None):
        kwargs = {}
        if block_size:
            kwargs['block_size'] = block_size
        return librsync.signature(file(self.path, 'rb'), **kwargs)

    def delta(self, signature):
        return librsync.delta(file(self.path, 'rb'), signature)

    def patch(self, delta):
        # Open the local file, data may be read from it.
        f = file(self.path, 'rb')
        # Unlink the local file, it will remain readable.
        os.unlink(self.path)
        # Now patch the file to the local path, replacing it.
        return librsync.patch(f, delta, o=file(self.path, 'wb'))


class RemoteFile(BaseFile):
    """
    Represents a remote file that is being synchronized. Makes API calls to
    perform the steps of the rsync algorithm.
    """
    def __init__(self, path, api):
        super(RemoteFile, self).__init__(path)
        self.api = api

    def signature(self, block_size=None):
        kwargs = {}
        if block_size:
            kwargs['block_size'] = block_size
        return self.api.get('sync/signature', self.path, **kwargs)

    def delta(self, signature):
        return self.api.post('sync/delta', self.path, signature=signature)

    def patch(self, delta):
        return self.api.post('sync/patch', self.path, delta=delta)


class SyncClient(object):
    """
    Synchronizes remote and local files.
    """
    def __init__(self, api, block_size=None):
        self.api = api
        self.block_size = block_size

    def sync(self, src, dst):
        """
        Performs synchronization from source to destination.
        """
        return dst.patch(src.delta(dst.signature(block_size=self.block_size)))

    def sync_to_server(self, local, remote):
        """
        Performs synchronization from a local file to a remote file.
        """
        self.sync(LocalFile(local), RemoteFile(remote, self.api))

    def sync_from_server(self, local, remote):
        """
        Performs synchronization from a remote file to the local system.
        """
        new = self.sync(RemoteFile(remote, self.api), LocalFile(local))
