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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}
if (typeof(ko.fileutils)=='undefined') {
    ko.fileutils = {};
}

(function() {

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFile.properties");

function peFile() {
    this.name = 'peFile';
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peFile.prototype.constructor = peFile;

peFile.prototype.init = function() {
    // register our command handlers
    ko.projects.extensionManager.setDatapoint(_bundle.GetStringFromName("dateTreeColLabel"),'lastModifiedTime');
    ko.projects.extensionManager.setDatapoint(_bundle.GetStringFromName("filesizeTreeColLabel"),'fileSize');
    this._clipboard = [];
}

peFile.prototype.registerCommands = function() {
    var em = ko.projects.extensionManager;
    em.registerCommand('cmd_openInDir', this);
    em.registerCommand('cmd_dumpPartProperties', this);
    em.registerCommand('cmd_openFilePart', this);
    em.registerCommand('cmd_refreshStatus', this);
    em.registerCommand('cmd_editProperties', this);
    em.registerCommand('cmd_showUnsavedChanges', this);
    em.registerCommand('cmd_compareFiles', this);
    em.registerCommand('cmd_compareFileWith', this);
    em.registerCommand("cmd_exportItems",this);
    em.registerCommand("cmd_exportToPackage",this);
    em.registerCommand("cmd_cut",this);
    em.registerCommand("cmd_copy",this);
    em.registerCommand("cmd_paste",this);
    em.registerCommand("cmd_findInPart",this);
    em.registerCommand("cmd_replaceInPart",this);
    em.registerCommand("cmd_showInFinder",this);
    em.registerCommand("cmd_renameFile",this);
}

peFile.prototype.registerEventHandlers = function() {
    ko.projects.extensionManager.addEventHandler(Components.interfaces.koIPart_file,'ondblclick',this);
    // we don't add a dblclick handler for Components.interfaces.koIPart_ProjectRef, since
    // it inherits from koIPart_file
}

peFile.prototype.registerMenus = function() {
    var em = ko.projects.extensionManager;
    em.createMenuItem(Components.interfaces.koIPart_file,
                                    _bundle.GetStringFromName("openFile"),
                                    'cmd_openFilePart',
                                    null,
                                    null,
                                    true);
    em.createMenuItem(Components.interfaces.koIPart_file,
                                    _bundle.GetStringFromName("refreshStatus"),
                                    'cmd_refreshStatus');
    em.createMenuItem(Components.interfaces.koIPart_file,
                                    _bundle.GetStringFromName("showUnsavedChanges"),
                                    'cmd_showUnsavedChanges');
    em.createMenuItem(Components.interfaces.koIPart_file,
                                    _bundle.GetStringFromName("compareFiles"),
                                    'cmd_compareFiles');
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("find"),
                                    'cmd_findInPart');
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("replace"),
                                    'cmd_replaceInPart');
// #if PLATFORM == "win"
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("showInExplorer"),
                                    'cmd_showInFinder');
// #elif PLATFORM == "darwin"
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("showInFinder"),
                                    'cmd_showInFinder');
// #else
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("showInFileManager"),
                                    'cmd_showInFinder');
// #endif
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("rename"),
                                    'cmd_renameFile');
    em.createMenuItem(Components.interfaces.koIPart_file,
                                    _bundle.GetStringFromName("compareFileWith"),
                                    'cmd_compareFileWith');
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("exportAsProjectFile"),
                                    'cmd_exportItems');
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("exportPackage"),
                                    'cmd_exportToPackage');

    // XXX debug info
    em.createMenuItem(Components.interfaces.koIPart,
                                    _bundle.GetStringFromName("dump"),
                                    'cmd_dumpPartProperties');
}

