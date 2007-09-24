#!/usr/bin/env python
# Copyright (c) 2005-2006 ActiveState Software Inc.
# Author:
#   Trent Mick (TrentM@ActiveState.com)

"""
    autowix -- preprocess WiX .in files to WiX source files

    usage:
        autowix.py

    options:
        -h, --help          Print this help and exit.
        -V, --version       Print the version of this script and exit.
        -v, --verbose       Increase the verbosity of output
        -q, --quiet         Only print output for warnings and errors.

        -f, --force         Force overwriting existing files.

    Autowix preprocessed all *.wxi.in and *.wxs.in files to *.wxi and
    *.wxs in the current directory. Its only purpose is to fill in
    "Guid" attributes in WiX source files before compilation.

    **The Problem:** Say you have a WiX project (a set of .wxi and .wxs
    files) for generating a .msi for your product. Additionally, say you
    have multiple flavours of your product and want to allow them to be
    installed side-by-side on a single Windows machine. With typical
    usage of WiX source file you hardcode guids in the "Guid" attribute
    of each <Component>:

          <Component Id="component304" DiskId="1" Guid="...">

    If that component contains resources that should NOT be shared
    between your different product flavours then you'll run in uninstall
    refcounting MSI problems -- the MSI database will *think* that
    component is shared.

    Existing solutions are to:
    1. Use different <Component>s for the difference product flavours.
       This is pain if the component definitions are otherwise very
       similar and if you have a lot of <Component>s.
    2. Use WiX's existing preprocessing facilities to create a separate
       guids.wxi with a config var for each component guid for each
       product flavour. This is pain if you have a lot of <Component>s.
    
    **Autowix's Solution:** The requirements are:
    (a) Each component has a unique guid.
    (b) Those guids must be consistent from build to build of the same
        product flavour.
    (c) Those guids must differ for different product flavours.

    These can be satisfied by calculating the guid for each component
    from the product flavour's ProductCode (to install two .msi's
    side-by-side they must have different ProductCode's) and the
    component id, as follows:

        >>> from md5 import md5
        >>> product_code = '96B8847F-2D78-488d-B049-E2B104919569'
        >>> component_id = 'component52'
        >>> "%s:%s" % (product_code, component_id)  # key
        '96B8847F-2D78-488d-B049-E2B104919569:component52'
        >>> md5(_).hexdigest().upper()  # digest
        '8F31EDC1198872F3906EF9EC33EAE043'
        >>> "%s-%s-%s-%s-%s" % (_[:8], _[8:12], _[12:16], _[16:20], _[20:])
        '8F31EDC1-1988-72F3-906E-F9EC33EAE043'

    Autowix does this replacement for all occurences of:

        Guid="$(autowix.guid)"

    in a <Component>. Note that this syntax was intentionally chosen to
    be similar to existing WiX preprocessor syntax, because I think
    WiX's compiler should reasonably grow this ability.
"""
#TODO:
# - Add ability to automatically pick out the ProductCode from the WiX proj
#   files. See notes in my black book p150.
# - add "-I" flag a la candle

