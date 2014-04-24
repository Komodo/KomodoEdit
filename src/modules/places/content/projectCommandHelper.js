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

(function() {

var log = ko.logging.getLogger("projectCommandHelper_js");
//log.setLevel(ko.logging.LOG_DEBUG);

var placesBundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo-places/locale/places.properties");

this.ProjectCommandHelper = function(owner, manager) {
    this.owner = owner;   // Either the single-project or multiple-project view
    this.manager = manager;
};

this.ProjectCommandHelper.prototype.onProjectTreeDblClick = function(event, index) {
    if (event) {
        if (event.which != 1) {
            return;
        }
        var row = {};
        this.owner.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
        index = row.value;
    } else if (typeof(index) == "undefined") {
        log.error("dbl click: neither event nor index specified");
        return;
    } else {
        event = null;
    }
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
                        var oldRow = this.owner.projectsTreeView.getIndexByPart(currentProject);
                        ko.projects.manager.setCurrentProject(part);
                        if (oldRow != -1) {
                            this.owner.projectsTree.treeBoxObject.invalidateRow(oldRow);
                        }
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
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
};

this.ProjectCommandHelper.prototype.onTreeKeyPress = function(event, sender) {
    var t = event.originalTarget;
    if (t.localName != "treechildren" && t.localName != 'tree') {
        return false;
    }
    var retVal = null;
    // Special-case some commands, and then look at the keybinding set
    // to determine a command to do.
    var row, index, indices, i, item, items, o1, unopened_projects, other_items;
    try {
        if (!(event.shiftKey || event.ctrlKey || event.altKey)) {
            if (ko.places.viewMgr.arrowKeys.indexOf(event.keyCode) >= 0) {
                // Nothing to do but squelch the keycode
                retVal = false;
                throw new Error("");
            }
            if (event.keyCode == event.DOM_VK_RETURN) {
                o1 = {};
                this.owner.projectsTreeView.getSelectedItems(true, o1, {});
                items = o1.value;
                if (items.length == 0) {
                    retVal = false;
                    throw new Error("no items selected");
                } else if (items.every(function(part) part.type == "unopened_project")) {
                    if (items.length == 1) {
                        this.onProjectTreeDblClick(null,
                                                   this.owner.projectsTreeView.getIndexByPart(items[0]));
                        retVal = true;
                    } else {
                        ko.dialogs.alert(placesBundle.formatStringFromName("cant open X projects at the same time", [items.length], 1));
                        retVal = false;
                    }
                    
                } else if (items.every(function(part)
                                ~["project", "livefolder"].indexOf(part.type))) {
                    if (items.length == 1) {
                        this.onProjectTreeDblClick(null,
                                                   this.owner.projectsTreeView.getIndexByPart(items[0]));
                        retVal = true;
                    } else {
                        ko.dialogs.alert(placesBundle.formatStringFromName("cant go to X directories at the same time", [items.length], 1));
                        retVal = false;
                    }
                } else if (items.every(function(part)
                                       ~["file", "folder"].indexOf(part.type))) {
                    for (i = items.length - 1; i >= 0; --i) {
                        item = items[i];
                        this.onProjectTreeDblClick(null,
                                                   this.owner.projectsTreeView.getIndexByPart(item));
                    }
                    retVal = true;
                } else {
                    ko.dialogs.alert(placesBundle.GetStringFromName("Return action not defined on a mixture of projects etc"));
                    retVal = false;
                }
                throw new Error("");
            } else if (event.keyCode == event.DOM_VK_DELETE) {
                o1 = {};
                this.owner.projectsTreeView.getSelectedItems(true, o1, {});
                items = o1.value;
                if (items.some(function(part) part.type == "project")) {
                    ko.dialogs.alert(placesBundle.GetStringFromName("cant delete projects"));
                    retVal = false;
                } else {
                    unopened_projects = [];
                    other_items = [];
                    for (i = 0; item = items[i]; i++) {
                        if (item.type == "unopened_project") {
                            unopened_projects.push(item);
                        } else {
                            other_items.push(item);
                        }
                    }
                    for (var i = unopened_projects.length - 1; i >= 0; i--) {
                        item = unopened_projects[i];
                        ko.mru.deleteValue('mruProjectList', item.url, true/*notify */);
                        this.owner.projectsTreeView.removeProject(item);
                    }
                    ko.projects.removeItems(other_items, this.owner.projectsTreeView.selection.count);
                }
                retVal = true;
                throw new Error("");
            }
        }
        var command = ko.places.viewMgr._getCommandFromEvent(event);
        if (!command) {
            return false;
        }
        var newCommand = command;
        if (newCommand) {
            var controller = document.commandDispatcher.getControllerForCommand(newCommand);
            if (controller) {
                event.preventDefault();
                event.stopPropagation();
                controller.doCommand(newCommand);
                return true;
            }
        }
    } catch(ex) {
        if (ex.message != "") {
            log.error("Error: " + ex + "\n");
        }
        event.stopPropagation();
        event.preventDefault();
        if (retVal !== null) {
            return retVal;
        }
    }
    return false;
};

this.ProjectCommandHelper.prototype.doDragOver = function(event, sender) {
    return this._checkDrag(event);
};

this.ProjectCommandHelper.prototype.doDragEnter = function(event, sender) {
    return this._checkDrag(event);
};

this.ProjectCommandHelper.prototype._projectSuffices = ["kpf", "komodoproject"];
this.ProjectCommandHelper.prototype._isProject = function(uri) {
    var lastDot = uri.lastIndexOf(".");
    if (lastDot === -1) {
        return false;
    }
    return ~this._projectSuffices.indexOf(uri.substr(lastDot + 1));
};

this.ProjectCommandHelper.prototype.doDrop = function(event, sender) {
    try {
        var dt = event.dataTransfer;
        var copying, dropEffect, from_uris, source_uri;
        [from_uris, dropEffect] = ko.places.viewMgr._getDraggedURIs(event);
        if (from_uris.length == 0) {
            return false;
        } else if (!from_uris[0]) {
            return false;
        } else if (from_uris.length == 1 && this._isProject(from_uris[0])) {
            // Projects don't get dropped on containers; they get dropped
            // on the tree as a whole, so we don't test for targets
            ko.projects.open(from_uris[0]);
            event.stopPropagation();
            event.preventDefault();
            return false;
        } else if (dropEffect == "none") {
            return false;
        } else if (dropEffect == "link") {
            return false;
        }

        var index = this._currentRow(event);
        if (index == -1) {
            return false;
        }
        var treeview = this.owner.projectsTreeView;
        var target_part = treeview.getRowItem(index);
        if (!treeview.isContainer(index) || target_part.type == "livefolder") {
            //dump("Not dumping on a containerable\n");
            return false;
        }
        
        var newPart;
        for (var i = 0; i < from_uris.length; i++) {
            source_uri = from_uris[i];
            var fileObj = (Components.classes["@activestate.com/koFileService;1"].
                           getService(Components.interfaces.koIFileService).
                           getFileFromURI(source_uri));
            if (fileObj.isLocal) {
                if (fileObj.isDirectory) {
                    newPart = ko.projects.addPartWithURLAndType(source_uri, 'livefolder', target_part);
                } else if (fileObj.isFile) {
                    newPart = ko.projects.addFileWithURL(source_uri, target_part);
                } else {
                    log.debug("doDrop: Error: Can't add " + source_uri + "\n");
                    continue;
                }
            } else if (fileObj.isRemoteFile) {
                // Don't trust fileObj -- grab a remote connection and test it.
                var RFService = Components.classes["@activestate.com/koRemoteConnectionService;1"].getService();
                var conn = RFService.getConnectionUsingUri(source_uri);
                var rfInfo = conn.list(fileObj.path, 0);
                if (rfInfo.isDirectory()) {
                    newPart = ko.projects.addPartWithURLAndType(source_uri, 'livefolder', target_part);
                } else if (rfInfo.isFile()) {
                    newPart = ko.projects.addFileWithURL(source_uri, target_part);
                } else {
                    log.debug("doDrop: Error: Can't add " + source_uri + "\n");
                    continue;
                }
            }
            if (newPart) {
                this.owner.projectsTreeView.showChild(target_part, newPart);
            }
        }
        event.stopPropagation();
        event.preventDefault();
        return false;
    } catch(ex) {
        log.error("doDrop: " + ex);
    } finally {
        this.doEndDrag(event, sender);
    }
    return false;
};

this.ProjectCommandHelper.prototype.doEndDrag = function(event, sender) {
    this.complainIfNotAContainer = false;
};

this.ProjectCommandHelper.prototype._currentRow = function(event) {
    var row = {};
    this.owner.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    return row.value;
};

var isSameURI = function(u1, u2) {
    // The dangers of doing equality on URIs...
    if (u1 == u2) return true;
    return unescape(u1) == unescape(u2);
}

this.ProjectCommandHelper.prototype._checkDrag = function(event) {
    // Project files are droppable everywhere.
    var from_uris, dropEffect;
    var retVal = null;
    [from_uris, dropEffect] = ko.places.viewMgr._getDraggedURIs(event);
    var this_ = this;
    if (from_uris.length == 0) {
        return false;
    } else if (!from_uris[0]) {
        return false;
    } else if (from_uris.some(function(uri) this_._isProject(uri))) {
        if (from_uris.length !== 1
            || from_uris[0].indexOf("file:/") != 0) {
            // Don't support drag sources that contain a project file
            // and something else, and don't support remote project files.
            retVal = false;
        } else {
            // Don't support a drag of the current project
            var currentProject = ko.projects.manager.currentProject;
            retVal = !currentProject || !isSameURI(currentProject.url, from_uris[0]);
            //if (!retVal) {
            //    log.debug("  _checkDrag: don't allow current project\n");
            //}
        }
        event.preventDefault();
    }
    if (retVal === null) {
        var inDragSource = this._checkDragSource(event);
        var index = this._currentRow(event);
        var part = index == -1 ? null : this.owner.projectsTreeView.getRowItem(index);
        if (!inDragSource
            || !part
            || ["unopened_project", "file", "livefolder"].indexOf(part.type) !== -1) {
            retVal = false;
        } else {
            retVal = true;
            event.preventDefault();
        }
    }
    if (event.dataTransfer) {
        event.dataTransfer.dropEffect = event.dataTransfer.effectAllowed = retVal ? "copy" : "none";
    } else {
        log.debug("_checkDrag: no event.dataTransfer");
    }
    return retVal;
};

this.ProjectCommandHelper.prototype.dragDropFlavors = ["text/uri-list", "text/x-moz-url", "komodo/tab"];
this.ProjectCommandHelper.prototype._checkDragSource = function(event) {
    // All dragged items must be URIs for the drag source to be valid.
    var dt = event.dataTransfer;
    if (!dt) {
        log.info("_checkDragSource: No dataTransfer");
        return false;
    }
    for (var i = 0; i < dt.mozItemCount; i++) {
        if (!this.dragDropFlavors.some(function(flav) dt.mozTypesAt(i).contains(flav) )) {
            if (this.complainIfNotAContainer) {
                log.debug("not a file data-transfer\n");
                this.complainIfNotAContainer = false;
            }
            return false;
        }
    }
    return true;
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
    this.owner.projectsTree.treeBoxObject.invalidate();
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
this.ProjectCommandHelper.prototype.renameProject = function() {
    this._getProjectItemAndOperate("renameProject", ko.projects);
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
    var filename = ko.filepicker.browseForFile(defaultDirectory /* =null */,
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

this.ProjectCommandHelper.prototype.showInFinder_XXXX = function() {
    var items = this.manager.getSelectedItems();
    if (items.length != 1) {
        log.warn("Function showInFinder is intended for only one item");
        return;
    }
    var part = items[0];
    var path = ko.uriparse.displayPath(part.url);
    if (!path) {
        log.error("showInFinder: no path for url " + path.url);
        return;
    }
    if (part.type == "livefolder") {
        path = ko.uriparse.dirName(path);
    }
    var sysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
    getService(Components.interfaces.koISysUtils);
    sysUtilsSvc.ShowFileInFileManager(path);
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

this.ProjectCommandHelper.prototype.displayCurrentFullPath = function(event, sender) {
    var row = {};
    this.owner.projectsTree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    try {
        if (index < 0) throw new Error("index: " + index);
        var part = this.owner.projectsTreeView.getRowItem(index);
        if (part.type == "folder") {
            throw new Error();
        }
        var uri = part.url;
        if (!uri) throw new Error("No url at index: " + index);
        var label = sender.childNodes[0];
        if (!label) {
            throw new Error("No child at index: " + index);
        } else if (label.nodeName != "label") {
            throw new Error("Expected label child at index: " + index
                            + ", got " + label.nodeName);
        }
        var fileObj = (Components.classes["@activestate.com/koFileService;1"].
                       getService(Components.interfaces.koIFileService).
                       getFileFromURI(uri));
        var labelValue = fileObj.isLocal ? fileObj.path : uri;
        label.setAttribute("value", labelValue);
    } catch(ex) {
        if (ex.message) {
            log.debug("displayCurrentFullPath: " + ex + "\n");
        }
        event.preventDefault();
        event.stopPropagation();
        return !ex.message;
    }
    return true;
};

this.ProjectCommandHelper.prototype.injectHelperFunctions = function(receiver) {
    var this_ = this;
    for (var p in { onProjectTreeDblClick: 1,
                    onTreeKeyPress: 1,
                    openRemoteProject:1,
                    doDragOver:1,
                    doDragEnter:1,
                    doDrop:1,
                    doEndDrag:1,
                    showProjectInPlaces:1,
                    makeCurrentProject:1,
                    closeProject:1,
                    saveProject:1,
                    saveProjectAs:1,
                    renameProject:1,
                    revertProject:1,
                    openFiles:1,
                    refreshFileStatus:1,
                    compareFileWith:1,
                    rebaseFolder:1,
                    importPackage:1,
                    displayCurrentFullPath:1,
                    exportAsProjectFile:1,
                    exportPackage:1,
                editProjectProperties:1,
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
