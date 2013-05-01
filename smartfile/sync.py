import os
import zlib
import hashlib
import tempfile

from collections import deque
from itertools import count


# Indicates that the block should come from the "server" (source) or "client"
# (destination) of the sync operation. Any machine can be either client or
# server, which it is depends on the direction of the sync.
SRC, DST = 0, 1
# Default block_size to use.
BS = 4096
# Default amount of file data to buffer in memory before using disk.
MAX_BUFFER = 1024 ** 2 * 5


class SyncError(Exception):
    pass


class RollingChecksum(object):
    def __init__(self, data=None, block_size=BS):
        self.bs, self.s, self.a, self.b = block_size, 0, 0, 0
        if data:
            l, data = len(data), map(ord, data)
            self.a = sum(data)
            for i, d in enumerate(data):
                self.b += (l - i) * d

    def roll(self, pop, add):
        pop, add = ord(pop), ord(add)
        self.a -= pop - add
        self.b -= pop * self.bs - self.a

    def digest(self):
        return (self.b << 16) | self.a


def table(f, block_size=BS):
    """
    Calculates a table containing block checksums for the given stream. These
    checksums are stored in dictionaries. The first (fast) checksum may have
    many collisions, so it is probable that multiple blocks will have the same
    value for the first checksum, but different values for the second.

    {
        'fast1': {
            'slow1': (offset, length),
            'slow2': (offset, length),
        },
        'fast2': {
            'slow3': (offset, length),
        }
    }

    So that the faster checksum can yield possible matching blocks. If a match
    is found at the first level, the slower (MD5) checksum is performed to find
    the location of the matching block.

    Returns a structure containing file information and the checksums.
    """
    try:
        f.seek(0)
    except AttributeError:
        pass
    blocks = {}
    while True:
        offset, block = f.tell(), f.read(block_size)
        if not block:
            break
        length = len(block)
        sum1 = RollingChecksum(block).digest()
        sum2 = hashlib.md5(block).hexdigest()
        blocks.setdefault(sum1, {})[sum2] = (offset, length)
    return blocks


def delta(f, blocks, block_size=BS, max_buffer=MAX_BUFFER):
    """
    Uses the block table of a remote file to generate a delta for the local
    copy. The stream is scanned one byte at a time while calculating a rolling
    checksum. At each step, the block list is searched for a match. If a match
    is found, the slower MD5 sum is used to verify a matching block.

    Returns a two-tuple of the delta structure and a blob containing the
    referenced blocks.

    For the purposes of this function, our local file is SRC.
    """
    try:
        f.seek(0)
    except AttributeError:
        pass
    # Ranges will contain a list of ranges to read from SRC or DST to
    # reassemble the SRC file. Blob contains the referenced ranges from
    # the SRC, so that the DST can apply them.
    ranges, blob = [], tempfile.SpooledTemporaryFile(max_size=max_buffer)
    # Window is the current block we are searching for. Reverse is our write
    # buffer, data that was examined and fell out of our window. Forward is our
    # read buffer, allowing us to read more than one byte at a time.
    window, forward, reverse = deque(), deque(), []
    # We will be calculating checksums as we move through the stream.
    sum1 = RollingChecksum()
    while True:
        if not window:
            if forward:
                window.extend(forward)
                forward.clear()
            need = block_size - len(window)
            if need:
                window.extend(f.read(need))
            sum1 = RollingChecksum(''.join(window), block_size=block_size)
        # Check if our window matches any blocks:
        matches = blocks.get(sum1.digest())
        if matches:
            sum2 = hashlib.md5(''.join(window)).hexdigest()
            offset, length = matches.get(sum2, (None, None))
            if offset is not None:
                # We found a block that matches our window.
                if reverse:
                    # First flush our reverse buffer.
                    ranges.append((SRC, blob.tell(), len(reverse)))
                    blob.write(''.join(reverse))
                    del reverse[:]
                elif ranges and ranges[-1][0] == DST:
                    # If the previous range is also of type DST, merge and
                    # replace it.
                    _, poffset, plength = ranges.pop()
                    offset, length = poffset, plength + length
                ranges.append((DST, offset, length))
                # dump our window
                window.clear()
                continue
        if not forward:
            forward.extend(f.read(block_size))
            if not forward:
                break
        nbyte = forward.popleft()
        # Start moving our window by popping it's tail.
        obyte = window.popleft()
        # Update rolling checksum.
        sum1.roll(obyte, nbyte)
        # Finish moving our window, appending to head.
        window.append(nbyte)
        # The old byte should be written to the blob
        reverse.append(obyte)
    # Combine our remaining buffers.
    reverse.extend(window)
    # Flush any remaining data.
    if reverse:
        ranges.append((SRC, blob.tell(), len(reverse)))
        blob.write(''.join(reverse))
    return ranges, blob


def patch(f, ranges, blob, max_buffer=MAX_BUFFER):
    """
    Applies a delta to the local file by alternately copying data from the
    local copy and provided blob to recreate the remote file locally.

    For the purposes of this function, our local file is DST.
    """
    try:
        f.seek(0)
    except AttributeError:
        pass
    sources = {
        SRC: blob,
        DST: f,
    }
    o = tempfile.SpooledTemporaryFile(max_size=max_buffer)
    for direction, offset, length in ranges:
        s = sources[direction]
        s.seek(offset)
        o.write(s.read(length))
    o.seek(0)
    return o
