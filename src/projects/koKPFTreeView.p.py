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

from xpcom import components, COMException, nsError
from xpcom.server import WrapObject, UnwrapObject

import sys, os, re, types
from koTreeView import TreeView
import koToolbox2
import uriparse

import logging

log = logging.getLogger("ProjectTreeView")
#log.setLevel(logging.DEBUG)

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
_g_suffix = koToolbox2.PROJECT_FILE_EXTENSION

class _Node(object):
    uri = None
    path = None
    def __init__(self, part, level, project):
        self.part = part
        if part is not None:
            # Store the path and url - saves having to get the part's koIFile.
            self.uri = part.url
            self.path = uriparse.URIToPath(self.uri)
        self.level = level
        self.project = project
        self.isContainer = False

class _ContainerNode(_Node):
    def __init__(self, part, level, project):
        _Node.__init__(self, part, level, project)
        self.isContainer = True
        self.isOpen = False

class _ProjectNode(_ContainerNode):
    pass

class _UnopenedProjectNode(_Node):
    pass

class _GroupNode(_ContainerNode):
    def __init__(self, part, level, project):
        _ContainerNode.__init__(self, part, level, project)
        self.file = None

class _FolderNode(_Node):
    pass    

class _RemoteFolderNode(_Node):
    pass

class _FileNode(_Node):
    pass

class _RemoteFileNode(_Node):
    pass

def _compareNodeClassCheck(a, b):
    """Make sure that the true projects always appear before the
    MRU unopened projects
    """
    return cmp(a[0], b[0])

def _compareNodeValue(a, b, field):
    aval = a[2].getFieldValue(field)
    bval = b[2].getFieldValue(field)
    if isinstance(aval, types.StringTypes):
        return cmp(aval.lower(), bval.lower())
    return cmp(aval, bval)

def compareNodeFolder(a, b, field, sortDir):
    # Each field comes in as a tuple with values
    # 0: project, 1: unopened project
    # 1: classtype for rebuilding the node
    # 2: part
    res = _compareNodeClassCheck(a, b)
    if res:
        return res
    a2 = a[2]
    b2 = b[2]
    a_c = hasattr(a2, 'children')
    b_c = hasattr(b2, 'children')
    if a_c and not b_c:
        return -1
    elif b_c and not a_c:
        return 1
    return _compareNodeValue(a,b,field) * sortDir

def compareNode(a, b, field):
    res = _compareNodeClassCheck(a, b)
    if res:
        return res
    return _compareNodeValue(a, b, field)

