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

from xpcom import components
from xpcom._xpcom import PROXY_SYNC, PROXY_ALWAYS, PROXY_ASYNC, getProxyForObject
from xpcom.server import WrapObject, UnwrapObject
 
import sys, os, re, types, string, threading
from koTreeView import TreeView
from URIlib import FileHandler

import logging

log = logging.getLogger("ProjectTreeView")
#log.setLevel(logging.DEBUG)

class nodeGenerator(threading.Thread):
    _cacheSize=1
    
    def __init__(self, treeview, node=None, level=0, childrenOnly=0):
        threading.Thread.__init__(self, name="ProjectTreeView")
        
        self._stop = 0
        self.treeview = treeview
        self.node = node
        self.level = level
        self.childrenOnly = childrenOnly
        self.cache=[]

    def stop(self):
        self._stop = 1
        try:
            self.treeview._observerProxy.notifyObservers(self.treeview, "kpf_tree_filter_status", "stopped")
        except:
            # noone listening
            pass
        
    def stopped(self):
        return self._stop
    
    def start(self):
        try:
            self.treeview._observerProxy.notifyObservers(self.treeview, "kpf_tree_filter_status", "searching")
        except:
            # noone listening
            pass
        threading.Thread.start(self)

    def run(self):
        self.node.generateRows(self,
                           self.treeview._nodeIsOpen,
                           sortBy=self.treeview._sortedBy,
                           level=self.level,
                           filterString=self.treeview._filterString,
                           sortDir=self.treeview._sortDir,
                           childrenOnly=self.childrenOnly)
        if not self._stop:
            self.emptyCache()
            self.stop()
        
    def emptyCache(self):
        if not self._stop:
            for row in self.cache:
                if self._stop:
                    return
                index = self.treeview.addRow(row)
            self.cache = []
            # we do this so the UI refreshes correctly
            self.treeview._wrapSelfAsync.invalidate()
        
    def addRow(self, row):
        if not self._stop:
            self.cache.append(row)
            if len(self.cache) % self._cacheSize == 0:
                self.emptyCache()

def compareNodeFolder(a, b, field):
    a_c = hasattr(a, 'children')
    b_c = hasattr(b, 'children')
    if a_c and not b_c:
        return -1
    elif b_c and not a_c:
        return 1
    return compareNode(a,b,field)

def compareNode(a, b, field):
    aval = a.getFieldValue(field)
    bval = b.getFieldValue(field)
    if isinstance(aval, types.StringTypes):
        return cmp(aval.lower(), bval.lower())
    return cmp(aval, bval)

# base class for the tree node generation.  this is subclassed by either the
# single kpf tree or the multi kpf tree.  It is used inside the nsITreeView
# below.  The treeview cannot use both at the same time and will throw
# exceptions if an attempt is made.
class KPFTree:
    # tree support
    def __init__(self, treeview):
        self.children = []
        self._sortedBy = 'name'
        self._sortDir = 0
        self.liverows = set([])
        self.treeview = treeview
        self.notificationSvc = components.classes["@activestate.com/koFileNotificationService;1"].\
                                    getService(components.interfaces.koIFileNotificationService)

    def _sortNodes(self, nodes, sortBy, sortDir, force=False):
        if force or self._sortedBy != sortBy or self._sortDir != sortDir:
            log.debug("KPFTree::_sortNodes()")
            if sortDir != 0:
                nodes.sort(lambda a,b: compareNodeFolder(a, b, sortBy) * sortDir)
            else:
                nodes.sort(lambda a,b: compareNode(a, b, sortBy))
            self._sortDir = sortDir # cache sort order
            self._sortedBy = sortBy # cache sort order
        else:
            log.debug("KPFTree::_sortNodes:: already sorted")

    def matchesFilter(self, child, filterString):
        """Returns a boolean indicating if this node matches the filter."""
        return child.name.lower().find(filterString.lower()) != -1

    def resetLiveRows(self):
        #print "Rows:"
        #for row in rows:
        #    print row
        liverows = set([ row['node'].get_liveDirectory() for row in self.treeview._rows if row['node'].live and row['is-open'] and hasattr(row['node'], 'get_liveDirectory') ])
        #print "resetLiveRows %d" % len(liverows)
        newnodes = liverows.difference(self.liverows)
        oldnodes = self.liverows.difference(liverows)
        for dir in oldnodes:
            if not dir: continue
            self.notificationSvc.removeObserver(self.treeview, dir)
        for dir in newnodes:
            if not dir: continue
            self.notificationSvc.addObserver(self.treeview, dir,
                                             components.interfaces.koIFileNotificationService.WATCH_DIR,
                                             _notificationsToReceive)
        self.liverows = liverows

