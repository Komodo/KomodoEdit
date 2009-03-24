#!python
# Copyright (c) 2003-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""The main PyXPCOM module for Komodo's 'fast open' feature, i.e. the
"Go to File" dialog.
"""

import os
from os.path import (expanduser, basename, split, dirname, splitext, join,
    abspath)
import sys
import string
import re
import threading
import logging
import types
from glob import glob
from pprint import pprint
from collections import defaultdict

from xpcom import components, nsError, ServerException, COMException
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import UnwrapObject
from koTreeView import TreeView

try:
    import fastopen
except ImportError:
    # PyXPCOM registration doesn't put extension 'pylib' dirs on sys.path, so
    # we put it in (HACK).
    pylib_dir = join(dirname(dirname(abspath(__file__))), "pylib")
    sys.path.insert(0, pylib_dir)
    import fastopen



#---- globals

log = logging.getLogger("fastopen")
#log.setLevel(logging.DEBUG)



#---- fastopen backend

class KoFastOpenTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.koIFastOpenTreeView]
    _reg_clsid_ = "{2d53a00d-9f41-634f-b702-d163e44061ee}"
    _reg_contractid_ = "@activestate.com/koFastOpenTreeView;1"
    _reg_desc_ = "Fast Open Results Tree View"

    _tree = None
    _rows = None

    def __init__(self, uiDriver):
        self.uiDriver = uiDriver
        TreeView.__init__(self) #, debug="fastopen")
        self._tree = None
        self._selectionProxy = None
        self.resetHits()

        ## Styling of the rows based on hit type.
        #atomSvc = components.classes["@mozilla.org/atom-service;1"].\
        #          getService(components.interfaces.nsIAtomService)
        #self._atomFromHitType = {
        #    "open-view": atomSvc.getAtom("open-view"),
        #    "path": atomSvc.getAtom("path"),
        #    "project-path": atomSvc.getAtom("project-path"),
        #    "history-uri": atomSvc.getAtom("history-uri"),
        #}
        #self._oddBlockAtom = atomSvc.getAtom("odd_block")
        #self._blockStartAtom = atomSvc.getAtom("blockStart")

    def resetHits(self):
        num_rows_before = self._rows and len(self._rows) or 0
        self._rows = []
        try:
            if self._tree:
                self._tree.beginUpdateBatch()
                self._tree.rowCountChanged(0, -num_rows_before)
                self._tree.invalidate()
                self._tree.endUpdateBatch()
        except AttributeError:
            pass # ignore `self._tree` going away

    def addHit(self, hit):
        index = len(self._rows)  # just appending for now
        self._rows.append(hit)
        try:
            self._tree.beginUpdateBatch()
            try:
                self._tree.rowCountChanged(index, 1)
                self._tree.invalidateRow(index)
            finally:
                self._tree.endUpdateBatch()
            if index == 0:  # i.e. added first row
                self._selectionProxy.select(0)
        except AttributeError:
            pass # ignore `self._tree` going away

    def addHits(self, hits):
        """Batch add multiple hits."""
        index = len(self._rows)
        self._rows += hits
        try:
            self._tree.beginUpdateBatch()
            try:
                self._tree.rowCountChanged(index, len(hits))
                self._tree.invalidateRange(index, len(self._rows))
            finally:
                self._tree.endUpdateBatch()
            if index == 0:  # i.e. added first row
                self._selectionProxy.select(0)
        except AttributeError:
            pass # ignore `self._tree` going away
    
    # Dev Note: These are just on the koIFastOpenTreeView to relay to the
    # koIFastOpenUIDriver because only the former is passed to the backend
    # `fastopen.Driver` thread. That is kind of lame.
    def searchStarted(self):
        self.uiDriver.searchStarted()
    def searchAborted(self):
        self.uiDriver.searchAborted()
    def searchCompleted(self):
        self.uiDriver.searchCompleted()
    
    def getSelectedHits(self): 
        hits = []
        for i in range(self.selection.getRangeCount()):
            start, end = self.selection.getRangeAt(i)
            for row_idx in range(start, end+1):
                hits.append(self._rows[row_idx])
        return hits
 
    #---- nsITreeView methods

    def setTree(self, tree):
        if tree is None:
            self._rawTree = self._tree = self._selectionProxy = None
        else:
            self._rawTree = tree
            self._tree = getProxyForObject(None,
                components.interfaces.nsITreeBoxObject,
                self._rawTree, PROXY_ALWAYS | PROXY_SYNC)
            self._selectionProxy = getProxyForObject(None,
                components.interfaces.nsITreeSelection,
                self.selection, PROXY_ALWAYS | PROXY_SYNC)

    def get_rowCount(self):
        try:
            return len(self._rows)
        except TypeError: # self._rows is None
            return 0

    def getCellText(self, row, column):
        try:
            return self._rows[row].label
        except IndexError:
            #log.debug("no %sth hit" % row)
            pass
    
    # Dev Note: Pieces of failed attempt at some differentiating styling of
    #   rows from different gatherers in the results tree.
    #def getRowProperties(self, row_idx, properties):
    #    try:
    #        row = self._rows[row_idx]
    #    except (IndexError, AttributeError):
    #        pass
    #    else:
    #        pass
    #        #print "row %d: %r -> %r" % (row_idx, row, odd_block)
    #        #if row.odd_block:
    #        #    properties.AppendElement(self._oddBlockAtom)
    #        
    #        #atom = self._atomFromHitType.get(row.type, None)
    #        #if atom:
    #        #    properties.AppendElement(atom)
    #        
    #        #if row_idx == 0 or self._rows[row_idx-1].type != row.type:
    #        #    properties.AppendElement(self._blockStartAtom)
    #        #    last_row = self._rows[row_idx-1]

    def selectionChanged(self):
        index = self.selection.currentIndex
        try:
            path = self._rows[index].path
        except IndexError:
            path = ""
        self.uiDriver.setCurrPath(path)

    def getImageSrc(self, row, column):
        try:
            hit = self._rows[row]
        except IndexError:
            pass
        else:
            if hit.type == "path" and hit.isdir:
                #TODO: How to get native *directory* icon from moz-icon?
                return "chrome://komodo/skin/images/folder-open.png"
            else:
                return "moz-icon://%s?size=16" % (hit.ext or ".txt")


class KoFastOpenSession(object):
    _com_interfaces_ = [components.interfaces.koIFastOpenSession]
    _reg_desc_ = "Fast Open search session"
    _reg_clsid_ = "{16d03764-c4b2-5342-a091-78fe11057d43}"
    _reg_contractid_ = "@activestate.com/koFastOpenSession;1"

    # Number of secs to wait for previous search to stop.
    SEARCH_STOP_TIMEOUT = 90

    resultsView = None
    uiDriver = None
    
    # Configuration attributes. These values determine the value returned
    # by `gatherers`, i.e. the sources for the list of files.
    project = None
    views = None

    def __init__(self, driver, uiDriver):
        self.driver = driver
        self.uiDriver = uiDriver
        self.resultsView = KoFastOpenTreeView(uiDriver)
        self.uiDriver.setTreeView(self.resultsView)

    @property
    def path_excludes_pref(self):
        """Get, convert to list and normalize `fastopen_path_excludes` pref.
        
        The list is stored as a ';'-separated string (':' and ',' also allowed
        as separators). Whitespace is stripped. Preceed a separator char with
        '\' to have it *not* separate.
        """
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        excludes = None
        if prefs.hasStringPref("fastopen_path_excludes"):
            excludes_str = prefs.getStringPref("fastopen_path_excludes")
            if excludes_str.strip():  # empty means "use default"
                excludes = self._excludes_from_str(excludes_str)
        return excludes
    
    _excludes_splitter = re.compile(r'(?<!\\)[;:,]') # be liberal about splitter char
    def _excludes_from_str(self, excludes_str):
        excludes = []
        for s in self._excludes_splitter.split(excludes_str):
            s = s.strip()
            if not s: continue
            if ';' in s: s = s.replace('\\;', ';')
            if ':' in s: s = s.replace('\\:', ':')
            if ',' in s: s = s.replace('\\,', ',')
            excludes.append(s)
        return excludes

    def _excludes_from_json(self, excludes_json):
        # Note: not currently used
        import json
        excludes = None
        try:
            excludes = json.loads(excludes_json)
        except ValueError:
            summary = (excludes_json if len(excludes_json) < 30
                else excludes_json[:30]+"...")
            log.warn("invalid json in `fastopen_path_excludes' pref: %s",
                summary)
        if not isinstance(excludes, list):
            excludes = None
        return excludes

    def setCurrProject(self, project):
        self.project = project
        self._gatherers_cache = None
    def setOpenViews(self, views):
        self.views = views
        self._gatherers_cache = None
    def setCurrHistorySession(self, sessionName):
        self.historySessionName = sessionName
        self._gatherers_cache = None

    @property
    def gatherersAndCwds(self):
        if self._gatherers_cache is None:
            g = fastopen.Gatherers()
            cwds = None
            if self.views:
                kovg = KomodoOpenViewsGatherer(self.views)
                g.append(kovg)
                cwds = list(kovg.cwds)
            g.append(KomodoHistoryURIsGatherer(self.historySessionName))
            if cwds:
                g.append(fastopen.DirGatherer("cwd", cwds, True,
                    self.path_excludes_pref))
            if self.project:
                g.append(fastopen.CachingKomodoProjectGatherer(
                    UnwrapObject(self.project)))
            self._gatherers_cache = (g, cwds)
        return self._gatherers_cache

    def findFiles(self, query):
        gatherers, cwds = self.gatherersAndCwds
        self.driver.search(query, gatherers, cwds, self.path_excludes_pref,
            self.resultsView)

class KoFastOpenService(object):
    _com_interfaces_ = [components.interfaces.koIFastOpenService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Fast Open service"
    _reg_clsid_ = "{1ffc88c7-b388-c844-b60b-e1f04bfb86d3}"
    _reg_contractid_ = "@activestate.com/koFastOpenService;1"

    DEFAULT_PATH_EXCLUDES = ';'.join(fastopen.DEFAULT_PATH_EXCLUDES)

    _driverCache = None
    @property
    def driver(self):
        if self._driverCache is None:
            self._driverCache = fastopen.Driver()
            obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService)
            obsSvc.addObserver(self, "xpcom-shutdown", 1)
        return self._driverCache

    def getSession(self, uiDriver):
        return KoFastOpenSession(self.driver, uiDriver)

    def observe(self, subject, topic, data):
        if topic == "xpcom-shutdown":
            if self._driverCache:
                self._driverCache.stop()
            obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService)
            obsSvc.removeObserver(self, "xpcom-shutdown")



#---- internal support stuff

class KomodoHistoryURIHit(fastopen.PathHit):
    type = "history-uri"
    def __init__(self, uri):
        from uriparse import URIToLocalPath
        self.uri = uri
        path = URIToLocalPath(uri)
        super(KomodoHistoryURIHit, self).__init__(path)
    @property
    def label(self):
        return u"%s (history) %s %s" % (self.base, fastopen.MDASH, self.nicedir)


class KomodoHistoryURIsGatherer(fastopen.Gatherer):
    """Gather recent URIs from the history."""
    name = "history"
    
    def __init__(self, sessionName):
        self.sessionName = sessionName
        try:
            koHistorySvc = components.classes["@activestate.com/koHistoryService;1"].\
                getService(components.interfaces.koIHistoryService)
        except COMException:
            self.koHistorySvc = None
        else:
            self.koHistorySvc = UnwrapObject(koHistorySvc)
        self._cachedHits = []
    
    _uri_generator = None
    def gather(self):
        if self.koHistorySvc is not None:
            # First yield any hits we've already gathered and cached.
            for hit in self._cachedHits:
                yield hit
            
            # Then, yield and cache any remaining ones.
            #TODO: pref for '50' here
            if self._uri_generator is None:
                self._uri_generator = self.koHistorySvc.recent_uris(
                    50, self.sessionName)
            for uri in self._uri_generator:
                if not uri.startswith("file://"):
                    #TODO: Is this a sufficient guard for possible history URLs?
                    continue
                hit = KomodoHistoryURIHit(uri)
                self._cachedHits.append(hit)
                yield hit

class KomodoOpenViewHit(fastopen.PathHit):
    type = "open-view"
    filterDupePaths = False
    def __init__(self, view, path, viewType, windowNum, tabGroupId, multi, **kwargs):
        super(KomodoOpenViewHit, self).__init__(path)
        self.view = view
        self.viewType = viewType
        self.windowNum = windowNum
        self.tabGroupId = tabGroupId
        self.multi = multi  # whether there are multiple views for this path
    @property
    def label(self):
        bits = ["open"]
        if self.viewType not in ("editor", "startpage"):
            bits.append("%s view" % self.viewType)
        if self.multi:
            # Don't bother while fastopen only works on views in the current
            # window.
            #bits.append("window %s" % self.windowNum)
            bits.append("tab group %s" % self.tabGroupId)
        if bits:
            extra = " (%s)" % ", ".join(bits)
        else:
            extra = ""
        if self.viewType == "startpage":
            return u"%s%s" % (self.path, extra)
        else:
            nicedir = self.nicedir
            if not nicedir:
                return u"%s%s" % (self.base, extra)
            else:
                return u"%s%s %s %s" % (self.base, extra, fastopen.MDASH, self.nicedir)

class KomodoOpenViewsGatherer(fastopen.Gatherer):
    """A gatherer of currently open Komodo views."""
    name = "open views"
    
    def __init__(self, views):
        self.views = views
    
    _viewDataCache = None
    @property
    def viewData(self):
        if self._viewDataCache is None:
            ifaceFromViewType = {
                "browser": components.interfaces.koIBrowserView,
                "startpage": components.interfaces.koIStartPageView,
                # Also "diff" view.
                "editor": components.interfaces.koIScintillaView,
            }
            viewData = []
            viewDataFromPath = defaultdict(list)
            viewIds = set()
            for view in self.views:
                viewType = view.getAttribute("type")
                try:
                    iface = ifaceFromViewType[viewType]
                except KeyError:
                    log.debug("skip `%s' view: don't know interface for it", viewType)
                    continue
                try:
                    view = view.QueryInterface(iface)
                except Exception:
                    log.debug("skip `%s' view: QI failed", viewType)
                    continue
                if viewType in ("editor", "browser"):
                    koFileEx = view.document.file
                    if koFileEx:
                        uri = koFileEx.URI
                        isLocal = koFileEx.isLocal
                    else:
                        uri = None
                        isLocal = False
                    path = view.document.displayPath
                elif viewType == "startpage":
                    uri = None
                    path = "Start Page"
                    isLocal = False
                else:
                    continue
                
                # Guard against bogus duplicate entries from viewhistory --
                # a problem in workspace restore, I believe. No bug yet.
                viewId = (viewType, path, view.windowNum, view.tabbedViewId)
                if viewId in viewIds:
                    continue
                viewIds.add(viewId)
                
                datum = dict(view=view, viewType=viewType, path=path,
                    windowNum=view.windowNum, tabGroupId=view.tabbedViewId,
                    uri=uri, isLocal=isLocal,
                    multi=False)
                viewData.append(datum)
                multi = path in viewDataFromPath
                viewDataFromPath[path].append(datum)
                if multi:
                    for d in viewDataFromPath[path]:
                        d["multi"] = True
            #pprint(viewData)
            self._viewDataCache = viewData
        
        return self._viewDataCache
    
    @property
    def cwds(self):
        """Generate the open editor view *dirs* in Ctrl+Tab order. Duplicates
        are removed.
        """
        from os.path import dirname
        dirs = set()
        for d in self.viewData:
            if d["viewType"] != "editor":
                continue
            if not d["isLocal"]:
                # Don't yet handle remote files.
                continue
            dir = dirname(d["path"])
            if dir in dirs:
                continue
            dirs.add(dir)
            yield dir
        
    def gather(self):
        # Skip the first view, this is the current view and is no use in the
        # "Go to file" dialog: we are already there.
        for d in self.viewData[1:]:
            yield KomodoOpenViewHit(**d)
    
