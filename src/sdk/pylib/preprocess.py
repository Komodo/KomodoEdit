#!/usr/bin/env python
# Copyright (c) 2002-2008 ActiveState Software Inc.
# License: MIT License (http://www.opensource.org/licenses/mit-license.php)

"""
    Preprocess a file.

    Command Line Usage:
        preprocess [<options>...] <infile>

    Options:
        -h, --help      Print this help and exit.
        -V, --version   Print the version info and exit.
        -v, --verbose   Give verbose output for errors.

        -o <outfile>    Write output to the given file instead of to stdout.
        -f, --force     Overwrite given output file. (Otherwise an IOError
                        will be raised if <outfile> already exists.
        -D <define>     Define a variable for preprocessing. <define>
                        can simply be a variable name (in which case it
                        will be true) or it can be of the form
                        <var>=<val>. An attempt will be made to convert
                        <val> to an integer so "-D FOO=0" will create a
                        false value.
        -I <dir>        Add an directory to the include path for
                        #include directives.

        -k, --keep-lines    Emit empty lines for preprocessor statement
                        lines and skipped output lines. This allows line
                        numbers to stay constant.
        -s, --substitute    Substitute defines into emitted lines. By
                        default substitution is NOT done because it
                        currently will substitute into program strings.
        -c, --content-types-path <path>
                        Specify a path to a content.types file to assist
                        with filetype determination. See the
                        `_gDefaultContentTypes` string in this file for
                        details on its format.

    Module Usage:
        from preprocess import preprocess
        preprocess(infile, outfile=sys.stdout, defines={}, force=0,
                   keepLines=0, includePath=[], substitute=0,
                   contentType=None)

    The <infile> can be marked up with special preprocessor statement lines
    of the form:
        <comment-prefix> <preprocessor-statement> <comment-suffix>
    where the <comment-prefix/suffix> are the native comment delimiters for
    that file type. 


    Examples
    --------

    HTML (*.htm, *.html) or XML (*.xml, *.kpf, *.xul) files:

        <!-- #if FOO -->
        ...
        <!-- #endif -->
    
    Python (*.py), Perl (*.pl), Tcl (*.tcl), Ruby (*.rb), Bash (*.sh),
    or make ([Mm]akefile*) files:

        # #if defined('FAV_COLOR') and FAV_COLOR == "blue"
        ...
        # #elif FAV_COLOR == "red"
        ...
        # #else
        ...
        # #endif

    C (*.c, *.h), C++ (*.cpp, *.cxx, *.cc, *.h, *.hpp, *.hxx, *.hh),
    Java (*.java), PHP (*.php) or C# (*.cs) files:

        // #define FAV_COLOR 'blue'
        ...
        /* #ifndef FAV_COLOR */
        ...
        // #endif

    Fortran 77 (*.f) or 90/95 (*.f90) files:

        C     #if COEFF == 'var'
              ...
        C     #endif

    And other languages.


    Preprocessor Syntax
    -------------------

    - Valid statements:
        #define <var> [<value>]
        #undef <var>
        #ifdef <var>
        #ifndef <var>
        #if <expr>
        #elif <expr>
        #else
        #endif
        #error <error string>
        #include "<file>"
        #include <var>
      where <expr> is any valid Python expression.
    - The expression after #if/elif may be a Python statement. It is an
      error to refer to a variable that has not been defined by a -D
      option or by an in-content #define.
    - Special built-in methods for expressions:
        defined(varName)    Return true if given variable is defined.  


    Tips
    ----

    A suggested file naming convention is to let input files to
    preprocess be of the form <basename>.p.<ext> and direct the output
    of preprocess to <basename>.<ext>, e.g.:
        preprocess -o foo.py foo.p.py
    The advantage is that other tools (esp. editors) will still
    recognize the unpreprocessed file as the original language.
"""

