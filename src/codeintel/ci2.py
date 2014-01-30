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
# Author:
#   Trent Mick (TrentM@ActiveState.com)

r"""ci2 -- playing with some new CodeIntel ideas"""

__revision__ = "$Id$"
__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import isfile, isdir, exists, dirname, abspath, splitext, join
import sys
import getopt
import stat
from cStringIO import StringIO
import logging
import time
import re
from collections import defaultdict
import optparse
import traceback
from pprint import pprint
import random
from glob import glob
import cStringIO

import ciElementTree as ET
from codeintel2.manager import Manager
from codeintel2.citadel import Citadel, CitadelBuffer
from codeintel2.common import *
from codeintel2.util import (indent, dedent, banner, unmark_text,
                             guess_lang_from_path)
from codeintel2.tree import tree_from_cix, pretty_tree_from_tree, check_tree
from codeintel2.gencix_utils import outline_ci_elem

sys.path.insert(0, join(dirname(abspath(__file__)), "support"))
try:
    import cmdln
    import applib
    import cix2html
finally:
    del sys.path[0]



#---- exceptions and globals

log = logging.getLogger("codeintel.ci2")


#---- replace Manager with out own wrapper that sets up the environment.
_Manager = Manager
class Manager(_Manager):
    def __init__(self):
        extra_module_dirs = os.environ.get("PYTHONPATH", "").split(os.pathsep)
        _Manager.__init__(self, extra_module_dirs=extra_module_dirs)


#---- internal support stuff

# From Komodo-devel/utils/rst2html/rst2html.py.
def _url_from_local_path(local_path):
    # HACKy: This isn't super-robust.
    from os.path import abspath, normpath
    url = normpath(abspath(local_path))
    if sys.platform == "win32":
        url = "file:///" + url.replace('\\', '/')
    else:
        url = "file://" + url
    return url



def _isident(char):
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"

def _isdigit(char):
    return "0" <= char <= "9"


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

#TODO: add to recipes
def _escaped_text_from_text(text, escapes="eol"):
    r"""Return escaped version of text.

        "escapes" is either a mapping of chars in the source text to
            replacement text for each such char or one of a set of
            strings identifying a particular escape style:
                eol
                    replace EOL chars with '\r' and '\n', maintain the actual
                    EOLs though too
                whitespace
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
                eol-one-line
                    replace EOL chars with '\r' and '\n'
                whitespace-one-line
                    replace EOL chars as above, tabs with '\t' and spaces
                    with periods ('.')
    """
    #TODO:
    # - Add 'c-string' style.
    # - Add _escaped_html_from_text() with a similar call sig.
    import re
    
    if isinstance(escapes, basestring):
        if escapes == "eol":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r"}
        elif escapes == "whitespace":
            escapes = {'\r\n': "\\r\\n\r\n", '\n': "\\n\n", '\r': "\\r\r",
                       '\t': "\\t", ' ': "."}
        elif escapes == "eol-one-line":
            escapes = {'\n': "\\n", '\r': "\\r"}
        elif escapes == "whitespace-one-line":
            escapes = {'\n': "\\n", '\r': "\\r", '\t': "\\t", ' ': '.'}
        else:
            raise ValueError("unknown text escape style: %r" % escapes)

    # Sort longer replacements first to allow, e.g. '\r\n' to beat '\r' and
    # '\n'.
    escapes_keys = escapes.keys()
    escapes_keys.sort(key=lambda a: len(a), reverse=True)
    def repl(match):
        val = escapes[match.group(0)]
        return val
    escaped = re.sub("(%s)" % '|'.join([re.escape(k) for k in escapes_keys]),
                     repl,
                     text)

    return escaped



def _outline_ci_elem(elem, stream=sys.stdout,
                     brief=False, doSort=False, encoding=None):
    """Dump an outline of the given codeintel tree element."""
    if encoding is None:
        encoding = sys.getfilesystemencoding()

    outline = outline_ci_elem(elem)
    stream.write(outline.encode(encoding))