# the KPFSingleTree class is used for tree views that do not have multiple projects
# for instance, toolbox and shared toolbox, where a single kpf file is used in
# the view
class KPFSingleTree(KPFTree):
    def __init__(self, treeview, kpf):
        KPFTree.__init__(self, treeview)
        self.kpf = kpf
        self.children = kpf.getChildren()

    def generateRows(self, generator, nodeIsOpen, sortBy='name', level=0,
                     filterString=None, sortDir=0, childrenOnly=0):

        log.debug("KPFSingleTree::generateRows")
        children = self.children[:]
        numChildren = len(self.children)
        if numChildren > 1:
            self._sortNodes(children, sortBy, sortDir, force=True)

        for i in range(numChildren):
            child = children[i]
            child.generateRows(generator, nodeIsOpen, sortBy, level, filterString, sortDir=sortDir)

        #self.kpf.generateRows(generator, nodeIsOpen, sortBy, level, filterString, sortDir=sortDir, childrenOnly=1)
        self.resetLiveRows()

# the KPFMultiTree class is used for tree views that can have multiple projects
# for instance, the project view
class KPFMultiTree(KPFTree):
        
    def append(self, kpf):
        self.children.append(kpf)

    def remove(self, kpf):
        self.children.remove(kpf)

    def generateRows(self, generator, nodeIsOpen, sortBy='name', level=0,
                     filterString=None, sortDir=0, childrenOnly=0):
        log.debug("KPFMultiTree::generateRows")
        # we leave projects in order they were opened
        numChildren = len(self.children)
        for i in range(numChildren):
            child = self.children[i]
            child.generateRows(generator, nodeIsOpen, sortBy, level, filterString, sortDir=sortDir)
        self.resetLiveRows()

# some constants used for live folders
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

