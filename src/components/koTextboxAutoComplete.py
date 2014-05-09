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

"""A module to hold all Komodo's <textbox type="autocomplete"/> autocomplete
search types. Some shared base-class details are in 'kotaclib.py'.

In XUL, one identifies the autocomplete source with the
"autocompletesearch" attribute:

    <textbox type="autocomplete"
             autocompletesearch="history"
             .../>

This instanciates a component with the contract ID:
    @mozilla.org/autocomplete/search;1?name=<name>
(in this example "@mozilla.org/autocomplete/search;1?name=history")
implementing the nsIAutoCompleteSearch interface.

See class KoTACDemoSearch for a sample search implementation to get you
started. See "Test -> Test Firefox AutoComplete" in a Komodo dev build to
play with the UI-side of things.

Currently implemented textbox autocomplete types:
    mru                 complete Komodo MRU preference list
    filepath            complete local paths
    mru_and_filepath    complete both an MRU pref and local paths
    dirpath             complete local directories
    mru_and_dirpath     complete both an MRU pref and local dirs
    item_and_mru        complete both an optionally provided item (in
                        'autocompletesearchparam' attr) and an MRU pref

http://developer.mozilla.org/en/docs/XUL:textbox_%28Firefox_autocomplete%29
"""

import os
from os.path import basename
import sys
import logging
import re

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject
import fileutils
from kotaclib import KoTACSearch, KoTACMatch

log = logging.getLogger("koTAC")
#log.setLevel(logging.DEBUG)

#---- helper stuff for autocomplete implementations below

class KoTACResult(object):
    """A base implementation of ns/koIAutoCompleteResult.
    
    This component can be used directly or may be subclassed for
    specific textbox autocomplete search types if extra functionality is
    required. If subclassed, all the _reg_*_ attributes MUST be
    overriden.

    Typical usage for creating a search result:

    1. For a successful search:
            result = components.classes["@activestate.com/autocomplete/result;1"] \
                .createInstance(components.interfaces.koIAutoCompleteResult)
            result.init(<search-string>)
            for match in <find-matches>:
                result.addMatch2(match)
    2. For an invalid search string:
            result = components.classes["@activestate.com/autocomplete/result;1"] \
                .createInstance(components.interfaces.koIAutoCompleteResult)
            result.init(<search-string>)
            result.setIgnored()
    3. For a failed search:
            result = components.classes["@activestate.com/autocomplete/result;1"] \
                .createInstance(components.interfaces.koIAutoCompleteResult)
            result.init(<search-string>)
            result.setFailed(<error-description>)

    http://lxr.mozilla.org/seamonkey/source/toolkit/components/autocomplete/public/nsIAutoCompleteResult.idl
    """
    _com_interfaces_ = [components.interfaces.koIAutoCompleteResult]
    _reg_clsid_ = "{F29911D8-F3C3-11D9-A507-000D934CF260}"
    _reg_contractid_ = "@activestate.com/autocomplete/result;1"
    _reg_desc_ = "Komodo textbox autocomplete search result"

    searchString = None
    searchResult = None
    defaultIndex = 0
    errorDescription = None
    matches = None   # list of koIAutoCompleteMatch

    def __init__(self):
        self.prefName = None
    
    def init(self, searchString):
        self.searchString = searchString
        self.searchResult = components.interfaces.nsIAutoCompleteResult.RESULT_NOMATCH
        self.matches = []

    def setIgnored(self):
        """Indicate an invalid search string."""
        self.searchResult = components.interfaces.nsIAutoCompleteResult.RESULT_IGNORED

    def setFailed(self, errorDescription):
        """The search failed."""
        self.searchResult = components.interfaces.nsIAutoCompleteResult.RESULT_FAILURE
        self.errorDescription = errorDescription

    def addMatch(self, value, comment=None, style=None, isDefault=False, image=None):
        """Add an AutoComplete search match/hit

            "value" is the (string) value of the match.
            "comment" is an optional comment string (which may or may
                not be shown in the autocomplete textbox UI depending on
                the "showcommentcolumn" XUL attribute).
            "style" is an optional style hint string to be used on this
                match row in the autocomplete textbox UI. Basically,
                this is a CSS class name and the usage here is equivalent to 
                the "showDetail" CSS class used in the Komodo Code
                Browser tree view for highlighting the hovered item.
            "isDefault" (optional, default False) is a boolean
                indicating if this match should be the "defaultIndex".
                The default index is used if the "completedefaultindex"
                XUL attribute is true. By default the zeroth index is
                the default. See:
                http://developer.mozilla.org/en/docs/XUL:textbox_%28Firefox_autocomplete%29#a-completedefaultindex
            "image" ... TODO: document
        """
        self.addMatch2(KoTACMatch(value, comment, style, isDefault, image))

    def addMatch2(self, match):
        nsIAutoCompleteResult = components.interfaces.nsIAutoCompleteResult
        if not self.matches \
           and self.searchResult == nsIAutoCompleteResult.RESULT_NOMATCH:
            self.searchResult = nsIAutoCompleteResult.RESULT_SUCCESS
        self.matches.append(match)
        if match.isDefault:
            self.defaultIndex = len(self.matches) - 1

    #---- nsIAutoCompleteResult implementation
    typeAheadResult = False
    def get_matchCount(self):
        return len(self.matches)
    def getValueAt(self, index):
        return self.matches[index].value
    def getCommentAt(self, index):
        return self.matches[index].comment
    def getStyleAt(self, index):
        return self.matches[index].style
    def getImageAt(self, index):
        return self.matches[index].image
    def removeValueAt(self, rowIndex, removeFromDb=False):
        if removeFromDb and self.prefName is not None:
            prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                .getService().prefs # global prefs
            try:
                prefSvc.getPref(self.prefName).deletePref(rowIndex)
            except:
                log.exception("Failed to delete pref %d(%s)",
                              rowIndex, self.matches[rowIndex])
        del self.matches[rowIndex]

    # New in mozilla-central nsIAutoCompleteResult interface.
    getLabelAt = getValueAt
    # New in mozilla 31 nsIAutoCompleteResult interface.
    getFinalCompleteValueAt = getValueAt