__version_info__ = (1, 1, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import getopt
import types
import re
import pprint



#---- exceptions

class PreprocessError(Exception):
    def __init__(self, errmsg, file=None, lineno=None, line=None):
        self.errmsg = str(errmsg)
        self.file = file
        self.lineno = lineno
        self.line = line
        Exception.__init__(self, errmsg, file, lineno, line)
    def __str__(self):
        s = ""
        if self.file is not None:
            s += self.file + ":"
        if self.lineno is not None:
            s += str(self.lineno) + ":"
        if self.file is not None or self.lineno is not None:
            s += " "
        s += self.errmsg
        #if self.line is not None:
        #    s += ": " + self.line
        return s



#---- global data

# Comment delimiter info.
#   A mapping of content type to a list of 2-tuples defining the line
#   prefix and suffix for a comment. Each prefix or suffix can either
#   be a string (in which case it is transformed into a pattern allowing
#   whitespace on either side) or a compiled regex.
_commentGroups = {
    "Python":     [ ('#', '') ],
    "Perl":       [ ('#', '') ],
    "PHP":        [ ('/*', '*/'), ('//', ''), ('#', '') ],
    "Ruby":       [ ('#', '') ],
    "Tcl":        [ ('#', '') ],
    "Shell":      [ ('#', '') ],
    # Allowing for CSS and JavaScript comments in XML/HTML.
    "XML":        [ ('<!--', '-->'), ('/*', '*/'), ('//', '') ],
    "HTML":       [ ('<!--', '-->'), ('/*', '*/'), ('//', '') ],
    "Makefile":   [ ('#', '') ],
    "JavaScript": [ ('/*', '*/'), ('//', '') ],
    "CSS":        [ ('/*', '*/') ],
    "C":          [ ('/*', '*/') ],
    "C++":        [ ('/*', '*/'), ('//', '') ],
    "Java":       [ ('/*', '*/'), ('//', '') ],
    "C#":         [ ('/*', '*/'), ('//', '') ],
    "IDL":        [ ('/*', '*/'), ('//', '') ],
    "Text":       [ ('#', '') ],
    "Fortran":    [ (re.compile(r'^[a-zA-Z*$]\s*'), ''), ('!', '') ],
    "TeX":        [ ('%', '') ],
}



#---- internal logging facility

class _Logger:
    DEBUG, INFO, WARN, ERROR, CRITICAL = range(5)
    def __init__(self, name, level=None, streamOrFileName=sys.stderr):
        self._name = name
        if level is None:
            self.level = self.WARN
        else:
            self.level = level
        if type(streamOrFileName) == types.StringType:
            self.stream = open(streamOrFileName, 'w')
            self._opennedStream = 1
        else:
            self.stream = streamOrFileName
            self._opennedStream = 0
    def __del__(self):
        if self._opennedStream:
            self.stream.close()
    def getLevel(self):
        return self.level
    def setLevel(self, level):
        self.level = level
    def _getLevelName(self, level):
        levelNameMap = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARN: "WARN",
            self.ERROR: "ERROR",
            self.CRITICAL: "CRITICAL",
        }
        return levelNameMap[level]
    def isEnabled(self, level):
        return level >= self.level
    def isDebugEnabled(self): return self.isEnabled(self.DEBUG)
    def isInfoEnabled(self): return self.isEnabled(self.INFO)
    def isWarnEnabled(self): return self.isEnabled(self.WARN)
    def isErrorEnabled(self): return self.isEnabled(self.ERROR)
    def isFatalEnabled(self): return self.isEnabled(self.FATAL)
    def log(self, level, msg, *args):
        if level < self.level:
            return
        message = "%s: %s: " % (self._name, self._getLevelName(level).lower())
        message = message + (msg % args) + "\n"
        self.stream.write(message)
        self.stream.flush()
    def debug(self, msg, *args):
        self.log(self.DEBUG, msg, *args)
    def info(self, msg, *args):
        self.log(self.INFO, msg, *args)
    def warn(self, msg, *args):
        self.log(self.WARN, msg, *args)
    def error(self, msg, *args):
        self.log(self.ERROR, msg, *args)
    def fatal(self, msg, *args):
        self.log(self.CRITICAL, msg, *args)

log = _Logger("preprocess", _Logger.WARN)



#---- internal support stuff

