#!python
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

# The implementation of the Komodo Find and Replace service

from __future__ import with_statement

import os
from os.path import abspath, islink, dirname, join, isabs, expanduser, normpath, realpath
import sys
import string, types
import re
import logging
import time
import threading
from pprint import pprint
from itertools import chain
from hashlib import md5

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import UnwrapObject
from koTreeView import TreeView
import findlib2
import textutils
import langinfo
import textinfo
from zope.cachedescriptors.property import Lazy as LazyProperty



#---- globals

log = logging.getLogger("find")
#log.setLevel(logging.DEBUG)

# find types
FOT_SIMPLE = components.interfaces.koIFindOptions.FOT_SIMPLE
FOT_WILDCARD = components.interfaces.koIFindOptions.FOT_WILDCARD
FOT_REGEX_PYTHON = components.interfaces.koIFindOptions.FOT_REGEX_PYTHON

# case sensitivity options
FOC_INSENSITIVE = components.interfaces.koIFindOptions.FOC_INSENSITIVE
FOC_SENSITIVE = components.interfaces.koIFindOptions.FOC_SENSITIVE
FOC_SMART = components.interfaces.koIFindOptions.FOC_SMART

koIFindContext = components.interfaces.koIFindContext
ISciMoz = components.interfaces.ISciMoz

# services setup in Find Service ctor
gPrefSvc = None
gLastErrorSvc = None
_g_loaded_path_accessor = None


#---- Runtime Environment
# This is a customization of the "runtime environment" API used by
# findlib2/textinfo for the Komodo runtime environment.
#TODO: Eventually hook in `runtimeenv.RuntimeEnv` stuff (see checklib)
#      when more fully using that facility.

class KomodoRuntimeEnv(object):
    def __init__(self):
        self.lidb = langinfo.get_default_database()

        langRegSvc = components.classes['@activestate.com/koLanguageRegistryService;1']\
            .getService(components.interfaces.koILanguageRegistryService)
        # We don't need the XPCOM version.
        self._langRegSvc = UnwrapObject(langRegSvc)

    def langinfo_from_filename(self, filename):
        """Return a `LangInfo` appropriate for the given filename based
        on Komodo file association prefs.
        
        If there is no Komodo file association for this filename, then
        return None. If there *is* a file association but the langinfo
        system has no appropriate `LangInfo` class, then return the
        base `TextLangInfo`. This works because for the purposes of
        Find/Replace in Files we just need to know if a given file is
        text or binary and all associable Komodo languages are text.

        This API is used by `textinfo._classify_filename` to attempt to
        determine filetype (aka "lang") from the filename. Here we hook
        that into Komodo's file-association prefs.
        """
        komodo_lang = self._langRegSvc.suggestLanguageForFile(filename)
        if not komodo_lang:
            return None

        # Komodo has a file association for this filename. Find an
        # appropriate LangInfo for this Komodo language name.
        try:
            li = self.lidb.langinfo_from_komodo_lang(komodo_lang)
        except langinfo.LangInfoError:
            li = self.lidb.langinfo_from_lang("Text")
        return li


#---- Find/Replace in Files backend

class _FindReplaceInFilesThread(threading.Thread):
    """A thread for doing find/replace operations in the background and
    reporting results to a "results manager" (a JS-implemented handlers
    for a "Find Results" tab in the Komodo UI.
    """
    # The number by which to chunk reporting results.
    REPORT_EVERY_N_HITS = 50
    REPORT_EVERY_N_PATHS_WITH_HITS = 5
    REPORT_EVERY_N_PATHS_SEARCHED = 100

    MAX_XUL_TREE_CELL_LENGTH = 256
    
    def __init__(self, id, regex, repl, desc, paths, resultsMgr, env,
                 loaded_path_accessor=None, do_smart_replace=False):
        """Create a find/replace thread.
        
        @param id {string} the ID for this find/replace session
        @param name {string} a name for this thread
        @param regex {regex} the regular expression to search for
        @param repl {string} the replacement string, or None if this
            is just a find operation
        @param desc {string} a readable string description of the
            find/replace operation
        @param paths {list|generator} a list or generator of paths to
            consider
        @param resultsMgr {components.interfaces.koIFindResultsTabManager}
        @param env {runtime environment} the Komodo Runtime Environment
            to pass to findlib2.
        @param do_smart_replace {boolean} Is the pattern all lower-case,
            and are we matching with smart-case on?
        """
        threading.Thread.__init__(self, name="Find/Replace Thread %s" % id)
        self.id = id
        self.regex = regex
        self.repl = repl
        self.desc = desc
        self.paths = paths
        self.resultsMgr = resultsMgr
        self.env = env
        self.do_smart_replace = do_smart_replace

        class ResultsManagerProxy:
            def __init__(self, obj):
                self.obj = obj
            @components.ProxyToMainThread
            def searchFinished(self, *args):
                return self.obj.searchFinished(*args)
            @components.ProxyToMainThread
            def setDescription(self, *args):
                return self.obj.setDescription(*args)
        self.resultsMgrProxy = ResultsManagerProxy(resultsMgr)

        class ResultsViewProxy:
            def __init__(self, obj):
                self.obj = obj
            @components.ProxyToMainThread
            def AddFindResults(self, *args):
                return self.obj.AddFindResults(*args)
            @components.ProxyToMainThread
            def AddReplaceResults(self, *args):
                return self.obj.AddReplaceResults(*args)
        self.resultsViewProxy = ResultsViewProxy(resultsMgr.view)

        self._stopped = False # when true the processing thread should terminate
        self._reset_hit_cache()
        self.loadedFileTextFactory = LoadedFileTextFactory(loaded_path_accessor)

    def stop(self):
        """Stop processing."""
        log.debug("stopping replace in files thread")
        self._stopped = True

    def run(self):
        # Rule: if self._stopped is true then this code MUST NOT use
        #       self.resultsMgrProxy or self.resultsViewProxy, because they
        #       may have been destroyed.
        errmsg = None
        self.num_hits = 0
        self.num_paths_with_hits = 0
        self.num_paths_searched = 0
        self.num_paths_skipped = 0
        self.skip_filesizes_larger_than = None
        if gPrefSvc.prefs.getBooleanPref("find-skipLargeFilesEnabled"):
            self.skip_filesizes_larger_than = gPrefSvc.prefs.getLongPref("find-skipFileSizesLargerThan")
        self.journal = None
        try:
            if self._stopped:
                return

            self.resultsMgrProxy.setDescription("Preparing...", 0)
            if self.repl is None:
                self._find_in_paths(self.regex, self.paths)
            else:
                self._replace_in_paths(self.regex, self.repl, self.desc,
                                       self.paths)
        except Exception, ex:
            # Log this error to the Komodo UI.
            errmsg = "unexpected error: %s (details in log file)" % ex
            raise
        finally:
            journal_id = None
            if self.journal:
                journal_id = self.journal.id
                self.journal.close()
                # Ensure <Journal> isn't kept in memory until the next
                # Replace in Files.
                del self.journal
            if not self._stopped:
                self._report(flush=True)
                self.resultsMgrProxy.searchFinished(
                    True, self.num_hits, self.num_paths_with_hits,
                    self.num_paths_searched, journal_id)
                if errmsg is not None:
                    self.resultsMgrProxy.setDescription(errmsg, True)
                elif self.num_paths_searched == 0:
                    self.resultsMgrProxy.setDescription(
                        "No files were found to search in.", 1)
            fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"] \
                .getService(components.interfaces.koIFileStatusService)
            fileStatusSvc.updateStatusForAllFiles(
                components.interfaces.koIFileStatusChecker.REASON_FILE_CHANGED)

    def _reset_hit_cache(self):
        self._r_types = []
        self._r_urls = []
        self._r_startIndexes = []
        self._r_endIndexes = []
        self._r_values = []
        self._r_fileNames = []
        self._r_lineNums = []
        self._r_columnNums = []
        self._r_contexts = []
        if self.repl is not None:
            self._r_replacements = []

    def _cache_hit(self, type, url, startIndex, endIndex, value, fileName,
                   lineNum, columnNum, context, replacement=None):
        self._r_types.append(type)
        self._r_urls.append(url)
        self._r_startIndexes.append(startIndex)
        self._r_endIndexes.append(endIndex)
        self._r_values.append(value)
        self._r_fileNames.append(fileName)
        self._r_lineNums.append(lineNum)
        self._r_columnNums.append(columnNum)
        self._r_contexts.append(context)
        if self.repl is not None:
            self._r_replacements.append(replacement)

    def _find_in_paths(self, regex, paths):
        last_path_with_hits = None
        for event in findlib2.grep(regex, paths, env=self.env,
                                   skip_filesizes_larger_than=self.skip_filesizes_larger_than,
                                   textInfoFactory=self.loadedFileTextFactory):
            if self._stopped:
                return

            if isinstance(event, findlib2.SkipPath):
                self.num_paths_searched += 1
            elif not isinstance(event, findlib2.Hit):
                continue
            else:
                self.num_hits += 1
                if event.path != last_path_with_hits:
                    self.num_paths_searched += 1
                    self.num_paths_with_hits += 1
                    last_path_with_hits = event.path
                self._cache_find_hit(event)
            self._report()

    def _replace_in_paths(self, regex, repl, desc, paths):
        for event in findlib2.replace(regex, repl, paths, summary=desc,
                                      skip_filesizes_larger_than=self.skip_filesizes_larger_than,
                                      do_smart_replace=self.do_smart_replace,
                                      textInfoFactory=self.loadedFileTextFactory,
                                      env=self.env):
            if self._stopped:
                return
            if isinstance(event, findlib2.StartJournal):
                self.journal = event.journal
                continue
            elif isinstance(event, findlib2.SkipPath):
                self.num_paths_searched += 1
                if isinstance(event, findlib2.SkipUnknownLangPath):
                    self.num_paths_skipped += 1
                    self._cache_skipped_path(event)
                elif isinstance(event, findlib2.SkipBinaryPath):
                    #TODO: put these as warning rows in the UI?
                    log.debug("Skip `%s' (binary).", event.path)
            elif not isinstance(event, findlib2.Hit):
                continue
            else:
                assert isinstance(event, findlib2.ReplaceHitGroup)
                self.num_paths_searched += 1
                self.num_paths_with_hits += 1
                self.num_hits += event.length
                # Note: we must `event.commit()` before
                # `self._cache_replace_hits()` because the former
                # determines `event.rhits` that the latter needs
                event.commit(loadedFileManager=self.loadedFileTextFactory)
                self._cache_replace_hits(event, self.repl)
            self._report()

    def _cache_find_hit(self, hit):
        context = self._prepare_context(hit.lines)
        start_line, start_col = hit.start_line_and_col_num
        self._cache_hit(
            "hit", # type
            hit.path, # url
            hit.start_pos, # startIndex
            hit.end_pos, # endIndex
            hit.match.group(0), # value
            hit.path, # fileName
            start_line + 1, # lineNum (0-based -> 1-based)
            start_col + 1, # columnNum (0-based -> 1-based)
            context # context
        )

    def _cache_replace_hits(self, rgroup, repl):
        for rhit in rgroup.rhits:
            match = rhit.find_hit.match
            start_line, start_col = rhit.start_line_and_col_num
            context = self._prepare_context(rhit.lines)
            self._cache_hit(
                "hit", # type
                rgroup.path, # url
                rhit.start_pos, # startIndex
                rhit.end_pos, # endIndex
                match.group(0), # value
                rgroup.path, # fileName
                start_line + 1, # lineNum (0-based -> 1-based)
                start_col + 1, # columnNum (0-based -> 1-based)
                context, # context
                match.expand(repl) # replacement
            )
            # Done with line/column calculations for this hit.
            rhit.cull_mem()

    def _cache_skipped_path(self, event):
        self._cache_hit(
            "warning", # type
            event.path, # url
            0, # startIndex
            0, # endIndex
            None, # value
            event.path, # fileName
            0, # lineNum (0-based -> 1-based)
            0, # columnNum (0-based -> 1-based)
            "skipped (%s)" % event.reason, # context
            None # replacement
        )

    def _prepare_context(self, lines):
        """Do some common processing of the "context" for a find- or
        replace-result.
        """
        context = '\n'.join(lines)

        # Don't want to see black boxes for EOLs in find results tab.
        context = context.rstrip('\r\n')

        # Firefox trees don't like displaying *very* long lines
        # which the occassional exceptional situation will cause
        # (e.g.  Komodo's own webdata.js). Trim the "content"
        # find result length.
        if len(context) > self.MAX_XUL_TREE_CELL_LENGTH:
            context = context[:self.MAX_XUL_TREE_CELL_LENGTH]

        # When the context gets passed to AddFindResults pyxpcom will
        # convert it into a unicode string automatically. However, if we
        # happened to get a result on a binary file, that will fail and we
        # will not see any results. protect against that by trying to make
        # the string unicode, and failing that, repr it.
        if type(context) != types.UnicodeType:
            try:
                context = unicode(context)
            except UnicodeError, ex:
                context = repr(context)[1:-1]
        
        return context

    _last_report_num_hits = 0
    _last_report_num_paths_searched = 0
    _last_report_num_paths_with_hits = 0
    def _report(self, flush=False):
        """Report current results to the `resultsMgr`.
        
        For performance we batch up reporting.
        """
        if self._stopped:
            return

        # Determine if we should report.
        if flush:
            pass    # report
        elif (self.num_hits != self._last_report_num_hits
              and self.num_hits % self.REPORT_EVERY_N_HITS == 0):
            pass    # report
        elif (self.num_paths_searched != self._last_report_num_paths_searched
              and self.num_paths_searched % self.REPORT_EVERY_N_PATHS_SEARCHED == 0):
            pass    # report
        elif (self.num_paths_with_hits != self._last_report_num_paths_with_hits
              and self.num_paths_with_hits % self.REPORT_EVERY_N_PATHS_WITH_HITS == 0):
            pass    # report
        else:
            return  # skip reporting

        if self.repl is None:
            verb = "Found"
        else:
            verb = "Replaced"

        if self._r_urls:
            if self.repl is None:
                self.resultsViewProxy.AddFindResults(
                    self._r_types,
                    self._r_urls, self._r_startIndexes, self._r_endIndexes,
                    self._r_values, self._r_fileNames,
                    self._r_lineNums, self._r_columnNums, self._r_contexts)
            else:
                self.resultsViewProxy.AddReplaceResults(
                    self._r_types,
                    self._r_urls, self._r_startIndexes, self._r_endIndexes,
                    self._r_values, self._r_replacements, self._r_fileNames,
                    self._r_lineNums, self._r_columnNums, self._r_contexts)
            self._reset_hit_cache()

        # Set a description of the current state for the results tab UI.
        if self.num_paths_searched == 1:
            files_str = "1 file"
        else:
            files_str = str(self.num_paths_searched) + " files"
        desc = "%s %d occurrences in %d of %s so far."\
               % (verb, self.num_hits, self.num_paths_with_hits,
                  files_str)
        self.resultsMgrProxy.setDescription(desc, 0)

        self._last_report_num_hits = self.num_hits
        self._last_report_num_paths_with_hits = self.num_paths_with_hits
        self._last_report_num_paths_searched = self.num_paths_searched