#---- specific TAC type searches

class KoTACDemoSearch(KoTACSearch):
    """This is a demostration nsIAutoCompleteSearch implementation to show how
    textbox autocomplete can be implemented in Komodo.
    """
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{9A4DEF8A-F3CD-11D9-AA2A-000D934CF260}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=demo"
    _reg_desc_ = "demo textbox autocomplete search: completes filenames in ~/tmp"

    def __init__(self):
        self.tmpdir = os.path.expanduser(os.path.join("~", "tmp"))

    def startSearch(self, searchString, searchParam, previousResult, listener):
        nsIAutoCompleteResult = components.interfaces.nsIAutoCompleteResult
        log.debug("startSearch(searchString=%r, searchParam=%r, "
                  "previousResult=%r, listener)", searchString, 
                  searchParam, previousResult)

        result = KoTACResult()
        result.init(searchString)

        try:
            filenames = os.listdir(self.tmpdir)
        except EnvironmentError, ex:
            result.setFailed("cannot list tmp dir: %s" % ex)
            listener.onSearchResult(self, result)
            return

        for name in [f for f in filenames if f.startswith(searchString)]:
            path = os.path.join(self.tmpdir, name)
            comment = "%s bytes" % os.stat(path).st_size
            # Notes on styling: For a given style to work you must be sure
            # to include the relevant CSS in the XUL with the autocomplete
            # textbox. For example, you might have CSS like this:
            #   treechildren::-moz-tree-cell-text(girly) {
            #       color: pink;
            #   }
            # and code here like this:
            #   if is_girly(name):
            #       style = "girly"
            style = None
            result.addMatch(name, comment, style, False)
        listener.onSearchResult(self, result)

    def stopSearch(self):
        """This is sent by the autocomplete controller to stop a
        possible previous asynchronous search.
        """
        pass


