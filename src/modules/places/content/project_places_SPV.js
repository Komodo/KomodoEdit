// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

// Define the ko.places.projects_SPV namespace
// This is used for implementing the v6.0-style single-project-view project system

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('places' in ko)) {
    ko.places = {};
}
if (!('projects_SPV' in ko.places)) {
    ko.places.projects_SPV = {};
}

(function() {

var _globalPrefs;
var _placePrefs;
const PROJECT_URI_REGEX = /^.*\/(.+?)\.(?:kpf|komodoproject)$/;

var log = ko.logging.getLogger("project_places_SPV_js");
log.setLevel(ko.logging.LOG_DEBUG);

this.createProjectMRUView = function() {
    _globalPrefs = (Components.classes["@activestate.com/koPrefService;1"].
                   getService(Components.interfaces.koIPrefService).prefs);
    _placePrefs = _globalPrefs.getPref("places");
    this.projectsTree = document.getElementById("placesSubpanelProjects_SPV");
    this.projectsTreeView = Components.classes["@activestate.com/koKPFTreeView;1"]
                          .createInstance(Components.interfaces.koIKPFTreeView);
    if (!this.projectsTreeView) {
        throw new Error("couldn't create a KPF ProjectsTreeView");
    }
    this.projectsTree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.projectsTreeView;
    this.projectsTreeView.initialize();
    this.manager = new ko.places.projects.PlacesProjectManager(this);
    ko.projects.manager.setViewMgr(this.manager);
    this.projectCommandHelper = new ko.places.projects.ProjectCommandHelper(this, this.manager);
    // Delegate all the context-menu commands to the projectCommandHelper
    this.projectCommandHelper.injectHelperFunctions(this);
    this.load_MRU_Projects();
    document.getElementById("placesSubpanelProjects_SPV").addEventListener("keypress", this.handleOnTreeKeypress, true);
};

this.handleOnTreeKeypress = function(event) {
    return ko.places.projects_SPV.onTreeKeyPress(event);
}

this.activateView = function() {
    ko.projects.manager.setViewMgr(this.manager);
};

this.rebuildView = function() {
    this.projectsTree.treeBoxObject.beginUpdateBatch();
    try {
        this.projectsTreeView.clearTree();
        var currentProject = ko.projects.manager.currentProject;
        if (currentProject) {
            this.projectsTreeView.addProject(currentProject);
        }
        this.load_MRU_Projects();
    } finally {
        this.projectsTree.treeBoxObject.endUpdateBatch();
    }
};

this.load_MRU_Projects = function() {
    var this_ = this;
    var currentProject = ko.projects.manager.currentProject;
    var currentURI = currentProject ? currentProject.url : null;
    ko.mru.getAll("mruProjectList").forEach(function(uri) {
            if (uri != currentURI) {
                var project = Components.classes["@activestate.com/koUnopenedProject;1"]
                    .createInstance(Components.interfaces.koIUnopenedProject);
                project.url = uri;
                project.isDirty = false;
                this_.projectsTreeView.addUnopenedProject(project);
            }
        });
    if (_placePrefs.hasPref("project_sort_direction")) {
        // See bug 89283 for an explanation of why all windows
        // now have the same sort direction.
        var direction = _placePrefs.getLongPref("project_sort_direction");
        setTimeout(function(this_) {
                this_.manager.sortProjects(direction);
            }, 1, this);
    } else {
        // dump('loading... _placePrefs.hasPref("project_sort_direction"): not found\n');
    }
};

this.refreshParentShowChild = function(parentPart, newPart) {
    ko.places.projects.refreshParentShowChildWithTreeview(parentPart, newPart,
                                                          this.projectsTree,
                                                          this.projectsTreeView);
};

this.removeUnopenedProject = function(url) {
    // Remove the URI, if found
    var part = this.projectsTreeView.getRowItemByURI(url)
    if (part) {
        if (part.url != url) {
            log.debug("**************** Expecting part for <\n"
                 + url
                 + "\n>, got part with url <\n"
                 + part.url
                 + ">");
            return;
        }
        this.projectsTreeView.removeItems([part], 1);
    } else {
        log.debug("Couldn't find a part for url " + url);
    }
};


// Methods for dealing with the projects tree context menu.

this._projectTestLabelMatcher = /^t:project\|(.+)\|(.+)$/;
//dev note: 
// initProjectsContextMenu used at 
// menupopup id="placesSubpanelProjectsContextMenu_SPV"
// refers to ko.places.projects_SPV.initProjectsContextMenu(event, this);
this.initProjectsContextMenu = function(event, menupopup) {
    if (event.explicitOriginalTarget.id
        != "placesSubpanelProjectsTreechildren_SPV") {
        // Invoked by an inner popupmenu.
        return true;
    }
    var row = {};
    this.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    if (index == -1) {
        // Means that we're clicking in white-space below.
        // Clear the selection, and return.
        this.projectsTreeView.selection.clearSelection();
        event.stopPropagation();
        event.preventDefault();
        return false;
    }
    var selectedUrl = this.getCellValue(index, "url");
    var selectionInfo = {};
    var treeView = this.projectsTreeView;
    var selectedIndices = ko.treeutils.getSelectedIndices(treeView,
                                                          false /*rootsOnly*/);
    var selectedItems = selectedIndices.map(function(i) treeView.getRowItem(i));
    var currentProject = ko.projects.manager.currentProject;
    if (!selectedItems.length && currentProject) {
        selectedItems = [currentProject];
    }
    var selectedUrls = selectedItems ? selectedItems.map(function(item) item.url) : [];
    var isRootNode = !selectedItems.length && index == -1;
    var itemTypes;
    if (isRootNode) {
        itemTypes = ['root'];
    } else {
        itemTypes = selectedItems.map(function(item) item.type);
    }
    if (!currentProject) {
        selectionInfo.currentProject = false;
    } else {
        for (var j = index; j >= 0 && treeView.getLevel(j) > 0; j--) {
            //EMPTY
        }
        selectionInfo.currentProject = (j >= 0
                                        && (currentProject.url ==
                                            treeView.getRowItem(j).url));
    }
    selectionInfo.projectIsDirty = selectionInfo.currentProject && currentProject.isDirty;
    selectionInfo.itemTypes = itemTypes;
    selectionInfo.isLocal = selectedUrls.every(function(uri) uri.indexOf("file:/") == 0);
    selectionInfo.isRemote = !selectionInfo.isLocal;
    selectionInfo.multipleNodesSelected = selectedUrls.length != 1;
    var projectIsOpen = false;
    var windows = ko.windowManager.getWindows();
    for (var win, i = 0; win = windows[i]; i++) {
        var otherProject = win.ko.projects.manager.currentProject;
        if (otherProject && otherProject.url == selectedUrl) {
            projectIsOpen = true;
            break;
        }
    }
    selectionInfo.projectIsOpen = projectIsOpen;
    
    var childNodes = menupopup.childNodes;
    for (var menuNode, i = 0; menuNode = childNodes[i]; i++) {
        var directive;
        if (!!(directive = menuNode.getAttribute('hideIf'))
            && ko.places.matchAnyType(menuNode.getAttribute('hideIf'), itemTypes)) {
            // hide the node
            menuNode.setAttribute('collapsed', true);
            continue; // No need to do anything else
        } else if (!!(directive = menuNode.getAttribute('hideUnless'))
                   && !ko.places.matchAnyType(directive, itemTypes)) {
            menuNode.setAttribute('collapsed', true);
            continue;
        }
        menuNode.removeAttribute('collapsed');
        ko.places.testDisableNode(menuNode, selectionInfo);
        if (menuNode.id == "menu_addItemToProject_projectsContext") {
            menupopup = menuNode.firstChild;
            if (menupopup.childNodes.length == 0) {
                ko.places.projects.copyNewItemMenu(menupopup, "SPV_projView_");
            }
        } else if (menuNode.id == "menu_SCCmenu_projectsContext") {
            var commonMenuIdPart = "menu_projCtxt_SPV_sccMenu";
            this._selectionInfo = selectionInfo;
            // ko.places.projects.initProject_SCC_ContextMenu expects
            // these fields on selectionInfo
            selectionInfo.index = index;
            selectionInfo.selectedUrls = selectedUrls;
            ko.places.projects.initProject_SCC_ContextMenu.call(this, menuNode, commonMenuIdPart);
        }
    }
    return true;
};

this.getCellValue = function(index, columnName) {
    if (typeof(columnName) == "undefined") {
        columnName = 'placesSubpanelProjectNameTreecol_MPV';
    }
    return this.projectsTreeView.getCellValue(index, {id : columnName});
}

this.openProjectInNewWindow = function() {
    this._openProject(true);
};

this.openProjectInCurrentWindow = function() {
    this._openProject(false);
}

this.removeProjectListing = function() {
    var index = this.projectsTreeView.selection.currentIndex;
    if (index == -1) {
        log.debug("removeProjectListing: No index");
        return;
    }
    var part = this.projectsTreeView.getRowItem(index);
    if (!part) {
        log.debug("removeProjectListing: No part at index:" + index);
        return;
    } else if (part.type != "unopened_project") {
        log.debug("removeProjectListing: opened-project part at index:" + index);
        return;
    }
    ko.mru.deleteValue('mruProjectList', part.url, true/*notify */);
    this.projectsTreeView.removeProject(part);
}

this._openProject = function(inNewWindow) {
    var index = this.projectsTreeView.selection.currentIndex;
    if (index == -1) {
        return;
    }
    var part = this.projectsTreeView.getRowItem(index);
    if (part.type != "unopened_project") {
        ko.dialogs.alert("Unexpected error: expecting type of project "
                         + part.name
                         + " to be 'unopened_project', but it's "
                         + part.type);
        return;
    }
    if (inNewWindow) {
        ko.launch.newWindow(part.url);
    } else {
        ko.projects.open(part.url);
    }
};

this.onTreeKeyPress = function(event) {
    var t = event.originalTarget;
    if (t.localName != "treechildren" && t.localName != 'tree') {
        return false;
    }
    // Special-case some commands, and then look at the keybinding set
    // to determine a command to do.
    if (!(event.shiftKey || event.ctrlKey || event.altKey)) {
        if (ko.places.viewMgr.arrowKeys.indexOf(event.keyCode) >= 0) {
            // Nothing to do but squelch the keycode
            event.stopPropagation();
            event.preventDefault();
            return false;
        } else if (event.keyCode == event.DOM_VK_RETURN) {
            // ENTER/RETURN should be handled by xbl bindings.
            this.handleReturn();
            event.stopPropagation();
            event.preventDefault();
            return true;
        } else if (event.keyCode == event.DOM_VK_DELETE) {
            this.removeProjectListing();
            event.cancelBubble = true;
            event.stopPropagation();
            event.preventDefault();
            return true;
        }
    }
    return false;
};

this.handleReturn = function() {
    var index = this.projectsTreeView.selection.currentIndex;
    if (index == -1) {
        return;
    }
    this.onProjectTreeDblClick(undefined, index);
}

}).apply(ko.places.projects_SPV);