def _evaluate(expr, defines):
    """Evaluate the given expression string with the given context.

    WARNING: This runs eval() on a user string. This is unsafe.
    """
    #interpolated = _interpolate(s, defines)
    try:
        rv = eval(expr, {'defined':lambda v: v in defines}, defines)
    except Exception, ex:
        msg = str(ex)
        if msg.startswith("name '") and msg.endswith("' is not defined"):
            # A common error (at least this is presumed:) is to have
            #   defined(FOO)   instead of   defined('FOO')
            # We should give a little as to what might be wrong.
            # msg == "name 'FOO' is not defined"  -->  varName == "FOO"
            varName = msg[len("name '"):-len("' is not defined")]
            if expr.find("defined(%s)" % varName) != -1:
                # "defined(FOO)" in expr instead of "defined('FOO')"
                msg += " (perhaps you want \"defined('%s')\" instead of "\
                       "\"defined(%s)\")" % (varName, varName)
        elif msg.startswith("invalid syntax"):
            msg = "invalid syntax: '%s'" % expr
        raise PreprocessError(msg, defines['__FILE__'], defines['__LINE__'])
    log.debug("evaluate %r -> %s (defines=%r)", expr, rv, defines)
    return rv


#---- module API

def preprocess(infile, outfile=sys.stdout, defines={},
               force=0, keepLines=0, includePath=[], substitute=0, 
               contentType=None, contentTypesRegistry=None,
               __preprocessedFiles=None):
    """Preprocess the given file.

    "infile" is the input path.
    "outfile" is the output path or stream (default is sys.stdout).
    "defines" is a dictionary of defined variables that will be
        understood in preprocessor statements. Keys must be strings and,
        currently, only the truth value of any key's value matters.
    "force" will overwrite the given outfile if it already exists. Otherwise
        an IOError will be raise if the outfile already exists.
    "keepLines" will cause blank lines to be emitted for preprocessor lines
        and content lines that would otherwise be skipped.
    "includePath" is a list of directories to search for given #include
        directives. The directory of the file being processed is presumed.
    "substitute", if true, will allow substitution of defines into emitted
        lines. (NOTE: This substitution will happen within program strings
        as well. This may not be what you expect.)
    "contentType" can be used to specify the content type of the input
        file. It not given, it will be guessed.
    "contentTypesRegistry" is an instance of ContentTypesRegistry. If not specified
        a default registry will be created.
    "__preprocessedFiles" (for internal use only) is used to ensure files
        are not recusively preprocessed.

    Returns the modified dictionary of defines or raises PreprocessError if
    there was some problem.
    """
    if __preprocessedFiles is None: 
        __preprocessedFiles = []
    log.info("preprocess(infile=%r, outfile=%r, defines=%r, force=%r, "\
             "keepLines=%r, includePath=%r, contentType=%r, "\
             "__preprocessedFiles=%r)", infile, outfile, defines, force,
             keepLines, includePath, contentType, __preprocessedFiles)
    absInfile = os.path.normpath(os.path.abspath(infile))
    if absInfile in __preprocessedFiles:
        raise PreprocessError("detected recursive #include of '%s'"\
                              % infile)
    __preprocessedFiles.append(os.path.abspath(infile))

    # Determine the content type and comment info for the input file.
    if contentType is None:
        registry = contentTypesRegistry or getDefaultContentTypesRegistry()
        contentType = registry.getContentType(infile)
        if contentType is None:
            contentType = "Text"
            log.warn("defaulting content type for '%s' to '%s'",
                     infile, contentType)
    try:
        cgs = _commentGroups[contentType]
    except KeyError:
        raise PreprocessError("don't know comment delimiters for content "\
                              "type '%s' (file '%s')"\
                              % (contentType, infile))

    # Generate statement parsing regexes. Basic format:
    #       <comment-prefix> <preprocessor-stmt> <comment-suffix>
    #  Examples:
    #       <!-- #if foo -->
    #       ...
    #       <!-- #endif -->
    #
    #       # #if BAR
    #       ...
    #       # #else
    #       ...
    #       # #endif
    stmts = ['#\s*(?P<op>if|elif|ifdef|ifndef)\s+(?P<expr>.*?)',
             '#\s*(?P<op>else|endif)',
             '#\s*(?P<op>error)\s+(?P<error>.*?)',
             '#\s*(?P<op>define)\s+(?P<var>[^\s]*?)(\s+(?P<val>.+?))?',
             '#\s*(?P<op>undef)\s+(?P<var>[^\s]*?)',
             '#\s*(?P<op>include)\s+"(?P<fname>.*?)"',
             r'#\s*(?P<op>include)\s+(?P<var>[^\s]+?)',
            ]
    patterns = []
    for stmt in stmts:
        # The comment group prefix and suffix can either be just a
        # string or a compiled regex.
        for cprefix, csuffix in cgs:
            if hasattr(cprefix, "pattern"):
                pattern = cprefix.pattern
            else:
                pattern = r"^\s*%s\s*" % re.escape(cprefix)
            pattern += stmt
            if hasattr(csuffix, "pattern"):
                pattern += csuffix.pattern
            else:
                pattern += r"\s*%s\s*$" % re.escape(csuffix)
            patterns.append(pattern)
    stmtRes = [re.compile(p) for p in patterns]

    # Process the input file.
    # (Would be helpful if I knew anything about lexing and parsing
    # simple grammars.)
    fin = open(infile, 'r')
    lines = fin.readlines()
    fin.close()
    if type(outfile) in types.StringTypes:
        if force and os.path.exists(outfile):
            os.chmod(outfile, 0777)
            os.remove(outfile)
        fout = open(outfile, 'w')
    else:
        fout = outfile

    defines['__FILE__'] = infile
    SKIP, EMIT = range(2) # states
    states = [(EMIT,   # a state is (<emit-or-skip-lines-in-this-section>,
               0,      #             <have-emitted-in-this-if-block>,
               0)]     #             <have-seen-'else'-in-this-if-block>)
    lineNum = 0
    for line in lines:
        lineNum += 1
        log.debug("line %d: %r", lineNum, line)
        defines['__LINE__'] = lineNum

        # Is this line a preprocessor stmt line?
        #XXX Could probably speed this up by optimizing common case of
        #    line NOT being a preprocessor stmt line.
        for stmtRe in stmtRes:
            match = stmtRe.match(line)
            if match:
                break
        else:
            match = None

        if match:
            op = match.group("op")
            log.debug("%r stmt (states: %r)", op, states)
            if op == "define":
                if not (states and states[-1][0] == SKIP):
                    var, val = match.group("var", "val")
                    if val is None:
                        val = None
                    else:
                        try:
                            val = eval(val, {}, {})
                        except:
                            pass
                    defines[var] = val
            elif op == "undef":
                if not (states and states[-1][0] == SKIP):
                    var = match.group("var")
                    try:
                        del defines[var]
                    except KeyError:
                        pass
            elif op == "include":
                if not (states and states[-1][0] == SKIP):
                    if "var" in match.groupdict():
                        # This is the second include form: #include VAR
                        var = match.group("var")
                        f = defines[var]
                    else:
                        # This is the first include form: #include "path"
                        f = match.group("fname")
                        
                    for d in [os.path.dirname(infile)] + includePath:
                        fname = os.path.normpath(os.path.join(d, f))
                        if os.path.exists(fname):
                            break
                    else:
                        raise PreprocessError("could not find #include'd file "\
                                              "\"%s\" on include path: %r"\
                                              % (f, includePath))
                    defines = preprocess(fname, fout, defines, force,
                                         keepLines, includePath, substitute,
                                         contentTypesRegistry=contentTypesRegistry, 
                                         __preprocessedFiles=__preprocessedFiles)
            elif op in ("if", "ifdef", "ifndef"):
                if op == "if":
                    expr = match.group("expr")
                elif op == "ifdef":
                    expr = "defined('%s')" % match.group("expr")
                elif op == "ifndef":
                    expr = "not defined('%s')" % match.group("expr")
                try:
                    if states and states[-1][0] == SKIP:
                        # Were are nested in a SKIP-portion of an if-block.
                        states.append((SKIP, 0, 0))
                    elif _evaluate(expr, defines):
                        states.append((EMIT, 1, 0))
                    else:
                        states.append((SKIP, 0, 0))
                except KeyError:
                    raise PreprocessError("use of undefined variable in "\
                                          "#%s stmt" % op, defines['__FILE__'],
                                          defines['__LINE__'], line)
            elif op == "elif":
                expr = match.group("expr")
                try:
                    if states[-1][2]: # already had #else in this if-block
                        raise PreprocessError("illegal #elif after #else in "\
                            "same #if block", defines['__FILE__'],
                            defines['__LINE__'], line)
                    elif states[-1][1]: # if have emitted in this if-block
                        states[-1] = (SKIP, 1, 0)
                    elif states[:-1] and states[-2][0] == SKIP:
                        # Were are nested in a SKIP-portion of an if-block.
                        states[-1] = (SKIP, 0, 0)
                    elif _evaluate(expr, defines):
                        states[-1] = (EMIT, 1, 0)
                    else:
                        states[-1] = (SKIP, 0, 0)
                except IndexError:
                    raise PreprocessError("#elif stmt without leading #if "\
                                          "stmt", defines['__FILE__'],
                                          defines['__LINE__'], line)
            elif op == "else":
                try:
                    if states[-1][2]: # already had #else in this if-block
                        raise PreprocessError("illegal #else after #else in "\
                            "same #if block", defines['__FILE__'],
                            defines['__LINE__'], line)
                    elif states[-1][1]: # if have emitted in this if-block
                        states[-1] = (SKIP, 1, 1)
                    elif states[:-1] and states[-2][0] == SKIP:
                        # Were are nested in a SKIP-portion of an if-block.
                        states[-1] = (SKIP, 0, 1)
                    else:
                        states[-1] = (EMIT, 1, 1)
                except IndexError:
                    raise PreprocessError("#else stmt without leading #if "\
                                          "stmt", defines['__FILE__'],
                                          defines['__LINE__'], line)
            elif op == "endif":
                try:
                    states.pop()
                except IndexError:
                    raise PreprocessError("#endif stmt without leading #if"\
                                          "stmt", defines['__FILE__'],
                                          defines['__LINE__'], line)
            elif op == "error":
                if not (states and states[-1][0] == SKIP):
                    error = match.group("error")
                    raise PreprocessError("#error: "+error, defines['__FILE__'],
                                          defines['__LINE__'], line)
            log.debug("states: %r", states)
            if keepLines:
                fout.write("\n")
        else:
            try:
                if states[-1][0] == EMIT:
                    log.debug("emit line (%s)" % states[-1][1])
                    # Substitute all defines into line.
                    # XXX Should avoid recursive substitutions. But that
                    #     would be a pain right now.
                    sline = line
                    if substitute:
                        for name in reversed(sorted(defines, key=len)):
                            value = defines[name]
                            sline = sline.replace(name, str(value))
                    fout.write(sline)
                elif keepLines:
                    log.debug("keep blank line (%s)" % states[-1][1])
                    fout.write("\n")
                else:
                    log.debug("skip line (%s)" % states[-1][1])
            except IndexError:
                raise PreprocessError("superfluous #endif before this line",
                                      defines['__FILE__'],
                                      defines['__LINE__'])
    if len(states) > 1:
        raise PreprocessError("unterminated #if block", defines['__FILE__'],
                              defines['__LINE__'])
    elif len(states) < 1:
        raise PreprocessError("superfluous #endif on or before this line",
                              defines['__FILE__'], defines['__LINE__'])

    if fout != outfile:
        fout.close()

    return defines


