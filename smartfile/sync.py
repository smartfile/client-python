import os
import errno
import tempfile

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
        "Calculates signature for local file."
        kwargs = {}
        if block_size:
            kwargs['block_size'] = block_size
        return librsync.signature(open(self.path, 'rb'), **kwargs)

    def delta(self, signature):
        "Generates delta for local file using remote signature."
        return librsync.delta(open(self.path, 'rb'), signature)

    def patch(self, delta):
        "Applies remote delta to local file."
        # Create a temp file in which to store our synced copy. We will handle
        # deleting it manually, since we may move it instead.
        with (tempfile.NamedTemporaryFile(prefix='.sync',
              suffix=os.path.basename(self.path),
              dir=os.path.dirname(self.path), delete=False)) as output:
            try:
                # Open the local file, data may be read from it.
                with open(self.path, 'rb') as reference:
                    # Patch the local file into our temporary file.
                    r = librsync.patch(reference, delta, output)
                    os.rename(output.name, self.path)
                    return r
            finally:
                try:
                    os.remove(output.name)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise


class RemoteFile(BaseFile):
    """
    Represents a remote file that is being synchronized. Makes API calls to
    perform the steps of the rsync algorithm.
    """
    def __init__(self, path, api):
        super(RemoteFile, self).__init__(path)
        self.api = api

    def signature(self, block_size=None):
        "Requests a signature for remote file via API."
        kwargs = {}
        if block_size:
            kwargs['block_size'] = block_size
        return self.api.get('path/sync/signature', self.path, **kwargs)

    def delta(self, signature):
        "Generates delta for remote file via API using local file's signature."
        return self.api.post('path/sync/delta', self.path, signature=signature)

    def patch(self, delta):
        "Applies delta for local file to remote file via API."
        return self.api.post('path/sync/patch', self.path, delta=delta)


class SyncClient(object):
    """
    Synchronizes remote and local files.
    """
    def __init__(self, api, block_size=None):
        """
        Synchronizes files with SmartFile using the sync API.
        """
        self.api = api
        self.block_size = block_size

    @property
    def version(self):
        return self.api.version

    def sync(self, src, dst):
        """
        Performs synchronization from source to destination. Performs the three
        steps:

        1. Calculate signature of destination.
        2. Generate delta from source.
        3. Apply delta to destination.
        """
        return dst.patch(src.delta(dst.signature(block_size=self.block_size)))

    def upload(self, local, remote):
        """
        Performs synchronization from a local file to a remote file. The local
        path is the source and remote path is the destination.
        """
        self.sync(LocalFile(local), RemoteFile(remote, self.api))

    def download(self, local, remote):
        """
        Performs synchronization from a remote file to a local file. The
        remote path is the source and the local path is the destination.
        """
        self.sync(RemoteFile(remote, self.api), LocalFile(local))