# nsITreeView class used with the partviewer xbl binding.
class KPFTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIKPFTreeView,
                        components.interfaces.nsITreeView,
                        components.interfaces.koIFileNotificationObserver]
    _reg_clsid_ = "{216F0F44-D15B-11DA-8CBD-000D935D3368}"
    _reg_contractid_ = "@activestate.com/koKPFTreeView;1"
    _reg_desc_ = "Komodo KPF Tree View"
        
    def __init__(self, debug=None):
        TreeView.__init__(self, debug=0)
        self._root = None
        self._rows = []
        self._datapoints = {}
        
        # Mapping of node "scoped-name" to a boolean indicating if that
        # node is open (or should be) in the Code Browser.
        self._nodeIsOpen = {}
        self._filterString = ''
        self._sortedBy = 'name'
        self._sortDir = 0

        self._tree = None
        self._document = None
        self._ft = None
        self._dataLock = threading.RLock()
        self.atomService = components.classes["@mozilla.org/atom-service;1"].\
                                getService(components.interfaces.nsIAtomService)
        # Get a handle on the Komodo asnychronous operations service. Used for
        # checking and displaying a in-progress image on the tree view.
        self._asyncOpSvc = components.classes['@activestate.com/koAsyncService;1'].\
                getService(components.interfaces.koIAsyncService)
        
        wrapSelf = WrapObject(self, components.interfaces.koIKPFTreeView)
        self._wrapSelf = getProxyForObject(1, components.interfaces.koIKPFTreeView,
                                          wrapSelf, PROXY_SYNC | PROXY_ALWAYS)
        self._wrapSelfAsync = getProxyForObject(1, components.interfaces.koIKPFTreeView,
                                          wrapSelf, PROXY_ASYNC | PROXY_ALWAYS)
        self._prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        #self.log = logging.getLogger("ProjectTreeView")
        #self.log.setLevel(logging.DEBUG)

        self.__io_service = components.classes["@mozilla.org/network/protocol;1?name=file"].\
                    getService(components.interfaces.nsIFileProtocolHandler)

        _proxyMgr = components.classes["@mozilla.org/xpcomproxy;1"].\
            getService(components.interfaces.nsIProxyObjectManager)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._observerProxy = _proxyMgr.getProxyForObject(None,
            components.interfaces.nsIObserverService, self._observerSvc,
            PROXY_ALWAYS | PROXY_SYNC)

        # XXX if we ever get more than one project viewer, this will be an issue
        self._partSvc = components.classes["@activestate.com/koPartService;1"]\
            .getService(components.interfaces.koIPartService)
        self._observerSvc.addObserver(self, "file_status",0)

    def observe(self, subject, topic, data):
        if topic == "file_status":
            # find the row for the file and invalidate it
            files = data.split("\n")
            self._dataLock.acquire()
            try:
                invalidRows = [i for (i,row) in enumerate(self._rows)
                               if 'file' in row and row['file'] and row['file'].URI in files]
                for row in invalidRows:
                    if 'properties' in self._rows[row]:
                        del self._rows[row]['properties']
            finally:
                self._dataLock.release()
            if invalidRows:
                self._tree.beginUpdateBatch()
                self._tree.invalidateRange(invalidRows[0],invalidRows[-1])
                self._tree.endUpdateBatch()

    # row generator interface
    def stopped(self):
        return 0

    # nsIFileNotificationObserver
    # we want to receive notifications for any live folders in our view
    # the addition of observers will occur during generateRows
    def fileNotification(self, uri, flags):
        #print "got notification [%s] flags %d"%(uri,flags)
        changed = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        changed.URI = uri
        matching_parts = []
        #print "   path is [%r] dirname [%r]"%(changed.path, changed.dirName)

        if flags & _rebuildFlags:
            log.debug("received fileNotification flags: %r, path: %r", flags,
                      changed.path);
            self._dataLock.acquire()
            try:
                for row in self._rows:
                    part = row["node"]
                    if hasattr(part,'get_liveDirectory'):
                        path = part.get_liveDirectory()
                    else:
                        if "file" not in row:
                            row["file"] = part.getFile()
                        file = row["file"]
                        if not file:
                            continue
                        path = file.path
                    if not path:
                        continue
                    #print "row is: %s" % (file.path)
                    if flags & _createdFlags and path == changed.dirName or \
                       path == changed.path:
                        matching_parts.append((part, path))
            finally:
                self._dataLock.release()
            if not matching_parts:
                return
            if flags & _createdFlags:
                for part, path in matching_parts:
                    if path == changed.dirName:
                        #print "Found parent, refreshing it now"
                        #print "Before:", row["node"].getChildren()
                        part.needrefresh = 1
                        self.refresh(part)
                        #print "After:", row["node"].getChildren()
            elif flags & _rebuildDirFlags:
                for part, path in matching_parts:
                    while part and not hasattr(part, "refreshChildren"):
                        part = part._parent
                    if part:
                        part.needrefresh = 1
                        self.refresh(part)
            elif path == changed.path:
                for part, path in matching_parts:
                    # file or dir deleted
                    #print "   compare [%r]==[%r]"%(file.path,changed.path)
                    part._parent.removeChild(part)
                    self.refresh(part._parent)
        else:
            # this is a modification change, just invalidate rows
            self._tree.invalidate()

    # nsIProjectTreeView
    def set_toolbox(self, kpf):
        if isinstance(self._root, KPFMultiTree):
            raise Exception("Toolbox set into project tree")
        if self._root:
            self.savePrefs(self._root.kpf)
        if not kpf:
            if not self._root:
                return

            # remove rows for project
            self._dataLock.acquire()
            try:
                num_rows = len(self._rows)
                self._rows = []
                self._tree.rowCountChanged(0, -num_rows)
                self._root = None
            finally:
                self._dataLock.release()
    
            return

        kpf = UnwrapObject(kpf)
        self.restorePrefs(kpf)
        self._root = KPFSingleTree(self, kpf)
        
    def get_toolbox(self):
        return self._root.kpf

    def addProject(self, kpf):
        if isinstance(self._root, KPFSingleTree):
            raise Exception("Project added to toolbox tree")
        self._partSvc.addProject(kpf)
        kpf = UnwrapObject(kpf)
        self.restorePrefs(kpf)
        if not self._root:
            self._root = KPFMultiTree(self)
            self._partSvc.currentProject = kpf
        self._root.append(kpf)
        if kpf.id not in self._nodeIsOpen:
            self._nodeIsOpen[kpf.id] = True
    
    def removeProject(self, kpf):
        if isinstance(self._root, KPFSingleTree):
            raise Exception("Project removal from toolbox tree")
        self._partSvc.removeProject(kpf)
        kpf = UnwrapObject(kpf)
        index = self._root.children.index(kpf)
        self.savePrefs(kpf)

        self._root.remove(kpf)
        if index > 0:
            # previous project becomes active
            self.set_currentProject(self._root.children[index-1])
        elif len(self._root.children) > 0:
            # first project becomes active
            self.set_currentProject(self._root.children[0])
        else:
            # closing the only project we have, no current project
            self.set_currentProject(None)

        # remove rows for project
        self._dataLock.acquire()
        try:
            index = self._getIndexByPart(kpf)
            sibling = self._getNextSiblingIndex(index)
            self._rows = self._rows[:index]+self._rows[sibling:]
            self._tree.rowCountChanged(index, (index - sibling))
        finally:
            self._dataLock.release()

    # XXX fixme save/restore doesn't work because the part id's change
    # every startup of komodo.  There is no permanently unique identifier
    # for a project part
    def restorePrefs(self, kpf):
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                            .getService().prefs # global prefs
        if prefSvc.hasStringPref("kpf_open_nodes_%s" % kpf.id):
            nioStr = prefSvc.getStringPref("kpf_open_nodes_%s" % kpf.id)
            try:
                nodeIsOpen = eval(nioStr)
                self._nodeIsOpen.update(nodeIsOpen)
            except SyntaxError, ex:
                pass

    def savePrefs(self, kpf):
        prefSvc = components.classes["@activestate.com/koPrefService;1"]\
                            .getService().prefs # global prefs
        if isinstance(self._root, KPFSingleTree):
            nodeIsOpen = self._nodeIsOpen
        else:
            # multi tree, we want JUST the project passed in.  Get all the
            # id's from the project, and then get the matching id's from
            # nodeIsOpen
            kpf = UnwrapObject(kpf)
            nodeIsOpen = {}
            for id in self._nodeIsOpen.keys():
                if kpf.getChildById(id):
                    nodeIsOpen[id] = self._nodeIsOpen[id]
        prefSvc.setStringPref("kpf_open_nodes_%s" % kpf.id,
                              repr(nodeIsOpen))

    def get_currentProject(self):
        return self._partSvc.currentProject
    
    def set_currentProject(self, prj):
        if isinstance(self._root, KPFSingleTree):
            raise Exception("Use toolbox member to set the toolbox")
        self._partSvc.currentProject = prj
        project = UnwrapObject(prj)
        if project and project not in self._root.children:
            raise Exception("Add the project to the view before making it the current project")
        if project is not None:
            index = self.getIndexByPart(prj)
            # if the project is not already visible, make it so
            firstVisRow = self._tree.getFirstVisibleRow()
            lastVisRow = self._tree.getLastVisibleRow()
            numVisRows = self._tree.getPageLength()
            #print "set_currentProject"
            #print "numVisRows: %d" % (numVisRows)
            #print "firstVisRow: %d" % (firstVisRow)
            #print "lastVisRow: %d" % (lastVisRow)
            # If completely outside the range
            # Or if there is un-utilized (empty) rows shown in the tree
            # Or the index is in the visible range, but the tree contents
            # scroll past the end of the visible range
            nextSibling = self._getNextSiblingIndex(index)
            if (index < firstVisRow or index >= lastVisRow or
                (len(self._rows) > numVisRows and
                 ((nextSibling - index) > numVisRows or
                  len(self._rows) < (firstVisRow + numVisRows)))):
                scrollToIndex = min(index, len(self._rows) - numVisRows)
                #print "Scrolling to row: %d" % (scrollToIndex)
                self._tree.scrollToRow(scrollToIndex)

    def _getNextSiblingIndex(self, index):
        # do not lock this function, used from within locked blocks
        level = self._rows[index]["level"]
        rc = len(self._rows)
        i = index + 1
        while i < rc and self._rows[i]["level"] > level:
            i = i + 1
        return i

    def addRow(self, row):
        # add this row into our rows index
        self._dataLock.acquire()
        try:
            if row['level'] > 0:
                part = row['node']
                index = self._getIndexByPart(part.get_parent())
                # insert this prior to the parents sibling
                sibling = self._getNextSiblingIndex(index)
                self._rows.insert(sibling, row)
            else:
                self._rows.append(row)
                index = len(self._rows) - 1
            return self._rows.index(row)
        finally:
            self._dataLock.release()
    
    def invalidate(self):
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()
        
    def stopGenerator(self):
        if self._ft:
            self._ft.stop()
        
    def regenerateRows(self, node, level=0, childrenOnly=0):
        log.debug("KPFTreeView::regenerateRows")
        if self._filterString:
            # use a background thread to generate our node list
            self._ft = nodeGenerator(self, node)
            self._ft.start()
        else:
            num_rows_before = len(self._rows)
            node.generateRows(self, self._nodeIsOpen,
                                    self._sortedBy, 
                                    filterString=self._filterString,
                                    sortDir=self._sortDir,
                                    level=level,
                                    childrenOnly=childrenOnly)

    def refresh(self, part):
        """ return the row that should be selected if that's relevant"""
        log.debug("KPFTreeView::refresh()")
        self._dataLock.acquire()
        changed = 0
        retval = 0
        level = 0
        index = -1
        # firstVisibleRow and firstVisiblePart are used to restore the treeview
        # position to the same place after the refresh is done. Fixes bug:
        # http://bugs.activestate.com/show_bug.cgi?id=71331
        firstVisibleRow = self._tree.getFirstVisibleRow()
        firstVisiblePart = None
        if firstVisibleRow >= 0 and firstVisibleRow < len(self._rows):
            firstVisiblePart = self._rows[firstVisibleRow]["node"]
        # Remember the selection as well
        selectedParts = self.getSelectedItems()

        try:
            node = None
            if part:
                part = UnwrapObject(part)
                index = self._getIndexByPart(part)
                if index >= 0 and index < len(self._rows):
                    node = self._rows[index]['node']
                    level = self._rows[index]['level']

            # if we get a part, we just refresh that
            if node:
                # remove the children from the rows
                self.stopGenerator()
                sibling = self._getNextSiblingIndex(index)
                self._rows = self._rows[:index+1] + self._rows[sibling:]
                #print "rowCountChanged(%d, %d)" %(index+1, (index+1) - sibling)
                self._tree.rowCountChanged(index+1, (index+1) - sibling)
                changed = 1
            elif self._root:
                self.stopGenerator()
                node = self._root
                num_rows = len(self._rows)
                self._rows = []
                #print "rowCountChanged(%d, %d)" % (0, -num_rows)
                self._tree.rowCountChanged(0, -num_rows)
                changed = 1
        finally:
            self._dataLock.release()

        if changed:
            num_rows = len(self._rows)
            self.regenerateRows(node, level=level, childrenOnly=1)
            if len(self._rows) != num_rows:
                #print "rowCountChanged(%d, %d)" % (index+1, len(self._rows) - num_rows)
                self._tree.rowCountChanged(index+1, len(self._rows) - num_rows)
            # Ensure the toggle state is correctly redrawn, fixes bug:
            #   http://bugs.activestate.com/show_bug.cgi?id=71942
            self._tree.invalidateRow(index)
            self._root.resetLiveRows()

            # Restore the treeview position back to how it originally was
            if firstVisiblePart:
                index = self._getIndexByPart(firstVisiblePart)
                if index >= 0:
                    #print "Scrolling to firstVisiblePart: %d" % (index)
                    self._tree.scrollToRow(index)
                elif firstVisibleRow < len(self._rows):
                    #print "Scrolling to firstVisibleRow: %d" % (firstVisibleRow)
                    self._tree.scrollToRow(firstVisibleRow)
            # Restore the selections
            if selectedParts:
                self.selectParts(selectedParts)

        return retval

    def addColumnDatapoint(self, name, value):
        self._datapoints[name.lower()]=value
        #print self._datapoints

    def getSelectedItems(self):
        # return the selected koIParts
        items = []
        self._dataLock.acquire()
        try:
            if not self._rows:
                return items
            if self.selection.single:
                # deselect all other selections except the current one
                self.selection.select(self.selection.currentIndex)
                items.append(self._rows[self.selection.currentIndex]["node"])
            else:
                for i in range(len(self._rows)):
                    if self.selection.isSelected(i):
                        items.append(self._rows[i]["node"])
            return items
        finally:
            self._dataLock.release()
    
    def getSelectedItem(self):
        self._dataLock.acquire()
        try:
            try:
                return self._rows[self.selection.currentIndex]["node"]
            except IndexError, e:
                return None
        finally:
            self._dataLock.release()

    def _getIndexByPart(self, part):
        # do not lock this function, used from within locked blocks
        # XXX possible optimization to change our rows array
        nodes = [row["node"] for row in self._rows]
        try:
            return nodes.index(part)
        except ValueError, e:
            return -1

    def getIndexByPart(self, part):
        part = UnwrapObject(part)
        self._dataLock.acquire()
        try:
            return self._getIndexByPart(part)
        finally:
            self._dataLock.release()

    def getRowItem(self, index):
        self._dataLock.acquire()
        try:
            if index >= 0 and index < len(self._rows):
                return self._rows[index]["node"]
        finally:
            self._dataLock.release()
        return None
    
    def selectPart(self, part):
        index = self.getIndexByPart(part)
        self.selection.select(index)

    def selectParts(self, parts):
        # Clear the current selection.
        self.selection.clearSelection()
        indeces = [ self._getIndexByPart(part) for part in parts ]
        indeces.sort()
        index = 0
        i = 0
        while i < len(indeces):
            index = indeces[i]
            i += 1
            if index < 0:
                # Part has been removed.
                continue
            to_index = index
            # Use the largest range possible for the selection.
            while i < len(indeces):
                if indeces[i] != to_index + 1:
                    break
                to_index += 1
                i += 1
            # Ranged select call, True means to append to the current selection
            self.selection.rangedSelect(index, to_index, True)

    def sortBy(self, key, direction):
        changed = 0

        self._dataLock.acquire()
        try:
            # get a current node that we can scroll to after sorting
            selectedNode = None
            if self._rows:
                selected = self.selection.currentIndex
                if selected < 0:
                    selected = self._tree.getFirstVisibleRow()
                if 0 <= selected < len(self._rows):
                    selectedNode = self._rows[selected]["node"]
            
            name = key.lower()
            if name in self._datapoints:
                key = self._datapoints[name]
            else:
                key = name

            if self._sortedBy != key or self._sortDir != direction:
                self._sortedBy = key
                self._sortDir = direction
                if self._root:
                    #print "sortBy regenerating rows on %s"%key
                    self.stopGenerator()
                    num_rows = len(self._rows)
                    self._rows = []
                    self._tree.rowCountChanged(0, -num_rows)
                    changed = 1
        finally:
            self._dataLock.release()

        if self._root and changed:
            self.regenerateRows(self._root)
            self._tree.rowCountChanged(0, len(self._rows))
    
            # reset to the node we had selected before
            if selectedNode:
                index = self.getIndexByPart(selectedNode)
                if 0 <= index < len(self._rows):
                    self.selection.currentIndex = index
                    self.selection.select(index);      
                    self._tree.ensureRowIsVisible(index)
                else:
                    self._tree.ensureRowIsVisible(0)

    def setFilter(self, filterString):
        if filterString in ['\n','\r','\r\n']:
            filterString = ""
        elif filterString and filterString.find('*') < 0:
            filterString = "*%s*" % filterString
        filterString = filterString.lower()
        if self._filterString == filterString:
            return
        self._filterString = filterString
        if not self._root:
            return
        self.stopGenerator()

        self._dataLock.acquire()
        try:
            num_rows = len(self._rows)
            self._rows = []
            self._tree.rowCountChanged(0, -num_rows)
        finally:
            self._dataLock.release()

        self.regenerateRows(self._root)
        self._tree.rowCountChanged(0, len(self._rows))

    #def addColumn(self, name, field):
    #    self._datapoints[name] = field
        
    # nsITreeView
    def isSeparator(self, index):
        return 0
    
    def get_rowCount( self ):
        self._dataLock.acquire()
        try:
            return len(self._rows)
        finally:
            self._dataLock.release()

    def getRowProperties( self, index, properties ):
        pass

    def _buildCellProperties(self, row, column):
        # do not lock this function, used from within locked blocks
        prop = []
        prop.append("primaryColumn")
        node = self._rows[row]['node']
        prop.append(node.type)
        
        if 'file' not in self._rows[row]:
            self._rows[row]['file'] = self._rows[row]['node'].getFile()
        if self._rows[row]['file']:
            f = UnwrapObject(self._rows[row]['file'])
            # missing, sccOk, sccSync, sccConflict, add, delete, edit,
            # isReadOnly, branch, integrate
            if self._asyncOpSvc.uriHasPendingOperation(f.URI):
                prop.append("asyncOperation")
            elif hasattr(f, 'exists') and not f.exists:
                prop.append("missing")
            else:
                if hasattr(f, 'get_scc'):
                    scc = f.get_scc()
                    if scc['sccAction']:
                        prop.append(scc['sccAction'])
                    if scc['sccOk']:
                        if isinstance(scc['sccOk'], basestring):
                            if int(scc['sccOk']):
                                prop.append("sccOk")
                        else:
                            prop.append("sccOk")
                    if scc['sccSync']:
                        if isinstance(scc['sccSync'], basestring):
                            if int(scc['sccSync']):
                                prop.append("sccSync")
                        else:
                            prop.append("sccSync")
                    if scc['sccConflict']:
                        prop.append("sccConflict")
                if hasattr(f, 'isReadOnly') and f.isReadOnly:
                    prop.append("isReadOnly")
        return prop
        
    def getCellProperties(self, index, column, properties):
        # here we build a list of properties that are used to get the icon
        # for the tree item, text style, etc.  *If getImageSrc returns
        # a url to an icon, the icon matched by properties here will be
        # ignored.  That is convenient since it allows custom icons to work*
        # XXX fixme, optimize
        if column.id != 'name':
            return
        plist = []
        self._dataLock.acquire()
        try:
            if index >= len(self._rows): return
            row = self._rows[index]
            # these are UI properties, such as the twisty, we want to always
            # get them
            if row["is-container"]:
                if row["is-open"]:
                    plist.append("open")
                else:
                    plist.append("closed")
                node = row['node']
                if node.type == "project" and node == UnwrapObject(self._partSvc.currentProject):
                    plist.append("projectActive")
            if 'properties' not in row:
                # these properties rarely change, keep them cached
                row['properties'] = self._buildCellProperties(index, column)
            plist.extend(row['properties'])
        finally:
            self._dataLock.release()

        #print "row %d %s : %r"% (row, column.id, plist)
        for p in plist:
            properties.AppendElement(self.atomService.getAtom(p))

    # in nsITreeColumn col, in nsISupportsArray properties
    def getColumnProperties(self, 
                            column,
                            properties):
        # Result: void - None
        # In: param0: wstring
        # In: param1: nsIDOMElement
        # In: param2: nsISupportsArray
        if self.log:
            self.log.debug("getColumnProperties(column=%s, props=%r)",
                           column, properties)

    def isContainer(self, index):
        self._dataLock.acquire()
        try:
            if index >= len(self._rows) or index < 0: return 0
            return self._rows[index]["is-container"]
        finally:
            self._dataLock.release()

    def isContainerOpen(self, index):
        self._dataLock.acquire()
        try:
            if index >= len(self._rows) or index < 0: return 0
            return self._rows[index]["is-open"]
        finally:
            self._dataLock.release()

    def isContainerEmpty( self, index ):
        self._dataLock.acquire()
        try:
            if index >= len(self._rows) or index < 0: return 0
            return self._rows[index]["is-empty"]
        finally:
            self._dataLock.release()

    def isSorted( self ):
        # Result: boolean
        return self._sortDir != 0

    def canDrop( self, index, orientation ):
        return 1

    def drop( self, row, orientation ):
        # Result: void - None
        # In: param0: int32
        # In: param1: int32
        if self.log:
            self.log.debug("drop()")
        pass

    def getParentIndex( self, index ):
        self._dataLock.acquire()
        try:
            if index >= len(self._rows) or index < 0: return -1
            try:
                i = index - 1
                l = self._rows[index]['level']
                while i > 0 and self._rows[i]['level'] >= l:
                    i -= 1
            except IndexError, e:
                i = -1
            return i
        finally:
            self._dataLock.release()

    def hasNextSibling( self, index, afterIndex ):
        self._dataLock.acquire()
        try:
            if index >= len(self._rows) or index < 0: return 0
            try:
                for n in self._rows[afterIndex + 1:]:
                    if self._rows[index]['level'] > n['level']:
                        return 0
                    if self._rows[index]['level'] == n['level']:
                        return 1
            except IndexError, e:
                pass
            return 0
        finally:
            self._dataLock.release()

    def getLevel(self, index):
        self._dataLock.acquire()
        try:
            if index >= len(self._rows) or index < 0: return -1
            return self._rows[index]['level']
        finally:
            self._dataLock.release()

    def getImageSrc(self, row, column):
        # see comment in getCellProperties regarding images
        # XXX fixme, optimize
        self._dataLock.acquire()
        try:
            if row >= len(self._rows) or row < 0: return ""
            if column.id.lower() == "name":
                node = self._rows[row]['node']
                if node._attributes.has_key('icon'):
                    #print "getImageSrc row %d [%s]"%(row,node._attributes['icon'])
                    return node._attributes['icon']
        finally:
            self._dataLock.release()
        return ""

    def getCellValue(self, row, column):
        self._dataLock.acquire()
        try:
            if row >= len(self._rows) or row < 0: return
            child = self._rows[row]['node']
        finally:
            self._dataLock.release()
        name = column.id.lower()
        if hasattr(child, name):
            return getattr(child, name)
        return ""

    def getCellText(self, row, column):
        # XXX fixme, optimize
        self._dataLock.acquire()
        try:
            if row >= len(self._rows) or row < 0: return
            child = self._rows[row]['node']
        finally:
            self._dataLock.release()
        name = column.id.lower()
        if name in self._datapoints:
            fieldname = self._datapoints[name]
        else:
            fieldname = name
        text = child.getFieldValue(fieldname)
        #print "field %s text %s" % (name, text)
        if not isinstance(text, basestring):
            if name == 'size':
                if text < 1024:
                    text = "%d bytes" % text
                elif text < 1024*1024:
                    text = "%d KB" % (text/1024)
                else:
                    text = "%d MB" % (text/(1024*1024))
            elif name == 'date':
                import time
                format = self._prefs.getStringPref("defaultDateFormat")
                t = time.localtime(text)
                text = time.strftime(format, t)
            else:
                text = str(text)
        #print "getCellText for row %d col %s is %s" %(row, name, text)
        if fieldname == 'name' and child.type == 'project' and child.get_isDirty():
            text = text+"*"
        return text

    def setTree(self, tree):
        self._tree = tree

    def toggleOpenState(self, index):
        if self._ft and not self._ft.stopped():
            # trying to toggle while searching causes all kinds of grief
            return
        #print "toggle row at index %d"%index
        self._dataLock.acquire()
        try:
            regen=0
            node = self._rows[index]["node"]
            isOpen = self._rows[index]["is-open"]
            self._nodeIsOpen[node.id] = not isOpen
            level = self._rows[index]["level"]
    
            # Must recalculate the rows.
            oldRowCount = len(self._rows)
            if isOpen:
                # just remove the children from the rows
                i = index + 1
                while i < oldRowCount and self._rows[i]["level"] > level:
                    i = i + 1
                #print "removing rows %d to %d" %(index,i)
                self._rows = self._rows[:index+1] + self._rows[i:]
                self._tree.rowCountChanged(index+1, ((index+1) - i))
            else:
                # just get the rows for the node, then insert them into our list
                regen=1
            self._rows[index]["is-open"] = not isOpen
        finally:
            self._dataLock.release()
        if regen:
            self.regenerateRows(node, level=level, childrenOnly=1)
            self._tree.rowCountChanged(index+1, (len(self._rows) - oldRowCount))
        # Ensure the toggle state is correctly redrawn, fixes bug:
        #   http://bugs.activestate.com/show_bug.cgi?id=71942
        self._tree.invalidateRow(index)
        self._root.resetLiveRows()

        self.selection.currentIndex = index
        self.selection.select(index);      

    def cycleHeader(self, column):
        # Result: void - None
        # In: param0: wstring
        # In: param1: nsIDOMElement
        if self.log:
            self.log.debug("cycleHeader()")
        pass
    def selectionChanged(self):
        # Result: void - None
        if self.log:
            self.log.debug("selectionChanged()")
        pass
    def cycleCell(self, row, column):
        # Result: void - None
        # In: param0: int32
        # In: param1: wstring
        if self.log:
            self.log.debug("cycleCell()")
        pass
    def isEditable(self, row, column):
        # Result: boolean
        # In: param0: int32
        # In: param1: wstring
        if self.log:
            self.log.debug("isEditable()")
        return 0
    def setCellText( self, param0, param1, param2 ):
        # Result: void - None
        # In: param0: int32
        # In: param1: wstring
        # In: param2: wstring
        if self.log:
            self.log.debug("setCellText()")
        pass
    def performAction(self, action):
        # Result: void - None
        # In: param0: wstring
        if self.log:
            self.log.debug("performAction(%s)" % action)
        pass
    def performActionOnRow(self, action, row):
        # Result: void - None
        # In: param0: wstring
        # In: param1: int32
        if self.log:
            self.log.debug("performActionOnRow(%s, %s)", action, row)
        pass
    def performActionOnCell(self, action, row, column):
        # Result: void - None
        # In: param0: wstring
        # In: param1: int32
        # In: param2: wstring
        if self.log:
            self.log.debug("performActionOnCell(%s, %s, %r)", action, row, column)
        pass

