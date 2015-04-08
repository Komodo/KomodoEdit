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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

"""KoPlacesTreeView - The back-end for the tree view for new projects (places)
"""

import traceback
import os
import sys
import re
import fileutils
import logging
import json
import shutil
import fnmatch
import pprint
import time
import stat
import uriparse

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject

from koTreeView import TreeView
from koLanguageServiceBase import sendStatusMessage
from koUnicodeEncoding import autoDetectEncoding
log = logging.getLogger("koPlaceTreeView")
#log.setLevel(logging.DEBUG)


#---- Global functions
def _umaskFromPermissions(rfi):
    umask = 0
    fileEx = components.interfaces.koIFileEx
    # Generate 0755 for directories, 0644 for files
    if rfi.isReadable():
        umask += (fileEx.PERM_IRUSR | fileEx.PERM_IRGRP | fileEx.PERM_IROTH)
    if rfi.isWriteable():
        umask += fileEx.PERM_IWUSR
    if rfi.isExecutable():
        umask += (fileEx.PERM_IXUSR | fileEx.PERM_IXGRP | fileEx.PERM_IXOTH)
    return umask


class _kplBase(object):
    """
    Each row has these fields:
    - level
    - uri
    - _name : init None, managed by property name
    - _path : init None, managed by property path
    - _koFile: init None, managed by property koFile, instance of koFileEx
    - properties: init None
    - cellImageURL: used for displaying moz-icon (native file) images
    - isContainer: class attribute
    - isOpen: should be called on _kplFolder only
    - childNodes: should be called on _kplFolder only
    - image_icon (off class)
    - original_image_icon
    - busy_count
    """
    cellImageURL = None
    def __init__(self, level, uri):
        self.level = level
        self.uri = uri
        self.properties = None
        self.propertyNames = None
        self._koFile = None # koIFileEx
        self.original_image_icon = self.image_icon
        self.busy_count = 0
        # Calc the others when we need them
        self._name = self._path = self._uri = None
        
    def getCellPropertyNames(self, col_id):
        if self.propertyNames is None:
            self.propertyNames = self.getCellPropertyNames_aux(col_id)
        return self.propertyNames

    def getCellPropertyNames_aux(self, col_id):
        if col_id == 'name':
            koFile = self.koFile
            if not koFile.exists:
                return ['missing_file_symlink']
            else:
                return [self.image_icon]
        return []

    _slash_re = re.compile(r'[/\\]')

    @property
    def koFile(self):
        if self._koFile is None:
            self._koFile = components.classes["@activestate.com/koFileService;1"].\
                           getService(components.interfaces.koIFileService).\
                           getFileFromURI(self.uri)
####            qlog.debug("koFile getter: file:%s, isLink:%r",
####                       self._koFile.path,
####                       self._koFile.isSymlink)
                       
        return self._koFile

    @property
    def name(self):
        if self._name is None:
            self._name = self.koFile.baseName
        return self._name

    @name.setter
    def name(self, val):
        self._name = val
        
    @property
    def path(self):
        if self._path is None:
            self._path = self.koFile.path
        return self._path

    @path.setter
    def path(self, val):
        self._path = val

    def matchesPath(self, path):
        # Don't instantiate koFileEx on every row while trying to match path
        if self._path is None:
            lastPart = os.path.basename(self.uri)
            if lastPart not in path:
                return False
        return self.path == path            

    def getName(self):
        return self.name

    #def getPath(self):
    #    return self.path

    def getURI(self):
        return self.uri

    getUri = getURI   # Because of how accessors are calculated

    # Getters from the treeview
    def getCellText(self, col_id):
        methodName = "get" + col_id.capitalize()
        return getattr(self, methodName)()

    def restore_icon(self):
        if self.busy_count > 0:
           self.busy_count -= 1
        if self.busy_count == 0:
            self.image_icon = self.original_image_icon

    def show_busy(self):
        self.image_icon = "places_busy"
        self.busy_count += 1


class _kplFolder(_kplBase):
    image_icon = 'places_folder'
    isContainer = True
    def __init__(self, level, uri):
        _kplBase.__init__(self, level, uri)
        self.childNodes = [_kplPlaceholder(level + 1, None)]
        self.__isOpen = self._nodeOpenStatusFromName.get(uri, False)

    @property
    def koFile(self):
        if self._koFile is None:
            # We only want to cause file status checks on the folder if the
            # folder is open, otherwise we just want an uncached koIFileEx which
            # will not perform any file status checking.
            if self.__isOpen:
                self._koFile = components.classes["@activestate.com/koFileService;1"].\
                               getService(components.interfaces.koIFileService).\
                               getFileFromURI(self.uri)
            else:
                self._koFile = components.classes["@activestate.com/koFileService;1"].\
                               getService(components.interfaces.koIFileService).\
                               getFileFromURINoCache(self.uri)
####            qlog.debug("koFile getter: file:%s, isLink:%r",
####                       self._koFile.path,
####                       self._koFile.isSymlink)
                       
        return self._koFile

    @property
    def isOpen(self):
        return self.__isOpen
    @isOpen.setter
    def isOpen(self, value):
        if self.__isOpen != value:
            self.__isOpen = value
            # Open state has changed - reset the koFile.
            self._koFile = None

    def getCellPropertyNames_aux(self, col_id):
        if col_id == 'name':
            if self.image_icon == 'places_busy':
                return ['places_busy']
            baseName = self.image_icon
            if self.isOpen:
                return [baseName + "_open"]
            else:
                return [baseName + "_closed"]
        return []

class _kplNonFolder(_kplBase):
    isOpen = False
    isContainer = False
    childNodes = []

class _kplFile(_kplNonFolder):
    image_icon = 'places_file'
    _cellImageURL = None

    @property
    def cellImageURL(self):
        if self._cellImageURL is None:
            self._cellImageURL = "koicon://" + self.koFile.baseName + "?size=16"
        return self._cellImageURL

class _kplOther(_kplNonFolder):
    image_icon = 'places_other'
    
class _kplPlaceholder(_kplNonFolder):
    image_icon = None
    
_PLACE_FOLDER = 1
_PLACE_FILE = 2
_PLACE_OTHER = 3
_PLACE_PLACEHOLDER = 4 # Not used

placeObject = {
    _PLACE_FOLDER : _kplFolder,
    _PLACE_FILE   : _kplFile,
    _PLACE_OTHER  : _kplOther,
}

class _KoPlaceItem(object):
    MAX_DIR_AGE = 60 * 60  # 1 HOUR
    def __init__(self, _type, uri, name, isSymbolicLink=False):
        self.type = _type
        self.uri = uri
        self.name = name
        self.lcName = name.lower()
        self.isSymbolicLink = isSymbolicLink
        if _type == _PLACE_FOLDER:
            self.childNodes = []
        else:
            self.childNodes = None
        self.lastUpdated = -1

    def __repr__(self):
        basePart = "<_KoPlaceItem(type:%r, uri:%s" % (self.type, self.uri)
        if self.type == _PLACE_FOLDER:
            basePart += ", lastUpdated:%g, \n  childNodes:%s\n" % (self.lastUpdated, [repr(x) for x in self.childNodes])
        basePart += ">"
        return basePart

    def needsRefreshing(self):
        return self.lastUpdated == -1 or time.time() - self.lastUpdated > self.MAX_DIR_AGE

    def markForRefreshing(self):
        self.lastUpdated = -1

import threading
from Queue import Queue

# some constants used for live folders
# from koKPFTreeView.p.py
_rebuildDirFlags = \
    components.interfaces.koIFileNotificationService.FS_FILE_CREATED | \
    components.interfaces.koIFileNotificationService.FS_FILE_DELETED | \
    components.interfaces.koIFileNotificationService.FS_UNKNOWN
_rebuildParentFlags = \
    components.interfaces.koIFileNotificationService.FS_DIR_CREATED | \
    components.interfaces.koIFileNotificationService.FS_DIR_DELETED
_createdFlags = \
    components.interfaces.koIFileNotificationService.FS_FILE_CREATED | \
    components.interfaces.koIFileNotificationService.FS_DIR_CREATED
_deletedFlags = \
    components.interfaces.koIFileNotificationService.FS_FILE_DELETED | \
    components.interfaces.koIFileNotificationService.FS_DIR_DELETED
_rebuildFlags = _rebuildDirFlags | _rebuildParentFlags
_notificationsToReceive = _rebuildFlags | \
    components.interfaces.koIFileNotificationService.FS_FILE_MODIFIED

class _UndoCommand():
    def __init__(self):
        self.clearArgs()

    def getArgs(self):
        return self.fromPath, self.toPath, self.isLocal
    
    def clearArgs(self):
        self.isLocal = True
        self.fromPath = self.toPath = None

    def update(self, targetFile, srcPath, isLocal):
        self.toPath = targetFile
        self.fromPath = srcPath
        self.isLocal = isLocal

    def canUndo(self):
        return self.fromPath is not None

class KoPlaceTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIPlaceTreeView,
                        components.interfaces.nsITreeView,
                        components.interfaces.koIFileNotificationObserver]
    _reg_clsid_ = "{3b4b4e60-0bbd-4efc-b118-a153b3f84166}"
    _reg_contractid_ = "@activestate.com/koPlaceTreeView;1"
    _reg_desc_ = "KoPlacesTreeView Tree View"
        
    def __init__(self, debug=None):
        TreeView.__init__(self, debug=0)
        # The model
        self._nodesForURI = {}
        self._root = None
        self._currentPlace_uri = None
        self._currentPlace_koFileEx = None
        self._rows = []
        self._watchedDirectories = set()  # Tracking filesystem changes
        self._lastSelectedRow = -1
        #TODO: Update this for each place 
        self.exclude_patterns = []
        self.include_patterns = []

        self._sortedBy = 'name'
        self.SORT_DIRECTION_NAME_NATURAL =\
            components.interfaces.koIPlaceTreeView.SORT_DIRECTION_NAME_NATURAL
        self.SORT_DIRECTION_NAME_ASCENDING =\
            components.interfaces.koIPlaceTreeView.SORT_DIRECTION_NAME_ASCENDING
        self.SORT_DIRECTION_NAME_DESCENDING =\
            components.interfaces.koIPlaceTreeView.SORT_DIRECTION_NAME_DESCENDING
        self._sortDir = self.SORT_DIRECTION_NAME_NATURAL
        self._pending_filter_requests = 0
        self._nodeOpenStatusFromName = {}
        self._isLocal = True
        self._data = {} # How threads share results

        # Map row # => requestID,
        # Used to avoid processing multiple sequential requests to refresh
        # the same row.
        self._currentRefreshRequests = {} 

        self._tree = None
        self._honorNextToggleOpenState = True
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._observerSvc.addObserver(self, "file_status", False)

        self._RCService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
                  getService(components.interfaces.koIRemoteConnectionService)
        self._nextRequestID = 0
        self._refreshOnUpdateCurrentPlace = set()
        
    def initialize(self):
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        if not prefs.hasPref("places"):
            placesPrefs = components.classes["@activestate.com/koPreferenceSet;1"].createInstance()
            prefs.setPref("places", placesPrefs)
        else:
            placesPrefs = prefs.getPref("places")
        if placesPrefs.hasPref("places-open-nodes"):
            # Shift it over into one area
            self._nodeOpenStatusFromName = {}
            oldOpenNodesPrefSet = placesPrefs.getPref("places-open-nodes")
            prefIds = oldOpenNodesPrefSet.getPrefIds()
            for prefId in prefIds:
                self._nodeOpenStatusFromName.update(json.loads(oldOpenNodesPrefSet.getStringPref(prefId)))
            pprint.pprint(self._nodeOpenStatusFromName)
            placesPrefs.deletePref("places-open-nodes")
        elif not placesPrefs.hasPref("places-open-nodes-v2"):
            self._nodeOpenStatusFromName = {}
        else:
            self._nodeOpenStatusFromName = json.loads(placesPrefs.getStringPref("places-open-nodes-v2"))
        # Make this attr work like a class variable
        _kplBase._nodeOpenStatusFromName = self._nodeOpenStatusFromName
        self.lock = threading.RLock()
        self.dragDropUndoCommand = _UndoCommand()
        self.workerThread = _WorkerThread(target=_WorkerThread.run,
                                          name="Places TreeView")
        self.workerThread.daemon = True
        self.workerThread.start()
        self.notificationSvc = components.classes["@activestate.com/koFileNotificationService;1"].\
                                    getService(components.interfaces.koIFileNotificationService)
            
    def terminate(self): # should be finalize
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        if prefs.hasPref("places-open-nodes-size"):
            lim = prefs.getLongPref("places-open-nodes-size")
        else:
            lim = 100
            prefs.setLongPref("places-open-nodes-size", lim)
        if len(self._nodeOpenStatusFromName) > lim:
            log.debug("self._nodeOpenStatusFromName has %d nodes, crop to %d",
                      len(self._nodeOpenStatusFromName), lim)
            try:
                import operator
                newDict = dict(sorted(self._nodeOpenStatusFromName.items(),
                                      key=operator.itemgetter(1), reverse=True)[:lim])
                self._nodeOpenStatusFromName = newDict
            except:
                log.exception("Problem trying to cull the list")
            
        prefs.getPref("places").setStringPref("places-open-nodes-v2",
                                  json.dumps(self._nodeOpenStatusFromName))
        self._observerSvc.removeObserver(self, "file_status")
        self.workerThread.shutdown();
        self.workerThread.join(3)
        self.set_currentPlace(None)
        self._rows = []
        self.resetDirectoryWatches()

    def observe(self, subject, topic, data):
        # Taken from koKPFTreeView
        # File Notification Handling is in fileNotification
        #qlog.debug("observe: subject:%r, topic:%r, data:%r", subject, topic, data)
        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return
        if topic == "file_status":
            #log.debug("observe: file_status: data: %s", data)
            
            # find the row for the file and invalidate it
            files = data.split("\n")
            invalidRows = sorted([i for (i,row) in enumerate(self._rows)
                                  if row.uri in files], reverse=True)
            self._tree.beginUpdateBatch()
            try:
                for row in invalidRows:
                    self._invalidateRow(row)
            finally:
                self._tree.endUpdateBatch()
        #qlog.debug("<< observe")

    # row generator interface
    def stopped(self):
        return 0

    def _addWatchForChanges(self, path):
        try:
            # This will call the fileNotification method (not 'observe'!)
            self.notificationSvc.addObserver(self, path,
                                             components.interfaces.koIFileNotificationService.WATCH_DIR,
                                             _notificationsToReceive)
        except:
            log.exception("Can't watch path: %s", path)
        
    def _removeWatchForChanges(self, path):
        self.notificationSvc.removeObserver(self, path)

    #---------------- Model for the tree view

    def getNodeForURI(self, uri):
        self.lock.acquire()
        try:
            return self._nodesForURI.get(uri, None)
        finally:
            self.lock.release()

    def setNodeForURI(self, uri, koItemNode):
        self.lock.acquire()
        try:
            self._nodesForURI[uri] = koItemNode
        finally:
            self.lock.release()
        
    def removeNodeForURI(self, uri):
        self.lock.acquire()
        try:
            del self._nodesForURI[uri]
        except KeyError:
            pass
        finally:
            self.lock.release()

    def removeSubtreeFromModelForURI(self, uri):
        koPlaceItem = self.getNodeForURI(uri)
        if not koPlaceItem: return
        self.removeSubtreeFromModelForURI_aux(koPlaceItem)
        self.removeNodeFromParent(uri)

    def removeSubtreeFromModelForURI_aux(self, koPlaceItem):
        self.lock.acquire()
        try:
            childNodes = koPlaceItem.childNodes
        finally:
            self.lock.release()

        for koChildItem in (childNodes or []):
            if not koChildItem.isSymbolicLink:
                self.removeSubtreeFromModelForURI_aux(koChildItem)
        self.removeNodeForURI(koPlaceItem.uri)
        self.lock.acquire()
        try:
            del self._nodeOpenStatusFromName[koPlaceItem.uri]
        except KeyError:
            pass
        finally:
            self.lock.release()

    def removeNodeFromParent(self, uri):
        parent_uri = self._getURIParent(uri)
        parent_node = self.getNodeForURI(parent_uri)
        if parent_node:
            self.lock.acquire()
            try:
                for (i, child_node) in enumerate(parent_node.childNodes):
                    if child_node.uri == uri:
                        #qlog.debug("removeChildNode: found %s at %d", uri, i)
                        del parent_node.childNodes[i]
                        break
                else:
                    pass
                    #qlog.debug("removeChildNode: didn't find %s in %s", uri, parent_uri)
            finally:
                self.lock.release()

    def removeNodeFromModel(self, uri):
        parent_uri = self._getURIParent(uri)
        parent_node = self.getNodeForURI(parent_uri)
        self.removeNodeFromParent(uri)
        self.removeNodeForURI(uri)
        self.lock.acquire()
        try:
            del self._nodeOpenStatusFromName[uri]
            if parent_node:
                parent_node.markForRefreshing()
        except KeyError:
            pass
        finally:
            self.lock.release()

    def _sortModel(self, uri):
        topModelNode = self.getNodeForURI(uri)
        if topModelNode is None:
            #qlog.debug("_sortModel(uri:%s) is None", uri)
            return
        self.lock.acquire()
        try:
            self._sortModel_aux(topModelNode)
        finally:
            self.lock.release()
        
    def _sortModel_aux(self, koPlaceItem):
        if not koPlaceItem.childNodes:
            return
        if not self._nodeOpenStatusFromName.get(koPlaceItem.uri, False):
            # log.debug("Node %s isn't open", koPlaceItem.uri)
            return
        # Only sort items we care about.
        #qlog.debug("_sortModel_aux: sort childNodes for %s", koPlaceItem.name)
        #qlog.debug("  orig nodes: %s", [x.name for x in koPlaceItem.childNodes])
        koPlaceItem.childNodes = self._sortItems(koPlaceItem.childNodes)
        #qlog.debug("  sorted nodes: %s", [x.name for x in koPlaceItem.childNodes])
        for subNode in koPlaceItem.childNodes:
            if not subNode.isSymbolicLink:
                #qlog.debug("go sort subNode %s", subNode.name)
                self._sortModel_aux(subNode)
            else:
                pass
                #qlog.debug("subNode %s isSymbolicLink", subNode.name)

    # These methods don't take a 'self' because of the way they're called
    # Keep them in this class for namespace purposes only.
    def _compare_item_natural(item1, item2):
        if item1[1].type == item2[1].type:
            return cmp(item1[0], item2[0])
        else:
            return cmp(item1[1].type, item2[1].type)  # folder:1, file:2

    def _compare_item_ascending(item1, item2):
        return cmp(item1[0], item2[0])

    def _compare_item_descending(item1, item2):
        return cmp(item2[0], item1[0])

    sortFuncTable = [None, _compare_item_natural, _compare_item_ascending,
                     _compare_item_descending]
    # Keep the items in sync with SORT_DIRECTION_NAME_NATURAL, etc.
    def _sortItems(self, childNodes):
        assert self._sortedBy == "name", 'sorting by %r, expected "name"' % (self._sortedBy,)
        adjustedItems = [(node.name.lower(), node) for node in childNodes]
        sortedItems = sorted(adjustedItems, cmp=self.sortFuncTable[self._sortDir])
        return [x[1] for x in sortedItems]    

    # nsIFileNotificationObserver
    # we want to receive notifications for any live folders in our view
    # the addition of observers will occur during generateRows
    #
    # This is called by doing
    # self.notificationSvc.addObserver(self, path,
    #      components.interfaces.koIFileNotificationService.WATCH_DIR,
    #      _notificationsToReceive)
    def fileNotification(self, uri, flags):
        # Pulled this from koKPFTreeView
        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return
        koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        koFileEx.URI = uri
        # bug 93336 -- Incoming URIs aren't necessarily canonical, but
        # they are after assigned to a koFileEx object.
        uri = koFileEx.URI
        #print "   path is [%r] dirname [%r]"%(koFileEx.path, koFileEx.dirName)

        dirname = koFileEx.dirName
        #log.debug("fileNotification: uri:%s, flags:0x%02x", uri, flags)
        # If we're filtering it out, do nothing.
        if not self._namePassesFilter(koFileEx.baseName, _PLACE_FILE):
            return
        if flags & _createdFlags:
            parent_uri = self._getURIParent(uri)
            index = self.getRowIndexForURI(parent_uri)
            if index != -1:
                # Refresh this directory.  refreshView will rebuild
                # the list of children and child view only if the
                # parent node is open.
                parent_node = self._rows[index]
                if not parent_node.isOpen:
                    self.onRefreshClosedRow(index)
                    return
                nextIndex = self.getNextSiblingIndex(index)
                if nextIndex == -1:
                    nextIndex = len(self._rows)
                newLevel = parent_node.level + 1
                if not self._insertNewURI(index + 1, nextIndex, uri, newLevel):
                    self.refreshView(index)
                return
            elif parent_uri == self._currentPlace_uri:
                # Insert in self._rows top-level
                if not self._insertNewURI(0, len(self._rows), uri, 0):
                    self.refreshFullTreeView()  # partly async
            else:
                log.info("**** Places: Can't find parent for created file %s", uri)
                # Bug 95132 -- handle changes and deletions that happen
                # outside the current root
                self._refreshOnUpdateCurrentPlace.add(self._endsWithSlash(parent_uri))

        elif flags & _deletedFlags:
            index = self.getRowIndexForURI(uri)
            if index != -1:
                #log.debug("fileNotification: About to remove uri %s from row %d", uri, row)
                node = self._rows[index]
                if isinstance(node, _kplFolder):
                    endIndex = self.getNextSiblingIndex(index)
                    if endIndex == -1:
                        endIndex = len(self._rows)
                else:
                    endIndex = index + 1
                for i in range(index, endIndex):
                    uri = self._rows[i].uri
                    koFileEx.URI = uri
                    self._removeWatchForChanges(koFileEx.path)
                    self.removeNodeFromModel(uri)
                del self._rows[index:endIndex]
                self._tree.rowCountChanged(index, index - endIndex)
                self.resetDirectoryWatches()
            elif uri == self._currentPlace_uri:
                self._moveToExistingPlace()
            else:
                # Bug 95132 -- track additions and deletions that happen
                # outside the current root, so we know which views will
                # need to be refreshed as they're encountered.
                # Just store directories, because we don't need to
                # track individual files.  View will be refreshed when a new
                # place (which is always the URI for a directory) starts with
                # the pending uri
                if flags & components.interfaces.koIFileNotificationService.FS_FILE_DELETED:
                    uri = self._getURIParent(uri) or uri
                self._refreshOnUpdateCurrentPlace.add(self._endsWithSlash(uri))
        else:
            # this is a modification change, just invalidate rows
            index = self.getRowIndexForURI(uri)
            if index >= 0:
                self._invalidateRow(index)

    def _insertNewURI(self, startIndex, endIndex, uri, level):
        #log.debug("_insertNewURI(startIndex:%d, endIndex:%d, uri:%s, level:%d)", startIndex, endIndex, uri, level)
        try:
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = uri
            if koFileEx.isDirectory:
                nodeType = _PLACE_FOLDER
                nodeClass = _kplFolder
            else:
                nodeType = _PLACE_FILE
                nodeClass = _kplFile
            newNode = placeObject[nodeType](level, uri)
            lc_uri = uri.lower()
            self._finishGettingItem(uri, koFileEx.baseName, nodeType)
            allow_case_insensitivity = not sys.platform.startswith("linux")
            for i in range(startIndex, endIndex):
                node = self._rows[i]
                current_lc_uri = node.uri.lower()
                if node.level > level:
                    # bug 93133: we can never insert a new node at a
                    # row that's occupied by a child of one of
                    # the new node's siblings.  Otherwise it will look like
                    # the new node has another parent's child nodes.
                    pass
                elif (node.uri == uri
                    or (allow_case_insensitivity and lc_uri == current_lc_uri)): 
                    return True
                elif self._sortDir == self.SORT_DIRECTION_NAME_NATURAL:
                    # Group folders with folders, files with files
                    if isinstance(node, nodeClass):
                        # They're the same type
                        if lc_uri < current_lc_uri:
                            break
                    elif isinstance(node, _kplFile):
                        #log.debug("insert folder before first file")
                        # Insert the new folder here, before first file
                        break
                elif self._sortDir == self.SORT_DIRECTION_NAME_ASCENDING:
                    if lc_uri < current_lc_uri:
                        break
                elif lc_uri > current_lc_uri:
                    break
            else:
                # When you fall off the end of i in range(a, b), i == b - 1
                i = endIndex
            self._rows.insert(i, newNode)
            self._tree.rowCountChanged(i, 1)
            if nodeType == _PLACE_FOLDER:
                self._addWatchForChanges(koFileEx.path)
            return True
        except:
            log.exception("_insertNewURI(%d, %d, %s, %d) exception:",
                          startIndex, endIndex, uri, level)
            return False

    def _invalidateRow(self, rowIndex):
        self._updateFileProperties(rowIndex)
        self._tree.invalidateRow(rowIndex)

    def _busyRow(self, rowIndex, rowNode=None):
        (rowNode or self._rows[rowIndex]).show_busy()
        self._tree.invalidateRow(rowIndex)

    def _fileStillExists(self, koFileEx):
        return os.path.exists(koFileEx.path)

    def safe_isLocal(self):
        self.lock.acquire()
        try:
            return self._isLocal
        finally:
            self.lock.release()

    def _moveToExistingPlace(self):
        if not self.safe_isLocal():
            #TODO: Handle remote places... (unlikely, because we don't have notifications)
            self.closePlace()
            return
        koFileEx = self._currentPlace_koFileEx
        if self._fileStillExists(koFileEx):
            return
        while True:
            dirName = koFileEx.dirName
            if not dirName or dirName == koFileEx.path:
                # Can't go up any higher
                log.info("_moveToExistingPlace: hit the top")
                # This is just a sanity check to break a loop.
                self.closePlace()
                break
            koFileEx.path = dirName
            if os.path.exists(koFileEx.path):
                self._observerSvc.notifyObservers(None, 'visit_directory_proposed', koFileEx.path)
                break

    #---- Change places.
    
    def get_currentPlace(self):
        return self._currentPlace_uri;
    
    def set_currentPlace(self, uri, callback=None):
        if self._currentPlace_uri is not None:
            self.closePlace()
        if uri:
            self._currentPlace_uri = uri
            self._currentPlace_koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
            self._currentPlace_koFileEx.URI = uri
            if not self._currentPlace_koFileEx.exists:
                msg = "set_currentPlace: URI %s doesn't exist" % (uri,)
                log.error("%s", msg)
                self.closePlace()
                if callback:
                    callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                                      msg)
                return
            self.openPlace(uri, callback)

    def setCurrentPlaceWithCallback(self, uri, callback):
        self.set_currentPlace(uri, callback)

    def setMainFilters(self, exclude_patterns, include_patterns):
        # Run the request through the worker thread, in case other
        # processes are working.
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'exclude_patterns':exclude_patterns,
                                     'include_patterns':include_patterns}
        finally:
            self.lock.release()
        self._pending_filter_requests += 1
        self.workerThread.put(('setMainFilters',
                                {'requestID':requestID,
                                'requester':self},
                               'post_setMainFilters'))

    def _decrementCheckPendingFilters(self):
        if self._pending_filter_requests > 0:
            self._pending_filter_requests -= 1
            if self._pending_filter_requests > 0:
                return False
        return True

    _non_ws_rx = re.compile(r'\S')
    def _keepNonWSFilters(self, patternList):
        return [x for x in patternList.split(';') if x and self._non_ws_rx.search(x)]

    def post_setMainFilters(self, rv, requestID):
        exclude_patterns, include_patterns = self.getItemsByRequestID(requestID, 'exclude_patterns', 'include_patterns')
        if not self._decrementCheckPendingFilters():
            return
        self.exclude_patterns = self._keepNonWSFilters(exclude_patterns)
        self.include_patterns = self._keepNonWSFilters(include_patterns)
        self._wrap_refreshTreeOnOpen_buildTree()

    def getRowIndexForURI(self, uri):
        # First look for a match respecting case.
        for (i, row) in enumerate(self._rows):
            if uri == row.uri:
                return i
        if sys.platform.startswith("linux") and uri.startswith("file:/"):
            # Local files on a case-sensitive file system: no match
            return -1
        uri_to_find = uri.lower()
        for (i, row) in enumerate(self._rows):
            if row.uri.lower() == uri_to_find:
                return i
        return -1

    def selectURI(self, uri):
        """If the given URI is one of the current rows in the tree,
        then select it.
        
        Note: This will *not* open directory nodes in the tree to
        find a possible row for the given URI.
        
        @param uri {str} The URI to select.
        """
        if len(self._rows) == 0:
            return
        index = self.getRowIndexForURI(uri)
        if index >= 0:
            self.selection.currentIndex = index
            self.selection.select(index)
            self._tree.ensureRowIsVisible(index)
            return

    def getURIForRow(self, index):
        return self._rows[index].uri

    def _targetFileExists(self, localFinalTargetPath, targetPath, srcBasename,
                          isDir_OutVal):
        if not self.safe_isLocal():
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            finalTargetPath = targetPath + "/" + srcBasename
            rfi = conn.list(finalTargetPath, True)
            isDir_OutVal['value'] = rfi and rfi.isDirectory()
            return rfi # Just want a boolean
        elif os.path.exists(localFinalTargetPath):
            isDir_OutVal['value'] = os.path.isdir(localFinalTargetPath)
            return True

    def _targetFileExistsByFileExObj(self, targetFileEx, isDir_OutVal):
        path = targetFileEx.path
        if not self.safe_isLocal():
            conn = self._RCService.getConnectionUsingUri(targetFileEx.URI)
            rfi = conn.list(path, True)
            isDir_OutVal['value'] = rfi and rfi.isDirectory()
            return rfi # Just want a boolean
        elif os.path.exists(path):
            isDir_OutVal['value'] = os.path.isdir(path)
            return True

    def treeOperationWouldConflict(self, srcIndex, targetIndex, copying):
        srcNode = self._rows[srcIndex]
        srcBasename = srcNode.name
        srcPath = srcNode.path
        targetNode = self._rows[targetIndex]
        targetPath = targetNode.path
        finalTargetPath = self.safe_isLocal() and os.path.join(targetPath, srcBasename) or (targetPath + "/" + srcBasename)
        isDir_OutVal = {}

        if self.getParentIndex(srcIndex) == targetIndex:
            if copying:
                res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
            else:
                res = components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR
        elif self._targetFileExists(finalTargetPath, targetPath,
                                    srcBasename, isDir_OutVal):
            if isDir_OutVal['value']:
                # We support copying directories with a merge, but not moving them.
                if copying:
                    return components.interfaces.koIPlaceTreeView.COPY_MOVE_OK, None, None
                res = components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR
            elif copying:
                res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
            else:
                res = components.interfaces.koIPlaceTreeView.MOVE_OTHER_DIR_FILENAME_CONFLICT
        else:
            return components.interfaces.koIPlaceTreeView.COPY_MOVE_OK, None, None
        srcFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
        finalTargetFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
        if self.safe_isLocal():
            srcFileInfo.path = srcPath
            finalTargetFileInfo.path = finalTargetPath
        else:
            srcFileInfo.URI = srcNode.uri
            finalTargetFileInfo.URI = targetNode.uri + "/" + srcBasename
        return res, srcFileInfo, finalTargetFileInfo

    def treeOperationWouldConflictByURI(self, srcIndex, targetURI, copying):
        """
        This is called when we're drag/dropping a node onto the root node,
        which doesn't live in the main tree view.
        """
        srcNode = self._rows[srcIndex]
        finalTargetFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
        finalTargetFileInfo.URI = targetURI + "/" + srcNode.name
        isDir_OutVal = {}

        if srcNode.level == 0:
            if copying:
                res = components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR
            else:
                res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
        elif self._targetFileExistsByFileExObj(finalTargetFileInfo,
                                               isDir_OutVal):
            if isDir_OutVal['value']:
                # We support copying directories with a merge, but not moving them.
                if copying:
                    return components.interfaces.koIPlaceTreeView.COPY_MOVE_OK, None, None
                res = components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR
            elif copying:
                res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
            else:
                res = components.interfaces.koIPlaceTreeView.MOVE_OTHER_DIR_FILENAME_CONFLICT
        else:
            return components.interfaces.koIPlaceTreeView.COPY_MOVE_OK, None, None
        
        srcFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
        srcFileInfo.URI = srcNode.uri
        return res, srcFileInfo, finalTargetFileInfo

    def _targetIsParent(self, srcURI, targetURI):
        srcURIParent = self._getURIParent(srcURI)
        return srcURIParent == targetURI

    def _srcContainsTarget(self, srcURI, targetURI):
        return targetURI.startswith(srcURI)

    def treeOperationWouldConflict_MultipleSrc(self, srcURIs, targetURI, copying):
        statuses = []
        srcKoExFiles = []
        destKoExFiles = []
        for srcURI in srcURIs:
            srcFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
            srcFileInfo.URI = srcURI
            srcBaseName = srcFileInfo.baseName
            
            finalTargetFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                                  createInstance(components.interfaces.koIFileEx)
            finalTargetFileInfo.URI = targetURI + "/" + srcBaseName
            isDir_OutVal = {}
            if self._targetIsParent(srcURI, targetURI):
                if copying:
                    res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
                else:
                    res = components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR
            elif self._targetFileExistsByFileExObj(finalTargetFileInfo,
                                                   isDir_OutVal):
                if isDir_OutVal['value']:
                    # We support copying directories with a merge, but not moving them.
                    if not srcFileInfo.isDirectory:
                        res = components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR
                    elif copying:
                        res = components.interfaces.koIPlaceTreeView.COPY_MOVE_OK
                    else:
                        res = components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR
                elif copying:
                    res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
                else:
                    res = components.interfaces.koIPlaceTreeView.MOVE_OTHER_DIR_FILENAME_CONFLICT
            elif self._srcContainsTarget(srcURI, targetURI):
                res = components.interfaces.koIPlaceTreeView.SRC_CONTAINS_TARGET
            else:
                res = components.interfaces.koIPlaceTreeView.COPY_MOVE_OK

            statuses.append(res)
            srcKoExFiles.append(srcFileInfo)
            destKoExFiles.append(finalTargetFileInfo)

        return statuses, srcKoExFiles, destKoExFiles

    def _targetIsChildOfSource(self, srcIndex, targetIndex):
        if targetIndex < srcIndex:
            return False
        if self._rows[targetIndex].level <= self._rows[srcIndex].level:
            return False
        nextSib = self.getNextSiblingIndex(srcIndex)
        if nextSib == -1:
            return True
        return srcIndex < targetIndex < nextSib

    def _getURIParent(self, uri):
        return uri[:uri.rindex("/")]

    def _endsWithSlash(self, uri):
        if uri[-1] != "/":
            return uri + "/"
        return uri

    def _copyMoveToChildSanityCheck(self, srcURI, targetURI, copying):
        if targetURI.startswith(self._endsWithSlash(srcURI)):
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  "Can't %s a folder (%s) into one of its own sub-folders (%s)" %
                                  ((copying and "copy") or "move",
                                   srcURI, targetURI))

    def _copyMoveSanityChecks(self, srcURI, targetURI, copying):
        if self._getURIParent(srcURI) == targetURI:
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                  "Can't copy/move an item on to its own container.");
        return self._copyMoveToChildSanityCheck(srcURI, targetURI, copying)
        
    def doTreeOperation(self, srcURI, targetURI, targetIndex, copying,callback):
        targetNode = self._rows[targetIndex]
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'copying':copying,
                                     'srcURI': srcURI,
                                     'targetURI': targetURI,
                                     'targetIndex': targetIndex,
                                     'final_msg': '',
                                     'callback': callback,
                                    }
        finally:
            self.lock.release()
        self._copyMoveSanityChecks(srcURI, targetURI, copying)

        #srcNode.show_busy()
        #self._tree.invalidateRow(srcIndex)
        self._busyRow(targetIndex, targetNode)
        #log.debug("%s %s %s", copying and "copy" or "move", srcPath, targetDirPath)
        self.workerThread.put(('doTreeOperation_WorkerThread',
                               {'requestID':requestID,
                                'requester':self},
                               'post_doTreeOperation'))

    def post_doTreeOperation(self, rv, requestID):
        copying, srcURI, targetURI, oldTargetIndex, \
            finalMsg, updateTargetTree, callback = self.getItemsByRequestID(
                requestID, 'copying', 'srcURI', 'targetURI',
                'targetIndex', 'finalMsg',
                'updateTargetTree', 'callback')
        # Restore busy nodes.
        srcIndex = self.getRowIndexForURI(srcURI)
        srcNode = (srcIndex != -1 and self._rows[srcIndex]) or None
        if srcNode:
            srcNode.restore_icon()
            
        targetNode = None
        try:
            targetNode = self._rows[oldTargetIndex]
            if targetNode.uri != targetURI:
                targetNode = None
            else:
                targetIndex = oldTargetIndex
        except IndexError:
            pass
        if targetNode is None:
            targetIndex = self.getRowIndexForURI(targetURI)
            targetNode = (targetIndex != -1 and self._rows[targetIndex]) or None
        if targetNode:
            targetNode.restore_icon()
        if rv:
            log.error("post_doTreeOperation: %s", rv)
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                              rv)
            return
        elif copying and not updateTargetTree:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        elif srcIndex == -1 or targetIndex == -1:
            # Things to do?
            self._tree.invalidate()
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
            
        # The worker thread updated the models; here we update the views.
        firstVisibleRow = self._tree.getFirstVisibleRow()
        parentSrcIndex = self.getParentIndex(srcIndex)
        parentNextIndex = self.getNextSiblingIndex(parentSrcIndex)
        if parentNextIndex == -1:
            parentNextIndex = len(self._rows)
        targetNextIndex = self.getNextSiblingIndex(targetIndex)
        if targetNextIndex == -1:
            targetNextIndex = len(self._rows)
        # Remember to manipulate higher-numbered tree segments first.
        # Also the two subtrees can't overlap
        if parentSrcIndex == -1:
            # We moved one of the top-level items, so just rebuild the
            # whole tree.
            #TODO: Optimize to minimize # of changed rows.
            self._wrap_refreshTreeOnOpen_buildTree()
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        assert((parentSrcIndex > targetIndex
                and parentSrcIndex > targetNextIndex)
               or (parentSrcIndex < targetIndex
                and parentNextIndex < targetIndex))
        #XXX: Track the original srcIndex to determine when this is true.
        doInvalidate = True
        if parentSrcIndex > targetIndex:
            self._finishRefreshingView(parentSrcIndex, parentNextIndex,
                                       doInvalidate, self._rows[parentSrcIndex],
                                       firstVisibleRow)
        self._finishRefreshingView(targetIndex, targetNextIndex, doInvalidate,
                                   targetNode,
                                   firstVisibleRow)
        if parentSrcIndex < targetIndex:
            self._finishRefreshingView(parentSrcIndex, parentNextIndex,
                                       doInvalidate, self._rows[parentSrcIndex],
                                       firstVisibleRow)
        callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                          "")

    def doTreeOperationToRootNode(self, srcIndex, targetURI, copying, callback):
        """TODO:
        If the source is in SCC, do the appropriate SCC operations on it.
        
        This is async, which is good.
        """
        srcNode = self._rows[srcIndex]
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'copying':copying,
                                     'srcIndex': srcIndex,
                                     'srcNode': srcNode,
                                     'targetURI': targetURI,
                                     'final_msg': '',
                                     'callback': callback,
                                    }
        finally:
            self.lock.release()
        self._busyRow(srcIndex, srcNode)
        #TODO: Make the top-node look busy
        #log.debug("%s %s %s", copying and "copy" or "move", srcPath, targetDirPath)
        if not copying and srcNode.level == 0:
            log.debug("Can't copy/move an item on to its own container.")
            return
        self.workerThread.put(('doTreeOperation_WorkerThread',
                               {'requestID':requestID,
                                'requester':self},
                               'post_doTreeOperationToRootNode'))

    def post_doTreeOperationToRootNode(self, rv, requestID):
        copying, srcIndex, originalSrcNode, targetURI,\
            finalMsg, updateTargetTree, callback = self.getItemsByRequestID(
                requestID, 'copying', 'srcIndex', 'srcNode', 'targetURI',
                'finalMsg', 'updateTargetTree', 'callback')
        # Restore busy nodes.
        fixedSrcIndex, fixedSrcNode = \
           self._postRequestCommonNodeHandling(originalSrcNode, srcIndex,
                                               "post_doTreeOperationToRootNode")
        if finalMsg:
            log.error("post_doTreeOperationToRootNode: %s", finalMsg)
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                              finalMsg)
            return
        elif copying and not updateTargetTree:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        elif fixedSrcIndex == -1:
            # Things to do?
            self._tree.invalidate()
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        elif fixedSrcIndex != srcIndex:
            doInvalidate = True
            srcIndex = fixedSrcIndex
            srcNode = self._rows[srcIndex]
        else:
            doInvalidate = False
            srcNode = originalSrcNode
            
        # The worker thread updated the models; here we update the views.
        firstVisibleRow = self._tree.getFirstVisibleRow()
        if srcIndex == 0:
            parentSrcIndex = 0
        else:
            parentSrcIndex = self.getParentIndex(srcIndex)
            if parentSrcIndex == -1:
                log.error("Unexpected parent(srcIndex:%d) => -1", srcIndex)
                return
        
        # Remember to manipulate higher-numbered tree segments first.
        # Also the two subtrees can't overlap
        self._wrap_refreshTreeOnOpen_buildTree()
        callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                          "")
        
    def doTreeCopyWithDestNameAndURI(self, srcURI, targetURI, targetIndex, newPath, callback):
        targetNode = self._rows[targetIndex]
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'srcURI': srcURI,
                                     'targetURI': targetURI,
                                     'targetIndex': targetIndex,
                                     'newPath': newPath,
                                     'callback': callback,
                                    }
        finally:
            self.lock.release()
        self._copyMoveToChildSanityCheck(srcURI, targetURI, True)

        self._busyRow(targetIndex, targetNode)
        #log.debug("%s %s %s", "copy", srcNode.path, targetNode.path)
        self.workerThread.put(('doTreeCopyWithDestNameAndURI_WorkerThread',
                               {'requestID':requestID,
                                'requester':self},
                               'post_doTreeCopyWithDestNameAndURI'))
        
    def post_doTreeCopyWithDestNameAndURI(self, rv, requestID):
        srcURI, targetURI, targetIndex, \
            newPath, callback = self.getItemsByRequestID(
                requestID, 'srcURI', 'targetURI', 'targetIndex',
                'newPath', 'callback')

        targetNode = None
        try:
            targetNode = self._rows[targetIndex]
            if targetNode.uri != targetURI:
                targetNode = None
        except IndexError:
            pass
        if targetNode is None:
            targetIndex = self.getRowIndexForURI(targetURI)
            targetNode = (targetIndex != -1 and self._rows[targetIndex]) or None
        if targetNode:
            targetNode.restore_icon()
        
        if rv and callback:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                              rv)

    def canUndoTreeOperation(self):
        self.lock.acquire()
        try:
            return self.dragDropUndoCommand.canUndo()
        finally:
            self.lock.release()

    def do_undoTreeOperation(self):
        self.lock.acquire()
        try:
            fromPath, toPath, isLocal = self.dragDropUndoCommand.getArgs()
            self.dragDropUndoCommand.clearArgs()
        finally:
            self.lock.release()
        if isLocal:
            shutil.move(toPath, fromPath)
            fromDir = os.path.dirname(fromPath)
            toDir = os.path.dirname(toPath)
        else:
            conn = self._RCService.getConnectionUsingUri(fromPath)
            fromFileEx = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
            fromFileEx.URI = fromPath
            toFileEx = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
            toFileEx.URI = toPath
            conn.rename(toFileEx.path, fromFileEx.path)
            fromDir = fromFileEx.dirName
            toDir = toFileEx.dirName
        fromIndex = self._lookupPath(fromDir)
        toIndex = self._lookupPath(toDir)
        if fromIndex > toIndex:
            self.refreshView(fromIndex)
            if toIndex > -1:
                self.refreshView(toIndex)
        else:
            self.refreshView(toIndex)
            if fromIndex != -1:
                self.refreshView(fromIndex)
            
    def _lookupPath(self, path):
        for (i, row) in enumerate(self._rows):
            if row.matchesPath(path):
                return i
        return -1
        
    #---- End remote file copying
                
    def _getTargetIndex(self, newBaseName, targetIndex):
        targetNode = self._rows[targetIndex]
        # Figure out where we're going to place the new node
        # Work in terms of the original nodes
        targetNodeFirstChildIndex = targetIndex + 1
        targetNodeLastChildIndex = self.getNextSiblingIndex(targetIndex)
        newBaseName_lc = newBaseName.lower()
        if targetNodeLastChildIndex == -1:
            targetNodeLastChildIndex = len(self._rows)
        targetLevel = targetNode.level + 1
        for i in range(targetNodeFirstChildIndex, targetNodeLastChildIndex):
            candidateNode = self._rows[i]
            if (candidateNode.level == targetLevel
                and candidateNode.name.lower() > newBaseName_lc):
                return i
        else:
            log.debug("Must be the highest node at this level")
            return targetNodeLastChildIndex

    def closePlace(self):
        if self._tree is None:
            # We're closing a window, no point updating the tree,
            # as it no longer exists.
            return
        lenBefore = len(self._rows)
        self._rows = []
        self.resetDirectoryWatches()
        self._tree.rowCountChanged(0, -lenBefore)
        self._currentPlace_uri = None
        self._currentPlace_koFileEx = None
        self.lock.acquire()
        try:
            self.dragDropUndoCommand.clearArgs()
        finally:
            self.lock.release()
        
        
    def openPlace(self, uri, callback=None):
        #qlog.debug(">> openPlace(uri:%s)", uri)
        placeFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        placeFileEx.URI = uri
        if (not placeFileEx.dirName
            and not placeFileEx.path
            and not uri.endswith("/")):
            # Bug 92121: URIs like ftp://ftp.mozilla.org have no
            # associated path info.
            uri += "/"
            placeFileEx.URI = uri
        self.lock.acquire()
        try:
            isLocal = self._isLocal = placeFileEx.isLocal
        finally:
            self.lock.release()
        if placeFileEx.isFile:
            placeFileEx.path = placeFileEx.dirName
            uri = placeFileEx.URI
        if isLocal:
            self._addWatchForChanges(placeFileEx.path)

        self._currentPlace_uri = uri
        self._currentPlace_koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        self._currentPlace_koFileEx.URI = uri
        self.lock.acquire()
        try:
            self._nodeOpenStatusFromName[uri] = time.time()
        finally:
            self.lock.release()
        self._trimOpenStatusDict()

        item = self.getNodeForURI(uri)
        if item is None:
            item = _KoPlaceItem(_PLACE_FOLDER, uri, placeFileEx.baseName)
            self.setNodeForURI(uri, item)
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'uri':uri, 'callback':callback}
        finally:
            self.lock.release()
        #qlog.debug("go do refreshTreeOnOpen")
        self.workerThread.put(('refreshTreeOnOpen',
                               {'index': 0,
                                'uri':uri,
                                'requestID':requestID,
                                'requester':self},
                               'post_refreshTreeOnOpen'))

    def post_refreshTreeOnOpen(self, rv, requestID):
        #qlog.debug(">> post_refreshTreeOnOpen")
        uri, callback = self.getItemsByRequestID(requestID, 'uri', 'callback')
        import pprint
        topModelNode = self.getNodeForURI(uri)
        #qlog.debug("  about to sort the model")
        self._sortModel(uri)
        #qlog.debug("  done")
        if rv:
            # Do this after the request data was cleared
            if callback:
                callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                          rv)
            else:
                sendStatusMessage(rv)
                raise Exception(rv)
        self._wrap_refreshTreeOnOpen_buildTree()
        if callback:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")

    OPEN_PLACES_LIMIT = 100
    def _trimOpenStatusDict(self):
        self.lock.acquire()
        try:
            diff_count = len(self._nodeOpenStatusFromName) - self.OPEN_PLACES_LIMIT
            if diff_count > self.OPEN_PLACES_LIMIT * 0.1:
                # The oldest items are the smallest, and come first
                keys_sorted_by_time = [a2 for a1, a2 in
                                       sorted([(y,x) for x, y in self._nodeOpenStatusFromName.items()])
                                       ]
                for k in keys_sorted_by_time[0 : diff_count]:
                    del self._nodeOpenStatusFromName[k]
        finally:
            self.lock.release()


    def _matchesFilter(self, name, filterString):
        return fnmatch.fnmatch(name, filterString)

    def _namePassesFilter(self, name, fileType):
        # See koProjectImportService.py#_filterFiles, slightly modified.
        # The code is an optimized version of this spec:
        # 1. No excludes, No includes: return it
        # 2. Excludes only: return unless it matches
        # 3. Includes only: return all dirs, and only files that match
        # 4. Both: take the includes from (3), and filter out unwanted
        #          otherwise if it's a non-excluded dir, return it

        if not self.include_patterns:
            if not self.exclude_patterns:
                return True
        elif fileType == _PLACE_FILE:
            for include_pattern in self.include_patterns:
                if self._matchesFilter(name, include_pattern):
                    break
            else:
                return False
        for exclude_pattern in self.exclude_patterns:
            if self._matchesFilter(name, exclude_pattern):
                return False
        return True

    def _refreshTreeOnOpen_buildTree(self, level, rowIndex, parentNode):
        if parentNode.type != _PLACE_FOLDER:
            log.error(("_refreshTreeOnOpen_buildTree: called on non-folder "
                       + "%s at index %d"),
                      parentNode.name, rowIndex)
            return

        
        self.lock.acquire()
        try:
            for childNode in parentNode.childNodes:
                childName = childNode.name
                if self._namePassesFilter(childName, childNode.type):
                    ####qlog.debug("insert %s (%s) at slot %d", childNode.uri, childNode.type, rowIndex)
                    newNode = placeObject[childNode.type](level, childNode.uri)
                    self._rows.insert(rowIndex, newNode)
                    isOpenNode = self.isContainerOpen(rowIndex)
                    rowIndex += 1
                    if isOpenNode:
                        rowIndex = self._refreshTreeOnOpen_buildTree(level + 1, rowIndex, childNode)
            #qlog.debug("<< _refreshTreeOnOpen_buildTree(rowIndex:%d)", rowIndex)
        finally:
            self.lock.release()
        return rowIndex
        

    def addNewFileAtParent(self, basename, parentIndex):
        if parentIndex == -1:
            parentPath = self._currentPlace_koFileEx.path
        else:
            parentPath = self._rows[parentIndex].path
        if self.safe_isLocal():
            fullPath = os.path.join(parentPath, basename)
            if os.path.exists(fullPath):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s" % (basename, parentPath))
            f = open(fullPath, "w")
            f.close()
        else:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            fullPath = parentPath + "/" +  basename
            if conn.list(fullPath, False):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s:%s" % (basename, conn.server, parentPath))
            conn.createFile(fullPath, 0644)
        if parentIndex == -1:
            self.refreshFullTreeView()
        else:
            self._insertNewItemAtParent(parentIndex)

    def addNewFolderAtParent(self, basename, parentIndex):
        if parentIndex == -1:
            parentPath = self._currentPlace_koFileEx.path
        else:
            parentPath = self._rows[parentIndex].path
        if self.safe_isLocal():
            fullPath = os.path.join(parentPath, basename)
            if os.path.exists(fullPath):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s" % (basename, parentPath))
            os.mkdir(fullPath)
        else:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            fullPath = parentPath + "/" +  basename
            if conn.list(fullPath, False):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s:%s" % (basename, conn.server, parentPath))
            perms = _umaskFromPermissions(conn.list(parentPath, False))
            conn.createDirectory(fullPath, perms)
        if parentIndex == -1:
            self.refreshFullTreeView()
        else:
            self._insertNewItemAtParent(parentIndex)

    def _insertNewItemAtParent(self, targetIndex):
        if not self.isContainer(targetIndex):
            return
        elif not self.isContainerOpen(targetIndex):
            uri = self._rows[targetIndex].uri
            modelNode = self.getNodeForURI(uri)
            if modelNode:
                modelNode.markForRefreshing()
            return
        self.refreshView(targetIndex)

    #---- delete-item Methods

    def itemIsNonEmptyFolder(self, index):
        # Called from places.js
        if not self.isContainer(index):
            return False
        rowNode = self._rows[index]
        if (index < len(self._rows) - 1
            and rowNode.level < self._rows[index + 1].level):
            return True
        uri = rowNode.uri
        modelNode = self.getNodeForURI(uri)
        self.lock.acquire()
        try:
            hasChildNodes = len(modelNode.childNodes) > 0
        finally:
            self.lock.release()
        if hasChildNodes:
            return True
        elif not modelNode.needsRefreshing():
            return False
        # Look at the system, don't rely on the tree.
        # No point updating the childNodes list, as we're about to delete this node.
        path = rowNode.path
        if self.safe_isLocal():
            return len(os.listdir(path)) > 0
        conn = self._RCService.getConnectionUsingUri(uri)
        rfi = conn.list(path, True)
        children = rfi.getChildren()
        return len(children) > 0

    def deleteItems(self, indices, uris):
        self.lock.acquire()
        try:
            self.dragDropUndoCommand.clearArgs()
        finally:
            self.lock.release()
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'indices':indices,
                                     'nodes_to_remove':[],
                                     'uris':uris,
                                     }
        finally:
            self.lock.release()
        for index in indices:
            node = self._rows[index]
            self._busyRow(index, node)
        self.workerThread.put(('deleteItems_workerThread',
                                {'requestID':requestID,
                                'requester':self},
                               'post_deleteItems'))
        
    def post_deleteItems(self, rv, requestID):
        indices, nodes_to_remove, uris = self.getItemsByRequestID(requestID, 'indices', 'nodes_to_remove', 'uris')
        if rv:
            sendStatusMessage(rv)
            #todo: callback.callback()
            return
        doInvalidate = False
        self._tree.beginUpdateBatch()
        undeleted_paths = []
        try:
            for uri, index in reversed(zip(uris, indices)):
                if not uri in nodes_to_remove:
                    undeleted_paths.append(uriparse.URIToPath(uri))
                    continue
                try:
                    node = self._rows[index]
                except IndexError:
                    node = None
                if node is not None and node.uri == uri:
                    # Good
                    actualIndex = index
                else:
                    actualIndex = self.getRowIndexForURI(uri)
                    if actualIndex == -1:
                        #XXX How do we stop the node from spinning?
                        log.error("post_deleteItems: Can't find URI %s", uri)
                        continue
                    doInvalidate = True
                node = self._rows[actualIndex]
                if node is None:
                    log.error("post_deleteItems: looking for URI %s: node %d is null", actualIndex)
                    continue
                node.restore_icon()
                if self.isContainerOpen(actualIndex):
                    nextIndex = self.getNextSiblingIndex(actualIndex)
                    if nextIndex == -1:
                        nextIndex = len(self._rows)
                else:
                    nextIndex = actualIndex + 1
                self.removeSubtreeFromModelForURI(uri)
                del self._rows[actualIndex:nextIndex]
                self.resetDirectoryWatches()
                self._tree.rowCountChanged(actualIndex, actualIndex - nextIndex)
            if doInvalidate:
                self.invalidateTree()
        finally:
            self._tree.endUpdateBatch()
        if undeleted_paths:
            if len(undeleted_paths) == 1:
                sendStatusMessage("Couldn't delete file %s" % (undeleted_paths[0],))
            else:
                sendStatusMessage("Couldn't %d delete files: %s" % (len(undeleted_paths), ", ".join(undeleted_paths)))            

    def _postRequestCommonNodeHandling(self, originalNode, index, context):
        originalNode.restore_icon()
        if index >= len(self._rows):
            log.error("_postRequestCommonNodeHandling: index:%d, # rows:%d",
                      index, len(self._rows))
            index = len(self._rows) - 1
            if index == -1:
                return -1, None
        rowNode = self._rows[index]
        if rowNode != originalNode:
            try:
                fixed_index = self._rows.index(originalNode)
                index = fixed_index
                self._invalidateRow(index)
            except ValueError:
                # Nodes have changed, try looking by uri
                i = 0
                uri = originalNode.uri
                for row in self._rows:
                    if uri == row.uri:
                        log.debug("Found uri %s at index %d", uri, i)
                        index = i
                        rowNode = row
                        break
                    i += 1
                else:
                    log.error("Can't find index %d in current tree", index)
                    return -1, rowNode
        else:
            self._invalidateRow(index)
        return index, rowNode

    def markRow(self, index):
        self._lastSelectedRow = index

    #---- nsITreeView Methods
    
    def get_rowCount(self):
        return len(self._rows)
    
    def getCellText(self, row, column):
        col_id = column.id
        #log.debug(">> getCellText:%d, %s", row, col_id)
        try:
            return self._rows[row].getCellText(col_id)
        except AttributeError:
            log.debug("getCellText: No id %s at row %d", col_id, row)
            return "?"

    def getCellProperties(self, row_idx, column):
        """Return cell properties - Mozilla 22+ version"""
        col_id = column.id
        assert col_id == "name"
        property_names = []
        try:
            rowNode = self._rows[row_idx]
            property_names = rowNode.getCellPropertyNames(col_id)
        except AttributeError:
            log.exception("getCellProperties(row_idx:%d, col_id:%r",
                          row_idx, col_id)
            return ""
        if rowNode.properties is None:
            # These values are cached, until there is a file_status change.
            rowNode.properties = self._buildCellProperties(rowNode)
        property_names += rowNode.properties
        return " ".join(property_names)

    def getImageSrc(self, row_idx, column):
        """Return the image for the given cell."""
        if column.id == 'name':
            prefs = components.classes["@activestate.com/koPrefService;1"].\
                getService(components.interfaces.koIPrefService).prefs

            if prefs.getBoolean("showFileIcons", True):
                return self._rows[row_idx].cellImageURL
            else:
                return ""

    def _updateFileProperties(self, idx):
        rowNode = self._rows[idx]
        try:
            #log.debug("_updateFileProperties: idx:%d", idx)
            rowNode.properties = None
            rowNode.propertyNames = None
        except AttributeError:
            pass
            
    def _buildCellProperties(self, rowNode):
        properties = []
        if not self.safe_isLocal():
            return properties
        koFileObject = rowNode.koFile
        if not koFileObject:
            return properties
        koFileObject = UnwrapObject(koFileObject)
        if koFileObject.isReadOnly:
            properties.append("isReadOnly")
        return properties


    def isContainer(self, index):
        #log.debug(">> isContainer[%d] => %r", index, self._rows[index].isContainer)
        return self._rows[index].isContainer
    
    def isContainerOpen(self, index):
        #log.debug(">> isContainerOpen[%d] => %r", index, self._rows[index].isOpen)
        return self._rows[index].isOpen
        
    def isContainerEmpty(self, index):
        #log.debug(">> isContainerEmpty[%d] => %r", index, len(self._rows[index].childNodes) == 0)
        try:
            return self.isContainer(index) and len(self._rows[index].childNodes) == 0
        except AttributeError, ex:
            node = self._rows[index]
            log.exception("level: %d, uri:%s, isContainer:%r",
                           node.level,
                           node.uri,
                           node.isContainer)
            return False

    def getParentIndex(self, index):
        if index >= len(self._rows) or index < 0: return -1
        try:
            i = index - 1
            level = self._rows[index].level
            while i >= 0 and self._rows[i].level >= level:
                i -= 1
        except IndexError, e:
            i = -1
        return i

    def hasNextSibling(self, index, afterIndex):
        if index >= len(self._rows) or index < 0: return 0
        try:
            current_level = self._rows[index].level
            for next_row in self._rows[afterIndex + 1:]:
                next_row_level = next_row.level
                if next_row_level < current_level:
                    return 0
                elif next_row_level == current_level:
                    return 1
        except IndexError, e:
            pass
        return 0
    
    def getLevel(self, index):
        if index >= len(self._rows) or index < 0: return -1
        return self._rows[index].level

    def getNextSiblingIndex(self, index):
        """
        @param index {int} points to the node whose next-sibling we want to find.
        @return index of the sibling, or -1 if not found.
        """
        level = self._rows[index].level
        lim = len(self._rows)
        index += 1
        while index < lim:
            if self._rows[index].level <= level:
                return index
            index += 1
        return -1

    def onRefreshClosedRow(self, index):
        # We'll get the refreshed view when we toggle the node.
        uri = self._rows[index].uri
        modelNode = self.getNodeForURI(uri)
        if modelNode:
            modelNode.markForRefreshing()
        #qlog.debug("not rowNode.isOpen:")
       
    def refreshView(self, index):
        if index == -1:
            self.refreshFullTreeView()
            return
        rowNode = self._rows[index]
        #qlog.debug("refreshView(index:%d)", index)
        if not rowNode.isOpen:
            self.onRefreshClosedRow(index)
            return
        nextIndex = self.getNextSiblingIndex(index)
        #qlog.debug("nextIndex: %d", nextIndex)
        if nextIndex == -1:
            nextIndex = len(self._rows)
            nextIndexURI = None
            #qlog.debug("adjust for -1, nextIndex: %d", nextIndex)
        else:
            nextIndexURI = self._rows[nextIndex].uri
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'index':index,
                                     'nextIndex':nextIndex,
                                     'nextIndexURI':nextIndexURI,
                                     'firstVisibleRow':self._tree.getFirstVisibleRow(),
                                     'node':rowNode}
        finally:
            self.lock.release()
        self._busyRow(index, rowNode)
        self._currentRefreshRequests[index] = requestID
        self.workerThread.put(('toggleOpenState_Open',
                               {'index': index,
                                'node':rowNode,
                                'uri':rowNode.uri,
                                'forceRefresh':True,
                                'requestID':requestID,
                                'requester':self},
                               'post_refreshView'))
        
    def post_refreshView(self, rv, requestID):
        index, nextIndex, nextIndexURI, originalNode, firstVisibleRow =\
            self.getItemsByRequestID(requestID, 'index', 'nextIndex', 'nextIndexURI', 'node', 'firstVisibleRow')
        try:
            if self._currentRefreshRequests[index] > requestID:
                # Another refreshView request on this node is underway
                originalNode.restore_icon()
                return
            del self._currentRefreshRequests[index]
        except KeyError:
            pass
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                         "post_refreshView")
        if 0:
            log.debug("post_refreshView: index:%d, nextIndex:%d, firstVisibleRow:%d, fixedIndex:%d, originalNode.uri:%s, rowNode.uri:%s",
                   index, nextIndex, firstVisibleRow, fixedIndex,
                   originalNode.uri,
                   rowNode.uri)
        if fixedIndex == -1:
            #qlog.debug("Invalidate, return")
            self._tree.invalidate()
            return
        elif fixedIndex != index:
            # recalc nextIndex
            index = fixedIndex != index
            nextIndex = self.getNextSiblingIndex(index)
            if nextIndex == -1:
                nextIndex = len(self._rows)
        if nextIndexURI:
            # Verify that we're pointing at the correct nextIndex
            # Because this method is called asynchronously the tree could
            # have changed size between the time refreshView() dispatched
            # the workerThread item and this method was invoked.
            if self._rows[nextIndex].uri != nextIndexURI:
                newNextIndex = self.getRowIndexForURI(nextIndexURI)
                if newNextIndex == -1:
                    log.error("Can't find the end URI %s in the tree",
                              nextIndexURI)
                    return
                nextIndex = newNextIndex
        elif nextIndex != len(self._rows):
            nextIndex = len(self._rows)
        doInvalidate = True
        self._finishRefreshingView(index, nextIndex, doInvalidate, rowNode,
                                   firstVisibleRow)

    def refreshFullTreeView(self):
        uri = self._currentPlace_uri
        if uri is None:
            log.debug("refreshFullTreeView: no current URI")
            return
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'firstVisibleRow':self._tree.getFirstVisibleRow(),
                                     'uri':uri,
                                     }
        finally:
            self.lock.release()
        #TODO: Make the top-node show a busy signal
        self.workerThread.put(('toggleOpenState_Open',
                                {'uri':uri,
                                'forceRefresh':True,
                                'requestID':requestID,
                                'requester':self},
                               'post_refreshFullTreeView'))
        
    def post_refreshFullTreeView(self, rv, requestID):
        firstVisibleRow =\
            self.getItemsByRequestID(requestID, 'firstVisibleRow')
        self._wrap_refreshTreeOnOpen_buildTree()
        self._tree.scrollToRow(firstVisibleRow)

    def _finishRefreshingView(self, index, nextIndex, doInvalidate, rowNode,
                              firstVisibleRow):
        topModelNode = self.getNodeForURI(rowNode.uri)
        if topModelNode is None:
            # We're probably shutting down now.
            log.debug("_finishRefreshingView: can't get a node for %s",
                      rowNode.uri)
            return
        before_len = len(self._rows)
        first_child_index = index + 1
        #qlog.debug("Delete rows %d:%d", first_child_index, nextIndex)
        del self._rows[first_child_index:nextIndex]
        before_len_2 = len(self._rows)
        self._refreshTreeOnOpen_buildTree(rowNode.level + 1,
                                          first_child_index,
                                          topModelNode)
        self.resetDirectoryWatches()
        after_len = len(self._rows)
        #qlog.debug("before_len: %d, before_len_2: %d, after_len:%d", before_len, before_len_2, after_len)
        numRowChanged = len(self._rows) - before_len
        #qlog.debug("numRowChanged: %d, doInvalidate:%r", numRowChanged, doInvalidate)
        if numRowChanged:
            #qlog.debug("rowCountChanged: index: %d, numRowChanged: %d", index, numRowChanged)
            self._tree.rowCountChanged(index, numRowChanged)
            self._tree.scrollToRow(firstVisibleRow)
        elif doInvalidate:
            self.invalidateTree()

    def resetDirectoryWatches(self): # from koKPFTreeView.p.py
        if not self.safe_isLocal():
            return
        # Too expensive to watch closed nodes too -- then we can mark them for refreshing
        openedDirs = set([row.path for row in self._rows if row.isOpen])
        #print "resetDirectoryWatches %d" % len(openedDirs)
        newDirs = openedDirs.difference(self._watchedDirectories)
        removedDirs = self._watchedDirectories.difference(openedDirs)
        for dir in removedDirs:
            self._removeWatchForChanges(dir)
        for dir in newDirs:
            self._addWatchForChanges(dir)
        self._watchedDirectories = openedDirs

    def _sameFiles(self, path1, path2):
        if os.path.normcase(path1) == os.path.normcase(path2):
            return True
        else:
            st1 = os.stat(path1)
            st2 = os.stat(path2)
            return st1.st_ino != 0 and st1.st_ino == st2.st_ino

    def renameItem(self, index, newBaseName, forceClobber):
        rowNode = self._rows[index]
        koFile = rowNode.koFile
        dirName = koFile.dirName
        path = koFile.path
        oldBaseName = koFile.baseName
        if self.safe_isLocal():
            newPath = os.path.join(dirName, newBaseName)
            if not os.path.exists(newPath):
                shutil.move(path, newPath)
            elif os.path.isdir(newPath):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem: invalid operation: you can't rename existing directory: %s" % (newPath))
            elif not forceClobber:
                raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem failure: file %s exists" % newPath)
            elif os.path.islink(path):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "renameItem failure: source file %s is a symbolic link" % (oldBaseName,))
            elif self._sameFiles(path, newPath):
                log.debug("Don't rename(%s) => %s", path, newPath)
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "renameItem failure: file names %s, %s indicate the same file" % (oldBaseName, newBaseName))
            else:
                try:
                    # Two cases:
                    # rename foo bar -- Windows throws an OSError, ok elsewhere
                    # rename foo FOO -- 
                    # Rename foo.txt FOO.txt on a case-insensitive system
                    os.rename(path, newPath)
                except OSError:
                    if os.path.normcase(oldBaseName) != os.path.normcase(newBaseName):
                        os.unlink(newPath)
                        os.rename(path, newPath)
                    else:
                        log.debug("Don't rename(%s) => %s", path, newPath)
                        raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                              "renameItem failure: file names %s, %s differ only by case, can't be renamed" % (oldBaseName, newBaseName))
        else:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            newPath = dirName + "/" + newBaseName
            rfi = conn.list(newPath, False)
            if not rfi:
                conn.rename(path, newPath)
            elif rfi.isDirectory():
                raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem: invalid operation: you can't rename existing directory: %s::%s" % (conn.server, newPath))
            elif not forceClobber:
                raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem failure: file %s::%s exists" % (conn.server, newPath))
            else:
                try:
                    # See local-system cases above
                    conn.rename(path, newPath)
                except:
                    # We don't know the type of remote system, so assume Windows
                    # because no other system should have thrown an exception
                    if oldBaseName.lower() != newBaseName.lower():
                        conn.removeFile(newPath)
                        conn.rename(path, newPath)
                    else:
                        raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                              "renameItem failure: file names %s, %s differ only by case, can't be renamed" % (oldBaseName, newBaseName))
        uri = koFile.URI
        self.removeSubtreeFromModelForURI(uri)
        parent_uri = self._getURIParent(uri)
        parent_index = self.getRowIndexForURI(parent_uri)
        if parent_index != -1:
            #qlog.debug("renameItem: refresh parent %s at %d", parent_uri, parent_index)
            self.refreshView(parent_index)
        else:
            self.refreshFullTreeView()

    def _wrap_refreshTreeOnOpen_buildTree(self):
        before_len = len(self._rows)
        self._rows = []
        topModelNode = self.getNodeForURI(self._currentPlace_uri)
        if topModelNode is None:
            log.error("_wrap_refreshTreeOnOpen_buildTree: top node for place:%s is None",
                      self._currentPlace_uri)
        else:
            self._refreshTreeOnOpen_buildTree(0, 0, topModelNode)
        after_len = len(self._rows)
        if self._tree:
            self._tree.rowCountChanged(0, after_len - before_len)
            self.invalidateTree()
        self.resetDirectoryWatches()
        # If the current tree could contain any pending URIs that reflect
        # added/deleted files or directories, refresh the tree view.

        # This code also removes items we no longer needed from the
        # _refreshOnUpdateCurrentPlace set.
        curr_pending_set_size = len(self._refreshOnUpdateCurrentPlace)
        self._refreshOnUpdateCurrentPlace = set([uri for uri in self._refreshOnUpdateCurrentPlace
                                       if not uri.startswith(self._currentPlace_uri)])
        if len(self._refreshOnUpdateCurrentPlace) < curr_pending_set_size:
            self.refreshFullTreeView()

    def sortRows(self):
        if not self._rows:
            return
        self._sortModel(self._currentPlace_uri)
        self._wrap_refreshTreeOnOpen_buildTree()
        self._tree.invalidate()

    def sortBy(self, sortKey, direction):
        # sortedBy: 'name'
        # sortDir: NATURAL (1), ASCENDING (2), DESCENDING (3)
        if sortKey != "name":
            log.exception("sortBy called with key %r instead of name", sortKey)
            return
        if direction not in (self.SORT_DIRECTION_NAME_NATURAL,
                             self.SORT_DIRECTION_NAME_ASCENDING,
                             self.SORT_DIRECTION_NAME_DESCENDING):
            log.exception("sortBy called with unrecognized direction %d", direction)
            return
        self._sortedBy = sortKey
        self._sortDir = direction

    def set_handleNextToggleOpenState(self, val):
        self._honorNextToggleOpenState = val
             
    def get_handleNextToggleOpenState(self):
        # Not used by Komodo, here for completeness
        return self._honorNextToggleOpenState

    def toggleOpenState(self, index):
        if not self._honorNextToggleOpenState:
            self._honorNextToggleOpenState = True
            return
        
        # Prevent double toggle calls
        # https://github.com/Komodo/KomodoEdit/issues/61
        timestamp = float(time.time())
        if hasattr(self, "_toggleTimer") and (timestamp - self._toggleTimer) < 0.1:
            return
        self._toggleTimer = timestamp
        
        rowNode = self._rows[index]
        #qlog.debug("toggleOpenState: index:%d", index)
        #qlog.debug("toggleOpenState: rowNode.isOpen: %r", rowNode.isOpen)
        if rowNode.isOpen:
            self.lock.acquire()
            try:
                del self._nodeOpenStatusFromName[rowNode.uri]
            except KeyError:
                pass
            finally:
                self.lock.release()
            nextIndex = self.getNextSiblingIndex(index)
            #qlog.debug("toggleOpenState: index:%d, nextIndex:%d", index, nextIndex)
            if nextIndex == -1:
                # example: index=5, have 13 rows,  delete 7 rows [6:13), 
                numNodesRemoved = len(self._rows) - index - 1
                del self._rows[index + 1:]
            else:
                # example: index=5, have 13 rows, next sibling at index=10
                # delete rows [6:10): 4 rows
                numNodesRemoved = nextIndex - index - 1
                del self._rows[index + 1: nextIndex]
            #qlog.debug("toggleOpenState: numNodesRemoved:%d", numNodesRemoved)
            if numNodesRemoved:
                self._tree.rowCountChanged(index + 1, -numNodesRemoved)
                self.resetDirectoryWatches()
                #log.debug("index:%d, numNodesRemoved:%d, numLeft:%d", index, numNodesRemoved, len(self._rows))
            rowNode.isOpen = False
            self._invalidateRow(index)
        else:
            requestID = self.getRequestID()
            self.lock.acquire()
            try:
                self._data[requestID] = {'index':index,
                                         'node':rowNode,
                                         'items':[], # init if the method fails
                                         }
            finally:
                self.lock.release()
            rowNode.show_busy()
            self.workerThread.put(('toggleOpenState_Open',
                                   {'index': index,
                                    'node':rowNode,
                                    'uri':rowNode.uri,
                                    'forceRefresh':False,
                                    'requestID':requestID,
                                    'requester':self},
                                   'post_toggleOpenState_Open'))

    def post_toggleOpenState_Open(self, rv, requestID):
        index, originalNode = self.getItemsByRequestID(requestID, 'index', 'node')
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                    "post_toggleOpenState_Open")
        if rv:
            sendStatusMessage(rv)
            #todo: callback.callback()
            return
        if fixedIndex == -1:
            # Things to do?
            self._tree.invalidate()
            return
        elif fixedIndex != index:
            doInvalidate = True
            index = fixedIndex
        else:
            doInvalidate = False
        uri = rowNode.uri
        self.lock.acquire()
        try:
            self._nodeOpenStatusFromName[uri] = time.time()
        finally:
            self.lock.release()
        self._trimOpenStatusDict()
        self._sortModel(uri)
        topModelNode = self.getNodeForURI(uri)
        if self.safe_isLocal():
            self._addWatchForChanges(rowNode.path)

        self.lock.acquire()
        try:
            hasChildNodes = len(topModelNode.childNodes) > 0
        finally:
            self.lock.release()

        rowNode.propertyNames = None
        if not hasChildNodes:
            #qlog.debug("Node we opened has no children")
            if doInvalidate:
                self.invalidateTree()
            else:
                self._tree.beginUpdateBatch()
                self._invalidateRow(index)
                self._tree.endUpdateBatch()
            return
        firstVisibleRow = self._tree.getFirstVisibleRow()
        rowNode.isOpen = True
        self._invalidateRow(index)
        self._finishRefreshingView(index, index + 1, doInvalidate, rowNode,
                                   firstVisibleRow)
        self.selection.currentIndex = index
        self.selection.select(index)
        self._tree.ensureRowIsVisible(index)

    def post_toggleOpenState_FilteredClose(self, rv, requestID):
        # 
        # Close the node
        # Reapply the filter.  Note that the node might be gone.
        index, originalNode = self.getItemsByRequestID(requestID, 'index', 'node')
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                    "post_toggleOpenState_FilteredClose")
        if fixedIndex == -1:
            # Things to do?
            self._tree.invalidate()
            return
        self._tree.rowCountChanged(0, len(self._rows) - origLen)
        if self._rows[fixedIndex].isOpen:
            self.toggleOpenState(fixedIndex)
        
    def invalidateTree(self):
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()
                                                
    def setTree(self, tree):
        #log.debug(">> setTree")
        self._tree = tree

    #---- Other methods

    def _finishGettingItem(self, uri, name, itemType):
        item = self.getNodeForURI(uri)
        if item is None or item.type != itemType:
            item = _KoPlaceItem(itemType, uri, name)
            self.setNodeForURI(uri, item)
        return item

    def getDirListFromLocalPath(self, uri):
        path = uriparse.URIToPath(uri)
        assert isinstance(path, unicode)
        # Bug 97419: by spec, os.listdir(unicode) returns unicode encodings
        # of each member as long as it can decode them. On Linux it can't
        # handle latin* encodings, so it returns a str.
        names = os.listdir(path)
        items = []
        for name in names:
            try:
                full_name = os.path.join(path, name)
            except UnicodeDecodeError:
                try:
                    full_name = os.path.join(path, autoDetectEncoding(name)[0])
                except:
                    log.error("Can't combine path %r with name %r", path, name)
                    continue
            if fileutils.isHiddenFile(full_name):
                continue
            # Uses stat (instead of isdir/isfile) to avoid multiple stat calls.
            try:
                fstat = os.stat(full_name)
            except os.error:
                # Can not access it, or could be a symlink that doesn't exist.
                fmode = 0
            else:
                fmode = fstat.st_mode
            if stat.S_ISDIR(fmode):
                itemType = _PLACE_FOLDER
            elif stat.S_ISREG(fmode):
                itemType = _PLACE_FILE
            else:
                itemType = _PLACE_OTHER
            item = self._finishGettingItem(uriparse.localPathToURI(full_name), name, itemType)
            items.append(item)
        return items

    def getDirListFromRemoteURI(self, uri):