#---- content-type handling

_gDefaultContentTypes = """
    # Default file types understood by "preprocess.py".
    #
    # Format is an extension of 'mime.types' file syntax.
    #   - '#' indicates a comment to the end of the line.
    #   - a line is:
    #       <filetype> [<pattern>...]
    #     where,
    #       <filetype>'s are equivalent in spirit to the names used in the Windows
    #           registry in HKCR, but some of those names suck or are inconsistent;
    #           and
    #       <pattern> is a suffix (pattern starts with a '.'), a regular expression
    #           (pattern is enclosed in '/' characters), a full filename (anything
    #           else).
    #
    # Notes on case-sensitivity:
    #
    # A suffix pattern is case-insensitive on Windows and case-sensitive
    # elsewhere.  A filename pattern is case-sensitive everywhere. A regex
    # pattern's case-sensitivity is defined by the regex. This means it is by
    # default case-sensitive, but this can be changed using Python's inline
    # regex option syntax. E.g.:
    #         Makefile            /^(?i)makefile.*$/   # case-INsensitive regex

    Python              .py
    Python              .pyw
    Perl                .pl
    Ruby                .rb
    Tcl                 .tcl
    XML                 .xml
    XML                 .kpf
    XML                 .xul
    XML                 .rdf
    XML                 .xslt
    XML                 .xsl
    XML                 .wxs
    XML                 .wxi
    HTML                .htm
    HTML                .html
    XML                 .xhtml
    Makefile            /^[Mm]akefile.*$/
    PHP                 .php
    JavaScript          .js
    CSS                 .css
    C++                 .c       # C++ because then we can use //-style comments
    C++                 .cpp
    C++                 .cxx
    C++                 .cc
    C++                 .h
    C++                 .hpp
    C++                 .hxx
    C++                 .hh
    IDL                 .idl
    Text                .txt
    Fortran             .f
    Fortran             .f90
    Shell               .sh
    Shell               .csh
    Shell               .ksh
    Shell               .zsh
    Java                .java
    C#                  .cs
    TeX                 .tex

    # Some Komodo-specific file extensions
    Python              .ksf  # Fonts & Colors scheme files
    Text                .kkf  # Keybinding schemes files
"""

