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

"""Python support for CodeIntel"""

import os
from os.path import (isfile, isdir, exists, dirname, abspath, splitext,
                     join, basename, isfile, normcase)
import sys
import logging
import random
import parser
from glob import glob
import weakref
import re
from pprint import pprint, pformat

import SilverCity
from SilverCity.Lexer import Lexer
from SilverCity import ScintillaConstants
from SilverCity.Keywords import python_keywords

from codeintel2.common import *
from codeintel2.citadel import (CitadelBuffer, CitadelEvaluator, ImportHandler,
                                CitadelLangIntel)
from codeintel2.indexer import PreloadLibRequest
from codeintel2 import pythoncile
from codeintel2.util import banner, indent, markup_text, isident, isdigit
from codeintel2 import tree
from codeintel2.tree_python import PythonTreeEvaluator
from codeintel2.langintel import (ParenStyleCalltipIntelMixin,
                                  ProgLangTriggerIntelMixin,
                                  PythonCITDLExtractorMixin)

if _xpcom_:
    from xpcom.server import UnwrapObject



#---- globals

lang = "Python"
log = logging.getLogger("codeintel.python")
#log.setLevel(logging.DEBUG)

CACHING = True #DEPRECATED: kill it

# See http://effbot.org/zone/pythondoc.htm
_g_pythondoc_tags = list(sorted("param keyparam return exception def "
                                "defreturn see link linkplain".split()))



#---- language support

class PythonLexer(Lexer):
    lang = lang
    def __init__(self):
        self._properties = SilverCity.PropertySet()
        self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_PYTHON)
        self._keyword_lists = [
            SilverCity.WordList(python_keywords),
            SilverCity.WordList(""), # hilighted identifiers
        ]


class PythonImportsEvaluator(Evaluator):
    def __str__(self):
        return "Python imports"
    def eval(self, mgr):
        try:
            imp_prefix = self.trg.extra["imp_prefix"]
            if imp_prefix:
                self.ctlr.set_desc("subimports of '%s'" % '.'.join(imp_prefix))
                cplns = []
                for lib in self.buf.libs:
                    imports = lib.get_blob_imports(imp_prefix)
                    if imports:
                        cplns.extend(
                            ((is_dir_import and "directory" or "module"), name)
                            for name, is_dir_import in imports
                        )
                        
                    if self.trg.type == "module-members":
                        # Also add top-level members of the specified module.
                        dotted_prefix = '.'.join(imp_prefix)
                        if lib.has_blob(dotted_prefix):
                            blob = lib.get_blob(dotted_prefix)
                            for name in blob.names:
                                elem = blob.names[name]
                                cplns.append((elem.get("ilk") or elem.tag, name))
                            #TODO: Should also add symbols from
                            #      top-level imports in this blob.
                            #TODO: Consider using the value of __all__
                            #      if defined.
                    if cplns:
                        break
                
            else:
                self.ctlr.set_desc("available imports")
                all_imports = set()
                for lib in self.buf.libs:
                    all_imports.update(lib.get_blob_imports(imp_prefix))
                cplns = [((is_dir_import and "directory" or "module"), name)
                         for name, is_dir_import in all_imports]
            if cplns:
                cplns.sort(key=lambda i: i[1].upper())
                self.ctlr.set_cplns(cplns)
        finally:
            self.ctlr.done("success")


