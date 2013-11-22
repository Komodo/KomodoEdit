import os
import shutil
import time
from mklib import Task
from mklib.common import relpath


class foo(Task):
    default = True
    results = ["foo.txt"]
    deps = ["bar.txt"]
    def make(self):
        src = self.deps[0].path
        dst = self.results[0].path
        self.log.info("cp %s %s", relpath(src), relpath(dst))
        shutil.copy(src, dst)

class bar(Task):
    def make(self):
        f = open("bar.txt", 'w')
        f.write(str(time.time()))
        f.close()

class clean(Task):
    def make(self):
        for p in ("foo.txt", "bar.txt"):
            if os.path.exists(p):
                os.remove(p)
