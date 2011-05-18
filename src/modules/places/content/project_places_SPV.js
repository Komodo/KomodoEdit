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
    this.projectsTreeView = new this.recentProjectsTreeView();
    if (!this.projectsTreeView) {
        throw new Error("couldn't create a recentProjectsTreeView");
    }
    this.projectsTree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.projectsTreeView;
    this.projectsTreeView.initialize();
};

// Methods for dealing with the projects tree context menu.

this._projectTestLabelMatcher = /^t:project\|(.+)\|(.+)$/;
//dev note: 
// initProjectsContextMenu used at 
// menupopup id="placesSubpanelProjectsContextMenu_SPV"
// refers to ko.places.projects_SPV.initProjectsContextMenu(event, this);
this.initProjectsContextMenu = function(event, menupopup) {
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
    var selectedUrl = this.projectsTreeView.getCellValue(index);
    var selectionInfo = {};
    var currentProject = ko.projects.manager.currentProject;
    selectionInfo.currentProject = (currentProject
                                    && currentProject.url == selectedUrl);
    selectionInfo.projectIsDirty = selectionInfo.currentProject && currentProject.isDirty;
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
        var disableNode = false;
        var directive = menuNode.getAttribute('disableIf');
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
    }
    return true;
};

this.onProjectTreeDblClick = function(event) {
    if (event.which != 1) {
        return;
    }
    var row = {};
    this.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    if (index != -1) {
        var uri = this.projectsTreeView.getCellValue(index);
        var currentProject = ko.projects.manager.currentProject;
        if (!currentProject || currentProject.url != uri) {
            ko.projects.open(uri);
        } else {
            this.showProjectInPlaces();
        }
    }
    event.stopPropagation();
    event.preventDefault();
};

this.showProjectInPlaces = function() {
    ko.places.manager.moveToProjectDir(ko.projects.manager.currentProject);
};

this.closeProject = function() {
    ko.projects.manager.closeProject(ko.projects.manager.currentProject,
                                     /* single_project_view= */ true);
};

this.saveProject = function() {
    ko.projects.manager.saveProject(ko.projects.manager.currentProject);
};

this.saveProjectAs = function() {
    ko.projects.saveProjectAs(ko.projects.manager.currentProject);
};

this.revertProject = function() {
    ko.projects.manager.revertProject(ko.projects.manager.currentProject,
                                      /* single_project_view= */ true);
};

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
    var uri = this.projectsTreeView.getCellValue(index);
    if (!uri) {
        log.debug("removeProjectListing: No uri at index:" + index);
        return;
    }
    ko.mru.deleteValue('mruProjectList', uri, true/*notify */);
}

this._openProject = function(inNewWindow) {
    var index = this.projectsTreeView.selection.currentIndex;
    if (index == -1) {
        return;
    }
    var uri = this.projectsTreeView.getCellValue(index);
    if (inNewWindow) {
        ko.launch.newWindow(uri);
    } else {
        ko.projects.open(uri);
    }
};

this.editProjectProperties = function() {
    var item = ko.places.getItemWrapper(ko.projects.manager.currentProject.url, 'project');
    ko.projects.fileProperties(item, null, true);
};

xtk.include("treeview");
this.recentProjectsTreeView = function() {
    xtk.dataTreeView.apply(this, []);
    this._atomService = Components.classes["@mozilla.org/atom-service;1"].
                            getService(Components.interfaces.nsIAtomService);
}
this.recentProjectsTreeView.prototype = new xtk.dataTreeView();
this.recentProjectsTreeView.prototype.constructor = this.recentProjectsTreeView;

this.recentProjectsTreeView.prototype.initialize = function() {
    this._resetRows();
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
    observerSvc.addObserver(this, "mru_changed", false);
    this.pref_observer_names = [ "showProjectPath" ];
    _placePrefs.prefObserverService.addObserverForTopics(this,
                                         this.pref_observer_names.length,
                                         this.pref_observer_names, true);
};

this.recentProjectsTreeView.prototype.terminate = function() {
    _placePrefs.prefObserverService.removeObserverForTopics(this,
                                            this.pref_observer_names.length,
                                            this.pref_observer_names);
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    try {
        observerSvc.removeObserver(this, "mru_changed");
    } catch(ex) {
        // Sometimes during shutdown this throws a 0x80004005 exception
    }
};

this.recentProjectsTreeView.prototype._resetRows = function() {
    var showProjectPath = _globalPrefs.getPref("places").getBooleanPref('showProjectPath');
    var rows = ko.mru.getAll("mruProjectList").map(function(uri) {
            if (!showProjectPath) {
                var m = PROJECT_URI_REGEX.exec(uri);
                if (m) {
                    return [uri, decodeURIComponent(m[1])];
                }
            }
            var path = ko.uriparse.URIToPath(uri);
            var name, lastSlash, lastDot;
            if (!showProjectPath) {
                var lastSlash = uri.lastIndexOf('/');
                if (lastSlash > -1) {
                    var lastDot = uri.lastIndexOf(".");
                    if (lastDot > -1
                        && ['.komodoproject', '.kpf'].indexOf(uri.substr(lastDot)) > -1) {
                        // Standard -- ends with ".komodoproject" or ".kpf"
                        path = path.substring(lastSlash + 1, lastDot);
                    } else {
                        path = path.substring(lastSlash + 1);
                    }
                }
                // else Do nothing
            } else {
                var lastDot = path.lastIndexOf(".");
                if (lastDot > -1
                    && ['.komodoproject', '.kpf'].indexOf(path.substr(lastDot)) > -1) {
                    path = path.substr(0, lastDot);
                }
            }
            return [uri, path];
        });
    rows.reverse();
    this.rows = rows;
};
this.recentProjectsTreeView.prototype.observe = function(subject, topic, data) {
    if (data == "mruProjectList") {
        this._resetRows();
    } else if (topic == "showProjectPath") {
        this._resetRows();
    }
};
// NSITreeView methods.
this.recentProjectsTreeView.prototype.getCellText = function(index, column) {
    var row = this.rows[index];
    var currentProject = ko.projects.manager.currentProject;
    if (currentProject
        && currentProject.isDirty
        && currentProject.url == row[0]) {
        return row[1] + "*";
    } else {
        return row[1];
    }
};
this.recentProjectsTreeView.prototype.getCellValue = function(index, column) {
    return this.rows[index][0];
};
this.recentProjectsTreeView.prototype.getImageSrc = function(index, column) {
    return 'chrome://komodo/skin/images/project_icon.png'
};
this.recentProjectsTreeView.prototype.getCellProperties = function(index, column, properties) {
    var row = this.rows[index];
    var currentProject = ko.projects.manager.currentProject;
    if (currentProject && currentProject.url == row[0]) {
        properties.AppendElement(this._atomService.getAtom("projectActive"));
    }
};

}).apply(ko.places.projects_SPV);