class PythonLangIntel(CitadelLangIntel, ParenStyleCalltipIntelMixin,
                      ProgLangTriggerIntelMixin,
                      PythonCITDLExtractorMixin):
    lang = "Python"

    # Used by ProgLangTriggerIntelMixin.preceding_trg_from_pos().
    trg_chars = tuple(" (.")
    
    def async_eval_at_trg(self, buf, trg, ctlr):
        if _xpcom_:
            trg = UnwrapObject(trg)
            ctlr = UnwrapObject(ctlr)
        ctlr.start(buf, trg)
        if trg.type in ("object-members", "call-signature",
                        "literal-members") or \
           trg.form == TRG_FORM_DEFN:
            line = buf.accessor.line_from_pos(trg.pos)
            if trg.type == "literal-members":
                # We could leave this to citdl_expr_from_trg, but this is a
                # little bit faster, since we already know the citdl expr.
                citdl_expr = trg.extra.get("citdl_expr")
            else:
                try:
                    citdl_expr = self.citdl_expr_from_trg(buf, trg)
                except CodeIntelError, ex:
                    ctlr.error(str(ex))
                    ctlr.done("error")
                    return
            evalr = PythonTreeEvaluator(ctlr, buf, trg, citdl_expr, line)
            buf.mgr.request_eval(evalr)
        elif trg.id == ("Python", TRG_FORM_CPLN, "pythondoc-tags"):
            #TODO: Would like a "tag" completion image name.
            cplns = [("variable", t) for t in _g_pythondoc_tags]
            ctlr.set_cplns(cplns)
            ctlr.done("success")
        elif trg.type in ("available-imports", "module-members"):
            evalr = PythonImportsEvaluator(ctlr, buf, trg)
            buf.mgr.request_eval(evalr)
        else:
            raise NotImplementedError("not yet implemented: completion for "
                                      "Python '%s' trigger" % trg.name)

    def _python_from_env(self, env):
        import which
        path = [d.strip() 
                for d in env.get_envvar("PATH", "").split(os.pathsep)
                if d.strip()]
        try:
            return which.which("python", path=path) 
        except which.WhichError:
            return None

    def _python_info_from_python(self, python, env):
        """Call the given Python and return:
            (<version>, <sys.prefix>, <lib-dir>, <site-lib-dir>, <sys.path>)

        TODO: Unicode path issues?
        """
        import process

        # Python 1.5.2 does not support sys.version_info.
        info_cmd = (
            r"import sys;"
            r"import string;"
            r"paren = string.find(sys.version, '(');"
            r"version = string.strip(sys.version[:paren]);"
            r"sys.stdout.write(version+'\n');"
            r"sys.stdout.write(sys.prefix+'\n');"
            r"sys.stdout.write('\n'.join(sys.path));")

        argv = [python, "-c", info_cmd]
        log.debug("run `%s -c ...'", python)
        p = process.ProcessOpen(argv, env=env.get_all_envvars(), stdin=None)
        stdout, stderr = p.communicate()
        stdout_lines = stdout.splitlines(0)
        retval = p.returncode
        if retval:
            log.warn("failed to determine Python info:\n"
                     "  path: %s\n"
                     "  retval: %s\n"
                     "  stdout:\n%s\n"
                     "  stderr:\n%s\n",
                     python, retval, indent('\n'.join(stdout_lines)),
                     indent(stderr))

        # We are only to rely on the first 2 digits being in the form x.y.
        ver_match = re.search("([0-9]+.[0-9]+)", stdout_lines[0])
        if ver_match:
            ver = ver_match.group(1)
        else:
            ver = None
        prefix = stdout_lines[1]
        if sys.platform == "win32":
            libdir = join(prefix, "Lib")
        else:
            libdir = join(prefix, "lib", "python"+ver)
        sitelibdir = join(libdir, "site-packages")
        sys_path = stdout_lines[2:]
        return ver, prefix, libdir, sitelibdir, sys_path

    def _gen_python_import_paths_from_dirs(self, dirs):
        """Generate all Python import paths from a given list of dirs.
        
        This involves handling .pth files on the given dirs. It generates
        import "paths" rather than "dirs" because Python .egg files can be
        returned.
        
        Dev Notes:
        - Python's .pth files can have *executable* Python code. This
          currently is not handled (those kinds of lines are skipped).
        """
        for dir in dirs:
            if not exists(dir):
                continue
            yield dir
            try:
                for pth_path in glob(join(dir, "*.pth")):
                    for p in self._gen_python_import_paths_from_pth_path(pth_path):
                        yield p
            except EnvironmentError, ex:
                log.warn("error analyzing .pth files in '%s': %s", dir, ex)

    def _gen_python_import_paths_from_pth_path(self, pth_path):
        pth_dir = dirname(pth_path)
        for line in open(pth_path, 'r'):
            line = line.strip()
            if line.startswith("#"): # comment line
                continue
            path = join(pth_dir, line)
            if exists(path):
                yield path

    def _extra_dirs_from_env(self, env):
        extra_dirs = set()
        for pref in env.get_all_prefs("pythonExtraPaths"):
            if not pref: continue
            extra_dirs.update(d.strip() for d in pref.split(os.pathsep)
                              if exists(d.strip()))
        if extra_dirs:
            extra_dirs = set(
                self._gen_python_import_paths_from_dirs(extra_dirs)
            )                
            log.debug("Python extra lib dirs: %r", extra_dirs)
        return tuple(extra_dirs)

    def _buf_indep_libs_from_env(self, env):
        """Create the buffer-independent list of libs."""
        cache_key = "python-libs"
        if cache_key not in env.cache:
            env.add_pref_observer("python", self._invalidate_cache)
            env.add_pref_observer("pythonExtraPaths",
                                  self._invalidate_cache_and_rescan_extra_dirs)
            env.add_pref_observer("codeintel_selected_catalogs",
                                  self._invalidate_cache)
            db = self.mgr.db

            # Gather information about the current python.
            python = None
            if env.has_pref("python"):
                python = env.get_pref("python").strip() or None
            if not python or not exists(python):
                python = self._python_from_env(env)
            if not python:
                log.warn("no Python was found from which to determine the "
                         "import path")
                ver, prefix, libdir, sitelibdir, sys_path \
                    = None, None, None, None, []
            else:
                ver, prefix, libdir, sitelibdir, sys_path \
                    = self._python_info_from_python(python, env)
            libs = []

            # - extradirslib
            extra_dirs = self._extra_dirs_from_env(env)
            if extra_dirs:
                libs.append( db.get_lang_lib("Python", "extradirslib",
                                extra_dirs) )

            # Figure out which sys.path dirs belong to which lib.
            paths_from_libname = {"sitelib": [], "envlib": [], "stdlib": []}
            canon_sitelibdir = sitelibdir and normcase(sitelibdir) or None
            canon_prefix = prefix and normcase(prefix) or None
            for dir in sys_path:
                STATE = "envlib"
                canon_dir = normcase(dir)
                if dir == "": # -> curdirlib (already handled)
                    continue
                elif canon_dir.endswith(".zip") and isfile(dir):
                    log.warn("`%s': not handling .zip file on Python sys.path",
                             dir)
                    continue
                elif canon_dir.endswith(".egg") and isfile(dir):
                    #log.warn("`%s': not handling .egg file on Python sys.path",
                    #         dir)
                    continue
                elif canon_dir.startswith(canon_sitelibdir):
                    STATE = "sitelib"
                elif canon_dir.startswith(canon_prefix):
                    STATE = "stdlib"
                if not exists(dir):
                    continue
                paths_from_libname[STATE].append(dir)
            log.debug("Python %s paths for each lib:\n%s",
                      ver, indent(pformat(paths_from_libname)))

            # - envlib, sitelib, cataloglib, stdlib
            if paths_from_libname["envlib"]:
                libs.append( db.get_lang_lib("Python", "envlib", 
                                paths_from_libname["envlib"]) )
            if paths_from_libname["sitelib"]:
                libs.append( db.get_lang_lib("Python", "sitelib", 
                                paths_from_libname["sitelib"]) )
            catalog_selections = env.get_pref("codeintel_selected_catalogs")
            libs += [
                db.get_catalog_lib("Python", catalog_selections),
                db.get_stdlib("Python", ver)
            ]
            env.cache[cache_key] = libs

        return env.cache[cache_key]

    def libs_from_buf(self, buf):
        env = buf.env

        # A buffer's libs depend on its env and the buf itself so
        # we cache it on the env and key off the buffer.
        if "python-buf-libs" not in env.cache:
            env.cache["python-buf-libs"] = weakref.WeakKeyDictionary()
        cache = env.cache["python-buf-libs"] # <buf-weak-ref> -> <libs>

        if buf not in cache:
            # - curdirlib
            # Using the dirname of this buffer isn't always right, but
            # hopefully is a good first approximation.
            cwd = dirname(buf.path)
            if cwd == "<Unsaved>":
                libs = []
            else:
                libs = [ self.mgr.db.get_lang_lib("Python", "curdirlib",
                                                  [dirname(buf.path)]) ]

            libs += self._buf_indep_libs_from_env(env)
            cache[buf] = libs
        return cache[buf]

    def _invalidate_cache(self, env, pref_name):
        for key in ("python-buf-libs", "python-libs"):
            if key in env.cache:
                log.debug("invalidate '%s' cache on %r", key, env)
                del env.cache[key]

    def _invalidate_cache_and_rescan_extra_dirs(self, env, pref_name):
        self._invalidate_cache(env, pref_name)
        extra_dirs = self._extra_dirs_from_env(env)
        if extra_dirs:
            extradirslib = self.mgr.db.get_lang_lib(
                "Python", "extradirslib", extra_dirs)
            request = PreloadLibRequest(extradirslib)
            self.mgr.idxr.stage_request(request, 1.0)