class _CancelableFindThread(threading.Thread):
    """ A thread for doing find operations in a single text string in the
    background; results are reported to a callback.  Can be cancelled.
    Callbacks will always be executed on the calling thread.
    """

    _com_interfaces_ = components.interfaces.nsICancelable

    def __init__(self, id, text, regex, callback):
        """ Create a find thread.
        @param text {string} The text to search in
        @param regex {regex} The regular expression to search for
        @param callback {callable} The callback to invoke (on the original
            thread) when a result is found; it has a single argument, the match
            object.  The callback will also be invoked when the find completes
            successfully (but not when it has been aborted), with a single
            argument of None.
        """
        threading.Thread.__init__(self, name="Find Thread %s" % id)
        self.text = text
        self.regex = regex
        self.callback = callback
        self.target = components.classes["@mozilla.org/thread-manager;1"] \
                            .getService().currentThread

        self._stopped = False
        self.result = nsError.NS_OK

    def cancel(self, reason):
        self.result = reason
        self._stopped = True

    @property
    def cancelled(self):
        """ Read-only property to check if cancel() has been called """
        return self._stopped

    def run(self):
        DISPATCH_SYNC = components.interfaces.nsIEventTarget.DISPATCH_SYNC
        try:
            if self._stopped:
                return
            for match in findlib2.find_all_matches(self.regex, self.text):
                if self._stopped:
                    return
                self.target.dispatch(lambda: self.callback(match), DISPATCH_SYNC)
                if self._stopped:
                    return
            self.target.dispatch(lambda: self.callback(None), DISPATCH_SYNC)
        finally:
            self.callback = None
            self.target = None

