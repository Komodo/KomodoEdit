// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

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

var _globalPrefs;
var _placePrefs;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://places/locale/places.properties");

this.createProjectMRUView = function() {
    _globalPrefs = (Components.classes["@activestate.com/koPrefService;1"].
                   getService(Components.interfaces.koIPrefService).prefs);
    _placePrefs = _globalPrefs.getPref("places");
    this.projectsTree = document.getElementById("placesSubpanelProjects");
    this.projectsTreeView = new this.PlaceProjectsTreeView();
    if (!this.projectsTreeView) {
        throw new Error("couldn't create a PlaceProjectsTreeView");
    }
    this.projectsTree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.projectsTreeView;
    this.projectsTreeView.initialize();
    this.initProjectMRUCogMenu();
    this.manager = new PlacesProjectManager(this);
    ko.projects.manager.setViewMgr(this.manager);
};

function PlacesProjectManager(owner) {
    this.owner = owner;
}

PlacesProjectManager.prototype = {
  addProject: function(project) {
        this.owner.projectsTreeView.addProject(project);
    },
  refresh: function(project) {
        this.owner.projectsTreeView.tree.invalidate();
    },
  removeProject: function(project) {
        this.owner.projectsTreeView.removeProject(project);
        dump("PlacesProjectManager.removeProject\n");
    },
  replaceProject: function(oldURL, project) {
        this.owner.projectsTreeView.replaceProject(oldURL, project);
    },
  setCurrentProject: function(project) {
        this.refresh();
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

this.terminate = function() {
    this.projectsTreeView.terminate();
};

// Methods for dealing with the projects tree context menu.

this._projectTestLabelMatcher = /^t:project\|(.+)\|(.+)$/;
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
    ko.projects.manager.closeProject(ko.projects.manager.currentProject);
};

this.saveProject = function() {
    ko.projects.manager.saveProject(ko.projects.manager.currentProject);
};

this.saveProjectAs = function() {
    ko.projects.saveProjectAs(ko.projects.manager.currentProject);
};

this.revertProject = function() {
    ko.projects.manager.revertProject(ko.projects.manager.currentProject);
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
    var title = _bundle.GetStringFromName("openProject.title");
    var defaultFilterName = _bundle.GetStringFromName("komodoProject.message");
    var filterNames = [_bundle.GetStringFromName("komodoProject.message"),
                       _bundle.GetStringFromName("all.message")];
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
    var item = ko.places.getItemWrapper(ko.projects.manager.currentProject.url, 'project');
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
    this._resetRows();
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

this.PlaceProjectsTreeView.prototype._resetRows = function() {
    this.rows = [];
};

this.PlaceProjectsTreeView.prototype.observe = function(subject, topic, data) {
    if (data == "mruProjectList") {
        this._resetRows();
    } else if (topic == "showProjectPath") {
        this._resetRows();
    }
};

this.PlaceProjectsTreeView.prototype.addProject = function(project) {
    var url = project.url
    var row = [url, ko.uriparse.baseName(url)];
    this.rows.push(row);
    this.tree.rowCountChanged(this.rows.length - 2, 1);
};

this.PlaceProjectsTreeView.prototype.removeProject = function(project) {
    var numToDelete;
    var listLen = this.rows.length;
    for (var i = listLen - 1; i >= 0; --i) {
        if (project.url == this.rows[i][0]) {
            var j = this.getNextSiblingIndex(i);
            if (j == -1) {
                numToDelete = listLen - i;
            } else {
                numToDelete = j - i;
            }
            this.rows.splice(i, numToDelete);
            this.tree.rowCountChanged(i, -1 * numToDelete);
            return;
        }
    }
    dump("PlaceProjectsTreeView.removeProject: Couldn't find "
         + project.name
         + " in the list of loaded projects\n");
};

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

// NSITreeView methods.
this.PlaceProjectsTreeView.prototype.getCellText = function(index, column) {
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
this.PlaceProjectsTreeView.prototype.getCellValue = function(index, column) {
    return this.rows[index][0];
};
this.PlaceProjectsTreeView.prototype.getImageSrc = function(index, column) {
    return 'chrome://komodo/skin/images/project_icon.png'
};
this.PlaceProjectsTreeView.prototype.getCellProperties = function(index, column, properties) {
    return; //@@@@ -- figure out which project is active.
    var row = this.rows[index];
    var currentProject = ko.projects.manager.currentProject;
    if (currentProject && currentProject.url == row[0]) {
        properties.AppendElement(this._atomService.getAtom("projectActive"));
    }
};

this.PlaceProjectsTreeView.prototype.getNextSiblingIndex = function(index) {
/**
 * @param index {int} points to the node whose next-sibling we want to find.
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
