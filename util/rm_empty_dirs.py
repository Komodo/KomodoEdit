#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****
#
# Authors:
#   Trent Mick (trentm at google's mail thing)

"""
    rm_empty_dirs - trim empty dirs under the given tree

    Usage:
        rm_empty_dirs DIR...      # rm empty dirs under DIR

    Options:
        -h, --help          dump this help and exit
        -V, --version       dump this script's version and exit
        -v, --verbose       verbose output
        -q, --quiet         quiet output (only warnings and errors)
        -n, --dry-run       just go through the motions
        -i, --interactive   prompt before any removal

    Please report inadequacies to Trent Mick <trentm at google's mail thing>.
"""
#TODO:
# - convert to using optparse
#
# Dev Notes:
#

__revision__ = "$Id$"
__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))
__all__ = ["rm_empty_dirs"]

import os
from os.path import join, isdir, isfile, exists
import sys
import getopt
import logging
import glob
import stat



#---- globals

log = logging.getLogger("rm_empty_dirs")



#---- public module interface

def rm_empty_dirs(dirpath, interactive=False, dry_run=False):
    for name in os.listdir(dirpath):
        path = join(dirpath, name)
        if isdir(path):
            rm_empty_dirs(path, interactive, dry_run)
    if not os.listdir(dirpath):
        if interactive:
            raise NotImplementedError("'-i' not implemented")
        if dry_run:
            log.info("rmdir `%s' (dry-run)", dirpath)
        else:
            log.info("rmdir `%s'", dirpath)
            os.rmdir(dirpath)


#---- internal support stuff

class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.
    
    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.levelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setupLogging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)
    

# Recipe: paths_from_path_patterns (0.1) in /home/trentm/tm/recipes/cookbook
def _paths_from_path_patterns(path_patterns, files=True, dirs=False,
                              recursive=True):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is boolean (default False) indicating if dir paths should
            be yielded
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
    """
    GLOB_CHARS = '*?'
    for pattern in path_patterns:
        # Determine the set of paths matching this pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in pattern:
                paths = glob(pattern)
                break
        else:
            paths = exists(pattern) and [pattern] or []
        if not paths:
            raise OSError("%s: No such file or directory" % pattern)
        for path in paths:
            if isdir(path):
                if dirs:
                    yield path
                if recursive:
                    for dirpath, dirnames, filenames in os.walk(path):
                        if dirs:
                            for dirname in dirnames:
                                yield join(dirpath, dirname)
                        if files:
                            for filename in filenames:
                                yield join(dirpath, filename)
            elif files:
                yield path


#---- mainline

def main(argv):
    _setupLogging()

    # Parse options.
    try:
        opts, path_patterns = getopt.getopt(argv[1:], "Vvqhin",
            ["version", "verbose", "quiet", "help", "interactive", "dry-run"])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `rm_empty_dirs --help'.")
        return 1
    interactive = False
    dry_run = False
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            print "rm_empty_dirs %s" % __version__
            return
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-q", "--quiet"):
            log.setLevel(logging.WARNING)
        elif opt in ("-i", "--interactive"):
            interactive = True
        elif opt in ("-n", "--dry-run"):
            dry_run = True

    for dirpath in _paths_from_path_patterns(path_patterns, dirs=True,
                        recursive=False, files=False):
        rm_empty_dirs(dirpath, interactive=interactive, dry_run=dry_run)


if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    try:
        retval = main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            log.error("%s: %s", exc_info[0].__name__, exc_info[1])
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.DEBUG):
            import traceback
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)


