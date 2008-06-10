
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
from mklib import utils
from mklib.common import MkError

sys.path.insert(0, join(dirname(__file__), "util"))
import buildsupport


include("util/checktasks.py", ns="check")


class cfg(Configuration):
    prefix = "bk"


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


class lscolornames(Task):
    """List color names used in the Mozilla toolkit themes."""
    def make(self):
        print self.cfg.mozBin
        print self.cfg.mozSrc
        themes_dir = join(self.cfg.mozSrc, "mozilla", "toolkit", "themes")
        
        color_names = set()
        for css_path in utils.paths_from_path_patterns(
                            [themes_dir], includes=["*.css"]):
            for color_name in self._color_names_from_css_path(css_path):
                if color_name not in color_names:
                    color_names.add(color_name)
                    print color_name

    # This doesn't get colors listed in groups CSS productions like
    #   border: 1px solid black;
    _css_color_re = re.compile("(?:\w-)?color\s*: (?P<color>.*?)[;}]")
    def _color_names_from_css_path(self, css_path):
        #print css_path
        css = open(css_path, 'r').read()
        for hit in self._css_color_re.findall(css):
            color = hit.strip()
            if color.endswith("!important"):
                color = color.rsplit(None, 1)[0]
            yield color