class KPFTreeView(TreeView):
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIKPFTreeView,
                        components.interfaces.nsITreeView,
                        components.interfaces.koIFileNotificationObserver,
                        components.interfaces.nsISupportsWeakReference]
    _reg_clsid_ = "{216F0F44-D15B-11DA-8CBD-000D935D3368}"
    _reg_contractid_ = "@activestate.com/koKPFTreeView;1"
    _reg_desc_ = "Komodo KPF Tree View"
        
    def __init__(self, debug=None):
        TreeView.__init__(self, debug=0)
        self._rows = []
        
        # Mapping of node "scoped-name" to a boolean indicating if that
        # node is open (or should be) in the Code Browser.
        self._nodeIsOpen = {}
        self._sortedBy = 'name'
        self._sortDir = 0

        self._tree = None
        self.statusObserver = None
        #self.log = logging.getLogger("ProjectTreeView")
        #self.log.setLevel(logging.DEBUG)
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        self._observerSvc.addObserver(self, "file_status",True) # weakref

    def initialize(self):
        self.atomService = components.classes["@mozilla.org/atom-service;1"].\
                                getService(components.interfaces.nsIAtomService)
        self._prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        self._observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)

        # XXX if we ever get more than one project viewer, this will be an issue
        self._partSvc = components.classes["@activestate.com/koPartService;1"]\
            .getService(components.interfaces.koIPartService)
        self._observerSvc.addObserver(self, "file_status", True) # weakref
        self.notificationSvc = components.classes["@activestate.com/koFileNotificationService;1"].\
                                    getService(components.interfaces.koIFileNotificationService)
        try:
            self._placePrefs = self._prefs.getPref("places")
            self._placePrefs.prefObserverService.addObserverForTopics(self,
                             ["showProjectPath",
                              "showProjectPathExtension"],
                                                                      True)
            self._showProjectPath = self._placePrefs.getBoolean('showProjectPath', False)
            self._showProjectPathExtension = self._placePrefs.getBoolean('showProjectPathExtension', False)
        except:
            self._placePrefs = None

    def terminate(self):
        if self._placePrefs:
            self._placePrefs.prefObserverService.removeObserverForTopics(self,
                                 ["showProjectPath",
                                  "showProjectPathExtension"])
        
    def observe(self, subject, topic, data):
        #TODO: When a watched file/folder no longer exists, paint it red.
        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return

        if topic == "file_status":
            try:
                # find the row for the file and invalidate it
                files = data.split("\n")
                invalidRows = [i for (i,row) in enumerate(self._rows) if row.uri in files]
                for row in invalidRows:
                    thisRow = self._rows[row]
                    try:
                        del thisRow.properties
                    except AttributeError:
                        pass
                if invalidRows:
                    self._tree.beginUpdateBatch()
                    map(self._tree.invalidateRow, invalidRows)
                    self._tree.endUpdateBatch()
            except:
                log.exception("Failed on file_status")
        elif topic == "showProjectPath":
            self._showProjectPath = self._placePrefs.getBooleanPref('showProjectPath')
            self._tree.invalidate()
        elif topic == "showProjectPathExtension":
            self._showProjectPathExtension = self._placePrefs.getBoolean('showProjectPathExtension', False)
            self._tree.invalidate()
        

    # nsIFileNotificationObserver
    # we want to receive notifications for any live folders in our view
    # the addition of observers will occur during generateRows
    def fileNotification(self, uri, flags):
        #TODO: When a watched file/folder no longer exists, paint it red.
        #print "got notification [%s] flags %d"%(uri,flags)

        if not self._tree:
            # No tree, Komodo is likely shutting down.
            return

        changed = components.classes["@activestate.com/koFileEx;1"].\
                createInstance(components.interfaces.koIFileEx)
        changed.URI = uri
        matching_parts = []
        #print "   path is [%r] dirname [%r]"%(changed.path, changed.dirName)

        if flags & _rebuildFlags:
            log.debug("received fileNotification flags: %r, path: %r", flags,
                      changed.path);
            for row in self._rows:
                part = row["node"]
                if hasattr(part,'get_liveDirectory'):
                    path = part.get_liveDirectory()
                else:
                    if not hasattr(row, "file"):
                        # Item has not yet been lazily loaded, so we don't
                        # need to compare this item.
                        continue
                    file = row.file
                    if not file:
                        continue
                    path = file.path
                if not path:
                    continue
                #print "row is: %s" % (file.path)
                if flags & _createdFlags and path == changed.dirName or \
                   path == changed.path:
                    matching_parts.append((part, path))
            if not matching_parts:
                return
            if flags & _createdFlags:
                for part, path in matching_parts:
                    if path == changed.dirName:
                        #print "Found parent, refreshing it now"
                        #print "Before:", part.getChildren()
                        part.needrefresh = 1
                        self.refresh(part)
                        #print "After:", part.getChildren()
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
                    parent = part._parent
                    parent.removeChild(part)
                    self.refresh(parent)
        else:
            # this is a modification change, just invalidate rows
            self._tree.invalidate()

    def addProject(self, kpf):
        unwrapped_kpf = self._addProjectPrologue(kpf)
        newProjectIndex = len(self._rows)
        self._rows.append(_ProjectNode(unwrapped_kpf, 0, unwrapped_kpf))
        self._tree.rowCountChanged(newProjectIndex, 1)
        self._addProjectEpilogue(unwrapped_kpf, newProjectIndex)

    def addProjectAtPosition(self, kpf, newProjectIndex):
        unwrapped_kpf = self._addProjectPrologue(kpf)
        self._rows.insert(newProjectIndex, _ProjectNode(unwrapped_kpf, 0, unwrapped_kpf))
        self._tree.rowCountChanged(newProjectIndex, 1)
        self._addProjectEpilogue(unwrapped_kpf, newProjectIndex)

    def moveProjectToEnd(self, project_tuple):
        _, kpfClass, kpf = project_tuple
        self._rows.append(kpfClass(kpf, 0, kpf))
        self._addProjectEpilogue(kpf, len(self._rows) - 1)
        
    def _addProjectPrologue(self, kpf):
        self._partSvc.addProject(kpf)
        unwrapped_kpf = UnwrapObject(kpf)
        self.restorePrefs(unwrapped_kpf)
        self._partSvc.currentProject = unwrapped_kpf
        url = kpf.url
        # If the project is being added while restoring the view state,
        # it's possible that this project is already in the tree as
        # an unopened project in single-project view mode.
        # Ref bug 92356
        for i, row in enumerate(self._rows):
            if row.uri == url:
                del self._rows[i]
                self._tree.rowCountChanged(i, 1)
                break
        return unwrapped_kpf

    def _addProjectEpilogue(self, kpf, newProjectIndex):
        if kpf.id not in self._nodeIsOpen:
            self._nodeIsOpen[kpf.id] = False
        elif (self._nodeIsOpen[kpf.id]
              and not self.isContainerOpen(newProjectIndex)
              and not self.isContainerEmpty(newProjectIndex)):
            self.toggleOpenState(newProjectIndex)

    def addUnopenedProject(self, kpf):
        newProjectIndex = len(self._rows)
        unwrapped_kpf = UnwrapObject(kpf)
        self._rows.append(_UnopenedProjectNode(unwrapped_kpf, 0, unwrapped_kpf))
        self._tree.rowCountChanged(newProjectIndex, 1)

    def addUnopenedProjectAtPosition(self, kpf, newProjectIndex):
        unwrapped_kpf = UnwrapObject(kpf)
        self._rows.insert(newProjectIndex, _UnopenedProjectNode(unwrapped_kpf, 0, unwrapped_kpf))
        self._tree.rowCountChanged(newProjectIndex, 1)
    
    def removeProject(self, kpfWrapped):
        self._partSvc.removeProject(kpfWrapped)
        kpf = UnwrapObject(kpfWrapped)
        self.savePrefs(kpf)
        needNewCurrentProject = kpfWrapped == self.get_currentProject()
        # remove rows for project
        index = self._getIndexByPart(kpf)
        if index == -1:
            log.debug("removeProject: can't find project %s", kpf.get_name())
            return
        sibling = self.getNextSiblingIndex(index)
        if needNewCurrentProject:
            if index == 0:
                # first project becomes active, if there is one
                if sibling < len(self._rows):
                    newCurrentIndex = 0
                else:
                    newCurrentIndex = -1
            else:
                # previous project becomes active
                newCurrentIndex = self._getPrevSiblingIndex(index)#@@@@
        self._rows = self._rows[:index]+self._rows[sibling:]
        if not self._tree:
            # bug 101553: Could happen at shutdown: there is no more project tree
            log.warn("koKPFTreeView.p.py: removeProject: there is no self._tree")
            return
        self._tree.rowCountChanged(index, (index - sibling))

        if needNewCurrentProject:
            self._tree.beginUpdateBatch()
            try:
                self._tree.invalidateRow(index)
                if newCurrentIndex != -1:
                    self.set_currentProject(self._rows[newCurrentIndex].part)
                    self._tree.invalidateRow(newCurrentIndex)
                else:
                    # closing the only project we have, no current project
                    self.set_currentProject(None)
            finally:
                self._tree.endUpdateBatch()
                    
    def clearTree(self):
        nlen = len(self._rows)
        self._rows = []
        self._tree.rowCountChanged(0, -nlen)

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
        self._partSvc.currentProject = prj
        project = UnwrapObject(prj)
        if project is None:
            return
        index = self._getIndexByPart(project)
        if index == -1:
            raise Exception("Add the project to the view before making it the current project")
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
        nextSibling = self.getNextSiblingIndex(index)
        if (index < firstVisRow
            or index >= lastVisRow
            or (len(self._rows) > numVisRows
                and ((nextSibling - index) > numVisRows
                     or len(self._rows) < (firstVisRow + numVisRows)))):
            scrollToIndex = min(index, len(self._rows) - numVisRows)
            #print "Scrolling to row: %d" % (scrollToIndex)
            self._tree.scrollToRow(scrollToIndex)
            self._tree.invalidateRow(index)

    def _getPrevSiblingIndex(self, index):
        level = self._rows[index].level
        i = index - 1
        while i >= 0 and self._rows[i].level > level:
            i = i - 1
        return i

    def getNextSiblingIndex(self, index):
        level = self._rows[index].level
        rc = len(self._rows)
        i = index + 1
        while i < rc and self._rows[i].level > level:
            i = i + 1
        return i

    def addRow(self, row): #@@@@ replace with addItem(item, row)?
        # add this row into our rows index
        if row.level > 0:
            part = row.part
            index = self._getIndexByPart(part.get_parent())
            # insert this prior to the parents sibling
            sibling = self.getNextSiblingIndex(index)
            self._rows.insert(sibling, row)
        else:
            self._rows.append(row)
            index = len(self._rows) - 1
        return self._rows.index(row)
    
    def invalidate(self):
        if self._tree:
            self._tree.beginUpdateBatch()
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def refresh(self, part):
        """ return the row that should be selected if that's relevant"""
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
            firstVisiblePart = self._rows[firstVisibleRow].part
        # Remember the selection as well
        selectedParts = self.getSelectedItems()

        node = None
        if part:
            part = UnwrapObject(part)
            index = self._getIndexByPart(part)
            if index >= 0 and index < len(self._rows):
                node = self._rows[index].part

        # if we get a part, we just refresh that
        if not node:
            log.debug("No node for part %s", part.name)
            return -1
        
        if self.isContainerOpen(index):
            # bink the parent node so we can see the new children
            self.toggleOpenState(index)
            self.toggleOpenState(index)
            
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

    def removeItems(self, parts):
        self._tree.beginUpdateBatch()
        try:
            for part in parts:
                index = self.getIndexByPart(part)
                if index != -1:
                    node = self._rows[index]
                    if self.isContainerOpen(index):
                        nextSiblingIndex = self.getNextSiblingIndex(index)
                    else:
                        nextSiblingIndex = index + 1
                    if index == len(self._rows) - 1:
                        pivot = index - 1
                    else:
                        pivot = index
                    self._rows = self._rows[:index] + self._rows[nextSiblingIndex:]
                    self._tree.rowCountChanged(pivot, index - nextSiblingIndex)
        finally:
            self._tree.endUpdateBatch()

    def showChild(self, parentPart, childPart):
        index = self.getIndexByPart(parentPart)
        if index == -1:
            log.error("Can't find parent %s in tree", parentPart.name)
            return
        self.toggleOpenState(index)
        if not self.isContainerOpen(index):
            self.toggleOpenState(index)
        index = self.getIndexByPart(childPart)
        if index == -1:
            log.error("Can't find child %s in tree", childPart.name)
            return
        self._tree.ensureRowIsVisible(index)
        self.selection.select(index)

    def getSelectedItems(self, rootsOnly=False):
        # return the selected koIParts
        if not self._rows:
            return []
        if self.selection.single:
            # deselect all other selections except the current one
            self.selection.select(self.selection.currentIndex)
            return [self._rows[self.selection.currentIndex].part]
        selectedIndices = self.getSelectedIndices(rootsOnly)
        return [self._rows[i].part for i in selectedIndices]
    
    def getSelectedItem(self):
        try:
            return self._rows[self.selection.currentIndex].part
        except IndexError, e:
            return None

    def _getIndexByPart(self, part):
        nodes = [row.part for row in self._rows]
        try:
            return nodes.index(part)
        except ValueError, e:
            return -1
        ids = [row.part.id for row in self._rows]
        try:
            return ids.index(part.id)
        except ValueError, e:
            return -1

    def getIndexByPart(self, part):
        return self._getIndexByPart(UnwrapObject(part))

    def getRowItem(self, index):
        if index >= 0 and index < len(self._rows):
            return self._rows[index].part
        return None

    def getRowItemByURI(self, uri):
        for row in self._rows:
            node = row.part
            try:
                if node.url == uri:
                    return node
            except AttributeError:
                pass
    
    def selectPart(self, part):
        index = self.getIndexByPart(part)
        self.selection.select(index)

    def selectParts(self, parts):
        # Clear the current selection.
        self.selection.clearSelection()
        indices = [ self._getIndexByPart(part) for part in parts ]
        indices.sort()
        index = 0
        i = 0
        while i < len(indices):
            index = indices[i]
            i += 1
            if index < 0:
                # Part has been removed.
                continue
            to_index = index
            # Use the largest range possible for the selection.
            while i < len(indices):
                if indices[i] != to_index + 1:
                    break
                to_index += 1
                i += 1
            # Ranged select call, True means to append to the current selection
            self.selection.rangedSelect(index, to_index, True)

    def sortBy(self, key, direction):
        changed = 0

        # get a current node that we can scroll to after sorting
        selectedNode = None
        if self._rows:
            selected = self.selection.currentIndex
            if selected < 0:
                selected = self._tree.getFirstVisibleRow()
            if 0 <= selected < len(self._rows):
                selectedNode = self._rows[selected]

        if self._sortedBy != key or self._sortDir != direction:
            self._sortedBy = key
            self._sortDir = direction

    def get_sortDirection(self):
        return self._sortDir

    def sortRows(self):
        if self._sortDir == 0:
            # There is no "natural order" in v6.1+
            return
        # projects = [UnwrapObject(x) for x in self._partSvc.getProjects()]
        opened_projects = [(0, _ProjectNode, x.part) for x in self._rows
                           if x.part.type == 'project']
        unopened_projects = [(1, _UnopenedProjectNode, x.part) for x in self._rows
                           if x.part.type == 'unopened_project']
        projects = opened_projects + unopened_projects
        self._sortNodes(projects, self._sortedBy, self._sortDir, force=True)
        olen = len(self._rows)
        self._rows = []
        self._tree.beginUpdateBatch()
        try:
            for p in projects:
                self.moveProjectToEnd(p)
        finally:
            self._tree.endUpdateBatch()
        nlen = len(self._rows)
        self._tree.rowCountChanged(nlen - olen, 0)
        
    def _sortNodes(self, nodes, sortBy, sortDir, force=False):
        if force or self._sortedBy != sortBy or self._sortDir != sortDir:
            log.debug("KPFTree::_sortNodes()")
            if sortDir != 0:
                nodes.sort(lambda a,b: compareNodeFolder(a, b, sortBy, sortDir))
            else:
                nodes.sort(lambda a,b: compareNode(a, b, sortBy))
            self._sortDir = sortDir # cache sort order
            self._sortedBy = sortBy # cache sort order
        else:
            log.debug("KPFTree::_sortNodes:: already sorted")


    _nodeTypeName_from_partTypeName = { 'part' : _Node,
                                        'file' : _FileNode,
                                        'folder' : _GroupNode,
                                        'livefolder': _FolderNode,
                                        'project': _ProjectNode,
                                        }
    def makeRowsFromParts(self, children, level, project):
        """
        @param children: array of koPart
        @returns list of _Node
        """
        nodeList = [self._nodeTypeName_from_partTypeName[child.type](child, level + 1, project)
                  for child in children]
        return sorted(nodeList, key=lambda row: row.part.get_name().lower())
        
    # nsITreeView
    def isSeparator(self, index):
        return 0
    
    def get_rowCount(self):
        return len(self._rows)

    def getRowProperties( self, index, properties=None):
        pass

    def _buildCellProperties(self, row, column):
        prop = []
        prop.append("primaryColumn")
        part = self._rows[row].part
        prop.append(part.type)
        
        if not hasattr(part, 'file'):
            # We hold a reference to the koFile instance, this causes the file
            # status service to check/maintain the file's status information.
            part.file = part.getFile()
        if part.file and not part.file.isLocal:
            prop.append("remote")
        if part.file:
            f = UnwrapObject(part.file)
            # missing, sccOk, sccSync, sccConflict, add, delete, edit,
            # isReadOnly, branch, integrate
            if hasattr(f, 'exists') and not f.exists:
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
        
    def getCellProperties(self, index, column, properties=None):
        # here we build a list of properties that are used to get the icon
        # for the tree item, text style, etc.  *If getImageSrc returns
        # a url to an icon, the icon matched by properties here will be
        # ignored.  That is convenient since it allows custom icons to work*
        # XXX fixme, optimize
        col_id = self._getFieldName(column)
        if col_id != 'name':
            log.debug("Can't work with column %s, got %s", column.id, col_id)
            return
        plist = []
        if index >= len(self._rows): return
        row = self._rows[index]
        # these are UI properties, such as the twisty, we want to always
        # get them
        if row.isContainer:
            if row.isOpen:
                plist.append("open")
            else:
                plist.append("closed")
            part = row.part
            if part.type == "project" and part.id == getattr(self._partSvc.currentProject, 'id', None):
                plist.append("projectActive")
        if not hasattr(row, 'properties'):
            # these properties rarely change, keep them cached
            row.properties = self._buildCellProperties(index, column)
        plist.extend(row.properties)

        #print "row %d %s : %r"% (index, column.id, plist)

        # Mozilla 22+ does not have a properties argument.
        if properties is None:
            return " ".join(plist)
        for p in plist:
            properties.AppendElement(self.atomService.getAtom(p))

    # in nsITreeColumn col, in nsISupportsArray properties
    def getColumnProperties(self, 
                            column,
                            properties=None):
        # Result: void - None
        # In: param0: wstring
        # In: param1: nsIDOMElement
        # In: param2: nsISupportsArray
        if self.log:
            self.log.debug("getColumnProperties(column=%s, props=%r)",
                           column, properties)
            
    def _getContainerNode(self, index):
        if index >= len(self._rows) or index < 0: return None
        return self._rows[index]

    def isContainer(self, index):
        node = self._getContainerNode(index)
        if node is None: return False
        return node.isContainer

    def isContainerOpen(self, index):
        node = self._getContainerNode(index)
        if node is None: return False
        return node.isContainer and node.isOpen

    def isContainerEmpty( self, index ):
        node = self._getContainerNode(index)
        if node is None: return False
        try:
            return node.isContainer and len(node.part.children) == 0
        except AttributeError:
            #log.debug("isContainerEmpty: node:%d, part:%s",
            #           index, node.part or "<null>")
            return False

    def isSorted( self ):
        # Result: boolean
        return self._sortDir != 0

    def getParentIndex( self, index):
        if index >= len(self._rows) or index < 0: return -1
        i = index - 1
        targetLevel = self._rows[index].level - 1
        if targetLevel < 0:
            return -1
        while i >= 0 and self._rows[i].level > targetLevel:
            i -= 1
        if i == -1:
            log.debug("getParentIndex: couldn't find parent of item %d", index)
        elif self._rows[i].level < targetLevel:
            log.debug("getParentIndex: looking for item at level %d above %d, landed at level %d at item %d",
                      targetLevel, index, self._rows[i].level, i)
        return i

    def hasNextSibling( self, index, afterIndex ):
        if index >= len(self._rows) or index < 0: return 0
        current_level = self._rows[index].level
        for n in self._rows[afterIndex + 1:]:
            n_level = n.level
            if n_level < current_level:
                return 0
            elif n_level == current_level:
                return 1
        return 0

    def getLevel(self, index):
        if index >= len(self._rows) or index < 0: return -1
        return self._rows[index].level

    _name_fields = { 'placesSubpanelProjectNameTreecol_MPV':'name',
                     'placesSubpanelProjectNameTreecol_SPV':'name', }
    def _getFieldName(self, column):
        return self._name_fields.get(column.id, column.id)

    def getImageSrc(self, index, column):
        # see comment in getCellProperties regarding images
        # XXX fixme, optimize
        if index >= len(self._rows) or index < 0: return ""
        name = self._getFieldName(column)
        if name == "name":
            part = self._rows[index].part
            if part._attributes.has_key('icon'):
                #print "getImageSrc row %d [%s]"% (index, part._attributes['icon'])
                return part._attributes['icon']
            else:
                try:
                    return part.get_iconurl() or ""
                except:
                    log.exception("Error trying to get icon")
        return ""

    def getCellValue(self, index, column):
        ####log.debug("getCellValue(%d/%s) => ...", index, column.id)
        if index >= len(self._rows) or index < 0: return
        part = self._rows[index].part
        name = self._getFieldName(column)
        if hasattr(part, name):
            ####log.debug(" => %s", getattr(part, name))
            return getattr(part, name)
        get_name = "get_" + name
        if hasattr(part, get_name):
            ####log.debug(" => %s", getattr(part, get_name)())
            return getattr(part, get_name)()
        ####log.debug(" => %s", "")
        return ""

    def getCellText(self, index, column):
        ####log.debug("getCellText(%d/%s) => ...", index, column.id)
        # XXX fixme, optimize
        if index >= len(self._rows) or index < 0: return
        node = self._rows[index]
        child = node.part
        name = self._getFieldName(column)
        if node.level == 0:
            if self._showProjectPath:
                text = node.path
            else:
                text = child.getFieldValue(name)
            if not self._showProjectPathExtension:
                text = text[:-len(_g_suffix)]
        else:
            text = child.getFieldValue(name)
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
        #print "getCellText for index %d col %s is %s" %(index, name, text)
        if name == 'name' and child.type == 'project' and child.get_isDirty():
            text = text+"*"
        ####log.debug("... %s", text)
        return text

    def setTree(self, tree):
        self._tree = tree

    def toggleOpenState(self, index):
        #print "toggle row at index %d"%index
        node = self._rows[index]
        if not node or not node.isContainer:
            log.error("toggleOpenState: index:%d: not a container", index)
            return
        isOpen = node.isOpen
        level = node.level

        # Must recalculate the rows.
        nextSiblingIndex = self.getNextSiblingIndex(index)
        if isOpen:
            # just remove the children from the rows
            #print "removing rows %d to %d" %(index,i)
            self._rows = self._rows[:index + 1] + self._rows[nextSiblingIndex:]
            self._tree.rowCountChanged(index + 1,(index + 1) - nextSiblingIndex)
        else:
            # just get the rows for the node, then insert them into our list
            try:
                children = self.makeRowsFromParts(node.part.children, node.level, node.project)
            except AttributeError, ex:
                msg = ("Error trying to get children for row %d (%s)" %
                       (index, node.part.get_name()))
                if ex.message == "'koProject' object has no attribute 'children'":
                    log.debug("%s", msg)
                              
                else:
                    log.exception("%s", msg)
                children = []
            self._rows = self._rows[:index + 1] + children + self._rows[nextSiblingIndex:]
            self._tree.rowCountChanged(index + 1, len(children))
            for child in children:
                childPart = child.part
                if self._nodeIsOpen.get(childPart.id, False):
                    childIndex = self.getIndexByPart(childPart)
                    if (childIndex != -1
                          and not self.isContainerOpen(childIndex)
                          and not self.isContainerEmpty(childIndex)):
                        self.toggleOpenState(childIndex)
                            
        self._nodeIsOpen[node.part.id] = node.isOpen = not isOpen
        # Ensure the toggle state is correctly redrawn, fixes bug:
        #   http://bugs.activestate.com/show_bug.cgi?id=71942
        self._tree.invalidateRow(index)

        self.selection.currentIndex = index
        self.selection.select(index)
