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
import logging
import json
import shutil
import fnmatch
import pprint
import time
import uriparse

from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject

from koTreeView import TreeView
from koLanguageServiceBase import sendStatusMessage
log = logging.getLogger("KoPlaceTreeView")
log.setLevel(logging.DEBUG)
qlog = logging.getLogger("KoPlaceTreeView.q")
qlog.setLevel(logging.DEBUG)

class _kplBase(object):
    def __init__(self, fileObj):
        self.fileObj = fileObj # koIFileEx
        if fileObj:
            if not fileObj.URI:
                raise Exception("No fileObj.URI")
        self.original_image_icon = self.image_icon
        self.busy_count = 0
        
    def getCellPropertyNames(self, col_id):
        if col_id == 'name':
            return [self.image_icon]
        return []

    def getName(self):
        return self.fileObj.baseName

    def getPath(self):
        return self.fileObj.path

    def getURI(self):
        return self.fileObj.URI

    getUri = getURI   # Because of how accessors are calculated

    def getCellPropertyNames(self, col_id):
        if col_id == 'name':
            return [self.image_icon]
        return []

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
    def getCellPropertyNames(self, col_id):
        if col_id == 'name':
            if self.image_icon == 'places_busy':
                return ['places_busy']
            elif self.isOpen:
                return [self.image_icon + "_open"]
            else:
                return [self.image_icon + "_closed"]
        return []

class _kplFile(_kplBase):
    image_icon = 'places_file'
    isContainer = False
    
class _kplPlaceholder(_kplBase):
    image_icon = None
    isContainer = False
    
class _kplOther(_kplBase):
    image_icon = 'places_other'
    isContainer = False
    
_PLACE_FOLDER = 1
_PLACE_FILE = 2
_PLACE_OTHER = 3
_PLACE_PLACEHOLDER = 4 # Not used