#---- mainline

class Shell(cmdln.Cmdln):
    r"""ci2 -- the new Code Intel, a tool for working with source code

    usage:
        ${name} SUBCOMMAND [ARGS...]
        ${name} help SUBCOMMAND

    ${option_list}
    ${command_list}
    ${help_list}
    """
    name = "ci2"
    version = __version__
    _do_profiling = False

    #XXX There is a bug in cmdln.py alignment when using this. Leave it off
    #    until that is fixed. -- I think this may be fixed now.
    #helpindent = ' '*4

    def _set_profiling(self, option, opt_str, value, parser):
        self._do_profiling = True

    def get_optparser(self):
        optparser = cmdln.Cmdln.get_optparser(self)
        optparser.add_option("-v", "--verbose", 
            action="callback", callback=_set_verbosity,
            help="More verbose output. Repeat for more and more output.")
        optparser.add_option("-L", "--log-level",
            action="callback", callback=_set_logger_level, nargs=1, type="str",
            help="Specify a logger level via '<logname>:<levelname>'.")
        optparser.add_option("-p", "--profile",
            action="callback", callback=self._set_profiling,
            help="Enable code profiling, prints out a method summary.")
        return optparser

    def do_test(self, argv):
        """Run the ci2 test suite.

        See `ci2 test -h' for more details.
        """
        import subprocess
        testdir = join(dirname(__file__), "test2")
        if self._do_profiling:
            cmd = '"%s" -m cProfile -s time test.py %s' % (sys.executable, ' '.join(argv[1:]))
        else:
            cmd = '"%s" test.py %s' % (sys.executable, ' '.join(argv[1:]))
        env = os.environ.copy()
        env["CODEINTEL_NO_PYXPCOM"] = "1"
        p = subprocess.Popen(cmd, cwd=testdir, env=env, shell=True)
        p.wait()
        return p.returncode

    def do_clean_unicode_directories(self, argv):
        """ Remove the unicode directories after running `ci2 test`."""
        import subprocess
        testdir = join(dirname(__file__), "test2")
        cmd = '"%s" clean_tests.py' % (sys.executable,)
        env = os.environ.copy()
        p = subprocess.Popen(cmd, cwd=testdir, env=env, shell=True)
        p.wait()
        return p.returncode

    def do_doctest(self, subcmd, opts):
        """Run the ci2 internal doctests.

        ${cmd_usage}
        ${cmd_option_list}
        I'd prefer these just be run as part of the 'test' command, but
        I don't know how to integrate that into unittest.main().
        """
        import doctest
        doctest.testmod()

    def _cidb_path_from_kover(self, kover):
        ko_user_data_dir = applib.user_data_dir("Komodo", "ActiveState",
                                                "%s.%s" % kover)
        if not exists(ko_user_data_dir):
            raise OSError("`%s' does not exist" % ko_user_data_dir)
        return join(ko_user_data_dir, "codeintel.db")

    def do_play(self, subcmd, opts):
        """Run my current play/dev code.

        ${cmd_usage}
        ${cmd_option_list}
        """
        if False:
            lang = "CSS"
            markedup_content = dedent("""
                /* http://www.w3.org/TR/REC-CSS2/fonts.html#propdef-font-weight */
                h1 {
                    border: 1px solid black;
                    font-weight /* hi */: <|> !important
                }
            """)
            content, data = unmark_text(markedup_content)
            pos = data["pos"]
            mgr = Manager()
            #mgr.upgrade() # Don't need it for just CSS usage.
            mgr.initialize()
            try:
                buf = mgr.buf_from_content(content, lang=lang, path="play.css")
                trg = buf.trg_from_pos(pos)
                if trg is None:
                    raise Error("unexpected trigger: %r" % trg)
                completions = buf.cplns_from_trg(trg)
                print "COMPLETIONS: %r" % completions
            finally:
                mgr.finalize()

        elif False:
            lang = "Python"
            path = join("<Unsaved>", "rand%d.py" % random.randint(0, 100))
            markedup_content = dedent("""
                import sys, os

                class Foo:
                    def bar(self):
                        pass

                sys.<|>path    # should have path in completion list
                f = Foo()
                """)
            content, data = unmark_text(markedup_content)
            print banner(path)
            print _escaped_text_from_text(content, "whitespace")
            pos = data["pos"]
            mgr = Manager()
            mgr.upgrade()
            mgr.initialize()
            try:
                buf = mgr.buf_from_content(content, lang=lang, path=path)
                print banner("cix", '-')
                print buf.cix

                trg = buf.trg_from_pos(pos)
                if trg is None:
                    raise Error("unexpected trigger: %r" % trg)
                print banner("completions", '-')
                ctlr = LogEvalController(log)
                buf.async_eval_at_trg(trg, ctlr)
                ctlr.wait(2) #XXX
                if not ctlr.is_done():
                    ctlr.abort()
                    raise Error("XXX async eval timed out")
                pprint(ctlr.cplns)
                print banner(None)
            finally:
                mgr.finalize()
        elif False:
            lang = "Ruby"
            path = join("<Unsaved>", "rand%d.py" % random.randint(0, 100))
            markedup_content = dedent("""\
            r<1>equire 'net/http'
            include Net
            req = HTTPRequest.new
            req.<2>get()
            """)
            content, data = unmark_text(markedup_content)
            print banner(path)
            print _escaped_text_from_text(content, "whitespace")
            pos = data[1]
            mgr = Manager()
            mgr.upgrade()
            mgr.initialize()
            try:
                buf = mgr.buf_from_content(content, lang=lang, path=path)
                print banner("cix", '-')
                cix = buf.cix
                print ET.tostring(pretty_tree_from_tree(tree_from_cix(buf.cix)))

                trg = buf.trg_from_pos(pos, implicit=False)
                if trg is None:
                    raise Error("unexpected trigger: %r" % trg)
                print banner("completions", '-')
                ctlr = LogEvalController(log)
                buf.async_eval_at_trg(trg, ctlr)
                ctlr.wait(30) #XXX
                if not ctlr.is_done():
                    ctlr.abort()
                    raise Error("XXX async eval timed out")
                pprint(ctlr.cplns)
                print banner(None)
            finally:
                mgr.finalize()

        
    @cmdln.alias("up")
    def do_unpickle(self, subcmd, opts, *path_patterns):
        """Unpickle and dump the given paths.

        ${cmd_usage}
        ${cmd_option_list}
        """
        import cPickle as pickle
        for path in _paths_from_path_patterns(path_patterns):
            fin = open(path, 'rb')
            try:
                obj = pickle.load(fin)
            finally:
                fin.close()
            pprint(obj)

    @cmdln.option("-d", "--db-base-dir",
                  help="the database base dir to check (defaults to ~/.codeintel)")
    def do_dbcheck(self, subcmd, opts):
        """Run an internal consistency check on the database.

        ${cmd_usage}
        ${cmd_option_list}
        Any errors will be printed. Returns the number of errors (i.e.
        exit value is 0 if there are no consistency problems).
        """
        mgr = Manager(opts.db_base_dir)
        try:
            errors = mgr.db.check()
        finally:
            mgr.finalize()
        for error in errors:
            print error
        return len(errors)

    @cmdln.option("-l", "--language", dest="lang",
                  help="the language of the given path content")
    @cmdln.option("-b", "--brief", dest="brief", action="store_true",
                  help="just print the brief name outline")
    @cmdln.option("-s", "--sorted", dest="doSort", action="store_true",
                  help="sort child names alphabetically")
    def do_outline(self, subcmd, opts, path):
        """Print code outline of the given file.

        You can specify a lookup path into the file code outline to
        display via URL-anchor syntax, e.g.:
            ci2 outline path/to/foo.py#AClass.amethod

        ${cmd_usage}
        ${cmd_option_list}
        """
        mgr = Manager()
        mgr.upgrade()
        mgr.initialize()
        try:
            if '#' in path:
                path, anchor = path.rsplit('#', 1)
            else:
                anchor = None

            if path.endswith(".cix"):
                tree = tree_from_cix(open(path, 'r').read())
                #buf = mgr.buf_from_content("", tree[0].get("lang"), path=path)
            else:
                buf = mgr.buf_from_path(path, lang=opts.lang)
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
                _outline_ci_elem(elem, brief=opts.brief, doSort=opts.doSort)
            except IOError, ex:
                if ex.errno == 0:
                    # Ignore this error from aborting 'less' of 'ci2 outline'
                    # output:
                    #    IOError: (0, 'Error')
                    pass
                else:
                    raise
        finally:
            mgr.finalize()

    def do_cix_check(self, subcmd, opts, *path_patterns):
        """Check the given CIX file(s) for warnings, errors.

        ${cmd_usage}
        ${cmd_option_list}
        Eventually this should include an XML validity check against the
        RelaxNG schema for CIX. However, currently it just checks for
        some common errors.

        Returns the number of warnings/errors generated.
        """
        num_results = 0
        for path in _paths_from_path_patterns(path_patterns):
            tree = None
            cix = open(path, 'r').read()
            tree = tree_from_cix(cix)
            for sev, msg in check_tree(tree):
                num_results += 1
                print "%s: %s: %s" % (path, sev, msg)
        return num_results

    @cmdln.option("-2", dest="convert", action="store_true",
                  help="convert to CIX 2.0 before printing")
    @cmdln.option("-p", "--pretty-print", action="store_true",
                  help="pretty-print the CIX output (presumes '-2')")
    def do_cix(self, subcmd, opts, *path_patterns):
        """Read in and print a CIX file (possibly converting to CIX 2.0
        and prettifying in the process.

        ${cmd_usage}
        ${cmd_option_list}
        """
        if opts.pretty_print:
            opts.convert = True
        for path in _paths_from_path_patterns(path_patterns):
            tree = None
            cix = open(path, 'r').read()
            if opts.convert:
                tree = tree_from_cix(cix)
                if opts.pretty_print:
                    tree = pretty_tree_from_tree(tree)
                ET.dump(tree)
            else:
                sys.stdout.write(cix)

    @cmdln.option("-l", "--language", dest="lang",
                  help="the language of the given path content")
    @cmdln.option("-q", "--quiet", dest="quiet", action="store_true",
                  help="suppress printing of output (useful when just timing)")
    @cmdln.option("-p", "--pretty-print", action="store_true",
                  help="pretty-print the CIX output (presumes '-2')")
    @cmdln.option("-f", "--force", action="store_true",
                  help="force a scan (rather than loading from DB)")
    @cmdln.option("-i", "--include", dest="includes", action="append",
                  help="specify include file patterns (e.g. \"*.pm\")")
    @cmdln.option("-t", dest="time_it", action="store_true",
                  help="dump a time summary (implies --force)")
    @cmdln.option("-T", dest="time_details", action="store_true",
                  help="dump timing info per file (implies --force)")
    @cmdln.option("-r", dest="recursive", action="store_true",
                  help="recursively find files")
    @cmdln.option("-n", dest="stripfuncvars", action="store_true",
                  help="Don't output variables inside of functions (for stdlib creation)")
    def do_scan(self, subcmd, opts, *path_patterns):
        """Scan and print the CIX for the given path(s).

        ${cmd_usage}
        ${cmd_option_list}
        """
        mgr = Manager()
        mgr.upgrade()
        mgr.initialize()
        try:
            if opts.time_it:
                start = time.time()
            quiet = opts.quiet
            if opts.time_it or opts.time_details:
                opts.force = True

            scan_count = 0
            lang_warnings = set()
            tree = None
            for path in _paths_from_path_patterns(path_patterns,
                                                  recursive=opts.recursive,
                                                  includes=opts.includes):
                if opts.time_it:
                    sys.stderr.write(path+"\n")
                if opts.time_details:
                    start1 = time.time()

                try:
                    lang = opts.lang or guess_lang_from_path(path)
                except CodeIntelError:
                    log.info("skip `%s': couldn't determine language", path)
                    continue
                try:
                    buf = mgr.buf_from_path(path, lang=lang)
                except OSError as ex:
                    # Couldn't access the file.
                    if not opts.recursive:
                        raise
                    # Ignore files we don't really care about.
                    log.warn("%r - %r", ex, path)
                    continue
                if not isinstance(buf, CitadelBuffer):
                    if opts.recursive:
                        # Ignore files that scanning isn't provided for.
                        continue
                    raise CodeIntelError("`%s' (%s) is not a language that "
                                         "uses CIX" % (path, buf.lang))

                scan_count += 1
                if scan_count % 10 == 0:
                    log.info("%d scanning %r", scan_count, path)

                try:
                    if opts.force:
                        buf.scan()
                    if tree is None:
                        tree = ET.Element("codeintel", version="2.0")
                    file_elem = ET.SubElement(tree, "file",
                                              lang=buf.lang,
                                              mtime=str(int(time.time())),
                                              path=os.path.basename(path))
                    for lang, blob in sorted(buf.blob_from_lang.items()):
                        blob = buf.blob_from_lang[lang]
                        file_elem.append(blob)
                except KeyError as ex:
                    # Unknown cile language.
                    if not opts.recursive:
                        raise
                    message = str(ex)
                    if message not in lang_warnings:
                        lang_warnings.add(message)
                        log.warn("Skipping unhandled language %s", message)

                if opts.time_details: 
                   delta = time.time() - start1
                   sys.stderr.write("%.3f %s\n" % (delta, path)) 
                   sys.stderr.flush()

            if tree is not None:
                if opts.stripfuncvars:
                    # For stdlibs, we don't care about variables inside of
                    # functions and they take up a lot of space.
                    for function in tree.getiterator('scope'):
                        if function.get('ilk') == 'function':
                            function[:] = [child for child in function 
                                           if child.tag != 'variable']
                if opts.pretty_print:
                    tree = pretty_tree_from_tree(tree)
                if not quiet:
                    sys.stdout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    ET.dump(tree)
                if opts.time_it:
                    end = time.time()
                    sys.stderr.write("scan took %.3fs\n" % (end-start))
        finally:
            mgr.finalize()

    @cmdln.option("-o", "--output",
                  help="path to which to write HTML output (instead of "
                       "PATH.html, use '-' for stdout)")
    @cmdln.option("-b", "--browse", action="store_true",
                  help="open output file in browser")
    @cmdln.option("-f", "--force", action="store_true",
                  help="allow overwrite of existing file")
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
        
        The output includes trigger info and other stats. I.e. this is
        primarily a debugging tool.
        """
        mgr = Manager()
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
                if opts.force:
                    os.remove(output_path)
                else:
                    raise Error("`%s' exists: use -f|--force option to "
                                "allow overwrite" % output_path)
            output_file = open(output_path, 'w')
        #else:
        #    output_path = None
        #    output_file = sys.stdout
        #    #XXX Disable writing t
        #    output_file = None 
        if output_file:
            output_file.write(html)
        if output_path:
            output_file.close()

        if opts.browse:
            if not output_path:
                raise Error("cannot open in browser if stdout used "
                            "for output")
            import webbrowser
            url = _url_from_local_path(output_path)
            webbrowser.open_new(url)            

    @cmdln.option("-c", "--css", dest="css_reference_files", action="append",
                  help="add css reference file for styling"
                       " (can be used more than once)")
    @cmdln.option("-o", "--output", dest="output",
                  help="filename for generated html output, defaults to stdout")
    @cmdln.option("-t", "--toc-file", dest="toc_file",
                  help="filename for generated toc xml file")
    @cmdln.option("-l", "--language", dest="lang",
                  help="only include docs for the supplied language")
    def do_cix2html(self, subcmd, opts, path):
        """Turn cix file into html API documentation.

        Example:
            ci2 cix2html path/to/foo.cix#AClass.amethod
            ci2 cix2html path/to/foo.cix -o htmldir

        ${cmd_usage}
        ${cmd_option_list}
        """
        cix2html.cix2html(opts, path)

    @cmdln.option("-o", "--output",
                  help="path to which to write JSON output (instead of "
                       "PATH.json, use '-' for stdout)")
    @cmdln.option("-f", "--force", action="store_true",
                  help="allow overwrite of existing file")
    def do_json(self, subcmd, opts, path):
        """Convert cix XML file into json format.

        ${cmd_usage}
        ${cmd_option_list}
        """
        import json

        if opts.output == '-':
            output_path = None
            output_file = sys.stdout
        else:
            if opts.output:
                output_path = opts.output
            else:
                output_path = splitext(path)[0]+".json"
            if exists(output_path):
                if opts.force:
                    os.remove(output_path)
                else:
                    raise Error("`%s' exists: use -f|--force option to "
                                "allow overwrite" % output_path)
            output_file = open(output_path, 'w')

        mgr = Manager()
        mgr.upgrade()
        mgr.initialize()

        try:
            if path.endswith(".cix"):
                tree = tree_from_cix(open(path, 'r').read())
            else:
                buf = mgr.buf_from_path(path, lang=opts.lang)
                tree = buf.tree

            result = {}
            ci = result["codeintel"] = defaultdict(list)

            def _elemToDict(parent, elem):
                data = defaultdict(list)
                name = elem.get("name")
                if name is not None:
                    data["name"] = name
                data["tag"] = elem.tag
                for attr_name, attr in elem.attrib.items():
                    data[attr_name] = attr
                parent["children"].append(data)
                for child in elem:
                    _elemToDict(data, child)

            for child in tree:
                _elemToDict(ci, child)

            json.dump(result, output_file, indent=2)

        finally:
            mgr.finalize()

# Recipe: paths_from_path_patterns (0.3.4) in /home/trentm/tm/recipes/cookbook
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
            log.debug("exclude `%s' (matches no includes)", path)
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
                        for i in dir_indeces_to_remove:
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path


_v_count = 0
def _set_verbosity(option, opt_str, value, parser):
    global _v_count, log
    _v_count += 1
    if _v_count == 1:
        log.setLevel(logging.INFO)
        logging.getLogger("codeintel").setLevel(logging.INFO)
    elif _v_count > 1:
        log.setLevel(logging.DEBUG)
        logging.getLogger("codeintel").setLevel(logging.DEBUG)

def _set_logger_level(option, opt_str, value, parser):
    # Optarg is of the form '<logname>:<levelname>', e.g.
    # "codeintel:DEBUG", "codeintel.db:INFO".
    lname, llevelname = value.split(':', 1)
    llevel = getattr(logging, llevelname)
    logging.getLogger(lname).setLevel(llevel)

def _do_main(argv):
    return Shell().main(sys.argv)

def main(argv=sys.argv):
    _setup_logging() # defined in recipe:pretty_logging
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
                tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                log.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                          tb_lineno, tb_func)
        else:  # string exception
            log.error(exc_info[0])
        if not skip_it:
            if True or log.isEnabledFor(logging.DEBUG):
                print
                traceback.print_exception(*exc_info)
            sys.exit(1)
    else:
        sys.exit(retval)

if __name__ == "__main__":
    main(sys.argv)


