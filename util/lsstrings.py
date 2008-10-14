#!/usr/bin/env python
# Copyright (c) 2008 ActiveState Software Inc.

r"""List the string-bundle strings/properties used in the given JavaScript
file.

Usage:
    lsstrings JAVASCRIPT-PATH
"""

__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import join, dirname, basename, abspath, exists, normpath, expanduser
import sys
import re
from pprint import pprint, pformat
import traceback
import datetime
import types
import logging
import optparse





#---- exceptions

class Error(Exception):
    pass



#---- globals

log = logging.getLogger("lsstrings")



#---- main functions

def lsstrings(path):
    log.debug("lsstrings `%s'", path)
    if not path.endswith(".js"):
        raise Error("`%s' doesn't look like a JavaScipt file" % path)
    javascript = open(path, 'r').read()
    
    # Look for loaded properties URLs.
    create_bundle_re = re.compile(r'\.createBundle\((.*?)\)')
    properties_urls = set(u[1:-1] for u in create_bundle_re.findall(javascript))
    if properties_urls:
        log.debug("loaded properties URLs: %s", ', '.join(properties_urls))

    # Try to map properties URLs to actual files.
    locale_dir = None
    path_bits = _splitall(abspath(path))
    if "chrome" in path_bits:
        assert path_bits.count("chrome") == 1
        chrome_idx = path_bits.index("chrome")
        if path_bits[chrome_idx:chrome_idx+3] == ["chrome", "komodo", "content"]:
            locale_bits = path_bits[:chrome_idx+2] + ["locale", "en-US"]
            locale_dir = join(*locale_bits)
    if not locale_dir and properties_urls:
        log.warn("couldn't determine 'locale' dir for local paths to '%s'",
                 "', '".join(properties_urls))
    if locale_dir:
        properties_paths = []
        for u in properties_urls:
            assert u.startswith("chrome://komodo/locale/")
            p = normpath(join(locale_dir, u[len("chrome://komodo/locale/"):]))
            properties_paths.append(p)
    
    # Load all strings from the properties paths which will be used to
    # check against actual usage.
    strings = set()
    for p in properties_paths:
        for line in open(p, 'r'):
            if not line.strip():
                continue
            if line.strip().startswith("#"):
                continue
            strings.add(line.strip().split('=', 1)[0])
    #pprint(strings)

    # Find every string-bundle usage in the JS file.
    string_usage_re = re.compile(r'''\.(GetStringFromName|formatStringFromName)\(('|")(.*?)\2''')
    usages = set()
    for m in string_usage_re.findall(javascript):
        usage = m[2]
        if usage in usages:
            continue
        usages.add(usage)
        yield StringUsage(usage, usage in strings)


#---- internal support stuff

class StringUsage(object):
    def __init__(self, name, found_in_loaded_bundles):
        self.name = name
        self.found_in_loaded_bundles = found_in_loaded_bundles
    def __str__(self):
        if self.found_in_loaded_bundles:
            return self.name
        else:
            return "%s (warning: not found in loaded string bundles)" % (self.name, )
        


# Recipe: splitall (0.2)
def _splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    allparts = [p for p in allparts if p] # drop empty strings 
    return allparts



#---- mainline

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

def _setup_logging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)


def main(argv):
    usage = "usage: %prog"
    version = "%prog "+__version__
    parser = optparse.OptionParser(usage=usage, version=version,
                                   description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("-w", "--list-warnings-only", action="store_true",
        help="Only list those string property usages that can't be found "
             "in loaded string bundles")
    parser.set_defaults(log_level=logging.INFO, list_warnings_only=False)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    for path in args:
        for usage in lsstrings(path):
            if opts.list_warnings_only and usage.found_in_loaded_bundles:
                continue
            print usage


if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    _setup_logging()
    try:
        retval = main(sys.argv)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if log.isEnabledFor(logging.DEBUG):
            print
            traceback.print_exception(*exc_info)
        else:
            if hasattr(exc_info[0], "__name__"):
                #log.error("%s: %s", exc_info[0].__name__, exc_info[1])
                log.error(exc_info[1])
            else:  # string exception
                log.error(exc_info[0])
        sys.exit(1)
    else:
        sys.exit(retval)


