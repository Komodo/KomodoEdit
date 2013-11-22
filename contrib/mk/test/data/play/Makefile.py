import os
from mklib import Task, File
from mklib.common import relpath

class a(Task):
    default = True
    results = "foo bar".split()
    def make(self):
        for result in self.results:
            print "touch %s" % relpath(result.path)

class b(File):
    path = "foo"
    #XXX 'deps' for now, will add 'dep' later
    deps = ["blah"]
    


#---- support stuff

class testclean(Task):
    def make(self):
        for path in ("blah",):
            if os.path.exists(path):
                os.remove(path)

