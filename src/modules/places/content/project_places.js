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
  refresh: function(project) {
        this.owner.projectsTreeView.invalidate();
    },
  removeProject: function(project) {
        this.owner.projectsTreeView.removeProject(project);
        dump("PlacesProjectManager.removeProject\n");
    },
  replaceProject: function(oldURL, project) {
        dump("**************** Drop replaceProject\n");
        return;
        this.owner.projectsTreeView.replaceProject(oldURL, project);
    },
  setCurrentProject: function(project) {
        this.owner.projectsTreeView.currentProject = project;
        this.refresh();
    },

  // Methods for the projects context menu
  addNewFile: function(event, sender) {
        this.owner.projectsTreeView.doProjectContextMenu(event, sender, 'addNewFile');
        dump("****************addNewFile\n");
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
    var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var srcNodes = document.getElementById("placesSubpanelProjects_AddItemsMenu").childNodes;
    var attr, node, attributes;
    for (var i = 0; i < srcNodes.length; i++) {
        var srcNode = srcNodes[i];
        node = document.createElementNS(XUL_NS, srcNode.nodeName);
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
    var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
    var srcNodes = document.getElementById("placesSubpanelProjects_AddItemsMenu").childNodes;
    var target_tree = document.getElementById("menu_projCtxt_addMenu_Popup");
    var target_toolbar = document.getElementById("projectView_AddItemPopup");
    var attr, node, nodetb, attributes;
    dump(">> finishProjectsContextMenu, copy "
         + srcNodes.length
         + " nodes\n");
    for (var i = 0; i < srcNodes.length; i++) {
        var srcNode = srcNodes[i];
        node = document.createElementNS(XUL_NS, srcNode.nodeName);
        nodetb = document.createElementNS(XUL_NS, srcNode.nodeName);
        attributes = srcNode.attributes;
        dump("node " + i + " has " + attributes.length + " attrs\n");
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
    dump("# nodes added to menu_projCtxt_addMenu_Popup: \n");
    dump("  " + target_tree.childNodes.length + "\n");
    dump("# nodes added to projectView_AddItemPopup: \n");
    dump("  " + target_toolbar.childNodes.length + "\n");
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
    dump(">> initProjectsContextMenu, target:"
         + event.target.id
         + "\n");
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
    var selectedIndices = ko.treeutils.getSelectedIndices(this.projectsTreeView,
                                                          false /*rootsOnly*/);
    var selectedUrl = index >= 0 ? this.projectsTreeView.getCellValue(index, {id:'uri'}) : null;
    var isRootNode = index == -1;
    var itemTypes;
    if (isRootNode) {
        itemTypes = ['root'];
    } else {
        //XXXX: Fixz this once we have the tree working again.
        itemTypes = [ 'project' || this.projectsTreeView.getItem(index).type ];
    }
    var currentProject = ko.projects.manager.currentProject;
    var projectIsOpen = false;
    var windows = ko.windowManager.getWindows();
    for (var win, i = 0; win = windows[i]; i++) {
        var otherProject = win.ko.projects.manager.currentProject;
        if (otherProject && otherProject.url == selectedUrl) {
            projectIsOpen = true;
            break;
        }
    }
    this._selectionInfo = {
      currentProject: (currentProject
                       && currentProject.url == selectedUrl),
      index: index,
      itemTypes: itemTypes,
      multipleNodesSelected: selectedIndices.length > 1,
      projectIsOpen: projectIsOpen,
      __END__:null
    };
    this._selectionInfo.projectIsDirty =
            this._selectionInfo.currentProject && currentProject.isDirty;
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
    }
    menuNode.removeAttribute('collapsed');
    var disableNode = false;
    if (ko.places.matchAnyType(menuNode.getAttribute('disableIf'), itemTypes)) {
        disableNode = true;
    } else if (!ko.places.matchAllTypes(menuNode.getAttribute('disableUnless'), itemTypes)) {
        disableNode = true;
    }
    if (disableNode) {
        menuNode.setAttribute('disabled', true);
    } else {
        menuNode.removeAttribute('disabled');
    }
    var childNodes = menuNode.childNodes;
    for (var i = childNodes.length - 1; i >= 0; --i) {
        this._processProjectsMenu_TopLevel(childNodes[i]);
    }
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

this.PlaceProjectsTreeView.prototype.getSelectedIndex = function() {
    return this.selection.currentIndex;
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
