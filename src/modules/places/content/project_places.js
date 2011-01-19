/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

// Define the ko.places.projects namespace

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('places' in ko)) {
    ko.places = {};
}
if (!('projects' in ko.places)) {
    ko.places.projects = {};
}

(function() {

var log = getLoggingMgr().getLogger("project_places_js");
log.setLevel(LOG_DEBUG);

const PROJECT_URI_REGEX = /^.*\/(.+?)\.(?:kpf|komodoproject)$/;

var _globalPrefs;
var _placePrefs;
var _g_showProjectPath;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://places/locale/places.properties");

this.XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

this.createPlacesProjectView = function() {
    _globalPrefs = (Components.classes["@activestate.com/koPrefService;1"].
                   getService(Components.interfaces.koIPrefService).prefs);
    _placePrefs = _globalPrefs.getPref("places");
    _g_showProjectPath = _globalPrefs.getPref("places").getBooleanPref('showProjectPath');
    this.projectsTree = document.getElementById("placesSubpanelProjects");
    this.projectsTreeView = Components.classes["@activestate.com/koKPFTreeView;1"]
                          .createInstance(Components.interfaces.koIKPFTreeView);
    if (!this.projectsTreeView) {
        throw new Error("couldn't create a PlaceProjectsTreeView");
    }
    this.projectsTree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.projectsTreeView;
    this.projectsTreeView.initialize();
    this.initProjectMRUCogMenu();
    this.copyNewItemMenu(document.getElementById("projectView_AddItemPopup"),
                         "projCtxt_");
    this.manager = new PlacesProjectManager(this);
    ko.projects.manager.setViewMgr(this.manager);
};

this._copyTree = function(srcParentNode, destParentNode) {
    var srcNodes = srcParentNode.childNodes;
    var len = srcNodes.length;
    var attr, destNode, attributes;
    for (var i = 0; i < len; i++) {
        var srcNode = srcNodes[i];
        destNode = document.createElementNS(this.XUL_NS, srcNode.nodeName);
        attributes = srcNode.attributes;
        for (var j = 0; j < attributes.length; j++) {
            attr = attributes[j];
            destNode.setAttribute(attr.name, attr.value);
        }
        destNode.setAttribute("id", this._menuIdPrefix + srcNode.id);
        destParentNode.appendChild(destNode);
        this._copyTree(srcNode, destNode);
    }
}

function PlacesProjectManager(owner) {
    this.owner = owner;
}

PlacesProjectManager.prototype = {
  addProject: function(project) {
        this.owner.projectsTreeView.addProject(project);
    },
  getSelectedItem: function() {
        return this.owner.projectsTreeView.getSelectedItem();
    },
  refreshParentShowChild: function(parentPart, newPart) {
        return this.owner.refreshParentShowChild(parentPart, newPart);
    },
  
  refresh: function(project) {
        // this.owner.projectsTreeView.refresh(project);
        this.owner.projectsTreeView.invalidate();
    },
  refreshRow: function(project) {
        this.owner.projectsTreeView.refresh(project);
    },
  removeProject: function(project) {
        this.owner.projectsTreeView.removeProject(project);
    },
/*
  replaceProject: function(oldURL, project) {
        dump("**************** Drop replaceProject\n");
        return;
    },
*/
  savePrefs: function(project) {
        this.owner.projectsTreeView.savePrefs(project);
    },
  setCurrentProject: function(project) {
        this.owner.projectsTreeView.currentProject = project;
    },
  getSelectedItems: function(rootsOnly) {
        return this._getSelectedItems(rootsOnly);
    },

  _getSelectedItems: function(rootsOnly) {
        if (typeof(rootsOnly) == "undefined") rootsOnly = false;
        var o1 = {}, o2 = {};
        this.owner.projectsTreeView.getSelectedItems(rootsOnly, o1, o2);
        return o1.value;
    },
  
  _getSelectedItem: function(context) {
        var items = this._getSelectedItems();
        if (items.length != 1) {
            log.error(context + ": Expected 1 selected item, got " + items.length);
            return null;
        }
        var item = items[0];
        if (!item) {
            log.error(context + ": no part in selection");
            return null;
        }
        return item;
    },

  // Methods for the projects context menu

  addExistingFile: function(event, sender) {
        var parentPart = this._getSelectedItem("addExistingFile");
        var newParts = ko.projects.addFile(parentPart);
        if (newParts.length) {
            this.owner.projectsTreeView.showChild(parentPart, newParts[0]);
        }
    },

  addNewFile: function(event, sender) {
        var parentPart = this._getSelectedItem("addNewFile");
        var this_ = this;
        var callback = function(part) {
            if (part) {
                this_.owner.projectsTreeView.showChild(parentPart, part);
            }
        };
        // This has to be done via a callback because creating a file
        // via a template is an async call.
        ko.projects.addNewFileFromTemplate(parentPart, callback);
    },
  
  addGroup: function(event, sender) {
        var parentPart = this._getSelectedItem("addGroup");
        var part = ko.projects.addGroup(parentPart);
        if (part) {
            this.owner.projectsTreeView.showChild(parentPart, part);
        }
    },

  addLiveFolder: function(event, sender) {
        var parentPart = this._getSelectedItem("addLiveFolder");
        var prompt = _bundle.GetStringFromName("Select a new or existing folder");
        var path = ko.filepicker.getFolder(parentPart.project.getFile().dirName,
                                            prompt);
        if (!path) {
            return;
        }
        var uri = ko.uriparse.pathToURI(path);
        var part = ko.projects.addPartWithURLAndType(uri, 'livefolder', parentPart);
        if (part) {
            this.owner.projectsTreeView.showChild(parentPart, part);
        }
    },
  
  addRemoteFile: function(event, sender) {
        var parentPart = this._getSelectedItem("addExistingFile");
        var parts = ko.projects.addRemoteFile(parentPart);
        if (parts.length) {
            this.owner.projectsTreeView.showChild(parentPart, parts[0]);
        }
    },
  
  addRemoteFolder: function(event, sender) {
        var parentPart = this._getSelectedItem("addRemoteFolder");
        var part = ko.projects.addRemoteFolder(parentPart);
        if (part) {
            this.owner.projectsTreeView.showChild(parentPart, part);
        }
    },
  
  // The UI calls removeItems, which uses peFolder and baseManager
  // to actually delete the selected items.  It then calls into
  // removeSelectedItems, which will update the tree.
  
  removeItems: function(event, sender) {
        var parts = this._getSelectedItems(false);
        ko.projects.removeItems(parts, this.owner.projectsTreeView.selection.count);
    },
  removeSelectedItems: function(allItems) {
        // For updating the view, just get the roots
        var parts = this._getSelectedItems(true);
        this.owner.projectsTreeView.removeItems(parts, parts.length);
        this.owner.projectsTreeView.selection.clearSelection();
    },

  renameGroup: function(event, sender) {
        var part = this._getSelectedItem("renameGroup");
        var oldname = part.name;
        var newname = ko.dialogs.renameFileWrapper(oldname);
        if (!newname) {
            return;
        } else if (newname == oldname) {
            ko.dialogs.alert(_bundle.formatStringFromName("Old file and new basename are the same.template", [oldname, newname], 2));
            return;
        }
        part.name = newname;
    },
  
  _EOF_ : null
};

this.initProjectMRUCogMenu = function() {
    var srcMenu = document.getElementById("popup_project");
    var destMenu = document.getElementById("placesSubpanelProjectsToolsPopup");
    var srcNodes = srcMenu.childNodes;
    var node, newNode;
    var len = srcNodes.length;
    for (var i = 0; i < len; i++) {
        node = srcNodes[i];
        if (node.getAttribute("skipCopyToCogMenu") != "true") {
            newNode = node.cloneNode(false);
            newNode.id = node.id + "_places_projects_cog";
            destMenu.appendChild(newNode);
        }
    }
};

this.copyNewItemMenu = function(targetNode, targetPrefix) {
    var srcNodes = document.getElementById("placesSubpanelProjects_AddItemsMenu").childNodes;
    var attr, node, attributes;
    for (var i = 0; i < srcNodes.length; i++) {
        var srcNode = srcNodes[i];
        node = document.createElementNS(this.XUL_NS, srcNode.nodeName);
        attributes = srcNode.attributes;
        for (var j = 0; j < attributes.length; j++) {
            attr = attributes[j];
            node.setAttribute(attr.name, attr.value);
        }
        node.setAttribute("id", "projCtxt_" + srcNode.id);
        targetNode.appendChild(node);
    }
};

this.finishProjectsContextMenu = function(targetNode, targetPrefix) {
    var srcNodes = document.getElementById("placesSubpanelProjects_AddItemsMenu").childNodes;
    var target_tree = document.getElementById("menu_projCtxt_addMenu_Popup");
    var target_toolbar = document.getElementById("projectView_AddItemPopup");
    var attr, node, nodetb, attributes;
    for (var i = 0; i < srcNodes.length; i++) {
        var srcNode = srcNodes[i];
        node = document.createElementNS(this.XUL_NS, srcNode.nodeName);
        nodetb = document.createElementNS(this.XUL_NS, srcNode.nodeName);
        attributes = srcNode.attributes;
        for (var j = 0; j < attributes.length; j++) {
            attr = attributes[j];
            node.setAttribute(attr.name, attr.value);
            nodetb.setAttribute(attr.name, attr.value);
        }
        node.setAttribute("id", "projCtxt_" + srcNode.id);
        target_tree.appendChild(node);
        nodetb.setAttribute("id", "projView__" + srcNode.id);
        target_toolbar.appendChild(node);
    }
    //dump("# nodes added to menu_projCtxt_addMenu_Popup: \n");
    //dump("  " + target_tree.childNodes.length + "\n");
    //dump("# nodes added to projectView_AddItemPopup: \n");
    //dump("  " + target_toolbar.childNodes.length + "\n");
};

this.refreshParentShowChild = function(parentPart, newPart) {
    // Expand the extracted folder part and then select it.
    var treeview = this.projectsTreeView
    treeview.refresh(parentPart);
    var parentPartIndex = treeview.getIndexByPart(parentPart);
    if (parentPartIndex == -1) {
        log.warn("refreshParentShowChild: can't find part "
                 + parentPart.name
                 + " in the tree");
        return;
    }
    if (!treeview.isContainerOpen(parentPartIndex)) {
        treeview.toggleOpenState(parentPartIndex);
    }
    var childPartIndex  = treeview.getIndexByPart(newPart);
    if (childPartIndex == -1) {
        log.warn("refreshParentShowChild: can't find part "
                 + newPart.name
                 + " in the tree");
        return;
    }
    treeview.selection.select(childPartIndex);
    this.projectsTree.treeBoxObject.ensureRowIsVisible(childPartIndex);
};

this.terminate = function() {
    this.projectsTreeView.terminate();
};

// Methods for dealing with the projects tree context menu.

this._projectTestLabelMatcher = /^t:project\|(.+)\|(.+)$/;
this.allowed_click_nodes = ["placesSubpanelProjectsTreechildren",
                            "projectView_AddItemPopup",
                            "placesRootButton"],
this.initProjectsContextMenu = function(event, menupopup) {
    var clickedNodeId = event.explicitOriginalTarget.id;
    if (this.allowed_click_nodes.indexOf(clickedNodeId) == -1) {
        // We don't want to fillup this context menu (i.e. it's likely a
        // sub-menu such as the scc context menu).
        return false;
    } else if (clickedNodeId == "menu_projCtxt_addMenu_Popup") {
        return true;
    }
    var row = {};
    this.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    var treeView = this.projectsTreeView;
    var selectedIndices = ko.treeutils.getSelectedIndices(treeView,
                                                          false /*rootsOnly*/);
    var selectedItems = selectedIndices.map(function(i) treeView.getRowItem(i));
    var selectedUrls = selectedItems ? selectedItems.map(function(item) item.url) : [];
    var isRootNode = !selectedItems.length && index == -1;
    var itemTypes;
    if (isRootNode) {
        itemTypes = ['root'];
    } else {
        itemTypes = selectedItems.map(function(item) item.type);
    }
    var currentProject = ko.projects.manager.currentProject;
    this._selectionInfo = {
      currentProject: (selectedUrls.length == 1
                       && currentProject
                       && currentProject.url == selectedUrls[0]),
      index: index,
      itemTypes: itemTypes,
      multipleNodesSelected: selectedIndices.length > 1,
      projectIsDirty: selectedItems.filter(function(item) item.isDirty).length > 0,
      needSeparator: [false],
      lastVisibleNode: null,
      selectedUrls: selectedUrls,
      isLocal: selectedUrls[0].indexOf("file://") == 0,
      __END__:null
    };
    this._processProjectsMenu_TopLevel(menupopup);
    delete this._selectionInfo;
    return true;
}

this._processProjectsMenu_TopLevel = function(menuNode) {
    var selectionInfo = this._selectionInfo;
    var itemTypes = selectionInfo.itemTypes;
    if (ko.places.matchAnyType(menuNode.getAttribute('hideIf'), itemTypes)) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
    } else if (!ko.places.matchAllTypes(menuNode.getAttribute('hideUnless'), itemTypes)) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
    }
    if (menuNode.id == "menu_projCtxt_addMenu_Popup"
        && menuNode.childNodes.length == 0) {
        ko.places.projects.copyNewItemMenu(menuNode, "projView_");
        selectionInfo.lastVisibleNode = null;
    } else if (menuNode.nodeName == "menuseparator") {
        if (selectionInfo.needSeparator[0]) {
            menuNode.removeAttribute('collapsed');
            selectionInfo.needSeparator[0] = false;
            selectionInfo.lastVisibleNode = menuNode;
        } else {
            menuNode.setAttribute('collapsed', true);
        }
        return;
    }
    selectionInfo.needSeparator[0] = true;
    selectionInfo.lastVisibleNode = menuNode;
    menuNode.removeAttribute('collapsed');
    var disableNode = false;
    if (ko.places.matchAnyType(menuNode.getAttribute('disableIf'), itemTypes)) {
        disableNode = true;
    } else if (!ko.places.matchAllTypes(menuNode.getAttribute('disableUnless'), itemTypes)) {
        disableNode = true;
    }
    if (!disableNode) {
        var testDisableIf = menuNode.getAttribute('testDisableIf');
        if (testDisableIf) {
            testDisableIf = testDisableIf.split(/\s+/);
            testDisableIf.map(function(s) {
                    if (s == 't:currentProject' && selectionInfo.currentProject) {
                        disableNode = true;
                    } else if (s == "t:multipleSelection" && selectionInfo.multipleNodesSelected) {
                        disableNode = true;
                    }
                });
        }
        if (!disableNode) {
            var testDisableUnless = menuNode.getAttribute('testDisableUnless');
            if (testDisableUnless) {
                testDisableUnless = testDisableUnless.split(/\s+/);
                var anyTestPasses = false;
                testDisableUnless.map(function(s) {
                        if (!anyTestPasses && s == 't:projectIsDirty' && selectionInfo.projectIsDirty) {
                            anyTestPasses = true;
                        }
                });
                disableNode = !anyTestPasses;
            }
        }
    }
    if (disableNode) {
        menuNode.setAttribute('disabled', true);
    } else {
        menuNode.removeAttribute('disabled');
    }
    if (menuNode.id == "menu_projCtxt_SCCmenu") {
        selectionInfo.isFolder = (selectionInfo.itemTypes[0] == 'project'
                                  || selectionInfo.itemTypes[0] == 'folder'
                                  || gPlacesViewMgr.view.isContainer(selectionInfo.index));
        this.initProject_SCC_ContextMenu(menuNode);
        return;
    }
    var childNodes = menuNode.childNodes;
    var childNodesLength = childNodes.length;
    if (childNodesLength) {
        selectionInfo.needSeparator.unshift(false);
        for (var i = 0; i < childNodesLength; i++) {
            this._processProjectsMenu_TopLevel(childNodes[i]);
        }
        if (selectionInfo.lastVisibleNode
            && selectionInfo.lastVisibleNode.nodeName == "menuseparator") {
            // Collapse the final node
            selectionInfo.lastVisibleNode.setAttribute('collapsed', true);
            selectionInfo.lastVisibleNode = null;
        }
        selectionInfo.needSeparator.shift();
    }
};

