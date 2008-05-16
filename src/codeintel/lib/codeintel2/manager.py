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

"""The "Manager" is the controlling instance for a codeintel system."""

import os
from os.path import dirname, join, abspath, splitext, basename, isabs
import sys
import time
import md5
import pprint
import threading
import stat
import types
import imp
import shutil
import logging
from glob import glob
import threading
from Queue import Queue
import traceback

from SilverCity import ScintillaConstants

from codeintel2.common import *
from codeintel2.accessor import *
from codeintel2.citadel import Citadel
from codeintel2.buffer import ImplicitBuffer
from codeintel2.langintel import ImplicitLangIntel
from codeintel2.database.database import Database
from codeintel2.environment import DefaultEnvironment
from codeintel2 import indexer
from codeintel2.util import guess_lang_from_path
from codeintel2.udl import XMLParsingBufferMixin, UDLBuffer

import langinfo

try:
    from xpcom import components
    from xpcom.client import WeakReference
    _xpcom_ = True
except ImportError:
    _xpcom_ = False



#---- global variables

log = logging.getLogger("codeintel")
#log.setLevel(logging.INFO)



#---- public interface

class Manager(threading.Thread, Queue):
    # See the module docstring for usage information.

    def __init__(self, db_base_dir=None, on_scan_complete=None, langs=None,
                 extra_lang_module_dirs=None, env=None,
                 db_event_reporter=None, db_catalog_dirs=None,
                 db_import_everything_langs=None):
        """Create a CodeIntel manager.
        
            "db_base_dir" (optional) specifies the base directory for
                the codeintel database. If not given it will default to
                '~/.codeintel'.
            "on_scan_complete" (optional) is a callback for Citadel scan
                completion. It will be passed the ScanRequest instance
                as an argument.
            "langs" (optional, default all) is a list of language names
                to register. By default all available supported languages are
                setup.
            "extra_lang_module_dirs" (optional) is a list of extra dirs
                in which to look for and use "lang_*.py" lang support
                modules.
            "env" (optional) is an Environment instance (or subclass).
                See environment.py for details.
            "db_event_reporter" (optional) is a callback that will be called
                    db_event_reporter(<event-desc-string>)
                before "significant" long processing events in the DB. This
                may be useful to forward to a status bar in a GUI.
            "db_catalog_dirs" (optional) is a list of catalog dirs in
                addition to the std one to use for the CatalogsZone. All
                *.cix files in a catalog dir are made available.
            "db_import_everything_langs" (optional) is a set of langs for which
                the extra effort to support Database
                `lib.hits_from_lpath()' should be made. See class
                Database for more details.
        """
        threading.Thread.__init__(self, name="CodeIntel Manager")
        Queue.__init__(self)

        self.citadel = Citadel(self)

        # Language registry bits.
        self._attempted_registered_safe_lang = {}  # {safe-lang: True}
        self._registered_lang_from_safe_lang = {}
        self.silvercity_lexer_from_lang = {}
        self.buf_class_from_lang = {}
        self.langintel_class_from_lang = {}
        self._langintel_from_lang_cache = {}
        self.import_handler_class_from_lang = {}
        self._is_citadel_from_lang = {} # registered langs that are Citadel-based
        self._is_cpln_from_lang = {} # registered langs for which completion is supported

        self.register_langs(langs, extra_lang_module_dirs)
        self.env = env or DefaultEnvironment() 
        self.db = Database(self, base_dir=db_base_dir,
                           catalog_dirs=db_catalog_dirs,
                           event_reporter=db_event_reporter,
                           import_everything_langs=db_import_everything_langs)
        self.idxr = indexer.Indexer(self, on_scan_complete)
        self.lidb = langinfo.get_default_database()

    def upgrade(self):
        """Upgrade the database, if necessary.
        
        It blocks until the upgrade is complete.  Alternatively, if you
        want more control over upgrading use:
            Database.upgrade_info()
            Database.upgrade()
            Database.reset()
        """
        log.debug("upgrade db if necessary")
        status, reason = self.db.upgrade_info()
        if status == Database.UPGRADE_NECESSARY:
            log.info("db upgrade is necessary")
            self.db.upgrade()
        elif status == Database.UPGRADE_NOT_POSSIBLE:
            log.warn("%s (resetting db)", reason)
            log.info("reset db at `%s' (creating backup)", self.db.base_dir)
            self.db.reset()
        elif status == Database.UPGRADE_NOT_NECESSARY:
            log.debug("no upgrade necessary")
        else:
            raise CodeIntelError("unknown db upgrade status: %r" % status)

    def initialize(self):
        """Initialize the codeintel system."""
        self.idxr.start()

    def register_langs(self, langs=None, extra_lang_module_dirs=None):
        """Register languages.
        
        @param langs {list} is an optional list of language names
            to register. If not given, all available languages are
            registered. Note that these given language names are
            compared (case-insensitively) to the name of the
            "lang_<lang>.py" module *filenames*. Admittedly this isn't ideal.
        @param extra_lang_module_dirs {list} is an optional list of extra
            dirs in which to look for and use "lang_*.py" lang support
            modules. By default just the codeintel2 package directory is
            used.
            
        An "available" language is one for which there is a "lang_*.py"
        module.
        """
        dirs = [dirname(__file__)]
        if extra_lang_module_dirs:
            dirs += extra_lang_module_dirs
        remaining_langs = langs and set(lang.lower() for lang in langs) or None
        for dir in dirs:
            for module_path in glob(join(dir, "lang_*.py")):
                lang = basename(module_path)[5:-3]
                if langs and lang not in remaining_langs:
                    continue
                self.register_lang(lang, module_path)
                if remaining_langs:
                    remaining_langs.remove(lang)
        if remaining_langs:
            log.warn("could not find support modules for these langs: %s"
                     % ", ".join(remaining_langs))

    def register_lang(self, lang, module_path):
        """Register the given language.
        
        @param lang {str} is the name of the language to register (e.g.
            "Python"). To support .initialize(lang='*') this argument may
            be the "safe lang" name (e.g. "python")
        @param module_path {str} is the path to the lang support module.

        This will import the given module path and call its top-level
        "register" function passing it the Manager instance. That is
        expected to callback to `mgr.set_lang_info()'. This can raise
        ImportError or CodeIntelError. This is a no-op if already called
        for a particular language.
        """
        safe_lang = lang.lower()
        if safe_lang in self._attempted_registered_safe_lang:
            return
        self._attempted_registered_safe_lang[safe_lang] = True
        module_dir, module_name = os.path.split(module_path)
        module_name = splitext(module_name)[0]
        iinfo = imp.find_module(module_name, [module_dir])
        module = imp.load_module(module_name, *iinfo)
        if hasattr(module, "register"):
            log.debug("register %s (%s) lang support", module.lang, safe_lang)
            try:
                module.register(self)
            except CodeIntelError, ex:
                log.warn("error registering %s (%s) lang (lang will be "
                         "disabled): %s", module.lang, safe_lang, ex)
            except:
                log.exception("error registering %s (%s) lang",
                              module.lang, safe_lang)
            else:
                self._registered_lang_from_safe_lang[safe_lang] = module.lang

    def set_lang_info(self, lang, silvercity_lexer=None, buf_class=None,
                      import_handler_class=None, cile_driver_class=None,
                      is_cpln_lang=False, langintel_class=None):
        """Called by register() functions in language support modules."""
        if silvercity_lexer:
            self.silvercity_lexer_from_lang[lang] = silvercity_lexer
        if buf_class:
            self.buf_class_from_lang[lang] = buf_class
        if langintel_class:
            self.langintel_class_from_lang[lang] = langintel_class
        if import_handler_class:
            self.import_handler_class_from_lang[lang] = import_handler_class
        if cile_driver_class is not None:
            self._is_citadel_from_lang[lang] = True
            self.citadel.set_lang_info(lang, cile_driver_class,
                                       is_cpln_lang=is_cpln_lang)
        if is_cpln_lang:
            self._is_cpln_from_lang[lang] = True

    def finalize(self, timeout=None):
        if self.citadel is not None:
            self.citadel.finalize()
        if self.isAlive():
            self.stop()
            self.join(timeout)
        self.idxr.finalize()
        if self.db is not None:
            try:
                self.db.save()
            except Exception:
                log.exception("error saving database")
            self.db = None # break the reference

    # Proxy the batch update API onto our Citadel instance.
    def batch_update(self, join=True, updater=None):
        return self.citadel.batch_update(join=join, updater=updater)

    def is_registered_lang(self, lang):
        """Return true if this is a registered language."""
        safe_lang = lang.lower()
        return safe_lang in self._registered_lang_from_safe_lang

    def is_multilang(self, lang):
        """Return True iff this is a multi-lang language.

        I.e. Is this a language that supports embedding of different
        programming languages. For example RHTML can have Ruby and
        JavaScript content, HTML can have JavaScript content.
        """
        return issubclass(self.buf_class_from_lang[lang], UDLBuffer)

    def is_xml_lang(self, lang):
        try:
            buf_class = self.buf_class_from_lang[lang]
        except KeyError:
            return False
        return issubclass(buf_class, XMLParsingBufferMixin)

    def is_cpln_lang(self, lang):
        """Return True iff codeintel supports completion (i.e. autocomplete
        and calltips) for this language."""
        return lang in self._is_cpln_from_lang
    def get_cpln_langs(self):
        return self._is_cpln_from_lang.keys()

    def is_citadel_lang(self, lang):
        """Returns True if the given lang has been registered and
        is a Citadel-based language.
        
        A "Citadel-based" language is one that uses CIX/CIDB/CITDL tech for
        its codeintel. Note that currently not all Citadel-based langs use
        the Citadel system for completion (e.g. PHP and Tcl).
        """
        return lang in self._is_citadel_from_lang
    def get_citadel_langs(self):
        return self._is_citadel_from_lang.keys()

    def langintel_from_lang(self, lang):
        if lang not in self._langintel_from_lang_cache:
            try:
                langintel_class = self.langintel_class_from_lang[lang]
            except KeyError:
                langintel = ImplicitLangIntel(lang, self)
            else:
                langintel = langintel_class(self)
            self._langintel_from_lang_cache[lang] = langintel
        return self._langintel_from_lang_cache[lang] 

    #XXX
    #XXX Cache bufs based on (path, lang) so can share bufs. (weakref)
    #XXX 
    def buf_from_koIDocument(self, doc, env=None):
        lang = doc.language
        path = doc.displayPath
        if doc.isUntitled:
            path = join("<Unsaved>", path)
        accessor = KoDocumentAccessor(doc,
            self.silvercity_lexer_from_lang.get(lang))
        encoding = doc.encoding.python_encoding_name
        try:
            buf_class = self.buf_class_from_lang[lang]
        except KeyError:
            buf = ImplicitBuffer(lang, self, accessor, env, path, encoding)
        else:
            buf = buf_class(self, accessor, env, path, encoding)
        return buf

    def buf_from_content(self, content, lang, env=None, path=None,
                         encoding=None):
        lexer = self.silvercity_lexer_from_lang.get(lang)
        accessor = SilverCityAccessor(lexer, content)
        try:
            buf_class = self.buf_class_from_lang[lang]
        except KeyError:
            buf = ImplicitBuffer(lang, self, accessor, env, path, encoding)
        else:
            buf = buf_class(self, accessor, env, path, encoding)
        return buf

    def buf_from_path(self, path, lang=None, env=None, encoding=None):
        if lang is None:
            import textinfo
            ti = textinfo.textinfo_from_path(path, encoding=encoding,
                    follow_symlinks=True)
            lang = ti.lang
            encoding = ti.encoding
            content = ti.text
        elif encoding:
            content = codecs.open(path, 'rb', encoding).read()
        else:
            content = open(path, 'rb').read()

        #TODO: Re-instate this when have solution for CILE test failures
        #      that this causes.
        #if not isabs(path) and not path.startswith("<Unsaved>"):
        #    path = abspath(path)

        return self.buf_from_content(content, lang, env, path, encoding)

    
    #---- Completion Evaluation Session/Queue handling

    # The current eval session (an Evaluator instance). A current session's
    # lifetime is as follows:
    # - [self._get()] Starts when the evaluator thread (this class) takes it
    #   off the queue.
    # - [self._put()] Can be aborted (via sess.ctlr.abort()) if a new eval
    #   request comes in.
    # - [self._handle_eval_sess()] Done when the session completes either by
    #   (1) an unexpected error during sess.eval() or (2) sess.ctlr.is_done()
    #   after sess.eval().
    _curr_eval_sess = None

    def request_eval(self, evalr):
        """Request evaluation of the given completion.
        
            "evalr" is the Evaluator instance.

        The manager has an evaluation thread on which this evalr will be
        scheduled. Only one request is ever eval'd at one time. A new
        request will cause an existing on to be aborted and requests made in
        the interim will be trumped by this new one.

        Dev Notes:
        - XXX Add a timeout to the put and raise error on timeout?
        """
        #self._handle_eval_sess(evalr)
        self.put((evalr, False))
    
    def request_reeval(self, evalr):
        """Occassionally evaluation will need to defer until something (e.g.
        scanning into the CIDB) is one. These sessions will re-request
        evaluation via this method.
        """
        self.put((evalr, True))

    def stop(self):
        self.put((None, None)) # Sentinel to tell thread mainloop to stop.

    def run(self):
        while 1:
            eval_sess, is_reeval = self.get()
            if eval_sess is None: # Sentinel to stop.
                break
            try:
                self._handle_eval_sess(eval_sess)
            except:
                exc_info = sys.exc_info()
                tb_path, tb_lineno, tb_func \
                    = traceback.extract_tb(exc_info[2])[-1][:3]
                if hasattr(exc_info[0], "__name__"):
                    exc_str = "%s: %s" % (exc_info[0].__name__, exc_info[1])
                else: # string exception
                    exc_str = exc_info[0]
                eval_sess.ctlr.error("error evaluating %s: %s "
                                     "(%s#%s in %s)", eval_sess, exc_str,
                                     tb_path, tb_lineno, tb_func)
                log.exception("error evaluating %s" % eval_sess)
                eval_sess.ctlr.done("unexpected eval error")

    def _handle_eval_sess(self, eval_sess):
        try:
            eval_sess.eval(self)
        except Exception:
            self._curr_eval_sess = None
            raise
        else:
            if eval_sess.ctlr.is_done():
                self._curr_eval_sess = None

    def _put(self, (eval_sess, is_reeval)):
        # Only consider re-evaluation if we are still on the same eval
        # session.
        if is_reeval and self._curr_eval_sess is not eval_sess:
            return
        
        # We only allow *one* eval session at a time.
        # - Drop a possible accumulated eval session.
        if len(self.queue):
            self.queue.clear()
        # - Abort the current eval session.
        if not is_reeval and self._curr_eval_sess is not None:
            self._curr_eval_sess.ctlr.abort()

        # Lazily start the eval thread.
        if not self.isAlive():
            self.start()

        Queue._put(self, (eval_sess, is_reeval))
        assert len(self.queue) == 1

    def _get(self):
        eval_sess, is_reeval = Queue._get(self)
        if is_reeval:
            assert self._curr_eval_sess is eval_sess
        else:
            self._curr_eval_sess = eval_sess
        return eval_sess, is_reeval



