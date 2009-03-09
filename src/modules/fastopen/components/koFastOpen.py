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
import pprint

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
    
    def searchStarted(self):
        self.uiDriver.searchStarted()
    def searchAborted(self):
        self.uiDriver.searchAborted()
    def searchCompleted(self):
        self.uiDriver.searchCompleted()
    
    def getSelectedPaths(self): 
        paths = []
        for i in range(self.selection.getRangeCount()):
            start, end = self.selection.getRangeAt(i)
            for row_idx in range(start, end+1):
                paths.append(self._rows[row_idx].path)
        return paths
 
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

    def selectionChanged(self):
        index = self.selection.currentIndex
        try:
            path = self._rows[index].path
        except IndexError:
            path = ""
        self.uiDriver.setCurrPath(path)

    def getImageSrc(self, row, column):
        try:
            ext = self._rows[row].ext
        except IndexError:
            pass
        else:
            return "moz-icon://%s?size=16" % (ext or ".txt")
        #return "chrome://komodo/skin/images/folder-open.png"


class KoFastOpenSession(object):
    _com_interfaces_ = [components.interfaces.koIFastOpenSession]
    _reg_desc_ = "Fast Open search session"
    _reg_clsid_ = "{16d03764-c4b2-5342-a091-78fe11057d43}"
    _reg_contractid_ = "@activestate.com/koFastOpenSession;1"

    # Number of secs to wait for previous search to stop.
    SEARCH_STOP_TIMEOUT = 90

    resultsView = None
    uiDriver = None
    project = None
    cwd = None

    def __init__(self, driver, uiDriver):
        self.driver = driver
        self.uiDriver = uiDriver
        self.resultsView = KoFastOpenTreeView(uiDriver)
        self.uiDriver.setTreeView(self.resultsView)

    _gatherers_cache_key = None
    _gatherers_cache = None
    @property
    def gatherers(self):
        key = (self.project, self.cwd)
        if self._gatherers_cache is None or self._gatherers_cache_key != key:
            # Re-generate the gatherers struct.
            g = fastopen.Gatherers()
            if self.cwd:
                g.append(fastopen.DirGatherer("cwd", self.cwd))
            if self.project:
                g.append(fastopen.ProjectGatherer(UnwrapObject(self.project)))
            self._gatherers_cache_key = key
            self._gatherers_cache = g
        return self._gatherers_cache

    def findFiles(self, query):
        self.driver.search(self.gatherers, query, self.resultsView)

class KoFastOpenService(object):
    _com_interfaces_ = [components.interfaces.koIFastOpenService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Fast Open service"
    _reg_clsid_ = "{1ffc88c7-b388-c844-b60b-e1f04bfb86d3}"
    _reg_contractid_ = "@activestate.com/koFastOpenService;1"

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

