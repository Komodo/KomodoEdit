#!/usr/bin/env python2.5
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

"""codeintel -- a tool for developing with Komodo's Code Intelligence system"""

__revision__ = "$Id$"
__version_info__ = (2, 0, 0)
__version__ = '.'.join(map(str, __version_info__))


import os
from os.path import (join, exists, isdir, isfile, abspath, normcase,
                     splitext, dirname, expanduser, normpath, isabs,
                     basename)
import sys
import getopt
import time
import re
from pprint import pprint
from glob import glob
import traceback
import logging
from optparse import OptionParser

sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "pylib"))
import cmdln
from cmdln import option
import koextlib

def _setup_xpcom_env():
    ko_info = koextlib.KomodoInfo()
    os.environ["PATH"] += ";" + ko_info.moz_bin_dir
    sys.path += ko_info.py_lib_dirs
    try:
        from xpcom import components
    except ImportError:
        pass
    else:
        # Ensure have a dir svc provider providing XREExtDL.
        koTestSvc = components.classes["@activestate.com/koTestService;1"] \
            .getService(components.interfaces.koITestService)
        koTestSvc.init()
_setup_xpcom_env()

import ciElementTree as ET
from codeintel2.common import CodeIntelError
from codeintel2.manager import Manager
from codeintel2.citadel import CitadelBuffer
from codeintel2.util import guess_lang_from_path
from codeintel2.tree import pretty_tree_from_tree, check_tree


#---- global data

log = logging.getLogger("codeintel")



#---- main public stuff

