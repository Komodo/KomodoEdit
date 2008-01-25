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

import os
from os.path import join, isabs, expanduser, normpath
import sys
import string, types
import re
import logging
import threading
import pprint
from itertools import chain

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import UnwrapObject
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
import findlib2



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

# services setup in Find Service ctor
gPrefSvc = None
gLastErrorSvc = None


#---- Find/Replace in Files backend

class _ReplacerInFiles(threading.Thread):
    def __init__(self, id, regex, repl, folders, cwd, searchInSubfolders,
                 includeFiletypes, excludeFiletypes, resultsMgr,
                 resultsView):
        threading.Thread.__init__(self, name="ReplacerInFiles")

        self.id = id
        self.regex = regex
        self.repl = repl
        self.folders = folders
        self.cwd = normpath(expanduser(cwd))
        self.searchInSubfolders = searchInSubfolders
        self.includeFiletypes = includeFiletypes
        self.excludeFiletypes = excludeFiletypes
        self.resultsMgr = resultsMgr
        self.resultsView = resultsView

        self.resultsMgrProxy = getProxyForObject(None,
            components.interfaces.koIFindResultsTabManager,
            self.resultsMgr, PROXY_ALWAYS | PROXY_SYNC)
        self.resultsViewProxy = getProxyForObject(None,
            components.interfaces.koIFindResultsView,
            self.resultsView, PROXY_ALWAYS | PROXY_SYNC)
        self._resultsView = UnwrapObject(resultsView)

        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                      .getService(components.interfaces.koILastErrorService)

        self._stop = 0 # when true the processing thread should terminate

    def stop(self):
        """Stop processing."""
        log.debug("stopping replace in files thread")
        self._stop = 1

    def _norm_dir_from_dir(self, dir):
        dir = normpath(dir)
        if dir.startswith("~"):
            return expanduser(dir)
        elif not isabs(dir):
            return join(self.cwd, dir)
        else:
            return dir

    def run(self):
        # Rule: if self._stop is true then this code MUST NOT use
        #       self.resultsMgrProxy or self.resultsViewProxy, because they
        #       may have been destroyed.

        # optimization: delay reporting of results, store them here
        self._resetResultCache()

        self.numResults = 0
        self.numFiles = 0
        self.numSearchedFiles = 0
        self.searched_norm_dirs = set() # used to avoid dupes
        try:
            if self._stop:
                return
            else:
                self.resultsMgrProxy.setDescription(
                    "Phase 1: gathering list of files...", 0)

            paths = findlib2.paths_from_path_patterns(
                        [self._norm_dir_from_dir(d) for d in self.folders],
                        recursive=self.searchInSubfolders,
                        includes=self.includeFiletypes,
                        excludes=self.excludeFiletypes,
                        skip_dupe_dirs=True)
            for event in findlib2.replace(self.regex, self.repl, paths,
                                          include_diff_events=True,
                                          dry_run=True):
                if self._stop:
                    return
                print repr(event)

            self._flushResultCache() # Add the last chunk of find results
        finally:
            if not self._stop:
                self.resultsMgrProxy.searchFinished(1, self.numResults,
                                                    self.numFiles,
                                                    self.numSearchedFiles)
                if self.numSearchedFiles == 0:
                    self.resultsMgrProxy.setDescription(
                        "No files were found to search in.", 1)

    def _resetResultCache(self):
        self._r_urls = []
        self._r_startIndexes = []
        self._r_endIndexes = []
        self._r_values = []
        self._r_replacements = []
        self._r_fileNames = []
        self._r_lineNums = []
        self._r_columnNums = []
        self._r_contexts = []

    def _cacheResult(self, url, startIndex, endIndex, value, fileName,
                     lineNum, columnNum, context):
        self._r_urls.append(url)
        self._r_startIndexes.append(startIndex)
        self._r_endIndexes.append(endIndex)
        self._r_values.append(value)
        self._r_replacements.append(replacement)
        self._r_fileNames.append(fileName)
        self._r_lineNums.append(lineNum)
        self._r_columnNums.append(columnNum)
        self._r_contexts.append(context)

    def _flushResultCache(self):
        if self._r_urls:
            self.resultsViewProxy.AddReplaceResults(
                self._r_urls, self._r_startIndexes, self._r_endIndexes,
                self._r_values, self._r_replacements, self._r_fileNames,
                self._r_lineNums, self._r_columnNums, self._r_contexts)
            self._resetResultCache()

            numSearchedFiles = len(self.searchedFiles)
            if numSearchedFiles == 1:
                filesStr = "1 file"
            else:
                filesStr = str(numSearchedFiles) + " files"
            #TODO: mk appropriate for *replace*
            desc = "Found %d occurrences in %d of %s so far."\
                   % (self.numResults, self.numFiles, filesStr)
            self.resultsMgrProxy.setDescription(desc, 0)


