from __future__ import with_statement
from __future__ import print_function
import threading

def do_something():
    with open('/etc/passwd:', 'r') \
            as f:  # making this: hard 
        for line in f:
            print(line)

def foo():
    lock = threading.Lock()
    with lock:
        # Critical section of code
        do_something()

