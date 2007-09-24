#!/usr/bin/env python
# Copyright (c) 2005-2006 ActiveState Software Inc.
#
# Authors:
#   Trent Mick (trentm at google's mail thing)

"""
    eol - a tool for working with EOLs in text files

    Usage:
        eol FILE...                 # list EOL-type of file(s)
        eol -C LF|CRLF|... FILE...  # convert file(s) to SHORTCUT EOL type

    Options:
        -h, --help          dump this help and exit
        -V, --version       dump this script's version and exit
        -v, --verbose       verbose output
        -q, --quiet         quiet output (only warnings and errors)
        --test              run self-test and exit (use 'eol.py -v --test' for
                            verbose test output)
        -C SHORTCUT, --convert SHORTCUT
                            convert file(s) to the given EOL type;
                            SHORTCUT must be one of "LF", "CRLF", "CR"
                            or "NATIVE" (case-insensitive)

    `eol` is a tool for working with EOLs in text files: determining the
    EOL type and converting between types. `eol.py` can also be used as
    a Python module.

    Please report inadequacies to Trent Mick <trentm at google's mail thing>.
"""
#TODO:
# - a better interface for the conversion:
#   How about either 2crlf, 2lf, etc. stubs or allow eol.py to react to
#   a argv[0] name difference: 2crlf, 2lf, dos2unix, et al
# - --pretty or --align or something for nicer output
# - skip non-text files by default?
# - s/eol_type/eol/g and then must s/eol.py/something-else.py/g ???
# - s/name/eol_name/?, s/shortcut/eol_shortname/? or something else
# - shortcut_from_eol_type()?
# - add doctests to convert_text_eol_type()
# - any other conversions to take from eollib.py?
# - module usage docstring and move command-line docstring
# - Add 'hint' for the suggested eol in eol_info_from_text()? Useful for
#   Komodo if there is a pref.
# - Add 'convert_stream_eol_type(stream, eol_type, n=1024)'? Where 'n'
#   is the read chunksize and this is generator: yields chunks.
# - __all__
#
# Dev Notes:
# - If we *do* want to output like `file` then (1) we need to gather all
#   results for tabular alignment; and (2) we need to NOT use log.error
#   for non-existant files:
#        $ file foo* tools trentm.com
#        foo*:       Can't stat `foo*' (No such file or directory)
#        tools:      directory
#        trentm.com: directory


