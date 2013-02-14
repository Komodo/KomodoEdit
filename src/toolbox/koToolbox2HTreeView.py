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

"""
Manage a hierarchical view of the loaded tools.  The hierarchy stores
only the name, id, iconurl of a tool, and a list of filtered child nodes by id.
"""

import sys
import os
import json
from os.path import join
import copy
import shutil
import time
import logging

from xpcom import components, ServerException, nsError
from xpcom.server import WrapObject, UnwrapObject
from projectUtils import *
import fileutils
import eollib
import fileutils
from koTreeView import TreeView

import koToolbox2



#---- globals

log = logging.getLogger("Toolbox2HTreeView")
#log.setLevel(logging.DEBUG)

_tbdbSvc = None  # module-global handle to the database service
_view = None     # module-global handle to the tree-view (needs refactoring)



#---- Classes used for rows of a toolbox hierarchical view

class _KoToolHView(object):
    isContainer = False
    def __init__(self, tool):
        self.id = tool.id
        self.name = tool.name
        self.iconurl = tool.get_iconurl()
        self.path = tool.get_path()

    def get_type(self):
        return self.typeName
    
    def get_id(self):
        return str(self.id)

    def get_name(self):
        return self.name

    def get_iconurl(self):
        return self.iconurl

    def isToolboxRow(self, index):
        return False
            
class _KoContainerHView(_KoToolHView):
    isContainer = True
    folderTypes = ('folder', 'menu', 'toolbar')
    def rebuildChildren(self):
        self.unfilteredChildNodes = [x + (x[2] in self.folderTypes,)
                                     for x in _tbdbSvc.getChildNodes(self.id)]

    def addChild(self, item):
        item_uw = UnwrapObject(item)
        id = int(item_uw.id)
        self.unfilteredChildNodes.append((id, item_uw.name, item_uw.typeName, item_uw.isContainer))
        #self.childIDs.append(id)

    def removeChild(self, childViewItem):
        child_id = int(childViewItem.id)
        for i, node in enumerate(self.unfilteredChildNodes):
            if node[0] == child_id:
                del self.unfilteredChildNodes[i]
                break
        else:
            #log.debug("Failed to find a child node in parent %d", self.id)
            pass

    def __init__(self, tool):
        _KoToolHView.__init__(self, tool)
        self.rebuildChildren()
        self.isOpen = False

class _KoFolderHView(_KoContainerHView):
    typeName = 'folder'

    def isToolboxRow(self, index):
        if self.level > 0:
            return False
        # Now we need to check to see if we're in the std toolbox range,
        # or elsewhere
        nextToolbox = _view.getNextSiblingIndexModel(0)
        if nextToolbox == -1 or index < nextToolbox - 1:
            return False
        else:
            return True

    def getImageSrc(self, index, column):
        if self.isToolboxRow(index):
            return 'chrome://fugue/skin/icons/toolbox.png'
        else:
            return self.get_iconurl()

class _KoMenuHView(_KoFolderHView):
    typeName = 'menu'
        
class _KoToolbarHView(_KoFolderHView):
    typeName = 'toolbar'

class _KoCommandToolHView(_KoToolHView):
    typeName = 'command'

class _KoMacroToolHView(_KoToolHView):
    typeName = 'macro'

class _KoSnippetToolHView(_KoToolHView):
    typeName = 'snippet'

class _KoTemplateToolHView(_KoToolHView):
    typeName = 'template'

class _KoURLToolHView(_KoToolHView):
    typeName = 'URL'


_viewClassFromTypeName = {}
for _obj in globals().values():
    if (isinstance(_obj, type) and issubclass(_obj, _KoToolHView)
        and getattr(_obj, "typeName", None)):
        _viewClassFromTypeName[_obj.typeName] = _obj

def _koToolHViewFromTool(tool):
    return _viewClassFromTypeName[tool.typeName](tool)



#---- Toolbox tree view


def _appendDirSepIfNeeded(s):
    if s[-1] == os.sep:
        return s
    return s + os.sep
    