class _ConfirmReplacerInFiles(threading.Thread, TreeView):
    _com_interfaces_ = [components.interfaces.koIConfirmReplacerInFiles]
    _reg_clsid_ = "{b864c489-6de2-48ad-a965-86b2676e5929}"
    _reg_contractid_ = "@activestate.com/koConfirmReplacerInFiles;1"
    _reg_desc_ = "Komodo replacer-in-files thread and tree view"

    # The numbers by which to chunk reporting results.
    REPORT_EVERY_N_PATHS_WITH_HITS = 5
    REPORT_EVERY_N_PATHS_SEARCHED = 100

    def __init__(self, regex, repl, desc, paths, controller, env, loaded_path_accessor, do_smart_replace=False):
        threading.Thread.__init__(self, name="ConfirmReplacerInFiles")
        TreeView.__init__(self)

        self.regex = regex
        self.repl = repl
        self.desc = desc
        self.paths = paths
        self.env = env
        self.do_smart_replace = do_smart_replace

        self.controller = controller
        class ControllerProxy:
            def __init__(self, obj):
                self.obj = obj
            @components.ProxyToMainThread
            def report(self, *args):
                return self.obj.report(*args)
            @components.ProxyToMainThread
            def done(self, *args):
                return self.obj.done(*args)
        self.controllerProxy = ControllerProxy(controller)

        self._stopped = False # when true the processing thread should terminate

        self.journal = None
        self.journal_id = None
        self._filter_skipped_paths = False
        self.events = []
        self.all_events = []
        self.num_hits = 0
        self.num_paths_with_hits = 0
        self.num_paths_skipped = 0
        self.num_paths_searched = 0
        self._lock = threading.RLock()  # a guard for `self.events`

        atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self._warning_atom = atomSvc.getAtom("warning")
        self.loadedFileTextFactory = LoadedFileTextFactory(loaded_path_accessor)

    def stop(self):
        self._stopped = True

    def run(self):
        # Rule: If self._stopped is true then this code MUST NOT use
        #       self.controllerProxy because it may have been destroyed.

        skip_filesizes_larger_than = None
        if gPrefSvc.prefs.getBooleanPref("find-skipLargeFilesEnabled"):
            skip_filesizes_larger_than = gPrefSvc.prefs.getLongPref("find-skipFileSizesLargerThan")
        try:
            if self._stopped:
                return

            for event in findlib2.replace(self.regex, self.repl,
                                          self.paths, summary=self.desc,
                                          skip_filesizes_larger_than=skip_filesizes_larger_than,
                                          do_smart_replace=self.do_smart_replace,
                                          textInfoFactory=self.loadedFileTextFactory,
                                          env=self.env):
                if self._stopped:
                    return
                if isinstance(event, findlib2.StartJournal):
                    self.journal = event.journal
                    self.journal_id = self.journal.id
                    continue
                elif isinstance(event, findlib2.SkipPath):
                    self.num_paths_searched += 1
                    if isinstance(event, findlib2.SkipUnknownLangPath):
                        self._add_skipped_path(event)
                    elif isinstance(event, findlib2.SkipLargeFilePath):
                        self._add_skipped_path(event)
                    elif isinstance(event, findlib2.SkipBinaryPath):
                        #TODO: put these as warning rows in the UI?
                        log.debug("Skip `%s' (binary).", event.path)
                elif not isinstance(event, findlib2.Hit):
                    continue
                else:
                    self.num_paths_searched += 1
                    assert isinstance(event, findlib2.ReplaceHitGroup)
                    self._add_repl_group(event)

                self._report()
            self._report(flush=True)

        finally:
            if not self._stopped:
                self.controllerProxy.done()

    def getPath(self, row_idx):
        return self.events[row_idx].path

    def getSkippedReason(self, row_idx):
        event = self.events[row_idx]
        if isinstance(event, findlib2.SkipLargeFilePath):
            return components.interfaces.koIConfirmReplacerInFiles.SKIPPED_LARGE_FILE
        if isinstance(event, findlib2.SkipBinaryPath):
            return components.interfaces.koIConfirmReplacerInFiles.SKIPPED_BINARY_FILE
        if isinstance(event, findlib2.SkipUnknownLangPath):
            return components.interfaces.koIConfirmReplacerInFiles.SKIPPED_UNKNOWN_LANG
        return 0

    def toggle_mark(self, row_idx):
        with self._lock:
            self.events[row_idx]._marked = not self.events[row_idx]._marked
        if self._tree:
            self._tree.invalidateRow(row_idx)

    def diff_from_indeces(self, indeces):
        rgroups = []
        with self._lock:
            for i in indeces:
                rgroup = self.events[i]
                if isinstance(rgroup, findlib2.ReplaceHitGroup):
                    rgroups.append(rgroup)
        return '\n'.join(rgroup.diff for rgroup in rgroups)

    def marked_diff(self):
        rgroups = []
        with self._lock:
            for rgroup in self.events:
                if isinstance(rgroup, findlib2.ReplaceHitGroup) \
                   and rgroup._marked:
                    rgroups.append(rgroup)
        return '\n'.join(rgroup.diff for rgroup in rgroups)

    @components.ProxyToMainThreadAsync
    def _treeRowCountChanged(self, rowIdx, numRows):
        try:
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(rowIdx, numRows)
            self._tree.invalidate()
            self._tree.endUpdateBatch()
        except AttributeError, ex:
            # Ignore if `self._tree` goes away on us during
            # shutdown of the confirmation dialog.
            pass

    def filterSkippedPaths(self, doFilter):
        self._filter_skipped_paths = doFilter
        with self._lock:
            previous_num_events = len(self.events)
            previous_last_report_num_tree_rows = self._last_report_num_tree_rows

            if doFilter:
                self.events = [event for event in self.all_events if not self._isFilteredEvent(event)]
            else:
                self.events = self.all_events
            num_events_now = len(self.events)
            num_rows_changed = num_events_now - previous_num_events
            self._last_report_num_tree_rows = previous_last_report_num_tree_rows + num_rows_changed

        if num_rows_changed != 0:
            self._treeRowCountChanged(
                    # Starting at row N...
                    previous_num_events,
                    # ...for M rows.
                    num_rows_changed)

    def commit(self, resultsMgr):
        if self.isAlive():
            msg = "cannot commit replacements until done finding them all"
            gLastErrorSvc.setLastError(0, msg)
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, msg)
        if self.journal is None:
            msg = "cannot commit replacements: none were found (no journal)"
            gLastErrorSvc.setLastError(0, msg)
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, msg)
    
        num_hits = 0
        num_paths_with_hits = 0
        loadedFileTextFactory = LoadedFileTextFactory(_get_loaded_path_accessor(),
                                                      need_proxy=False)
        try:
            for event in self.events:
                if not isinstance(event, findlib2.ReplaceHitGroup):
                    resultsMgr.view.AddReplaceResult(
                        "warning", # type
                        event.path, # url
                        0, # startIndex
                        0, # endIndex
                        None, # value
                        None, # replacement
                        event.path,  # fileNames == urls (for now, at least)
                        0, # lineNum
                        0, # columnNum
                        "skipped (%s)" % event.reason) # context
                    continue

                # Skip if this path was unchecked in the confirmation
                # dialog.
                rgroup = event
                if not rgroup._marked:
                    continue

                # Make the actual changes on disk.
                rgroup.commit(loadedFileTextFactory)
                num_paths_with_hits += 1
                num_hits += rgroup.length

                # Post the results to the "Find Results" tab.
                types = []
                urls = []
                startIndeces = []
                endIndeces = []
                values = []
                replacements = []
                lineNums = []
                columnNums = []
                contexts = []
                for rhit in rgroup.rhits:
                    types.append("hit")
                    urls.append(rgroup.path)
                    startIndeces.append(rhit.start_pos)
                    endIndeces.append(rhit.end_pos)
                    match = rhit.find_hit.match
                    values.append(match.group(0))
                    replacements.append(match.expand(self.repl))
                    start_line, start_col = rhit.start_line_and_col_num
                    lineNums.append(start_line+1)
                    columnNums.append(start_col+1)
                    contexts.append('\n'.join(rhit.lines).rstrip())
        
                resultsMgr.view.AddReplaceResults(
                    types,
                    urls,
                    startIndeces,
                    endIndeces,
                    values,
                    replacements,
                    urls,  # fileNames == urls (for now, at least)
                    lineNums,
                    columnNums,
                    contexts)

            resultsMgr.searchFinished(True, num_hits, num_paths_with_hits,
                                      self.num_paths_searched,
                                      self.journal.id)
        
            fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"] \
                .getService(components.interfaces.koIFileStatusService)
            fileStatusSvc.updateStatusForAllFiles(
                components.interfaces.koIFileStatusChecker.REASON_FILE_CHANGED)
        finally:
            self.journal.close()
            # Ensure <Journal> isn't kept in memory until the next
            # Replace in Files.
            del self.journal

    _last_report_num_paths_with_hits = 0
    _last_report_num_paths_searched = 0
    _last_report_num_tree_rows = 0
    def _report(self, flush=False):
        """Report current results to the controller.
        
        For performance we batch up reporting.
        """
        if self._stopped:
            return

        # Determine if we should report.
        if flush:
            pass    # report
        elif (self.num_paths_searched != self._last_report_num_paths_searched
              and self.num_paths_searched % self.REPORT_EVERY_N_PATHS_SEARCHED == 0):
            pass    # report
        elif (self.num_paths_with_hits != self._last_report_num_paths_with_hits
              and self.num_paths_with_hits % self.REPORT_EVERY_N_PATHS_WITH_HITS == 0):
            pass    # report
        else:
            return  # skip reporting

        with self._lock:
            num_tree_rows = len(self.events)
        if num_tree_rows > self._last_report_num_tree_rows:
            self._treeRowCountChanged(
                # Starting at row N...
                self._last_report_num_tree_rows,
                # ...for M rows.
                num_tree_rows - self._last_report_num_tree_rows)
            self._last_report_num_tree_rows = num_tree_rows

        self.controllerProxy.report(self.num_hits,
                                    self.num_paths_with_hits,
                                    self.num_paths_searched,
                                    self.num_paths_skipped)
        self._last_report_num_paths_with_hits = self.num_paths_with_hits
        self._last_report_num_paths_searched = self.num_paths_searched

    def _isFilteredEvent(self, event):
        if self._filter_skipped_paths and isinstance(event, findlib2.SkipPath):
            return True
        return False

    def _add_repl_group(self, rgroup):
        self.num_paths_with_hits += 1
        self.num_hits += rgroup.length
        with self._lock:
            self.all_events.append(rgroup)
            # No need to filter the actual replace hits.
            rgroup._marked = True
            self.events.append(rgroup)

    def _add_skipped_path(self, event):
        self.num_paths_skipped += 1
        with self._lock:
            self.all_events.append(event)
            if not self._isFilteredEvent(event):
                self.events.append(event)

    #---- koITreeView methods
    def get_rowCount(self):
        with self._lock:
            return len(self.events)

    def isEditable(self, row_idx, col):
        if col.id == "repls-marked":
            return True
        else:
            return False
    
    def getCellValue(self, row_idx, col):
        assert col.id == "repls-marked"
        with self._lock:
            rgroup = self.events[row_idx]
            if not isinstance(rgroup, findlib2.ReplaceHitGroup):
                return "false"
            else:
                return (rgroup._marked and "true" or "false")

    def setCellValue(self, row_idx, col, value):
        assert col.id == "repls-marked"
        with self._lock:
            rgroup = self.events[row_idx]
            if not isinstance(rgroup, findlib2.ReplaceHitGroup):
                return
            rgroup._marked = (value == "true" and True or False)
        if self._tree:
            self._tree.invalidateCell(row_idx, col)

    def getCellText(self, row_idx, col):
        if col.id == "repls-marked":
            return ""
        assert col.id == "repls-desc"
        with self._lock:
            event = self.events[row_idx]
            if isinstance(event, findlib2.ReplaceHitGroup):
                return "%s (%d replacements)" % (event.path, event.length)
            else:
                return str(event)

    def getCellProperties(self, row_idx, col, properties=None):
        if col.id != "repls-desc":
            return
        with self._lock:
            event = self.events[row_idx]
        if isinstance(event, findlib2.SkipPath):
            # Mozilla 22+ does not have a properties argument.
            if properties is None:
                return "warning"
            else:
                properties.AppendElement(self._warning_atom)

    def getRowProperties(self, row_idx, properties=None):
        with self._lock:
            event = self.events[row_idx]
        if isinstance(event, findlib2.SkipPath):
            # Mozilla 22+ does not have a properties argument.
            if properties is None:
                return "warning"
            else:
                properties.AppendElement(self._warning_atom)

def _get_loaded_path_accessor():
    global _g_loaded_path_accessor
    if _g_loaded_path_accessor is None:
        _g_loaded_path_accessor = components.classes["@activestate.com/koLoadedPathAccessor;1"].\
            getService(components.interfaces.koILoadedPathAccessor)
    return _g_loaded_path_accessor

