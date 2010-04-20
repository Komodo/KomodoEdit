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


from xpcom import components, COMException, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject

from koTreeView import TreeView
log = logging.getLogger("KoPlaceTreeView")
log.setLevel(logging.DEBUG)

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

class _HierarchyNode(object):
    def __init__(self, level, infoObject):
        self.level = level
        self.infoObject = infoObject
        self.isContainer = infoObject.isContainer
        self.infoObject.isOpen = (self.isContainer
                       and self._nodeOpenStatusFromName.get(self.getURI(), False))
        if self.isContainer:
            self.childNodes = [_HierarchyNode(level + 1, _kplPlaceholder(None))]
            self.innerNodes = []  # Used for filtering.
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
        return fnmatch.fnmatch(self.getName(), filterString)

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

FILTER_EXCLUDED = 0
FILTER_INCLUDED = 1
FILTER_INCLUDED_AS_PARENT = 2

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
        self._root = None
        self._currentPlace_uri = None
        self._rows = []
        self._originalRows = self._rows  # For filtering
        self._filteredRows = None
        self._lastFilteredString = None
        self._lastSelectedRow = -1
        self._filterString = None
        #TODO: Update this for each place 
        self.exclude_patterns = []
        self.include_patterns = []

        self._sortedBy = 'name'
        self._sortDir = 0
        self._pending_filter_requests = 0
        self._nodeOpenStatusFromName = {}
        self._isLocal = True
        self._data = {} # How threads share results
        # Make this attr work like a class variable
        _HierarchyNode._nodeOpenStatusFromName = self._nodeOpenStatusFromName

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
        if not placesPrefs.hasPref("places-open-nodes"):
            placesPrefs.setPref("places-open-nodes",
                                components.classes["@activestate.com/koPreferenceSet;1"].createInstance())
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
        self._observerSvc.removeObserver(self, "file_status")
        self.workerThread.put((None, None, None))
        self.workerThread.join(3)
        self.set_currentPlace(None)

    def observe(self, subject, topic, data):
        # Taken from koKPFTreeView
        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return
        if topic == "file_status":
            # find the row for the file and invalidate it
            files = data.split("\n")
            invalidRows = [i for (i,row) in enumerate(self._rows)
                           if row.getURI() in files]
            for row in invalidRows:
                try:
                    del self._rows[row].properties
                except AttributeError:
                    pass
            if invalidRows:
                self._tree.beginUpdateBatch()
                map(self._tree.invalidateRow, invalidRows)
                self._tree.endUpdateBatch()

    # row generator interface
    def stopped(self):
        return 0

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
            self._insertFileObject(koFileEx, dirname)
        elif flags & _deletedFlags:
            self._removeFileObject(koFileEx, dirname)
        else:
            # this is a modification change, just invalidate rows
            idx = self._lookupFileObject(koFileEx)
            if idx >= 0:
                self._updateFileProperties(idx, koFileEx)
                self._tree.invalidateRow(idx)

    def _insertFileObject(self, koFileEx, dirname):
        basename = koFileEx.baseName
        basename_lc = basename.lower()
        i = 0
        for row in self._rows:
            if row.isContainer and row.getPath() == dirname:
                j = self.getNextSiblingIndex(i)
                if j == -1:
                    j = len(self._rows)
                target_index = -1
                for k in range(i + 1, j):
                    currName = self._rows[k].getName().lower()
                    if currName < basename_lc:
                        pass
                    elif currName == basename_lc:
                        break
                    else:
                        target_index = k
                        break
                else:
                    # It goes at the end
                    target_index = j
                if target_index >= 0:
                    full_name = koFileEx.path
                    name = basename
                    if koFileEx.isDirectory:
                        nodeType = _PLACE_FOLDER
                    else:
                        nodeType = _PLACE_FILE
                    newNode = _HierarchyNode(self._rows[i].level + 1,
                                             placeObject[nodeType](fileObj=koFileEx))
                    self._rows.insert(target_index, newNode)
                    self._tree.rowCountChanged(target_index - 1, 1)
                    break
            i += 1
        else:
            log.error("_insertFileObject: couldn't find dir %s for file %s",
                      dirname, koFileEx.baseName)

    def _removeFileObject(self, koFileEx, dirname):
        idx = self._lookupFileObject(koFileEx)
        if idx == -1:
            log.debug("_removeFileObject: couldn't find path %s", koFileEx.path)
        else:
            del self._rows[idx]
            self._tree.rowCountChanged(idx, -1)

    def _lookupFileObject(self, koFileEx):
        path = koFileEx.path
        i = 0
        for row in self._rows:
            if row.getPath() == path:
                return i
            i += 1
        return -1

    def get_currentPlace(self):
        return self._currentPlace_uri;
    
    def set_currentPlace(self, uri):
        if self._currentPlace_uri is not None:
            self.closePlace()
        if uri:
            self._currentPlace_uri = uri
            self.openPlace(uri)

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

    def setFilter(self, filterString):
        # Run the request through the worker thread, in case other
        # processes are working.  This will also collect multiple
        # events into one run.
        requestID = self.getRequestID()
        self.lock.acquire()
        try:
            self._data[requestID] = {'filterString':filterString}
        finally:
            self.lock.release()
        self._pending_filter_requests += 1
        self.workerThread.put(('setFilter',
                                {'requestID':requestID,
                                'requester':self},
                               'post_setFilter'))
        
    def post_setFilter(self, rv, requestID):
        filterString = self.getItemsByRequestID(requestID, 'filterString')[0]
        if not self._decrementCheckPendingFilters():
            return
        self._filterString = filterString
        self._buildFilteredView()

    def _buildFilteredView(self):
        if not self._rows:
            return
        origLen = len(self._rows)
        filterString = self._filterString
        restoreURI = None
        if not filterString:
            if self._lastFilteredString and self._lastSelectedRow > -1:
                self._lastFilteredString = None
                try:
                    restoreURI = self._rows[self._lastSelectedRow].getURI()
                except IndexError:
                    log.debug("no row at %d", self._lastSelectedRow)
        else:
            self._lastFilteredString = filterString
            
        for node in self._originalRows:
            node.includedInFilter = FILTER_EXCLUDED
        # Always include the first row in the full tree.
        self._filteredRows = [self._originalRows[0]]
        self._filteredRows[0].includedInFilter = FILTER_INCLUDED
        for i in range(1, len(self._originalRows)):
            node = self._originalRows[i]
            if self._nodeMatchesFilterOrContainsAMatch(filterString, node):
                #log.debug("include node %d (%s)", i, node.getURI())
                parentNodes = self.includeParentsInFilter(i)
                self._filteredRows += parentNodes# [p[1] for p in parentNodes]
                self._filteredRows.append(node)
                node.includedInFilter = FILTER_INCLUDED
                
        self._rows = self._filteredRows
        delta = len(self._rows) - origLen
        self._tree.rowCountChanged(0, delta)
        self._tree.invalidate()
        if restoreURI:
            # Keep the selected row
            for i in range(len(self._rows)):
                if self._rows[i].getURI() == restoreURI:
                    self.selection.currentIndex = i
                    self.selection.select(i)
                    self._tree.ensureRowIsVisible(i)
                    self._lastSelectedRow = i
                    # if the selected row is in the bottom half of the view,
                    # move it to the half-way point
                    fvrow = self._tree.getFirstVisibleRow()
                    if fvrow + self._tree.getPageLength() < len(self._rows):
                        lvrow = self._tree.getLastVisibleRow()
                        midpt = (fvrow + lvrow)/2
                        if midpt < i:
                            self._tree.scrollToRow(fvrow + i - midpt)
                        break
        else:
            self._lastSelectedRow = -1
        
            

    def _nodeMatchesFilterOrContainsAMatch(self, filterString, node,
                                           consultChildren=True):
        # First pass on the main include/exclude nodes
        look_at_excludes = True
        look_at_filename = True
        for include_pattern in self.include_patterns:
            if node.matchesFilter(include_pattern):
                look_at_excludes = False
                break
        if look_at_excludes:
            for exclude_pattern in self.exclude_patterns:
                if node.matchesFilter(exclude_pattern):
                    if consultChildren:
                        look_at_filename = False
                        break
                    else:
                        return False
        # The above are for a coarse filter.  Now having eliminated
        # the rough kind of item, we can go look at the current pattern.
        if (look_at_filename
            and (not filterString or node.matchesFilter(filterString))):
            return True
        if not node.isContainer or node.infoObject.isOpen:
            return False
        self.lock.acquire()
        try:
            innerNodes = node.innerNodes
        finally:
            self.lock.release()
        if consultChildren:
            for childNode in innerNodes:
                if self._nodeMatchesFilterOrContainsAMatch(filterString,
                                                           childNode,
                                                       consultChildren=False):
                    return True

    def getParentIndex_OffOriginalRow(self, index):
        if index >= len(self._originalRows) or index < 0: return -1
        try:
            i = index - 1
            level = self._originalRows[index].level
            while i > 0 and self._originalRows[i].level >= level:
                i -= 1
        except IndexError, e:
            i = -1
        return i

    def includeParentsInFilter(self, idx):
        parentNodes = []
        while idx > 0:
            parentIdx = self.getParentIndex_OffOriginalRow(idx)
            if parentIdx == -1:
                break
            node = self._originalRows[parentIdx]
            if node.includedInFilter != FILTER_EXCLUDED:
                break
            parentNodes.insert(0, node)
            node.includedInFilter = FILTER_INCLUDED_AS_PARENT
            idx = parentIdx
        return parentNodes
        
            
    def getRowIndexForURI(self, uri):
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
        uri = self.getItemsByRequestID(requestID, 'uri')[0]
        self._rows[0].infoObject.restore_icon()
        self._tree.invalidateRow(0)
        if rv:
            raise Exception(rv)
        index = self.getRowIndexForURI(uri)
        if index >= -1:
            self.selection.currentIndex = index
        
    def getURIForRow(self, index):
        return self._rows[index].getURI()
        
    def canDrag(self, index):
        try:
            return self._rows[index].level > 0
            # force build.
        except Exception, ex:
            log.exception("canDrag: %d: fails", index)

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
            
        # Now update the model:

        cls = srcNode.infoObject.__class__ # clone
        #XXX: remote: does this node need a URI?
        newURI = targetNode.getURI() + "/" + srcNode.getName();
        koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        koFileEx.URI = newURI;
        newNode = _HierarchyNode(targetNode.level + 1, cls(fileObj=koFileEx))

        if not copying and self.isContainerOpen(srcIndex):
            try:
                del self._nodeOpenStatusFromName[srcNode.getURI()]
            except KeyError:
                log.error("Shouldn't get this")
        
        #numChanged = 0
        # Save tree/row properties before we modify it
        if not copying:
            if self.isContainerOpen(srcIndex):
                srcRangeEnd = self.getNextSiblingIndex(srcIndex)
            else:
                srcRangeEnd = srcIndex + 1

        numChangedAtSrc = 0
        numChangedAtTarget = 0

        targetIsOpen = self.isContainerOpen(targetIndex)
        if not targetIsOpen:
            if not copying:
                self._rows = (self._rows[:srcIndex]
                              + self._rows[srcRangeEnd:])
                numChangedAtSrc = srcIndex - srcRangeEnd
                
            # else: leave rows the same -- nothing to show.
        else:
            finalIdx = self._getTargetIndex(srcNode.getName(), targetIndex)
            if not copying:
                if updateTargetTree: # File doesn't exist
                    if srcIndex < targetIndex:
                        self._rows = (self._rows[:srcIndex]
                                      + self._rows[srcRangeEnd:finalIdx]
                                      + [newNode]
                                      + self._rows[finalIdx:])
                    else:
                        self._rows = (self._rows[:finalIdx]
                                      + [newNode]
                                      + self._rows[finalIdx:srcIndex]
                                      + self._rows[srcRangeEnd:])
                    numChangedAtSrc = srcIndex - srcRangeEnd
                    numChangedAtTarget = 1
                else: # Target does exist, so don't create a new node.
                    self._rows = (self._rows[:srcIndex]
                                  + self._rows[srcRangeEnd:])
                    numChangedAtSrc = srcIndex - srcRangeEnd
            elif updateTargetTree: # File doesn't exist
                self._rows = (self._rows[:finalIdx]
                              + [newNode]
                              + self._rows[finalIdx:])
                numChangedAtTarget = 1
            # else there's nothing to do
        self._originalRows = self._rows
            
        # This is the easiest way to update the level counts of the copied/moved
        # item (and its children), and make sure it gets placed in the correct posn.
        # Update the later item first, so we don't have to add 1 to the srcIndex
        if numChangedAtSrc and srcIndex > targetIndex:
            self._tree.rowCountChanged(srcIndex, numChangedAtSrc)
        if numChangedAtTarget:
            self._tree.rowCountChanged(finalIdx, numChangedAtTarget)
            #XXX Shouldn't need to refresh; just need to sort targetNode's tree
            #self.refreshTreeOnOpen(targetNode)
        
        if numChangedAtSrc and srcIndex < targetIndex:
            self._tree.rowCountChanged(srcIndex, numChangedAtSrc)
        self._buildFilteredView()
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
            if self.isContainerOpen(targetIndex):
                finalIdx = self._getTargetIndex(os.path.basename(newPath), targetIndex)
                self._rows = (self._rows[:finalIdx]
                              + [newNode]
                              + self._rows[finalIdx:])
                self._originalRows = self._rows
                self._tree.rowCountChanged(finalIdx, 1)
        self._buildFilteredView()

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
        if self._currentPlace_uri:
            openNodesByURIPrefs = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService).prefs.\
                            getPref("places").getPref("places-open-nodes")
            #TODO: Clean out old URIs.
            openNodesByURIPrefs.setStringPref(self._currentPlace_uri,
                                              json.dumps(self._nodeOpenStatusFromName))
            if self._isLocal:
                path = self._rows[0].getPath()
                self.notificationSvc.removeObserver(self, path)
            
        lenBefore = len(self._rows)
        self._rows = []
        self._originalRows = self._rows
        self._tree.rowCountChanged(0, -lenBefore)
        self._currentPlace_uri = None
        self.dragDropUndoCommand.clearArgs()
        
        
    def openPlace(self, uri):
        placeFileEx = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        placeFileEx.URI = uri
        self._isLocal = placeFileEx.isLocal
        if placeFileEx.isFile:
            placeFileEx.file = placeFileEx.dirName
            uri = placeFileEx.URI
        if self._isLocal:
            self.notificationSvc.addObserver(self, placeFileEx.path,
                                             components.interfaces.koIFileNotificationService.WATCH_DIR,
                                             _notificationsToReceive)
        else:
            #log.debug("openPlace: not local:(%s)", uri)
            pass

        self._currentPlace_uri = uri
        openNodesByURIPrefs = components.classes["@activestate.com/koPrefService;1"].\
                              getService(components.interfaces.koIPrefService).prefs.\
                              getPref("places").getPref("places-open-nodes")
        if openNodesByURIPrefs.hasPref(uri):
            self._nodeOpenStatusFromName = json.loads(openNodesByURIPrefs.getStringPref(uri))
            forceOpen = False
        else:
            self._nodeOpenStatusFromName = {}
            forceOpen = True
        
        # Update the class variable
        _HierarchyNode._nodeOpenStatusFromName = self._nodeOpenStatusFromName

        folderObject = placeObject[_PLACE_FOLDER](fileObj=placeFileEx)
        homeFolderNode = _HierarchyNode(0, folderObject) 
        self._rows = [homeFolderNode]
        self._originalRows = self._rows
        self._tree.rowCountChanged(0, 1)
        if folderObject.isOpen:
            requestID = self.getRequestID()
            self.lock.acquire()
            try:
                self._data[requestID] = {'beforeLen':1}
            finally:
                self.lock.release()
            homeFolderNode.infoObject.show_busy()
            self._tree.invalidateRow(0)
            self.workerThread.put(('refreshTreeOnOpen',
                                   {'index': 0,
                                    'node':homeFolderNode,
                                    'requestID':requestID,
                                    'requester':self},
                                   'post_refreshTreeOnOpen'))
        elif forceOpen:
            self.toggleOpenState(0)

    def post_refreshTreeOnOpen(self, rv, requestID):
        newRows, beforeLen = self.getItemsByRequestID(requestID, 'items', 'beforeLen')
        self._rows[0].infoObject.restore_icon()
        self._tree.invalidateRow(0)
        if rv:
            # Do this after the request data was cleared
            raise Exception(rv)
        self._rows += newRows
        self._tree.rowCountChanged(beforeLen, len(newRows))

    def addNewFileAtParent(self, basename, parentIndex):
        parentNode = self._rows[parentIndex]
        parentPath = parentNode.getPath()
        koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                   createInstance(components.interfaces.koIFileEx)
        if self._isLocal:
            fullPath = os.path.join(parentPath, basename)
            if os.path.exists(fullPath):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s" % (basename, parentPath))
            f = open(fullPath, "w")
            f.close()
            koFileEx.path = fullPath
        else:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            fullPath = parentPath + "/" +  basename
            if conn.list(fullPath, False):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s:%s" % (basename, conn.server, parentPath))
            conn.createFile(fullPath, 0644)
            koFileEx.URI = parentNode.getURI() + "/" + basename
        self._insertNewItemAtParent(parentIndex, parentNode, koFileEx, basename)

    def addNewFolderAtParent(self, basename, parentIndex):
        parentNode = self._rows[parentIndex]
        parentPath = parentNode.getPath()
        koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                   createInstance(components.interfaces.koIFileEx)
        if self._isLocal:
            fullPath = os.path.join(parentPath, basename)
            if os.path.exists(fullPath):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s" % (basename, parentPath))
            os.mkdir(fullPath)
            koFileEx.path = fullPath
        else:
            conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
            fullPath = parentPath + "/" +  basename
            if conn.list(fullPath, False):
                raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                                      "File %s already exists in %s:%s" % (basename, conn.server, parentPath))
            perms = self._umaskFromPermissions(self, conn.list(parentPath, False))
            conn.createDirectory(fullPath, perms)
            koFileEx.URI = parentNode.getURI() + "/" + basename
        self._insertNewItemAtParent(parentIndex, parentNode, koFileEx, basename)

    def _insertNewItemAtParent(self, targetIndex, targetNode, koFileEx, basename):
        if not self.isContainer(targetIndex):
            return
        elif not self.isContainerOpen(targetIndex):
            self.toggleOpenState(targetIndex)
            return
        if not sys.platform.startswith('lin'):
            basename_lc = basename.lower()
        else:
            # Fold case on OSX and Windows
            basename_lc = basename
        nextParentSiblingIndex = self.getNextSiblingIndex(targetIndex)
        if nextParentSiblingIndex == -1:
            finalIndex = len(self._rows)  # Put the item at this point
        else:
            finalIndex = nextParentSiblingIndex - 1

        for i in range(targetIndex + 1, finalIndex + 1):
            row = self._rows[i]
            currName = row.getName().lower()
            if currName < basename_lc:
                pass
            elif currName == basename_lc:
                return # it's already there.
            else:
                target_index = i
                break
        else:
            # It goes at the end
            target_index = finalIndex + 1
        if target_index >= 0:
            full_name = koFileEx.path
            if koFileEx.isDirectory:
                nodeType = _PLACE_FOLDER
            else:
                nodeType = _PLACE_FILE
            newNode = _HierarchyNode(targetNode.level + 1,
                                     placeObject[nodeType](fileObj=koFileEx))
            self._rows.insert(target_index, newNode)
            self._tree.rowCountChanged(target_index, 1)

    #---- delete-item Methods

    def itemIsNonEmptyFolder(self, index):
        if not self.isContainer(index):
            return False
        node = self._rows[index]
        if (index < len(self._rows) - 1
            and node.level < self._rows[index + 1].level):
            return True
        # Look at the system, don't rely on the tree.
        path = node.getPath()
        if self._isLocal:
            return len(os.listdir(path)) > 0
        conn = self._RCService.getConnectionUsingUri(node.getURI())
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
        if fixedIndex != index:
            doInvalidate = True
            index = fixedIndex
        else:
            doInvalidate = False
        if self.isContainerOpen(index):
            nextIndex = self.getNextSiblingIndex(index)
            if nextIndex == -1:
                nextIndex = len(self._rows)
        else:
            nextIndex = index + 1
        del self._rows[index:nextIndex]
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
        # Code taken from koKPFTreeView:: KPFTreeView._buildCellProperties
        # missing, sccOk, sccSync, sccConflict, add, delete, edit,
        # isReadOnly, branch, integrate
        if hasattr(koFileObject, 'get_scc'):
            try:
                #log.debug("**************** File: %s: About to get scc info",
                #          rowNode.getPath())
                scc = koFileObject.get_scc()
                # log.debug("scc: %s", scc)
            except:
                log.exception("Failed to get_scc")
                return properties
            if scc['sccAction']:
                properties.append(scc['sccAction'])
            if scc['sccOk']:
                if isinstance(scc['sccOk'], basestring):
                    if int(scc['sccOk']):
                        properties.append("sccOk")
                else:
                    properties.append("sccOk")
            if scc['sccSync']:
                if isinstance(scc['sccSync'], basestring):
                    if int(scc['sccSync']):
                        properties.append("sccSync")
                else:
                    properties.append("sccSync")
            if scc['sccConflict']:
                properties.append("sccConflict")
            if hasattr(koFileObject, 'isReadOnly') and koFileObject.isReadOnly:
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
            while i > 0 and self._rows[i].level >= level:
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
        if not rowNode.infoObject.isOpen:
            return
        nextIndex = self.getNextSiblingIndex(index)
        if nextIndex == -1:
            nextIndex = len(self._rows)
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
                                'requestID':requestID,
                                'requester':self},
                               'post_refreshView'))
        
    def post_refreshView(self, rv, requestID):
        newRows, index, nextIndex, originalNode, firstVisibleRow =\
            self.getItemsByRequestID(requestID, 'items', 'index', 'nextIndex', 'node', 'firstVisibleRow')
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                         "post_refreshView")
        if fixedIndex == -1:
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
        self._rows = self._rows[0:index + 1] + newRows + self._rows[nextIndex:]
        self._originalRows = self._rows
        numRowChanged = len(newRows) - (nextIndex - index - 1)
        if numRowChanged:
            self._tree.rowCountChanged(index + 1, numRowChanged)
            self._tree.scrollToRow(firstVisibleRow)
        elif doInvalidate:
            self.invalidateTree()
        # And always filter after
        self._buildFilteredView()

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
        self.refreshView(self.getParentIndex_OffOriginalRow(index))
            
    def toggleOpenState(self, index):
        rowNode = self._rows[index]
        #log.debug("toggleOpenState: rowNode.infoObject.isOpen: %r", rowNode.infoObject.isOpen)
        if rowNode.infoObject.isOpen:
            if self._filterString or self.exclude_patterns or self.include_patterns:
                # Clear the filter
                # Re-call this function, to close the full node
                # Reapply the filter, and rebuild list
                filterString = self._filterString
                include_patterns = self.include_patterns
                exclude_patterns = self.exclude_patterns
                originalIndex = self._originalRows.index(rowNode)
                origLen = len(self._rows)
                self._rows = self._originalRows
                self._tree.rowCountChanged(0, len(self._rows) - origLen)
                if self._rows[originalIndex].infoObject.isOpen:
                    self._filterString = None
                    self.include_patterns = []
                    self.exclude_patterns = []
                    self.toggleOpenState(originalIndex)
                self._filterString = filterString
                self.include_patterns = include_patterns
                self.exclude_patterns = exclude_patterns
                self._buildFilteredView()
                return
            
            try:
                del self._nodeOpenStatusFromName[rowNode.getURI()]
            except KeyError:
                pass
            nextIndex = self.getNextSiblingIndex(index)
            if nextIndex == -1:
                # example: index=5, have 13 rows,  delete 7 rows [6:13), 
                numNodesRemoved = len(self._rows) - index - 1
                del self._rows[index + 1:]
            else:
                # example: index=5, have 13 rows, next sibling at index=10
                # delete rows [6:10): 4 rows
                numNodesRemoved = nextIndex - index - 1
                del self._rows[index + 1: nextIndex]
            if numNodesRemoved:
                self._tree.rowCountChanged(index + 1, -numNodesRemoved)
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
                                    'requestID':requestID,
                                    'requester':self},
                                   'post_toggleOpenState_Open'))

    def post_toggleOpenState_Open(self, rv, requestID):
        newRows, index, originalNode = self.getItemsByRequestID(requestID, 'items', 'index', 'node')
        fixedIndex, rowNode = self._postRequestCommonNodeHandling(originalNode, index,
                                                    "post_toggleOpenState_Open")
        if rv:
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
        self._nodeOpenStatusFromName[rowNode.getURI()] = True
        if len(newRows) == 0:
            rowNode.unsetContainer()
            if doInvalidate:
                self.invalidateTree()
            else:
                self._tree.beginUpdateBatch()
                self._tree.invalidateRow(index)
                self._tree.endUpdateBatch()
            return
        self._rows = self._rows[0:index + 1] + newRows + self._rows[index + 1:]
        if not self._filterString:
            self._originalRows = self._rows
        self._tree.rowCountChanged(index + 1, len(newRows))
        if doInvalidate:
            self.invalidateTree()
        self._buildFilteredView()

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
        filterString = self._filterString
        originalIndex = self._originalRows.index(rowNode)
        self._rows = self._originalRows
        self._tree.rowCountChanged(0, len(self._rows) - origLen)
        if self._rows[originalIndex].infoObject.isOpen:
            self.toggleOpenState(originalIndex)
        self._filterString = filterString
        self._buildFilteredView()
        
    def invalidateTree(self):
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()
                                                
    def setTree(self, tree):
        #log.debug(">> setTree")
        self._tree = tree

    #---- Other methods

    def getDirListFromLocalPath(self, path):
        names = os.listdir(path)
        items = []
        for name in names:
            full_name = os.path.join(path, name)
            if os.path.isdir(full_name):
                items.append((_PLACE_FOLDER, name))
            elif os.path.isfile(full_name):
                items.append((_PLACE_FILE, name))
            else:
                items.append((_PLACE_OTHER, name))
        return items

    def getDirListFromRemoteURI(self, rowNode):
        path = rowNode.getPath()
        conn = self._RCService.getConnectionUsingUri(self._currentPlace_uri)
        try:
            rfi = conn.list(path, True) # Really a stat
            if not rfi:
                raise Exception("Can't read path:%s on server:%s" %
                                (path, conn.server))
            rfi_children = rfi.getChildren()
            items = []
            for rfi in rfi_children:
                full_name = rfi.getFilepath()
                name = re.compile(r'[\\/]').split(full_name)[-1]
                child_uri = rowNode.getURI() + "/" + name
                # For remote we need to specify everything
                name_info = {'name':name,
                        'uri':child_uri,
                        'path':full_name,
                        }
                        
                name = rfi.getFilename()
                if rfi.isDirectory():
                    items.append((_PLACE_FOLDER, name))
                elif rfi.isFile():
                    items.append((_PLACE_FILE, name))
                else:
                    items.append((_PLACE_OTHER, name))
            return items
        finally:
            conn.close()

    def _compare_item1(self, item1, item2):
        res = item1[0] - item2[0]
        if not res:
            return res
        return cmp(item1[1], item2[1])

    def sortItemList(self, items):
        return sorted(items, cmp=self._compare_item1)

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
        rowNode = args['node']
        requester = args['requester']
        newRows = self.refreshTreeOnOpen_Aux(requester, rowNode)
        requestID = args['requestID']
        requester.lock.acquire()
        try:
            requester._data[requestID]['items'] = newRows
        finally:
            requester.lock.release()
        return ""

    def refreshTreeOnOpen_Aux(self, requester, rowNode):
        path = rowNode.getPath()
        newRows = []
        if requester._isLocal:
            items = requester.getDirListFromLocalPath(path)
        else:
            items = requester.getDirListFromRemoteURI(rowNode)
        if len(items) == 0:
            rowNode.infoObject.isOpen = False
            return newRows
        rowNode.infoObject.isOpen = True
        requester.sortItemList(items)
        newLevel = rowNode.level + 1
        parentURI = rowNode.getURI()
        for itemType, itemName in items:
            koFileEx = components.classes["@activestate.com/koFileEx;1"].\
                    createInstance(components.interfaces.koIFileEx)
            koFileEx.URI = parentURI + "/" + itemName
            newNode = _HierarchyNode(newLevel,
                                     placeObject[itemType](fileObj=koFileEx))
            newRows.append(newNode)
            if newNode.infoObject.isOpen:
                innerRows = self.refreshTreeOnOpen_Aux(requester, newNode)
                newRows += innerRows
                newNode.infoObject.isOpen = len(innerRows) > 0
        requester.lock.acquire()
        try:
            rowNode.innerNodes = newRows
        finally:
            requester.lock.release()
        return newRows

    def toggleOpenState_Open(self, args):
        rowNode = args['node']
        requester = args['requester']
        newRows = self.refreshTreeOnOpen_Aux(requester, rowNode)
        requestID = args['requestID']
        requester.lock.acquire()
        try:
            requester._data[requestID]['items'] = newRows
        finally:
            requester.lock.release()
        return ""

    def selectURI_toggleNodeOpen(self, args):
        rowNode = args['node']
        requester = args['requester']
        if not rowNode.infoObject.isOpen:
            return "selectURI: internal error: node %s isn't open" % (rowNode.getName())
        self.refreshTreeOnOpen_Aux(requester, rowNode)
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
                sysUtils.MoveToTrash(path)
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
        targetNode = requester_data['targetNode']
        copying = requester_data['copying']
        
        srcPath = srcNode.getPath()
        targetDirPath = targetNode.getPath()
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
                        requester.dragDropUndoCommand.update(targetNode.getURI() + "/" + srcNode.getName(), srcNode.getURI(), False)
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

    def setFilter(self, args):
        # Just use the thread to stack up requests.
        return ''

    def setMainFilters(self, args):
        # Another do-nothing routine just used to serialize requests
        return ''
    