class Shell(cmdln.Cmdln):
    """${name} -- a tool for developing with Komodo's codeintel system

    Usage:
        ${name} SUBCOMMAND [ARGS...]
        ${name} help SUBCOMMAND       # help on a specific command

    ${option_list}
    This tool provides some commands for working with Komodo's
    Code Intelligence system.

    ${command_list}
    ${help_list}
    """
    name = 'codeintel'
    version = __version__
    helpindent = '  '

    def get_optparser(self):
        parser = cmdln.Cmdln.get_optparser(self)
        parser.add_option("-v", "--verbose", dest="log_level",
                          action="store_const", const=logging.DEBUG,
                          help="more verbose output")
        parser.add_option("-q", "--quiet", dest="log_level",
                          action="store_const", const=logging.WARNING,
                          help="quieter output")
        parser.set_defaults(log_level=logging.INFO)
        return parser

    def postoptparse(self):
        global log
        log.setLevel(self.options.log_level)

    @cmdln.option("-l", "--lang", dest="lang",
                  help="the language of the given path content")
    @cmdln.option("-p", "--pretty-print", action="store_true",
                  help="pretty-print the CIX output")
    def do_scan(self, subcmd, opts, *path_patterns):
        """Scan and print the CIX for the given path(s).

        ${cmd_usage}
        ${cmd_option_list}
        """
        extra_module_dirs = []
        if koextlib.is_ext_dir() and exists("pylib"):
            sys.path.append(abspath("pylib"))
            extra_module_dirs = [sys.path[-1]]
            
        mgr = Manager(extra_module_dirs=extra_module_dirs)
        mgr.upgrade()
        mgr.initialize()
        try:
            tree = None
            for path in _paths_from_path_patterns(path_patterns):
                try:
                    lang = opts.lang or guess_lang_from_path(path)
                except CodeIntelError:
                    log.info("skip `%s': couldn't determine language "
                             "(use --lang option)", path)
                    continue
                buf = mgr.buf_from_path(path, lang=opts.lang)
                if not isinstance(buf, CitadelBuffer):
                    raise CodeIntelError("`%s' (%s) is not a language that "
                                         "uses CIX" % (path, buf.lang))
                buf.scan()  # force a fresh scan
                tree = buf.tree
                for severity, msg in check_tree(tree):
                    dump = {"warning": log.warn,
                            "error": log.error}[severity]
                    dump(msg)
                if opts.pretty_print:
                    tree = pretty_tree_from_tree(tree)
                ET.dump(tree)
        finally:
            mgr.finalize()

    @cmdln.option("-l", "--lang", dest="lang",
                  help="the language of the given path content")
    @cmdln.option("-q", "--quiet", action="store_true", default=False,
                  help="don't output imports, function args and vars "
                       "(i.e. just the major structures)")
    def do_outline(self, subcmd, opts, path):
        """Scan and outline the structure of the given path.

        ${cmd_usage}
        ${cmd_option_list}
        """
        extra_lang_module_dirs = []
        if koextlib.is_ext_dir() and exists("pylib"):
            sys.path.append(abspath("pylib"))
            extra_lang_module_dirs = [sys.path[-1]]
            
        mgr = Manager(extra_lang_module_dirs=extra_lang_module_dirs)
        mgr.upgrade()
        mgr.initialize()
        try:
            if '#' in path:
                path, anchor = path.rsplit('#', 1)
            else:
                anchor = None

            tree = None
            try:
                lang = opts.lang or guess_lang_from_path(path)
            except CodeIntelError:
                log.info("skip `%s': couldn't determine language "
                         "(use --lang option)", path)
                return

            if path.endswith(".cix"):
                tree = tree_from_cix(open(path, 'r').read())
                #buf = mgr.buf_from_content("", tree[0].get("lang"), path=path)
            else:
                buf = mgr.buf_from_path(path, lang=opts.lang)
                if not isinstance(buf, CitadelBuffer):
                    raise CodeIntelError("`%s' (%s) is not a language that "
                                         "uses CIX" % (path, buf.lang))
                tree = buf.tree

            if anchor is not None:
                # Lookup the anchor in the codeintel CIX tree.
                lpath = re.split(r'\.|::', anchor)
                def blobs_from_tree(tree):
                    for file_elem in tree:
                        for blob in file_elem:
                            yield blob

                for elem in blobs_from_tree(tree):
                    # Generally have 3 types of codeintel trees:
                    # 1. single-lang file: one <file>, one <blob>
                    # 2. multi-lang file: one <file>, one or two <blob>'s
                    # 3. CIX stdlib/catalog file: possibly multiple
                    #    <file>'s, likely multiple <blob>'s
                    # Allow the first token to be the blob name or lang.
                    # (This can sometimes be weird, but seems the most
                    # convenient solution.)
                    if lpath[0] in (elem.get("name"), elem.get("lang")):
                        remaining_lpath = lpath[1:]
                    else:
                        remaining_lpath = lpath
                    for name in remaining_lpath:
                        try:
                            elem = elem.names[name]
                        except KeyError:
                            elem = None
                            break # try next lang blob
                    if elem is not None:
                        break # found one
                else:
                    log.error("could not find `%s' definition (or blob) in `%s'",
                              anchor, path)
                    return 1
            else:
                elem = tree

            try:
                _outline_ci_elem(mgr, elem, quiet=opts.quiet)
            except IOError, ex:
                if ex.errno == 0:
                    # Ignore this error from aborting 'less' of this
                    # command:
                    #    IOError: (0, 'Error')
                    pass
                else:
                    raise
        finally:
            mgr.finalize()

    @cmdln.option("-o", "--output",
                  help="path to which to write HTML output (instead of "
                       "PATH.html, use '-' for stdout)")
    @cmdln.option("-b", "--browse", action="store_true",
                  help="open output file in browser")
    @cmdln.option("-e", "--do-eval", action="store_true",
                  help="do (and show) completion evaluation")
    @cmdln.option("-t", "--do-trg", action="store_true",
                  help="do (and show) trigger handling (also implies -e)")
    @cmdln.option("-l", "--lang",
                  help="specify the language of the given path (if not "
                       "given it will be guessed)")
    def do_html(self, subcmd, opts, path):
        """Convert the given path to styled HTML.

        ${cmd_usage}
        ${cmd_option_list}
        
        The generated HTML provides a good tool for seeing how Komodo's
        lexer lexes the given content. This is the same tokenization that
        you get from "buf.accessor.*" methods -- which you can use for
        writing the CILE, trigger handling, and completion evaluation
        for this language.
        
        Use the "-t" and "-e" option to also exercise the current
        trigger handling and completion evaluation (i.e. determining
        the appropriate completions and calltips at a given trigger
        point).
        """
        extra_lang_module_dirs = []
        if koextlib.is_ext_dir() and exists("pylib"):
            sys.path.append(abspath("pylib"))
            extra_lang_module_dirs = [sys.path[-1]]
            
        mgr = Manager(extra_lang_module_dirs=extra_lang_module_dirs)
        try:
            if opts.browse:
                htmls = []
            buf = mgr.buf_from_path(path, lang=opts.lang)
            html = buf.to_html(True, True, title=path,
                               do_trg=opts.do_trg,
                               do_eval=opts.do_eval)
        finally:
            mgr.finalize()
        
        if opts.output == '-':
            output_path = None
            output_file = sys.stdout
        else:
            if opts.output:
                output_path = opts.output
            else:
                output_path = path+".html"
            if exists(output_path):
                os.remove(output_path)
            output_file = open(output_path, 'w')
        if output_file:
            output_file.write(html)
        if output_path:
            output_file.close()

        if opts.browse:
            if not output_path:
                raise CodeIntelError("cannot open in browser if stdout "
                                     "used for output")
            import webbrowser
            url = _url_from_local_path(output_path)
            webbrowser.open_new(url)  


