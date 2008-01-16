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

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import UnwrapObject
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
import findlib



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
lastErrorSvc = None


#---- Find/Replace in Files backend

class _FinderInFiles(threading.Thread):
    """Find all hits of the given pattern in the given files and
    load them into the given koIFindResultsView.
    
    The running thread can be terminated early by calling the .stop() method.

    XXX:TODO:
    - Need proper lock-synchronization around usages of self._stop, for
      example.
    """
    def __init__(self, id, pattern, patternType, caseSensitivity, matchWord,
                 folders, cwd, searchInSubfolders, includeFiletypes,
                 excludeFiletypes, resultsMgr, resultsView):
        threading.Thread.__init__(self, name="FinderInFiles")

        self.id = id
        self.pattern = pattern
        self.patternType = patternType
        self.caseSensitivity = caseSensitivity
        self.matchWord = matchWord
        self.folders = folders
        self.cwd = cwd
        self.searchInSubfolders = searchInSubfolders
        self.includeFiletypes = includeFiletypes
        self.excludeFiletypes = excludeFiletypes
        self.resultsMgr = resultsMgr
        self.resultsMgrProxy = getProxyForObject(None,
            components.interfaces.koIFindResultsTabManager,
            self.resultsMgr, PROXY_ALWAYS | PROXY_SYNC)
        self.resultsView = resultsView
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

    def run(self):
        # Rule: if self._stop is true then this code MUST NOT use
        #       self.resultsMgrProxy or self.resultsViewProxy, because they
        #       may have been destroyed.
        log.debug("start find in files thread")

        # optimization: delay reporting of results, store them here
        self._resetResultCache()

        self.numResults = 0
        self.numFiles = 0
        self.searchedFiles = {} # list of files searched, to avoid dupes
        try:
            if self._stop:
                return
            else:
                self.resultsMgrProxy.setDescription(
                    "Phase 1: gathering list of files...", 0)

            for folder in self.folders:
                if self._stop:
                    return
                folder = expanduser(folder)
                if not isabs(folder) and self.cwd is not None:
                    folder = join(self.cwd, folder)
                #XXX *Could* still be relative here, if cwd is None?
                self._searchFolder(folder)
                
            self._flushResultCache() # Add the last chunk of find results
        finally:
            if not self._stop:
                self.resultsMgrProxy.searchFinished(1, self.numResults,
                                                    self.numFiles,
                                                    len(self.searchedFiles))
                if not self.searchedFiles:
                    self.resultsMgrProxy.setDescription(
                        "No files were found to search in.", 1)

        log.debug("done find in files thread")

    def _searchFolder(self, folder):
        """Search the given folder and report results.

            "folder" is the directory to search.
        
        Search results are reported to self.resultsMgrProxy,
        self.resultsViewProxy and self.numResults.
        """
        folder = normpath(folder)
        path_patterns = [folder]
        if not self.searchInSubfolders:
            path_patterns = [join(folder, "*"), join(folder, ".*")]

        for path in _paths_from_path_patterns(
                        path_patterns,
                        includes=self.includeFiletypes,
                        excludes=self.excludeFiletypes,
                        recursive=self.searchInSubfolders):
            if self._stop:
                return
            if path in self.searchedFiles:
                continue
            self.searchedFiles[path] = True
            try:
                self._searchFile(path)
            except COMException, ex:
                errcode, errmsg = self.lastErrorSvc.getLastError()
                log.warn("skipping '%s': %s: %s", path, errcode, errmsg)
            except EnvironmentError, ex:
                log.warn("skipping '%s': %s", path, ex)

            if len(self.searchedFiles) % 50 == 0:
                self._flushResultCache()

    def _searchFile(self, file):
        """Search the given file and report results.
        
            "file" is the filename to search.
            
        Search results are reported to self.resultsMgrProxy,
        self.resultsViewProxy and self.numResults.
        """
        #log.debug("search '%s'", file)
        
        # Read the file.
        #XXX Might want to do unicode-y, Komodo preference-y stuff here at
        #    some point.
        fin = open(file, 'rb')
        content = fin.read()
        fin.close()

        # Find any matches.
        matches = findlib.findallex(content, self.pattern,
                                    patternType=self.patternType,
                                    case=self.caseSensitivity,
                                    matchWord=self.matchWord)

        # Report results.
        if matches:
            # Determine line offsets for finding the line and column number
            # of each match.
            lines = [] # One for each line: (start offset, line content)
            offset = 0
            for line in content.splitlines(1):
                lines.append( (offset, line) )
                offset += len(line)

            lower = 0 # initialize out here because matches are sequential
            for match in matches:
                start = match.start()
                end = match.end()
                value = content[start:end]
                #print "\tmatch: %d-%d: %r" % (start, end, value)
                # Determine the line and line offset of this match.
                # - Algorithm adapted from scintilla's LineFromPosition.
                if not lines:
                    lineNum = 0  # lineNum is 0-based
                    lineOffset, line = 0, ""
                elif start >= lines[-1][0]:
                    lineNum = len(lines)
                    lineOffset, line = lines[-1]
                else:
                    upper = len(lines)
                    while lower < upper:
                        middle = (upper + lower + 1) / 2
                        if start < lines[middle][0]:
                            upper = middle - 1
                        else:
                            lower = middle
                    lineNum = lower
                    lineOffset, line = lines[lower]
                columnNum = start - lineOffset

                file = normpath(file)

                # Optimization: cache find results to only call through
                # XPCOM to log them every 25 or so (see AddFindResults()).
                #self.resultsViewProxy.AddFindResult(
                #    file, start, end, value, file,
                #    lineNum+1, columnNum+1,
                #    line)

                # Firefox trees don't like displaying *very* long lines
                # which the occassional exceptional situation will cause
                # (e.g.  Komodo's own webdata.js). Trim the "content"
                # find result length.
                MAX_CONTENT_LENGTH = 256
                if len(line) > MAX_CONTENT_LENGTH:
                    line = line[:MAX_CONTENT_LENGTH]
                
                # When line gets passed to AddFindResults pyxpcom will convert it into
                # a unicode string automagicaly.  However, if we happened to get a
                # result on a binary file, that will fail and we will not see any results.
                # protect against that by trying to make the string unicode, and failing
                # that, repr it, then limit it to 100 bytes as it could be *very* long.
                if type(line) != types.UnicodeType:
                    try:
                        line = unicode(line)
                    except UnicodeError, e:
                        line = line[:MAX_CONTENT_LENGTH]
                        line = repr(line)[1:-1]
                
                self._cacheResult(file, start, end, value, file,
                                  lineNum+1, columnNum+1, line.rstrip())

                self.numResults += 1
            self.numFiles += 1

            if self.numResults % 25 == 0:
                self._flushResultCache()

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

    def _flushResultCache(self):
        if self._r_urls:
            self.resultsViewProxy.AddFindResults(
                self._r_urls, self._r_startIndexes, self._r_endIndexes,
                self._r_values, self._r_fileNames,
                self._r_lineNums, self._r_columnNums, self._r_contexts)
            self._resetResultCache()

            numSearchedFiles = len(self.searchedFiles)
            if numSearchedFiles == 1:
                filesStr = "1 file"
            else:
                filesStr = str(numSearchedFiles) + " files"
            desc = "Found %d occurrences in %d of %s so far."\
                   % (self.numResults, self.numFiles, filesStr)
            self.resultsMgrProxy.setDescription(desc, 0)

    #def _readFile(self, file):
    #    """Return a Unicode object of the file's content.
    #    
    #        "file" is the name of the file to open and read.
    #        XXX For local PythoAdd some preferences...
    #        
    #    It would be nice to have a Python-only implementation of this,
    #    but for now we will use Komodo-specific code. For a Python-only
    #    impl we would need to provide a mechanism for providing some
    #    preferences/directives for detection handling similar to Komodo's.
    #    
    #    Returns a 3-tuple: (ucontent, encoding, bom)
    #    where,
    #        "ucontent" is a unicode buffer of the file's content
    #        "encoding" is a Python encoding name
    #        "bom" is a boolean indicating if the document uses a byte-order
    #            marker
    #    May raise an EnvironmentError if the file cannot be accessed. May
    #    also raise an XPCOM ServerException, in which case the last error
    #    will be set on koILastErrorService.
    #    """
    #    import uriparse
    #    uri = uriparse.localPathToURI(file)
    #    print "XXX %s:" % file
    #    print "\turi: %s" % uri
    #
    #    #docStateMRU = self._globalPrefSvc.getPrefs("docStateMRU");
    #    #if not self.isUntitled and docStateMRU.hasPref(self.file.URI):
    #    #    url = self.file.URI
    #    #    docState = docStateMRU.getPref(url)
    #    #    self.prefs = docState
    #    #else:
    #    #    self.prefs = components.classes['@activestate.com/koPreferenceSet;1'].\
    #    #                             createInstance(components.interfaces.koIPreferenceSet)
    #    #    if self.isUntitled:
    #    #        self.prefs.id = self._untitledName
    #    #    else:
    #    #        self.prefs.id = self.file.URI
    #    #    docStateMRU.setPref(self.prefs)
    #    #self.prefs.parent = self._globalPrefs
    #
    #    encoding_name = self._getStringPref('encodingDefault')
    #    defaultEncoding = self.encodingServices.get_encoding_info(encoding_name)\
    #                   .python_encoding_name
    #    tryEncoding = self._getStringPref('encoding')
    #    tryXMLDecl = self._getBooleanPref('encodingXMLDec')
    #    tryHTMLMeta = self._getBooleanPref('encodingHTML')
    #    tryModeline = self._getBooleanPref('encodingModeline')
    #    #autodetect = self._getBooleanPref('encodingAutoDetect')
    #
    #    import koUnicodeEncoding
    #    ucontent, encoding, bom = koUnicodeEncoding.autoDetectEncoding(
    #        content, tryXMLDecl, tryHTMLMeta, tryModeline, wantThisEncoding,
    #        defaultEncoding)
    #    bom = len(bom) > 0
    #
    #    
    #    doc = self.docSvcProxy.createDocumentFromURI(uri)
    #    enc_info = doc.myDetectEncoding()
    #    print "\t%r, %r, %r"\
    #          % (enc_info[0][:10]+'...'+enc_info[0][-10:],
    #             enc_info[1], enc_info[2])
    #    return enc_info