#        RCService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
#                  getService(components.interfaces.koIRemoteConnectionService)
#        conn = RCService.getConnectionUsingUri(self._currentPlace_uri)
        try:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
        except COMException:
            msg = "Failed to connect to %s" % self._currentPlace_uri
            log.exception("%s", msg)
            raise Exception(msg)
        path = uriparse.URIToPath(uri)
        rfi = conn.list(path, True) # Really a stat
        if not rfi:
            raise Exception("Can't read path:%s on server:%s" %
                            (path, conn.server))
        rfi_children = rfi.getChildren()
        items = []
        for rfi in rfi_children:
            if rfi.isDirectory():
                itemType = _PLACE_FOLDER
            elif rfi.isFile():
                itemType = _PLACE_FILE
            else:
                itemType = _PLACE_OTHER
            name = rfi.getFilename()
            if uri.endswith('/') or name.startswith('/'):
                slash = ''
            else:
                slash = '/'
            item = self._finishGettingItem(uri + slash + name, name, itemType)
            items.append(item)
        return items
        

    #---- Methods related to working with the workerThread:
    
    def getRequestID(self):
        val = self._nextRequestID
        self._nextRequestID += 1
        return val

    def getItemsByRequestID(self, requestID, *names):
        self.lock.acquire()
        try:
            values = [self._data[requestID][name] for name in names]
        finally:
            del self._data[requestID]
            self.lock.release()
        if len(values) == 1:
            return values[0]
        return values
    
    @components.ProxyToMainThreadAsync
    def handleCallback(self, callback, rv, requestID):
        #log.debug("handleCallback: callback:%s, rv:%s, requestID:%d", callback, rv, requestID)
        try:
            getattr(self, callback)(rv, requestID)
        except:
            log.exception("handleCallback: callback %s", callback)
            # Not much else we can do here.


    # Asych part of the module