this.initProject_SCC_ContextMenu = function(menuNode) {
    var popupmenu = menuNode.childNodes[0];
    var selectionInfo = this._selectionInfo;
    if (!selectionInfo.isLocal) {
        ko.places.viewMgr._disable_all_items(popupmenu);
        return;
    }
    var enabled_scc_components = ko.scc.getAvailableSCCComponents(true);
    if (!enabled_scc_components.length) {
        // No scc components are enabled for functional.
        ko.places.viewMgr._disable_all_items(popupmenu);
        return;
    }
    if (selectionInfo.multipleNodesSelected) {
        ko.places.viewMgr._disable_all_items(popupmenu);
        return;
    }
    var index = selectionInfo.index;
    var uri = selectionInfo.selectedUrls[0];
    var fileObj = (Components.classes["@activestate.com/koFileService;1"].
                   getService(Components.interfaces.koIFileService).
                   getFileFromURI(uri));
    var sccObj = {};
    var isFolder = false;
    if (!ko.places.viewMgr._determineItemSCCSupport(fileObj, sccObj, isFolder)) {
        // use this function to disable everything
        ko.places.viewMgr._disable_all_items(popupmenu);
        return;
    }
    var status_by_name = ko.places.viewMgr.setupSCCStatus(fileObj, sccObj, isFolder);
    for (var menuitem, i = 0; menuitem = popupmenu.childNodes[i]; ++i) {
        var id = menuitem.id;
        var commonPart = "menu_projCtxt_sccButton";
        var lastPart = id.substring(commonPart.length).toLowerCase();
        if (status_by_name[lastPart]) {
            menuitem.removeAttribute("disabled");
            var command = ("ko.projects.SCC.doCommand('"
                           + menuitem.getAttribute("observes")
                           + "');");
            menuitem.setAttribute("oncommand", command);
        } else {
            menuitem.setAttribute("disabled", "true");
        }
    }
};

