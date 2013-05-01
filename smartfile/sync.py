import os
import zlib
import hashlib
import tempfile

from itertools import count


# Indicates that the block should come from the "server" (source) or "client"
# (destination) of the sync operation. Any machine can be either client or
# server, which it is depends on the direction of the sync.
SRC, DST = 0, 1
# Default block_size to use.
BS = 4096
# Min / Max block_size to use.
BS_MIN, BS_MAX = 1024, 32768
# Default amount of file data to buffer in memory before using disk.
MAX_BUFFER = 1024 ** 2 * 5


class SyncError(Exception):
    pass


def calc_block_size(f):
    "Tries to obtain the optimal block size."
    # Try to determine the file size using methods with decreasing chance of
    # success.
    size = None
    # Try to use os.fstat() to determine file size.
    if callable(getattr(f, 'fileno', None)):
        try:
            size = os.fstat(f.fileno()).st_size
        except:
            pass
    # Hmm, try to use seek() to determine file size.
    if size is None and callable(getattr(f, 'seek', None)):
        try:
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
        except:
            pass
    # len()?
    if size is None:
        try:
            size = len(f)
        except:
            pass
    # If we could not determine the size, use the default.
    if size is None:
        return BS
    # Try to use about 1024 blocks, but not less than 1K or greater than 32K.
    return min(BS_MAX, max(BS_MIN, size / 1024))


def checksum(f, block_size=None):
    """
    Calculates the rolling checksum of a file. Uses both the fast adler32 and
    md5 algorithms. Both are used because during delta creation, if the faster
    adler32 does not match, md5 is skipped. In the case adler32 matches, md5
    is performed as a stronger "double-check".

    Returns a structure containing file information and the checksums.
    """
    if not block_size:
        block_size = calc_block_size(f)
    try:
        f.seek(0)
    except AttributeError:
        pass
    blocks, md5sum = [], hashlib.md5()
    while True:
        block = f.read(block_size)
        md5sum.update(block)
        if not block:
            break
        sum1 = hex(zlib.adler32(block))
        sum2 = hashlib.md5(block).hexdigest()
        blocks.append((sum1, sum2))
    return md5sum.hexdigest(), blocks, block_size


def delta(f, md5sum, blocks, block_size=None, max_buffer=MAX_BUFFER):
    """
    Uses the rolling checksum of a remote file to generate a delta for the local
    copy. The result is a structure that instructs how to peice together blocks
    from the remote file and the local file to create a file that is identical
    to the local file. Any blocks from the local file that are referenced by
    this structure will be contained within the blob.

    Returns a two-tuple of the delta structure and a blob containing the
    referenced blocks.

    For the purposes of this function, our local file is SRC.
    """
    if not block_size:
        block_size = calc_block_size(f)
    try:
        f.seek(0)
    except AttributeError:
        pass
    md5sum, blob = hashlib.md5(), tempfile.SpooledTemporaryFile(max_size=max_buffer)
    i, ranges = 0, []
    for i in count(0):
        direction, block = None, f.read(block_size)
        if block:
            md5sum.update(block)
        else:
            # We ran out of data in our local copy, delta should
            # instruct copying data from remote file.
            direction = DST
        try:
            sum1, sum2 = blocks[i]
        except IndexError:
            if not block:
                # If we ran out of data AND checksums, we are done.
                break
            # We ran out of checksums, delta should instruct copying
            # data from our local copy.
            direction = SRC
        if direction is None:
            # We have not yet determined direction, meaning, we have a
            # block and checksums that need to be compared.
            if sum1 == hex(zlib.adler32(block)) and \
               sum2 == hashlib.md5(block).hexdigest():
                # Data is identical in both copies, delta should instruct
                # copying data from remote file.
                direction = DST
            else:
                # Data differs, delta should instruct copying data from our
                # local copy.
                direction = SRC
        if direction == DST:
            offset, length = i * block_size, block_size
        else:
            offset, length = blob.tell(), len(block)
            blob.write(block)
        ranges.append((direction, offset, length))
    blob.seek(0)
    return md5sum.hexdigest(), ranges, blob


def patch(f, ranges, blob, max_buffer=MAX_BUFFER):
    """
    Applies a delta to the local file by alternately copying data from the
    local copy and provided blob to recreate the remote file locally.

    After patching it uses the file information to verify that the local file
    and remote file are identical.

    For the purposes of this function, our local file is DST.
    """
    try:
        f.seek(0)
    except AttributeError:
        pass
    md5sum = hashlib.md5()
    sources = {
        SRC: blob,
        DST: f,
    }
    o = tempfile.SpooledTemporaryFile(max_size=max_buffer)
    for direction, offset, length in ranges:
        s = sources[direction]
        s.seek(offset)
        block = s.read(length)
        md5sum.update(block)
        o.write(block)
    o.seek(0)
    return o