peFile.prototype.supportsCommand = function(command, item) {
    var items = null;
    var file = null;
    if (ko.projects.active) {
        items = ko.projects.active.getSelectedItems();
    }
    switch (command) {
    case 'cmd_cut':
    case 'cmd_copy':
        if (!items || items.length == 0) return false;
        if (command == 'cmd_cut' && !ko.projects.active.manager.writeable()) return false;
        // We want to make sure that no projects are selected
        var notlive = command == 'cmd_cut';
        for (var i = 0; i < items.length; i++) {
            if ((notlive && items[i].live) || items[i].type == 'project') {
                return false;
            }
        }
        return true;
    case 'cmd_paste':
        // XXX we might not want to allow files to be pasted into a live folder
        //if (!items || items.length == 0) return false;
        //for (var i = 0; i < items.length; i++) {
        //    if (items[i].live) {
        //        return false;
        //    }
        //}
        return 1; // see http://bugs.activestate.com/show_bug.cgi?id=27527

    case 'cmd_dumpPartProperties':
        // Only return true in developer builds
        var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                  getService(Components.interfaces.koIInfoService);
        return infoSvc.buildFlavour == "dev";
    case 'cmd_openFilePart':
        for (i = 0; i < items.length; i++) {
            if (items[i].type == 'file') return true;
        }
        return false;
    case 'cmd_findInPart':
    case 'cmd_replaceInPart':
        for (i = 0; i < items.length; i++) {
            var type = items[i].type;
            if (type == 'file' && items[i].getFile().isLocal) {
                return true;
            } else if (type == 'project' || type == 'livefolder'
                       || type == 'folder') {
                return true;
            }
        }
        return false;
    case 'cmd_showInFinder':
        if (items.length != 1) return false;
        file = items[0].getFile();
        return (items.length == 1 && file && file.isLocal);
    case 'cmd_renameFile':
        if (items.length != 1) return false;
        file = items[0].getFile();
        return (items.length == 1 && items[0].type != 'project' && file && file.isLocal);
    case 'cmd_refreshStatus':
        // if a toolbox has focus, get the currently selected item and refresh it
        // otherwise, always refresh the currentView if there is one.
        if (ko.projects.getFocusedProjectView()) {
            item = ko.projects.active.getSelectedItem();
            // item must be a file
            if (item && item.url) return true;
        }
        return ko.views.manager.currentView != null;
        break;
    case 'cmd_editProperties':
        if (!items || items.length < 1) return false;
        var type;
        for (i = 0; i < items.length; i++) {
            type = items[i].type;
            switch (type) {
                case 'file':
                case 'folder':
                case 'livefolder':
                case 'project':
                    continue;
                default:
                    //dump('returning false because type is not correct\n');
                    return false;
            }
        }
        return true;
    case 'cmd_showUnsavedChanges':
        var view = ko.views.manager.currentView;
        return (view && view.koDoc && view.koDoc.isDirty &&
                !view.koDoc.isUntitled);
    case 'cmd_compareFiles':
        return (items.length == 2 && items[0].type == 'file' && items[1].type == 'file');
    case 'cmd_compareFileWith':
        return (items && items.length == 1 && items[0].type == 'file');
    case 'cmd_exportItems':
        // the following isn't great, but it deals with
        // http://bugs.activestate.com/show_bug.cgi?id=23226
        // with minimal risk.
        if (items && items.length == 1 && items[0].type == 'project') return 0;
        return items.length > 0;
    case 'cmd_exportToPackage':
        return items && items.length > 0;
    default:
        break;
    }
    return false;
}

peFile.prototype.isCommandEnabled = peFile.prototype.supportsCommand;