this.getFocusedProjectView = function() {
    if (xtk.domutils.elementInFocus(document.getElementById('placesSubpanelProjects'))) {
        return this;
    }
    return null;
};

this.onProjectTreeDblClick = function(event) {
    if (event.which != 1) {
        return;
    }
    var row = {};
    this.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    if (index != -1) {
        var part = this.projectsTreeView.getRowItem(index);
        if (!part) {
            log.error("onProjectTreeDblClick(" + index + ") => null\n");
        } else {
            var uri = part.url;
            switch (part.type) {
                case "project":
                    var currentProject = ko.projects.manager.currentProject;
                    if (!currentProject || currentProject.id != part.id) {
                        ko.projects.manager.setCurrentProject(part);
                    }
                    this.showProjectInPlaces(part);
                    break;

                case "livefolder":
                    ko.places.manager.openDirectory(part.getFile().path);
                    break;

                case "file":
                    ko.open.multipleURIs([uri]);
                    break;
            }
        }
    }
    event.stopPropagation();
    event.preventDefault();
};

this._getProjectItemAndOperate = function(context, obj, callback) {
    if (typeof(callback) == "undefined") callback = context;
    var items = this.manager.getSelectedItems();
    if (items.filter(function(item) item.type != "project").length) {
        log.warn("Function " + context + " is intended only for projects");
        return;
    }
    items.map(function(project) {
        obj[callback].call(obj, project);
        });
};
        