class KoTACFilePathSearch(KoTACSearch):
    """Textbox AutoComplete search for local filepaths."""
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{681A2200-F3E9-11D9-8F02-000D934CF260}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=filepath"
    _reg_desc_ = "local file path textbox autocomplete search"

    dirsOnly = False
    normPaths = True   # normalize paths

    def startSearch(self, pattern, cwd, previousResult, listener):
        """Synchronously complete the given path pattern. If the path is
        relative, then treat it relative to the given "cwd". If "cwd" is
        empty then do not commplete on relative paths.
        """
        result = KoTACResult()
        result.init(pattern)
        cwd = self.parseSearchParam(cwd).get("filepath", cwd)

        #XXX Disable this optimization because
        #    - It screws up with non-normalized paths, e.g. 'foo//bar'.
        if False and (previousResult and previousResult.searchString
            and pattern.startswith(previousResult.searchString)
            and os.sep not in pattern[len(previousResult.searchString):]):
            # OPTIMIZATION: Use the previous result too more efficiently
            # pare down the list (instead of stat'ing again).
            for i in range(previousResult.matchCount):
                value = previousResult.getValueAt(i)
                if value.startswith(pattern):
                    result.addMatch(value, None, None, False)
        else:
            #XXX For mounted filesystems this could take a long time.
            #    Ideally this should be asynchronous with the result being
            #    dropped if get stopSearch() before finished.
            for path in _genPathCompletions(pattern, cwd, self.dirsOnly):
                if self.normPaths:
                    path = os.path.normpath(path)
                result.addMatch(path, None, None, False)

        listener.onSearchResult(self, result)

    def stopSearch(self):
        pass


class KoTACDirPathSearch(KoTACFilePathSearch):
    """Textbox AutoComplete search for local directory paths."""
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{A6725BFC-FB38-11D9-977C-000D93B826C2}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=dirpath"
    _reg_desc_ = "local directory path textbox autocomplete search"

    dirsOnly = True # argument to path completion generator


class KoTACMruSearch(KoTACSearch):
    """Textbox AutoComplete search for an MRU (most recently used list)
    in Komodo preferences.
    """
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{686ED0A6-F4AC-11D9-9048-000D934CF260}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=mru"
    _reg_desc_ = "Komodo MRU pref textbox autocomplete search"

    def __init__(self):
        KoTACSearch.__init__(self)
        self.prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                .getService().prefs # global prefs

    def startSearch(self, searchString, prefName, previousResult, listener):
        """Synchronously complete the given string against the Komodo
        MRU pref list.
        """
        DEBUG = log.getEffectiveLevel() <= logging.DEBUG
        log.debug("startSearch(searchString=%r, prefName=%r, "
                  "previousResult=%r, listener)", searchString, 
                  prefName, previousResult)

        result = KoTACResult()
        result.init(searchString)

        # Try to parse the search param, in case we have multiple autocompleters
        prefDict = self.parseSearchParam(prefName)
        prefName = prefDict.get("mru", prefName)
        if DEBUG: log.debug("prefDict: %r", prefDict)

        if DEBUG: allitems = []
        if self.prefSvc.hasPref(prefName):
            mru = self.prefSvc.getPref(prefName)
            if mru:
                result.prefName = prefName
            for i in range(mru.length):
                item = mru.getStringPref(i)
                if DEBUG: allitems.append(item)
                if item.startswith(searchString):
                    result.addMatch(item, None, None, False)
        if DEBUG: log.debug("All '%s' items: %r", prefName, allitems)
        listener.onSearchResult(self, result)

    def stopSearch(self):
        pass


