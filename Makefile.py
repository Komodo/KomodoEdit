
"""Makefile for the 'komodo' project.

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

sys.path.insert(0, join(dirname(__file__), "util"))
import buildsupport


include("util/checktasks.py", ns="check")


class todo(Task):
    """Print out todo's and xxx's in the docs area."""
    def make(self):
        excludes = [".svn", "*.pyc", "TO""DO.txt",
                    "*.png", "*.gif", "build", "preprocess.py",
                    "externals"]
        paths = buildsupport.paths_from_path_patterns(['.'], excludes=excludes)
        for path in paths:
            self._dump_pattern_in_path("TO\DO\\|XX\X", normpath(path))

    def _dump_pattern_in_path(self, pattern, path):
        os.system('grep -nH "%s" "%s"' % (pattern, path))


