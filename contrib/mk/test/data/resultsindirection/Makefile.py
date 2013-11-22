
"""Makefile to test out-of-date determination through
a target that is just a virtual grouping of other targets with
real results (e.g. `finishup' depending on `sources').

Answer: mk will keep the make and rake semantics where 'finishup'
will always be re-run. To get around this, something like  a new "Alias"
would be required:

    class sources(Alias):
        targets = ["foo", "bar"]
"""

from os.path import *
from mklib import Task, Alias
from mklib import sh


class foo(Task):
    deps = ["src/foo.txt"]
    results = ["build/foo.txt"]
    def make(self):
        dst = self.results[0].relpath
        sh.mkdir(dirname(dst), log=self.log)
        sh.cp(self.deps[0].relpath, dst, log=self.log.info)
class bar(Task):
    deps = ["src/bar.txt"]
    results = ["build/bar.txt"]
    def make(self):
        dst = self.results[0].relpath
        sh.mkdir(dirname(dst), log=self.log)
        sh.cp(self.deps[0].relpath, dst, log=self.log.info)

class sources(Alias):
    deps = ["foo", "bar"]

class finishup(Task):
    deps = ["sources"]
    results = ["build/done.txt"]
    def make(self):
        sh.touch("build/done.txt", self.log)

class clean(Task):
    def make(self):
        if exists("build"):
            sh.rm("build")

