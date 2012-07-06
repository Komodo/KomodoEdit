#!python
# Copyright (c) 2003-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""The main PyXPCOM module for Komodo's 'fast open' feature, i.e. the
"Go to File" dialog.
"""

import os
from os.path import (expanduser, basename, split, dirname, splitext, join,
    abspath, isabs)
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
        # uiDriver is a JavaScript instance, so we must *always* proxy any
        # calls made to this object through the main thread.
        self.uiDriver = getProxyForObject(1, # 1 means the main thread.
            components.interfaces.koIFastOpenUIDriver,
            uiDriver, PROXY_ALWAYS | PROXY_SYNC)
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

    _last_num_hits = 0

    # Batch update the tree every n rows - bug 82962.
    def _updateTreeView(self, force=False):
        """Update tree view when forced, or num rows changed significantly."""

        num_hits = len(self._rows)
        prev_num_hits = self._last_num_hits
        if (not force and num_hits < (prev_num_hits + 1000)) or not self._tree:
            # Don't update the tree yet.
            return
        self._last_num_hits = num_hits
        try:
            self._tree.beginUpdateBatch()
            try:
                num_rows_changed = num_hits - prev_num_hits
                if num_rows_changed < 0:
                    self._tree.rowCountChanged(num_hits, num_rows_changed)
                    #self._tree.invalidate()
                else:
                    self._tree.rowCountChanged(prev_num_hits, num_rows_changed)
                    #self._tree.invalidateRange(num_hits, num_rows_changed)
            finally:
                self._tree.endUpdateBatch()
        except AttributeError:
            pass # ignore `self._tree` going away
        if prev_num_hits == 0 and len(self._rows):  # i.e. added first row
            self._selectionProxy.select(0)

    def resetHits(self):
        self._rows = []
        self._updateTreeView(force=True)

    def addHit(self, hit):
        self._rows.append(hit)
        self._updateTreeView()

    def addHits(self, hits):
        """Batch add multiple hits."""
        self._rows += hits
        self._updateTreeView()
    
    # Dev Note: These are just on the koIFastOpenTreeView to relay to the
    # koIFastOpenUIDriver because only the former is passed to the backend
    # `fastopen.Driver` thread. That is kind of lame.
    def searchStarted(self):
        self.uiDriver.searchStarted()
        self._timer = threading.Timer(0.5, self._updateTreeView,
                                      kwargs={'force': True})
        self._timer.setDaemon(True)
        self._timer.start()
    def searchAborted(self):
        self._timer.cancel()
        self.uiDriver.searchAborted()
    def searchCompleted(self):
        self._timer.cancel()
        self.uiDriver.searchCompleted()
        self._updateTreeView(force=True)
    
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
            self._tree = getProxyForObject(1,
                components.interfaces.nsITreeBoxObject,
                self._rawTree, PROXY_ALWAYS | PROXY_SYNC)
            self._selectionProxy = getProxyForObject(1,
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
            if hit.type == "go":
                return "chrome://famfamfamsilk/skin/icons/folder_go.png"
            elif hit.type in ("path", "project-path") and hit.isdir:
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
    currentPlace = None

    def __init__(self, driver, uiDriver):
        self.driver = driver
        self.uiDriver = uiDriver
        self.resultsView = KoFastOpenTreeView(uiDriver)
        self.uiDriver.setTreeView(self.resultsView)

    _globalPrefsCache = None
    @property
    def _globalPrefs(self):
        if self._globalPrefsCache is None:
            self._globalPrefsCache = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs
        return self._globalPrefsCache

    @property
    def pref_path_excludes(self):
        """Get, convert to list and normalize `fastopen_path_excludes` pref.
        
        The list is stored as a ';'-separated string (':' and ',' also allowed
        as separators). Whitespace is stripped. Preceed a separator char with
        '\' to have it *not* separate.
        """
        excludes = None
        if self._globalPrefs.hasStringPref("fastopen_path_excludes"):
            excludes_str = self._globalPrefs.getStringPref("fastopen_path_excludes")
            if excludes_str.strip():  # empty means "use default"
                excludes = self._excludes_from_str(excludes_str)
        return excludes
    
    @property
    def pref_enable_go_tool(self):
        """Whether to enable go-tool integration.
        
        http://code.google.com/p/go-tool
        """
        enable = False
        if self._globalPrefs.hasBooleanPref("fastopen_enable_go_tool"):
            enable = self._globalPrefs.getBooleanPref("fastopen_enable_go_tool")
        return enable

    @property
    def pref_enable_open_views_gatherer(self):
        enable = True
        if self._globalPrefs.hasBooleanPref("fastopen_enable_open_views_gatherer"):
            enable = self._globalPrefs.getBooleanPref("fastopen_enable_open_views_gatherer")
        return enable

    @property
    def pref_enable_history_gatherer(self):
        enable = True
        if self._globalPrefs.hasBooleanPref("fastopen_enable_history_gatherer"):
            enable = self._globalPrefs.getBooleanPref("fastopen_enable_history_gatherer")
        return enable

    @property
    def pref_enable_cwd_gatherer(self):
        enable = True
        if self._globalPrefs.hasBooleanPref("fastopen_enable_cwd_gatherer"):
            enable = self._globalPrefs.getBooleanPref("fastopen_enable_cwd_gatherer")
        return enable

    @property
    def pref_enable_project_gatherer(self):
        enable = True
        if self._globalPrefs.hasBooleanPref("fastopen_enable_project_gatherer"):
            enable = self._globalPrefs.getBooleanPref("fastopen_enable_project_gatherer")
        return enable

    @property
    def pref_enable_project_dir_gatherer(self):
        enable = True
        if self._globalPrefs.hasBooleanPref("fastopen_enable_project_dir_gatherer"):
            enable = self._globalPrefs.getBooleanPref("fastopen_enable_project_dir_gatherer")
        return enable

    @property
    def pref_follow_symlinks(self):
        return self._globalPrefs.getBoolean("fastopen_follow_symlinks", True)

    @property
    def pref_history_num_entries(self):
        value = 50
        if self._globalPrefs.hasLongPref("fastopen_history_num_entries"):
            value = self._globalPrefs.getLongPref("fastopen_history_num_entries")
        return value
    
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
    def setCurrentPlace(self, currentPlace):
        self.currentPlace = currentPlace
        self._gatherers_cache = None
    def setCurrHistorySession(self, sessionName):
        self.historySessionName = sessionName
        self._gatherers_cache = None

    #TODO: rename to gathererInfo, the current name is already inaccurate
    @property
    def gatherersAndCwds(self):
        if self._gatherers_cache is None:
            g = fastopen.Gatherers()
            cwds = []
            if self.views:
                kovg = KomodoOpenViewsGatherer(self.views)
                if self.pref_enable_open_views_gatherer:
                    g.append(kovg)
                cwds = list(kovg.cwds)
            if self.currentPlace and self.currentPlace.startswith("file://"):
                from uriparse import URIToLocalPath
                cwds.append(URIToLocalPath(self.currentPlace))
            if self.pref_enable_project_gatherer and self.project:
                g.append(fastopen.CachingKomodoProjectGatherer(
                    UnwrapObject(self.project),
                    self.pref_enable_project_dir_gatherer,
                    self.pref_follow_symlinks))
            if self.pref_enable_cwd_gatherer and cwds:
                g.append(fastopen.DirGatherer("cwd", cwds, True,
                    self.pref_path_excludes))
            if self.pref_enable_go_tool:
                gog = fastopen.GoGatherer()
                g.append(gog)
                dirShortcuts = gog.getShortcuts()
            else:
                dirShortcuts = None
            if self.pref_enable_history_gatherer:
                g.append(KomodoHistoryURIsGatherer(self.historySessionName,
                    self.pref_history_num_entries))
            self._gatherers_cache = (g, cwds, dirShortcuts)
        return self._gatherers_cache

    def findFiles(self, query):
        """Asynchronously search with the given query."""
        gatherers, cwds, dirShortcuts = self.gatherersAndCwds
        self.driver.search(query, gatherers, cwds, self.pref_path_excludes,
            dirShortcuts, self.resultsView)

    def findFileSync(self, query, timeout):
        """Synchronously search with the given query and return the first hit.
        
        @param query {str} The query string with which to search.
        @param timeout {float} A number of seconds to wait for that first
            hit. If None, then don't timeout.
        """
        gatherers, cwds, dirShortcuts = self.gatherersAndCwds
        return self.driver.searchOne(query, gatherers, cwds,
            self.pref_path_excludes, dirShortcuts, timeout)

    def abortSearch(self):
        self.driver.abortSearch()

    def relavatizePath(self, path):
        """Return the shortest path based on the enabled gathers."""
        if not isabs(path):
            return path
        possibile_paths = []
        gatherers, cwds, dirShortcuts = self.gatherersAndCwds

        if "HOME" in os.environ:
            home = os.environ["HOME"]
            if path.startswith(home):
                possibile_paths.append("~" + path[len(home):])
        if dirShortcuts:
            for alias, dirpath in dirShortcuts.items():
                if path.startswith(dirpath):
                    # Ensure the path matches against a directory boundary,
                    # bug 89371.
                    if len(path) == len(dirpath) or path[len(dirpath)] in "/\\":
                        possibile_paths.append(alias + path[len(dirpath):])
        for gatherer in gatherers:
            if isinstance(gatherer, fastopen.CachingKomodoProjectGatherer):
                if path.startswith(gatherer.base_dir):
                    possibile_paths.append("{%s}%s" % (gatherer.project_name,
                                            path[len(gatherer.base_dir):]))

        bestpath = path
        for path in possibile_paths:
            if len(path) < len(bestpath):
                bestpath = path
        return bestpath

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
    
    def __init__(self, sessionName, numEntries=50):
        self.sessionName = sessionName
        self.numEntries = numEntries
        try:
            koHistorySvc = components.classes["@activestate.com/koHistoryService;1"].\
                getService(components.interfaces.koIHistoryService)
        except COMException:
            self._koHistorySvcProxy = None
        else:
            self._koHistorySvcProxy = \
                getProxyForObject(1, components.interfaces.koIHistoryService,
                                  koHistorySvc, PROXY_SYNC|PROXY_ALWAYS)

    _cachedHits = None
    def gather(self):
        if self._koHistorySvcProxy is not None:
            if self._cachedHits is None:
                self._cachedHits = []
                for uri in self._koHistorySvcProxy.recent_uris_as_array(
                        self.numEntries, self.sessionName):
                    if not uri.startswith("file://"):
                        #TODO: Is this a sufficient guard for possible history URLs?
                        continue
                    hit = KomodoHistoryURIHit(uri)
                    self._cachedHits.append(hit)
            
            for hit in self._cachedHits:
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
                    koFileEx = view.koDoc.file
                    if koFileEx:
                        uri = koFileEx.URI
                        isLocal = koFileEx.isLocal
                    else:
                        uri = None
                        isLocal = False
                    path = view.koDoc.displayPath
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
    