this.closeProject = function() {
    this._getProjectItemAndOperate("closeProject", ko.projects.manager);
};

this.compareFileWith = function() {
    var items = this.manager.getSelectedItems();
    if (!items || !items[0]) {
        return;
    } else if (items.length != 1) {
        log.warn("Function compareFileWith is intended only for a single file");
        return;
    } else if (["file", "project"].indexOf(items[0].type) == -1) {
        log.warn("Function compareFileWith is intended only for files or projects, got an item of type:" + items[0].type);
        return;
    }
    var url = items[0].url;
    var file = Components.classes["@activestate.com/koFileEx;1"].
    createInstance(Components.interfaces.koIFileEx);
    file.URI = url;
    var pickerDir = file.isLocal? file.dirName : '';
    var otherfile = ko.filepicker.browseForFile(pickerDir);
    if (otherfile) {
        ko.fileutils.showDiffs(file.path, otherfile);
    }
};

this.rebaseFolder = function() {
    var items = this.manager.getSelectedItems();
    if (!items || !items[0]) {
        return;
    } else if (items.length != 1) {
        log.warn("Function rebaseFolder is intended only for a single file");
        return;
    } else if (items[0].type != "livefolder") {
        log.warn("Function rebaseFolder is intended only for folders, got an item of type:" + items[0].type);
        return;
    }
    ko.places.manager.openDirURI(items[0].url);
};

