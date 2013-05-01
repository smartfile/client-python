import os
import cProfile

from StringIO import StringIO

from smartfile import sync


s1 = StringIO(os.urandom(1024**2))
s2 = StringIO(os.urandom(1024**2))

#blocks = sync.table(s1)
cProfile.run('blocks = sync.table(s1)')

#ranges, blob = sync.delta(s2, blocks)
cProfile.run('ranges, blob = sync.delta(s2, blocks)')

#out = sync.patch(s1, ranges, blob)
cProfile.run('out = sync.patch(s1, ranges, blob)')