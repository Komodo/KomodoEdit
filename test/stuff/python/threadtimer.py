import dbgpClient
# dbgpClient.set_thread_support(0)

import threading

def timer_callback():
    print "Hello"

objTimer = threading.Timer(2.0, timer_callback)
objTimer.start()

print "main done"