class _WorkerThread(threading.Thread, Queue):
    def __init__(self, **kwargs):
        threading.Thread.__init__(self, **kwargs)
        Queue.__init__(self)
        self._isShuttingDown = False

    def shutdown(self):
        self._isShuttingDown = True
        self.put((None, None, None))

    def run(self):
        while 1:
            request, args, callback = self.get()
            if not request or self._isShuttingDown:
                break
            try:
                rv = getattr(self, request)(args)
            except:
                log.exception("Request:%s", request)
                reason = sys.exc_info()[1]
                if reason:
                    rv = "Exception: request:%s, message:%s" % (request, reason)
                else:
                    # Bug 89496: We don't have a good message to relay,
                    # so don't bother with the normal callback.  Build the
                    # tree with whatever info the worker thread picked up.
                    rv = ""
                
            if not self._isShuttingDown:
                treeView = args['requester']
                treeView.handleCallback(callback, rv, args['requestID'])

    def refreshTreeOnOpen(self, args):
        uri = args['uri']
        requester = args['requester']
        self.refreshTreeOnOpen_Aux(requester, uri)
        return ""

    def refreshTreeOnOpen_Aux(self, requester, uri, forceRefresh=False):
        itemNode = requester.getNodeForURI(uri)
        if itemNode is None:
            #qlog.debug("**************** No node for uri %s", uri)
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                       createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = uri
            if koFileEx.isDirectory:
                nodeType = _PLACE_FOLDER
            else:
                nodeType = _PLACE_FILE
            itemNode = _KoPlaceItem(nodeType, uri, koFileEx.baseName)
            requester.setNodeForURI(uri, itemNode)
        if itemNode.type != _PLACE_FOLDER:
            return
        # We can't hold onto the lock around getDirListFromRemoteURI,
        # because it makes a proxy call on the main thread.
        requester.lock.acquire()
        try:
            refreshNodes = forceRefresh or itemNode.needsRefreshing()
        finally:
            requester.lock.release()
        if refreshNodes:
            if requester.safe_isLocal():
                items = requester.getDirListFromLocalPath(uri)
            else:
                items = requester.getDirListFromRemoteURI(uri)
        else:
            items = None
        requester.lock.acquire()
        try:
            if items is not None:
                itemNode.childNodes = items
                itemNode.lastUpdated = time.time()
            else:
                items = itemNode.childNodes
        finally:
            requester.lock.release()
        for item in items:
            requester.lock.acquire()
            try:
                updateNodes = requester._nodeOpenStatusFromName.get(item.uri, False)
            finally:
                requester.lock.release()
            if updateNodes:
                self.refreshTreeOnOpen_Aux(requester, item.uri, forceRefresh)

    def toggleOpenState_Open(self, args):
        requester = args['requester']
        uri = args['uri']
        forceRefresh = args['forceRefresh']
        #qlog.debug("toggleOpenState_Open: forceRefresh:%r", forceRefresh)
        self.refreshTreeOnOpen_Aux(requester, uri, forceRefresh)
        requester._sortModel(uri)
        return ""

    def _deleteRemoteDirectoryContents(self, conn, rfi):
        children = rfi.getChildren()
        for child_rfi in children:
            path = child_rfi.getFilepath()
            if child_rfi.isDirectory():
                child_rfi = conn.list(path, True)
                self._deleteRemoteDirectoryContents(conn, child_rfi)
                conn.removeDirectory(path)
                rfi2 = conn.list(path, True)
                if rfi2:
                    raise Exception("Can't remove directory %s on server %s" %
                                    (path, conn.server))
            else:
                conn.removeFile(path)

    def deleteItems_workerThread(self, args):
        requester = args['requester']
        requestID = args['requestID']
        requester.lock.acquire()
        try:
            requester_data = requester._data[requestID]
        finally:
            requester.lock.release()
        uris = requester_data['uris']
        indices = requester_data['indices']
        nodes_to_remove = requester_data['nodes_to_remove']

        for uri, index in reversed(zip(uris, indices)):
            try:
                if self._do_deleteItem(requester, uri, index):
                    nodes_to_remove.append(uri)
            except:
                log.exception("Failed to delete %s", uri)
        
    def _do_deleteItem(self, requester, uri, index):
        koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                   createInstance(components.interfaces.koIFileEx)
        koFileEx.URI = uri
        path = koFileEx.path
        if koFileEx.isLocal:
            sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
                              getService(components.interfaces.koISysUtils)
            try:
                res = sysUtils.MoveToTrash(path)
                if os.path.exists(path):
                    log.error("Failed to remove local file %s" % (path,))
                    return False
            except:
                log.exception("sysUtils.MoveToTrash(%s) failed", path)
                if os.path.isdir(path):
                    from distutils.dir_util import remove_tree
                    remove_tree(path)
                else:
                    os.unlink(path)
            return not os.path.exists(path)
        else:
            conn = requester._RCService.getConnectionUsingUri(uri)
            rfi = conn.list(path, True)
            if rfi.isDirectory():
                self._deleteRemoteDirectoryContents(conn, rfi)
                conn.removeDirectory(path)
            else:
                conn.removeFile(path)
            rfi2 = conn.list(path, True)
            if rfi2:
                log.error("deleteItem: failed to delete %s on server %s" % (path, conn.server))
                return False
            return True

    def doTreeOperation_WorkerThread(self, args):
        requester = args['requester']
        requestID = args['requestID']
        requester.lock.acquire()
        try:
            requester_data = requester._data[requestID]
        finally:
            requester.lock.release()
        srcURI = requester_data['srcURI']
        targetURI = requester_data['targetURI']
        targetIndex = requester_data['targetIndex']
        copying = requester_data['copying']
        
        finalMsg = ""
        errorMsg = ""
        srcFileEx = components.classes["@activestate.com/koFileEx;1"].\
                       createInstance(components.interfaces.koIFileEx)
        srcFileEx.URI = srcURI
        targetFileEx = components.classes["@activestate.com/koFileEx;1"].\
                       createInstance(components.interfaces.koIFileEx)
        targetFileEx.URI = targetURI

        # When we copy or move an open folder, the target folder will be
        # closed, even if it was open before.  Windows explorer works this way.
        updateTargetTree = False
        srcPath = srcFileEx.path
        if srcFileEx.isLocal and targetFileEx.isLocal:
            finalTargetFilePath = os.path.join(targetFileEx.path,
                                               srcFileEx.baseName)
            srcPath = srcPath
            updateTargetTree = not os.path.exists(finalTargetFilePath)
            #XXX Watch out if targetFile is an open folder.
            if not copying:
                try:
                    shutil.move(srcPath, finalTargetFilePath)
                except IOError, ex:
                    finalMsg = ("doTreeOperation_WorkerThread: can't copy %s to %s: %s" %
                                (srcPath, finalTargetFilePath, ex.message))
                    return finalMsg
                requester.lock.acquire()
                try:
                    requester.dragDropUndoCommand.update(finalTargetFilePath, srcPath, True)
                finally:
                    requester.lock.release()
            elif srcFileEx.isDirectory:
                fileutils.copyLocalFolder(srcPath, targetFileEx.path)
            else:
                shutil.copy(srcPath, finalTargetFilePath)
                # Nothing to undo
        elif ((not srcFileEx.isLocal)
              and (not targetFileEx.isLocal)
              and srcFileEx.server == targetFileEx.server):
            conn = requester._RCService.getConnectionUsingUri(srcURI)
            finalTargetFilePath = targetFileEx.path + "/" + srcFileEx.baseName
            target_rfi = conn.list(finalTargetFilePath, True)
            updateTargetTree = not target_rfi
            #XXX Watch out if targetFile is an open folder.
            if not copying:
                try:
                    conn.rename(srcPath, finalTargetFilePath)
                except:
                    log.exception("Can't rename %s, %s", srcPath, finalTargetFilePath)
                    if target_rfi:
                        # File already exists, so we can't just rename it
                        try:
                            newTempName = "%s-%f" % (finalTargetFilePath,
                                                     time.time())
                            conn.rename(finalTargetFilePath, newTempName)
                            conn.rename(srcPath, finalTargetFilePath)
                            try:
                                conn.removeFile(newTempName)
                            except:
                                log.exception("Can't remove file %s", newTempName)
                                try:
                                    conn.removeDirectoryRecursively(newTempName)
                                except:
                                    log.exception("Can't remove dir %s", newTempName)
                        except:
                            log.exception("Can't rename this thing")
                requester.lock.acquire()
                try:
                    requester.dragDropUndoCommand.update(targetURI + "/" + srcFileEx.baseName, srcURI, False)
                finally:
                    requester.lock.release()
            elif srcFileEx.isDirectory:
                requester_data['uncopied_symlinks'] = []
                requester_data['unrecognized_filetypes'] = []
                self._copyRemoteFolder(conn, srcPath, targetFileEx.dirName, requester_data)
                if requester_data['uncopied_symlinks'] or requester_data['unrecognized_filetypes']:
                    finalMsg = ("There were problems copying folder %s to %s:\n"
                           % (srcPath, targetFileEx.dirName))
                    if requester_data['uncopied_symlinks']:
                        finalMsg += "\nThe following symbolic links weren't copied:\n"
                        finalMsg += "\n    ".join(requester_data['uncopied_symlinks'])
                    if requester_data['unrecognized_filetypes']:
                        finalMsg += "\nThe following files had an unexpected type:\n"
                        finalMsg += "\n    ".join(requester_data['unrecognized_filetypes'])
            else:
                # Copy infile outfile
                try:
                    data = conn.readFile(srcPath)
                    conn.writeFile(finalTargetFilePath, data)
                except:
                    log.exception("can't copy file %s (data:%r))",
                                  srcPath, data)
                    errorMsg = "Exception: can't copy file %s (data:%s)): %s" % (srcPath, data, sys.exc_info()[1])
                            
        else:
            errorMsg = "drag/drop across different servers not yet supported"
        requester_data['finalMsg'] = finalMsg
        requester_data['updateTargetTree'] = updateTargetTree
        if errorMsg:
            return errorMsg
        if not copying:
            parentURI = requester._getURIParent(srcURI)
            self.refreshTreeOnOpen_Aux(requester, parentURI, forceRefresh=True)
            requester._sortModel(parentURI)
        self.refreshTreeOnOpen_Aux(requester, targetURI, forceRefresh=True)
        requester._sortModel(targetURI)
        return ""

    #---- Remote file copying

    def _copyRemoteFolder(self, conn, srcPath, targetDirPath, requester_data):
        # Do this as a depth-first walk
        rfi = conn.list(srcPath, True)
        if rfi is None:
            raise Exception("internal error: _copyRemoteFolder: can't resolve srcPath=%s (targetDirPath:%s)" % 
                            (srcPath, targetDirPath))
        self._copyRemoteItem(conn, rfi, targetDirPath, requester_data)

    def _copyRemoteFile(self, conn, rfi, targetDirPath):
        targetPath = targetDirPath + "/" + rfi.getFilename()
        conn.createFile(targetPath, _umaskFromPermissions(rfi))
        conn.writeFile(targetPath, conn.readFile(rfi.getFilepath()))

    def _copyRemoteDirectoryAndContents(self, conn, rfi, targetDirPath, requester_data):
        targetPath = targetDirPath + "/" + rfi.getFilename()
        conn.createDirectory(targetPath, _umaskFromPermissions(rfi))
        # Refresh the current rfi.  Otherwise it won't find items
        # that haven't been visited yet.
        new_rfi = conn.list(rfi.getFilepath(), True)
        children = new_rfi.getChildren()
        for child_rfi in children:
            self._copyRemoteItem(conn, child_rfi, targetPath, requester_data)

    def _copyRemoteItem(self, conn, rfi, targetPath, requester_data):
        if rfi.originalIsSymlink:
            requester_data['uncopied_symlinks'].append(rfi.getFilepath())
        elif rfi.isFile():
            self._copyRemoteFile(conn, rfi, targetPath)
        elif rfi.isDirectory():
            self._copyRemoteDirectoryAndContents(conn, rfi, targetPath, requester_data)
        else:
            requester_data['unrecognized_filetypes'].append(rfi.getFilepath())

    def doTreeCopyWithDestNameAndURI_WorkerThread(self, args):
        requester = args['requester']
        requester.lock.acquire()
        try:
            requester.dragDropUndoCommand.clearArgs()
        finally:
            requester.lock.release()
        requester = args['requester']
        requestID = args['requestID']
        requester.lock.acquire()
        try:
            requester_data = requester._data[requestID]
        finally:
            requester.lock.release()
        srcURI = requester_data['srcURI']
        targetURI = requester_data['targetURI']
        newPath = requester_data['newPath']
        
        srcFileEx = components.classes["@activestate.com/koFileEx;1"].\
                       createInstance(components.interfaces.koIFileEx)
        srcFileEx.URI = srcURI
        srcPath = srcFileEx.path
        # This is always done in the same window, so both nodes are
        # always on the same server.
        if srcFileEx.isLocal:
            try:
                if srcFileEx.isDirectory:
                    if os.path.exists(newPath):
                        # newPath exists, so add the baseName
                        newPath2 = os.path.join(newPath, srcFileEx.baseName)
                        if os.path.exists(newPath2):
                            raise Exception("path %s already exists" %
                                            newPath2)
                    else:
                        # newPath doesn't exist, no further change needed
                        newPath2 = newPath
                    shutil.copytree(srcPath, newPath2)
                else:
                    newPath2 = newPath
                    shutil.copy(srcPath, newPath2)
            except (Exception, IOError), ex:
                finalMsg = ("doTreeCopyWithDestNameAndURI_WorkerThread: can't copy %s to %s: %s" %
                            (srcPath, newPath2, ex.message))
                log.exception("%s", finalMsg)
                return finalMsg
        else:
            #Bug 100160: Handle copying remote folders.
            conn = requester._RCService.getConnectionUsingUri(requester._currentPlace_uri)
            src_rfi = conn.list(srcPath, True)
            try:
                self._copyRemoteItem(conn, src_rfi, newPath, requester_data)
            except Exception, ex:
                finalMsg = ("doTreeCopyWithDestNameAndURI_WorkerThread: can't copy file %s to %s: %s" %
                            (srcPath, newPath, ex.message))
                log.exception("%s", finalMsg)
                return finalMsg
        requester._sortModel(targetURI)
        return ''

    def setMainFilters(self, args):
        # Another do-nothing routine just used to serialize requests
        return ''
    