class _ReplaceUndoer(threading.Thread, TreeView):
    _com_interfaces_ = [components.interfaces.koIReplaceUndoer]
    _reg_clsid_ = "{19ae78d3-806f-4e75-bc34-4efe75d9966a}"
    _reg_contractid_ = "@activestate.com/koReplacerUndoer;1"
    _reg_desc_ = "Komodo thread and tree view to undo a 'replace all in files'"

    # The numbers by which to chunk reporting results.
    REPORT_EVERY_N_PATHS = 5

    def __init__(self, journal_id, controller):
        threading.Thread.__init__(self, name="ReplaceUndoer")
        #TreeView.__init__(self, debug="undorepl") # for debug logging
        TreeView.__init__(self)

        self.journal_id = journal_id
        self.controller = controller
        class ControllerProxy:
            def __init__(self, obj):
                self.obj = obj
            @components.ProxyToMainThread
            def set_summary(self, *args):
                return self.obj.set_summary(*args)
            @components.ProxyToMainThread
            def report(self, *args):
                return self.obj.report(*args)
            @components.ProxyToMainThread
            def error(self, *args):
                return self.obj.error(*args)
            @components.ProxyToMainThread
            def done(self, *args):
                return self.obj.done(*args)
        self.controllerProxy = ControllerProxy(controller)

        self._stopped = False # when true the processing thread should terminate
        
        self.records = []
        self.num_hits = 0
        self.num_paths = 0

        self._lock = threading.RLock()  # A guard for `self.records`.
        self.loadedFileTextFactory = LoadedFileTextFactory(_get_loaded_path_accessor())

    def stop(self):
        self._stopped = True

    def run(self):
        try:
            if self._stopped:
                return

            #TODO (later): Allow individual file errors, but still continue?
            for event in findlib2.undo_replace(self.journal_id,
                               loadedFileManager=self.loadedFileTextFactory):
                if isinstance(event, findlib2.LoadJournal):
                    self.controllerProxy.set_summary(
                        "Undo %s in %s files." % (event.journal.summary,
                                                  len(event.journal)))
                    continue
                assert isinstance(event, findlib2.JournalReplaceRecord)
                with self._lock:
                    self.records.append(event)
                self.num_paths += 1
                self.num_hits += event.length
                self._report()
                if self._stopped:
                    break

            self._report(flush=True)
        except findlib2.FindError, ex:
            # Note: `break_up_words` is a hack to ensure that the XUL
            # <description> in which this message will appear doesn't
            # screw up wrapping because of a very long token.
            self.controllerProxy.error(textutils.break_up_words(unicode(ex)))
        except:
            # Note: `break_up_words` is a hack to ensure that the XUL
            # <description> in which this message will appear doesn't
            # screw up wrapping because of a very long token.
            self.controllerProxy.error(textutils.break_up_words(
                "unexpected error: %s" % _exc_info_summary()))
        else:
            self.controllerProxy.done()
        finally:
            fileStatusSvc = components.classes["@activestate.com/koFileStatusService;1"] \
                .getService(components.interfaces.koIFileStatusService)
            fileStatusSvc.updateStatusForAllFiles(
                components.interfaces.koIFileStatusChecker.REASON_FILE_CHANGED)

    @components.ProxyToMainThreadAsync
    def _treeRowCountChanged(self, rowIdx, numRows):
        try:
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(rowIdx, numRows)
            self._tree.invalidate()
            self._tree.endUpdateBatch()
        except AttributeError, ex:
            # Ignore if `self._tree` goes away on us during
            # shutdown of the confirmation dialog.
            pass

    _last_report_num_paths = 0
    def _report(self, flush=False):
        """Report current results to the controller.
        
        For performance we batch up reporting.
        """
        if self._stopped:
            return

        if flush or self.num_paths % self.REPORT_EVERY_N_PATHS == 0:
            pass        # report
        else:
            return      # skip reporting

        if self.num_paths > self._last_report_num_paths:
            self._treeRowCountChanged(
                    # Starting at row N...
                    self._last_report_num_paths,
                    # ...for M rows.
                    self.num_paths - self._last_report_num_paths)

        self.controllerProxy.report(self.num_hits, self.num_paths)
        self._last_report_num_paths = self.num_paths


    #---- koITreeView methods
    def get_rowCount(self):
        with self._lock:
            return len(self.records)

    def getCellText(self, row_idx, col):
        assert col.id == "repls-desc"
        with self._lock:
            record = self.records[row_idx]
            return "%s (%d replacements undone)" % (record.path, record.length)


def _getKoReplaceHit(hit):
    return KoFindReplaceHit(hit.start_pos,
                            hit.end_pos,
                            hit.start_line,
                            hit.before,
                            hit.after)


class LoadedFileTextFactory(object):
    def __init__(self, loaded_path_accessor, need_proxy=True):
        """
        @param loaded_path_accessor {koILoadedPathAccessor} - object for getting
           information about dirty loaded paths from Komodo instead of via textinfo.TextInfo()
        """
        viewSvc = components.classes["@activestate.com/koViewService;1"].getService()
        dirtyDocs = [view.koDoc for view in viewSvc.getAllViews("editor")
                     if (view.koDoc
                         and view.koDoc.file
                         and view.koDoc.file.isLocal
                         and view.koDoc.isDirty)]
        dirtyPaths = [koDoc.displayPath for koDoc in dirtyDocs]
        self.dirtyDocInfo = {}
        for koDoc in dirtyDocs:
            if koDoc.displayPath not in self.dirtyDocInfo:
                self.dirtyDocInfo[koDoc.displayPath] = {
                    # If the user edits this document during a search, tough....
                    # Komodo will show how things used to be
                    'text': koDoc.getView().scimoz.text,
                    'encoding': koDoc.encoding.python_encoding_name,
                    'koDoc': koDoc,
                }
        if loaded_path_accessor:
            if need_proxy:
                class LoadedPathProxy:
                    def __init__(self, obj):
                        self.obj = obj
                    @components.ProxyToMainThread
                    def applyChanges(self, *args):
                        self.obj.applyChanges(*args)
                    @components.ProxyToMainThread
                    def bufferHasChanged(self, *args):
                        self.obj.bufferHasChanged(*args)
                    @components.ProxyToMainThread
                    def undoChanges(self, *args):
                        self.obj.undoChanges(*args)
                    @components.ProxyToMainThread
                    def applySetText(self, *args):
                        self.obj.applySetText(*args)
                self.loaded_path_accessor = loaded_path_accessor
                self.loadedPathAccessorProxy = LoadedPathProxy(loaded_path_accessor)
            else:
                self.loaded_path_accessor =\
                    self.loadedPathAccessorProxy = loaded_path_accessor
        else:
            self.loaded_path_accessor = self.loadedPathAccessorProxy = None
        
    def init_from_path(self, path, follow_symlinks=True, env=None):
        if follow_symlinks and islink(path):
            path = realpath(path)
        ti = textinfo.TextInfo.init_from_path(path, follow_symlinks=False, env=env)
        if path in self.dirtyDocInfo:
            docInfo = self.dirtyDocInfo[path]
            ti.is_loaded_path = True
            ti.text = docInfo['text']
            ti.encoding = docInfo['encoding']
        else:
            ti.is_loaded_path = False
        return ti

    def _koDoc_from_path(self, path):
        return self.dirtyDocInfo[path]['koDoc']

    # This method can be called from a background thread, and needs
    # to use the proxy
    def applyChanges(self, path, after_text, changeHits):
        changeHits = [_getKoReplaceHit(hit) for hit in reversed(changeHits)]
        self.loadedPathAccessorProxy.applySetText(self._koDoc_from_path(path),
                                                  after_text, changeHits)

    def bufferHasChanged(self, path, after_md5sum):
        return self.loadedPathAccessorProxy.bufferHasChanged(self._koDoc_from_path(path),
                                                             after_md5sum)

    def undoChanges(self, path):
        self.loadedPathAccessorProxy.undoChanges(self._koDoc_from_path(path))

class koLoadedPathAccessor:
    """
    This is a service used as a PyXPCOM proxy
    """
    _com_interfaces_ = [components.interfaces.koILoadedPathAccessor]
    _reg_clsid_ = "{faa65697-6710-4c5e-a2d2-f1eaf9bd3e19}"
    _reg_contractid_ = "@activestate.com/koLoadedPathAccessor;1"

    def applySetText(self, koDoc, text, changeHits):
        scimoz = koDoc.getView().scimoz
        scimoz.beginUndoAction()
        bailOut = False
        try:
            for hit in changeHits:
                # Convert from character to byte coordinates
                start_pos = scimoz.positionAtChar(0, hit.start_pos)
                end_pos = scimoz.positionAtChar(0, hit.end_pos)
                scimoz.targetStart = start_pos
                scimoz.targetEnd = end_pos
                targetReplacedText = scimoz.getTextRange(scimoz.targetStart,
                                                         scimoz.targetEnd)
                if targetReplacedText != hit.before:
                    #log.debug("Expecting target text of %s, got %s",
                    #          hit.before, targetReplacedText)
                    bailOut = True
                    break
                scimoz.replaceTarget(len(hit.after), hit.after)
        finally:
            scimoz.endUndoAction()
        if not bailOut:
            return
        #log.debug("Internal nuisance: have to replace text wholesale")
                                                         
        scimoz.beginUndoAction()
        try:
            currentPos = scimoz.currentPos
            anchor = scimoz.anchor
            firstVisibleLine = scimoz.firstVisibleLine
            xOffset = scimoz.xOffset
            selectionStart = scimoz.selectionStart
            selectionEnd = scimoz.selectionEnd
            scimoz.text = text
            scimoz.currentPos = currentPos
            scimoz.anchor = anchor
            scimoz.selectionStart = selectionStart
            scimoz.selectionEnd = selectionEnd
            scimoz.firstVisibleLine = firstVisibleLine
            scimoz.xOffset = xOffset
        finally:
            scimoz.endUndoAction()

    def bufferHasChanged(self, koDoc, after_md5sum):
        return md5(koDoc.getView().scimoz.text).hexdigest() != after_md5sum

    def undoChanges(self, koDoc):
        koDoc.getView().scimoz.undo()

class KoFindReplaceHit:
    _com_interfaces_ = [components.interfaces.koIFinderReplaceHit]
    _reg_clsid_ = "{433cf3db-69b8-4627-8f6b-8f65d057fdbb}"
    _reg_contractid_ = "@activestate.com/koFindReplaceHit;1"

    def __init__(self, *args, **kwargs):
        self.initialize(*args, **kwargs)

    def initialize(self, start_pos, end_pos, start_line, before, after):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.start_line = start_line
        self.before = before
        self.after = after
                        
#---- find and replace components

class KoFindResult(object):
    _com_interfaces_ = components.interfaces.koIFindResult
    _reg_desc_ = "Find Result"
    _reg_clsid_ = "{0D889F34-0369-4363-BAAB-7465D14EE421}"
    _reg_contractid_ = "@activestate.com/koFindResult;1"

    def __init__(self, url, start, end, value):
        self.url = url
        self.start = start
        self.end = end
        self.value = value


class KoReplaceResult(object):
    _com_interfaces_ = [components.interfaces.koIReplaceResult]
    _reg_desc_ = "Replace Result"
    _reg_clsid_ = "{53056470-F2F0-4a05-B8FF-36DE117C9741}"
    _reg_contractid_ = "@activestate.com/koReplaceResult;1"

    def __init__(self, url, start, end, value, replacement):
        self.url = url
        self.start = start
        self.end = end
        self.value = value
        self.replacement = replacement