this.exportAsProjectFile = function() {
    var items = this.manager.getSelectedItems();
    if (items.length != 1 || !items[0] || items[0].type != "folder") {
        log.warn("Function exportAsProjectFile is intended only for groups");
        return;
    }
    ko.projects.exportItems(items);
};

this.exportPackage = function() {
    var items = this.manager.getSelectedItems();
    var validTypes = ["folder", "project"];
    if (items.filter(function(item) validTypes.indexOf(item.type) == -1).length) {
        log.warn("Function exportPackage is intended only for "
                 + validTypes);
        return;
    }
    ko.projects.exportPackageItems(items);
};

this.importPackage = function() {
    var item = this.manager.getSelectedItem();
    if (!item || item.type != "folder") {
        log.warn("Function importPackage is intended only for groups");
        return;
    }
    ko.projects.importFromPackage(this.manager, item);
};

this.makeCurrentProject = function() {
    var this_ = this;
    this._getProjectItemAndOperate("makeCurrentProject", this,
                                   "_continueMakeCurrentProject");
};

this.openFiles = function() {
    var items = this.manager.getSelectedItems();
    if (items.filter(function(item) item.type != "file").length) {
        log.warn("Function openFiles is intended only for files");
        return;
    }
    ko.open.multipleURIs(items.map(function(item) item.url));
};