class KoToolbox2HTreeView(TreeView):
    """
    There are actually four tree views here.  They each contain an
    array of nodes consisting of (name, level, type, icon, path).
    The four trees are complete (contains everything), no-toolbox,
    filtered, and filtered-no-toolbox.
    
    Now the user never sees the top-level standard-toolbox, but
    all operations on the tree work on it.
    """
    _com_interfaces_ = [components.interfaces.nsIObserver,
                        components.interfaces.koIToolbox2HTreeView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{7b345b58-bae7-4e0b-9a49-30119a1ffd29}"
    _reg_contractid_ = "@activestate.com/KoToolbox2HTreeView;1"
    _reg_desc_ = "KoToolbox2 Hierarchical TreeView"

    _SORT_BY_NATURAL_ORDER = components.interfaces.koIToolbox2HTreeView.SORT_BY_NATURAL_ORDER
    _SORT_BY_NAME_ASCENDING = components.interfaces.koIToolbox2HTreeView.SORT_BY_NAME_ASCENDING
    _SORT_BY_NAME_DESCENDING = components.interfaces.koIToolbox2HTreeView.SORT_BY_NAME_DESCENDING

    def __init__(self, debug=None):
        TreeView.__init__(self, debug=0)
        # The _rows_model shows all the rows currently loaded
        # The _rows_view shows all the rows actually displayed
        # _rows_view == _rows_model[1:] 
        self._rows_model = []
        self._rows_view = []
        self._sortDirection = self._SORT_BY_NATURAL_ORDER
        self._nodeOpenStatusFromName = {}
        self._tree = None
        self.toolbox_db = None
        _observerSvc = components.classes["@mozilla.org/observer-service;1"].\
            getService(components.interfaces.nsIObserverService)
        _observerSvc.addObserver(self, 'tool-appearance-changed', 0)
        _observerSvc.addObserver(self, 'xpcom-shutdown', 0)
        self.toolbox2Svc = components.classes["@activestate.com/koToolbox2Service;1"]\
                .getService(components.interfaces.koIToolbox2Service)

        self._unfilteredRows_view = self._unfilteredRows_model = None
        self._toolsMgr = UnwrapObject(components.classes["@activestate.com/koToolbox2ToolManager;1"].getService(components.interfaces.koIToolbox2ToolManager))
        self._toolsMgr.set_hierarchicalView(self)
        self._loadedProjects = {} # Map project.id to project
        
    def initialize(self, currentProject):
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        if not prefs.hasPref("toolbox2"):
            toolboxPrefs = components.classes["@activestate.com/koPreferenceSet;1"].createInstance()
            prefs.setPref("toolbox2", toolboxPrefs)
        else:
            toolboxPrefs = prefs.getPref("toolbox2")
        if toolboxPrefs.hasPref("sortDirection"):
            sortDirectionString = toolboxPrefs.getStringPref("sortDirection")
            self._sortDirection = {'natural':self._SORT_BY_NATURAL_ORDER,
                                   'ascending':self._SORT_BY_NAME_ASCENDING,
                                   'descending':self._SORT_BY_NAME_DESCENDING,
                                   }.get(sortDirectionString,
                                         self._SORT_BY_NATURAL_ORDER)
                                   
            
        if toolboxPrefs.hasPref("open-nodes"):
            self._nodeOpenStatusFromName = json.loads(toolboxPrefs.getStringPref("open-nodes"))
        else:
            self._nodeOpenStatusFromName = {}
        global _tbdbSvc, _view
        _tbdbSvc = self.toolbox_db = UnwrapObject(components.classes["@activestate.com/KoToolboxDatabaseService;1"].\
                       getService(components.interfaces.koIToolboxDatabaseService))
        _view = self
        self._toolsManager = UnwrapObject(components.classes["@activestate.com/koToolbox2ToolManager;1"]
        .getService(components.interfaces.koIToolbox2ToolManager));
        self._std_toolbox_id = self.toolbox2Svc.getStandardToolboxID()

        self._redoTreeView(currentProject)
        self._restoreView()
        self._tree.invalidate()

    def observe(self, subject, topic, data):
        if not topic:
            return
        if _tbdbSvc is None:
            # Not fully initialized, but we'll update the tree later,
            # before startup is done.
            return
        elif topic == 'tool-appearance-changed':
            if self._tree is None:
                log.debug("observe: tool-appearance-changed: no tree")
                return
            # Update the tool's values, and then invalidate the row
            id = int(data)
            view_index = self.getIndexById(id)
            if view_index == -1:
                return
            model_index = self._modelIndexFromViewIndex(view_index)
            if model_index == -1:
                return
            node = self._rows_model[model_index]
            tool = self._toolsMgr.getToolById(id)
            node.name = tool.name
            node.iconurl = tool.get_iconurl()
            parent_index = self.getParentIndexModel(model_index)
            if parent_index > -1:
                self._rows_model[parent_index].rebuildChildren()
                self.refreshView_Model(parent_index)
            self._filter_std_toolbox()
            view_index = self.getIndexById(id)
            if view_index == -1:
                return
            self._tree.invalidateRow(view_index)
        elif topic == 'xpcom-shutdown':
            _observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                getService(components.interfaces.nsIObserverService)
            _observerSvc.removeObserver(self, 'xpcom-shutdown')

    def getPathFromIndex(self, index):
        id = self._rows_view[index].id
        return self.toolbox_db.getPath(id)

    def get_toolType(self, index):
        if index == -1:
            return None
        return self._rows_view[index].typeName
    
    def getIndexByPath(self, path):
        for i, row in enumerate(self._rows_view):
            if row.path == path:
                return i
        return -1
    
    def getIndexByPathModel(self, path, viewIndex=None):
        if viewIndex is not None:
            if self._rows_model[viewIndex].path == path:
                return viewIndex
            elif (viewIndex > 0
                  and self._rows_model[viewIndex - 1].path == path):
                return viewIndex - 1
        for i, row in enumerate(self._rows_model):
            if row.path == path:
                return i
        return -1
    
    def getIndexByTool(self, tool):
        path = tool.path
        for i, row in enumerate(self._rows_view):
            #log.debug("%d: %s (%s/%s", i, row.path, row.typeName, row.name)
            if row.path == path:
                return i
        return -1

    def getIndexByToolFromModel(self, tool):
        path = tool.path
        for i, row in enumerate(self._rows_model):
            #log.debug("%d: %s (%s/%s", i, row.path, row.typeName, row.name)
            if row.path == path:
                return i
        return -1

    def getIndexById(self, id):
        for i, row in enumerate(self._rows_view):
            #log.debug("%d: %d (%s/%s", i, row.id, row.typeName, row.name)
            if row.id == id:
                return i
        return -1

    def selectedItemsHaveSameParent(self):
        # Ignore all child nodes in the selection
        treeSelection = self.selection
        selectedIndices = []
        parent_index = -2
        rangeCount = treeSelection.getRangeCount()
        for i in range(rangeCount):
            min_index, max_index = treeSelection.getRangeAt(i)
            index = min_index
            while index < max_index + 1:
                tool = self.getTool(index)
                res = self.toolbox_db.getValuesFromTableByKey('hierarchy',
                                                      ['parent_path_id'],
                                                      'path_id', tool.id)
                if not res:
                    if parent_index != -2:
                        return False
                else:
                    candidate_index = res[0]
                    if parent_index == -2:
                        parent_index = candidate_index
                    elif parent_index != candidate_index:
                        return False
                # And skip any selected children, if all are selected.
                if self.isContainerOpen(index):
                    nextSiblingIndex = self.getNextSiblingIndex(index)
                    if nextSiblingIndex <= max_index + 1:
                        index = nextSiblingIndex
                        continue  # don't increment at end of loop
                    elif (nextSiblingIndex == -1
                          and max_index == len(self._rows_view) - 1
                          and i == rangeCount - 1):
                        return True
                    else:
                        return False
                
                index += 1 # end while index < max_index + 1:
        return True

    # Is the node at row srcIndex an ancestor of the node at targetIndex?
    def isAncestor(self, srcIndex, targetIndex):
        if srcIndex < 0 or targetIndex < 0:
            return False
        elif srcIndex > targetIndex:
            return False
        elif srcIndex == targetIndex:
            return True
        
        srcLevel = self._rows_view[srcIndex].level
        while targetIndex > srcIndex and self._rows_view[targetIndex].level > srcLevel:
            targetIndex -= 1
        return targetIndex == srcIndex

    def addNewItemToParent(self, parent, item):
        # Not XPCOM
        # Called from the model.
        # Add and show the new item
        # Work on the "model view", and then refilter into the
        # actual view, because we might be adding items to the
        # invisible toolbox.
        if self._unfilteredRows_view:
            # Bug 87806 - add the item to the full unfiltered view,
            # and then refilter it.
            try:
                filterPattern = self._filterPattern
                self.clearFilter()
                try:
                    self.addNewItemToParent(parent, item)
                finally:
                    self.useFilter(filterPattern)
            except:
                log.error("koToolbox2HTreeView.py: addNewItemToParent failed: %s", ex.message)
            return
                
        self._toolsMgr.addNewItemToParent(parent, item, showNewItem=False)
        index = self.getIndexByToolFromModel(parent)
        if index == -1:
            raise Exception(nsError.NS_ERROR_ILLEGAL_VALUE,
                                  ("Can't find parent %s/%s in the tree" %
                                   (parent.type, parent.name)))
        view_before_len = len(self._rows_view)
        log.debug("addNewItemToParent: add tool %s to _rows_model[%d] ", item.name, index)
        self._rows_model[index].addChild(item)
        firstVisibleRow = self._tree.getFirstVisibleRow()
        if self.isContainerOpenModel(index):
            #TODO: Make showing the added item a pref?
            # Easy hack to resort the items
            self.toggleOpenStateModel(index)
            self.toggleOpenStateModel(index)
        else:
            self.toggleOpenStateModel(index)
        self._filter_std_toolbox()
        try:
            newIndex = self._rows_view.index(item, index - 1)
        except ValueError:
            pass
        else:
            index = newIndex
        view_after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, view_after_len - view_before_len)
        self._tree.scrollToRow(firstVisibleRow)
        self.selection.currentIndex = index
        self.selection.select(index)
        self._tree.ensureRowIsVisible(index)
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        try:
            observerSvc.notifyObservers(None, 'toolbox-reload-view',
                                        parent.path)
        except:
            log.exception("For notification toolbox-reload-view on %s",
                          parent.path)

    def deleteToolAt(self, index, path=None):
        row = self._rows_view[index]
        if path is None:
            path = row.path
        self._toolsMgr.deleteTool(row.id)
        
        # Work with the model rows, and then refilter to the view
        model_index = self._modelIndexFromViewIndex(index)
        if model_index != -1:
            model_parentIndex = self.getParentIndexModel(model_index)
            if model_parentIndex != -1:
                self._rows_model[model_parentIndex].removeChild(self._rows_model[index])

        before_len = len(self._rows_view)
        if self.isContainerOpenModel(model_index):
            self.toggleOpenStateModel(model_index)
        try:
            del self._nodeOpenStatusFromName[path]
        except KeyError:
            pass
        log.debug("deleteToolAt: del tool %s at _rows_model[%d] ", self._rows_model[model_index].name, model_index)
        del self._rows_model[model_index]
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        self._tree.rowCountChanged(index, after_len - before_len)
        observerSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        parentPath = self._rows_model[model_parentIndex].path
        try:
            observerSvc.notifyObservers(None, 'toolbox-reload-view',
                                        parentPath)
        except:
            log.exception("For notification 'toolbox-reload-view' on %s",
                          parentPath)
        

    def copyLocalFolder(self, srcPath, targetDirPath):
        fileutils.copyLocalFolder(srcPath, targetDirPath)

    def addProject(self, project):
        self._loadedProjects[project.id] = project
        
    def removeProject(self, project):
        try:
            del self._loadedProjects[project.id]
        except KeyError:
            log.debug("Can't find project %s (id %s) in self._loadedProjects",
                      project.name, project.id)        
    
    def _getTargetInfo(self, targetIndex):
        if targetIndex == -1:
            stdToolboxPath = self._toolsMgr.getToolById(self.toolbox2Svc.getStandardToolboxID()).path
            targetModelIndex = self.getIndexByPathModel(stdToolboxPath)
        else:
            targetModelIndex = self._modelIndexFromViewIndex(targetIndex)
        if targetModelIndex == -1:
            raise Exception("Can't find a model index for targetIndex: %d" % targetIndex)
            
        targetTool = self.getToolFromModel(targetModelIndex)
        if not targetTool.isContainer:
            raise Exception("_getTargetInfo: item at row %d isn't a container, it's a %s" %
                            (targetModelIndex, targetTool.typeName))
        targetPath = targetTool.path
        targetId = targetTool.id
        if targetId is None:
            raise Exception("target %s (%d) isn't in the database" % (
                targetPath, targetIndex
            ))
        return targetModelIndex, targetPath

    def _postPasteItemsByCopy(self, targetModelIndex, targetPath):
        self.toolbox2Svc.reloadToolsDirectory(targetPath)
        self.reloadToolsDirectoryView_ByModel(targetModelIndex)
        view_before_len = len(self._rows_view)
        self._filter_std_toolbox()
        view_after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, view_after_len - view_before_len)
        self._tree.invalidate()

    def pasteItemsIntoTarget(self, targetIndex, paths, copying):
        # We need to work with the model indices, because we're
        # changing this tree.  We can use the current view to
        # find the source and destination, but then need to work
        # with model coordinates for updating the rows.
        targetModelIndex, targetPath = self._getTargetInfo(targetIndex)
        if copying:
            # Just copy the paths to the targetIndex, refresh the
            # target and its children, and refresh the view
            for path in paths:
                if not os.path.exists(path):
                    #TODO: Bundle all the problems into one string that gets raised back.
                    log.debug("Path %s doesn't exist", path)
                elif os.path.isdir(path):
                    if targetPath.startswith(_appendDirSepIfNeeded(path)):
                        log.error("Refuse to copy path %s into one of its descendants (%s)",
                                  path, targetPath)
                        continue
                    try:
                        fileutils.copyLocalFolder(path, targetPath)
                    except:
                        log.exception("fileutils.copyLocalFolder(src:%s to  targetPath:%s) failed", path, targetPath)
                else:
                    try:
                        shutil.copy(path, targetPath)
                    except:
                        log.exception("Can't copy src:%s to  targetPath:%s", path, targetPath)
            self._postPasteItemsByCopy(targetModelIndex, targetPath)
            return

        # Now do the part where we move the items, not copying.
        parentIndicesToUpdate = [targetModelIndex]
        # Moving is harder, because we have to track the indices we've dropped.
        for path in paths:
            if not os.path.exists(path):
                #TODO: Bundle all the problems into one string that gets raised back.
                log.debug("Path %s doesn't exist", path)
                continue
            if os.path.isdir(path):
                if targetPath.startswith(_appendDirSepIfNeeded(path)):
                    log.error("Refuse to move path %s into one of its descendants (%s)",
                              path, targetPath)
                    continue
                try:
                    fileutils.copyLocalFolder(path, targetPath)
                    shutil.rmtree(path)
                except:
                    log.exception("fileutils.copyLocalFolder(src:%s to  targetPath:%s) failed", path, targetPath)
                    continue
            else:
                try:
                    finalTargetPath = join(targetPath, os.path.basename(path))
                    shutil.move(path, finalTargetPath)
                except:
                    log.exception("shutil.move(src:%s to finalTargetPath:%s) failed", path, finalTargetPath)
                    continue
            index = self.getIndexByPathModel(path)
            parentIndex = self.getParentIndexModel(index)
            if parentIndex != -1 and parentIndex not in parentIndicesToUpdate:
                parentIndicesToUpdate.append(parentIndex)
                
        view_before_len = len(self._rows_view)
        parentIndicesToUpdate.sort(reverse=True)
        for parentIndex in parentIndicesToUpdate:
            parentPath = self._rows_model[parentIndex].path
            self.toolbox2Svc.reloadToolsDirectory(parentPath)
            self.reloadToolsDirectoryView_ByModel(parentIndex)
        self._filter_std_toolbox()
        view_after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, view_after_len - view_before_len)
        self._tree.invalidate()
        if targetIndex != -1:
            finalTargetIndex = self.getIndexByPath(targetPath)
            if finalTargetIndex != -1:
                self._tree.ensureRowIsVisible(finalTargetIndex)
        # Otherwise who knows.  Leave the tree alone.
                
    def copyItemIntoTargetWithNewName(self, targetIndex, srcPath, newBaseName):
        # See comments at start of pasteItemsIntoTarget
        targetModelIndex, targetPath = self._getTargetInfo(targetIndex)
        newPath = os.path.join(targetPath, newBaseName)
        if not os.path.exists(srcPath):
            #TODO: Bundle all the problems into one string that gets raised back.
            log.debug("Path %s doesn't exist", srcPath)
        elif os.path.isdir(srcPath):
            if targetPath.startswith(_appendDirSepIfNeeded(srcPath)):
                log.error("Refuse to copy path %s into one of its descendants (%s)",
                          srcPath, targetPath)
                return
            try:
                fileutils.copyLocalFolder(srcPath, targetPath)
            except:
                log.exception("fileutils.copyLocalFolder(src:%s to  targetPath:%s) failed", srcPath, targetPath)
        else:
            try:
                shutil.copy(srcPath, newPath)
                koToolbox2.updateToolName(newPath, newBaseName)
            except:
                log.exception("Can't copy src:%s to  targetPath:%s", srcPath, newPath)
        self._postPasteItemsByCopy(targetModelIndex, targetPath)
        return

    def reloadToolsDirectoryView(self, viewIndex):
        # Refresh the model tree, and refilter into the view tree
        before_len = len(self._rows_view)
        if viewIndex == -1:
            modelIndex = 0
            tool = self.getToolFromModel(0)
            targetPath = tool.path
        else:
            targetPath = self.getPathFromIndex(viewIndex)
            modelIndex = self.getIndexByPathModel(targetPath, viewIndex)
        node = self._rows_model[modelIndex]
        if node.isContainer:
            node.rebuildChildren()
        self.refreshView_Model(modelIndex)
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, after_len - before_len)

    def reloadToolsDirectoryView_ByModel(self, modelIndex):
        # Refresh the model tree, and refilter into the view tree
        node = self._rows_model[modelIndex]
        if node.isContainer:
            node.rebuildChildren()
        self.refreshView_Model(modelIndex)

    def renameTool(self, viewIndex, newName):
        isContainer = self.isContainer(viewIndex)
        modelIndex = self._modelIndexFromViewIndex(viewIndex)
        modelNode = self._rows_model[modelIndex]
        if modelNode.level == 0:
            raise Exception("can't rename top-level folder %s" % modelNode.name)
        if isContainer:
            self._toolsMgr.renameContainer(modelNode.id, newName)
        else:
            self._toolsMgr.renameItem(modelNode.id, newName)
        # We have to refresh the subtree, because the top-node and
        # all its children now have different paths.
        newNode = self._toolsManager.getToolById(modelNode.id)
        modelNode.path = newNode.path
        modelNode.name = newNode.name

        # Also uncache the parent's children, so they get resorted
        parentModelIndex = self.getParentIndexModel(modelIndex)
        self._removeChildNodes(self._rows_model[parentModelIndex])
        # Do a full refresh to make sure the toolbox is resorted correctly
        self.refreshFullView()

    def _zipNode(self, zf, currentDirectory):
        nodes = os.listdir(currentDirectory)
        numZippedItems = 0
        for path in nodes:
            fullPath = join(currentDirectory, path)
            # these filenames should be "sluggified" already,
            # although maybe not the dirnames.
            relativePath = fullPath[self._targetZipFileRootLen:]
            if os.path.isfile(fullPath):
                zf.write(fullPath, relativePath)
                numZippedItems += 1
            elif os.path.isdir(fullPath) and not os.path.islink(fullPath):
                numZippedItems += self._zipNode(zf, fullPath)
        return numZippedItems

    def zipSelectionToFile(self, targetZipFile, zipStandardToolboxOnly):
        if zipStandardToolboxOnly:
            return self._zipStandardToolbox(targetZipFile)
        else:
            return self._zipSelectedFiles(targetZipFile)

    def _zipStandardToolbox(self, targetZipFile):
        path = self.toolbox2Svc.getStandardToolbox().path
        import zipfile
        zf = zipfile.ZipFile(targetZipFile, 'w')
        try:
            if path[-1] in "\\/":
                path = path[:-1]
            self._targetZipFileRootLen = len(os.path.dirname(path)) + 1
            return self._zipNode(zf, path)
        finally:
            zf.close()
    
    def _zipSelectedFiles(self, targetZipFile):
        selectedIndices = self.getSelectedIndices(rootsOnly=True)
        import zipfile
        zf = zipfile.ZipFile(targetZipFile, 'w')
        try:
            numZippedItems = 0
            for index in selectedIndices:
                tool = self.getTool(index)
                path = self.getPathFromIndex(index)
                if tool.isContainer and path[-1] in "\\/":
                    path = path[:-1]
                self._targetZipFileRootLen = len(os.path.dirname(path)) + 1
                if not tool.isContainer:
                    zf.write(path, path[self._targetZipFileRootLen:])
                    numZippedItems += 1
                else:
                    numZippedItems += self._zipNode(zf, path)
        finally:
            zf.close()
        return numZippedItems

    def _removeChildNodes(self, node):
        try:
            del node.unfilteredChildNodes
        except AttributeError:
            pass
    
    def refreshFullView(self):
        lim = len(self._rows_model)
        view_before_len = len(self._rows_view)
        std_toolbox_id = self.toolbox2Svc.getStandardToolboxID()
        firstVisibleRow = self._tree.getFirstVisibleRow()
        currentIndex = self.selection.currentIndex if self.selection is not None else -1
        i = 0
        while i < lim:
            before_len = len(self._rows_model)
            if self.isContainerOpenModel(i):
                self._removeChildNodes(self._rows_model[i])
                self.toggleOpenStateModel(i)
                self.toggleOpenStateModel(i)
            elif (self._nodeOpenStatusFromName.get(self._rows_model[i].path, False)
                  or self._rows_model[i].id == std_toolbox_id):
                # Force the stdtoolbox open
                self._removeChildNodes(self._rows_model[i])
                self.toggleOpenStateModel(i)
            after_len = len(self._rows_model)
            delta = after_len - before_len
            lim += delta
            i += delta + 1
        self._filter_std_toolbox()
        self._tree.ensureRowIsVisible(firstVisibleRow)
        if self.selection is not None:
            self.selection.select(currentIndex)
        view_after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, view_after_len - view_before_len)
        self._tree.invalidate()
            
    def refreshView(self, index):
        firstVisibleRow = self._tree.getFirstVisibleRow()
        before_len = len(self._rows_view)
        modelIndex = self._modelIndexFromViewIndex(index)
        if self.isContainerOpenModel(modelIndex):
            self.toggleOpenStateModel(modelIndex)
            self.toggleOpenStateModel(modelIndex)
        elif self._nodeOpenStatusFromName.get(self._rows_view[index].path, None):
            self.toggleOpenStateModel(modelIndex)
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        delta = after_len - before_len
        if delta:
            self._tree.rowCountChanged(index, delta)
        self._tree.ensureRowIsVisible(firstVisibleRow)
        
    def refreshToolView(self, tool):
        index = self.getIndexByTool(tool)
        if index == -1:
            log.warn("refreshToolView: can't find index for tool %s", tool.name)
            self.refreshStandardToolboxView()
            return
        self.refreshView(index)

    def refreshStandardToolboxView(self):
        firstVisibleRow = self._tree.getFirstVisibleRow()
        before_len = len(self._rows_view)
        modelIndex = 0
        self.toggleOpenStateModel(modelIndex)
        self.toggleOpenStateModel(modelIndex)
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        delta = after_len - before_len
        if delta:
            self._tree.rowCountChanged(0, delta)
        self._tree.ensureRowIsVisible(firstVisibleRow)

    def _modelIndexFromViewIndex(self, viewIndex):
        path = self._rows_view[viewIndex].path
        if self._rows_model[viewIndex].path == path:
            return viewIndex
        elif self._rows_model[viewIndex + 1].path == path:
            return viewIndex + 1
        else:
            modelIndex = self.getIndexByPathModel(path)
            return modelIndex        

    def refreshView_Model(self, index):
        if self.isContainerOpenModel(index):
            self.toggleOpenStateModel(index)
            self.toggleOpenStateModel(index)
        elif self._nodeOpenStatusFromName.get(self._rows_model[index].path, None):
            # Force it open.
            self.toggleOpenStateModel(index)

    def redoTreeView(self, currentProject):
        self._redoTreeView(currentProject)

    def _redoTreeView(self, currentProject=None):
        if not self._tree:
            return
        self._tree.beginUpdateBatch()
        try:
            self._redoTreeView1_aux(currentProject)
        finally:
            pass
            self._tree.endUpdateBatch()
        self.refreshFullView()

    def _redoTreeView1_aux(self, currentProject):
        if self.toolbox_db is None:
            log.error("_redoTreeView: self.toolbox_db is None")
            return
        top_level_nodes = self.toolbox_db.getTopLevelNodes()
        top_level_ids = [x[0] for x in top_level_nodes]
        project_uri_ids = UnwrapObject(self.toolbox2Svc).getLoadedProjectIDs()
        ids_to_drop = []
        loaded_URIs = []
        for p in self._loadedProjects.values():
            try:
                loaded_URIs.append(p.getFile().URI)
            except KeyError:
                log.debug("Can't get a file obj off project %s", p.name)
        for candidate_id, candidate_uri in project_uri_ids:
            if candidate_uri not in loaded_URIs:
                ids_to_drop.append(candidate_id)
        if ids_to_drop:
            f_top_level_ids = list(set(top_level_ids) - set(ids_to_drop))
            top_level_ids = f_top_level_ids
        index = 0
        lim = len(self._rows_model)
        while index < lim:
            id = int(self._rows_model[index].id)
            nextIndex = self.getNextSiblingIndexModel(index)
            if nextIndex == -1:
                finalIndex = lim
            else:
                finalIndex = nextIndex
            if id in top_level_ids:
                del top_level_ids[top_level_ids.index(id)]
                index = finalIndex
            else:
                if nextIndex == -1:
                    del self._rows_model[index:]
                    break
                else:
                    del self._rows_model[index : nextIndex]
                    lim -= (nextIndex - index)
        
        for path_id, name, node_type in top_level_nodes:
            if path_id not in top_level_ids:
                #log.debug("No need to reload tree %s", name)
                continue
            toolPart = self._toolsManager.getOrCreateTool(node_type, name, path_id)
            toolView = _koToolHViewFromTool(toolPart) 
            toolView.level = 0
            log.debug("_redoTreeView1_aux: append tool %s at _rows_model[%d] ", toolView.name, len(self._rows_model))
            self._rows_model.append(toolView)
        
    def _restoreView(self):

        toolboxPrefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs.getPref("toolbox2")
        if toolboxPrefs.hasPref("firstVisibleRow"):
            firstVisibleRow = toolboxPrefs.getLongPref("firstVisibleRow")
        else:
            firstVisibleRow = -1
        if toolboxPrefs.hasPref("currentIndex"):
            currentIndex = toolboxPrefs.getLongPref("currentIndex")
        else:
            currentIndex = -1

        self._restoreViewWithSettings(firstVisibleRow, currentIndex)

    def _restoreViewWithSettings(self, firstVisibleRow, currentIndex):
        greatestPossibleFirstVisibleRow = len(self._rows_view) - self._tree.getPageLength()
        if greatestPossibleFirstVisibleRow < 0:
            greatestPossibleFirstVisibleRow = 0
        if firstVisibleRow > greatestPossibleFirstVisibleRow:
            firstVisibleRow = greatestPossibleFirstVisibleRow
        
        if currentIndex >= len(self._rows_view):
           currentIndex =  len(self._rows_view) - 1

        if firstVisibleRow != -1:
            self._tree.scrollToRow(firstVisibleRow)
        if currentIndex != -1:
            self.selection.currentIndex = currentIndex
            self.selection.select(currentIndex)
            self._tree.ensureRowIsVisible(currentIndex)

    def terminate(self):
        prefs = components.classes["@activestate.com/koPrefService;1"].\
            getService(components.interfaces.koIPrefService).prefs
        try:
            toolboxPrefs = prefs.getPref("toolbox2")

            if prefs.hasPref("toolbox-open-nodes-size"):
                lim = prefs.getLongPref("toolbox-open-nodes-size")
            else:
                lim = 100
                prefs.setLongPref("toolbox-open-nodes-size", lim)
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

            toolboxPrefs.setStringPref("open-nodes",
                                       json.dumps(self._nodeOpenStatusFromName))
            if self._tree:
                toolboxPrefs.setLongPref("firstVisibleRow",
                                         self._tree.getFirstVisibleRow())
            toolboxPrefs.setLongPref("currentIndex",
                                     self.selection.currentIndex)
        except:
            log.exception("problem in terminate")

    def getTool(self, index):
        if index < 0: return None
        try:
            id = self._rows_view[index].id
            return self._toolsManager.getToolById(id)
        except IndexError:
            log.error("Failed getTool(index:%d), id:%r", index, id)
            return None

    def getToolFromModel(self, index):
        if index < 0: return None
        try:
            id = self._rows_model[index].id
            return self._toolsManager.getToolById(id)
        except IndexError:
            log.error("Failed getTool(index:%d), id:%r", index, id)
            return None

    def get_type(self, index):
        if index == -1:
            return None
        return self._rows_view[index].typeName
        
    #---- nsITreeView Methods
    
    def get_rowCount(self):
        return len(self._rows_view)

    def getCellText(self, index, column):
        col_id = column.id
        #log.debug(">> getCellText:%d, %s", row, col_id)
        try:
            return self._rows_view[index].name
        except AttributeError:
            log.debug("getCellText: No id %s at row %d", col_id, row)
            return "?"
        
    def getImageSrc(self, index, column):
        col_id = column.id
        node = self._rows_view[index]
        method = getattr(node, "getImageSrc", None)
        if method:
            return method(index, column)
        try:
            return self._rows_view[index].get_iconurl()
        except:
            return ""

    def isToolboxRow(self, index):
        try:
            return self._rows_view[index].isToolboxRow(index)
        except IndexError:
            return False
        
    def isContainer(self, index):
        try:
            return self._rows_view[index].isContainer
        except IndexError:
            log.error("isContainer[index:%d]", index)
            return False
        
    def isContainerOpen(self, index):
        node = self._rows_view[index]
        return node.isContainer and node.isOpen
        
    def isContainerOpenModel(self, index):
        node = self._rows_model[index]
        return node.isContainer and node.isOpen
        
    def isContainerEmpty(self, index):
        node = self._rows_view[index]
        return node.isContainer and not getattr(node, 'unfilteredChildNodes', None)

    def getParentIndex(self, index):
        if index >= len(self._rows_view) or index < 0: return -1
        try:
            i = index - 1
            level = self._rows_view[index].level
            while i >= 0 and self._rows_view[i].level >= level:
                i -= 1
        except IndexError:
            i = -1
        return i

    def getParentIndexModel(self, index):
        if index >= len(self._rows_model) or index < 0: return -1
        try:
            i = index - 1
            level = self._rows_model[index].level
            while i >= 0 and self._rows_model[i].level >= level:
                i -= 1
        except IndexError:
            i = -1
        return i

    def hasNextSibling(self, index, afterIndex):
        if index >= len(self._rows_view) or index < 0: return 0
        try:
            current_level = self._rows_view[index].level
            for next_row in self._rows_view[afterIndex + 1:]:
                next_row_level = next_row.level
                if next_row_level < current_level:
                    return 0
                elif next_row_level == current_level:
                    return 1
        except IndexError:
            pass
        return 0
    
    def getLevel(self, index):
        try:
            return self._rows_view[index].level
        except IndexError:
            return -1
                                                
    def setTree(self, tree):
        self._tree = tree
        
    def getNextSiblingIndex(self, index):
        """
        @param index {int} points to the node whose next-sibling we want to find.
        @return index of the sibling, or -1 if not found.
        """
        level = self._rows_view[index].level
        lim = len(self._rows_view)
        index += 1
        while index < lim:
            if self._rows_view[index].level <= level:
                return index
            index += 1
        return -1
    
    def getNextSiblingIndexModel(self, index):
        """
        @param index {int} points to the node whose next-sibling we want to find.
        @return index of the sibling, or -1 if not found.
        """
        level = self._rows_model[index].level
        node = self._rows_model[index]
        lim = len(self._rows_model)
        index += 1
        while index < lim:
            if self._rows_model[index].level <= level:
                return index
            index += 1
        return -1

    def setFilter(self, filterPattern):
        if not filterPattern:
            self.clearFilter()
        else:
            self.useFilter(filterPattern)
            
    def clearFilter(self):
        currentIndex = -1
        # Set currentIndex to the current node if it's selected,
        # and it's a container -- the idea is to keep the container around,
        if self.selection.count > 0:
            index = self.selection.currentIndex
            if self.isContainer(index):
                pathsToOpen = []
                currentIndex = index
                currentPath = self._rows_view[index].path
                while True:
                    parentIndex = self.getParentIndex(index)
                    if parentIndex == -1 or parentIndex == index:
                        break
                    index = parentIndex
                    rowNode = self._rows_view[index]
                    path = rowNode.path
                    if path in self._nodeOpenStatusFromName:
                        break
                    pathsToOpen.append(path)
        before_len = len(self._rows_view)
        self._rows_view = self._unfilteredRows_view
        self._rows_model = self._unfilteredRows_model
        self._unfilteredRows_view = self._unfilteredRows_model = None
        self._filterPattern = None
        #log.debug("Had %d rows, now have %d rows", before_len, after_len)
        if currentIndex != -1:
            # Open up the necessary nodes first, from the highest
            # nodes first, which happen to be the last ones we
            # pushed on the list.
            # Work with the model nodes, not the filtered view nodes.
            while pathsToOpen:
                path = pathsToOpen.pop()
                candidateIndex = self.getIndexByPathModel(path)
                if not self._rows_model[candidateIndex].isOpen:
                    self._doContainerOpenModel(self._rows_model[candidateIndex],
                                               candidateIndex)
            # Revise: currentIndex to point to new location of currentPath
            currentIndex = self.getIndexByPath(currentPath)
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, after_len - before_len)
        self._tree.invalidate()
        if currentIndex == -1:
            fvr = self._unfiltered_firstVisibleRow
            ufci = self._unfiltered_currentIndex
        else:
            fvr = -1
            ufci = currentIndex
        self._restoreViewWithSettings(fvr, ufci)
        
    def useFilter(self, filterPattern):
        if self._unfilteredRows_view is None:
            self._unfilteredRows_view = self._rows_view
            self._unfilteredRows_model = self._rows_model
            self._unfiltered_firstVisibleRow = self._tree.getFirstVisibleRow()
            self._unfiltered_currentIndex = self.selection.currentIndex;
            self._filterPattern = filterPattern
            
        t1 = time.time()
        matched_nodes = _tbdbSvc.getHierarchyMatch(filterPattern)
        t2 = time.time()
        #log.debug("Time to query %s: %g msec", filterPattern, (t2 - t1) * 1000.0)
        #log.debug("matched nodes: %s", matched_nodes)
        before_len = len(self._rows_view)
        self._rows_model = []
        for node in matched_nodes:
            path_id, name, node_type, matchedPattern, level = node
            toolPart = self._toolsManager.getToolById(path_id)
            toolView = _koToolHViewFromTool(toolPart) 
            toolView.level = level
            self._rows_model.append(toolView)
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        self._tree.rowCountChanged(0, after_len - before_len)                
        self._tree.invalidate()
        self._restoreViewWithSettings(0, 0)

    def _filter_std_toolbox(self):
        # Copy self._rows_model to self._rows_view, removing the
        # std toolbox node, and shifting its components down one level.
        # Note that the std toolbox node isn't always the first one
        # in the list.
        if len(self._rows_model) == 0:
            self._rows_view = []
            return
        # Copy the items, because at least one of the nodes in the
        # original view won't be in the final view.  And when we
        # start decrementing levels, we want to change the
        # view but not the model items.
        self._rows_view = self._rows_model[:]
        lim = len(self._rows_model)
        startPoint = stopPoint = None
        i = 0
        while i < lim:
            next_toolbox_index = self.getNextSiblingIndexModel(i)
            if next_toolbox_index == -1:
                j = lim
            else:
                j = next_toolbox_index
            if self._rows_model[i].id == self._std_toolbox_id:
                del self._rows_view[i]
                startPoint = i
                stopPoint = j - 1
                break
            i = j
        if startPoint is not None:
            for i in range(startPoint, stopPoint):
                # These need to be copied, because before filtering 
                # _rows_view[i] === _rows_model[i].  If we don't
                # copy then the _rows_model items will have a smaller
                # level as well.
                self._rows_view[i] = copy.copy(self._rows_view[i])
                self._rows_view[i].level -= 1

    def get_sortDirection(self):
        return self._sortDirection

    def set_sortDirection(self, value):
        self._sortDirection = value
        self.refreshFullView()

    def toggleOpenState(self, index, suppressUpdate=False):
        if self._unfilteredRows_view:
            # "trying to toggle while searching causes all kinds of grief"
            # - koKPFTreeView.p.py
            # To fix: make row info thinner.
            return

        rowNode = self._rows_model[index]
        if not suppressUpdate:
            firstVisibleRow = self._tree.getFirstVisibleRow()
        before_len = len(self._rows_view)
        self.toggleOpenStateModel(index + 1)
        self._filter_std_toolbox()
        after_len = len(self._rows_view)
        delta = after_len - before_len
        if delta:
            self._tree.rowCountChanged(index, delta)
        if not suppressUpdate:
            self._tree.ensureRowIsVisible(firstVisibleRow)
            self.selection.select(index)

    def toggleOpenStateModel(self, index):
        log.debug("toggleOpenStateModel: index:%d, node:%s", index, self._rows_model[index].name)
        rowNode = self._rows_model[index]
        if rowNode.isOpen:
            try:
                del self._nodeOpenStatusFromName[rowNode.path]
            except KeyError:
                pass
            nextIndex = self.getNextSiblingIndexModel(index)
            if nextIndex == -1:
                del self._rows_model[index + 1:]
            else:
                del self._rows_model[index + 1: nextIndex]
            rowNode.isOpen = False
        else:
            self._doContainerOpenModel(rowNode, index)
            self._nodeOpenStatusFromName[rowNode.path] = time.time()

    def _compareChildNode(self, item1, item2):
        # Nodes contain (id, name, type, isContainer)
        if self._sortDirection == self._SORT_BY_NATURAL_ORDER:
            folderDiff = cmp(not item1[3], not item2[3])
            if folderDiff:
                return folderDiff
        items = [item1, item2]
        if self._sortDirection == self._SORT_BY_NAME_DESCENDING:
            lowerIndex = 1
            upperIndex = 0
        else:
            lowerIndex = 0
            upperIndex = 1
        return cmp(items[lowerIndex][1].lower(), items[upperIndex][1].lower())

    def _sortAndExtractIDs(self, rowNode):
        if not hasattr(rowNode, 'unfilteredChildNodes'):
            rowNode.rebuildChildren()
        sortedNodes = sorted(rowNode.unfilteredChildNodes,
                             cmp=self._compareChildNode)
        return [x[0] for x in sortedNodes]

    def _doContainerOpenModel(self, rowNode, index):
        childIDs = self._sortAndExtractIDs(rowNode)
        if childIDs:
            posn = index + 1
            #for path_id, name, node_type in childNodes:
            for path_id in childIDs:
                toolPart = self._toolsManager.getToolById(path_id)
                if toolPart is None:
                    log.error("_doContainerOpenModel: getToolById(path_id:%r) => None", path_id)
                    continue
                toolView = _koToolHViewFromTool(toolPart)
                toolView.level = rowNode.level + 1
                self._rows_model.insert(posn, toolView)
                posn += 1
            rowNode.isOpen = True
            # Now open internal nodes working backwards
            lastIndex = index + len(childIDs)
            firstIndex = index
            # Work from bottom up so we don't have to readjust the index.
            for i, row in enumerate(self._rows_model[lastIndex: index: -1]):
                openNode = self._nodeOpenStatusFromName.get(row.path, None)
                if openNode:
                    self._doContainerOpenModel(row, lastIndex - i)

