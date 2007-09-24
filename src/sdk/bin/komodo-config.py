#!/usr/bin/env python

"""Return configuration info for this installation of Komodo."""

__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))


import os
from os.path import dirname, join, abspath, basename, exists
import sys
import logging
import optparse



#---- public interface

class KomodoConfigError(Exception):
    pass


def get_dev_build_info(type):
    # This script is here:
    #   <moz-dist>/bin/komodo-config[.py]
    moz_dist_dir = dirname(dirname(abspath(__file__)))

    if type == "sdk-dir":
        # <moz-dist>/komodo-bits/sdk/
        return join(moz_dist_dir, "komodo-bits", "sdk")
    elif type == "idl-includes":
        idl_dir = join(get_dev_build_info("sdk-dir"), "idl")
        return '-I "%s"' % idl_dir
    else:
        raise KomodoConfigError("unknown info type: %r" % type)


def get_info(type):
    is_dev_build = exists(join(dirname(__file__), "is_dev_tree.txt"))
    if is_dev_build:
        return get_dev_build_info(type)
    
    # This script is here:
    #   [Mac OS X] <install_dir>/Contents/MacOS/komodo-config
    #   [Windows]  <install_dir>/komodo-config.py
    #   [Linux]    <install_dir>/bin/komodo-config
    if sys.platform == "win32":
        install_dir = dirname(abspath(__file__))
    elif sys.platform == "darwin":
        install_dir = dirname(dirname(dirname(abspath(__file__))))
    else:
        install_dir = dirname(dirname(abspath(__file__)))

    if type == "sdk-dir":
        # [Mac OS X] <install_dir>/Contents/SharedSupport/sdk/
        # [Windows]  <install_dir>\lib\sdk\
        # [Linux]    <install_dir>/lib/sdk/
        if sys.platform == "darwin":
            return join(install_dir, "Contents", "SharedSupport", "sdk")
        else:
            return join(install_dir, "lib", "sdk")
    elif type == "idl-includes":
        idl_dir = join(get_info("sdk-dir"), "idl")
        return '-I "%s"' % idl_dir
    else:
        raise KomodoConfigError("unknown info type: %r" % type)



#---- internal support stuff

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

def _setup_logging():
    """Setup logging to the console (controlled by -v|-q options)."""
    global log

    log = logging.getLogger("komodo-config")
    log.setLevel(logging.INFO)

    # Logging to console.
    hdlr = logging.StreamHandler()
    default_fmt = "%(name)s: %(lowerlevelname)s: %(message)s"
    info_fmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=default_fmt,
                              fmtFromLevel={logging.INFO: info_fmt})
    hdlr.setFormatter(fmtr)
    hdlr.setLevel(logging.INFO)
    logging.root.addHandler(hdlr)



#---- mainline

def main(argv):
    usage = "usage: %prog [--sdk-dir|--idl-includes|...]"
    parser = optparse.OptionParser(prog="komodo-config", usage=usage,
                                   description=__doc__)
    parser.add_option("-v", "--verbose", dest="log_level",
                      action="store_const", const=logging.DEBUG,
                      help="more verbose output")
    parser.add_option("-q", "--quiet", dest="log_level",
                      action="store_const", const=logging.WARNING,
                      help="quieter output")
    parser.add_option("--sdk-dir", dest="info",
                      action="store_const", const="sdk-dir",
                      help="print the Komodo SDK base dir")
    parser.add_option("--idl-includes", dest="info",
                      action="store_const", const="idl-includes",
                      help="print IDL include args appropriate for 'xpidl'")
    parser.set_defaults(log_level=logging.INFO, info=None)
    opts, args = parser.parse_args()
    log.setLevel(opts.log_level)

    if opts.info is None:
        parser.print_help()
        return 1
    else:
        print get_info(opts.info)


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
        if log.level <= logging.DEBUG:
            import traceback
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