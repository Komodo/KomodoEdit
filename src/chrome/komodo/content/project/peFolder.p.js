/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

var log = ko.logging.getLogger('peFolder');
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFolder.properties");

this.addFileWithURL = function peFolder_addFileWithURL(url, /*koIPart*/ parent)
{
    return this.addPartWithURLAndType(url, 'file', parent);
}

this.addPartWithURLAndType = function(url, typename, parent) {
    if (typeof(parent)=='undefined' || !parent)
        parent = ko.projects.active.getSelectedItem();
    var part = parent.getChildByAttributeValue('url', url, false);
    if (part) {
        //dump("Found file " + part.url + " in parent " + parent.name + "\n");
        return part;
    }
    var part = parent.project.createPartFromType(typename);
    part.setStringAttribute('url', url);
    part.setStringAttribute('name', ko.uriparse.baseName(url));
    ko.projects.manager.addItem(part, parent);
    return part;
}

this._getDirFromPart = function(part) {
    log.deprecated("_getDirFromPart: Nothing in core Komodo calls this code, and it shouldn't be used");
    var defaultDir = null;
    try {
        // project => dirName
        // anything else: fall back to dirName, since paths
        // might not be directories.
        switch (part.type) {
        case "file":
        case "project":
            defaultDir = part.getFile().dirName;
            break;
        case "livefolder":
            defaultDir = part.getFile().path;
            break;
        default:
            // For folders and things, start at the project's home dir
            defaultDir = part.project.getFile().dirName;
        }
    } catch(ex) {
        log.exception(ex, "addFiles to project failed");
    }
    if (!defaultDir) {
        log.error("No default dir for part(" + part + ")");
        defaultDir = ko.projects.manager.getSelectedProject().getFile().dirName;
    }
    return defaultDir;
};

this.addNewFileFromTemplate = function peFolder_addNewFileFromTemplate(/*koIPart*/ parent, callback)
{
    var this_ = this;
    var view_callback = function(view) {
        if (view) {
            var part;
            try {
                part = this_.addPartWithURLAndType(view.koDoc.file.URI, 'file', parent);
            } catch(ex) {
                part = null;
            }
            if (callback) {
                callback(part);
            }
        }
    };
    var targetDir = null;
    if (parent.type == "folder") {
        var children = {};
        parent.getChildrenByType('livefolder', true, children, {});
        children = children.value;
        if (children.length) {
            targetDir = children[0].getFile().path;
        } else {
            children = {};
            parent.getChildrenByType('file', true, children, {});
            children = children.value;
            if (children.length) {
                targetDir = children[0].getFile().dirName;
            }
        }
    }
    if (!targetDir) {
        targetDir = parent.project.getFile().dirName;
    }
    ko.views.manager.newTemplateAsync(targetDir, view_callback);
}
    
this.addFile = function peFolder_addFile(parent_item)
{
    //XXX todo: Support other resources

    var defaultDir = parent_item.project.getFile().dirName;
    var files = ko.filepicker.browseForFiles(defaultDir, // default dir
                                             null, // default filename
                                             _bundle.GetStringFromName("addFilesToProject")); // title
    if (files == null) {
        return [];
    } else {
        var part, parts = [], url;
        for (var i = 0; i < files.length; ++i) {
            url = ko.uriparse.localPathToURI(files[i]);
            part = ko.projects.addFileWithURL(url, parent_item);
            if (part) {
                parts.push(part);
            }
        }
        return parts;
    }
}

this.addRemoteFile = function peFolder_addRemoteFile(item)
{
    var result = ko.filepicker.remoteFileBrowser(); // in fileops.js
    var parts = [];
    if (!result) {
        return parts;
    }
    var filepaths = result.filepaths;
    if (!filepaths) {
        return parts;
    }
    //dump("ko.projects.addRemoteFile result.filepaths: " + result.filepaths+ "\n");
    for (var i = 0; i < filepaths.length; i++) {
        var part = ko.projects.addFileWithURL(filepaths[i], item);
        if (part) {
            parts.push(part);
        }
    }
    return parts;
}

this.addRemoteFolder = function peFolder_addRemoteFolder(item)
{
    var url, obj = {value:null};
    ko.filepicker.browseForRemoteDir(obj);
    if (!obj.value) {
        return null;
    }
    //dump("ko.projects.addRemoteFolder result: " + obj.value + "\n");
    var part = ko.projects.addPartWithURLAndType(obj.value, 'livefolder', item);
    return part;
}

this.addGroup = function peFolder_addGroup(/*koIPart*/ parent)
{
    var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFolderName"));
    if (!name) {
        return null;
    }
    // Check to see if it exists.
    var part = parent.getChildWithTypeAndStringAttribute('folder',
                                                         'name', name,
                                                         false);
    if (part) {
        //dump("Found child " + name + " in the tree already\n");
        return part;
    }
    var part = parent.project.createPartFromType('folder');
    part.setStringAttribute('name', name);
    ko.projects.manager.addItem(part, parent);
    return part;
}

this.removeItems = function peFolder_removeItems(/*array of koIPart*/ items) {
    if (items.length < 1) return;
    var prompt;
    var title = _bundle.GetStringFromName("removeFromProject");
    if (items.length > 1) {
        prompt = _bundle.formatStringFromName("doYouWantToRemoveThe", [items.length], 1);
    } else {
        if (items[0].type == "project") return;
        prompt = _bundle.GetStringFromName("doYouWantToRemoveTheItemYouHaveSelected");
    }
    var response = "No";
    var text = null;
    var res = ko.dialogs.yesNoCancel(prompt, response, text, title);
    if (res == "Yes") {
        ko.projects.active.manager.removeItems(items, false);
    }
};

}).apply(ko.projects);