peFile.prototype.doCommand = function(command) {
    var item = null, items = null;
    var i, fname, otherfile;
    var dirname = '';
    if (ko.projects.active) {
        item = ko.projects.active.getSelectedItem();
        items = ko.projects.active.getSelectedItems();
    }
    switch (command) {
    case 'cmd_openFilePart':
        // get the current selection, then open the file
        if (!items) return;
        var paths = [];
        for (i = 0; i < items.length; i++) {
            if (items[i].type == 'file') paths.push(items[i].url);
        }
        ko.open.multipleURIs(paths);
        break;
    case 'cmd_findInPart':
    case 'cmd_replaceInPart':
        var coll = Components.classes["@activestate.com/koCollectionFindContext;1"]
                .createInstance(Components.interfaces.koICollectionFindContext);
        for (i = 0; i < items.length; i++) {
            var item = items[i];
            switch (item.type) {
            case 'file':
                if (item.getFile().isLocal) {
                    coll.add_file(item);
                }
                break;
            case 'project':
            case 'folder':
            case 'livefolder':
                coll.add_koIContainer(item);
                break;
            default:
                log.warn("unexpected item type for 'cmd_findInPart': "+item.type);
            }
        }
        if (command == "cmd_findInPart") {
            ko.launch.findInCollection(coll);
        } else {  // command == "cmd_replaceInPart"
            ko.launch.replaceInCollection(coll);
        }
        break;
    case 'cmd_showInFinder':
        var sysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
                    getService(Components.interfaces.koISysUtils);
        sysUtilsSvc.ShowFileInFileManager(item.getFile().path)
        break;
    case 'cmd_renameFile':
        var newname = ko.dialogs.renameFileWrapper(item.name);
        if (!newname) return;
        var osSvc = Components.classes["@activestate.com/koOs;1"]
                                    .getService(Components.interfaces.koIOs);
        var newfile = osSvc.path.join(item.getFile().dirName, newname);
        osSvc.rename(item.getFile().path, newfile);
        if (!item.live)
            item.url = newfile;
        var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].getService(Components.interfaces.koIFileStatusService);
        fileStatusSvc.updateStatusForUris(1, [newfile], true /* forcerefresh */);
        ko.projects.active.view.refresh(item);
        break;
    case 'cmd_refreshStatus':
        ko.projects.refreshStatus();
        break;
    case 'cmd_dumpPartProperties':
        if (!ko.projects.active) return;
        item = ko.projects.active.getSelectedItem();
        if (item) item.dump(0);
        break;
    case 'cmd_editProperties':
        //if (!ko.projects.getFocusedProjectView())
        //    return;
        if (!items) return;
        for (i = 0; i < items.length; i++) {
            item = items[i];
            switch (item.type) {
                case 'file':
                    ko.projects.fileProperties(item, null, false);
                    continue;
                case 'folder':
                case 'livefolder':
                case 'project':
                    ko.projects.fileProperties(item, null, true);
                    continue;
            }
        }
        break;
    case 'cmd_showUnsavedChanges':
        view = ko.views.manager.currentView;
        var changes = view.koDoc.getUnsavedChanges();
        ko.launch.diff(changes,
                       _bundle.formatStringFromName("unsavedChangesForWindowTitle",
                                                    [view.koDoc.displayPath],
                                                    1));
        break;
    case 'cmd_compareFiles':
        if (!ko.projects.active || !items || items.length == 0) {
            return;
        } else {
            fname = items[0].getFile().URI;
            otherfile = items[1].getFile().URI;
        }
        ko.fileutils.showDiffs(fname, otherfile);
        return;
    case 'cmd_compareFileWith':
        if (!ko.projects.active) return;
        var file = items[0].getFile()
        fname = file.URI;
        var pickerDir = file.isLocal? file.dirName : '';
        otherfile = ko.filepicker.browseForFile(pickerDir);
        if (otherfile) {
            ko.fileutils.showDiffs(fname, otherfile);
        }
        return;
    case "cmd_exportItems":
        if (!ko.projects.active) return;
        ko.projects.exportItems(items);
        break;
    case 'cmd_exportToPackage':
        ko.projects.exportPackageItems(items);
        break;
    case 'cmd_cut':
        // get the current selection, then open the file
        if (!ko.projects.active) return;
        this.doCut(items)
        break;
    case 'cmd_copy':
        // get the current selection, then open the file
        this.doCopy(items)
        break;
    case 'cmd_paste':
        if (this._clipboard.length == 0) return;
        this.doPaste(items)
        break;
    default:
        break;
    }
}

peFile.prototype.ondblclick = function(item,event) {
    ko.open.URI(item.url);
}


peFile.prototype.doCut = function(items)
{
    var needUpdate = this._clipboard.length == 0 && items.length != 0;
    this._clipboard = [];
    var i, index, parent;
    // Find out what the "first" index of the parts is
    var first_index = null;
    var parentindex = 0;
    for (i = 0; i < items.length; i++) {
        index = ko.projects.active.getIndexByPart(items[i]);
        if (first_index == null || index < first_index) {
            first_index = index;
            parentindex = ko.projects.active.getIndexByPart(items[i].parent);
        }
    }

    // Do the cut
    for (i = 0; i < items.length; i++) {
        this._clipboard.push(items[i].clone());
    }
    ko.projects.active.manager.removeItems(items, false);
    // Select the parent
    if (parentindex != -1 && ko.projects.active.selection) {
        ko.projects.active.selection.select(parentindex);
    }
    if (needUpdate) {
        window.updateCommands('clipboard');
    }
}

peFile.prototype.doCopy = function(items)
{
    // XXX use moz clipboard for this?
    var needUpdate = this._clipboard.length == 0 && items.length != 0;
    this._clipboard = [];
    for (var i = 0; i < items.length; i++) {
        this._clipboard.push(items[i].clone());
    }
    if (needUpdate) {
        window.updateCommands('clipboard');
    }
}

peFile.prototype.doPaste = function()
{
    // XXX use moz clipboard for this?
    var item;
    var dest = ko.projects.active.getSelectedItem();
    for (var i = 0; i < this._clipboard.length; i++) {
        item = this._clipboard[i];
        if (item) {
            ko.projects.addItem(item.clone(), dest);
        }
    }
}

// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peFile());
}).apply();