class KoTACMruAndFilePathSearch(KoTACSearch):
    """Textbox AutoComplete search combining elements (as best as
    possible) of the "filepath" and "mru" autocomplete backends.
    Sometimes you want both, e.g.: the 'folders' part of the Find
    toolbar.
    """
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{6064FA68-F5A3-11D9-B732-000D934CF260}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=mru_and_filepath"
    _reg_desc_ = "Komodo MRU+filepath textbox autocomplete search"

    dirsOnly = False
    normPaths = True   # normalize paths

    def __init__(self):
        KoTACSearch.__init__(self)
        self.prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                .getService().prefs # global prefs

    def startSearch(self, searchString, searchParam, previousResult, listener):
        r"""Synchronously complete the given string against the Komodo
        MRU pref list *and* the filepath.
        
        Here is how it could (and does currently) work:
        - limit the number of MRU hits to, say, 5 (something small)
        - put the MRU hits first
        - style the MRU and path hits slightly differently (icons?)
        - perhaps make the *default index* the first path hit (so really
          it completes paths by default if the textbox set
          completedefaultindex="true")

        The searchParam (i.e. the 'autocompletesearchparam' attribute)
        syntax is like specifying CSS style attributes (the key/value
        pairs can be in any order):

            cwd: ...; mru: ...; maxmru: ...; multipaths: ...

        Where:
            'cwd' is the current working directory. If not given then
                there won't be any completions for relative paths.
            'mru' is an MRU list preference name and is require to get
                MRU results.
            'maxmru' is a maximum number of MRU results to return.
                Something like '5' is typical. If not specified then all
                MRU results are returned.
            'multipaths' is a boolean (should be "true" or "false")
                indicating if the textbox can contain multiple
                ('os.pathsep'-separated) paths. By default this is false.
        """
        DEBUG = False
        log.debug("startSearch(searchString=%r, searchParam=%r, "
                  "previousResult=%r, listener)", searchString, 
                  searchParam, previousResult)

        # Parse the searchParam
        if DEBUG: print "startSearch: parse searchParam: %r" % searchParam
        params = self.parseSearchParam(searchParam)
        cwd = params.get("cwd")
        prefName = params.get("mru")
        mruLimit = params.get("maxmru")
        if mruLimit is not None:
            try:
                mruLimit = int(mruLimit)
            except ValueError:
                log.warn("invalid searchParam 'maxmru' value, skipping: %r",
                         mruLimit)
                mruLimit = None
        multiPaths = self._boolFromStr(params.get("multipaths", ""))
        if not cwd and not prefName:
            log.warn("potentially bogus autocompletesearchparam for "
                     "mru_and_filepath search: %r" % searchParam)
        if DEBUG:
            print "startSearch: prefName=%r" % prefName
            print "startSearch: cwd=%r" % cwd
            print "startSearch: mruLimit=%r" % mruLimit

        result = result = KoTACResult()
        result.init(searchString)

        # Pref hits first (limited number)
        if prefName:
            num = 0
            if self.prefSvc.hasPref(prefName):
                mru = self.prefSvc.getPref(prefName)
                for i in range(mru.length):
                    item = mru.getStringPref(i)
                    if item.startswith(searchString):
                        if DEBUG:
                            print "startSearch: mru hit: %r" % item
                        result.addMatch(item, None, "ac-special", False)
                        num += 1
                        if mruLimit is not None and num >= mruLimit:
                            break
                    else:
                        if DEBUG:
                            print "startSearch: skip mru item: %r" % item

        # Now filepath hits.
        if multiPaths:
            # If this is textbox can hold multiple 'os.pathsep'-separated
            # paths, then just complete on the last one.
            paths = searchString.rsplit(os.pathsep, 1)
            leadingPaths, searchString = paths[:-1], paths[-1]
        if DEBUG:
            print "startSearch: complete '%s' path in '%s'" % (searchString, cwd)
        num = 0
        for path in _genPathCompletions(searchString, cwd, self.dirsOnly):
            if DEBUG:
                print "startSearch: path hit: '%s'" % path
            isDefault = num == 0
            if self.normPaths:
                path = os.path.normpath(path)
            if multiPaths and leadingPaths:
                result.addMatch(os.pathsep.join(leadingPaths + [path]),
                                path, None, isDefault)
            else:
                result.addMatch(path, None, None, isDefault)
            num += 1

        listener.onSearchResult(self, result)

    def stopSearch(self):
        pass

    def _boolFromStr(self, s):
        if s.strip() == "true":
            return True
        else:
            return False


class KoTACMruAndDirPathSearch(KoTACMruAndFilePathSearch):
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{0D80BBBF-FB39-11D9-8CCB-000D93B826C2}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=mru_and_dirpath"
    _reg_desc_ = "Komodo MRU+dirpath textbox autocomplete search"

    dirsOnly = True



