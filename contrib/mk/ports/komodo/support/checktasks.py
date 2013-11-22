
"""Tasks for checking things in the Komodo tree.

    mk check:*
"""

import os
from os.path import join, dirname, normpath, abspath, isabs, exists, \
                    splitext, basename
import re
import sys
from urlparse import urlparse
from pprint import pprint

from mklib import Task, Configuration, Alias
from mklib import sh
from mklib.common import MkError



class cfg(Configuration):
    dir = ".."


class all(Alias):
    #deps = ["links", "toc", "unusedimgs", "manifest"]
    default = True



#---- internal support stuff

