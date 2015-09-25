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
    em.registerCommand('cmd_refreshStatus', this);  //TODO: impl in places
    em.registerCommand('cmd_editProperties', this);
    em.registerCommand('cmd_showUnsavedChanges', this);
    em.registerCommand('cmd_compareFiles', this);
    em.registerCommand('cmd_compareFileWith', this);
    em.registerCommand("cmd_cut",this);
    em.registerCommand("cmd_copy",this);
    em.registerCommand("cmd_paste",this);
    em.registerCommand("cmd_findInPart",this);
    em.registerCommand("cmd_replaceInPart",this);
    em.registerCommand("cmd_renameFile",this);
}

peFile.prototype.registerEventHandlers = function() {
    ko.projects.extensionManager.addEventHandler(Components.interfaces.koIPart_file,'ondblclick',this);
    // we don't add a dblclick handler for Components.interfaces.koIPart_ProjectRef, since
    // it inherits from koIPart_file
}

peFile.prototype.registerMenus = function() {
}

peFile.prototype.supportsCommand = function(command, item) {
    var items = null;
    var file = null;
    if (ko.places && ko.places.currentPlace) {
        items = ko.places.manager.getSelectedItems();
    }
    switch (command) {
    case 'cmd_cut':
    case 'cmd_copy':
        if (!items || items.length == 0) return false;
        if (command == 'cmd_cut' && !ko.projects.active.manager.writeable()) return false;
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

    case 'cmd_findInPart':
    case 'cmd_replaceInPart':
        if (!items) return false;
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
    case 'cmd_renameFile':
        return (items && items.length == 1 && items[0].type != 'project' && items[0].isLocal);
    case 'cmd_refreshStatus':
        return ko.views.manager.currentView != null;
    case 'cmd_editProperties':
        return items && items.length > 0;
    case 'cmd_showUnsavedChanges':
        var view = ko.views.manager.currentView;
        return (view && view.koDoc && view.koDoc.isDirty &&
                !view.koDoc.isUntitled);
    case 'cmd_compareFiles':
        return (items && items.length == 2 && items[0].type == 'file' && items[1].type == 'file');
    case 'cmd_compareFileWith':
        return (items && items.length == 1 && items[0].type == 'file');
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
    if (ko.places && ko.places.manager.currentPlace !== null) {
        item = ko.places.manager.getSelectedItem();
        items = ko.places.manager.getSelectedItems();
    }
    switch (command) {
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
        if (ko.places) {
            ko.places.manager.refreshItem(item);
        }
        break;
    case 'cmd_refreshStatus':
        ko.projects.refreshStatus();
        break;
    case 'cmd_editProperties':
        if (!items) return;
        for (i = 0; i < items.length; i++) {
            item = items[i];
            ko.projects.fileProperties(item, null, item.type != 'file');
        }
        break;
    case 'cmd_showUnsavedChanges':
        var view = ko.views.manager.currentView;
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
            fname = items[0].uri;
            otherfile = items[1].uri;
        }
        ko.fileutils.showDiffs(fname, otherfile);
        return;
    case 'cmd_compareFileWith':
        if (!items) return;
        item = items[0];
        var file = item.getFile();
        fname = item.uri;
        var pickerDir = item.isLocal? file.dirName : '';
        otherfile = ko.filepicker.browseForFile(pickerDir);
        if (otherfile) {
            ko.fileutils.showDiffs(fname, otherfile);
        }
        return;
    case 'cmd_cut':
        // get the current selection, then open the file
        if (!items) return;
        this.doCut(items)
        break;
    case 'cmd_copy':
        // get the current selection, then open the file
        this.doCopy(items)
        break;
    case 'cmd_paste':
        if (!xtk.clipboard.getText())
            return;
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
    var pview = ko.projects.safeGetFocusedPlacesView();
    if (pview) {
        items = pview.manager.doCutPlaceItem();
    }
}

peFile.prototype.doCopy = function(items)
{
    var pview = ko.projects.safeGetFocusedPlacesView();
    if (pview) {
        items = pview.manager.doCopyPlaceItem();
    }
}

peFile.prototype.doPaste = function()
{
    var pview = ko.projects.safeGetFocusedPlacesView();
    if (pview) {
        items = pview.manager.doPastePlaceItem();
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
        var pview = ko.projects.safeGetFocusedPlacesView();
        if (pview) {
            items = pview.manager.getSelectedItems();
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
            ko.codeintel.scan_document(view.koDoc, 0, true /* forcedScan */);
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
    if (item && !view) {
        // try to get the view from the view manager
        //XXX: Settle on one of .uri and .url
        view = ko.views.manager.getViewForURI(item.uri || item.url);
    }
    try {
        // Handle cancel from prefs window
        var resp = new Object ();
        resp.res = "";
        resp.part = item;
        resp.title = _bundle.GetStringFromName("filePreferences");
        resp.folder = folder;
        resp.view = view;
        if (item && item.type == "project") {
            resp.title = _bundle.GetStringFromName("projectPreferences");
        } else if (folder) {
            resp.title = _bundle.GetStringFromName("folderPreferences");
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
        if (item) {
            if (item.type == 'project') {
                window.updateCommands('project_dirty');
            } else if (ko.places) {
                // make the tree refresh this part
                ko.places.manager.refreshItem(item);
            }
        }
        return true;
    } catch (e) {
        log.exception(e);
    } finally {
        if (view) {
            view.scintilla.focus();
        }
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

this.setFileStatusAttributesFromFile = function peFile_setFileStatusAttributesFromFile(element, koFile) {
    // Here we set the attributes for our file status indicators. The following
    // attributes on the element can be set:

    // alt_image = [async_operation];
    // file_readonly = [readonly]

    // File image url.
    element.setAttribute('file_image_url', 'koicon://' + koFile.baseName + '?size=16');

    // Readonly status.
    if (!koFile.exists || koFile.isWriteable) {
        element.removeAttribute('file_readonly');
    } else {
        element.setAttribute('file_readonly', 'readonly');
    }

    // File status.
    var asyncSvc = Components.classes['@activestate.com/koAsyncService;1'].
                    getService(Components.interfaces.koIAsyncService);
    if (asyncSvc.uriHasPendingOperation(koFile.URI)) {
        // This file has an asynchronous operation pending, give it
        // the "processing" throbber image.
        element.removeAttribute('file_image_url');
        element.setAttribute('alt_image', 'async_operation');
    } else if (element.getAttribute('alt_image') == 'async_operation') {
        element.removeAttribute('alt_image');
    }
}

this.setFileStatusAttributesFromDoc = function peFile_setFileStatusAttributesFromDoc(element, koDoc) {
    let koFile = koDoc.isUntitled ? null : koDoc.file;

    if (!koFile) {
        element.removeAttribute('file_image_url');
        element.removeAttribute('file_status');
        element.removeAttribute('alt_image');
        return;
    }

    this.setFileStatusAttributesFromFile(element, koFile);
}

this.setFileStatusAttributesFromView = function peFile_setFileStatusAttributesFromView(element, view) {
    var viewType = view.getAttribute("type");
    if (viewType != "browser" && viewType != "quickstart") {
        let koFile = view && view.koDoc && view.koDoc.file;
        if (koFile && view.koDoc.isUntitled) {
            koFile = null;
        }
        
        if (koFile) {
            this.setFileStatusAttributesFromFile(element, koFile);
        } else {
            if (view.koDoc) {
                // Deal with untitled documents (that do not have a koFile).
                element.setAttribute('file_image_url', 'koicon://' + view.koDoc.baseName + '?size=16');
            } else {
                element.removeAttribute('file_image_url');
            }
            element.removeAttribute('file_status');
            if (!view.icon_type) {
                element.removeAttribute('alt_image');
            }
        }
    
        if (view.icon_type) {
            element.removeAttribute('file_image_url');
            element.setAttribute('alt_image', view.icon_type);
        }
    } else {
        if (view.icon_type) {
            element.setAttribute('alt_image', view.icon_type);
        } else {
            element.setAttribute('alt_image', viewType);
        }
    }
}

}).apply(ko.fileutils);