#---- internal support functions

def _outline_ci_elem(mgr, elem, stream=sys.stdout, lang=None, quiet=False,
                     _lvl=0):
    """Dump an outline of the given codeintel tree element."""
    indent = '  '
    def _dump(s):
        stream.write(indent*_lvl + s + '\n')

    if elem.tag == "codeintel":
        _lvl -= 1 # don't count this one
    elif elem.tag == "file":
        lang = elem.get("lang")
        _dump("file %(path)s [%(lang)s]" % elem.attrib)
    elif elem.tag == "variable":
        if elem.get("ilk") == "argument":
            s = "arg "+elem.get("name") # skip?
        else:
            s = "var "+elem.get("name")
        if elem.get("citdl"):
            s += " [%s]" % elem.get("citdl")
        _dump(s)
    elif elem.tag == "scope" and elem.get("ilk") == "function" \
         and elem.get("signature"):
        _dump("function %s" % elem.get("signature").split('\n')[0])
    elif elem.tag == "scope" and elem.get("ilk") == "blob":
        lang = elem.get("lang")
        _dump("blob %(name)s [%(lang)s]" % elem.attrib)
    elif elem.tag == "scope" and elem.get("ilk") == "class" \
         and elem.get("classrefs"):
        _dump("%s %s(%s)" % (elem.get("ilk"), elem.get("name"),
                             ', '.join(elem.get("classrefs").split())))
    elif elem.tag == "scope":
        _dump("%s %s" % (elem.get("ilk"), elem.get("name")))
    elif elem.tag == "import":
        if not quiet:
            langintel = mgr.langintel_from_lang(lang)
            data = langintel.cb_import_data_from_elem(elem)
            _dump(data["detail"])
    else:
        raise ValueError("unknown tag: %r (%r)" % (elem.tag, elem))

    if quiet and (elem.tag == "scope" and elem.get("ilk") == "function"):
        pass
    else:
        for child in elem:
            _outline_ci_elem(mgr, child, stream, lang=lang, quiet=quiet,
                             _lvl=_lvl+1)


# From komodo/utils/rst2html/rst2html.py.
def _url_from_local_path(local_path):
    # HACKy: This isn't super-robust.
    from os.path import abspath, normpath
    url = normpath(abspath(local_path))
    if sys.platform == "win32":
        url = "file:///" + url.replace('\\', '/')
    else:
        url = "file://" + url
    return url

# Recipe: paths_from_path_patterns (0.3.7)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path


# Recipe: pretty_logging (0.1+)
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
    infoFmt = "%(message)s"
    fmtFromLevel={logging.INFO: "%(name)s: %(message)s"}
    fmtr = _PerLevelFormatter(defaultFmt, fmtFromLevel=fmtFromLevel)
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)



#---- mainline

def _do_main(argv):
    shell = Shell()
    return shell.main(argv)

def main(argv=sys.argv):
    _setup_logging()
    try:
        retval = _do_main(argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except:
        skip_it = False
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            if isinstance(exc, IOError) and exc.args[0] == 32:
                # Skip 'IOError: [Errno 32] Broken pipe'.
                skip_it = True
            if not skip_it:
                #tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                #log.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                #          tb_lineno, tb_func)
                log.error(exc_info[1])
        else:  # string exception
            log.error(exc_info[0])
        if not skip_it:
            if log.isEnabledFor(logging.DEBUG):
                print
                traceback.print_exception(*exc_info)
            sys.exit(1)
    else:
        sys.exit(retval)

if __name__ == "__main__":
    main(sys.argv)