#class PythonCitadelEvaluator(CitadelEvaluator):
#    def post_process_cplns(self, cplns):
#        """Drop special __FOO__ methods.
#        
#        Note: Eventually for some Python completions we might want to leave
#        these in. For example:
#        
#            class Bar(Foo):
#                def __init__(self):
#                    Foo.<|>    # completions should include "__init__" here
#        """
#        for i in range(len(cplns)-1, -1, -1):
#            value = cplns[i][1]
#            if value.startswith("__") and value.endswith("__"):
#                del cplns[i]
#        return CitadelEvaluator.post_process_cplns(self, cplns)


class PythonBuffer(CitadelBuffer):
    lang = lang
    # Fillup chars for Python: basically, any non-identifier char.
    # - remove '*' from fillup chars because: "from foo import <|>*"
    cpln_fillup_chars = "~`!@#$%^&()-=+{}[]|\\;:'\",.<>?/ "
    cpln_stop_chars = "~`!@#$%^&*()-=+{}[]|\\;:'\",.<>?/ "
    sce_prefixes = ["SCE_P_"]

    cb_show_if_empty = True

    @property
    def libs(self):
        return self.langintel.libs_from_buf(self)

    def trg_from_pos(self, pos, implicit=True):
        """Python trigger types:

        python-complete-object-members
        python-calltip-call-signature
        python-complete-pythondoc-tags
        complete-available-imports
        complete-module-members
        
        Not yet implemented:
            complete-available-classes
            calltip-base-signature
        """
        DEBUG = False # not using 'logging' system, because want to be fast
        if DEBUG:
            print "\n----- Python trg_from_pos(pos=%r, implicit=%r) -----"\
                  % (pos, implicit)

        if pos == 0:
            return None
        accessor = self.accessor
        last_pos = pos - 1
        last_char = accessor.char_at_pos(last_pos)
        if DEBUG:
            print "  last_pos: %s" % last_pos
            print "  last_char: %r" % last_char

        # Quick out if the preceding char isn't a trigger char.
        if last_char not in " .(@":
            if DEBUG:
                print "trg_from_pos: no: %r is not in ' .(@'" % last_char
            return None

        style = accessor.style_at_pos(last_pos)
        if DEBUG:
            style_names = self.style_names_from_style_num(style)
            print "  style: %s (%s)" % (style, ", ".join(style_names))

        if last_char == "@":
            # Possibly python-complete-pythondoc-tags (the only trigger
            # on '@').
            #
            # Notes:
            # - PythonDoc 2.1b6 started allowing pythondoc tags in doc
            #   strings which we are yet supporting here.
            # - Trigger in comments should only happen if the comment
            #   begins with the "##" pythondoc signifier. We don't
            #   bother checking that (PERF).
            if style in self.comment_styles():
                # Only trigger at start of comment line.
                WHITESPACE = tuple(" \t")
                SENTINEL = 20
                i = last_pos-1
                while i >= max(0, last_pos-SENTINEL):
                    ch = accessor.char_at_pos(i)
                    if ch == "#":
                        return Trigger(self.lang, TRG_FORM_CPLN,
                                       "pythondoc-tags", pos, implicit)
                    elif ch in WHITESPACE:
                        pass
                    else:
                        return None
                    i -= 1
            return None

        # Remaing triggers should never trigger in some styles.
        if (implicit and style in self.implicit_completion_skip_styles
            or style in self.completion_skip_styles):
            if DEBUG:
                print "trg_from_pos: no: completion is suppressed "\
                      "in style at %s: %s (%s)"\
                      % (last_pos, style, ", ".join(style_names))
            return None

        if last_char == " ":
            # used for complete-available-imports and complete-module-members

            # Triggering examples ('_' means a space here):
            #   import_                 from_
            # Non-triggering examples:
            #   from FOO import_        Ximport_
            # Not bothering to support:
            #;  if FOO:import_          FOO;import_

            # Typing a space is very common so lets have a quick out before
            # doing the more correct processing:
            if last_pos-1 < 0 or accessor.char_at_pos(last_pos-1) not in "tm,":
                return None

            working_text = accessor.text_range(max(0,last_pos-200),
                                               last_pos)
            line = self._last_logical_line(working_text).strip()
            if not line: return None
            ch = line[-1]
            line = line.replace('\t', ' ')

            # from <|>
            # import <|>
            if line == "from" or line == "import":
                return Trigger(self.lang, TRG_FORM_CPLN,
                               "available-imports", pos, implicit,
                               imp_prefix=())

            # is it "from FOO import <|>" ?
            if line.endswith(" import"):
                if line.startswith('from '):
                    imp_prefix = tuple(line[len('from '):-len(' import')].strip().split('.'))
                    return Trigger(self.lang, TRG_FORM_CPLN,
                               "module-members", pos, implicit,
                               imp_prefix=imp_prefix)

            if ch == ',':
                # is it "from FOO import BAR, <|>" ?
                if line.startswith('from ') and ' import ' in line:
                    imp_prefix = tuple(line[len('from '):line.index(' import')].strip().split('.'))
                    # Need better checks
                    return Trigger(self.lang, TRG_FORM_CPLN,
                               "module-members", pos, implicit,
                               imp_prefix=imp_prefix)

        elif last_char == '.': # must be "complete-object-members" or None
            # If the first non-whitespace character preceding the '.' in the
            # same statement is an identifer character then trigger, if it
            # is a ')', then _maybe_ we should trigger (yes if this is
            # function call paren).
            #
            # Triggering examples:
            #   FOO.            FOO .                       FOO; BAR.
            #   FOO().          FOO.BAR.                    FOO(BAR, BAZ.
            #   FOO().BAR.      FOO("blah();", "blam").     FOO = {BAR.
            #   FOO(BAR.        FOO[BAR.
            #   ...more cases showing possible delineation of expression
            # Non-triggering examples:
            #   FOO..
            #   FOO[1].         too hard to determine sequence element types
            #   from FOO import (BAR.         
            # Not sure if want to support:
            #   "foo".          do we want to support literals? what about
            #                   lists? tuples? dicts?
            working_text = accessor.text_range(max(0,last_pos-200),
                                               last_pos)
            line = self._last_logical_line(working_text).strip()
            if line:
                ch = line[-1]
                if (isident(ch) or isdigit(ch) or ch == ')'):
                    line = line.replace('\t', ' ')
                    if line.startswith('from '):
                        if ' import ' in line:
                            # we're in "from FOO import BAR." territory,
                            # which is not a trigger
                            return None
                        # from FOO.
                        imp_prefix = tuple(line[len('from '):].strip().split('.'))
                        return Trigger(self.lang, TRG_FORM_CPLN,
                                       "available-imports", pos, implicit,
                                       imp_prefix=imp_prefix)
                    elif line.startswith('import '):
                        # import FOO.
                        # figure out the dotted parts of "FOO" above
                        imp_prefix = tuple(line[len('import '):].strip().split('.'))
                        return Trigger(self.lang, TRG_FORM_CPLN,
                                       "available-imports", pos, implicit,
                                       imp_prefix=imp_prefix)
                    else:
                        return Trigger(self.lang, TRG_FORM_CPLN,
                                       "object-members", pos, implicit)
                elif ch in ("\"'"):
                    return Trigger(self.lang, TRG_FORM_CPLN,
                                   "literal-members", pos, implicit,
                                   citdl_expr="str")
            else:
                ch = None
            if DEBUG:
                print "trg_from_pos: no: non-ws char preceding '.' is not "\
                      "an identifier char or ')': %r" % ch
            return None

        elif last_char == '(':
            # If the first non-whitespace character preceding the '(' in the
            # same statement is an identifer character then trigger calltip,
            #
            # Triggering examples:
            #   FOO.            FOO (                       FOO; BAR(
            #   FOO.BAR(        FOO(BAR, BAZ(               FOO = {BAR(
            #   FOO(BAR(        FOO[BAR(
            # Non-triggering examples:
            #   FOO()(      a function call returning a callable that is
            #               immediately called again is too rare to bother
            #               with
            #   def foo(    might be a "calltip-base-signature", but this
            #               trigger is not yet implemented
            #   import (    will be handled by complete_members
            #   class Foo(  is an "complete-available-classes" trigger,
            #               but this is not yet implemented
            working_text = accessor.text_range(max(0,last_pos-200), last_pos)
            line = self._last_logical_line(working_text).rstrip()
            if line:
                ch = line[-1]
                if isident(ch) or isdigit(ch):
                    # If this is:
                    #   def foo(
                    # then this might be the (as yet unimplemented)
                    # "calltip-base-signature" trigger or it should not be a
                    # trigger point.
                    #
                    # If this is:
                    #   class Foo(
                    # then this should be the (as yet unimplemented)
                    # "complete-available-classes" trigger.
                    line = line.replace('\t', ' ')
                    lstripped = line.lstrip()
                    if lstripped.startswith("def"):
                        if DEBUG: print "trg_from_pos: no: point is function declaration"
                    elif lstripped.startswith("class") and '(' not in lstripped:
                        # Second test is necessary to not exclude:
                        #   class Foo(bar(<|>
                        if DEBUG: print "trg_from_pos: no: point is class declaration"
                    elif lstripped.startswith('from ') and ' import' in lstripped:
                        # Need better checks
                        # is it "from FOO import (<|>" ?
                        imp_prefix = tuple(lstripped[len('from '):lstripped.index(' import')].split('.'))
                        if DEBUG: print "trg_from_pos: from FOO import ("
                        return Trigger(self.lang, TRG_FORM_CPLN,
                                   "module-members", pos, implicit,
                                   imp_prefix=imp_prefix)
                    else:
                        return Trigger(self.lang, TRG_FORM_CALLTIP,
                                       "call-signature", pos, implicit)
                else:
                    if DEBUG:
                        print "trg_from_pos: no: non-ws char preceding "\
                              "'(' is not an identifier char: %r" % ch
            else:
                if DEBUG: print "trg_from_pos: no: no chars preceding '('"
            return None

    def _last_logical_line(self, text):
        lines = text.splitlines(0) or ['']
        logicalline = lines.pop()
        while lines and lines[-1].endswith('\\'):
            logicalline = lines.pop()[:-1] + ' ' + logicalline
        return logicalline



