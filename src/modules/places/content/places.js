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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2010
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

/* Places -- projects v2
 *
 * Defines the "ko.places" namespace.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('places' in ko)) {
    ko.places = {};
}

xtk.include("clipboard");

var gPlacesViewMgr = null;

(function() {

var _globalPrefs;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://places/locale/places.properties");
var _placePrefs;
var filterPrefs;
var uriSpecificPrefs;
var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

var widgets = {};
var osPathSvc;

const DEFAULT_EXCLUDE_MATCHES = ".*;*~;#*;CVS;*.bak;*.pyo;*.pyc";
const DEFAULT_INCLUDE_MATCHES = ".login;.profile;.bashrc;.bash_profile";
    
var log = getLoggingMgr().getLogger("places_js");
log.setLevel(LOG_DEBUG);

// Yeah, not really a class per se, but it acts like one, so
// give it an appropriate name.
// This object will manage the JS side of the tree view.
function viewMgrClass() {
    this.startingIndex = -1;
    this.default_exclude_matches = ".*;*~;#*;CVS;*.bak;*.pyo;*.pyc";
    // overides, to include:
    this.default_include_matches = ".login;.profile;.bashrc;.bash_profile";
    this._nextSortDir = {
        natural: 'ascending',
        ascending: 'descending',
        descending:'natural'
    };
    this._mozSortDirNameToKomodoSortDirValue = {
        natural: Components.interfaces.koIPlaceTreeView.SORT_DIRECTION_NAME_NATURAL,
        ascending: Components.interfaces.koIPlaceTreeView.SORT_DIRECTION_NAME_ASCENDING,
        descending:Components.interfaces.koIPlaceTreeView.SORT_DIRECTION_NAME_DESCENDING
    };
};

viewMgrClass.prototype = {
    initialize: function() {
        this.tree = document.getElementById("places-files-tree");
        this.view = Components.classes["@activestate.com/koPlaceTreeView;1"]
            .createInstance(Components.interfaces.koIPlaceTreeView);
        if (!this.view) {
            throw("couldn't create a koPlaceTreeView");
        }
        if (!this.view) {
            throw("couldn't create a koPlaceTreeView");
        }
        this.tree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.view;
        this.view.initialize();
        var treecol = this.tree.getElementsByTagName('treecol')[0];
        var sortDir = treecol.getAttribute("sortDirection");
        if (!sortDir) {
            var placePrefs = _globalPrefs.getPref("places");
            if (placePrefs.hasPref("sortDirection")) {
                sortDir = placePrefs.getStringPref("sortDirection");
            }
            if (!sortDir || !this._nextSortDir[sortDir]) {
                sortDir = 'natural';
            }
            treecol.setAttribute("sortDirection", sortDir);
        }
        this.view.sortBy(treecol.id, this._mozSortDirNameToKomodoSortDirValue[sortDir]);
    },
    focus: function() {
          dump("places: viewMgr.focus()\n");
      },
    updateView: function() {
          dump("places: viewMgr.updateView()\n");
      },
    _currentRow: function(event) {
        var row = {};
        this.tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
        return row.value;
    },

    onDblClick: function(event) {
        if (event.which != 1) {
            return;
        }
        var index = this._currentRow(event);
        var isFolder = this.view.isContainer(index);
        if (!isFolder) {
            this.openFileByIndex(index);
        } else {
            ko.places.manager.toggleRebaseFolderByIndex(index);
            //TODO: get this to stop the folder from toggling?
            // See the dbexplorer xbl bindings for how this is done.
        }
        // Don't handle this event further for both files and folders.
        event.stopPropagation();
        event.cancelBubble = true;
        event.preventDefault();
    },

    rebaseByIndex: function(index) {
        ko.places.manager.toggleRebaseFolderByIndex(index);
    },
    
    rebaseToParentByIndex: function(index) {
        var uri = this.view.getURIForRow(index);
        var parent_uri;
        if (this.currentPlaceIsLocal) {
            parent_uri = ko.uriparse.localPathToURI(ko.uriparse.dirName(uri));
        } else {
            parent_uri = uri.replace(/[/\\][^/\\]+$/, '');
        }
        ko.places.manager.rebaseToDirByURI(parent_uri, uri);
    },
    
    refreshViewByIndex: function(index) {
        this.view.refreshView(index);
    },

    openFileByIndex: function(index) {
        ko.open.URI(this.view.getURIForRow(index));
    },

    refreshStatus: function(index) {
        var uri = this.view.getURIForRow(index);
        var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].getService(Components.interfaces.koIFileStatusService);
        fileStatusSvc.updateStatusForUris(1, [uri],
                                          true /* forcerefresh */);
    },

    compareFileWith: function(index) {
        var uri = this.view.getURIForRow(index);
        var file = Components.classes["@activestate.com/koFileEx;1"].
                createInstance(Components.interfaces.koIFileEx);
        file.URI = uri
        var pickerDir = file.isLocal? file.dirName : '';
        var otherfile = ko.filepicker.openFile(pickerDir);
        if (otherfile) {
            ko.fileutils.showDiffs(file.path, otherfile);
        }
    },

    addNewFile: function(index) {
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFileName"));
        if (!name) return;
        try {
            this.view.addNewFileAtParent(name, index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
    },

    addNewFolder: function(index) {
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFolderName"));
        if (!name) return;
        try {
            this.view.addNewFolderAtParent(name, index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
    },

    onTreeClick: function(event) {
        var index = this._currentRow(event);
        this.view.markRow(index);
    },

    onTreecolsClick: function(event) {
        gEvent = event;
        // c.f. mozilla/mailnews/base/resources/content/threadPane.js
        var t = event.originalTarget;
        
        // single-click on a column
        if (t.localName == "treecol" && event.detail == 1) {
            var sortDir = t.getAttribute("sortDirection");
            var newSortDir = this._nextSortDir[sortDir];
            t.setAttribute("sortDirection", newSortDir);
            this.view.sortBy(t.id, this._mozSortDirNameToKomodoSortDirValue[newSortDir]);
            this.view.sortRows();
        }
    },

    onTreeKeyPress: function(event) {
        //dump("TODO: viewMgrClass.onTreeKeyPress\n");
    },
    initFilesContextMenu: function(event) {
        if (event.explicitOriginalTarget.id != "places-files-tree-body") {
            dump("No context menu when clicking on "
                 + event.explicitOriginalTarget.id
                 + "\n");
            //XXX What do we do to prevent a small-box empty-menu from appearing?
            /*
            event.stopPropagation();
            event.cancelBubble = true;
            event.preventDefault();
            */
            return false;
        }
        //gEvent = event;
        /*
         * Menus:
         *   *Folder: Rebase
         *   *Folder: Move up one level
         *   *File: Open
         *   *Folder: Refresh View
         *   *File: Compare File With...
         *   *File: ----------------
         *   Cut   
         *   Copy  
         *   Paste (*File: disabled, *Folder: always enabled)
         *   Undo (undo a move)
         *----------------
         *   Find... (should be in this file|folder)
         *   Replace... (same)
         *   Show in {Explorer | File Manager | Finder}
         *   Rename...
         *   Refresh Status
         *----------------
         *   [Source Control | Source Control on Contents] ...
         *----------------
         *   Delete
         *   New File...
         *   New Folder...
         *----------------
         *   Properties (*Folder:disabled)
         */
        var index = this._currentRow(event);
        if (index == -1) {
            event.stopPropagation();
            event.cancelBubble = true;
            event.preventDefault();
            return false;
        }
        var isFolder = this.view.isContainer(index);
        var popupmenu = event.target;
        var nodes = popupmenu.childNodes;
        var firstMenuItem = nodes[0];
        var firstFolderMenuItemId_rebase = "placesContextMenu_folder_rebase";
        var firstFileMenuItemId_fileOpen = "placesContextMenu_file_open";
        var firstFolderMenuItemId_refreshView = "placesContextMenu_folder_refresh_view";
        var node, i = 0;
        var isLocal = ko.places.manager.currentPlaceIsLocal;
        while (!!(node = nodes[i])) {
            if (node.getAttribute("keep") != "true") {
                popupmenu.removeChild(node);
            } else {
                i++;
            }
            if (node.id == "placesContextMenu_partPaste") {
                node.disabled = !isFolder;
            }
        }
        var firstCommonNode = null;
        for (i = 0; node = nodes[i]; ++i) {
            if (node.id == "placesContextMenu_separatorCut") {
                firstCommonNode = node;
                break;
            }
        }
        if (!firstCommonNode) {
            dump("Can't find the common menu item placesContextMenu_separatorCut");
            return false;
        }
        var menuitem, newMenuItemNode;
        var _bundle_peFile = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/project/peFile.properties");

        var first_item_is_root = false;
        if (isFolder) {
            
            var disable_item = !this.view.isContainerOpen(index);
            menuitem = this._makeMenuItem(firstFolderMenuItemId_refreshView,
                                          _bundle.GetStringFromName("refreshView.label"),
                                          ("gPlacesViewMgr.refreshViewByIndex("
                                           + index
                                           + ");"));
            if (disable_item) {
                menuitem.setAttribute("disabled", "true");
            }
            newMenuItemNode = popupmenu.insertBefore(menuitem, firstCommonNode);

            menuitem = this._makeMenuItem("placesContextMenu_moveUp",
                                          _bundle.GetStringFromName("moveUpOneLevel.label"),
                                          "gPlacesViewMgr.rebaseToParentByIndex("
                                          + index
                                          + ");");
            if (index == 0) {
                if (isLocal) {
                    first_item_is_root =
                        (this.view.getCellText(index, {id:'name'})
                         == ko.uriparse.URIToLocalPath(ko.places.manager.
                                                       currentPlace));
                } else {
                    first_item_is_root =
                        (this.view.getCellText(index, {id:'uri'})
                         == ko.places.manager.currentPlace);
                }
            }
            menuitem.setAttribute("disabled",
                                  (first_item_is_root || index > 0).toString());
            //XXX Is the node's path the top-level?
            newMenuItemNode = popupmenu.insertBefore(menuitem, newMenuItemNode);

            var bundle_label = "rebaseFolder.label";
            disable_item = index == 0;
            menuitem = this._makeMenuItem(firstFolderMenuItemId_rebase,
                                          _bundle.GetStringFromName(bundle_label),
                                          ("gPlacesViewMgr.rebaseByIndex("
                                           + index
                                           + ");"));
            if (disable_item) {
                menuitem.setAttribute("disabled", "true");
            }
            popupmenu.insertBefore(menuitem, newMenuItemNode);
            menuitem = document.getElementById("placesContextMenu_newFile");
            menuitem.removeAttribute("disabled");
            menuitem.setAttribute("oncommand",
                                  ("gPlacesViewMgr.addNewFile("
                                    + index
                                    + ");"));
            menuitem = document.getElementById("placesContextMenu_newFolder");
            menuitem.removeAttribute("disabled");
            menuitem.setAttribute("oncommand",
                                  ("gPlacesViewMgr.addNewFolder("
                                    + index
                                    + ");"));
        } else {
            menuitem = this._makeMenuItem("placesContextMenu_compareFileWith",
                                          _bundle_peFile.GetStringFromName("compareFileWith"),
                                          ("gPlacesViewMgr.compareFileWith("
                                           + index
                                           + ");"));
            newMenuItemNode = popupmenu.insertBefore(menuitem, firstCommonNode);
            menuitem = this._makeMenuItem(firstFileMenuItemId_fileOpen,
                                          _bundle_peFile.GetStringFromName("open"),
                                          ("gPlacesViewMgr.openFileByIndex("
                                           + index
                                           + ");"));
            popupmenu.insertBefore(menuitem, newMenuItemNode);
        }
        menuitem = document.getElementById("placesContextMenu_showInFinder");
        var platform = navigator.platform.toLowerCase();
        var bundle_id;
        if (platform.substring(0, 3) == "win") {
            bundle_id = "ShowInExplorer.label";
        } else if (platform.substring(0, 5) == "linux") {
            bundle_id = "ShowInFileManager.label";
        } else {
            bundle_id = "ShowInFinder.label";
        }
        menuitem.setAttribute("label",
                              _bundle.GetStringFromName(bundle_id));
        return true;
    },

    _makeMenuItem: function(id, label, handler) {
        var menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", label);
        menuitem.setAttribute("id", id);
        menuitem.setAttribute("oncommand", handler);
        return menuitem;
    },

    updateMRUMenu: function(menupopup) {
        var mruList = null;
        if (_placePrefs.hasPref("mru_places")) {
            mruList = _placePrefs.getPref("mru_places");
        }
        while (menupopup.firstChild) {
            menupopup.removeChild(menupopup.lastChild);
        }
        var uriItems = [];
        var i;
        for (i = mruList.length - 1; i >= 0; i--) {
            uriItems.push([mruList.getStringPref(i), 'M', i]);
        }
        var history_prevPlaces = ko.places.manager.history_prevPlaces;
        for (i = history_prevPlaces.length - 1; i >= 0; i--) {
            uriItems.push([history_prevPlaces[i], 'P', i]);
        }
        var history_forwardPlaces = ko.places.manager.history_forwardPlaces;
        for (i = history_forwardPlaces.length - 1; i >= 0; i--) {
            uriItems.push([history_forwardPlaces[i], 'F', i]);
        }
        uriItems.sort(function(a, b) {
                if (a[0] < b[0]) return -1;
                else if (a[0] == b[0]) return 0;
                else return 1;
            });
        var uri, path, uriItem, lastURI = null;
        var length = uriItems.length;
        var fileObj = Components.classes["@activestate.com/koFileEx;1"].
              createInstance(Components.interfaces.koIFileEx);
        var menuItemNo = 0;
        var menuitem;
        if (length > 0) {
            for (i = 0; i < length; ++i) {
                uriItem = uriItems[i];
                if (uriItem[0] == lastURI) continue;
                fileObj.URI = lastURI = uriItem[0];
                path = (fileObj.isLocal ? fileObj.displayPath : lastURI);
                menuitem = document.createElement("menuitem");
                // Mozilla does not handle duplicate accesskeys, so only putting
                // them on first 10.
                if ((menuItemNo + 1) <= 9) {
                    menuitem.setAttribute("accesskey", "" + (menuItemNo+1));
                } else if ((menuItemNo+1) == 10) {
                    menuitem.setAttribute("accesskey", "0");
                }
                menuitem.setAttribute("label", (menuItemNo+1) + " " + path);
                menuitem.setAttribute("class", "menuitem_mru");
                menuitem.setAttribute("crop", "center");
                menuitem.setAttribute("oncommand",
                                      ("ko.places.manager.loadRecentURI_byIndex('"
                                       + uriItem[1] // code
                                       + "', "
                                       + uriItem[2] // index
                                       + ")"));
                menupopup.appendChild(menuitem);
                menuItemNo += 1;
            }
        } else {
            // create a dead menu item
            menuitem = document.createElement("menuitem");
            var label = _bundle.GetStringFromName("noRecentDirectories");
            menuitem.setAttribute("label", label);
            menuitem.setAttribute("disabled", "true");
            menupopup.appendChild(menuitem);
        }
    },

    doStartDrag: function(event, tree) {
        var index = this._currentRow(event);
        if (!this.view.canDrag(index)) {
            return;
        }
        this.complainIfNotAContainer = true;
        var uri = this.view.getURIForRow(index);
        if (!uri) {
            return;
        }
        var path;
        var dt = event.dataTransfer;
        if (this.currentPlaceIsLocal) {
            var nsLocalFile = Components.classes["@mozilla.org/file/local;1"]
                .createInstance(Components.interfaces.nsILocalFile);
            path = ko.uriparse.URIToLocalPath(uri);
            nsLocalFile.initWithPath(path);
            dt.mozSetDataAt("application/x-moz-file", nsLocalFile, 0);
            dt.setData('text/plain', path);
        } else {
            dt.mozSetDataAt("application/x-moz-file", uri, 0);
            dt.setData('text/plain', uri);
        }
        this.startingIndex = index;
        if (event.ctrlKey) {
            dt.effectAllowed = this.originalEffect = "copy";
            this.copying = true;
        } else {
            dt.effectAllowed = this.originalEffect = "move";
            this.copying = false;
        }
    },

    doDragEnter: function(event, tree) {
        //dump("viewMgrClass.doDragEnter\n");
        return this._checkDrag(event);
    },

    doDragOver: function(event, tree) {
        //dump("viewMgrClass.doDragOver\n");
        return this._checkDrag(event);
    },
    
    _checkDrag: function(event) {
        if (!event.dataTransfer.types.contains("application/x-moz-file")) {
            if (this.complainIfNotAContainer) {
                log.debug("not a file data-transfer\n");
                this.complainIfNotAContainer = false;
            }
        }
        var index = this._currentRow(event);
        var retVal = false;
        if (index == this.startingIndex) {
            // Can't drag onto oneself
        } else if (!this.view.isContainer(index)) {
            //if (this.complainIfNotAContainer) {
            //    log.debug("Not a container\n");
            //    this.complainIfNotAContainer = false;
            //}
        } else if (index == this.view.getParentIndex(this.startingIndex)) {
            // Can't drop into the parent
            //TODO: Check targetIsChildOfSource here.
        } else {
            retVal = true;
            //dump("this.originalEffect: " + this.originalEffect + "\n");
        }
        event.dataTransfer.effectAllowed = retVal ? this.originalEffect : "none";
        return retVal;
    },

    doDrop : function(event, tree) {
        if (this.startingIndex == -1) {
            log.debug("onDrop: startingIndex: -1: don't do anything");
            return false;
        }
        var from_index = this.startingIndex;
        var to_index = this._currentRow(event);
        try {
            this._finishFileCopyOperation(from_index, to_index, this.copying);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
        this.startingIndex = -1;
        return true;
    },

    _universalNewPath: function(conn, osPathSvc, path, basename) {
        if (!conn) {
            return osPathSvc.join(path, basename);
        } else {
            return path + "/" + basename;
        }
    },

    _universalFileExists: function(conn, osPathSvc, path, basename) {
        if (!conn) {
            return osPathSvc.exists(this._universalNewPath(conn, osPathSvc, path, basename));
        } else {
            return conn.list(this._universalNewPath(conn, osPathSvc, path, basename), true);
        }
    },

    _finishFileCopyOperation: function(from_index, to_index, copying) {
        var srcFileInfo = {}, targetFileInfo = {};
        var callback = {
            callback: function(result, data) {
                if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    ko.dialogs.alert(data);
                } else {
                    window.updateCommands("did_tree_operation");
                }
            }
        };
        var from_uri = this.view.getURIForRow(from_index);
        var from_view = ko.views.manager.getViewForURI(from_uri);
        if (from_view) {
            if (from_view.isDirty) {
                var prompt = ("File "
                              + ko.uriparse.URIToPath(from_uri)
                              + " has unsaved changed.  "
                              + (copying ? "Copy" : "Move")
                              + " without saving?");
                var response = "No";
                var title = "Save changes first?";
                var res = ko.dialogs.yesNo(prompt, response, null, title);
                if (res != "Yes") {
                    return;
                }
            }
        }
        var res = this.view.treeOperationWouldConflict(from_index,
                                                       to_index,
                                                       copying,
                                                       srcFileInfo,
                                                       targetFileInfo);
        if (res) {
            srcFileInfo = srcFileInfo.value;
            targetFileInfo = targetFileInfo.value;
            // targetFileInfo points at the existing file
            var srcFileInfoText = this._formatFileInfo(srcFileInfo);
            var targetFileInfoText = this._formatFileInfo(targetFileInfo);
            var prompt = "File already exists";//@@@
            var buttons, text, title;
            if (res == Components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR) {
                title = "Directory already exists";
                prompt = "Replacing a directory within Komodo isn't supported";
                text = ("For source file "
                        + srcFileInfo.baseName
                        + " in directory "
                        + srcFileInfo.dirName);
                ko.dialogs.alert(prompt, text, title);
                return true;
            } else if (res == Components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR) {
                title = "Not moving the file anywhere";
                prompt = "You can't move a file into its own directory";
                text = ("For file "
                        + srcFileInfo.baseName
                        + ", "
                        + srcFileInfo.dirName);
                ko.dialogs.alert(prompt, text, title);
                return true;
            }
            title = "File already exists";//@@@
            var buttons;
            text = ("For source file: "
                    + srcFileInfoText
                    + ",\ntarget file: "
                    + targetFileInfoText
                    + ".");
            if (res == Components.interfaces.koIPlaceTreeView.MOVE_OTHER_DIR_FILENAME_CONFLICT) {
                prompt = ("Overwrite file "
                          + srcFileInfo.baseName
                          + "?");
                buttons = ["Overwrite", "Cancel"];
            } else {
                prompt = ("Save file "
                          + srcFileInfo.baseName
                          + " with a new name, or overwrite?");
                buttons = ["Copy with New Name", "Overwrite", "Cancel"];
            }
            var response = ko.dialogs.customButtons(prompt, buttons, "Cancel", text, title);
            if (!response || response == "Cancel") {
                return true;
            } else if (response == "Overwrite") {
                // do nothing, just copy it over
            } else if (response == "Copy with New Name") {
                // This is where we need a new dialog.
                var newName = srcFileInfo.baseName;
                var label = "File name:";
                title = "Enter a new name for the copied file";
                var value;
                var newPath;
                var regEx = /(.*)\((\d+)\)$/;
                var idx;
                var targetDirPath = targetFileInfo.dirName;
                var basePart, numPart;
                var conn = null;
                if (!ko.places.manager.currentPlaceIsLocal) {
                    var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
                    conn = RCService.getConnectionUsingUri(ko.places.manager.currentPlace);
                }
                try {
                    while (true) {
                        prompt = ("File "
                                  + newName
                                  + " exists");
                        var m = regEx.exec(newName);
                        if (m) {
                            basePart = m[1];
                            numPart = parseInt(m[2]);
                        } else {
                            basePart = newName + " ";
                            numPart = 0;
                        }
                        // Find the lowest paren # that doesn't exist
                        while (numPart < 1000) {
                            numPart += 1;
                            value = basePart + "(" + numPart + ")";
                            if (!this._universalFileExists(conn, osPathSvc,
                                                          targetDirPath,
                                                          value)) {
                                break;
                            }
                            if (numPart == 1000) {
                                ko.dialogs.alert("Can't find a unique filename; cancelling");
                                return true;
                            }
                        }
                        newName = ko.dialogs.prompt(prompt, label, value, title);
                        if (!newName) {
                            return true;
                        }
                        
                        if (!this._universalFileExists(conn, osPathSvc, targetDirPath, newName)) {
                            newPath = this._universalNewPath(conn, osPathSvc, targetDirPath, newName);
                            break;
                        }
                    }
                    this.view.doTreeCopyWithDestName(from_index, to_index,
                                                     newPath, callback);
                    return true;
                } finally {
                    if (conn) {
                        conn.close();
                    }
                }
            }
        }
        if (!copying) {
            var to_uri = this.view.getURIForRow(to_index);
            callback = {
            callback: function(result, data) {
                    if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                        ko.dialogs.alert(data);
                    } else {
                        // Update the Komodo view
                        if (from_view) {
                            var orig_view_type = from_view.getAttribute("type");
                            // var orig_tabbed_view_id = from_view.tabbedViewId;
                            var orig_tabbed_list = document.getElementById(from_view.parentView.id);
                            var orig_tabbed_index = ko.history.tabIndex_for_view(from_view);
                            var scimozPropertyNames =
                                ['anchor',
                                 'currentPos',
                                 'scrollWidth',
                                 'scrollWidthTracking',
                                 'xOffset',
                                 'firstVisibleLine',
                                 'useTabs',
                                 'tabWidth',
                                 'indent'
                                 ];
                            // We can't set these:
                            var scimozDocSettingsProperties = [
                                 'showWhitespace',
                                 'showLineNumbers',
                                 'showIndentationGuides',
                                 'showEOL',
                                 'editFoldLines',
                                 'editWrapType'
                                 ];
                            var config = {};
                            var fromScimoz = from_view.scimoz;
                            scimozPropertyNames.map(function(name) {
                                    config[name] = fromScimoz[name];
                                });
                            from_view.closeUnconditionally();
                            var full_to_uri = to_uri + "/" + ko.uriparse.baseName(from_uri);
                            var inner_callback = function(newView) {
                                var newScimoz = newView.scimoz;
                                scimozPropertyNames.map(function(name) {
                                        try {
                                            newScimoz[name] = config[name];
                                        } catch(ex) {
                                            log.exception("Can't set " + name);
                                        }
                                    });
                            };
                            ko.views.manager.doFileOpenAsync(full_to_uri,
                                                             orig_view_type,
                                                             orig_tabbed_list,
                                                             orig_tabbed_index,
                                                             inner_callback);
                        }
                        window.updateCommands("did_tree_operation");
                    }
                }
            };
        }
        this.view.doTreeOperation(from_index, to_index,
                                  copying, callback);
        return true;
    },

    _formatNumber: function(size) {
        var rev_str = size.toString().split('').reverse().join('').replace(/(\d{3})/g, "$1,");
        return rev_str.split('').reverse().join('') + " bytes";
    },

    _formatDate: function(dateVal) {
        var d = Date(dateVal);
        return d.toLocaleString();
    },
    
    _formatFileInfo: function(fileInfo) {
        var size = fileInfo.fileSize;
        var s = (fileInfo.path // baseName
                 + ", "
                 + this._formatNumber(fileInfo.fileSize)
                 + ", modified at "
                 + this._formatDate(fileInfo.lastModifiedTime)
                 + ".");
        return s;
    },
    
    finalize: function() {
        this.view.terminate();
        this.view = null;
        var treecol = this.tree.childNodes[0].childNodes[0];
        _globalPrefs.getPref("places").getStringPref("sortDirection",
                                                     treecol.getAttribute("sortDirection"));
    },

    // Filtering routines:

    _updateCurrentUriViewPref: function(viewName) {
        var uri = ko.places.manager.currentPlace;
        var prefSet;
        if (uriSpecificPrefs.hasPref(uri)) {
            prefSet = uriSpecificPrefs.getPref(uri);
        } else {
            prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
            uriSpecificPrefs.setPref(uri, prefSet);
        }
        prefSet.setStringPref('viewName', viewName);
    },
                

    placeView_defaultView: function() {
        gPlacesViewMgr.view.setMainFilters(this.default_exclude_matches,
                                           this.default_include_matches);
        gPlacesViewMgr._uncheckAll();
        widgets.placeView_defaultView_menuitem.setAttribute('checked', 'true');
        this._updateCurrentUriViewPref("Default");
    },

    placeView_viewAll: function() {
        gPlacesViewMgr.view.setMainFilters("", "");
        gPlacesViewMgr._uncheckAll();
        widgets.placeView_viewAll_menuitem.setAttribute('checked', 'true');
        this._updateCurrentUriViewPref("");
    },
    
    placeView_selectCustomView: function(prefName) {
        try {
            var pref = filterPrefs.getPref(prefName);
            gPlacesViewMgr.view.setMainFilters(pref.getStringPref("exclude_matches"),
                                               pref.getStringPref("include_matches"));
            gPlacesViewMgr._uncheckAll();
            document.getElementById("places_custom_filter_" + prefName).setAttribute('checked', 'true');
            this._updateCurrentUriViewPref(prefName);
            return true;
        } catch(ex) {
            log.exception("Can't find prefName in menu: " + prefName + ":: " + ex + "\n");
            return false;
        }
    },

    placeView_customView: function() {
        // Use the same format as managing the list of servers.
        var resultObj = {needsChange:true};
        ko.windowManager.openDialog("chrome://places/content/manageViewFilters.xul",
                                    "_blank",
                                    "chrome,all,dialog=yes,modal=yes",
                                    resultObj);
        if (resultObj.needsChange) {
            ko.places.updateFilterViewMenu();
        }
    },
    
    placeView_updateView: function(viewName) {
        var defaultName = _bundle.GetStringFromName("default");
        if (viewName == null || viewName == defaultName) {
            this.placeView_defaultView();
            return defaultName;
        } else if (viewName == "*") {
            this.placeView_viewAll();
            return viewName;
        }
        else if (!filterPrefs.hasPref(viewName)) {
            // do default.
        } else {
            if (this.placeView_selectCustomView(viewName)) {
                return viewName;
            }
        }
        this.placeView_defaultView();
        return defaultName;
    },
    
    _uncheckAll: function() {
        widgets.placeView_defaultView_menuitem.setAttribute('checked', 'false');
        widgets.placeView_viewAll_menuitem.setAttribute('checked', 'false');
        widgets.placeView_customView_menuitem.setAttribute('checked', 'false');
        var node = document.getElementById("places_view_separator");
        while (node) {
            if (node.getAttribute('type') == 'checkbox') {
                node.setAttribute('checked', 'false');
            }
            node = node.nextElementSibling;
        }
    },
    
    onFilterKeypress : function(event) {
        try {
            if (event.keyCode == event.DOM_VK_TAB && !event.ctrlKey) {
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
                this.tree.focus();
                return;
            } else if (event.keyCode == event.DOM_VK_ESCAPE) {
                if (widgets.filterTextbox.value != '') {
                    widgets.filterTextbox.value = '';
                    this.updateFilter();
                    event.cancelBubble = true;
                    event.stopPropagation();
                    event.preventDefault();
                }
                return;
            }
        } catch (e) {
            dump("onFilterKeypress: exception: " + ex + "\n");
            log.exception(ex);
        }
    },

    updateFilter : function(event) {
        try {
            var textbox = widgets.filterTextbox;
            var filterPattern = textbox.value;
            try {
                this.view.setFilter(filterPattern);
                if (textbox.hasAttribute("error")) {
                    textbox.removeAttribute("error");
                    textbox.setAttribute("tooltiptext",
                                         textbox.getAttribute("basetooltiptext"));
                }
            } catch (ex) { // Means an invalid regex pattern.
                textbox.setAttribute("error", "true");
                textbox.setAttribute("tooltiptext",
                                     textbox.getAttribute("basetooltiptext") + " -- error in pattern: " + ex);
            }
            if (this.view.rowCount) {
                this.view.selection.select(0);
            }
        } catch(ex) {
            dump("updateFilter: exception: " + ex + "\n");
            log.exception(ex);
        }
    },
  __ZIP__: null
};

function ManagerClass() {
    this.currentPlace = null;
    this.currentPlaceIsLocal = true;
    this.lastHomePlace = null;
    this.lastLocalDirectoryChoice = null;
    this.lastRemoteDirectoryChoice = null;
    this.history_prevPlaces = [];
    this.history_forwardPlaces = [];
    this.history_maxPrevPlaceSize = 20;
    this.focused = false;
    this.controller = new ko.places.PlacesController();
    window.controllers.appendController(this.controller);
    this.copying = null;
    
    var gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);
    gObserverSvc.addObserver(this, 'visit_directory_proposed', false);
}

ManagerClass.prototype = {
    doOpenDirectory: function() {
        var defaultDir = null;
        var placeToTry = (this.currentPlaceIsLocal
                          ? this.currentPlace
                          : this.lastLocalDirectoryChoice);
        if (placeToTry) {
            var fileObj = Components.classes["@activestate.com/koFileEx;1"].
                          createInstance(Components.interfaces.koIFileEx);
            fileObj.URI = placeToTry;
            if (fileObj.isLocal) {
                defaultDir = fileObj.path;
            }
        }
        var dir = ko.filepicker.getFolder(defaultDir,
                          _bundle.GetStringFromName("directoryPickerPrompt"));
        if (dir == null) {
            return;
        }
        this._recordLastHomePlace();
        this.openDirectory(dir);
        ko.uilayout.ensureTabShown("places_tab");
    },
    
    doOpenRemoteDirectory: function() {
        // No need for defaults here?
        var currentUrl = this.lastRemoteDirectoryChoice;
        var fileBrowserRetvals = ko.filepicker.remoteFileBrowser(currentUrl, 
                                              "" /* defaultFilename */,
                                              Components.interfaces.nsIFilePicker.modeGetFolder);
        var uri = fileBrowserRetvals.file;
        if (!uri) {
            return;
        }
        this._recordLastHomePlace();
        var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
            getService(Components.interfaces.koIRemoteConnectionService);
        if (!RCService.isSupportedRemoteUrl(uri)) {
            ko.dialogs.alert(
               "Places internal error: browseForRemoteDir returned remote uri "
               + uri
               + ", but can't process it with the RemoteConnectionService");
            return;
        }
        this._enterMRU_Place(uri);
        this._setURI(uri, true);
        ko.uilayout.ensureTabShown("places_tab");
    },

    openDirectory: function(dir) {
        if (!osPathSvc.exists(dir)) {
            var prompt = _bundle.formatStringFromName('directoryDoesntExist.prompt',
                                                      [dir], 1);
            ko.dialogs.alert(prompt);
            return;
        }
        var uri = ko.uriparse.localPathToURI(dir);
        this._enterMRU_Place(uri);
        this._setURI(uri, true);
    },

    openURI : function(uri) {
        this._enterMRU_Place(uri);
        this._setURI(uri, true);
    },
 
    _checkForExistenceByURI: function(uri) {
        var fileObj = Components.classes["@activestate.com/koFileEx;1"].
        createInstance(Components.interfaces.koIFileEx);
        fileObj.URI = uri;
        if (fileObj.isLocal) {
            if (!osPathSvc.exists(fileObj.displayPath)) {
                var prompt = _bundle.formatStringFromName('cantFindPath.prompt',
                                                          [fileObj.displayPath],
                                                          1);
                ko.dialogs.alert(prompt);
                _placePrefs.getPref("mru_places").deletePref(idx);
                return false;
            }
        }
        return true;
    },

    loadRecentURI_byIndex: function(code, idx) {
        var uri;
        var checkedExistence = false;
        if (code == 'M') {
            var mruList = _placePrefs.getPref("mru_places");
            uri = mruList.getStringPref(idx);
            if (!this._checkForExistenceByURI(uri)) {
                return;
            }
            checkedExistence = true;
        } else if (code == 'P') {
            uri = this.history_prevPlaces[idx];
        } else if (code == 'F') {
            uri = this.history_forwardPlaces[idx];
        } else {
            var msg = "Don't know how to handle code '" + code + "'\n";
            log.error(msg);
            dump(msg);
            return;
        }
        if (!checkedExistence && !this._checkForExistenceByURI(uri)) {
            return;
        }
        this._enterMRU_Place(uri);
        this._setURI(uri, true);
    },

    _enterMRU_Place: function(destination_uri) {
        if (!this.currentPlace) {
            return;
        }
        var uri = gPlacesViewMgr.view.getURIForRow(0);
        var mruList;
        if (_placePrefs.hasPref("mru_places")) {
            mruList = _placePrefs.getPref("mru_places");
            var idx = mruList.findStringPref(uri);
            if (idx == 0) {
                // Do nothing: it's at the top.
            } else if (idx > 0) {
                // Move it to the top
                mruList.deletePref(idx);
                mruList.insertStringPref(0, uri);
            } else {
                // Add it
                var length = mruList.length;
                //TODO: Give this its own pref
                var maxMRUPlaces;
                try {
                    maxMRUPlaces = _globalPrefs.getLongPref("mruProjectSize");
                } catch(ex) {
                    maxMRUPlaces = 10;
                }
                while (length >= maxMRUPlaces) {
                    mruList.deletePref(length - 1);
                    length--;
                }
                mruList.insertStringPref(0, uri);
            }
        } else {
            mruList = Components.classes["@activestate.com/koOrderedPreference;1"].
            createInstance(Components.interfaces.koIOrderedPreference);
            mruList.appendStringPref(uri);
            _placePrefs.setPref("mru_places", mruList);
        }
        this.pushHistoryInfo(uri, destination_uri);
    },

    _recordLastHomePlace: function() {
        if (this.currentPlace) {
            this.lastHomePlace = this.currentPlace;
            if (this.currentPlaceIsLocal) {
                this.lastLocalDirectoryChoice = this.currentPlace;
            } else {
                this.lastRemoteDirectoryChoice = this.currentPlace;
            }
        }
    },
    
    _setURI: function(uri, setThePref) {
        var file = Components.classes["@activestate.com/koFileEx;1"].
                createInstance(Components.interfaces.koIFileEx);
        file.URI = uri
        this.currentPlaceIsLocal = file.isLocal; 
        gPlacesViewMgr.view.currentPlace = this.currentPlace = uri;
        widgets.rootPath.value = (file.scheme == "file" ? file.displayPath : uri);
        widgets.rootPath.setAttribute('class', 'someplace');
        window.setTimeout(window.updateCommands, 1,
                          "current_place_opened");
        if (setThePref) {
            _placePrefs.setStringPref(window._koNum, uri);
        }
        var viewName = null;
        var prefSet;
        if (uriSpecificPrefs.hasPref(uri)) {
            var prefSet = uriSpecificPrefs.getPref(uri);
            try { viewName = prefSet.getStringPref('viewName')} catch(ex) {}
            var finalViewName = gPlacesViewMgr.placeView_updateView(viewName);
            if (finalViewName != viewName) {
                prefSet.setStringPref('viewName', finalViewName)
            }
        } else {
            var finalViewName = gPlacesViewMgr.placeView_updateView(null);
            prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
            prefSet.setStringPref('viewName', finalViewName);
            uriSpecificPrefs.setPref(uri, prefSet);
        }
    },

    toggleRebaseFolderByIndex: function(index) {
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        if (index > 0) {
            this._enterMRU_Place(uri);
            gPlacesViewMgr.view.currentPlace = this.currentPlace = uri;
        } else if (index == 0) {
            // Get the home URI back
            var lastSlashIdx = uri.lastIndexOf("/");
            if (lastSlashIdx == -1) return;
            var parent_uri = uri.substr(0, lastSlashIdx);
            this._enterMRU_Place(parent_uri);
            gPlacesViewMgr.view.currentPlace = this.currentPlace = parent_uri;
            if (!gPlacesViewMgr.view.isContainerOpen(0)) {
                // Should be done as an async callback.
                gPlacesViewMgr.view.toggleOpenState(0);
                setTimeout(gPlacesViewMgr.view.selectURI, 1000, uri);
            } else {
                gPlacesViewMgr.view.selectURI(uri);
            }
        }
    },

    rebaseToDirByURI: function(uri, child_uri) {
        if (typeof(child_uri) == "undefined") child_uri = null;
        this.pushHistoryInfo(child_uri, uri);
        gPlacesViewMgr.view.currentPlace = this.currentPlace = uri;
        if (child_uri) gPlacesViewMgr.view.selectURI(child_uri)
    },

    /* doCutPlaceItem
     * This is a bit weird until we work out how to do it.
     * Marking an item with 'cut' does nothing, until we do
     * a paste on it, and then it gets moved.
     * Maybe at some point we can color the icon differently...
     *
     * Best would be to actually remove it from the folder, but
     * then we really need full undo to give users a better experience.
     */
    doCutPlaceItem: function() {
        this.copying = false;
        this._selectCurrentItem();
    },

    doCopyPlaceItem: function() {
        this.copying = true;
        this._selectCurrentItem();
    },

    _selectCurrentItem: function() {
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        xtk.clipboard.setText(uri);
        window.setTimeout(window.updateCommands, 1, "clipboard");
    },

    doPastePlaceItem: function() {
        var srcURI = xtk.clipboard.getText();
        var srcIndex = gPlacesViewMgr.view.getRowIndexForURI(srcURI);
        if (srcIndex == -1) {
            //XXX: Watch out for remote files.
            ko.dialogs.alert("Can't find file "
                             + ko.uriparse.URIToLocalPath(srcURI)
                             + " in the current tree");
            return;
        }
        var index = gPlacesViewMgr.view.selection.currentIndex;
        try {
            gPlacesViewMgr._finishFileCopyOperation(srcIndex, index,
                                                    this.copying);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
        this.copying = null;
        window.setTimeout(window.updateCommands, 1, "clipboard");
    },

    // uncomment this if we want to have more control over how the fields are initialized
    //_waitForProperty: function(targetObject, propName, waitTime, timeLeft, workerFunc) {
    //    if (propName in targetObject && targetObject[propName]) {
    //        workerFunc();
    //        return;
    //    }
    //    timeLeft -= waitTime;
    //    if (timeLeft <= 0) {
    //        return;
    //    }
    //    setTimeout(arguments.callee, waitTime,
    //               targetObject, propName, waitTime, timeLeft, workerFunc);
    //},

    doFindInPlace: function() {
        if (!this.currentPlaceIsLocal) {
            return;
        }
        //var findWindow = ko.launch.find(null, true);
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        var isFolder = gPlacesViewMgr.view.isContainer(index);
        var path = isFolder ? ko.uriparse.displayPath(uri) : ko.uriparse.dirName(uri) ;
        dump("doFindInPlace: let's launch findInFiles(" + path + ")\n");
        ko.launch.findInFiles(null, path);
        //this._waitForProperty(findWindow, 'widgets', 50, 1000,
        //    function() {
        //        var fwWidgets = findWindow.widgets;
        //        fwWidgets.search_in_menu.value = 'files';
        //        findWindow.update('search-in');
        //        fwWidgets.dirs.value = path;
        //        fwWidgets.search_in_subdirs.checked = isFolder;
        //    });
    },

    doReplaceInPlace: function() {
        if (!this.currentPlaceIsLocal) {
            return;
        }
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        var isFolder = gPlacesViewMgr.view.isContainer(index);
        var path = isFolder ? ko.uriparse.displayPath(uri) : ko.uriparse.dirName(uri) ;
        ko.launch.replaceInFiles(null, null, path);
    },

    doShowInFinder: function() {
        if (!this.currentPlaceIsLocal) {
            return;
        }
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        var path = ko.uriparse.displayPath(uri);
        var sysUtilsSvc = Components.classes["@activestate.com/koSysUtils;1"].
                    getService(Components.interfaces.koISysUtils);
        sysUtilsSvc.ShowFileInFileManager(path);
    },

    _doRenameItem_file_exists_re : /renameItem failure: file (.*) exists/,

    _doRenameItem_dir_exists_re: /renameItem: invalid operation: you can\'t rename existing directory: (.*)/,

    doRenameItem: function() {
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        var newname = ko.dialogs.renameFileWrapper(ko.uriparse.baseName(uri));
        if (!newname) return;
        try {
            gPlacesViewMgr.view.renameItem(index, newname, false);
        } catch(ex) {
            var m = this._doRenameItem_file_exists_re.exec(ex.message);
            var title;
            if (m) {
                var prompt = _bundle.formatStringFromName('FileExistsOverwrite.prompt',
                                                          [m[1]], 1);
                var response = _bundle.GetStringFromName("Yes.label");
                title = _bundle.GetStringFromName("newFileExists.message");
                var result = ko.dialogs.yesNo(prompt, response, null, title);
                if (result == response) {
                    try {
                        gPlacesViewMgr.view.renameItem(index, newname, true);
                    } catch(ex2) {
                        dump("doRenameItem: " + ex2 + "\n");
                    }
                }
            } else {
                m = this._doRenameItem_dir_exists_re.exec(ex.message);
                if (m) {
                    title = _bundle.GetStringFromName("fileRenameFailed.message");
                    var prompt = _bundle.formatStringFromName(
                        'cantRenameOverExistingDirectory.template',
                        [m[1]], 1);
                    ko.dialogs.alert(prompt, null, title);
                } else {
                    dump("doRenameItem: " + ex + "\n");
                }
            }
        }
    },

    doDeletePlace: function() {
        var index = gPlacesViewMgr.view.selection.currentIndex;
        if (index == 0) {
            ko.dialogs.alert(_bundle.GetStringFromName("cantDeleteFullTreeView"));
            return;
        }
        var deleteContents = false;
        var prompt;
        var response = _bundle.GetStringFromName("no");
        var text = null;
        var title;
        if (gPlacesViewMgr.view.itemIsNonEmptyFolder(index)) {
            //XXX: Adjust when we handle multiple selected items
            prompt = _bundle.formatStringFromName(
                      "deleteNonEmptyFolderPrompt",
                      [gPlacesViewMgr.view.getCellText(index, {id:'name'})],
                      1);
            title = _bundle.GetStringFromName("aboutToDeleteNonEmptyFolder");
            deleteContents = true;
        } else {
            var peFolderBundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/project/peFolder.properties");
            prompt = peFolderBundle.GetStringFromName(
                      "doYouWantToRemoveTheItemYouHaveSelected");
            title = peFolderBundle.GetStringFromName("deleteSelectedItems");
        }
        if (!this.currentPlaceIsLocal) {
            prompt += ("  "
                       + _bundle.GetStringFromName("remoteDeleteNotReversible"));
        }
        var response = ko.dialogs.yesNo(prompt, response, text, title);
        if (response != _bundle.GetStringFromName("yes")) {
            return;
        }
        try {
            gPlacesViewMgr.view.deleteItem(index, deleteContents);
        } catch(ex) {
            alert(ex);
            return;
        }
    },
    
    initialize: function() {
        var uri = null;
        try {
            uri = _globalPrefs.getPref("places").getStringPref(window._koNum);
        } catch(ex) {
        }
        if (!uri) {
            const nsIDirectoryServiceProvider = Components.interfaces.nsIDirectoryServiceProvider;
            const nsIDirectoryServiceProvider_CONTRACTID = "@mozilla.org/file/directory_service;1";
            try {
                var dirServiceProvider = Components.classes[nsIDirectoryServiceProvider_CONTRACTID]
                    .getService(nsIDirectoryServiceProvider);
                var homeDir = dirServiceProvider.getFile("Home", {});
                if (!homeDir) {
                    if (navigator.platform.toLowerCase().substr(0, 3)
                        == "win") {
                        homeDir = "C:\\";
                    } else {
                        homeDir = "/";
                    }
                } else {
                    homeDir = homeDir.path;
                }
                uri = ko.uriparse.localPathToURI(homeDir);
            } catch(e) {
                log.debug("ManagerClass.initialize on homeDir: " + e+ "\n");
            }
        }
        if (uri) {
            try {
                this._setURI(uri, false);
            } catch(ex) {}
        }
        try {
            var placesPrefs = _globalPrefs.getPref("places");
            var name_list = ['lastLocalDirectoryChoice', 'lastRemoteDirectoryChoice', 'lastHomePlace'];
            name_list.map(function(name) {
                try {
                    this[name] = placesPrefs.getStringPref(name);
                } catch(ex) {
                    if (placesPrefs.hasStringPref(name)) {
                        log.exception("placesPrefs.hasStringPref('"
                                      + name
                                      + "'), but got exception: "
                                      + ex);
                    }
                }
            }, this);
                    
            this.history_prevPlaces = [];
            this.history_forwardPlaces = [];
            if (placesPrefs.hasPref('history_prevPlaces')) {
                var prevPlace_prefs = placesPrefs.getPref('history_prevPlaces');
                var len = prevPlace_prefs.length;
                for (var i = 0; i < len; ++i) {
                    this.history_prevPlaces.push(prevPlace_prefs.getStringPref(i));
                }
            }
            if (placesPrefs.hasPref('history_forwardPlaces')) {
                var forwardPlace_prefs = placesPrefs.getPref('history_forwardPlaces');
                var len = forwardPlace_prefs.length;
                for (var i = 0; i < len; ++i) {
                    this.history_forwardPlaces.push(forwardPlace_prefs.getStringPref(i));
                }
                setTimeout(window.updateCommands, 100, 'place_history_changed');
            }
        } catch(ex) {
            dump("Error init'ing the viewMgrClass (2): " + ex + "\n");
        }
    },
    
    finalize: function() {
        var placesPrefs = _globalPrefs.getPref("places");
        var prevPlace_prefs = Components.classes["@activestate.com/koOrderedPreference;1"].
            createInstance(Components.interfaces.koIOrderedPreference);
        this.history_prevPlaces.map(function(uri) {
                prevPlace_prefs.appendStringPref(uri);
            });
        placesPrefs.setPref('history_prevPlaces', prevPlace_prefs);
        var forwardPlace_prefs = Components.classes["@activestate.com/koOrderedPreference;1"].
            createInstance(Components.interfaces.koIOrderedPreference);
        this.history_forwardPlaces.map(function(uri) {
                forwardPlace_prefs.appendStringPref(uri);
            });
        placesPrefs.setPref('history_forwardPlaces', forwardPlace_prefs);
        this._recordLastHomePlace();
        var name_list = ['lastLocalDirectoryChoice', 'lastRemoteDirectoryChoice', 'lastHomePlace'];
        name_list.map(function(name) {
            if (this[name]) {
                placesPrefs.setStringPref(name, this[name]);
            } else {
                placesPrefs.deletePref(name);
            }
        }, this);
        this._enterMRU_Place(null);
        this.cleanPrefs();
        this.currentPlace = null;
        window.controllers.removeController(this.controller);
        this.controller = null;
        var gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
        gObserverSvc.removeObserver(this, 'visit_directory_proposed');
    },

    can_goPreviousPlace: function() {
        return this.history_prevPlaces.length > 0;
    },

    goPreviousPlace: function() {
        if (this.history_prevPlaces.length == 0) {
            return;
        }
        var targetURI = this.history_prevPlaces.pop();
        if (this.currentPlace) {
            this.history_forwardPlaces.unshift(this.currentPlace);
        }
        this._setURI(targetURI);
        window.updateCommands('place_history_changed');
    },

    can_goNextPlace: function() {
        return this.history_forwardPlaces.length > 0;
    },

    goNextPlace: function() {
        if (this.history_forwardPlaces.length == 0) {
            return;
        }
        var targetURI = this.history_forwardPlaces.shift();
        if (this.currentPlace) {
            this.history_prevPlaces.push(this.currentPlace);
        }
        this._setURI(targetURI, true);
        window.updateCommands('place_history_changed');
    },

    can_undoTreeOperation: function() {
        var res = gPlacesViewMgr.view.canUndoTreeOperation();
        return res;
    },

    undoTreeOperation: function() {
        try {
            gPlacesViewMgr.view.do_undoTreeOperation();
            window.updateCommands('did_tree_operation');
        } catch(ex) {
            alert(ex);
        }
    },

    init_popup_menu_recent_locations: function(event) {
        var popupMenu = event.target;
        while (popupMenu.hasChildNodes()) {
            popupMenu.removeChild(popupMenu.lastChild);
        }
        var menuitem;
        if (!this.history_forwardPlaces.length
            && !this.history_forwardPlaces.length
            && !this.currentPlace) {
            menuitem = document.createElement("menuitem");
            menuitem.label = "No places have been visited yet";
            menuitem.disabled = true;
            popupMenu.appendChild(menuitem);
            return;
        }
        var currentURI = null;
        try {
            currentURI = gPlacesViewMgr.view.getURIForRow(0) ;
        } catch(ex) {}
        if (!currentURI) currentURI = this.currentPlace;
        var blocks = [this.history_forwardPlaces,
                      [currentURI],
                      this.history_prevPlaces];
        var codes = ['F', 'C', 'B'];
        var file = Components.classes["@activestate.com/koFileEx;1"].
                createInstance(Components.interfaces.koIFileEx);
        for (var i = 0; i < blocks.length; ++i) {
            var block = blocks[i];
            var code = codes[i];
            for (var j = block.length - 1; j >= 0; --j) {
                var uri = block[j];
                if (!uri) {
                    continue;
                }
                menuitem = document.createElement("menuitem");
                menuitem.setAttribute("crop", "center");
                file.URI = uri;
                var label = (file.scheme == "file" ? file.displayPath : uri);
                menuitem.setAttribute('label', label);
                if (code == 'C') {
                    menuitem.setAttribute("class", "primary_menu_item");
                } else {
                    menuitem.setAttribute("class", "menuitem_mru");
                }
                menuitem.setAttribute('oncommand',
                                      ('ko.places.manager.goSelectedPlace("'
                                       + code
                                       + '", '
                                       + j
                                       + ');'));
                popupMenu.appendChild(menuitem);
            }
        }
    },

    init_popup_parent_directories: function(event) {
        var popupMenu = event.target;
        while (popupMenu.hasChildNodes()) {
            popupMenu.removeChild(popupMenu.lastChild);
        }
        var menuitem;
        var currentURI = this.currentPlace;
        // Just use pattern-matching to tear apart the URI and put it back
        var menuitem;
        var m = /(^[\w\-\+\.]+:\/\/.*?\/)(.*)/.exec(currentURI);
        if (!m) {
            menuitem = document.createElement("menuitem");
            menuitem.setAttribute('label',
                                  _bundle.GetStringFromName("noPartsFound"));
            menuitem.setAttribute('disabled', 'true');
            popupMenu.appendChild(menuitem);
            return;
        }
        var uriLeader = m[1];
        var pathPart = m[2];
        var originalParts = pathPart.split("/")
        var numParts = originalParts.length;
        var parts;
        if (!pathPart.length) {
            parts = ['/'];
        } else {
            parts = pathPart.split("/");
            if (parts[0][1] == ':') {
                parts[0] += "\\";
            } else {
                parts.unshift("/");
            }
        }
        var i = 0;
        var buildingURI;
        var selectedItem = null;
        parts.reverse();
        parts.map(function(partName) {
                menuitem = document.createElement("menuitem");
                menuitem.setAttribute('label', unescape(partName));
                if (i == 0) {
                    menuitem.setAttribute("class", "primary_menu_item");
                    selectedItem = menuitem;
                } else {
                    menuitem.setAttribute("class", "menuitem_mru");
                }
                buildingURI = uriLeader + originalParts.slice(0, numParts - i).join("/");
                if (i == numParts - 1) {
                    buildingURI += "/";
                }
                menuitem.setAttribute('oncommand',
                                      ('ko.places.manager.openURI("'
                                       + buildingURI
                                       + '");'));
                popupMenu.appendChild(menuitem);
                i += 1;
            });
        if (selectedItem) {
            popupMenu.selectedItem = selectedItem;
        }
    },

    goSelectedPlace: function(blockCode, index) {
        var uri, partsToShift;
        if (blockCode == 'C') {
            return; // Nothing to do
        } else if (blockCode == 'B') {
            uri = this.history_prevPlaces[index];
            this.history_prevPlaces.splice(index, 1);
            partsToShift = this.history_prevPlaces.splice(index);
            if (this.currentPlace) {
                partsToShift.push(this.currentPlace);
            }
            if (partsToShift.length) {
                this.history_forwardPlaces = partsToShift.concat(this.history_forwardPlaces);
            }
        } else {
            var uri = this.history_forwardPlaces[index];
            this.history_forwardPlaces.splice(index, 1);
            if (this.currentPlace) {
                this.history_prevPlaces.push(this.currentPlace);
            }
            if (index > 0) {
                partsToShift = this.history_forwardPlaces.splice(0, index);
                this.history_prevPlaces = this.history_prevPlaces.concat(partsToShift);
            }
        }
        window.updateCommands('place_history_changed');
        this._setURI(uri, true);
    },

    pushHistoryInfo: function(anchor_uri, destination_uri) {
        // We are about to leave anchor_uri, and move to destination_uri
        // See kd-0247#Updating the Previous/Forward Place History for
        // design notes for the policy used here.
        
        var anchor_prev_idx = this.history_prevPlaces.indexOf(anchor_uri);
        var anchor_fwd_idx = this.history_forwardPlaces.indexOf(anchor_uri);
        // These should both be -1, but pull out just in case.
        if (anchor_prev_idx >= 0) {
            this.history_prevPlaces.splice(anchor_prev_idx, 1);
        }
        if (anchor_fwd_idx >= 0) {
            this.history_forwardPlaces.splice(anchor_prev_idx, 1);
        }
        var dest_prev_idx = this.history_prevPlaces.indexOf(destination_uri);
        var dest_fwd_idx = this.history_forwardPlaces.indexOf(destination_uri);
        if (dest_prev_idx >= 0) {
            this.history_prevPlaces.splice(dest_prev_idx, 1);
            if (dest_fwd_idx >= 0) {
                // Shouldn't happen: target was in both lists.
                this.history_forwardPlaces.splice(dest_fwd_idx, 1);
            }
        } else if (this.history_forwardPlaces.length) {
            if (dest_fwd_idx == -1) {
                // Copy all of them
                dest_fwd_idx = this.history_forwardPlaces.length;
            }
            for (i = 0; i < dest_fwd_idx; i++) {
                this.history_prevPlaces.push(this.history_forwardPlaces[i]);
            }
            this.history_forwardPlaces.splice(0, dest_fwd_idx + 1);
        }
        if (anchor_uri) {
            this.history_prevPlaces.push(anchor_uri);
        }
        if (this.history_prevPlaces.length > this.history_maxPrevPlaceSize) {
            this.history_prevPlaces.splice(0,
                           (this.history_prevPlaces.length
                            - this.history_maxPrevPlaceSize));
        }
        window.updateCommands('place_history_changed');
    },

    /*
            // Remove others
            while(true) {
                dest_prev_idx = this.history_prevPlaces.indexOf(destination_uri);
                if (dest_prev_idx == -1) break;
                this.history_prevPlaces.splice(dest_prev_idx, 1);
            }                
            // Remove others
            while(true) {
                dest_fwd_idx = this.history_forwardPlaces.indexOf(destination_uri);
                if (dest_fwd_idx == -1) break;
                this.history_forwardPlaces.splice(dest_fwd_idx, 1);
            }
    */
    cleanPrefs: function() {
        var mru_places = _placePrefs.getPref("mru_places");
        var ids = {};
        uriSpecificPrefs.getPrefIds(ids, {});
        ids = ids.value;
        ids.map(function(uri) {
            if (mru_places.findStringPref(uri) == -1) {
                uriSpecificPrefs.deletePref(uri);
            }
        })
    },

    'observe': function(cancelQuit, topic, data) {
        if (topic == 'visit_directory_proposed') {
            cancelQuit.QueryInterface(Components.interfaces.nsISupportsPRBool);
            if (cancelQuit.data) {
               // someone else handled it (nothing else in core komodo)
            } else {
                cancelQuit.data = true; // we handled it.
                ko.places.manager.openDirectory(data);
                ko.uilayout.ensureTabShown("places_tab");
                gPlacesViewMgr.view.selection.select(0);
            }
        }
    },
    __ZIP__: null
};

this._instantiateRemoteConnectionService = function() { 
    // From publish-dialog.js
    // Have to initialize these services before we launch publishing -
    // otherwise there will be erros and/or a crash when trying to get these
    // services from inside the publishing code (likely related to
    // threading).
    var rfSvc = Components.classes["@activestate.com/koRemoteConnectionService;1"].
    getService(Components.interfaces.koIRemoteConnectionService);
    var loginmanager = Components.classes["@mozilla.org/login-manager;1"].
    getService(Components.interfaces.nsILoginManager);
    var logins = {};
    loginmanager.getAllLogins(logins);
};

// In these functions 'this' is top (window)
this.onLoad = function places_onLoad() {
    osPathSvc = (Components.classes["@activestate.com/koOsPath;1"]
                 .getService(Components.interfaces.koIOsPath));
    // Init the prefs
    _globalPrefs = (Components.classes["@activestate.com/koPrefService;1"].
                   getService(Components.interfaces.koIPrefService).prefs);
    if (!_globalPrefs.hasPref("places")) {
        //dump("global prefs has no places\n");
        _globalPrefs.setPref("places",
                             Components.classes["@activestate.com/koPreferenceSet;1"].createInstance());
    }
    _placePrefs = _globalPrefs.getPref("places");
    if (!_placePrefs.hasPref('filters')) {
        filterPrefs = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        //dump("global/places prefs has no filters\n");
        _placePrefs.setPref("filters", filterPrefs);
    } else {
        filterPrefs = _placePrefs.getPref("filters");
    }
    var defaultName = _bundle.GetStringFromName("default");
    if (!filterPrefs.hasPref(defaultName)) {
        //dump("global/places/filters prefs has no " + defaultName + "\n");
        var prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        prefSet.setStringPref("exclude_matches", DEFAULT_EXCLUDE_MATCHES);
        prefSet.setStringPref("include_matches", DEFAULT_INCLUDE_MATCHES);
        prefSet.setBooleanPref("readonly", true);
        filterPrefs.setPref(defaultName, prefSet);
    }
    if (!_placePrefs.hasPref('current_filter_by_uri')) {
        uriSpecificPrefs = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        _placePrefs.setPref('current_filter_by_uri', uriSpecificPrefs);
    } else {
        uriSpecificPrefs = _placePrefs.getPref('current_filter_by_uri');
    }
    
    var this_ = ko.places;
    this_._instantiateRemoteConnectionService();
    this_.viewMgr = gPlacesViewMgr = new viewMgrClass();
    this_.viewMgr.initialize();
    this_.manager = new ManagerClass();
    setTimeout(function() {
            this_.manager.initialize();
        }, 5000);
    widgets.rootPath = document.getElementById("place-view-rootPath");
    widgets.filterTextbox = document.getElementById("places-filter-textbox");
    widgets.placeView_defaultView_menuitem =
        document.getElementById("placeView_defaultView");
    widgets.placeView_viewAll_menuitem =
        document.getElementById("placeView_viewAll");
    widgets.placeView_customView_menuitem =
        document.getElementById("placeView_customView");
    this_.updateFilterViewMenu();
};

this.onUnload = function places_onUnload() {
    var this_ = ko.places;
    this_.manager.finalize();
    this_.viewMgr.finalize();
    this_.manager = this_._viewMgr = null;
};

this.updateFilterViewMenu = function() {
    // Find which node is checked.  Then update the menu, maintaining
    // the checked item.  If it was deleted, make the default view the
    // checked one.
    var menupopup = document.getElementById("placeView_toolsPopup");
    var childNodes = menupopup.childNodes;
    for (var idx = menupopup.childElementCount - 1; idx >= 0; --idx) {
        var node = childNodes[idx];
        if (!node.getAttribute('keep')) {
            menupopup.removeChild(node);
        }
    }
    var ids = {};
    filterPrefs.getPrefIds(ids, {});
    ids = ids.value;
    var defaultName = _bundle.GetStringFromName("default");
    var sep = document.getElementById("places_manage_view_separator");
    var menuitem;
    ids.map(function(prefName) {
        if (prefName == defaultName) {
            // It's already there.
            return;
        }
        menuitem = document.createElementNS(XUL_NS, 'menuitem');
        menuitem.setAttribute("id", "places_custom_filter_" + prefName);
        menuitem.setAttribute('label',  prefName);
        menuitem.setAttribute("type", "checkbox");
        menuitem.setAttribute("checked", "false");
        menuitem.setAttribute("oncommand", "ko.places.viewMgr.placeView_selectCustomView('" + prefName + "');");
        menupopup.insertBefore(menuitem, sep);    
    });
};

}).apply(ko.places);