__revision__ = "$Id$"
__version_info__ = (0, 2, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import getopt
import logging
import glob
import stat



#---- globals

log = logging.getLogger("eol")

# The EOL types
CR = "\r"
LF = "\n"
CRLF = "\r\n"
if sys.platform == "win32":
    NATIVE = CRLF
else:
    # Yes, LF is the native EOL even on Mac OS X. CR is just for
    # Mac OS <=9 (a.k.a. "Mac Classic")
    NATIVE = LF
class MIXED:
    """EOL-type for files with mixed EOLs"""
    pass



#---- public module interface

def name_from_eol_type(eol_type):
    r"""name_from_eol_type(eol_type) -> English description for EOL type

        >>> name_from_eol_type(LF)
        'Unix (LF)'
        >>> name_from_eol_type('\r\n')
        'Windows (CRLF)'
        >>> name_from_eol_type(CR)
        'Mac Classic (CR)'
        >>> name_from_eol_type(MIXED)
        'Mixed'
        >>> name_from_eol_type(None)
        'No EOLs'
    """
    try:
        return {CRLF : "Windows (CRLF)",
                CR   : "Mac Classic (CR)",
                LF   : "Unix (LF)",
                MIXED: "Mixed",
                None : "No EOLs"}[eol_type]
    except KeyError:
        raise ValueError("unknown EOL type: %r" % eol_type)


def eol_type_from_shortcut(shortcut):
    r"""eol_type_from_shortcut(SHORTCUT) -> EOL type for this

     Return the EOL type for the given shortcut string:

        >>> eol_type_from_shortcut("LF")
        '\n'
        >>> eol_type_from_shortcut("CRLF")
        '\r\n'
        >>> eol_type_from_shortcut("CR")
        '\r'
        >>> eol_type_from_shortcut("CRLF") == CRLF
        True
        >>> eol_type_from_shortcut("NATIVE") == NATIVE
        True
    """
    try:
        return {"CRLF"  : CRLF,
                "CR"    : CR,
                "LF"    : LF,
                "NATIVE": NATIVE}[shortcut]
    except KeyError:
        raise ValueError("unknown EOL shortcut: %r" % eol_type)

def shortcut_from_eol_type(eol_type):
    r"""shortcut_from_eol_type(EOL-TYPE) -> EOL shortcut for this

     Return the EOL shortcut string for the given EOL type:

        >>> shortcut_from_eol_type("\n")
        'LF'
        >>> shortcut_from_eol_type("\r\n")
        'CRLF'
        >>> shortcut_from_eol_type("\r")
        'CR'
    """
    try:
        return {CRLF: "CRLF",
                CR  : "CR",
                LF  : "LF"}[eol_type]
    except KeyError:
        raise ValueError("unknown EOL type: %r" % eol_type)


def eol_info_from_text(text):
    r"""eol_info_from_text(text) -> (EOL-TYPE, SUGGESTED-EOL)
    
    Return a 2-tuple containing:
    1) The detected end-of-line type: one of CR, LF, CRLF, MIXED or None.
    2) The suggested end-of-line to use for this text: one of CR, LF or
       CRLF. This is the typically the most common EOL used in the text,
       preferring the native EOL when ambiguous.
    
        >>> eol_info_from_text('foo\nbar')
        ('\n', '\n')
        >>> eol_info_from_text('foo\r\nbar')
        ('\r\n', '\r\n')
        >>> eol_info_from_text('foo') == (None, NATIVE)  # no EOLs in text
        True
        >>> eol_info_from_text('\nfoo\nbar\r\n') == (MIXED, '\n')  # mixed text
        True
    """
    numCRLFs = text.count("\r\n")
    numCRs   = text.count("\r") - numCRLFs
    numLFs   = text.count("\n") - numCRLFs

    if numCRLFs == numLFs == numCRs == 0:
        return (None, NATIVE)

    # One a tie, prefer the native EOL.
    eols = [(numCRLFs, CRLF == NATIVE, CRLF),
            (numCRs,   CR   == NATIVE, CR),
            (numLFs,   LF   == NATIVE, LF)]
    eols.sort()

    if eols[0][0] or eols[1][0]:
        return (MIXED, eols[-1][-1])
    else:
        return (eols[-1][-1], eols[-1][-1])


def eol_info_from_file(file):
    """eol_info_from_file(PATH-OR-STREAM) -> (EOL-TYPE, SUGGESTED-EOL)
    
    Return EOL info for the given file path (or file stream).
    See eol_info_from_text() docstring for details.
    """
    if isinstance(file, basestring):
        fin = open(file, "rb")
        try:
            content = fin.read()
        finally:
            fin.close()
    else:
        content = file.read()
    return eol_info_from_text(content) 


def convert_text_eol_type(text, eol_type):
    """convert_text_eol_type(TEXT, EOL-TYPE) -> converted text

    Convert the given text to the given EOL type.
    """
    if eol_type not in (LF, CRLF, CR):
        raise ValueError("illegal eol_type: %r" % eol_type)
    import re
    return re.sub('\r\n|\r|\n', eol_type, text)


def convert_path_eol_type(path, eol_type, log=log):
    """convert_path_eol_type(PATH, EOL-TYPE)
    
    Convert the given file (in-place) to the given EOL type. If no
    changes are necessary the file is not touched.
    """
    fin = open(path, "rb")
    try:
        original = fin.read()
    finally:
        fin.close()
    converted = convert_text_eol_type(original, eol_type)
    if original != converted:
        log.info("convert %s EOLs: %s",
                 name_from_eol_type(eol_type), path)
        fout = open(path, "wb")
        try:
            fout.write(converted)
        finally:
            fout.close()


def list_path_eol_type(path):
    try:
        st = os.stat(path)
    except OSError, ex:
        #XXX Should use unicode-safe stringification here.
        log.error(str(ex))
        return
    if stat.S_ISREG(st.st_mode): # skip non-files (a la grep)
        eol_type = eol_info_from_file(path)[0]
        eol_name = name_from_eol_type(eol_type)
        log.info("%s: %s", path, eol_name)


def mixed_eol_lines_in_text(text, eol_type=None):
    r"""mixed_eol_lines_in_text(TEXT[, EOL-TYPE]) -> LINE-NUMBERS...
    
        "text" is the text to analyze
        "eol_type" indicates the expected EOL for each line: one of LF,
            CR or CRLF. It may also be left out (or None) to indicate
            that the most common EOL in the text is the expected one.
    
    Return a list of line numbers (0-based) with an EOL that does not
    match the expected EOL.

        >>> s = 'line0\nline1\r\nline2\nline3\nline4\r\nline5'
        >>> mixed_eol_lines_in_text(s)
        [1, 4]
        >>> mixed_eol_lines_in_text(s, CRLF)
        [0, 2, 3]
    """
    lines = text.splitlines(1)
    LFs = []; CRs = []; CRLFs = []
    for i in range(len(lines)):
        line = lines[i]
        if line.endswith(CRLF): CRLFs.append(i)
        elif line.endswith(LF): LFs.append(i)
        elif line.endswith(CR): CRs.append(i)

    # Determine the expected EOL.
    if eol_type is None:
        eols = [(len(CRLFs), CRLF == NATIVE, CRLF),
                (len(CRs),   CR   == NATIVE, CR),
                (len(LFs),   LF   == NATIVE, LF)]
        eols.sort() # last in list is the most common, native EOL on a tie
        eol_type = eols[-1][-1]
    
    # Get the list of lines with unexpected EOLs.
    if eol_type == LF:
        mixed_eol_lines = CRs + CRLFs
    elif eol_type == CR:
        mixed_eol_lines = LFs + CRLFs
    elif eol_type == CRLF:
        mixed_eol_lines = CRs + LFs
    else:
        raise ValueError("illegal 'eol_type' value: %r" % eol_type)
    mixed_eol_lines.sort()
    return mixed_eol_lines



#---- internal support stuff

#TODO: refer to my recipe for this
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
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)
    

#---- mainline

def main(argv):
    _setupLogging()

    # Parse options.
    try:
        opts, patterns = getopt.getopt(argv[1:], "VvqhC:",
            ["version", "verbose", "quiet", "help", "test",
             "convert="])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try `eol --help'.")
        return 1
    action = "list"
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return
        elif opt in ("-V", "--version"):
            print "eol %s" % __version__
            return
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt in ("-q", "--quiet"):
            log.setLevel(logging.WARNING)
        elif opt == "--test":
            action = "test"
        elif opt in ("-C", "--convert"):
            eol_type = eol_type_from_shortcut(optarg.upper())
            action = "convert"

    if action == "test":
        log.debug("run eol.py self-test...")
        import doctest
        doctest.testmod()
        return
    if not patterns:
        log.error("no files specified (see `eol --help' for usage)")
        return 1
    for pattern in patterns:
        if sys.platform == "win32":
            # Windows shell does not do globbing for you.
            paths = glob.glob(pattern) or [pattern]
        else:
            paths = [pattern]
        for path in paths:
            if action == "list":
                list_path_eol_type(path)
            elif action == "convert":
                convert_path_eol_type(path, eol_type)


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


