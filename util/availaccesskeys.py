#!/usr/bin/env python
#
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

"""List available accesskeys for the given .xul dialog/window.
    
Notes:
- This doesn't catch dynamically added accesskeys, of course.
"""
#TODO:
# - Add support for looking at DTD entities.

__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import basename
import sys
import re
import traceback
import optparse
import logging
from pprint import pprint, pformat
from glob import glob
import codecs



#---- exceptions

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("availaccesskeys")



#---- main functionality

def avail_accesskeys(xul_path):
    content = codecs.open(xul_path, 'r', encoding="utf-8").read()
    accesskey_re = re.compile(r'''accesskey=('|")(\w)\1''')
    
    avail = set('abcdefghijklmnopqrstuvwxyz1234567890-=.,/;\'[]\`')
    
    for quote, accesskey in accesskey_re.findall(content):
        norm_accesskey = accesskey.lower()
        if norm_accesskey not in avail:
            log.warn("%r accesskey is a potential duplicate in `%s'",
                     accesskey, basename(xul_path))
        avail.discard(norm_accesskey)

    for ch in avail:
        yield ch



#---- internal support stuff

class _NoReflowFormatter(optparse.IndentedHelpFormatter):
    """An optparse formatter that does NOT reflow the description."""
    def format_description(self, description):
        return description or ""

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
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
        record.lowerlevelname = record.levelname.lower()
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

def _setup_logging(stream=None):
    """Do logging setup:

    We want a prettier default format:
         do: level: ...
    Spacing. Lower case. Skip " level:" if INFO-level. 
    """
    hdlr = logging.StreamHandler(stream)
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)



#---- mainline

def main(argv):
    usage = "usage: %prog XUL_PATH"
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage,
        version=version, description=__doc__,
        formatter=_NoReflowFormatter())
    parser.add_option("-q", "--quiet", dest="log_level",
        action="store_const", const=logging.WARNING,
        help="quieter output")
    parser.add_option("-v", "--verbose", dest="log_level",
        action="store_const", const=logging.INFO-1,
        help="more verbose output")
    parser.add_option("-d", "--debug", dest="log_level",
        action="store_const", const=logging.DEBUG,
        help="verbose debugging output")
    parser.set_defaults(log_level=logging.INFO)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    # Validate and prepare the args.
    if len(args) != 1:
        log.error("incorrect number of arguments (see `%s --help')", argv[0])
        return 1
    xul_path = args[0]

    for accesskey in avail_accesskeys(xul_path):
        print accesskey


if __name__ == "__main__":
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            exc_str = str(exc_info[1])
            sep = ('\n' in exc_str and '\n' or ' ')
            where_str = ""
            tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
            in_str = (tb_func != "<module>"
                      and " in %s" % tb_func
                      or "")
            where_str = "%s(%s#%s%s)" % (sep, tb_path, tb_lineno, in_str)
            log.error("%s%s", exc_str, where_str)
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.INFO-1):
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)