class _FinderInFiles(threading.Thread):
    REPORT_CHUNK_SIZE = 50  # The number by which to chunk reporting results.
    
    def __init__(self, id, regex, folders, cwd, searchInSubfolders,
                 includeFiletypes, excludeFiletypes, resultsMgr,
                 resultsView):
        threading.Thread.__init__(self, name="FinderInFiles")

        self.id = id
        self.regex = regex
        self.folders = folders
        self.cwd = normpath(expanduser(cwd))
        self.searchInSubfolders = searchInSubfolders
        self.includeFiletypes = includeFiletypes
        self.excludeFiletypes = excludeFiletypes
        self.resultsMgr = resultsMgr
        self.resultsView = resultsView

        self.resultsMgrProxy = getProxyForObject(None,
            components.interfaces.koIFindResultsTabManager,
            self.resultsMgr, PROXY_ALWAYS | PROXY_SYNC)
        self.resultsViewProxy = getProxyForObject(None,
            components.interfaces.koIFindResultsView,
            self.resultsView, PROXY_ALWAYS | PROXY_SYNC)
        self._resultsView = UnwrapObject(resultsView)

        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                      .getService(components.interfaces.koILastErrorService)

        self._stop = 0 # when true the processing thread should terminate

    def stop(self):
        """Stop processing."""
        log.debug("stopping find in files thread")
        self._stop = 1

    def _norm_dir_from_dir(self, dir):
        dir = normpath(dir)
        if dir.startswith("~"):
            return expanduser(dir)
        elif not isabs(dir):
            return join(self.cwd, dir)
        else:
            return dir

    def run(self):
        # Rule: if self._stop is true then this code MUST NOT use
        #       self.resultsMgrProxy or self.resultsViewProxy, because they
        #       may have been destroyed.

        self._resetResultCache()

        self.num_hits = 0
        self.num_paths_with_hits = 0
        self.num_paths_searched = 0
        try:
            if self._stop:
                return
            else:
                self.resultsMgrProxy.setDescription(
                    "Phase 1: gathering list of files...", 0)

            paths = findlib2.paths_from_path_patterns(
                        [self._norm_dir_from_dir(d) for d in self.folders],
                        recursive=self.searchInSubfolders,
                        includes=self.includeFiletypes,
                        excludes=self.excludeFiletypes,
                        skip_dupe_dirs=True)
            last_path_with_hits = None
            for event in findlib2.grep(self.regex, paths):
                if self._stop:
                    return

                if isinstance(event, findlib2.SkipPath):
                    self.num_paths_searched += 1
                    continue
                elif not isinstance(event, findlib2.Hit):
                    continue
                self.num_hits += 1
                if event.path != last_path_with_hits:
                    self.num_paths_searched += 1
                    self.num_paths_with_hits += 1
                    last_path_with_hits = event.path
                
                self._report_hit(event)

            self._flushResultCache() # Add the last chunk of find results
        finally:
            if not self._stop:
                self.resultsMgrProxy.searchFinished(
                    1, self.num_hits, self.num_paths_with_hits,
                    self.num_paths_searched)
                if self.num_paths_searched == 0:
                    self.resultsMgrProxy.setDescription(
                        "No files were found to search in.", 1)

    def _report_hit(self, hit):
        """Report/cache this findlib2 Hit."""
        context = '\n'.join(hit.lines)

        # Don't want to see black boxes for EOLs in find results tab.
        context = context.rstrip('\r\n')

        # Firefox trees don't like displaying *very* long lines
        # which the occassional exceptional situation will cause
        # (e.g.  Komodo's own webdata.js). Trim the "content"
        # find result length.
        MAX_CONTENT_LENGTH = 256
        if len(context) > MAX_CONTENT_LENGTH:
            context = context[:MAX_CONTENT_LENGTH]

        # When the context gets passed to AddFindResults pyxpcom will
        # convert it into a unicode string automatically. However, if we
        # happened to get a result on a binary file, that will fail and we
        # will not see any results. protect against that by trying to make
        # the string unicode, and failing that, repr it, then limit its
        # length as it could be *very* long.
        if type(context) != types.UnicodeType:
            try:
                context = unicode(context)
            except UnicodeError, ex:
                context = context[:MAX_CONTENT_LENGTH]
                context = repr(context)[1:-1]

        line_num, col_num = hit.start_line_and_col_num
        self._cacheResult(hit.path, hit.start_pos, hit.end_pos,
                          hit.match.group(0), hit.path,
                          line_num+1, col_num+1, context)

    def _resetResultCache(self):
        self._r_urls = []
        self._r_startIndexes = []
        self._r_endIndexes = []
        self._r_values = []
        self._r_fileNames = []
        self._r_lineNums = []
        self._r_columnNums = []
        self._r_contexts = []

    def _cacheResult(self, url, startIndex, endIndex, value, fileName,
                     lineNum, columnNum, context):
        self._r_urls.append(url)
        self._r_startIndexes.append(startIndex)
        self._r_endIndexes.append(endIndex)
        self._r_values.append(value)
        self._r_fileNames.append(fileName)
        self._r_lineNums.append(lineNum)
        self._r_columnNums.append(columnNum)
        self._r_contexts.append(context)
        
        if len(self._r_urls) >= self.REPORT_CHUNK_SIZE:
            self._flushResultCache()

    def _flushResultCache(self):
        if self._r_urls:
            #TODO: what's the diff btwn url and fileName?
            self.resultsViewProxy.AddFindResults(
                self._r_urls, self._r_startIndexes, self._r_endIndexes,
                self._r_values, self._r_fileNames,
                self._r_lineNums, self._r_columnNums, self._r_contexts)
            self._resetResultCache()

            if self.num_paths_searched == 1:
                filesStr = "1 file"
            else:
                filesStr = str(self.num_paths_searched) + " text files"
            desc = "Found %d occurrences in %d of %s so far."\
                   % (self.num_hits, self.num_paths_with_hits, filesStr)
            self.resultsMgrProxy.setDescription(desc, 0)





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

        self.patternType = gPrefSvc.prefs.getLongPref(self.patternTypePrefName)
        self.caseSensitivity = gPrefSvc.prefs.getLongPref(self.caseSensitivityPrefName)
        self.matchWord = gPrefSvc.prefs.getBooleanPref(self.matchWordPrefName)
        self.searchBackward = gPrefSvc.prefs.getBooleanPref(self.searchBackwardPrefName)
        self.preferredContextType = gPrefSvc.prefs.getLongPref(self.preferredContextTypePrefName)
        self.displayInFindResults2 = gPrefSvc.prefs.getBooleanPref(self.displayInFindResults2PrefName)
        self.showReplaceAllResults = gPrefSvc.prefs.getBooleanPref(self.showReplaceAllResultsPrefName)
        self.cwd = gPrefSvc.prefs.getStringPref(self.cwdPrefName)

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


