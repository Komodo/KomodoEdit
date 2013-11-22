
import os
from os.path import join, isdir
from mklib import sh
from mklib import TaskGroup, Task

build_dir = "build"

class src_files(TaskGroup):
    def pairs(self):
        for path in os.listdir("src"):
            if path == ".svn": continue
            dep = join("src", path)
            if isdir(dep): continue
            yield dep, join(build_dir, path)

    def make_pair(self, src, dst):
        sh.cp(src, dst, self.log)


class clean(Task):
    def make(self):
        sh.rm(build_dir)