placeObject = {
    _PLACE_FOLDER : _kplFolder,
    _PLACE_FILE   : _kplFile,
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

class _HierarchyNode(object):
    def __init__(self, level, infoObject):
        self.level = level
        self.infoObject = infoObject
        self.isContainer = infoObject.isContainer
        self.infoObject.isOpen = (self.isContainer
                       and self._nodeOpenStatusFromName.get(self.getURI(), False))
        if self.isContainer:
            self.childNodes = [_HierarchyNode(level + 1, _kplPlaceholder(None))]
        else:
            self.childNodes = []
        
    def getURI(self):
        return self.infoObject.getURI()
            
    def getName(self):
        return self.infoObject.getName()

    def getCellText(self, col_id):
        methodName = "get" + col_id.capitalize()
        return getattr(self.infoObject, methodName)()

    def getCellPropertyNames(self, col_id):
        return self.infoObject.getCellPropertyNames(col_id)

    def getPath(self):
        #XXX Store URIs, return paths or file names on demand
        # Cache leafnames
        return self.infoObject.getPath()

    def unsetContainer(self):
        self.isContainer = False

    def matchesFilter(self, filterString):
        """Returns a boolean indicating if this node matches the filter."""
        name = self.getName()
        return filterString.lower() in name.lower() or fnmatch.fnmatch(self.getName(), filterString)

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
                        components.interfaces.koIFileNotificationObserver,
                        components.interfaces.nsISupportsWeakReference]
    _reg_clsid_ = "{3b4b4e60-0bbd-4efc-b118-a153b3f84166}"
    _reg_contractid_ = "@activestate.com/koPlaceTreeView;1"
    _reg_desc_ = "KoPlacesTreeView Tree View"
        
    def __init__(self, debug=None):
        TreeView.__init__(self, debug=0)
        # The model
        self._nodesForURI = {}
        self._root = None
        self._currentPlace_uri = None
        self._rows = []
        self._liverows = set()  # Tracking changes
        self._originalRows = self._rows  # For filtering
        self._filteredRows = None
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

        self._tree = None
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._wrapSelf = WrapObject(self, components.interfaces.nsIObserver)
        self._observerSvc.addObserver(self._wrapSelf, "file_status", True) # weakref

        self._RCService = components.classes["@activestate.com/koRemoteConnectionService;1"].\
                  getService(components.interfaces.koIRemoteConnectionService)
        self._nextRequestID = 0
        
    def initialize(self):
        self.atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self._atomsFromName = {}
        for name in ["places_busy",
                     "places_folder_open",
                     "places_folder_closed",
                     "places_file",
                     ]:
            self._atomsFromName[name] = self.atomSvc.getAtom(name)
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
        _HierarchyNode._nodeOpenStatusFromName = self._nodeOpenStatusFromName
        self.lock = threading.RLock()
        self.dragDropUndoCommand = _UndoCommand()
        wrapSelf = WrapObject(self, components.interfaces.koIPlaceTreeView)
        self.proxySelf = getProxyForObject(None,
                                      components.interfaces.koIPlaceTreeView,
                                      wrapSelf, PROXY_ALWAYS | PROXY_SYNC)
        self.workerThread = _WorkerThread(target=_WorkerThread.run,
                                          name="Places TreeView")
        self.workerThread.daemon = True
        self.workerThread.start()
        self.notificationSvc = components.classes["@activestate.com/koFileNotificationService;1"].\
                                    getService(components.interfaces.koIFileNotificationService)
            
    def terminate(self): # should be finalize
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        prefs.getPref("places").setStringPref("places-open-nodes-v2",
                                  json.dumps(self._nodeOpenStatusFromName))
        self._observerSvc.removeObserver(self, "file_status")
        self.workerThread.put((None, None, None))
        self.workerThread.join(3)
        self.set_currentPlace(None)
        self._rows = []
        self.resetLiveRows()

    def observe(self, subject, topic, data):
        # Taken from koKPFTreeView
        #qlog.debug("observe: subject:%r, topic:%r, data:%r", subject, topic, data)
        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return
        if topic == "file_status":
            
            # find the row for the file and invalidate it
            files = data.split("\n")
            invalidRows = sorted([i for (i,row) in enumerate(self._rows)
                                  if row.getURI() in files], reverse=True)
            for row in invalidRows:
                node = self._rows[row]
                uri = node.getURI()
                koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                           createInstance(components.interfaces.koIFileEx)
                koFileEx.URI = uri
                if koFileEx.exists:
                    if koFileEx.isDirectory:
                        # A file has been added to this dir.
                        # Spin off a refresh request for each row
                        if node.isContainer and node.infoObject.isOpen:
                            self.refreshView(row)
                        else:
                            koPlaceItem = self.getNodeForURI(uri)
                            if koPlaceItem:
                                koPlaceItem.markForRefreshing()
                else:
                    try:
                        #qlog.debug("About to remove uri %s from row %d", uri, row)
                        del self._rows[row]
                        self._tree.rowCountChanged(row, -1)
                        self.resetLiveRows()
                    except AttributeError:
                        pass
                    self.removeNodeFromModel(uri)
        #qlog.debug("<< observe")

    # row generator interface
    def stopped(self):
        return 0

    def _addWatchForChanges(self, path):
        try:
            self.notificationSvc.addObserver(self, path,
                                             components.interfaces.koIFileNotificationService.WATCH_DIR,
                                             _notificationsToReceive)
        except:
            log.exception("Can't watch path: %s", path)
        
    def _removeWatchForChanges(self, path):
        self.notificationSvc.removeObserver(self, path)

    #---------------- Model for the tree view

    def getNodeForURI(self, uri):
        return self._nodesForURI.get(uri, None)

    def setNodeForURI(self, uri, koItemNode):
        self._nodesForURI[uri] = koItemNode
        
    def removeNodeForURI(self, uri):
        try:
            del self._nodesForURI[uri]
        except KeyError:
            pass

    def removeSubtreeFromModelForURI(self, uri):
        koPlaceItem = self.getNodeForURI(uri)
        if not koPlaceItem: return
        self.removeSubtreeFromModelForURI_aux(koPlaceItem)
        self.removeNodeFromParent(uri)

    def removeSubtreeFromModelForURI_aux(self, koPlaceItem):
        childNodes = koPlaceItem.childNodes
        for koChildItem in (childNodes or []):
            if not koChildItem.isSymbolicLink:
                self.removeSubtreeFromModelForURI_aux(koChildItem)
        self.removeNodeForURI(koPlaceItem.uri)
        try:
            del self._nodeOpenStatusFromName[koPlaceItem.uri]
        except KeyError:
            pass

    def removeNodeFromParent(self, uri):
        parent_uri = uri[:uri.rindex("/")]
        parent_node = self.getNodeForURI(parent_uri)
        if parent_node:
            for (i, child_node) in enumerate(parent_node.childNodes):
                if child_node.uri == uri:
                    #qlog.debug("removeChildNode: found %s at %d", uri, i)
                    del parent_node.childNodes[i]
                    break
            else:
                pass
                #qlog.debug("removeChildNode: didn't find %s in %s", uri, parent_uri)

    def removeNodeFromModel(self, uri):
        self.removeNodeFromParent(uri)
        self.removeNodeForURI(uri)
        try:
            del self._nodeOpenStatusFromName[uri]
        except KeyError:
            pass

    def _sortModel(self, uri):
        topModelNode = self.getNodeForURI(uri)
        if topModelNode is None:
            #qlog.debug("_sortModel(uri:%s) is None", uri)
            return
        self._sortModel_aux(topModelNode)
        
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
    def _sortingAdjustCase(self, name):
        if sys.platform.startswith('lin'):
            return name
        return name.lower()

    def _sortItems(self, childNodes):
        assert self._sortedBy == "name"
        adjustedItems = [(self._sortingAdjustCase(x.name), x)
                         for x in childNodes]
        sortedItems = sorted(adjustedItems, cmp=self.sortFuncTable[self._sortDir])
        return [x[1] for x in sortedItems]    

    # nsIFileNotificationObserver
    # we want to receive notifications for any live folders in our view
    # the addition of observers will occur during generateRows
    def fileNotification(self, uri, flags):
        # Pulled this from koKPFTreeView
        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return

        koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        koFileEx.URI = uri
        matching_parts = []
        #print "   path is [%r] dirname [%r]"%(koFileEx.path, koFileEx.dirName)

        dirname = koFileEx.dirName
        if flags & _createdFlags:
            parent_uri = uri[:uri.rindex("/")]
            index = self.getRowIndexForURI(parent_uri)
            if index != -1:
                self.refreshView(index)
        elif flags & _deletedFlags:
            index = self.getRowIndexForURI(uri)
            if index != -1:
                #qlog.debug("fileNotification: About to remove uri %s from row %d", uri, row)
                del self._rows[index]
                self._removeWatchForChanges(koFileEx.path)
                self.removeNodeFromModel(uri)
                self.resetLiveRows()
        else:
            # this is a modification change, just invalidate rows
            index = self.getRowIndexForURI(uri)
            if index >= 0:
                self._updateFileProperties(index, koFileEx)
                self._tree.invalidateRow(index)

    #---- Change places.
    
    def get_currentPlace(self):
        return self._currentPlace_uri;
    
    def set_currentPlace(self, uri, callback=None):
        if self._currentPlace_uri is not None:
            self.closePlace()
        if uri:
            self._currentPlace_uri = uri
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

    def post_setMainFilters(self, rv, requestID):
        exclude_patterns, include_patterns = self.getItemsByRequestID(requestID, 'exclude_patterns', 'include_patterns')
        if not self._decrementCheckPendingFilters():
            return
        self.exclude_patterns = exclude_patterns.split(';')
        self.include_patterns = include_patterns.split(';')
        self._buildFilteredView()

    def _buildFilteredView(self):
        #qlog.debug("_buildFilteredView: exclude:%s, include:%s", self.exclude_patterns, self.include_patterns)
        if not self._rows:
            qlog.debug("No rows")
            return
        origLen = len(self._rows)
        self._filteredRows = []
        # Always include the first row in the full tree.
        for i in range(0, len(self._originalRows)):
            node = self._originalRows[i]
            if self._nodePassesFilter(node):
                self._filteredRows.append(node)
                
        self._rows = self._filteredRows
        delta = len(self._rows) - origLen
        self._tree.rowCountChanged(0, delta)
        self._tree.invalidate()

    def _nodePassesFilter(self, node):
        # First pass on the main include/exclude nodes
        look_at_excludes = True
        for include_pattern in self.include_patterns:
            if node.matchesFilter(include_pattern):
                return True
        for exclude_pattern in self.exclude_patterns:
            if node.matchesFilter(exclude_pattern):
                return False
        return True

    def getRowIndexForURI(self, uri, considerFiltered=False):
        #XXX handle considerFiltered
        for i in range(len(self._rows)):
            if self._rows[i].getURI() == uri:
                return i
        return -1

    def selectURI(self, uri):
        """This is the last part of a call, so this can use a callback on
        the toggleOpenState part
        """
        index = self.getRowIndexForURI(uri)
        if len(self._rows) == 0:
            return
        if index > 0:
            self.selection.currentIndex = index
            return
        node = self._rows[0]
        if node.infoObject.isOpen:
            return
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'uri':uri}
        finally:
            self.lock.release()
        node.infoObject.show_busy()
        self._tree.invalidateRow(0)
        self.workerThread.put(('selectURI_toggleNodeOpen',
                                {'requestID':requestID,
                                 'node':node,
                                 'uri':uri,
                                'requester':self},
                               'post_selectURI'))

    def post_selectURI(self, rv, requestID):
        uri = self.getItemsByRequestID(requestID, 'uri')
        self._rows[0].infoObject.restore_icon()
        self._tree.invalidateRow(0)
        if rv:
            raise Exception(rv)
        index = self.getRowIndexForURI(uri)
        if index >= -1:
            self.selection.currentIndex = index
            self.selection.select(index)
            self._tree.ensureRowIsVisible(index)
        
    def getURIForRow(self, index):
        return self._rows[index].getURI()

    def _targetFileExists(self, localFinalTargetPath, targetPath, srcBasename,
                          isDir_OutVal):
        if not self._isLocal:
            try:
                conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
                finalTargetPath = targetPath + "/" + srcBasename
                rfi = conn.list(finalTargetPath, True)
                isDir_OutVal['value'] = rfi and rfi.isDirectory()
                return rfi # Just want a boolean
            finally:
                conn.close()
        elif os.path.exists(localFinalTargetPath):
            isDir_OutVal['value'] = os.path.isdir(localFinalTargetPath)
            return True

    def _targetFileExistsByFileExObj(self, targetFileEx, isDir_OutVal):
        path = targetFileEx.path
        if not self._isLocal:
            try:
                conn = self._RCService.getConnectionUsingUri(targetFileEx.URI)
                rfi = conn.list(path, True)
                isDir_OutVal['value'] = rfi and rfi.isDirectory()
                return rfi # Just want a boolean
            finally:
                conn.close()
        elif os.path.exists(path):
            isDir_OutVal['value'] = os.path.isdir(path)
            return True

    def treeOperationWouldConflict(self, srcIndex, targetIndex, copying):
        srcNode = self._rows[srcIndex]
        srcBasename = srcNode.getName()
        srcPath = srcNode.getPath()
        targetNode = self._rows[targetIndex]
        targetPath = targetNode.getPath()
        finalTargetPath = self._isLocal and os.path.join(targetPath, srcBasename) or (targetPath + "/" + srcBasename)
        isDir_OutVal = {}

        if self.getParentIndex(srcIndex) == targetIndex:
            if copying:
                res = components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR
            else:
                res = components.interfaces.koIPlaceTreeView.COPY_FILENAME_CONFLICT
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
        if self._isLocal:
            srcFileInfo.path = srcPath
            finalTargetFileInfo.path = finalTargetPath
        else:
            srcFileInfo.URI = srcNode.getURI()
            finalTargetFileInfo.URI = targetNode.getURI() + "/" + srcBasename
        return res, srcFileInfo, finalTargetFileInfo

    def treeOperationWouldConflictByURI(self, srcIndex, targetURI, copying):
        """
        This is called when we're drag/dropping a node onto the root node,
        which doesn't live in the main tree view.
        """
        srcNode = self._rows[srcIndex]
        finalTargetFileInfo = components.classes["@activestate.com/koFileEx;1"].\
                          createInstance(components.interfaces.koIFileEx)
        finalTargetFileInfo.URI = targetURI + "/" + srcNode.getName()
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
        srcFileInfo.URI = srcNode.getURI()
        return res, srcFileInfo, finalTargetFileInfo

    def _targetIsChildOfSource(self, srcIndex, targetIndex):
        if targetIndex < srcIndex:
            return False
        if self._rows[targetIndex].level <= self._rows[srcIndex].level:
            return False
        return srcIndex < targetIndex < self.getNextSiblingIndex(srcIndex)
        
    def doTreeOperation(self, srcIndex, targetIndex, copying, callback):
        """TODO:
        If the source is in SCC, do the appropriate SCC operations on it.
        
        XXX: This should definitely be async.
        """
        srcNode = self._rows[srcIndex]
        targetNode = self._rows[targetIndex]
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'copying':copying,
                                     'srcIndex': srcIndex,
                                     'srcNode': srcNode,
                                     'targetIndex': targetIndex,
                                     'targetNode': targetNode,
                                     'final_msg': '',
                                     'callback': callback,
                                    }
        finally:
            self.lock.release()
        srcNode.infoObject.show_busy()
        self._tree.invalidateRow(srcIndex)
        targetNode.infoObject.show_busy()
        self._tree.invalidateRow(targetIndex)
        #log.debug("%s %s %s", copying and "copy" or "move", srcPath, targetDirPath)
        if not copying and self.getParentIndex(srcIndex) == targetIndex:
            log.debug("Can't copy/move an item on to its own container.")
            return
        elif self.isContainer(srcIndex) and self._targetIsChildOfSource(srcIndex, targetIndex):
            raise Exception("Can't %s a folder (%s) into one of its own sub-folders (%s)" %
                            ((copying and "copy") or "move",
                                srcNode.getPath(), targetNode.getPath()))
        
        self.workerThread.put(('doTreeOperation',
                               {'requestID':requestID,
                                'requester':self},
                               'post_doTreeOperation'))

    def post_doTreeOperation(self, rv, requestID):
        copying, srcIndex, originalSrcNode, targetIndex, originalTargetNode,\
            finalMsg, updateTargetTree, callback = self.getItemsByRequestID(
                requestID, 'copying', 'srcIndex', 'srcNode',
                'targetIndex', 'targetNode', 'finalMsg',
                'updateTargetTree', 'callback')
        # Restore busy nodes.
        fixedSrcIndex, fixedSrcNode = \
           self._postRequestCommonNodeHandling(originalSrcNode, srcIndex,
                                               "post_doTreeOperation")
        fixedTargetIndex, fixedTargetNode = \
           self._postRequestCommonNodeHandling(originalTargetNode, targetIndex,
                                               "post_doTreeOperation")

        if finalMsg:
            log.error("post_doTreeOperation: %s", finalMsg)
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                              finalMsg)
            return
        elif copying and not updateTargetTree:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        elif fixedSrcIndex == -1 or fixedTargetIndex == -1:
            # Things to do?
            self._tree.invalidate()
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        elif fixedSrcIndex != srcIndex:
            doInvalidate = True
            srcIndex = fixedSrcIndex
            srcNode = self._rows[srcIndex]
        elif fixedTargetIndex != targetIndex:
            doInvalidate = True
            targetIndex = fixedTargetIndex
            targetNode = self._rows[targetIndex]
        else:
            doInvalidate = False
            srcNode = originalSrcNode
            targetNode = originalTargetNode
            
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
            topModelNode = self.getNodeForURI(self._currentPlace_uri)
            self._refreshTreeOnOpen_buildTree(0, 0, topModelNode)
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")
            return
        assert((parentSrcIndex > targetIndex
                and parentSrcIndex > targetNextIndex)
               or (parentSrcIndex < targetIndex
                and parentNextIndex < targetIndex))
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
        srcNode.infoObject.show_busy()
        self._tree.invalidateRow(srcIndex)
        #TODO: Make the top-node look busy
        #log.debug("%s %s %s", copying and "copy" or "move", srcPath, targetDirPath)
        if not copying and srcNode.level == 0:
            log.debug("Can't copy/move an item on to its own container.")
            return
        self.workerThread.put(('doTreeOperation',
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
        topModelNode = self.getNodeForURI(targetURI)
        self._refreshTreeOnOpen_buildTree(0, 0, topModelNode)
        callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                          "")

    def doTreeCopyWithDestName(self, srcIndex, targetIndex, newPath, callback):
        #log.debug("doTreeCopyWithDestName: srcIndex:%d, targetIndex:%d, newPath:%s)", srcIndex, targetIndex, newPath)
        srcNode = self._rows[srcIndex]
        targetNode = self._rows[targetIndex]
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'srcIndex': srcIndex,
                                     'srcNode': srcNode,
                                     'targetIndex': targetIndex,
                                     'targetNode': targetNode,
                                     'newPath': newPath,
                                     'callback': callback,
                                    }
        finally:
            self.lock.release()
        srcNode.infoObject.show_busy()
        self._tree.invalidateRow(srcIndex)
        targetNode.infoObject.show_busy()
        self._tree.invalidateRow(targetIndex)
        #log.debug("%s %s %s", "copy", srcNode.getPath(), targetNode.getPath())
        self.workerThread.put(('doTreeCopyWithDestName',
                               {'requestID':requestID,
                                'requester':self},
                               'post_doTreeCopyWithDestName'))
        
    def post_doTreeCopyWithDestName(self, rv, requestID):
        srcIndex, originalSrcNode, targetIndex, originalTargetNode,\
            newPath, updateTargetTree, callback = self.getItemsByRequestID(
                requestID, 'srcIndex', 'srcNode',
                'targetIndex', 'targetNode', 'newPath',
                'updateTargetTree', 'callback')
        if rv:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                              rv)
            return
        fixedSrcIndex, fixedSrcNode = \
           self._postRequestCommonNodeHandling(originalSrcNode, srcIndex,
                                               "post_doTreeCopyWithDestName")
        fixedTargetIndex, fixedTargetNode = \
           self._postRequestCommonNodeHandling(originalTargetNode, targetIndex,
                                               "post_doTreeCopyWithDestName")
        if fixedSrcIndex == -1 or fixedTargetIndex == -1:
            # Things to do?
            self._tree.invalidate()
            return
        elif fixedSrcIndex != srcIndex:
            doInvalidate = True
            srcIndex = fixedSrcIndex
            srcNode = self._rows[srcIndex]
        elif fixedTargetIndex != targetIndex:
            doInvalidate = True
            targetIndex = fixedTargetIndex
            targetNode = self._rows[targetIndex]
        else:
            doInvalidate = False
            srcNode = originalSrcNode
            targetNode = originalTargetNode

        if updateTargetTree:
            cls = srcNode.infoObject.__class__ # clone
            newURI = targetNode.getURI() + "/" + os.path.basename(newPath)
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                    createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = newURI;
            newNode = _HierarchyNode(targetNode.level + 1, cls(fileObj=koFileEx))
            if newNode.isContainer:
                if self._isLocal:
                    self._addWatchForChanges(newNode.getPath())
                if self.isContainerOpen(targetIndex):
                    finalIdx = self._getTargetIndex(os.path.basename(newPath), targetIndex)
                    self._rows = (self._rows[:finalIdx]
                                  + [newNode]
                                  + self._rows[finalIdx:])
                    self._tree.rowCountChanged(finalIdx, 1)
        self._originalRows = self._rows
        self._buildFilteredView()

    def doTreeCopyWithDestNameAndURI(self, srcIndex, targetURI, newPath, callback):
        #log.debug("doTreeCopyWithDestName: srcIndex:%d, targetURI:%s, newPath:%s)", srcIndex, targetIndex, newPath)
        srcNode = self._rows[srcIndex]
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'srcIndex': srcIndex,
                                     'srcNode': srcNode,
                                     'targetURI': targetURI,
                                     'newPath': newPath,
                                     'callback': callback,
                                    }
        finally:
            self.lock.release()
        srcNode.infoObject.show_busy()
        self._tree.invalidateRow(srcIndex)
        targetNode.infoObject.show_busy()
        self._tree.invalidateRow(targetIndex)
        #log.debug("%s %s %s", "copy", srcNode.getPath(), targetNode.getPath())
        self.workerThread.put(('doTreeCopyWithDestNameAndURI',
                               {'requestID':requestID,
                                'requester':self},
                               'post_doTreeCopyWithDestNameAndURI'))
        
    def post_doTreeCopyWithDestNameAndURI(self, rv, requestID):
        srcIndex, originalSrcNode, targetURI,\
            newPath, updateTargetTree, callback = self.getItemsByRequestID(
                requestID, 'srcIndex', 'srcNode',
                'targetURI', 'newPath',
                'updateTargetTree', 'callback')
        if rv:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_ERROR,
                              rv)
            return
        fixedSrcIndex, fixedSrcNode = \
           self._postRequestCommonNodeHandling(originalSrcNode, srcIndex,
                                               "post_doTreeCopyWithDestNameAndURI")
        if fixedSrcIndex == -1:
            # Things to do?
            self._tree.invalidate()
            return
        elif fixedSrcIndex != srcIndex:
            doInvalidate = True
            srcIndex = fixedSrcIndex
            srcNode = self._rows[srcIndex]
        else:
            doInvalidate = False
            srcNode = originalSrcNode

        if updateTargetTree:
            cls = srcNode.infoObject.__class__ # clone
            newURI = targetURI + "/" + os.path.basename(newPath)
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                    createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = newURI;
            newNode = _HierarchyNode(targetNode.level + 1, cls(fileObj=koFileEx))
            if newNode.isContainer and self._isLocal:
                self._addWatchForChanges(newNode.getPath())
            #TODO: Sort this correctly
            finalIdx = self._getTargetIndex(os.path.basename(newPath), targetIndex)
            self._rows = (self._rows[:finalIdx]
                                  + [newNode]
                                  + self._rows[finalIdx:])
            self._tree.rowCountChanged(finalIdx, 1)

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
        for i in range(len(self._rows)):
            if self._rows[i].getPath() == path:
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
                and candidateNode.getName().lower() > newBaseName_lc):
                return i
        else:
            log.debug("Must be the highest node at this level")
            return targetNodeLastChildIndex

    def closePlace(self):
        lenBefore = len(self._rows)
        self._originalRows = self._rows = []
        self.resetLiveRows()
        self._tree.rowCountChanged(0, -lenBefore)
        self._currentPlace_uri = None
        self.dragDropUndoCommand.clearArgs()
        
        
    def openPlace(self, uri, callback=None):
        #qlog.debug(">> openPlace(uri:%s)", uri)
        placeFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        placeFileEx.URI = uri
        self._isLocal = placeFileEx.isLocal
        if placeFileEx.isFile:
            placeFileEx.path = placeFileEx.dirName
            uri = placeFileEx.URI
        if self._isLocal:
            self._addWatchForChanges(placeFileEx.path)
        else:
            #log.debug("openPlace: not local:(%s)", uri)
            pass

        self._currentPlace_uri = uri
        if self._nodeOpenStatusFromName.get(uri, False):
            #qlog.debug("openNodesByURIPrefs.hasPref(%s) is true", uri)
            forceOpen = False
        else:
            #qlog.debug("???? openNodesByURIPrefs.hasPref(%s) is false", uri)
            forceOpen = True

        item = self.getNodeForURI(uri)
        if item is None:
            item = _KoPlaceItem(_PLACE_FOLDER, uri, placeFileEx.baseName)
            self.setNodeForURI(uri, item)
        self._originalRows = self._rows = []
        if True or folderObject.isOpen:  #TODO: remove this line
            #qlog.debug("ok folderObject.isOpen:")
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
        before_len = len(self._rows)
        anchor_index = 0
        self._refreshTreeOnOpen_buildTree(0, 0, topModelNode)
        self.resetLiveRows()
        after_len = len(self._rows)
        self._tree.rowCountChanged(anchor_index, after_len - before_len)
        if callback:
            callback.callback(components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL,
                              "")

    def _refreshTreeOnOpen_buildTree(self, level, rowIndex, parentNode):
        assert parentNode.type == _PLACE_FOLDER
        #qlog.debug(">> _refreshTreeOnOpen_buildTree: level:%d, rowIndex:%d", level, rowIndex)
        for childNode in parentNode.childNodes:
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                       createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = childNode.uri
            #qlog.debug("insert %s at slot %d", koFileEx.baseName, rowIndex)
            newNode = _HierarchyNode(level,
                                     placeObject[childNode.type](fileObj=koFileEx))
            self._rows.insert(rowIndex, newNode)
            isOpenNode = self.isContainerOpen(rowIndex)
            rowIndex += 1
            if isOpenNode:
                rowIndex = self._refreshTreeOnOpen_buildTree(level + 1, rowIndex, childNode)
        #qlog.debug("<< _refreshTreeOnOpen_buildTree(rowIndex:%d)", rowIndex)
        return rowIndex
        

    def addNewFileAtParent(self, basename, parentIndex):
        parentPath = self._rows[parentIndex].getPath()
        if self._isLocal:
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
        self._insertNewItemAtParent(parentIndex)

    def addNewFolderAtParent(self, basename, parentIndex):
        parentPath = self._rows[parentIndex].getPath()
        if self._isLocal:
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
            perms = self._umaskFromPermissions(self, conn.list(parentPath, False))
            conn.createDirectory(fullPath, perms)
        self._insertNewItemAtParent(parentIndex)

    def _insertNewItemAtParent(self, targetIndex, targetNode, koFileEx, basename):
        if not self.isContainer(targetIndex):
            return
        elif not self.isContainerOpen(targetIndex):
            self.toggleOpenState(targetIndex)
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
        uri = rowNode.getURI()
        modelNode = self.getNodeForURI(uri)
        if modelNode.childNodes:
            return True
        elif not modelNode.needsRefreshing():
            return False
        # Look at the system, don't rely on the tree.
        # No point updating the childNodes list, as we're about to delete this node.
        path = rowNode.getPath()
        if self._isLocal:
            return len(os.listdir(path)) > 0
        conn = self._RCService.getConnectionUsingUri(uri)
        try:
            rfi = conn.list(path, True)
            children = rfi.getChildren()
            return len(children) > 0
        finally:
            conn.close()

    def deleteItem(self, index, deleteContents):
        requestID = self.getRequestID()
        rowNode = self._rows[index]
        self.lock.acquire()
        try:
            self._data[requestID] = {'index':index,
                                     'node':rowNode,
                                     }
        finally:
            self.lock.release()
        rowNode.infoObject.show_busy()
        self._tree.invalidateRow(index)
        self.workerThread.put(('deleteItem',
                               {'index': index,
                                'deleteContents':deleteContents,
                                'node':rowNode,
                                'requestID':requestID,
                                'requester':self},
                               'post_deleteItem'))

    def post_deleteItem(self, rv, requestID):
        index, originalNode = self.getItemsByRequestID(requestID, 'index', 'node')
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                    "post_deleteItem")
        if rv:
            sendStatusMessage(rv)
            #todo: callback.callback()
            return
        if fixedIndex != index:
            doInvalidate = True
            index = fixedIndex
        else:
            doInvalidate = False
        # Verify the item is deleted
        if self.isContainerOpen(index):
            nextIndex = self.getNextSiblingIndex(index)
            if nextIndex == -1:
                nextIndex = len(self._rows)
        else:
            nextIndex = index + 1
        self.removeSubtreeFromModelForURI(self._rows[index].getURI())
        del self._rows[index:nextIndex]
        self.resetLiveRows()
        self._tree.rowCountChanged(index, index - nextIndex)
        if doInvalidate:
            self.invalidateTree()

    def _postRequestCommonNodeHandling(self, originalNode, index, context):
        originalNode.infoObject.restore_icon()
        rowNode = self._rows[index]
        if rowNode != originalNode:
            try:
                fixed_index = self._rows.index(originalNode)
                index = fixed_index
                self._tree.invalidateRow(index)
            except ValueError:
                # Nodes have changed, try looking by uri
                i = 0
                uri = originalNode.getURI()
                for row in self._rows:
                    if uri == row.getURI():
                        log.debug("Found uri %s at index %d", uri, i)
                        index = i
                        rowNode = row
                        break
                    i += 1
                else:
                    log.error("Can't find index %d in current tree", index)
                    return -1, rowNode
        else:
            self._tree.invalidateRow(index)
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

    def getCellProperties(self, row_idx, column, properties):
        #assert col.id == "name"
        col_id = column.id
        try:
            rowNode = self._rows[row_idx]
            for propName in rowNode.getCellPropertyNames(col_id):
                try:
                    properties.AppendElement(self._atomsFromName[propName])
                except KeyError:
                    log.debug("getCellProperties: no property for %s",
                               propName)
        except AttributeError:
            log.exception("getCellProperties(row_idx:%d, col_id:%r",
                          row_idx, col_id)
            return ""
        if not hasattr(rowNode, 'properties'):
            # Like in koKPFTreeView.p.py, these are kept cached, unless
            # there's a change.  Changes within Komodo will be broadcast
            # via notifications
            rowNode.properties = self._buildCellProperties(rowNode)
        for prop in rowNode.properties:
            properties.AppendElement(self.atomSvc.getAtom(prop))
            # ???? self._atomsFromName[prop])
    
    def _updateFileProperties(self, idx, koFileEx):
        rowNode = self._rows[idx]
        rowNode.koFileObject = koFileEx
        try:
            #log.debug("_updateFileProperties: idx:%d, koFileEx:%s", idx, koFileEx.path)
            del rowNode.properties
        except AttributeError:
            pass
            
    def _buildCellProperties(self, rowNode):
        properties = []
        if not self._isLocal:
            return properties
        node = rowNode.infoObject
        if not hasattr(rowNode, 'koFileEx'):
            rowNode.koFileObject = \
               components.classes["@activestate.com/koFileService;1"].\
               getService(components.interfaces.koIFileService).\
               getFileFromURI(rowNode.getURI())
        if not rowNode.koFileObject:
            return properties
        koFileObject = UnwrapObject(rowNode.koFileObject)
        if koFileObject.isReadOnly:
            properties.append("isReadOnly")
        return properties


    def isContainer(self, index):
        #log.debug(">> isContainer[%d] => %r", index, self._rows[index].isContainer)
        return self._rows[index].infoObject.isContainer
    
    def isContainerOpen(self, index):
        #log.debug(">> isContainerOpen[%d] => %r", index, self._rows[index].infoObject.isOpen)
        return self._rows[index].infoObject.isOpen
        
    def isContainerEmpty(self, index):
        #log.debug(">> isContainerEmpty[%d] => %r", index, len(self._rows[index].childNodes) == 0)
        try:
            return self.isContainer(index) and len(self._rows[index].childNodes) == 0
        except AttributeError, ex:
            node = self._rows[index]
            log.exception("level: %d, infoObject:%r, connectorObject:%r, isContainer:%r",
                           node.level,
                           node.infoObject,
                           node.connectorObject,
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

    def getNextSiblingIndex_OffOriginal(self, index):
        """
        @param index {int} points to the node whose next-sibling we want to find.
        @return index of the sibling, or -1 if not found.
        """
        level = self._originalRows[index].level
        lim = len(self._originalRows)
        index += 1
        while index < lim:
            if self._originalRows[index].level <= level:
                return index
            index += 1
        return -1


    def refreshView(self, index):
        rowNode = self._rows[index]
        #qlog.debug("refreshView(index:%d)", index)
        if not rowNode.infoObject.isOpen:
            #qlog.debug("not rowNode.infoObject.isOpen:")
            return
        nextIndex = self.getNextSiblingIndex(index)
        #qlog.debug("nextIndex: %d", nextIndex)
        if nextIndex == -1:
            nextIndex = len(self._rows)
            #qlog.debug("adjust for -1, nextIndex: %d", nextIndex)
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'index':index,
                                     'nextIndex':nextIndex,
                                     'firstVisibleRow':self._tree.getFirstVisibleRow(),
                                     'node':rowNode}
        finally:
            self.lock.release()
        rowNode.infoObject.show_busy()
        self._tree.invalidateRow(index)
        self.workerThread.put(('toggleOpenState_Open',
                               {'index': index,
                                'node':rowNode,
                                'uri':rowNode.getURI(),
                                'forceRefresh':True,
                                'requestID':requestID,
                                'requester':self},
                               'post_refreshView'))
        
    def post_refreshView(self, rv, requestID):
        index, nextIndex, originalNode, firstVisibleRow =\
            self.getItemsByRequestID(requestID, 'index', 'nextIndex', 'node', 'firstVisibleRow')
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                         "post_refreshView")
        if 0:
            log.debug("post_refreshView: index:%d, nextIndex:%d, firstVisibleRow:%d, fixedIndex:%d, originalNode.getURI():%s, rowNode.getURI():%s",
                   index, nextIndex, firstVisibleRow, fixedIndex,
                   originalNode.getURI(),
                   rowNode.getURI())
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
            doInvalidate = True
        else:
            doInvalidate = False
        self._finishRefreshingView(index, nextIndex, doInvalidate, rowNode,
                                   firstVisibleRow)

    def _finishRefreshingView(self, index, nextIndex, doInvalidate, rowNode,
                              firstVisibleRow):
        before_len = len(self._rows)
        first_child_index = index + 1
        #qlog.debug("Delete rows %d:%d", first_child_index, nextIndex)
        del self._rows[first_child_index:nextIndex]
        before_len_2 = len(self._rows)
        topModelNode = self.getNodeForURI(rowNode.getURI())
        self._refreshTreeOnOpen_buildTree(rowNode.level + 1,
                                          first_child_index,
                                          topModelNode)
        self.resetLiveRows()
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
        # And always filter after
        self._originalRows = self._rows
        self._buildFilteredView() #XXX reinstate.

    def resetLiveRows(self): # from koKPFTreeView.p.py
        if not self._isLocal:
            return
        # Too expensive to watch closed nodes too -- then we can mark them for refershing
        liverows = set([row.getPath()
                        for row in self._rows
                        if row.infoObject.isOpen])
        #print "resetLiveRows %d" % len(liverows)
        newnodes = liverows.difference(self._liverows)
        oldnodes = self._liverows.difference(liverows)
        for dir in oldnodes:
            self._removeWatchForChanges(dir)
        for dir in newnodes:
            self._addWatchForChanges(dir)
        self._liverows = liverows

    def renameItem(self, index, newBaseName, forceClobber):
        rowNode = self._rows[index]
        fileObj = rowNode.infoObject.fileObj
        dirName = fileObj.dirName
        path = fileObj.path
        if self._isLocal:
            newPath = os.path.join(dirName, newBaseName)
            if os.path.exists(newPath):
                if os.path.isdir(newPath):
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem: invalid operation: you can't rename existing directory: %s" % (newPath))
                if not forceClobber:
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem failure: file %s exists" % newPath)
                os.unlink(newPath)
            os.rename(path, newPath)
        else:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            newPath = dirName + "/" + newBaseName
            rfi = conn.list(newPath, False)
            if rfi:
                if rfi.isDirectory():
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem: invalid operation: you can't rename existing directory: %s::%s" % (conn.server, newPath))
                if not forceClobber:
                    raise ServerException(nsError.NS_ERROR_INVALID_ARG, "renameItem failure: file %s::%s exists" % (conn.server, newPath))
                conn.removeFile(newPath)
            conn.rename(path, newPath)
        uri = fileObj.URI
        self.removeSubtreeFromModelForURI(uri)
        parent_uri = uri[:uri.rindex("/")]
        index = self.getRowIndexForURI(parent_uri, considerFiltered=True)
        if index != -1:
            #qlog.debug("renameItem: refresh parent %s at %d", parent_uri, index)
            self.refreshView(index)

    def sortRows(self):
        if self._rows:
            index = 0
            rowNode = self._rows[index]
            topModelNode = self.getNodeForURI(rowNode.getURI())
            #qlog.debug("\n\nBefore sorting: topModelNode: %s", topModelNode)
            self._sortModel(rowNode.getURI())
            #qlog.debug("After sorting: topModelNode: %s\n\n", topModelNode)
            nextIndex = len(self._rows)
            doInvalidate = False
            firstVisibleRow = self._tree.getFirstVisibleRow()
            self._finishRefreshingView(index, nextIndex, doInvalidate, rowNode,
                                       firstVisibleRow)

    def sortBy(self, sortKey, direction):
        self._sortedBy = sortKey
        self._sortDir = direction
            
    def toggleOpenState(self, index):
        rowNode = self._rows[index]
        #qlog.debug("toggleOpenState: index:%d", index)
        #qlog.debug("toggleOpenState: rowNode.infoObject.isOpen: %r", rowNode.infoObject.isOpen)
        if rowNode.infoObject.isOpen:
            if self.exclude_patterns or self.include_patterns:
                # Clear the filter
                # Re-call this function, to close the full node
                # Reapply the filter, and rebuild list
                include_patterns = self.include_patterns
                exclude_patterns = self.exclude_patterns
                # originalIndex = self._originalRows.index(rowNode)
                originalIndex = self._rows.index(rowNode)
                origLen = len(self._rows)
                self._rows = self._originalRows
                self._tree.rowCountChanged(0, len(self._rows) - origLen)
                if self._rows[originalIndex].infoObject.isOpen:
                    self.include_patterns = []
                    self.exclude_patterns = []
                    self.toggleOpenState(originalIndex)
                self.include_patterns = include_patterns
                self.exclude_patterns = exclude_patterns
                self._originalRows = self._rows
                self._buildFilteredView()
                return
            
            try:
                del self._nodeOpenStatusFromName[rowNode.getURI()]
            except KeyError:
                pass
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
                self.resetLiveRows()
                #log.debug("index:%d, numNodesRemoved:%d, numLeft:%d", index, numNodesRemoved, len(self._rows))
            rowNode.infoObject.isOpen = False
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
            rowNode.infoObject.show_busy()
            self._tree.invalidateRow(index)
            self.workerThread.put(('toggleOpenState_Open',
                                   {'index': index,
                                    'node':rowNode,
                                    'uri':rowNode.getURI(),
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
        uri = rowNode.getURI()
        self._nodeOpenStatusFromName[uri] = True
        self._sortModel(uri)
        topModelNode = self.getNodeForURI(uri)
        if self._isLocal:
            self._addWatchForChanges(rowNode.getPath())
        if not topModelNode.childNodes:
            #qlog.debug("Node we opened has no children")
            rowNode.unsetContainer()
            if doInvalidate:
                self.invalidateTree()
            else:
                self._tree.beginUpdateBatch()
                self._tree.invalidateRow(index)
                self._tree.endUpdateBatch()
            return
        firstVisibleRow = self._tree.getFirstVisibleRow()
        rowNode.infoObject.isOpen = True
        self._tree.invalidateRow(index)
        self._finishRefreshingView(index, index + 1, doInvalidate, rowNode,
                                   firstVisibleRow)

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
        originalIndex = self._originalRows.index(rowNode)
        self._rows = self._originalRows
        self._tree.rowCountChanged(0, len(self._rows) - origLen)
        if self._rows[originalIndex].infoObject.isOpen:
            self.toggleOpenState(originalIndex)
        self._originalRows = self._rows
        self._buildFilteredView()
        
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
        names = os.listdir(path)
        items = []
        for name in names:
            full_name = os.path.join(path, name)
            if os.path.isdir(full_name):
                itemType = _PLACE_FOLDER
            elif os.path.isfile(full_name):
                itemType = _PLACE_FILE
            else:
                itemType = _PLACE_OTHER
            item = self._finishGettingItem(uri + "/" + name, name, itemType)
            items.append(item)
        return items

    def getDirListFromRemoteURI(self, uri):
        conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
        try:
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
                item = self._finishGettingItem(uri + "/" + name, name, itemType)
                items.append(item)
            return items
        finally:
            conn.close()
        

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
        threading.Thread.__init__(self, kwargs)
        Queue.__init__(self)

    def run(self):
        while 1:
            request, args, callback = self.get()
            if not request:
                break
            try:
                rv = getattr(self, request)(args)
            except:
                log.exception("Request:%s", request)
                rv = "Exception: request:%s, message:%s" % (request, sys.exc_info()[1])
            treeView = args['requester']
            treeView.proxySelf.handleCallback(callback, rv, args['requestID'])

    def refreshTreeOnOpen(self, args):
        uri = args['uri']
        requester = args['requester']
        newRows = self.refreshTreeOnOpen_Aux(requester, uri)
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
        if forceRefresh or itemNode.needsRefreshing():
            if requester._isLocal:
                items = requester.getDirListFromLocalPath(uri)
            else:
                items = requester.getDirListFromRemoteURI(uri)
            itemNode.childNodes = items
            itemNode.lastUpdated = time.time()
        else:
            items = itemNode.childNodes
        for item in items:
            if requester._nodeOpenStatusFromName.get(item.uri, False):
                self.refreshTreeOnOpen_Aux(requester, item.uri, forceRefresh)

    def toggleOpenState_Open(self, args):
        requester = args['requester']
        uri = args['uri']
        forceRefresh = args['forceRefresh']
        #qlog.debug("toggleOpenState_Open: forceRefresh:%r", forceRefresh)
        self.refreshTreeOnOpen_Aux(requester, uri, forceRefresh)
        requester._sortModel(uri)
        return ""

    def selectURI_toggleNodeOpen(self, args):
        requester = args['requester']
        uri = args['uri']
        self.refreshTreeOnOpen_Aux(requester, uri)
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

    def deleteItem(self, args):
        node = args['node']
        requester = args['requester']
        deleteContents = args['deleteContents']
        path = node.getPath()
        if requester._isLocal:
            sysUtils = components.classes["@activestate.com/koSysUtils;1"].\
                              getService(components.interfaces.koISysUtils)
            try:
                res = sysUtils.MoveToTrash(path)
                if not res:
                    return "Failed to remove %s" % (path,)
            except:
                log.exception("sysUtils.MoveToTrash(%s) failed", path)
                if os.path.isdir(path):
                    if deleteContents:
                        from distutils.dir_util import remove_tree
                        remove_tree(path)
                    else:
                        os.rmdir(path)
                else:
                    os.unlink(path)
        else:
            uri = node.getURI()
            conn = requester._RCService.getConnectionUsingUri(uri)
            try:
                rfi = conn.list(path, True)
                if rfi.isDirectory():
                    self._deleteRemoteDirectoryContents(conn, rfi)
                    conn.removeDirectory(path)
                else:
                    conn.removeFile(path)
                rfi2 = conn.list(path, False)
                if rfi2:
                    return("deleteItem: failed to delete %s on server %s" % (path, conn.server))
            finally:
                conn.close()
        return ""

    def doTreeOperation(self, args):
        requester = args['requester']
        requestID = args['requestID']
        requester.lock.acquire()
        try:
            requester_data = requester._data[requestID]
        finally:
            requester.lock.release()
        srcIndex = requester_data['srcIndex']
        srcNode = requester_data['srcNode']
        targetNode = requester_data.get('targetNode', None)
        if targetNode is None:
            targetURI = requester_data.get('targetURI', None)
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                       createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = targetURI
            targetDirPath = koFileEx.path
        else:
            targetURI = targetNode.getURI()
            targetDirPath = targetNode.getPath()
        copying = requester_data['copying']
        
        srcPath = srcNode.getPath()
        finalMsg = ""

        # When we copy or move an open folder, the target folder will be
        # closed, even if it was open before.  Windows explorer works this way.
        clearDragDropUndoCommand = True
        if requester._isLocal:
            targetFile = os.path.join(targetDirPath, os.path.basename(srcPath))
            updateTargetTree = not os.path.exists(targetFile)
            #XXX Watch out if targetFile is an open folder.
            if not copying:
                shutil.move(srcPath, targetFile)
                requester.lock.acquire()
                try:
                    requester.dragDropUndoCommand.update(targetFile, srcPath, True)
                finally:
                    requester.lock.release()
                clearDragDropUndoCommand = False
            elif requester.isContainer(srcIndex):
                self._copyLocalFolder(srcPath, targetDirPath)
            else:
                shutil.copy(srcPath, targetFile)
                # Nothing to undo
        else:
            conn = requester._RCService.getConnectionUsingUri(requester._currentPlace_uri)
            try:
                targetFile = targetDirPath + "/" + srcNode.getName()
                target_rfi = conn.list(targetFile, True)
                updateTargetTree = not target_rfi
                #XXX Watch out if targetFile is an open folder.
                if not copying:
                    conn.rename(srcPath, targetFile)
                    requester.lock.acquire()
                    try:
                        requester.dragDropUndoCommand.update(targetURI + "/" + srcNode.getName(), srcNode.getURI(), False)
                    finally:
                        requester.lock.release()
                    clearDragDropUndoCommand = False
                elif requester.isContainer(srcIndex):
                    requester_data['uncopied_symlinks'] = []
                    requester_data['unrecognized_filetypes'] = []
                    self._copyRemoteFolder(conn, srcPath, targetDirPath, requester_data)
                    if requester_data['uncopied_symlinks'] or requester_data['unrecognized_filetypes']:
                        finalMsg = ("There were problems copying folder %s to %s:\n"
                               % (srcPath, targetDirPath))
                        if requester_data['uncopied_symlinks']:
                            finalMsg += "\nThe following symbolic links weren't copied:\n"
                            finalMsg += "\n    ".join(requester_data['uncopied_symlinks'])
                        if requester_data['unrecognized_filetypes']:
                            finalMsg += "\nThe following files had an unexpected type:\n"
                            finalMsg += "\n    ".join(requester_data['unrecognized_filetypes'])
                else:
                    try:
                        data = "<not read yet>"
                        # Determine if there's nothing left to do after copying
                        data = conn.readFile(srcPath)
                        conn.writeFile(targetFile, data)
                    except:
                        log.exception("can't copy file %s (data:%s))",
                                      srcPath, data)
                        return ("Exception: can't copy file %s (data:%s)): %s" %
                                srcPath, data, sys.exc_info()[1])
            finally:
                conn.close()
        requester_data['finalMsg'] = finalMsg
        requester_data['updateTargetTree'] = updateTargetTree
        if not copying:
            srcURI = srcNode.getURI()
            parentURI = srcURI[:srcURI.rindex("/")]
            self.refreshTreeOnOpen_Aux(requester, parentURI, forceRefresh=True)
        self.refreshTreeOnOpen_Aux(requester, targetURI, forceRefresh=True)
        return ""

    #---- Local tree copying: shutil.copytree works when only target doesn't exist,
    #     so copy parts manually, and use shutil.copytree for new sub-parts.
    
    def _copyLocalFolder(self, srcPath, targetDirPath):
        targetFinalPath = os.path.join(targetDirPath, os.path.basename(srcPath))
        if not os.path.exists(targetFinalPath):
            shutil.copytree(srcPath, targetFinalPath, symlinks=True)
        else:
            for d in os.listdir(srcPath):
                candidate = os.path.join(srcPath, d)
                if os.path.isdir(candidate):
                    self._copyLocalFolder(candidate, targetFinalPath)
                else:
                    shutil.copy(candidate, os.path.join(targetFinalPath, d))

    #---- Remote file copying

    def _copyRemoteFolder(self, conn, srcPath, targetDirPath, requester_data):
        # Do this as a depth-first walk
        rfi = conn.list(srcPath, True)
        if rfi is None:
            raise Exception("internal error: _copyRemoteFolder: can't resolve srcPath=%s (targetDirPath:%s)" % 
                            (srcPath, targetDirPath))
        self._copyRemoteItem(conn, rfi, targetDirPath, requester_data)

    def _umaskFromPermissions(self, rfi):
        umask = 0
        if rfi.isReadable():
            umask += 4
        if rfi.isWriteable():
            umask += 2
        if rfi.isExecutable():
            umask += 1
        return umask

    def _copyRemoteFile(self, conn, rfi, targetDirPath):
        targetPath = targetDirPath + "/" + rfi.getFilename()
        conn.createFile(targetPath, self._umaskFromPermissions(rfi))
        conn.writeFile(targetPath, conn.readFile(rfi.getFilepath()))

    def _copyRemoteDirectoryAndContents(self, conn, rfi, targetDirPath, requester_data):
        targetPath = targetDirPath + "/" + rfi.getFilename()
        conn.createDirectory(targetPath, self._umaskFromPermissions(rfi))
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

    def doTreeCopyWithDestName(self, args):
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
        srcIndex = requester_data['srcIndex']
        srcNode = requester_data['srcNode']
        targetNode = requester_data['targetNode']
        newPath = requester_data['newPath']
        
        srcPath = srcNode.getPath()
        targetDirPath = targetNode.getPath()
        updateTargetTree = False
        if requester._isLocal:
            try:
                updateTargetTree = not os.path.exists(newPath)
                shutil.copy(srcPath, newPath)
            except (Exception, IOError), ex:
                finalMsg = ("doTreeCopyWithDestName: can't copy %s to %s: %s" %
                            (srcPath, newPath, ex.message))
                log.exception("%s", finalMsg)
                return finalMsg
        else:
            conn = requester._RCService.getConnectionUsingUri(requester._currentPlace_uri)
            target_rfi = conn.list(newPath, True)
            updateTargetTree = not target_rfi
            try:
                data = conn.readFile(srcPath)
                conn.writeFile(newPath, data)
            except:
                finalMsg = ("doTreeCopyWithDestName: can't copy file %s to %s: %s" %
                            (srcPath, newPath, ex.message))
                log.exception("%s", finalMsg)
                return finalMsg
            finally:
                conn.close()
        requester_data['updateTargetTree'] = updateTargetTree
        return ''

    def doTreeCopyWithDestNameAndURI(self, args):
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
        srcNode = requester_data['srcNode']
        newPath = requester_data['newPath']
        
        srcPath = srcNode.getPath()
        updateTargetTree = False
        if requester._isLocal:
            try:
                updateTargetTree = not os.path.exists(newPath)
                shutil.copy(srcPath, newPath)
            except (Exception, IOError), ex:
                finalMsg = ("doTreeCopyWithDestName: can't copy %s to %s: %s" %
                            (srcPath, newPath, ex.message))
                log.exception("%s", finalMsg)
                return finalMsg
        else:
            conn = requester._RCService.getConnectionUsingUri(requester._currentPlace_uri)
            target_rfi = conn.list(newPath, True)
            updateTargetTree = not target_rfi
            try:
                data = conn.readFile(srcPath)
                conn.writeFile(newPath, data)
            except:
                finalMsg = ("doTreeCopyWithDestName: can't copy file %s to %s: %s" %
                            (srcPath, newPath, ex.message))
                log.exception("%s", finalMsg)
                return finalMsg
            finally:
                conn.close()
        requester_data['updateTargetTree'] = updateTargetTree
        return ''

    def setMainFilters(self, args):
        # Another do-nothing routine just used to serialize requests
        return ''
    
