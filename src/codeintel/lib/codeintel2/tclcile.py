#!/usr/bin/env python
# Copyright (c) 2005-2006 ActiveState Software Inc.
#
# Contributors:
#   Eric Promislow (EricP@ActiveState.com)

"""
    tclcile - a Code Intelligence Language Engine for the Tcl language

    Module Usage:
        from tclcile import scan
        mtime = os.stat("foo.rb")[stat.ST_MTIME]
        content = open("foo.rb", "r").read()
        scan(content, "foo.rb", mtime=mtime)
    
    Command-line Usage:
        tclcile.py [<options>...] [<Tcl files>...]

    Options:
        -h, --help          dump this help and exit
        -V, --version       dump this script's version and exit
        -v, --verbose       verbose output, use twice for more verbose output
        -f, --filename <path>   specify the filename of the file content
                            passed in on stdin, this is used for the "path"
                            attribute of the emitted <file> tag.
        --md5=<string>      md5 hash for the input
        --mtime=<secs>      modification time for output info, in #secs since
                            1/1/70.
        -L, --language <name>
                            the language of the file being scanned
        -c, --clock         print timing info for scans (CIX is not printed)

    One or more Tcl files can be specified as arguments or content can be
    passed in on stdin. A directory can also be specified, in which case
    all .rb files in that directory are scanned.

    This is a Language Engine for the Code Intelligence (codeintel) system.
    Code Intelligence XML format. See:
        http://specs.tl.activestate.com/kd/kd-0100.html
    
    The command-line interface will return non-zero iff the scan failed.
"""

import os
from os.path import basename, splitext, isfile, isdir, join
import sys
import getopt
import md5
import re
import logging
import glob
import time
import stat

from ciElementTree import Element, SubElement, tostring
from SilverCity import ScintillaConstants

from codeintel2 import tcl_lexer, tcl_parser
from codeintel2.parseutil import getAttrStr, xmlencode, cdataescape
from codeintel2.common import CILEError
from codeintel2 import parser_cix

#---- exceptions

class TclCILEError(CILEError):
    pass


#---- global data

_version_ = (0, 1, 0)
log = logging.getLogger("tclcile")
#log.setLevel(logging.DEBUG)

_gClockIt = 0   # if true then we are gathering timing data
_gClock = None  # if gathering timing data this is set to time retrieval fn
_gStartTime = None   # start time of current file being scanned

def scan(content, filename, md5sum=None, mtime=None, lang="Tcl"):
    log.info("scan '%s'", filename)
    content = content.expandtabs(8)
    tokenizer = tcl_lexer.TclLexer(content)
    parser = tcl_parser.Parser(tokenizer, lang)
    if 1:
        parse_tree = parser.parse()
        if mtime is None:
            actual_mtime = int(time.time())
        else:
            actual_mtime = mtime
        if md5sum is None:
            actual_md5 = md5.new(content).hexdigest()
        else:
            actual_md5 = md5sum
        return parser_cix.produce_cix(parse_tree, filename, actual_md5, actual_mtime, "Tcl", "tclcile")


def scan_purelang(content, filename):
    content = content.expandtabs(8)
    tokenizer = tcl_lexer.TclLexer(content)
    parser = tcl_parser.Parser(tokenizer, "Tcl")
    parse_tree = parser.parse()
    #XXX Change last arg from "Tcl" to "tclcile"?
    tree = parser_cix.produce_elementTree_cix(parse_tree, filename, "Tcl",
                                              "Tcl")
    return tree


def scan_multilang(tokens, module_elem):
    """Build the Tcl module CIX element tree.

        "tokens" is a generator of UDL tokens for this UDL-based
            multi-lang document.
        "module_elem" is the <module> element of a CIX element tree on
            which the Tcl module should be built.

    This should return a list of the CSL tokens in the token stream.
    """
        
    tokenizer = tcl_lexer.TclMultiLangLexer(tokens)
    parser = tcl_parser.Parser(tokenizer, "AOL")
    parse_tree = parser.parse()
    parser_cix.produce_elementTree_contents_cix(parse_tree, module_elem)
    csl_tokens = tokenizer.get_csl_tokens()
    return csl_tokens


#---- mainline

def main(argv):
    logging.basicConfig()
    # Parse options.
    try:
        opts, args = getopt.getopt(argv[1:], "Vvhf:cL:",
            ["version", "verbose", "help", "filename=", "md5=", "mtime=",
             "clock", "language="])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `tclcile --help'.")
        return 1
    numVerboses = 0
    stdinFilename = None
    md5sum = None
    mtime = None
    lang = "Tcl"
    global _gClockIt
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            ver = '.'.join([str(part) for part in _version_])
            print "tclcile %s" % ver
            return
        elif opt in ("-v", "--verbose"):
            numVerboses += 1
            if numVerboses == 1:
                log.setLevel(logging.INFO)
            else:
                log.setLevel(logging.DEBUG)
        elif opt in ("-f", "--filename"):
            stdinFilename = optarg
        elif opt in ("-L", "--language"):
            lang = optarg
        elif opt in ("--md5",):
            md5sum = optarg
        elif opt in ("--mtime",):
            mtime = optarg
        elif opt in ("-c", "--clock"):
            _gClockIt = 1
            global _gClock
            if sys.platform.startswith("win"):
                _gClock = time.clock
            else:
                _gClock = time.time

    if len(args) == 0:
        contentOnStdin = 1
        filenames = [stdinFilename or "<stdin>"]
    else:
        contentOnStdin = 0
        paths = []
        for arg in args:
            paths += glob.glob(arg)
        filenames = []
        for path in paths:
            if isfile(path):
                filenames.append(path)
            elif isdir(path):
                rbfiles = [join(path, n) for n in os.listdir(path)
                           if splitext(n)[1] == ".rb"]
                rbfiles = [f for f in rbfiles if isfile(f)]
                filenames += rbfiles

    try:
        for filename in filenames:
            if contentOnStdin:
                log.debug("reading content from stdin")
                content = sys.stdin.read()
                log.debug("finished reading content from stdin")
                if mtime is None:
                    mtime = int(time.time())
            else:
                if mtime is None:
                    mtime = int(os.stat(filename)[stat.ST_MTIME])
                content = open(filename, 'r').read()

            if _gClockIt:
                sys.stdout.write("scanning '%s'..." % filename)
                global _gStartTime
                _gStartTime = _gClock()
            data = tostring(scan_purelang(content, filename))
            # data = scan(content, filename, md5sum, mtime, lang=lang)
            if _gClockIt:
                sys.stdout.write(" %.3fs\n" % (_gClock()-_gStartTime))
            elif data:
                sys.stdout.write(data)
    except KeyboardInterrupt:
        log.debug("user abort")
        return 1
    if 0: #except Exception, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            print
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))