class ContentTypesRegistry:
    """A class that handles determining the filetype of a given path.

    Usage:
        >>> registry = ContentTypesRegistry()
        >>> registry.getContentType("foo.py")
        "Python"
    """

    def __init__(self, contentTypesPaths=None):
        self.contentTypesPaths = contentTypesPaths
        self._load()

    def _load(self):
        from os.path import dirname, join, exists

        self.suffixMap = {}
        self.regexMap = {}
        self.filenameMap = {}

        self._loadContentType(_gDefaultContentTypes)
        localContentTypesPath = join(dirname(__file__), "content.types")
        if exists(localContentTypesPath):
            log.debug("load content types file: `%r'" % localContentTypesPath)
            self._loadContentType(open(localContentTypesPath, 'r').read())
        for path in (self.contentTypesPaths or []):
            log.debug("load content types file: `%r'" % path)
            self._loadContentType(open(path, 'r').read())

    def _loadContentType(self, content, path=None):
        """Return the registry for the given content.types file.
       
        The registry is three mappings:
            <suffix> -> <content type>
            <regex> -> <content type>
            <filename> -> <content type>
        """
        for line in content.splitlines(0):
            words = line.strip().split()
            for i in range(len(words)):
                if words[i][0] == '#':
                    del words[i:]
                    break
            if not words: continue
            contentType, patterns = words[0], words[1:]
            if not patterns:
                if line[-1] == '\n': line = line[:-1]
                raise PreprocessError("bogus content.types line, there must "\
                                      "be one or more patterns: '%s'" % line)
            for pattern in patterns:
                if pattern.startswith('.'):
                    if sys.platform.startswith("win"):
                        # Suffix patterns are case-insensitive on Windows.
                        pattern = pattern.lower()
                    self.suffixMap[pattern] = contentType
                elif pattern.startswith('/') and pattern.endswith('/'):
                    self.regexMap[re.compile(pattern[1:-1])] = contentType
                else:
                    self.filenameMap[pattern] = contentType

    def getContentType(self, path):
        """Return a content type for the given path.

        @param path {str} The path of file for which to guess the
            content type.
        @returns {str|None} Returns None if could not determine the
            content type.
        """
        basename = os.path.basename(path)
        contentType = None
        # Try to determine from the path.
        if not contentType and self.filenameMap.has_key(basename):
            contentType = self.filenameMap[basename]
            log.debug("Content type of '%s' is '%s' (determined from full "\
                      "path).", path, contentType)
        # Try to determine from the suffix.
        if not contentType and '.' in basename:
            suffix = "." + basename.split(".")[-1]
            if sys.platform.startswith("win"):
                # Suffix patterns are case-insensitive on Windows.
                suffix = suffix.lower()
            if self.suffixMap.has_key(suffix):
                contentType = self.suffixMap[suffix]
                log.debug("Content type of '%s' is '%s' (determined from "\
                          "suffix '%s').", path, contentType, suffix)
        # Try to determine from the registered set of regex patterns.
        if not contentType:
            for regex, ctype in self.regexMap.items():
                if regex.search(basename):
                    contentType = ctype
                    log.debug("Content type of '%s' is '%s' (matches regex '%s')",
                              path, contentType, regex.pattern)
                    break
        # Try to determine from the file contents.
        content = open(path, 'rb').read()
        if content.startswith("<?xml"):  # cheap XML sniffing
            contentType = "XML"
        return contentType

