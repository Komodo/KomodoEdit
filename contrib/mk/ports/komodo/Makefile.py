
"""Makefile for Komodo

${common_task_list}

See `mk -h' for options.
"""

import os
from os.path import join, dirname, normpath, abspath, isabs, exists, \
                    splitext, basename
import re
import sys
from pprint import pprint

from mklib import Task, Configuration, Alias, include
from mklib import sh
from mklib.common import MkError

sys.path.insert(0, join(_mk_makefile_.dir, "support"))



include("support/checktasks.py", ns="check")


class cfg(Configuration):
    pass




class clean(Task):
    """Remove the build/obj dir."""
    def make(self):
        if exists(self.cfg.obj_dir):
            sh.rm(self.cfg.obj_dir, self.log)

class distclean(Task):
    """Remove all build/configure products."""
    deps = ["clean"]
    def make(self):
        if exists("config.py"):
            sh.rm("config.py", self.log)
        

class todo(Task):
    """Print out todo's and xxx's in the docs area."""
    def make(self):
        excludes = [".svn", "*.pyc", "TO""DO.txt",
                    "*.png", "*.gif", "build",
                    "externals"]
        for path in paths_from_path_patterns(['.'], excludes=excludes):
            self._dump_pattern_in_path("TO\DO\\|XX\X", normpath(path))

        path = join(self.dir, "TO""DO.txt")
        todos = re.compile("^- ", re.M).findall(open(path, 'r').read())
        print "(plus %d TO""DOs from TO""DO.txt)" % len(todos)

    def _dump_pattern_in_path(self, pattern, path):
        os.system('grep -nH "%s" "%s"' % (pattern, path))