class PythonImportHandler(ImportHandler):
    lang = lang #XXX do this for other langs as well
    PATH_ENV_VAR = "PYTHONPATH"
    sep = '.'

    def __init__(self, mgr):
        ImportHandler.__init__(self, mgr)
        self.__stdCIXScanId = None

    #TODO: may not be used. If so, drop it.
    def _shellOutForPath(self, compiler):
        import process
        argv = [compiler, "-c", "import sys; print '\\n'.join(sys.path)"]
        # Can't use -E to ignore PYTHONPATH because older versions of
        # Python don't have it (e.g. v1.5.2).
        env = dict(os.environ)
        if "PYTHONPATH" in env: del env["PYTHONPATH"]
        if "PYTHONHOME" in env: del env["PYTHONHOME"]
        if "PYTHONSTARTUP" in env: del env["PYTHONSTARTUP"]

        p = process.ProcessOpen(argv, env=env, stdin=None)
        stdout, stderr = p.communicate()
        retval = p.returncode
        path = [line for line in stdout.splitlines(0)]
        if path and (path[0] == "" or path[0] == os.getcwd()):
            del path[0] # cwd handled separately
        return path

    def setCorePath(self, compiler=None, extra=None):
        if compiler is None:
            import which
            compiler = which.which("python")
        self.corePath = self._shellOutForPath(compiler)

    def _findScannableFiles(self,
                            (files, searchedDirs, skipRareImports,
                             importableOnly),
                            dirname, names):
        if sys.platform.startswith("win"):
            cpath = dirname.lower()
        else:
            cpath = dirname
        if cpath in searchedDirs:
            while names:
                del names[0]
            return
        else:
            searchedDirs[cpath] = 1
        if skipRareImports:
            if (os.path.basename(dirname) == "encodings"
                and "undefined.py" in names):
                # Skip most of the specific encoding definitions (saves
                # about 50 files).
                names = [n for n in names if n == "__init__.py"
                         or os.path.splitext(n)[0].endswith("_codec")]
        for i in range(len(names)-1, -1, -1): # backward so can del from list
            path = os.path.join(dirname, names[i])
            if os.path.isdir(path):
                if skipRareImports:
                    # Skip Python's test package (saves over 200 files)
                    # and other likely test dirs.
                    if names[i] in ("test", "tests"):
                        del names[i]
                        continue
                if importableOnly:
                    possibles = [os.path.join(path, "__init__.py"),
                                 os.path.join(path, "__init__.pyc"),
                                 os.path.join(path, "__init__.pyo")]
                    for possible in possibles:
                        if os.path.isfile(possible):
                            break
                    else:
                        del names[i] # don't traverse non-package dirs
                        continue
                if path.endswith(os.path.join("win32com", "gen_py")):
                    del names[i]
                    continue
            elif os.path.splitext(names[i])[1] in (".py", ".pyw"):
                #XXX The list of Python extensions should be settable on
                #    the ImportHandler and Komodo should set whatever is
                #    set in prefs.
                #XXX This check for "Python" files should probably include
                #    python scripts, which might likely not have the
                #    extension: need to grow filetype-from-content smarts.
                files.append(path)

    def genScannableFiles(self, path=None, skipRareImports=False,
                          importableOnly=False):
        if path is None:
            path = self._getPath()
        searchedDirs = {}
        for dirname in path:
            #XXX Use os.walk().
            files = []
            os.path.walk(dirname, self._findScannableFiles,
                         (files, searchedDirs, skipRareImports,
                          importableOnly))
            for file in files:
                yield file

    def find_importables_in_dir(self, dir):
        """See citadel.py::ImportHandler.find_importables_in_dir() for
        details.

        Importables for Python look like this:
            {"foo":    ("foo.py",             None,       False),
             "foolib": ("foolib/__init__.py", "__init__", False)}

        TODO: consider *.pyd/so files when have a story for binary modules
              on the fly
        """
        if dir == "<Unsaved>":
            #TODO: stop these getting in here.
            return {}
        importables = {}
        for path in glob(join(dir, "*.py")):
            base = basename(path)
            sans_ext = splitext(base)[0]
            if sans_ext == '__init__': continue # no need for these
            importables[sans_ext] = (base, None, False)
        for path in glob(join(dir, "*", "__init__.py")):
            base = path[len(dir)+1:]
            importables[dirname(base)] = (base, "__init__", False)
        return importables




class PythonCILEDriver(CILEDriver):
    lang = lang

    def scan_purelang(self, buf):
        #log.warn("TODO: python cile that uses elementtree")
        content = buf.accessor.text
        if isinstance(content, unicode):
            encoding = buf.encoding or "utf-8"
            try:
                content = content.encode(encoding)
            except UnicodeError, ex:
                raise CodeIntelError("cannot encode Python content as %r (%s)"
                                     % (encoding, ex))
        cix = pythoncile.scan(content, buf.path)
        from codeintel2.tree import tree_from_cix
        return tree_from_cix(cix)



#---- internal support stuff




#---- registration

def register(mgr):
    """Register language support with the Manager."""
    mgr.set_lang_info(lang,
                      silvercity_lexer=PythonLexer(),
                      buf_class=PythonBuffer,
                      langintel_class=PythonLangIntel,
                      import_handler_class=PythonImportHandler,
                      cile_driver_class=PythonCILEDriver,
                      is_cpln_lang=True)