_gDefaultContentTypesRegistry = None
def getDefaultContentTypesRegistry():
    global _gDefaultContentTypesRegistry
    if _gDefaultContentTypesRegistry is None:
        _gDefaultContentTypesRegistry = ContentTypesRegistry()
    return _gDefaultContentTypesRegistry


#---- internal support stuff
#TODO: move other internal stuff down to this section

try:
    reversed
except NameError:
    # 'reversed' added in Python 2.4 (http://www.python.org/doc/2.4/whatsnew/node7.html)
    def reversed(seq):
        rseq = list(seq)
        rseq.reverse()
        for item in rseq:
            yield item
try:
    sorted
except NameError:
    # 'sorted' added in Python 2.4. Note that I'm only implementing enough
    # of sorted as is used in this module.
    def sorted(seq, key=None):
        identity = lambda x: x
        key_func = (key or identity)
        sseq = list(seq)
        sseq.sort(lambda self, other: cmp(key_func(self), key_func(other)))
        for item in sseq:
            yield item


#---- mainline

def main(argv):
    try:
        optlist, args = getopt.getopt(argv[1:], 'hVvo:D:fkI:sc:',
            ['help', 'version', 'verbose', 'force', 'keep-lines',
             'substitute', 'content-types-path='])
    except getopt.GetoptError, msg:
        sys.stderr.write("preprocess: error: %s. Your invocation was: %s\n"\
                         % (msg, argv))
        sys.stderr.write("See 'preprocess --help'.\n")
        return 1
    outfile = sys.stdout
    defines = {}
    force = 0
    keepLines = 0
    substitute = 0
    includePath = []
    contentTypesPaths = []
    for opt, optarg in optlist:
        if opt in ('-h', '--help'):
            sys.stdout.write(__doc__)
            return 0
        elif opt in ('-V', '--version'):
            sys.stdout.write("preprocess %s\n" % __version__)
            return 0
        elif opt in ('-v', '--verbose'):
            log.setLevel(log.DEBUG)
        elif opt == '-o':
            outfile = optarg
        if opt in ('-f', '--force'):
            force = 1
        elif opt == '-D':
            if optarg.find('=') != -1:
                var, val = optarg.split('=', 1)
                try:
                    val = int(val)
                except ValueError:
                    pass
            else:
                var, val = optarg, None
            defines[var] = val
        elif opt in ('-k', '--keep-lines'):
            keepLines = 1
        elif opt == '-I':
            includePath.append(optarg)
        elif opt in ('-s', '--substitute'):
            substitute = 1
        elif opt in ('-c', '--content-types-path'):
            contentTypesPaths.append(optarg)

    if len(args) != 1:
        sys.stderr.write("preprocess: error: incorrect number of "\
                         "arguments: argv=%r\n" % argv)
        return 1
    else:
        infile = args[0]

    try:
        contentTypesRegistry = ContentTypesRegistry(contentTypesPaths)
        preprocess(infile, outfile, defines, force, keepLines, includePath,
                   substitute, contentTypesRegistry=contentTypesRegistry)
    except PreprocessError, ex:
        if log.isDebugEnabled():
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write("preprocess: error: %s\n" % str(ex))
        return 1

if __name__ == "__main__":
    __file__ = sys.argv[0]
    sys.exit( main(sys.argv) )

