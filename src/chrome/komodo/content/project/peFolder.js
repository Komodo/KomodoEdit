/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

var log = ko.logging.getLogger('peFolder');

function peFolder() {
    this.name = 'peFolder';
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peFolder.prototype.constructor = peFolder;

peFolder.prototype.init = function() {
}

peFolder.prototype.registerCommands = function() {
    var em = ko.projects.extensionManager;
    em.registerCommand('cmd_delete', this);
    em.registerCommand('cmd_importFromFS', this);
    em.registerCommand('cmd_reimportFromFS', this);
    em.registerCommand("cmd_importFromPackage",this);
    em.registerCommand("cmd_renameFolderPart",this);
}

peFolder.prototype.registerMenus = function() {
    var em = ko.projects.extensionManager;
    em.createMenuItem(Components.interfaces.koIPart_folder,'Import from File System...','cmd_importFromFS');
    em.createMenuItem(Components.interfaces.koIPart_folder,'Re-import','cmd_reimportFromFS');
    em.createMenuItem(Components.interfaces.koIPart_folder,'Import Package...','cmd_importFromPackage');
    em.createMenuItem(Components.interfaces.koIPart_folder,'Refresh Status','cmd_refreshStatus');
    em.createMenuItem(Components.interfaces.koIPart_folder,'Rename...','cmd_renameFolderPart');
    var menupopup = document.getElementById('folder_context');
    em.addMenuItem(Components.interfaces.koIPart_folder, menupopup);
}

peFolder.prototype.registerEventHandlers = function() {
}

peFolder.prototype.supportsCommand = function(command, item) {
try {
    //dump('for ' + command + '\n');
    if (!ko.projects.active) return false;
    var items = ko.projects.active.getSelectedItems();
    var havemultiple = items.length > 1;
    //dump('for ' + command + ', items.length == ' + items.length + '\n');
    switch (command) {
    case 'cmd_delete':
        //HACK: Current behaviour for read-only toolbox's (typically the
        //      Shared Toolbox is to allow modifications and deal with the
        //      "can't save it" issues on save. Because adds and edits are
        //      allowed, it doesn't make sense to disallow delete. So we
        //      won't for now.
        //return ko.projects.active.manager.writeable();
        return true;
    case "cmd_importFromPackage":
    case "cmd_importFromFS":
    case "cmd_reimportFromFS":
        return items.length == 1 && !items[0].live;
    case "cmd_renameFolderPart":
        return items.length == 1 && !items[0].live && items[0].type == "folder";
    default:
        break;
    }
} catch (e) {
    log.exception(e);
}
    return false;
}

peFolder.prototype.isCommandEnabled = function(command, item) {
try {
    //dump('for ' + command + '\n');
    var items = null;

    if (ko.projects.active) {
        items = ko.projects.active.getSelectedItems();
        var havemultiple = items.length > 1;
    }
    switch (command) {
        case 'cmd_delete':
            // Delete is enabled for any part selection that isn't a project.
            if (ko.projects.getFocusedProjectView()) {
                if (!ko.projects.active.manager.writeable()) return false;
                item = ko.projects.active.getSelectedItem();
                if (!item) return false;
            }
            // leave cmd_delete enabled for any other element
            return true;
        case "cmd_importFromPackage":
        case "cmd_importFromFS":
            return items.length == 1 && !items[0].live;
        case "cmd_reimportFromFS":
            return items.length == 1 && !items[0].live &&
                   items[0].prefset.hasPrefHere("import_dirname");
        case "cmd_renameFolderPart":
            return items.length == 1 && !items[0].live && items[0].type == "folder";
        default:
            break;
    }
} catch (e) {
    log.exception(e);
}
    return false;
}

peFolder.prototype.doCommand = function(command) {
    var item = null;
    var firstchild, i;
    switch (command) {
    case 'cmd_addFilePart_Project':
        // XXX FIXME  nothing uses this???
        ko.projects.manager.viewMgr.focus();
        item = ko.projects.manager.getCurrentProject();
        // fall through
    case 'cmd_addFilePart':
        // XXX FIXME  nothing uses this???
        if (!item) item = ko.projects.active.getSelectedItem();
        ko.projects.addFile(item);
        break;
    case 'cmd_addNewFile':
    case 'cmd_addNewFileFromTemplate':
        if (!item) item = ko.projects.active.getSelectedItem();
        ko.projects.addNewFileFromTemplate(item);
        break;
    case 'cmd_addRemoteFilePart_Project':
        // XXX FIXME  nothing uses this???
        ko.projects.manager.viewMgr.focus();
        item = ko.projects.manager.getCurrentProject();
        // fall through
    case 'cmd_addRemoteFilePart':
        if (!item) item = ko.projects.active.getSelectedItem();
        ko.projects.addRemoteFile(item);
        break;
    case 'cmd_addFolderPart_Project':
        // XXX FIXME  nothing uses this???
        ko.projects.manager.viewMgr.focus();
        item = ko.projects.manager.getCurrentProject();
        // fall through
    case 'cmd_addFolderPart':
        if (!item) item = ko.projects.active.getSelectedItem();
        var fitem = new Object();
        fitem.name = 'New Folder';
        fitem.value = null;
        if (ko.projects.active.manager.renameItem(fitem)) {
            this.addFolder(fitem.name, item);
        }
        break;
    case 'cmd_renameFolderPart':
        if (!item) item = ko.projects.active.getSelectedItem();
        if (item) {
            ko.projects.active.manager.renameItem(item)
            ko.projects.active.view.refresh(item);
        }
        break;
    case 'cmd_delete':
        // this cmd_delete handler only implements for our part viewers
        if (!ko.projects.getFocusedProjectView()) return;
        var items = ko.projects.active.getSelectedItems();
        if (items.length < 1) return;
        var havemultiple = (items.length > 1);
        var question = null;

        var removeText;
        if (ko.projects.active.manager.name == "projectManager") {
            removeText = "Remove from Project";
        } else {
            removeText = "Remove from Toolbox";
        }
        var haveLive = false;
        if (havemultiple) {
            question = "Do you want to remove the " + items.length +
                           " items you have selected?";
            for (i=0; i < items.length; i++) {
                var file = items[i].getFile();
                if (file && file.isLocal) {
                    haveLive = true;
                    break;
                }
            }
        } else {
            if (items[0].type == "project") break;
            question = "Do you want to remove the item you have selected?";
            var file = items[0].getFile();
            haveLive = file && file.isLocal;
        }
        var buttons;
        var text = null;
        if (haveLive) {
            buttons = ["Move to Trash", removeText, "Cancel"];
            text = "You may delete the files on disk, or simply remove the selected "+
                    "items from the project or toolbox.  If you choose only to remove "+
                    "the items and they are in a live folder, they will reappear later.";
        } else {
            buttons = [removeText, "Cancel"];
        }
        var action = ko.dialogs.customButtons(question, buttons, "Cancel", text,
                                        "Delete Selected Items",
                                        null, "warning-icon spaced")
        if (action == "Cancel")
            return;

        ko.projects.active.manager.removeItems(items, action == "Move to Trash");
        break;
    case "cmd_importFromFS":
        item = ko.projects.active.getSelectedItem();
        if (!item) return;
        ko.projects.importFromFileSystem(item);
        ko.projects.active.view.refresh(item);
        ko.projects.active.view.selectPart(item);
        break;
    case "cmd_reimportFromFS":
        item = ko.projects.active.getSelectedItem();
        if (!item) return;
        ko.projects.reimportFromFileSystem(item);
        ko.projects.active.view.refresh(item);
        ko.projects.active.view.selectPart(item);
        break;
    case "cmd_importFromPackage":
        item = ko.projects.active.getSelectedItem();
        if (!item) return;
        ko.projects.importFromPackage(item);
        ko.projects.active.view.refresh(item);
        ko.projects.active.view.selectPart(item);
        break;
    default:
        break;
    }
}

// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peFolder());


this.getDefaultDirectory = function peFolder_getDefaultDirectory(/*koIPart*/ parent)
{
    if (parent) {
        var f = parent.getFile();
        while (!f) {
            parent = parent.parent;
            f = parent.getFile();
        }
        if (f) {
            if (f.isDirectory)
                return f.path;
            return f.dirName;
        }
    }
    return null;
}


this.addNewPart = function peFolder_add(type, partviewerId)
{
    try {
        var target, item, items, dirname, partviewer;
        if (!partviewerId) {
            target = ko.projects.active.getSelectedItem();
        } else {
            partviewer = document.getElementById(partviewerId);
            ko.uilayout.ensureTabShown(partviewer.getAttribute('tabid'));
            partviewer.focus()
            target = partviewer.manager.getCurrentProject();
            ko.projects.active = partviewer;
        }

        // type can be:
        //   'files': add existing files
        switch (type) {
            case 'files':
                ko.projects.addFile(target);
                break;
            case 'snippet':
                ko.projects.addSnippet(target);
                break;
            case 'command':
                ko.projects.addCommand(target);
                break;
            case 'menu':
                ko.projects.addMenu(target);
                break;
            case 'toolbar':
                ko.projects.addToolbar(target);
                break;
            case 'URL':
                ko.projects.addURL(target);
                break;
            case 'macro':
                ko.projects.addMacro(target);
                break;
            case 'remotefiles':
                ko.projects.addRemoteFile(target);
                break;
            case 'template':
                ko.projects.addTemplate(target);
                break;
            case 'directoryshortcut':
                dirname = ko.filepicker.getFolder();
                if (!dirname) return;
                ko.projects.addDirectoryShortcut(dirname, target);
                break;
            case 'newfile':
                ko.projects.addNewFileFromTemplate(target);
                break;
            case 'newfolder':
                var name = ko.dialogs.prompt("Enter folder name:");
                if (!name) return;
                ko.projects.addFolder(name, target);
                break;
            case 'livefolder':
                dirname = ko.filepicker.getFolder();
                if (!dirname) return;
                ko.projects.addLiveFolder(dirname, target);
                break;
            default:
                log.error("Unknown item type called to ko.projects.add: " + type);
        }
    } catch (e) {
        log.error(e);
    }
}

this.ensureAddMenu = function peFolder_ensureFolderAdd(popup) {
    if (popup.childNodes.length > 0) return;
    // clone the folder context menu to create a new menu
    var menupopup = document.getElementById('folder_context_popup');
    for (var i =0; i < menupopup.childNodes.length; i++) {
        popup.appendChild(menupopup.childNodes[i].cloneNode(1));
    }
}

this.addNewFileFromTemplate = function peFolder_addNewFileFromTemplate(/*koIPart*/ parent)
{
    var defaultDirectory = ko.projects.getDefaultDirectory(parent);
    return ko.views.manager.newTemplate(defaultDirectory, parent.project);
}
    
this.addFileWithURL = function peFolder_addFileWithURL(url, /*koIPart*/ parent)
{
    if (typeof(parent)=='undefined' || !parent)
        parent = ko.projects.active.getSelectedItem();
    var part = parent.project.createPartFromType('file');
    part.setStringAttribute('url', url);
    part.setStringAttribute('name', ko.uriparse.baseName(url));
    ko.projects.addItem(part,parent);
}

this.addFile = function peFolder_addFile(parent_item)
{
    //XXX todo: Support other resources

    var defaultDir = null;
    if (parent_item && parent_item.url) {
        defaultDir = ko.uriparse.URIToLocalPath(parent_item.url);
    }
    var files = ko.filepicker.openFiles(defaultDir, // default dir
                                     null, // default filename
                                     "Add Files to Project"); // title
    if (files == null) {
        return false;
    } else {
        var url;
        for (var i = 0; i < files.length; ++i) {
            url = ko.uriparse.localPathToURI(files[i]);
            ko.projects.addFileWithURL(url, parent_item);
        }
        return true;
    }
}

this.addRemoteFile = function peFolder_addRemoteFile(item)
{
    var result = ko.filepicker.remoteFileBrowser(); // in fileops.js
    if (result && result.filepaths.length > 0) {
        //dump("ko.projects.addRemoteFile result.filepaths: " + result.filepaths+ "\n");
        for (var i = 0; i < result.filepaths.length; i++) {
            ko.projects.addFileWithURL(result.filepaths[i], item);
        }
        return true;
    }
    return false;
}

this.addFolder = function peFolder_addFolder(name, /*koIPart*/ parent)
{
    var folder = parent.project.createPartFromType('folder');
    folder.name = name;
    ko.projects.addItem(folder,parent);
}

this.addLiveFolder = function peFolder_addLiveFolder(dirname, /*koIPart*/ parent)
{
    var folder = parent.project.createPartFromType('livefolder');
    folder.url = dirname;
    ko.projects.addItem(folder,parent);
}

}).apply(ko.projects);

// backwards compat api
var peFolder_getDefaultDirectory = ko.projects.getDefaultDirectory;
var peFolder_add = ko.projects.addNewPart;
var peFolder_ensureFolderAdd = ko.projects.ensureAddMenu;
var peFolder_addNewFileFromTemplate = ko.projects.addNewFileFromTemplate;
var peFolder_addFileWithURL  = ko.projects.addFileWithURL;
var peFolder_addFile = ko.projects.addFile;
var peFolder_addRemoteFile = ko.projects.addRemoteFile;
var peFolder_addFolder = ko.projects.addFolder;
var peFolder_addLiveFolder = ko.projects.addLiveFolder;