class KoTACItemAndMruSearch(KoTACSearch):
    """Textbox autocomplete combining an optional hardcoded item (in the
    'autocompletesearchparam' of the <textbox> element) and values from an
    "mru" preference.
    
    See the startSearch() docstring for details.
    """
    _com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    _reg_clsid_ = "{00bdea11-4f1f-43ce-a15e-91f4e3624b51}"
    _reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=item_and_mru"
    _reg_desc_ = "Komodo special item + MRU textbox autocomplete search"

    dirsOnly = False

    def __init__(self):
        KoTACSearch.__init__(self)
        self.prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                .getService().prefs # global prefs

    def startSearch(self, searchString, searchParam, previousResult, listener):
        r"""Synchronously complete the possible 'item' in the 'searchParam'
        plus MRU pref list items matching 'searchString'.
        
        The searchParam (i.e. the 'autocompletesearchparam' attribute)
        syntax is like specifying CSS style attributes (the key/value
        pairs can be in any order):

            mru: <mru-pref-name>; maxmru: ...; item: <item>

        Where:
            'mru' is an MRU list preference name and is require to get
                MRU results.
            'maxmru' is a maximum number of MRU results to return.
                Something like '5' is typical. If not specified then all
                MRU results are returned.
            'item' is an optional autocomplete item to return *first*.
            'item-comment' is an optional autocomplete comment to use for
                the item.
        """
        DEBUG = False
        log.debug("startSearch(searchString=%r, searchParam=%r, "
                  "previousResult=%r, listener)", searchString, 
                  searchParam, previousResult)

        # Parse the searchParam
        if DEBUG: print "startSearch: parse searchParam: %r" % searchParam
        params = self.parseSearchParam(searchParam)
        prefName = params.get("mru")
        item = params.get("item")
        itemComment = params.get("item-comment")
        mruLimit = params.get("maxmru")
        if mruLimit is not None:
            try:
                mruLimit = int(mruLimit)
            except ValueError:
                log.warn("invalid searchParam 'maxmru' value, skipping: %r",
                         mruLimit)
                mruLimit = None

        result = KoTACResult()
        result.init(searchString)

        if item is not None:
            result.addMatch(item, itemComment, "ac-special", False)

        # Pref hits first (limited number)
        if prefName:
            num = 0
            if self.prefSvc.hasPref(prefName):
                mru = self.prefSvc.getPref(prefName)
                for i in range(mru.length):
                    value = mru.getStringPref(i)
                    if value.startswith(searchString):
                        if DEBUG:
                            print "startSearch: mru hit: %r" % value
                        result.addMatch(value, None, None, False)
                        num += 1
                        if mruLimit is not None and num >= mruLimit:
                            break
                    else:
                        if DEBUG:
                            print "startSearch: skip mru value: %r" % value

        listener.onSearchResult(self, result)

    def stopSearch(self):
        pass



#---- internal support routines

def _genPathCompletions(pattern, cwd, dirsOnly=False):
    import sys, glob
    from os.path import isabs, join, isdir, ismount

    RELATIVE, ABSOLUTE, TILDE = range(3)
    if isabs(pattern):
        type = ABSOLUTE
        abspattern = pattern
    elif pattern and pattern[0] == '~':
        type = TILDE
        abspattern = os.path.expanduser(pattern)
        tilde_part = pattern.split(os.sep, 1)[0]
        home_part = os.path.expanduser(tilde_part)
    else:
        type = RELATIVE
        if cwd:
            abspattern = join(cwd, pattern)
        else:
            raise StopIteration
        cwd_with_sep = (cwd[-1] in (os.sep, os.altsep)
                        and cwd or cwd+os.sep)

    try:
        flist = glob.glob(abspattern+"*")
    except UnicodeDecodeError, ex:
        # Python's os.listdir doesn't handle names with high-bit characters,
        # since it doesn't know which encoding to use, and doesn't bother
        # trying to guess.
        dirPart, restPart = os.path.split(abspattern)
        if not dirPart:
            # os.path.split(<no slashes>) => ('', <no slashes>)
            return
        if restPart:
            # os.path.split(<ends-with-slash>) => (x, '')
            restPartStar = restPart + "*"
        names = os.listdir(dirPart)
        flist = []
        for name in names:
            if not restPart or glob.fnmatch.fnmatch(name, restPartStar):
                try:
                    flist.append(os.path.join(dirPart, name))
                except UnicodeDecodeError:
                    from koUnicodeEncoding import autoDetectEncoding
                    flist.append(os.path.join(dirPart, autoDetectEncoding(name)[0]))
        
    for path in sorted(flist):
        if fileutils.isHiddenFile(path):
            continue
        elif isdir(path) or (sys.platform == "win32" and ismount(path)):
            path += os.sep
        elif dirsOnly:
            continue
        if type == RELATIVE:
            if cwd:
                path = path[len(cwd_with_sep):]
        elif type == TILDE:
            path = tilde_part + path[len(home_part):]
        yield path