__version_info__ = (0, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import (exists, isdir, isfile, abspath, basename, splitext,
                     join, dirname)
import sys
import getopt
import re
import pprint
from glob import glob
import traceback
import logging
from optparse import OptionParser
import cgi

# Import our local ElementTree.
sys.path.insert(0, dirname(__file__))
try:
    import ElementTree as ET
finally:
    del sys.path[0]



class AutowixError(Exception):
    pass



#---- globals

log = logging.getLogger("autowix")



#---- main functions

def _guid_from_keys(keys, sep=":"):
    """Return a GUID string that is an MD5 hexdigest of the ':'-joined given
    keys.
    """
    from md5 import md5
    key = sep.join(keys)
    d = md5(key).hexdigest().upper() # MSI likes uppercase hexadecimal
    guid = "%s-%s-%s-%s-%s" % (d[:8], d[8:12], d[12:16], d[16:20], d[20:])
    return guid


def _get_product_code():
    """Get the ProductCode for this WiX project.
    
    HACK: Komodo-specific hack to get the current relevant ProductCode. We
          know that the ProductCode is defined once in guids.wxi. The correct
          way to get the ProductCode involves implementing at least some
          of WiX's preprocessing functionality which is more time than I want
          to spend right now.
    """
    _define_product_code_pat = re.compile(
        '<\?define\s+ProductCode\s*=\s*"([0-9A-Fa-f-]{36})"\s*\?>'
    )
    path = "guids.wxi"
    content = open(path, 'r').read()
    matches = _define_product_code_pat.findall(content)
    if not matches:
        raise AutowixError("no ProductCode definition in `%s'" % path)
    elif len(matches) > 1:
        raise AutowixError("more than one ProductCode definition in `%s'"
                           % path)
    return matches[0]


def _autowix_one_file(in_path, product_code, force=False):
    out_path = splitext(in_path)[0]
    log.info("process `%s' -> `%s'", in_path, out_path)
    if exists(out_path) and not force:
        raise AutowixError("`%s' exists: use -f|--force to allow overwrite"
                           % out_path)

    wix_ns = "{http://schemas.microsoft.com/wix/2003/01/wi}"
    guid_marker = "$(autowix.guid)"

    # Use special PIParser() to preserve PIs and comments.
    tree = ET.parse(in_path, PIParser())
    root = tree.getroot()
    for comp in root.getiterator(wix_ns+"Component"):
        marker = comp.get("Guid")
        if marker == guid_marker:
            id = comp.get("Id")
            guid = _guid_from_keys([product_code, id])
            log.debug("... component %r guid: %r", id, guid)
            comp.set("Guid", guid)

    # PIParser wraps with a <document> -- just serialize the
    # children.
    fout = open(out_path, 'w')
    try:
        fout.write('<?xml version="1.0" encoding="utf-8"?>\n')
        for child in root:
            # The newline is feeble attempt at some prettiness of
            # the output.
            s = ET.tostring(child)
            # Make some attempts to make the output XML pretty.
            # - We know that ElementTree puts in "ns0" for the WiX
            #   namespace. We are only using the one ns so can
            #   remove those.
            s = s.replace("<ns0:", "<") \
                 .replace("</ns0:", "</") \
                 .replace("xmlns:ns0=", "xmlns=")
            # - Sprinkle in some newlines.
            fout.write(s + '\n')
    finally:
        fout.close()


def autowix(force=False):
    """Generate WiX fragments from an install image.

        "force" is a boolean indicating if existing files can be
          overwritten (only makes sense if "write_files" is true).

    This function doesn't return anything.
    
    Dev Notes:
    - In *general* this might need to take a pointer to the top-level .wxs file
      (in case there are multiple <Product> "entry points").
    """
    log.debug("autowix(force=%r)", force)
    product_code = _get_product_code()
    log.info("ProductCode is %r", product_code)
    for in_path in glob("*.wxs.in") + glob("*.wxi.in"):
        _autowix_one_file(in_path, product_code, force)



#---- ElementTree PI and comment support
# (from http://effbot.org/zone/element-pi.htm)

class PIParser(ET.XMLTreeBuilder):
   def __init__(self):
       ET.XMLTreeBuilder.__init__(self)
       # assumes ElementTree 1.2.X
       self._parser.CommentHandler = self.handle_comment
       self._parser.ProcessingInstructionHandler = self.handle_pi
       self._target.start("document", {})

   def close(self):
       self._target.end("document")
       return ET.XMLTreeBuilder.close(self)

   def handle_comment(self, data):
       self._target.start(ET.Comment, {})
       self._target.data(data)
       self._target.end(ET.Comment)

   def handle_pi(self, target, data):
       self._target.start(ET.PI, {})
       self._target.data(target + " " + data)
       self._target.end(ET.PI)



#---- internal support functions

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



#---- mainline

def main(argv):
    # Process command line.
    try:
        optlist, args = getopt.getopt(argv[1:], "h?Vvqf",
            ["help", "version", "verbose", "quiet", "force"])
    except getopt.GetoptError, ex:
        raise Error(str(ex))
        return 1
    force = False
    for opt, optarg in optlist:
        if opt in ("-h", "-?", "--help"):
            print __doc__
            return 0
        elif opt in ("-V", "--version"):
            print "autowix %s" % __version__
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-q", "--quiet"):
            log.setLevel(logging.WARN)
        elif opt in ("-f", "--force"):
            force = True

    return autowix(force=force)


if __name__ == "__main__":
    if sys.version_info[:2] <= (2,2): __file__ = sys.argv[0]
    _setup_logging()
    try:
        retval = main(sys.argv)
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