class KoFindOptions:
    _com_interfaces_ = components.interfaces.koIFindOptions
    _reg_desc_ = "Find and Replace Session Options"
    _reg_clsid_ = "{3C4AC462-638E-4fa5-A264-3540FEFA558D}"
    _reg_contractid_ = "@activestate.com/koFindOptions;1"

    def __init__(self):
        self.patternTypePrefName = "find-patternType"
        self.caseSensitivityPrefName = "find-caseSensitivity"
        self.matchWordPrefName = "find-matchWord"
        self.searchBackwardPrefName = "find-searchBackward"
        self.preferredContextTypePrefName = "find-preferredContextType"
        self.displayInFindResults2PrefName = "find-displayInFindResults2"
        self.showReplaceAllResultsPrefName = "find-showReplaceAllResults"
        self.cwdPrefName = "find-cwd"
        self.foldersPrefName = "find-folders"
        self.searchInSubfoldersPrefName = "find-searchInSubfolders"
        self.includeFiletypesPrefName = "find-includeFiletypes"
        self.excludeFiletypesPrefName = "find-excludeFiletypes"
        self.multilinePrefName = "find-multiline"
        self.confirmReplacementsInFilesPrefName = "find-confirmReplacementsInFiles"

        global gPrefSvc
        if gPrefSvc is None:
            gPrefSvc = components.classes["@activestate.com/koPrefService;1"]\
                       .getService(components.interfaces.koIPrefService)
        self.patternType = gPrefSvc.prefs.getLongPref(self.patternTypePrefName)
        self.caseSensitivity = gPrefSvc.prefs.getLongPref(self.caseSensitivityPrefName)
        self.matchWord = gPrefSvc.prefs.getBooleanPref(self.matchWordPrefName)
        self.searchBackward = gPrefSvc.prefs.getBooleanPref(self.searchBackwardPrefName)
        self.preferredContextType = gPrefSvc.prefs.getLongPref(self.preferredContextTypePrefName)
        self.displayInFindResults2 = gPrefSvc.prefs.getBooleanPref(self.displayInFindResults2PrefName)
        self.showReplaceAllResults = gPrefSvc.prefs.getBooleanPref(self.showReplaceAllResultsPrefName)
        self.cwd = gPrefSvc.prefs.getStringPref(self.cwdPrefName)
        self.multiline = gPrefSvc.prefs.getBooleanPref(self.multilinePrefName)
        self.confirmReplacementsInFiles = gPrefSvc.prefs.getBooleanPref(self.confirmReplacementsInFilesPrefName)

        # In case we run into some alternate dimension where
        #   os.pathsep not in ';:'
        self._patternExtensionSep = re.compile('[,;:%s ]+' % os.pathsep)
        try:
            self._folders = []
            foldersPref = gPrefSvc.prefs.getPref(self.foldersPrefName)
            for i in range(foldersPref.length):
                self._folders.append(foldersPref.getStringPref(i))
        except COMException, ex:
            log.exception(ex, "Error retrieving 'File in Files' folders "
                              "preference. Some folders may have been lost.")
        self.encodedFolders = os.pathsep.join(self._folders)
        
        self.searchInSubfolders = gPrefSvc.prefs.getBooleanPref(self.searchInSubfoldersPrefName)

        try:
            self._includeFiletypes = []
            includeFiletypesPref = gPrefSvc.prefs.getPref(self.includeFiletypesPrefName)
            for i in range(includeFiletypesPref.length):
                s = includeFiletypesPref.getStringPref(i)
                if s.strip():
                    self._includeFiletypes.append(s.strip())
        except COMException, ex:
            log.exception(ex, "Error retrieving 'File in Files' include "
                              "filetypes preference. Some filetypes may have "
                              "been lost.")
        self.encodedIncludeFiletypes = os.pathsep.join(self._includeFiletypes)
        try:
            self._excludeFiletypes = []
            excludeFiletypesPref = gPrefSvc.prefs.getPref(self.excludeFiletypesPrefName)
            for i in range(excludeFiletypesPref.length):
                s = excludeFiletypesPref.getStringPref(i)
                if s.strip():
                    self._excludeFiletypes.append(s.strip())
        except COMException, ex:
            log.exception(ex, "Error retrieving 'File in Files' exclude "
                              "filetypes preference. Some filetypes may have "
                              "been lost.")
        self.encodedExcludeFiletypes = os.pathsep.join(self._excludeFiletypes)

    def set_patternType(self, value):
        self.patternType = value
        return gPrefSvc.prefs.setLongPref(self.patternTypePrefName, value)

    def set_caseSensitivity(self, value):
        self.caseSensitivity = value
        return gPrefSvc.prefs.setLongPref(self.caseSensitivityPrefName, value)

    def set_matchWord(self, value):
        self.matchWord = value
        return gPrefSvc.prefs.setBooleanPref(self.matchWordPrefName, value)

    def set_searchBackward(self, value):
        self.searchBackward = value
        return gPrefSvc.prefs.setBooleanPref(self.searchBackwardPrefName, value)

    def set_preferredContextType(self, value):
        self.preferredContextType = value
        return gPrefSvc.prefs.setLongPref(self.preferredContextTypePrefName, value)

    def set_displayInFindResults2(self, value):
        self.displayInFindResults2 = value
        return gPrefSvc.prefs.setBooleanPref(self.displayInFindResults2PrefName, value)

    def set_cwd(self, value):
        self.cwd = value
        return gPrefSvc.prefs.setStringPref(self.cwdPrefName, value)

    def set_showReplaceAllResults(self, value):
        self.showReplaceAllResults = value
        return gPrefSvc.prefs.setBooleanPref(self.showReplaceAllResultsPrefName, value)

    def set_encodedFolders(self, value):
        self.encodedFolders = value
        self._folders = value.split(os.pathsep)
        foldersPref = gPrefSvc.prefs.getPref(self.foldersPrefName)
        foldersPref.reset()
        for folder in self._folders:
            foldersPref.appendStringPref(folder)
        gPrefSvc.prefs.setPref(self.foldersPrefName, foldersPref)

    def getFolders(self):
        return self._folders

    def set_searchInSubfolders(self, value):
        self.searchInSubfolders = value
        return gPrefSvc.prefs.setBooleanPref(self.searchInSubfoldersPrefName, value)

    def _split_extensions(self, value):
        return [s.strip() for s in self._patternExtensionSep.split(value)
                if s.strip()]

    def set_encodedIncludeFiletypes(self, value):
        self.encodedIncludeFiletypes = value
        self._includeFiletypes = self._split_extensions(value)
        includeFiletypesPref = gPrefSvc.prefs.getPref(self.includeFiletypesPrefName)
        includeFiletypesPref.reset()
        for includeFiletype in self._includeFiletypes:
            includeFiletypesPref.appendStringPref(includeFiletype)
        gPrefSvc.prefs.setPref(self.includeFiletypesPrefName,
                               includeFiletypesPref)

    def getIncludeFiletypes(self):
        return self._includeFiletypes

    def set_encodedExcludeFiletypes(self, value):
        self.encodedExcludeFiletypes = value
        self._excludeFiletypes = self._split_extensions(value)
        excludeFiletypesPref = gPrefSvc.prefs.getPref(self.excludeFiletypesPrefName)
        excludeFiletypesPref.reset()
        for excludeFiletype in self._excludeFiletypes:
            excludeFiletypesPref.appendStringPref(excludeFiletype)
        gPrefSvc.prefs.setPref(self.excludeFiletypesPrefName,
                               excludeFiletypesPref)

    def getExcludeFiletypes(self):
        return self._excludeFiletypes

    def set_multiline(self, value):
        self.multiline = value
        return gPrefSvc.prefs.setBooleanPref(self.multilinePrefName, value)

    def set_confirmReplacementsInFiles(self, value):
        self.confirmReplacementsInFiles = value
        return gPrefSvc.prefs.setBooleanPref(self.confirmReplacementsInFilesPrefName, value)

    def searchDescFromPattern(self, pattern):
        opts = []
        if self.matchWord:
            opts.append("match whole word")
        if self.patternType == FOT_REGEX_PYTHON:
            bits = ["/", pattern.replace("/", "\\/"), "/"]
            if (self.caseSensitivity == FOC_INSENSITIVE
                or (self.caseSensitivity == FOC_SMART
                    and pattern.lower() == pattern)):
                bits.append('i')
            bits.append('m')
        else:
            bits = ["'", pattern, "'"]
            if (self.caseSensitivity == FOC_SENSITIVE
                or (self.caseSensitivity == FOC_SMART
                    and pattern.lower() != pattern)):
                opts.append("match case")
        if opts:
            bits += [" ", "(%s)" % ", ".join(opts)]
        return ''.join(bits)

