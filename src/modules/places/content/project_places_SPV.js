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
    this._load_MRU_Projects();
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

this.activateView = function() {
    ko.projects.manager.setViewMgr(this.manager);
};

this._load_MRU_Projects = function() {
    var this_ = this;
    var currentProject = ko.projects.manager.currentProject;
    var currentURI = currentProject ? currentProject.uri : null;
    ko.mru.getAll("mruProjectList").forEach(function(uri) {
            if (uri != currentURI) {
                var project = Components.classes["@activestate.com/koUnopenedProject;1"]
                    .createInstance(Components.interfaces.koIUnopenedProject);
                project.url = uri;
                project.isDirty = false;
                this_.projectsTreeView.addUnopenedProject(project);
            }
        });
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
    selectionInfo.currentProject = (currentProject
                                    && currentProject.url == selectedUrl);
    selectionInfo.projectIsDirty = selectionInfo.currentProject && currentProject.isDirty;
    selectionInfo.itemTypes = itemTypes;
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
        var directive, disableNode = false;
        if (!ko.places.matchAllTypes(menuNode.getAttribute('hideUnless'), itemTypes)) {
            // hide the node
            menuNode.setAttribute('collapsed', true);
            continue;
        }
        directive = menuNode.getAttribute('disableIf');
        if (directive) {
            if ((directive in selectionInfo) && selectionInfo[directive]) {
                disableNode = true;
            } 
        }
        if (!disableNode
            && !!(directive = menuNode.getAttribute('disableUnless'))
            && (!(directive in selectionInfo)
                || !selectionInfo[directive])) {
            disableNode = true;
        }
        if (disableNode) {
            menuNode.setAttribute('disabled', true);
        } else {
            menuNode.removeAttribute('disabled');
        }
        if (menuNode.id == "menu_addItemToProject_projectsContext"
            && selectionInfo.currentProject) {
            var menupopup = menuNode.firstChild;
            if (menupopup.childNodes.length == 0) {
                ko.places.projects.copyNewItemMenu(menupopup, "SPV_projView_");
            }
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
    }
    ko.mru.deleteValue('mruProjectList', part.uri, true/*notify */);
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
        var currentProject = ko.projects.manager.currentProject;
        if (currentProject) {
            this.projectsTreeView.removeProject(currentProject);
        }
        this.projectsTreeView.removeProject(part);
        if (currentProject) {
            this.projectsTreeView.removeProject(currentProject);
            ko.projects.manager.closeProject(currentProject);
            var unopenedProject = Components.classes["@activestate.com/koUnopenedProject;1"]
                    .createInstance(Components.interfaces.koIUnopenedProject);
            unopenedProject.url = currentProject.url;
            unopenedProject.isDirty = false;
            this.projectsTreeView.addUnopenedProject(unopenedProject);
            var direction = _placePrefs.getLongPref("project_sort_direction");
            this.manager.sortProjects(direction);
        }
        ko.projects.open(part.url);
    }
};

}).apply(ko.places.projects_SPV);