this._continueMakeCurrentProject = function(project) {
    ko.projects.manager.setCurrentProject(project);
    this.projectsTreeView.invalidate();
}

this.refreshFileStatus = function() {
    var items = this.manager.getSelectedItems();
    if (!items || items.length == 0) {
        return;
    }
    var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].getService(Components.interfaces.koIFileStatusService);
    fileStatusSvc.updateStatusForUris(items.length,
                                      items.map(function(item) item.url),
                                      true /* forcerefresh */);
};

this.revertProject = function() {
    this._getProjectItemAndOperate("revertProject", ko.projects.manager);
};

this.saveProject = function() {
    this._getProjectItemAndOperate("saveProject", ko.projects.manager);
};

this.saveProjectAs = function() {
    this._getProjectItemAndOperate("saveProjectAs", ko.projects);
};

this.showProjectInPlaces = function() {
    this._getProjectItemAndOperate("showProjectInPlaces",
                                   ko.places.manager, "moveToProjectDir");
};

this.openProjectInNewWindow = function() {
    this._openProject(true);
};

this.openProjectInCurrentWindow = function() {
    this._openProject(false);
}

this._openProject = function(inNewWindow) {
    var defaultDirectory = null;
    var defaultFilename = null;
    var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/projectManager.properties");
    var title = bundle.GetStringFromName("openProject.title");
    var defaultFilterName = bundle.GetStringFromName("komodoProject.message");
    var filterNames = [bundle.GetStringFromName("komodoProject.message"),
                       bundle.GetStringFromName("all.message")];
    filename = ko.filepicker.openFile(defaultDirectory /* =null */,
                                      defaultFilename /* =null */,
                                      title /* ="Open File" */,
                                      defaultFilterName /* ="All" */,
                                      filterNames /* =null */)
    if (filename == null) return;
    uri = ko.uriparse.localPathToURI(filename);
    if (inNewWindow) {
        ko.launch.newWindow(uri);
    } else {
        ko.projects.open(uri);
    }
};

this.editProjectProperties = function() {
    var items = this.manager.getSelectedItems();
    var filtered_items = items.filter(function(item) item.type != "project");
    if (filtered_items.length) {
        log.warn("Function editProjectProperties is intended only for projects");
        return;
    } else if (items.length != 1) {
        log.warn("Function editProjectProperties is intended for only one project");
        return;
    }
    var item = ko.places.getItemWrapper(items[0].url, 'project');
    ko.projects.fileProperties(item, null, true);
};

this.toggleSubpanel = function() {
    var button = document.getElementById("placesSubpanelToggle");
    var state = button.getAttribute("state");
    switch(state) {
    case "collapsed":
        button.setAttribute("state", "open");
        break;
    case "open":
    default:
        button.setAttribute("state", "collapsed");
        break;
    }
    this._updateSubpanelFromState();
};

this._updateSubpanelFromState = function() {
    var button = document.getElementById("placesSubpanelToggle");
    var deck = document.getElementById("placesSubpanelDeck");
    var state = button.getAttribute("state");
    switch(state) {
    case "collapsed":
        deck.collapsed = true;
        break;
    case "open":
    default:
        deck.collapsed = false;
        break;
    }
}

xtk.include("treeview");
this.PlaceProjectsTreeView = function() {
    xtk.dataTreeView.apply(this, []);
    this._atomService = Components.classes["@mozilla.org/atom-service;1"].
                            getService(Components.interfaces.nsIAtomService);
}
this.PlaceProjectsTreeView.prototype = new xtk.dataTreeView();
this.PlaceProjectsTreeView.prototype.constructor = this.PlaceProjectsTreeView;