class KoFindService:
    _com_interfaces_ = components.interfaces.koIFindService
    _reg_desc_  = "Find and Replace Service"
    _reg_clsid_ = "{3582DE9B-FA36-4787-B3D3-6B9F94EB4AD0}"
    _reg_contractid_ = "@activestate.com/koFindService;1"

    def __init__(self):
        global gPrefSvc, gLastErrorSvc
        gPrefSvc = components.classes["@activestate.com/koPrefService;1"]\
                  .getService(components.interfaces.koIPrefService)
        gLastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                       .getService(components.interfaces.koILastErrorService)

        # load the find and replace options
        self.options = KoFindOptions()
        
        self._threadMap = {}
       
    def find(self, url, text, pattern, start, end):
        try:
            regex, dummy = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
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

    def replace(self, url, text, pattern, repl, startOffset):
        """Return a result indicating how to replace the first occurrence
        of `pattern` in `text` with `repl`.

        Returns a KoReplaceResult or None.
        """
        try:
            regex, munged_repl = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord, repl)

            if self.options.searchBackward:
                gen = findlib2.find_all_matches_bwd(regex, text,
                        start=0, end=startOffset)
            else:
                gen = findlib2.find_all_matches(regex, text,
                        start=startOffset)

            for match in gen:
                return KoReplaceResult(url, match.start(), match.end(),
                                       match.group(0),
                                       match.expand(munged_repl))
                break # only want the first one
            else:
                return None        
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def findallex(self, url, text, pattern, resultsView, contextOffset,
                  scimoz):
        """Feed all occurrences of "pattern" in the "text" into the given
        koIFindResultsView.

            "url" is the viewId.
            "resultsView" is null or a koIFindResultView instance on which
                the replace results should be logged via the Add*() methods.
            "contextOffset" is text's offset into the scimoz buffer. This
                is only used if resultsView is specified.
            "scimoz" is the ISciMoz interface for current view. This is only
                used if resultsView is specified.
        
        No return value.
        """
        try:
            regex, dummy = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            resultsView = UnwrapObject(resultsView)
            for match in findlib2.find_all_matches(regex, text):
                value = match.group()
                startCharIndex = match.start() + contextOffset
                endCharIndex = startCharIndex + len(value)

                # Convert indices to *byte* offsets (as in scintilla) from
                # *char* offsets (which is what the Python regex engine
                # searching is using).
                startByteIndex = scimoz.positionAtChar(0, startCharIndex)
                endByteIndex = scimoz.positionAtChar(0, endCharIndex)

                startLineNum = scimoz.lineFromPosition(startByteIndex)
                endLineNum = scimoz.lineFromPosition(endByteIndex)
                contextStartPos = scimoz.positionFromLine(startLineNum)
                contextEndPos = scimoz.getLineEndPosition(endLineNum)
                context = scimoz.getTextRange(contextStartPos, contextEndPos)
                #TODO: consider batching this (.AddFindResults()) for
                #      perf for a large number of hits.
                resultsView.AddFindResult(
                    url, startByteIndex, endByteIndex, value,
                    url, # fileName (currently url/viewId is the displayName)
                    startLineNum + 1,
                    startByteIndex - scimoz.positionFromLine(startLineNum),
                    context)            
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

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
            regex, dummy = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)

            lines = set()
            for match in findlib2.find_all_matches(regex, text):
                startCharIndex = match.start() + contextOffset
                startByteIndex = scimoz.positionAtChar(0, startCharIndex)
                startLineNum = scimoz.lineFromPosition(startByteIndex)
                lines.add(startLineNum)
            
            return list(sorted(lines))
        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def replaceallex(self, url, text, pattern, repl, session,
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
            regex, munged_repl = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord, repl)

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

            if resultsView is not None:
                resultsView = UnwrapObject(resultsView)
            new_text_bits = []
            num_hits = 0
            curr_pos = 0  # current working position in `text'.
            for match in chain(*greppers):
                num_hits += 1
                new_text_bits.append(text[curr_pos:match.start()])
                repl_str = match.expand(munged_repl)
                new_text_bits.append(repl_str)
                curr_pos = match.end()

                if resultsView is not None:
                    startCharIndex = match.start() + contextOffset
                    endCharIndex = startCharIndex + len(repl_str)
    
                    # Convert indices to *byte* offsets (as in scintilla) from
                    # *char* offsets (which is what the Python regex engine
                    # searching is using).
                    startByteIndex = scimoz.positionAtChar(0, startCharIndex)
                    endByteIndex = scimoz.positionAtChar(0, endCharIndex)
    
                    startLineNum = scimoz.lineFromPosition(startCharIndex)
                    endLineNum = scimoz.lineFromPosition(endCharIndex)
                    contextStartPos = scimoz.positionFromLine(startLineNum)
                    contextEndPos = scimoz.getLineEndPosition(endLineNum)
                    context = scimoz.getTextRange(contextStartPos, contextEndPos)
                    resultsView.AddReplaceResult(
                        url, startByteIndex, endByteIndex,
                        match.group(), # value
                        repl_str, # replacement string
                        url, # fileName (currently url/viewId is the displayName)
                        startLineNum + 1, # 0-based -> 1-based
                        startByteIndex - scimoz.positionFromLine(startLineNum),
                        context)
            new_text_bits.append(text[curr_pos:])

            return ''.join(new_text_bits), num_hits

        except (re.error, ValueError, findlib2.FindError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

    def findallinfiles(self, id, pattern, resultsMgr, resultsView):
        """Feed all occurrences of "pattern" in the files identified by
        the options attribute into the given koIFindResultsView.

            "id" is a unique number to distinguish this findallinfiles
                session from others.
            "resultsMgr" is a koIFindResultsTabManager instance.
            "resultsView" is a koIFindResultView instance on which
                the find results should be logged via the Add*() methods.
        
        This process is done asynchronously -- i.e. a separate thread is
        started to do this.
        
        No return value.
        """
        try:
            regex, dummy = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord)
        except (re.error, ValueError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        t = _FinderInFiles(
                id, regex,
                self.options.getFolders(),
                resultsMgr.context_.cwd,
                self.options.searchInSubfolders,
                self.options.getIncludeFiletypes(),
                self.options.getExcludeFiletypes(),
                resultsMgr,
                resultsView)
        self._threadMap[id] = t
        resultsMgr.searchStarted()
        self._threadMap[id].start()

    def replaceallinfiles(self, id, pattern, repl, resultsMgr,
                          resultsView):
        """TODO: docstring"""
        try:
            regex, munged_repl = _regex_info_from_ko_find_data(
                pattern, self.options.patternType,
                self.options.caseSensitivity,
                self.options.matchWord,
                repl)
        except (re.error, ValueError), ex:
            gLastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        t = _ReplacerInFiles(
                id, regex, munged_repl,
                self.options.getFolders(),
                resultsMgr.context_.cwd,
                self.options.searchInSubfolders,
                self.options.getIncludeFiletypes(),
                self.options.getExcludeFiletypes(),
                resultsMgr,
                resultsView)
        self._threadMap[id] = t
        resultsMgr.searchStarted()
        self._threadMap[id].start()

    def stopfindreplaceinfiles(self, id):
        #XXX Do I need a lock-guard around usage of self._threadMap?
        if id in self._threadMap:
            self._threadMap[id].stop()
            del self._threadMap[id]

    def regex_escape_string(self, s):
        return re.escape(s)



#---- internal support stuff

def _regex_info_from_ko_find_data(pattern, patternType=FOT_SIMPLE,
                                  caseSensitivity=FOC_SENSITIVE,
                                  matchWord=False, repl=None):
    """Build the appropriate regex from the Komodo find/replace system
    data for a find/replace.
    
    Returns (<regex-object>, <massaged-repl>). May raise re.error or
    ValueError if there is a problem.
    """
    # Determine the flags.
    #TODO: should we turn on re.UNICODE all the time?
    flags = re.MULTILINE   # Generally always want line-based searching.
    if caseSensitivity == FOC_INSENSITIVE:
        flags |= re.IGNORECASE
    elif caseSensitivity == FOC_SENSITIVE:
        pass
    elif caseSensitivity == FOC_SMART:
        # Smart case-sensitivity is modelled after the options in Emacs
        # where by a search is case-insensitive if the seach string is
        # all lowercase. I.e. if the search string has an case
        # information then the implication is that a case-sensitive
        # search is desired.
        if pattern == pattern.lower():
            flags |= re.IGNORECASE
    else:
        raise ValueError("unrecognized case-sensitivity: %r"
                         % caseSensitivity)

    # Massage the pattern, if necessary.
    if patternType == FOT_SIMPLE:
        pattern = re.escape(pattern)
    elif patternType == FOT_WILDCARD:    # DEPRECATED
        pattern = re.escape(pattern)
        pattern = pattern.replace("\\?", "\w")
        pattern = pattern.replace("\\*", "\w*")
    elif patternType == FOT_REGEX_PYTHON:
        pass
    else:
        raise ValueError("unrecognized find pattern type: %r"
                         % patternType)
    if matchWord:
        # Bug 33698: "Match whole word" doesn't work as expected Before
        # this the transformation was "\bPATTERN\b" where \b means:
        #   matches a boundary between a word char and a non-word char
        # However what is really wanted (and what VS.NET does) is to match
        # if there is NOT a word character to either immediate side of the
        # pattern.
        pattern = r"(?<!\w)" + pattern + r"(?!\w)"
    if '$' in pattern:
        # Modifies the pattern such that the '$' anchor will match at
        # '\r\n' and '\r'-style EOLs. To do this we replace occurrences
        # '$' with '(?=\r\n|\n|\r|\Z)', being careful to skip escaped
        # dollar signs.
        chs = []
        STATE_DEFAULT, STATE_ESCAPE, STATE_CHARCLASS = range(3)
        state = STATE_DEFAULT
        for ch in pattern:
            chs.append(ch)
            if state == STATE_DEFAULT:
                if ch == '\\':
                    state = STATE_ESCAPE
                elif ch == '$':
                    chs[-1] = r"(?=\r\n|\n|\r|\Z)"
                elif ch == '[':
                    state = STATE_CHARCLASS
            elif state == STATE_ESCAPE:
                state = STATE_DEFAULT
            elif state == STATE_CHARCLASS:
                if ch == ']':
                    state == STATE_DEFAULT
        pattern = ''.join(chs)

    # Massage the replacement string, if appropriate.
    if repl is not None:
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

    return re.compile(pattern, flags), repl



