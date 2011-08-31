// Copyright (c) 2000-2011 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

// Provide an object that helps both project views to fire commands.


if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('places' in ko)) {
    ko.places = {};
}
if (!('projects' in ko.places)) {
    ko.places.projects = {};
}

dump(">> projectCommandHelper.js...\n");
(function() {

var log = ko.logging.getLogger("projectCommandHelper_js");
log.setLevel(ko.logging.LOG_DEBUG);

this.ProjectCommandHelper = function(owner, manager) {
    this.owner = owner;   // Either the single-project or multiple-project view
    this.manager = manager;
};

this.ProjectCommandHelper.prototype.onProjectTreeDblClick = function(event) {
    if (event.which != 1) {
        return;
    }
    var row = {};
    this.owner.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    if (index != -1) {
        var part = this.owner.projectsTreeView.getRowItem(index);
        if (!part) {
            log.error("onProjectTreeDblClick(" + index + ") => null\n");
        } else {
            var uri = part.url;
            var koFile;
            switch (part.type) {
                case "unopened_project":
                    // Can't happen in MPV projects, so invoke the SPV
                    // project object's method.
                    ko.places.projects_SPV.openProjectInCurrentWindow();
                    break;
                    
                case "project":
                    var currentProject = ko.projects.manager.currentProject;
                    if (!currentProject || currentProject.id != part.id) {
                        ko.projects.manager.setCurrentProject(part);
                    }
                    this.owner.showProjectInPlaces(part);
                    break;

                case "livefolder":
                    koFile = part.getFile();
                    if (koFile.isLocal) {
                        ko.places.manager.openDirectory(koFile.path);
                    } else {
                        ko.places.manager.openNamedRemoteDirectory(uri);
                    }
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

this.ProjectCommandHelper.prototype._getProjectItemAndOperate = function(context, obj, callback) {
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

this.ProjectCommandHelper.prototype.closeProject = function() {
    this._getProjectItemAndOperate("closeProject", ko.projects.manager);
};

this.ProjectCommandHelper.prototype.compareFileWith = function() {
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

this.ProjectCommandHelper.prototype.rebaseFolder = function() {
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

this.ProjectCommandHelper.prototype.exportAsProjectFile = function() {
    var items = this.manager.getSelectedItems();
    if (items.length != 1 || !items[0] || items[0].type != "folder") {
        log.warn("Function exportAsProjectFile is intended only for groups");
        return;
    }
    ko.projects.exportItems(items);
};
this.ProjectCommandHelper.prototype.exportPackage = function() {
    var items = this.manager.getSelectedItems();
    var validTypes = ["folder", "project"];
    if (items.filter(function(item) validTypes.indexOf(item.type) == -1).length) {
        log.warn("Function exportPackage is intended only for "
                 + validTypes);
        return;
    }
    ko.projects.exportPackageItems(items);
};
this.ProjectCommandHelper.prototype.createProjectTemplate = function() {
    this._getProjectItemAndOperate("createProjectTemplate",
                                   ko.projects.manager, "saveProjectAsTemplate");
};
this.ProjectCommandHelper.prototype.importPackage = function() {
    var item = this.manager.getSelectedItem();
    if (!item || item.type != "folder") {
        log.warn("Function importPackage is intended only for groups");
        return;
    }
    ko.projects.importFromPackage(this.manager, item);
};
this.ProjectCommandHelper.prototype._continueMakeCurrentProject = function(project) {
    ko.projects.manager.setCurrentProject(project);
    this.owner.projectsTreeView.invalidate();
}
this.ProjectCommandHelper.prototype.makeCurrentProject = function() {
    this._getProjectItemAndOperate("makeCurrentProject", this,
                                   "_continueMakeCurrentProject");
};
this.ProjectCommandHelper.prototype.openFiles = function() {
    var items = this.manager.getSelectedItems();
    if (items.filter(function(item) item.type != "file").length) {
        log.warn("Function openFiles is intended only for files");
        return;
    }
    ko.open.multipleURIs(items.map(function(item) item.url));
};
this.ProjectCommandHelper.prototype.refreshFileStatus = function() {
    var items = this.manager.getSelectedItems();
    if (!items || items.length == 0) {
        return;
    }
    var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].getService(Components.interfaces.koIFileStatusService);
    fileStatusSvc.updateStatusForUris(items.length,
                                      items.map(function(item) item.url),
                                      true /* forcerefresh */);
};
this.ProjectCommandHelper.prototype.revertProject = function() {
    this._getProjectItemAndOperate("revertProject", ko.projects.manager);
};

this.ProjectCommandHelper.prototype.saveProject = function() {
    this._getProjectItemAndOperate("saveProject", ko.projects.manager);
};

this.ProjectCommandHelper.prototype.saveProjectAs = function() {
    this._getProjectItemAndOperate("saveProjectAs", ko.projects);
};

this.ProjectCommandHelper.prototype.showProjectInPlaces = function() {
    this._getProjectItemAndOperate("showProjectInPlaces",
                                   ko.places.manager, "moveToProjectDir");
};

this.ProjectCommandHelper.prototype.openProjectInNewWindow = function() {
    this._openProject(true);
};

this.ProjectCommandHelper.prototype.openProjectInCurrentWindow = function() {
    this._openProject(false);
}

this.ProjectCommandHelper.prototype._openProject = function(inNewWindow) {
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

this.ProjectCommandHelper.prototype.editProjectProperties = function() {
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

this.ProjectCommandHelper.prototype.injectSpecificFunctions = function(receiver, functionList) {
    var this_ = this;
    for (var p in functionList) {
        // Force a closure so the this_[name] is rebound each time.
        (function(currName) {
            receiver[currName] = function() {
                return this_[currName].apply(this_, arguments);
            };
        })(p);
    }
};

this.ProjectCommandHelper.prototype.injectHelperFunctions = function(receiver) {
    var this_ = this;
    for (var p in { onProjectTreeDblClick: 1,
                    openRemoteProject:1,
                    showProjectInPlaces:1,
                    makeCurrentProject:1,
                    closeProject:1,
                    saveProject:1,
                    saveProjectAs:1,
                    revertProject:1,
                    openFiles:1,
                    refreshFileStatus:1,
                    compareFileWith:1,
                    rebaseFolder:1,
                    importPackage:1,
                    exportAsProjectFile:1,
                    exportPackage:1,
                createProjectTemplate:1}) {
        // Force a closure (see above)
        (function(currName) {
            receiver[currName] = function() {
                return this_[currName].apply(this_, arguments);
            };
        })(p);
    }
};

}).apply(ko.places.projects);
dump("<< projectCommandHelper.js: done defining ko.places.projects.ProjectCommandHelper = "
     + typeof(ko.places.projects.ProjectCommandHelper)
     + "\n");