this.PlaceProjectsTreeView.prototype.initialize = function() {
    this._initRows();
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
    this.pref_observer_names = [ "showProjectPath" ];
    _placePrefs.prefObserverService.addObserverForTopics(this,
                                         this.pref_observer_names.length,
                                         this.pref_observer_names, true);
};

this.PlaceProjectsTreeView.prototype.terminate = function() {
    _placePrefs.prefObserverService.removeObserverForTopics(this,
                                            this.pref_observer_names.length,
                                            this.pref_observer_names);
};

this.PlaceProjectsTreeView.prototype._initRows = function() {
    this.rows = [];
};

this.PlaceProjectsTreeView.prototype._resetRows = function() {
    var this_ = this;
};

this.PlaceProjectsTreeView.prototype.observe = function(subject, topic, data) {
    if (data == "mruProjectList") {
        this._resetRows();
    } else if (topic == "showProjectPath") {
        _g_showProjectPath = _globalPrefs.getPref("places").getBooleanPref('showProjectPath');
        this._resetRows();
    }
};

this.PlaceProjectsTreeView.prototype._getViewPart = function(uri) {
    if (!_g_showProjectPath) {
        var m = PROJECT_URI_REGEX.exec(uri);
        if (m) {
            return decodeURIComponent(m[1]);
        }
    }
    var path = ko.uriparse.URIToPath(uri);
    var name, lastSlash, lastDot;
    if (!_g_showProjectPath) {
        lastSlash = uri.lastIndexOf('/');
        if (lastSlash > -1) {
            lastDot = uri.lastIndexOf(".");
            if (lastDot > -1
                && ['.komodoproject', '.kpf'].indexOf(uri.substr(lastDot)) > -1) {
                // Standard -- ends with ".komodoproject" or ".kpf"
                path = path.substring(lastSlash + 1, lastDot);
            } else {
                path = path.substring(lastSlash + 1);
            }
        }
        // else do nothing -- show the extension as well.
    }
    return path;
}

this.PlaceProjectsTreeView.prototype.replaceProject = function(oldURL, project) {
    var listLen = this.rows.length;
    for (var i = listLen - 1; i >= 0; --i) {
        if (oldURL == this.rows[i][0]) {
            this.rows[i][0] = project.url;
            this.rows[i][1] = this._getViewPart(project.url);
            this.tree.invalidateRow(i);
            return;
        }
    }
    dump("PlaceProjectsTreeView.replaceProject: Couldn't find "
         + project.name
         + " in the list of loaded projects\n");
};

// Context Menu Methods
this.PlaceProjectsTreeView.prototype.doProjectContextMenu = function(event, sender, cmd) {
    var index = this.getSelectedIndex();
    if (index == -1) {
        index = this.currentProjectIndex();
        if (index == -1) {
            dump("no selected or current project: leave\n");
        }
    }
    var project = this.rows[index].project;
    dump("**************** " + cmd  + "(" + index + ")\n");
};

// Project/Part Accessor Methods
this.PlaceProjectsTreeView.prototype.currentProjectIndex = function() {
    var currentProject = ko.projects.manager.currentProject;
    if (!currentProject) {
        return -1;
    }
    var lim = this.rows.length;
    for (var i = 0; i < lim; i++) {
        var row = this.rows[i];
        if (row.type == "project" && row.url == currentProject.url) {
            return i;
        }
    }
    return -1;
}

this.PlaceProjectsTreeView.prototype.getSelectedProject = function() {
    var index = this.getSelectedIndex();
    if (index == -1) {
        return null;
    }
    var item;
    for (; i >= 0; --i) {
        var node = this.rows[i];
        if (node.type == "project") {
            return node;
        }
    }
    return null;
}

// NSITreeView methods.

this.PlaceProjectsTreeView.prototype.getNextSiblingIndex = function(index) {
/**
 * @param {int} index points to the node whose next-sibling we want to find.
 *
 * @return index of the sibling, or -1 if not found.
 */
    var level = this.rows[index].level;
    var listLen = this.rows.length;
    index += 1
    while (index < listLen) {
        if (this.rows[index].level <= level) {
            return index;
        }
        index += 1;
    }
    return -1;
};

}).apply(ko.places.projects);
