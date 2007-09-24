# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

import sys, time
import threading

def counting(name, duration = 10):
    for i in range(duration):
        print "%s i=%d" % (name, i)
        time.sleep(1)

threading.Thread(target = counting, args=('thread',)).start()

counting('main', 20)


print "done"