class KoFindService(object):
    _com_interfaces_ = components.interfaces.koIFindService
    _reg_desc_  = "Find and Replace Service"
    _reg_clsid_ = "{3582DE9B-FA36-4787-B3D3-6B9F94EB4AD0}"
    _reg_contractid_ = "@activestate.com/koFindService;1"

    def __init__(self):
        global gPrefSvc, gLastErrorSvc
        if gPrefSvc is None:
            gPrefSvc = components.classes["@activestate.com/koPrefService;1"]\
                       .getService(components.interfaces.koIPrefService)
        gLastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                       .getService(components.interfaces.koILastErrorService)

        self.eol_re = re.compile(r'\r\n|\r|\n')
        self.DECORATOR_FIND_HIGHLIGHT = components.interfaces.koILintResult.DECORATOR_FIND_HIGHLIGHT
        
        # Configure where findlib2 stores "replace in files" journals.

        dirSvc = components.classes["@activestate.com/koDirs;1"]\
                  .getService(components.interfaces.koIDirs)
        journal_dir = join(dirSvc.userCacheDir, "repl-journals")
        findlib2.Journal.set_journal_dir(journal_dir)

        # load the find and replace options
        self.options = KoFindOptions()
        
        self._threadMap = {}

    @LazyProperty
    def env(self):
        return KomodoRuntimeEnv()

    def find(self, url, text, pattern, start, end):
        try:
            regex, dummy, desc = _regex_info_from_ko_find_data(
                pattern, None,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            if self.options.searchBackward:
                gen = findlib2.find_all_matches_bwd(regex, text,
                        start=0, end=start)
            else:
                gen = findlib2.find_all_matches(regex, text,
                        start=start, end=end)

            for match in gen:
                return KoFindResult(url, match.start(), match.end(),
                                    match.group(0))
                break # only want the first one
            else:
                return None
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def replace(self, url, text, pattern, repl, startOffset, scimoz):
        """Return a result indicating how to replace the first occurrence
        of `pattern` in `text` with `repl`.

        Returns a KoReplaceResult or None.

        TODO: handle EOL-normalization of replacement if this is used.
        """
        try:
            regex, munged_repl, desc = _regex_info_from_ko_find_data(
                pattern, repl,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            if self.options.searchBackward:
                gen = findlib2.find_all_matches_bwd(regex, text,
                        start=0, end=startOffset)
            else:
                gen = findlib2.find_all_matches(regex, text,
                        start=startOffset)

            # Prepare for normalizing replacement strings with the
            # target EOL chars.
            if scimoz.eOLMode == ISciMoz.SC_EOL_CRLF:
                eol_to_normalize_to = "\r\n"
            elif scimoz.eOLMode == ISciMoz.SC_EOL_CR:
                eol_to_normalize_to = "\r"
            else:
                eol_to_normalize_to = None
            eol_re = self.eol_re

            for match in gen:
                repl_str = match.expand(munged_repl)
                if eol_to_normalize_to:
                    repl_str = eol_re.sub(eol_to_normalize_to, repl_str)
                repl_str = self._do_smart_conversion(pattern, text[match.start():match.end()], repl_str)
                return KoReplaceResult(url, match.start(), match.end(),
                                       match.group(0), repl_str)
                break # only want the first one
            else:
                return None        
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    # Highlighting performance tweaks:
    # These are settings for remembering the last highlighted text. Since the
    # highlighting will occur even for a FindNext command, which results
    # in the find highlighting searching the whole text, we cache the last
    # highlight results and if it's the same the next time, we don't need to
    # re-find all of the find matches (we already have them).
    # XXX: This type of caching could be moved into a general part of the
    #      find service.
    _lastHighlightMatches = []
    _lastHighlightTextId = None
    _lastHighlightRegexTuple = None
    
    def highlightall(self, scimoz, pattern, start, end, timeout_ms):
        """Highlight the pattern in the scimoz text."""
        try:
            #print "highlightall:: pattern: %r, between: %d-%d" % (pattern, start, end)
            regex, dummy, desc = _regex_info_from_ko_find_data(
                pattern, None,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            # Check to see if the search highlight is the same as the last one.
            textId = scimoz.textId
            regexTuple = (regex, desc)
            if regexTuple == self._lastHighlightRegexTuple and \
                self._lastHighlightMatches and \
                self._lastHighlightTextId == textId:
                # It's the same. Use the last matches again.
                hightlight_matches = self._lastHighlightMatches
                # Perf: Check the first match to see if it's still highlighted,
                #       if it is, we don't need to make any changes.
                startByte, byteLength = hightlight_matches[0]
                if scimoz.indicatorValueAt(self.DECORATOR_FIND_HIGHLIGHT,
                                           startByte):
                    # It's still highlighted from a previous search.
                    return True
            else:
                # It's different. Perform a new find all now.
                hightlight_matches = []
                expired_time = time.time() + (timeout_ms / 1000.0)
                if start == end:
                    # Search the whole text.
                    end = None
                last_endChar = 0
                last_endByte = 0
                text = scimoz.text
                for match in findlib2.find_all_matches(regex, text,
                                                       start=start, end=end):
                    # Remember the match.
                    startChar = match.start()
                    endChar = match.end()
                    startByte = scimoz.positionAtChar(last_endByte, startChar - last_endChar)
                    endByte = scimoz.positionAtChar(startByte, endChar - startChar)
                    byteLength = endByte - startByte
                    hightlight_matches.append((startByte, byteLength))
                    if time.time() > expired_time:
                        # Timed out.
                        break
                    last_endByte = endByte
                    last_endChar = endChar
                self._lastHighlightMatches = hightlight_matches
                self._lastHighlightRegexTuple = regexTuple
                self._lastHighlightTextId = textId

            prevIndicator = scimoz.indicatorCurrent
            prevIndicatorValue = scimoz.indicatorValue
            scimoz.indicatorValue = scimoz.INDIC_BOX
            scimoz.indicatorCurrent = self.DECORATOR_FIND_HIGHLIGHT
            # Clear all existing find indicators.
            scimoz.indicatorClearRange(0, scimoz.length);
            try:
                for highlight in hightlight_matches:
                    scimoz.indicatorFillRange(*highlight)
            finally:
                scimoz.indicatorCurrent = prevIndicator
                scimoz.indicatorValue = prevIndicatorValue
            return len(hightlight_matches) > 0
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
        return False # not reached

    def highlightlastresults(self, scimoz):
        """Highlight the last find/replace patterns in the scimoz text."""
        try:
            scimoz.indicatorValue = scimoz.INDIC_BOX
            scimoz.indicatorCurrent = self.DECORATOR_FIND_HIGHLIGHT
            # Clear all existing find indicators.
            scimoz.indicatorClearRange(0, scimoz.length);
            for highlight in self._lastHighlightMatches:
                scimoz.indicatorFillRange(*highlight)
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def findallex(self, url, text, pattern, resultsView, contextOffset,
                  scimoz):
        """Feed all occurrences of "pattern" in the "text" into the given
        koIFindResultsView.

            "url" is the viewId.
            "resultsView" is a koIFindResultView instance on which
                the replace results should be logged via AddFindResult()
            "contextOffset" is text's offset into the scimoz buffer (in chars).
            "scimoz" is the ISciMoz interface for current view.
        
        No return value.
        """
        try:
            regex, dummy, desc = _regex_info_from_ko_find_data(
                pattern, None,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            try:
                resultsView = UnwrapObject(resultsView)
            except:
                pass # will be slower, but still work
            self._lastHighlightMatches = []
            self._lastHighlightRegexTuple = None
            self._lastHighlightTextId = None
            last_endCharIndex = 0
            last_endByteIndex = 0
            for match in findlib2.find_all_matches(regex, text):
                value = match.group()
                startCharIndex = match.start() + contextOffset
                endCharIndex = startCharIndex + len(value)

                # Convert indices to *byte* offsets (as in scintilla) from
                # *char* offsets (which is what the Python regex engine
                # searching is using).
                startByteIndex = scimoz.positionAtChar(last_endByteIndex, (startCharIndex - last_endCharIndex))
                endByteIndex = scimoz.positionAtChar(startByteIndex, len(value))
                # Save the match location for highlighting purposes.
                self._lastHighlightMatches.append((startByteIndex,
                                                   endByteIndex - startByteIndex))

                startLineNum = scimoz.lineFromPosition(startByteIndex)
                endLineNum = scimoz.lineFromPosition(endByteIndex)
                contextStartPos = scimoz.positionFromLine(startLineNum)
                contextEndPos = scimoz.getLineEndPosition(endLineNum)
                context = scimoz.getTextRange(contextStartPos, contextEndPos)
                #TODO: consider batching this (.AddFindResults()) for
                #      perf for a large number of hits.
                resultsView.AddFindResult(
                    "hit",
                    url, startCharIndex, endCharIndex, value,
                    url, # fileName (currently url/viewId is the displayName)
                    startLineNum + 1, # 1-based line
                    startCharIndex - scimoz.positionFromLine(startLineNum) + 1, # 1-based column.
                    context)
                last_endCharIndex = endCharIndex
                last_endByteIndex = endByteIndex
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def findallasync(self, pattern, text, callback, offset=0, options=None):
        cancelable = None
        try:
            if not options:
                options = self.options
            regex, dummy, desc = _regex_info_from_ko_find_data(
                pattern, None,
                options.patternType,
                options.caseSensitivity,
                options.matchWord)

        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        offset = [offset] # make this a mutable object so the callback can modify it
        def matchcallback(match):
            if cancelable.cancelled:
                return
            if match is None:
                log.debug("no more matches")
                try:
                    callback.onDone(cancelable.result)
                except COMException:
                    pass
                cancelable.cancel(nsError.NS_ERROR_FAILURE)
                return
            hit = KoFindReplaceHit(offset[0] + match.start(),
                                   offset[0] + match.end(),
                                   0, None, None)
            try:
                offset[0] += callback.onHit(hit)
            except COMException, ex:
                log.debug("failed to notify onHit: %r", ex)
                cancelable.cancel(ex.errno)
        cancelable = _CancelableFindThread(desc, text, regex, matchcallback)
        cancelable.start()
        log.debug("findallasync: started thread %r", cancelable)
        return cancelable

    def findalllines(self, url, text, pattern, contextOffset, scimoz):
        """Return all lines on which "pattern" is found.

            "url" is the viewId.
            "contextOffset" is text's offset into the scimoz buffer. This
                is only used if resultsView is specified.
            "scimoz" is the ISciMoz interface for current view. This is only
                used if resultsView is specified.
        
        Returns a list of line numbers (0-based).
        """
        try:
            regex, dummy, desc = _regex_info_from_ko_find_data(
                pattern, None,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            lines = set()
            last_startCharIndex = 0
            last_startByteIndex = 0
            for match in findlib2.find_all_matches(regex, text):
                startCharIndex = match.start() + contextOffset
                startByteIndex = scimoz.positionAtChar(last_startByteIndex, startCharIndex - last_startCharIndex)
                startLineNum = scimoz.lineFromPosition(startByteIndex)
                lines.add(startLineNum)
                last_startCharIndex = startCharIndex
                last_startByteIndex = startByteIndex
            
            return list(sorted(lines))
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def replaceallex(self, url, text, pattern, repl, firstOnLine, session,
                     resultsView, contextOffset, scimoz):
        """Replace all occurrences of "pattern" in the given text.

            "url" is the viewId.
            "session" is the koIFindSession instance.
            "resultsView" is null or a koIFindResultView instance on which
                the replace results should be logged via the Add*() methods.
            "contextOffset" is text's offset into the scimoz buffer. This
                is only used if resultsView is specified.
            "scimoz" is the ISciMoz interface for current view. This is only
                used if resultsView is specified.
        
        Returns:
            1. the replacement text if there was a change, otherwise null
            2. the number of replacements made
        """
        try:
            # Build the appropriate regex and replacement.
            regex, munged_repl, desc = _regex_info_from_ko_find_data(
                pattern, repl,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            # Determine a "skip-zone" in the current text. I.e., the area
            # already covered by the user in this replace session.
            session = UnwrapObject(session)
            secondLastHit = session.GetSecondLastFindResult()
            if not secondLastHit or secondLastHit.url != url:
                skipZone = None
            elif session.wrapped:
                # Skip zone is from 0 to end of second last hit and from
                # fileStartPos to end of file.
                if self.options.searchBackward:
                    skipZone = [
                        (0, session.fileStartPos - contextOffset),
                        (secondLastHit.start - contextOffset, len(text))
                    ]
                else:
                    skipZone = [
                        (0, secondLastHit.end - contextOffset),
                        (session.fileStartPos - contextOffset, len(text))
                    ]
            else:
                # Skip zone is from the fileStartPos to the end of the second
                # last hit. (_Second_ last, because the current hit (the "last")
                # one is still a candidate for replacement.)
                if self.options.searchBackward:
                    skipZone = [(secondLastHit.start - contextOffset,
                                 session.fileStartPos - contextOffset)]
                else:
                    skipZone = [(session.fileStartPos - contextOffset,
                                 secondLastHit.end - contextOffset)]

            # Gather all the hits, because actually making the change.
            if not skipZone:
                includeZone = [(0, len(text))]
                greppers = [
                    findlib2.find_all_matches(regex, text)
                ]
            elif len(skipZone) == 1:
                # e.g., skipZone = [(13, 26)]
                includeZone = [(0, skipZone[0][0]),
                               (skipZone[0][1], len(text))]
                greppers = [
                    findlib2.find_all_matches(regex, text,
                            start=0, end=skipZone[0][0]),
                    findlib2.find_all_matches(regex, text,
                            start=skipZone[0][1]),
                ]
            else:
                # e.g., skipZone = [(0, 25), (300, 543)] # where 543 == len(text)
                assert len(skipZone) == 2
                includeZone = [(skipZone[0][1], skipZone[1][0])]
                greppers = [
                    findlib2.find_all_matches(regex, text,
                            start=skipZone[0][1], end=skipZone[1][0]),
                ]

            # Prepare for normalizing replacement strings with the
            # target EOL chars.
            if scimoz.eOLMode == ISciMoz.SC_EOL_CRLF:
                eol_to_normalize_to = "\r\n"
            elif scimoz.eOLMode == ISciMoz.SC_EOL_CR:
                eol_to_normalize_to = "\r"
            else:
                eol_to_normalize_to = None
            eol_re = self.eol_re

            if resultsView is not None:
                resultsView = UnwrapObject(resultsView)
            self._lastHighlightMatches = []
            self._lastHighlightRegexTuple = None
            self._lastHighlightTextId = None
            # The offset between the original text pos and the replacement pos.
            replacementByteOffset = 0
            new_text_bits = []
            last_hit_line = None
            num_hits = 0
            curr_pos = 0  # current working position in `text'.
            last_startByteIndex = 0
            last_startCharIndex = 0
            for match in chain(*greppers):
                if resultsView is not None or firstOnLine:
                    startCharIndex = match.start() + contextOffset
                    # Convert indices to *byte* offsets (as in scintilla) from
                    # *char* offsets (which is what the Python regex engine
                    # searching is using).
                    startByteIndex = scimoz.positionAtChar(last_startByteIndex, startCharIndex - last_startCharIndex)
                    startLineNum = scimoz.lineFromPosition(startByteIndex)
                    last_startCharIndex = startCharIndex
                    last_startByteIndex = startByteIndex
                if firstOnLine:
                    # If `firstOnLine == True` then we skip this hit if we
                    # already have one on this line.
                    if startLineNum == last_hit_line:
                        continue
                    last_hit_line = startLineNum

                num_hits += 1
                new_text_bits.append(text[curr_pos:match.start()])
                repl_str = match.expand(munged_repl)
                if eol_to_normalize_to:
                    repl_str = eol_re.sub(eol_to_normalize_to, repl_str)
                repl_str = self._do_smart_conversion(pattern, text[match.start():match.end()], repl_str)
                new_text_bits.append(repl_str)
                curr_pos = match.end()
                #print "replacement %d-%d: %r -> %r"\
                #      % (match.start(), match.end(), 
                #         text[match.start():match.end()], repl_str)

                if resultsView is not None:
                    endCharIndex = startCharIndex + len(repl_str)
                    # Convert indices to *byte* offsets (as in scintilla) from
                    # *char* offsets (which is what the Python regex engine
                    # searching is using).
                    # The 'context' is about the text before the
                    # replacement -- this changes the end point.
                    contextEndCharIndex = match.end() + contextOffset
                    contextEndByteIndex = scimoz.positionAtChar(startByteIndex, contextEndCharIndex - startCharIndex)
                    contextEndLineNum = scimoz.lineFromPosition(contextEndByteIndex)
                    contextStartPos = scimoz.positionFromLine(startLineNum)
                    contextEndPos = scimoz.getLineEndPosition(contextEndLineNum)
                    context = scimoz.getTextRange(contextStartPos, contextEndPos)

                    resultsView.AddReplaceResult(
                        "hit",
                        url, startCharIndex, endCharIndex,
                        match.group(), # value
                        repl_str, # replacement string
                        url, # fileName (currently url/viewId is the displayName)
                        startLineNum + 1, # 1-based line
                        startCharIndex - scimoz.positionFromLine(startLineNum) + 1, # 1-based column.
                        context)

                # Save the match location for highlighting purposes.
                # Convert indices to *byte* offsets (as in scintilla) from
                # *char* offsets (which is what the Python regex engine
                # searching is using).
                if resultsView is None and not firstOnLine: # otherwise it's already calculated.
                    startCharIndex = match.start() + contextOffset
                    startByteIndex = scimoz.positionAtChar(last_startByteIndex, startCharIndex - last_startCharIndex)
                    last_startCharIndex = startCharIndex
                    last_startByteIndex = startByteIndex
                # We use utf-8 encoding to determine the byte length because
                # this is the encoding scintilla *always* uses for displaying
                # text.
                replaceByteLength = len(repl_str.encode('utf-8'))
                self._lastHighlightMatches.append((startByteIndex + replacementByteOffset,
                                                   replaceByteLength))
                # Adjust the text offset for this replacement. 
                replacementByteOffset += (replaceByteLength -
                                          len(match.group().encode('utf-8')))

            new_text_bits.append(text[curr_pos:])

            if not num_hits:
                return None, num_hits
            else:
                return ''.join(new_text_bits), num_hits

        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def findallinfiles(self, id, pattern, resultsMgr):
        """Find all hits of 'pattern' in a set of files.

        *What* files to search are either defined on `resultsMgr.context_`
        (if it is a `koICollectionFindContext`) or by `self.options`
        values.
        
        Dev Note: this is a little messy and should eventually change to
        be consistent in the usage of find "options" and "context" to
        carry what information.
        
        This process is done asynchronously -- i.e. a separate thread is
        started to do this.
        
        No return value.
        """
        try:
            regex, dummy, desc = _regex_info_from_ko_find_data(
                pattern, None,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)
        except (re.error, ValueError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        # This is either a "Replace in Files" with path info in
        # `self.options` or a "Replace in Collection" with path info
        # on the koICollectionFindContext instance.
        context = resultsMgr.context_
        if context.type == koIFindContext.FCT_IN_COLLECTION:
            paths = UnwrapObject(context).paths
        else:
            if context.type != koIFindContext.FCT_IN_FILES:
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "Context has invalid type %r" % (context.type,))
            paths = _paths_from_ko_info(self.options, cwd=context.cwd)

        do_smart_replace = self._should_do_smart_conversion(pattern)
        t = _FindReplaceInFilesThread(id, regex, None, desc, paths, resultsMgr,
                                      self.env,
                                      do_smart_replace=do_smart_replace)
        self._threadMap[id] = t
        resultsMgr.searchStarted()
        self._threadMap[id].start()

    def replaceallinfiles(self, id, pattern, repl, resultsMgr):
        """Start a thread that replaces all instances of 'pattern' with
        'repl' in a set of files.

        See `findallinfiles` for a discussion of what files are searched.
        
        @param id {str} is a unique number to distinguish this
            thread from others (for use by `stopfindreplaceinfiles(id)`).
            Typically this is the number of the Find Results tab to which
            results are logged.
        @param pattern {str} the search pattern
        @param repl {str} the replacement string
        @param resultsMgr {components.interfaces.koIFindResultsTabManager}
            The JS-implemented manager for the "Find Results" tab to
            which results are written.
        """
        try:
            regex, munged_repl, desc = _regex_info_from_ko_find_data(
                pattern, repl,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)
        except (re.error, ValueError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        # This is either a "Replace in Files" with path info in
        # `self.options` or a "Replace in Collection" with path info
        # on the koICollectionFindContext instance.
        context = resultsMgr.context_
        if context.type == koIFindContext.FCT_IN_COLLECTION:
            paths = UnwrapObject(context).paths
        else:
            assert context.type == koIFindContext.FCT_IN_FILES
            paths = _paths_from_ko_info(self.options, cwd=context.cwd)

        do_smart_replace = self._should_do_smart_conversion(pattern)
        t = _FindReplaceInFilesThread(id, regex, munged_repl, desc, paths,
                                      resultsMgr, self.env,
                                      loaded_path_accessor=_get_loaded_path_accessor(),
                                      do_smart_replace=do_smart_replace)
        self._threadMap[id] = t
        resultsMgr.searchStarted()
        self._threadMap[id].start()

    def confirmreplaceallinfiles(self, pattern, repl, context, controller):
        """Start and return a replacement thread that determines
        replacements (for confirmation) and updates the given confirmation
        UI manager.

        See `findallinfiles` for a discussion of what files are searched.

        @param pattern {str} the search pattern
        @param repl {str} the replacement string
        @param context {components.interfaces.koIFindContext} the context
            in which to search (defines some info for what paths to
            search).
        @param controller {components.interfaces.koIConfirmReplaceController}
            the "Confirm Replacements" dialog controller.
        @returns {components.interfaces.koIConfirmReplacerInFiles}
            the replacer thread and tree view.
        """
        try:
            regex, munged_repl, desc = _regex_info_from_ko_find_data(
                pattern, repl,
                self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)
        except (re.error, ValueError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        # This is either a "Replace in Files" with path info in
        # `self.options` or a "Replace in Collection" with path info
        # on the koICollectionFindContext instance.
        if context.type == koIFindContext.FCT_IN_COLLECTION:
            paths = UnwrapObject(context).paths
        else:
            assert context.type == koIFindContext.FCT_IN_FILES
            paths = _paths_from_ko_info(self.options, cwd=context.cwd)

        do_smart_replace = self._should_do_smart_conversion(pattern)
        t = _ConfirmReplacerInFiles(regex, munged_repl, desc, paths,
                                    controller, self.env,
                                    _get_loaded_path_accessor(),
                                    do_smart_replace=do_smart_replace)
        return t

    def undoreplaceallinfiles(self, journal_id, controller):
        """Undo the given "Replace All in Files" operation.
        
        @param journal_id {str}  Identifies the journal for the op.
        @param controller {components.interfaces.koIUndoReplaceController}
            The UI controller.
        """
        return _ReplaceUndoer(journal_id, controller)

    def stopfindreplaceinfiles(self, id):
        #XXX Do I need a lock-guard around usage of self._threadMap?
        if id in self._threadMap:
            isAlive = self._threadMap[id].isAlive()
            self._threadMap[id].stop()
            del self._threadMap[id]
            return isAlive
        return False

    def regex_escape_string(self, s):
        return re.escape(s)

    def _should_do_smart_conversion(self, pattern):
        """
        If we're doing a search/replace with a simple lower-case pattern,
        with smart-case on, then we can preserve the upper-case-ness
        and first-capital-letter-ness of the matches
        """
        return (self.options.caseSensitivity == FOC_SMART
                and self.options.patternType == FOT_SIMPLE
                and pattern.lower() == pattern)

    def _do_smart_conversion(self, pattern, foundText, replText):
        """
        If pattern isn't simple, smart-case, return replText as is
        If pattern isn't all lower-case, return replText as is
        If found is all lower-case, return replText as is
        If FOUND is all upper-case, return replText.upper()
        If Found is capitalized and return replText.capitalize()
        """
        if not self._should_do_smart_conversion(pattern):
            return replText
        return findlib2.do_smart_conversion(foundText, replText)


#---- internal support stuff

def _norm_dir_from_dir(dir, cwd=None):
    if dir.startswith("~"):
        dir = expanduser(dir)
    elif not isabs(dir):
        if cwd:
            dir = join(cwd, dir)
        else:
            dir = abspath(dir)
    return normpath(dir)

def _paths_from_ko_info(options, cwd=None):
    """Return a generator of paths to search from the Komodo
    find system data.
    
    @param options {components.interfaces.koIFindOptions}
    @param cwd {string} the current working dir for interpreting
        relative paths, or None if no appropriate cwd.
    """
    dirs = options.getFolders()
    if cwd:
        cwd = normpath(expanduser(cwd))
    if options.searchInSubfolders:
        path_patterns = [_norm_dir_from_dir(d, cwd) for d in dirs]
    else:
        path_patterns = []
        for d in dirs:
            d = _norm_dir_from_dir(d, cwd)
            path_patterns.append(join(d, "*"))
            path_patterns.append(join(d, ".*"))
    return findlib2.paths_from_path_patterns(
                path_patterns,
                recursive=options.searchInSubfolders,
                includes=options.getIncludeFiletypes(),
                excludes=options.getExcludeFiletypes(),
                on_error=None,
                follow_symlinks=True,
                skip_dupe_dirs=True)

#TODO: put in a recipe, use in ifmain-template
def _exc_info_summary():
    """Return a user-friendly string summary of the current exception."""
    import traceback
    exc_info = sys.exc_info()
    if hasattr(exc_info[0], "__name__"):
        exc_class, exc, tb = exc_info
        exc_str = str(exc_info[1])
        sep = ('\n' in exc_str and '\n' or ' ')
        where_str = ""
        tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
        in_str = (tb_func != "<module>"
                  and " in %s" % tb_func
                  or "")
        where_str = "%s(%s#%s%s)" % (sep, tb_path, tb_lineno, in_str)
        return exc_str + where_str
    else:  # string exception
        return exc_info[0]


_high_bit_chr_re = re.compile(r'[^\x00-\x7f]')
_wrapping_newlines_re = re.compile(r'^([\r\n]*)(.*?)([\r\n]*)$', flags=re.DOTALL)
def _regex_info_from_ko_find_data(pattern, repl=None,
                                  patternType=FOT_SIMPLE,
                                  caseSensitivity=FOC_SENSITIVE,
                                  matchWord=False):
    """Build the appropriate regex from the Komodo find/replace system
    data for a find/replace.
    
    Returns (<regex-object>, <massaged-repl>, <desc>). May raise re.error or
    ValueError if there is a problem.
    """
    orig_pattern = pattern
    orig_repl = repl
    desc_flag_bits = []
    
    # Determine the flags.
    flags = re.MULTILINE   # Generally always want line-based searching.
    if caseSensitivity not in (FOC_INSENSITIVE, FOC_SENSITIVE, FOC_SMART):
        log.warn("Unrecognized case-sensitivity %r, setting to insensitive",
                 caseSensitivity)
        caseSensitivity = FOC_INSENSITIVE
    if caseSensitivity == FOC_INSENSITIVE:
        desc_flag_bits.append("ignore case")
        flags |= re.IGNORECASE
    elif caseSensitivity == FOC_SENSITIVE:
        pass
    elif caseSensitivity == FOC_SMART:
        # Smart case-sensitivity is modelled after the options in Emacs
        # where by a search is case-insensitive if the seach string is
        # all lowercase. I.e. if the search string has an case
        # information then the implication is that a case-sensitive
        # search is desired.
        desc_flag_bits.append("smart case")
        if pattern == pattern.lower():
            flags |= re.IGNORECASE
    else:
        raise AssertionError("unrecognized case-sensitivity %r, failed to fallback"
                             % caseSensitivity)
    if (flags & re.IGNORECASE) and _high_bit_chr_re.search(pattern):
        # Fix bug 89863:
        # eg: re.UNICODE will allow AGRAVE to match agrave when ignoring case.
        flags |= re.UNICODE

    # Massage the pattern, if necessary.
    if patternType == FOT_REGEX_PYTHON:
        pass
    else:
        m = _wrapping_newlines_re.match(pattern)
        if not m.group(2):
            # Bug 88293 on newlines
            # splitlines converts leading newline to "", drops trailing newline
            # But we can't use splitlines(keepends=True) because then we'll
            # escape the newlines to "\\\n" (r'\n') -- better to pull them
            # off before calling splitlines, and then tack them off after.
            pass
        else:
            pattern = '\n'.join(re.escape(ln) for ln in m.group(2).splitlines(0))
            if patternType == FOT_WILDCARD:    # DEPRECATED
                pattern = pattern.replace("\\?", "\w").replace("\\*", "\w*")
            elif patternType != FOT_SIMPLE:
                raise ValueError("unrecognized find pattern type: %r"
                                 % patternType)
            pattern = m.group(1) + pattern + m.group(3)

    if '\n' in pattern and '\r' not in pattern:
        pattern = pattern.replace('\n', '(?:\r\n|\n|\r)')
    if matchWord:
        # Bug 33698: "Match whole word" doesn't work as expected Before
        # this the transformation was "\bPATTERN\b" where \b means:
        #   matches a boundary between a word char and a non-word char
        # However what is really wanted (and what VS.NET does) is to match
        # if there is NOT a word character to either immediate side of the
        # pattern.
        desc_flag_bits.append("match word")
        # Bug 96542: Shows that the fix for bug 33698 didn't work correctly,
        # because it wasn't allowing for low-precedence operators in the
        # wrapped pattern (namely '|').  Also, it's simpler to just use '\b'
        # rather than look-not-behind for \w and lookahead for \w
        #
        # Bug 96871: Even simpler: put a \b at the start of the pattern
        # if pattern[0] isn't alphanumeric, and \b at end.  Note that
        # this can easily break with regexes that start with
        # '(?:X' or end with 'X)' where X is alnum
        # Don't worry about wrapping weird pattern P as (?:P) because
        # if they're asking for search-word, it most likely looks a
        # lot like a word.
        patternParts = []
        if re.compile('\\w').match(pattern[0]):
            patternParts.append("\\b")
        patternParts.append("(?:")
        patternParts.append(pattern)
        patternParts.append(")")
        if re.compile('\\w').match(pattern[-1]):
            patternParts.append("\\b")
        pattern = "".join(patternParts)
    if '$' in pattern:
        # Modifies the pattern such that the '$' anchor will match at
        # '\r\n' and '\r'-style EOLs. To do this we replace occurrences
        # '$' with a pattern that properly matches all EOL styles, being
        # careful to skip escaped dollar signs. (Bug 72692.)
        chs = []
        STATE_DEFAULT, STATE_ESCAPE, STATE_CHARCLASS = range(3)
        state = STATE_DEFAULT
        for ch in pattern:
            chs.append(ch)
            if state == STATE_DEFAULT:
                if ch == '\\':
                    state = STATE_ESCAPE
                elif ch == '$':
                    chs[-1] = r"(?=\r\n|(?<!\r)\n|\r(?!\n)|\Z)"
                elif ch == '[':
                    state = STATE_CHARCLASS
            elif state == STATE_ESCAPE:
                state = STATE_DEFAULT
            elif state == STATE_CHARCLASS:
                if ch == ']':
                    state = STATE_DEFAULT
        pattern = ''.join(chs)

    desc_flag_str = (desc_flag_bits
                     and (" (%s)" % ', '.join(desc_flag_bits))
                     or "")
    if repl is None:
        desc = "find '%s'%s" % (
            textutils.one_line_summary_from_text(orig_pattern, 30),
            desc_flag_str)
    else:
        desc = "replace '%s' with '%s'%s" % (
            textutils.one_line_summary_from_text(orig_pattern, 30),
            textutils.one_line_summary_from_text(orig_repl, 30),
            desc_flag_str)
        
        # Massage the replacement string, if appropriate.

        # For replacement strings not using regexes, backslashes must
        # be escaped to prevent the unlucky "\1" or "\g<foo>" being
        # interpreted as a back-reference.
        if patternType != FOT_REGEX_PYTHON:
            repl = repl.replace('\\', '\\\\')
            
        # Check for and return a nicer error message for an unescaped
        # trailing slash than what sre would return:
        #   sre_constants.error: bogus escape (end of line)
        num_trailing_slashes = 0
        for ch in reversed(repl):
            if ch == '\\':
                num_trailing_slashes += 1
            else:
                break
        if num_trailing_slashes % 2:
            raise ValueError("trailing backslash in the replacement "
                             "string must be escaped")


    return re.compile(pattern, flags), repl, desc



