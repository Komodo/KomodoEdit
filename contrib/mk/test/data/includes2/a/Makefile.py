from mklib import include, Task

include('b/Makefile.py', ns='b')

class ack(Task):
    default = True
class clean(Task):
    "clean up"
    pass