#---- find and replace components

class KoFindResult:
    _com_interfaces_ = components.interfaces.koIFindResult
    _reg_desc_ = "Find Result"
    _reg_clsid_ = "{0D889F34-0369-4363-BAAB-7465D14EE421}"
    _reg_contractid_ = "@activestate.com/koFindResult;1"

    def __init__(self, url, start, end, value):
        self.url = url
        self.start = start
        self.end = end
        self.value = value


class KoReplaceResult:
    _com_interfaces_ = [components.interfaces.koIFindResult,
                        components.interfaces.koIReplaceResult]
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
        global gPrefSvc, lastErrorSvc
        gPrefSvc = components.classes["@activestate.com/koPrefService;1"]\
                  .getService(components.interfaces.koIPrefService)
        lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                       .getService(components.interfaces.koILastErrorService)

        # Define mappings from koIFinder.idl option enums to findlib option
        # values.
        self.patternTypeMap = {    # koIFinder.patternType -> findlib.patternType
            FOT_SIMPLE:      "simple",
            FOT_WILDCARD:    "wildcard",
            FOT_REGEX_PYTHON:"regex-python",
        }
        self.caseMap = {   # koIFinder.caseSensitivity -> findlib.case
            FOC_INSENSITIVE: "insensitive",
            FOC_SENSITIVE:   "sensitive",
            FOC_SMART:       "smart",
        }

        # load the find and replace options
        self.options = KoFindOptions()
        
        self._threadMap = {}
       
    def find(self, url, text, pattern, startOffset):
        """Return the result of searching for the first "pattern" in "text".
        Return value is a KoFindResult or None.
        """
        patternType = self.patternTypeMap[self.options.patternType]
        case = self.caseMap[self.options.caseSensitivity]
        try:
            result = findlib.find(text, pattern, startOffset=startOffset,
                                  patternType=patternType, case=case,
                                  searchBackward=self.options.searchBackward,
                                  matchWord=self.options.matchWord);
        except (re.error, findlib.FindError), ex:
            global lastErrorSvc
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        if result:
            retval = KoFindResult(url=url, start=result.start, end=result.end,
                                  value=result.value)
        else:
            retval = None
        return retval

    def replace(self, url, text, pattern, replacement, startOffset):
        """Return a result indicating how to replace the first "pattern" in
        "text" with "replacement".

        Return value is a KoReplaceResult or None.
        """
        patternType = self.patternTypeMap[self.options.patternType]
        case = self.caseMap[self.options.caseSensitivity]
        try:
            result = findlib.replace(text, pattern, replacement,
                                     startOffset=startOffset,
                                     patternType=patternType, case=case,
                                     searchBackward=self.options.searchBackward,
                                     matchWord=self.options.matchWord);
        except (re.error, findlib.FindError), ex:
            global lastErrorSvc
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        if result:
            retval = KoReplaceResult(url=url,
                                     start=result.start, end=result.end,
                                     value=result.value,
                                     replacement=result.replacement)
        else:
            retval = None
        return retval

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
        log.info("findallex(url='%s', text=%r, pattern='%s', resultsView,"
                 "contextOffset=%s, scimoz)", url, text[:20]+text[-20:],
                 pattern, contextOffset)

        patternType = self.patternTypeMap[self.options.patternType]
        case = self.caseMap[self.options.caseSensitivity]
        try:
            matches = findlib.findallex(
                text, pattern,
                patternType=patternType, case=case,
                matchWord=self.options.matchWord)
        except (re.error, findlib.FindError), ex:
            global lastErrorSvc
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        if matches:
            resultsView = UnwrapObject(resultsView)
            for match in matches:
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
                resultsView.AddFindResult(
                    url, startByteIndex, endByteIndex, value,
                    url, # fileName (currently url/viewId is the displayName)
                    startLineNum + 1,
                    startByteIndex - scimoz.positionFromLine(startLineNum),
                    context)

    def findalllines(self, url, text, pattern, contextOffset, scimoz):
        """Return all lines on which "pattern" is found.

            "url" is the viewId.
            "contextOffset" is text's offset into the scimoz buffer. This
                is only used if resultsView is specified.
            "scimoz" is the ISciMoz interface for current view. This is only
                used if resultsView is specified.
        
        Returns a list of line numbers (0-based).
        """
        
        patternType = self.patternTypeMap[self.options.patternType]
        case = self.caseMap[self.options.caseSensitivity]
        try:
            matches = findlib.findallex(
                text, pattern,
                patternType=patternType, case=case,
                matchWord=self.options.matchWord)
        except (re.error, findlib.FindError), ex:
            global lastErrorSvc
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        lines = {}  # use dict to avoid dupes
        for match in matches:
            startCharIndex = match.start() + contextOffset
            startByteIndex = scimoz.positionAtChar(0, startCharIndex)
            startLineNum = scimoz.lineFromPosition(startByteIndex)
            lines[startLineNum] = 1
        return lines.keys()

    def replaceallex(self, url, text, pattern, replacement, session,
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
        # Determine a "skip-zone" in the current URL. I.e., the area already
        # covered by the user in this find session.
        session = UnwrapObject(session)
        secondLastHit = session.GetSecondLastFindResult()
        if not secondLastHit or secondLastHit.url != url:
            skipZone = None
        elif session.wrapped:
            # Skip zone is from 0 to end of second last hit and from
            # fileStartPos to end of file.
            if self.options.searchBackward:
                skipZone = [(0, session.fileStartPos),
                            (secondLastHit.start, len(text))]
            else:
                skipZone = [(0, secondLastHit.end),
                            (session.fileStartPos, len(text))]
        else:
            # Skip zone is from the fileStartPos to the end of the second
            # last hit. (_Second_ last, because the current hit (the "last")
            # one is still a candidate for replacement.)
            if self.options.searchBackward:
                skipZone = [(secondLastHit.start, session.fileStartPos)]
            else:
                skipZone = [(session.fileStartPos, secondLastHit.end)]
        
        patternType = self.patternTypeMap[self.options.patternType]
        case = self.caseMap[self.options.caseSensitivity]
        try:
            replacementText, numReplacements, matches = findlib.replaceallex(
                text, pattern, replacement,
                patternType=patternType, case=case,
                searchBackward=self.options.searchBackward,
                matchWord=self.options.matchWord, skipZone=skipZone,
                wantMatches=resultsView is not None)
        except (re.error, findlib.FindError), ex:
            global lastErrorSvc
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        if matches:
            resultsView = UnwrapObject(resultsView)
            for match in matches:
                repl = match.expand(replacement)
                startCharIndex = match.start() + contextOffset
                endCharIndex = startCharIndex + len(repl)

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
                    repl, # replacement string
                    url, # fileName (currently url/viewId is the displayName)
                    startLineNum + 1,
                    startByteIndex - scimoz.positionFromLine(startLineNum),
                    context)

        return replacementText, numReplacements

    def replaceallinfiles(self, id, pattern, repl, resultsMgr,
                          resultsView):
        log.info("s/%s/%s/g", pattern, repl)
        print "TODO: s/%s/%s/g" % (pattern, repl)

        #patternType = self.patternTypeMap[self.options.patternType]
        #caseSensitivity = self.caseMap[self.options.caseSensitivity]
        #try:
        #    findlib.validatePattern(pattern, patternType=patternType,
        #                            case=caseSensitivity,
        #                            matchWord=self.options.matchWord)
        #except (re.error, findlib.FindError), ex:
        #    lastErrorSvc.setLastError(0, str(ex))
        #    raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))
        #
        #t = _ReplacerInFiles(
        #        id, pattern, patternType, repl, caseSensitivity,
        #        self.options.matchWord,
        #        self.options.getFolders(),
        #        resultsMgr.context_.cwd,
        #        self.options.searchInSubfolders,
        #        self.options.getIncludeFiletypes(),
        #        self.options.getExcludeFiletypes(),
        #        resultsMgr,
        #        resultsView)
        #self._threadMap[id] = t
        #resultsMgr.searchStarted()
        #self._threadMap[id].start()        

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
        log.info("findallinfiles(pattern='%s', resultsView)", pattern)

        patternType = self.patternTypeMap[self.options.patternType]
        caseSensitivity = self.caseMap[self.options.caseSensitivity]
        # validate now
        try:
            findlib.validatePattern(pattern, patternType=patternType,
                                    case=caseSensitivity,
                                    matchWord=self.options.matchWord)
        except (re.error, findlib.FindError), ex:
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_INVALID_ARG, str(ex))

        t = _FinderInFiles(id, pattern, patternType, caseSensitivity,
                           self.options.matchWord,
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

# Recipe: paths_from_path_patterns (0.3.5)
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
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path