(function() {

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFile.properties");

this.refreshStatus = function doRefreshStatus(/*koIPart []*/ items) {
    var urls = [];

    if (!items) {
        var pview = ko.projects.getFocusedProjectView();
        if (pview) {
            items = pview.getSelectedItems();
        }
    }
    if (items) {
        for (var i=0; i<items.length; i++) {
            urls.push(items[i].url);
        }
    } else {
        // always fall back to the current view
        var view = ko.views.manager.currentView;
        var item = view.item;
        if (!view.koDoc || view.koDoc.isUntitled) {
            // This is an unsaved file -- cannot refresh.
            return;
        }
        item.url = view.koDoc.file.URI;
        urls.push(item.url);

        // Also refresh CodeIntel data for this view, if enabled.
        if (view.isCICitadelStuffEnabled || view.isCIXMLStuffEnabled) {
            gCodeIntelSvc.scan_document(view.koDoc, 0, false);
        }
    }
    try {
        var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].getService(Components.interfaces.koIFileStatusService);
        fileStatusSvc.updateStatusForUris(urls.length, urls,
                                          true /* forcerefresh */);
    } catch(e) {
        ko.projects.manager.log.error(e);
    }
}

this.fileProperties = function peFile_Properties(item, view, folder)
{
    if (typeof(view) == 'undefined') view = null;
    if (typeof(folder) == 'undefined') folder = false;
    if (typeof(item) == 'undefined') item = null;

    var file = null;
    if (item && !view)
        file = item.getFile();
    if (file) {
        // try to get the view from the view manager
        view = ko.views.manager.getViewForURI(file.URI);
    }
    try {
        // Handle cancel from prefs window
        var resp = new Object ();
        resp.res = "";
        resp.part = item;
        resp.title = _bundle.GetStringFromName("filePropertiesAndSettings");
        resp.folder = folder;
        resp.view = view;
        if (item && item.type == "project") {
            resp.title = _bundle.GetStringFromName("projectPropertiesAndSettings");
        } else if (folder) {
            resp.title = _bundle.GetStringFromName("folderPropertiesAndSettings");
        }
        try {
            window.openDialog(
                    "chrome://komodo/content/pref/project.xul",
                    'Komodo:ProjectPrefs',
                    "chrome,dependent,resizable,close=yes,modal=yes",
                    resp);
        } catch(ex) {
            log.exception(ex);
            //log.warn("error opening preferences dialog:"+ex);
            return false;
        }
        if (resp.res != "ok") {
            return false;
        }
        // make the tree refresh this part
        ko.projects.active.view.refresh(item);
        return true;
    } catch (e) {
        log.exception(e);
    }
    return false;
}

}).apply(ko.projects);


(function() {
    
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFile.properties");

function _openDiffWindowForFiles(fname1, fname2) {
    window.setCursor("wait");
    try {
        var diff = Components.classes['@activestate.com/koDiff;1']
                      .createInstance(Components.interfaces.koIDiff);
        try {
            diff.initByDiffingFiles(fname1, fname2);
        } catch (ex) {
            log.error(ex);
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                        getService(Components.interfaces.koILastErrorService);
            var msg = _bundle.GetStringFromName("errorCalculatingDifferences") +
                       lastErrorSvc.getLastErrorMessage();
            alert(msg);
            return;
        }

        if (!diff.diff) {
            var txt = _bundle.formatStringFromName("thereAreNoDifferencesBetween", [fname1, fname2], 2);
            if (diff.doc1.existing_line_endings !=
                diff.doc2.existing_line_endings) {
                txt = _bundle.GetStringFromName("onlyLineEndingsDiffer");
            }
            ko.dialogs.alert(txt);
        } else {
            var title = _bundle.formatStringFromName("compareFilesWindowTitle",
                                                     [ko.uriparse.baseName(fname1),
                                                      ko.uriparse.baseName(fname2)],
                                                     2);
            ko.launch.diff(diff.diff, title, diff.warning);
        }
    } finally {
        window.setCursor('auto');
    }
}

this.showDiffs = function peFile_ShowDiffs(fname1, fname2) {
    // fname1/2 can be filenames or uri's.
    fname1 = fname1.replace("\\", "\\\\", 'g');
    fname2 = fname2.replace("\\", "\\\\", 'g');
    // difflib can be slow, so we do this in a timeout
    window.setTimeout(_openDiffWindowForFiles, 0, fname1, fname2);
}

}).apply(ko.fileutils);

// setTimeout in case projectManager.p.js hasn't been loaded yet.
setTimeout(function() {
ko.projects.addDeprecatedGetter("peFile_Properties", "fileProperties");
    },1);
// Do this one here.
var _deprecated_getters_noted = {peFile_ShowDiffs:false};
__defineGetter__('peFile_ShowDiffs',
 function() {
    if (!_deprecated_getters_noted.peFile_ShowDiffs) {
        _deprecated_getters_noted.peFile_ShowDiffs = true;
        ko.projects.manager.log.error("DEPRECATED: "
                                      + 'peFile_ShowDiffs'
                                      + ", use ko.fileutils.showDiffs"
                                      + "\n");
    }
    return ko.fileutils.showDiffs;
 });
