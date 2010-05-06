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
    this.startingLevel = -1;
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
    
    refreshViewByIndex: function(index) {
        // pyView.refreshView(-1) ==> pyView.refreshFullTreeView()
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
    allowed_click_nodes: ["places-files-tree-body", "place-view-rootPath-icon"],
    initFilesContextMenu: function(event) {
        var clickedNodeId = event.explicitOriginalTarget.id;
        if (this.allowed_click_nodes.indexOf(clickedNodeId) == -1) {
            if (clickedNodeId == "places-scc-popup") {
                // quietly return
                return false;
            }
            dump("No context menu when clicking on "
                 + event.explicitOriginalTarget.id
                 + "\n");
            return false;
        }
        //gEvent = event;
        /*
         * Menus:
         *   *Folder: Rebase (tree folders only)
         *   *Folder: Refresh View
         *----------------
         *   Cut   (tree items only)
         *   Copy  
         *   Paste (*File: disabled, *Folder: always enabled)
         *   Undo (undo a move)
         *----------------
         *   Find... (should be in this file|folder)
         *   Replace... (same)
         *   Show in {Explorer | File Manager | Finder}
         *   Rename...  (tree items only)
         *   Refresh Status
         *----------------
         *   [Source Control | Source Control on Contents] ...
         *----------------
         *   Delete (tree items only)
         *   New File...
         *   New Folder...
         *----------------
         *   Properties (*Folder:disabled)
         */
        var index;
        var isRootNode;
        if (clickedNodeId == "place-view-rootPath-icon") {
            index = -1;
            isRootNode = true;
        } else {
            index = this._currentRow(event);
            isRootNode = (index == -1);
        }
        var isFolder = index == -1 ? true : this.view.isContainer(index);
        var popupmenu = event.target;
        var nodes = popupmenu.childNodes;
        var firstMenuItem = nodes[0];
        var firstFolderMenuItemId_rebase = "placesContextMenu_folder_rebase";
        var firstFileMenuItemId_fileOpen = "placesContextMenu_file_open";
        var firstFolderMenuItemId_refreshView = "placesContextMenu_folder_refresh_view";
        var node, i = 0;
        var isLocal = ko.places.manager.currentPlaceIsLocal;
        // Do global stuff here: remove nodes from last run, and
        // handle blanket disable/enabling
        var disableAll = (isRootNode
                          && widgets.rootPath.getAttribute('class') ==  'noplace');
        while (!!(node = nodes[i])) {
            if (node.getAttribute("keep") != "true") {
                popupmenu.removeChild(node);
            } else {
                if (disableAll) {
                    node.setAttribute("disabled", "true");
                } else {
                    node.removeAttribute("disabled");
                }
                i++;
            }
        }
        if (disableAll) {
            return true;
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
        menuitem = document.getElementById("placesContextMenu_undo");
        if ((isFolder || isRootNode)
            && ko.places.manager.can_undoTreeOperation()) {
            menuitem.removeAttribute("disabled");
        } else {
            menuitem.setAttribute("disabled", "true");
        }
        if (isFolder) {
            var disable_item = !isRootNode && !this.view.isContainerOpen(index);
            menuitem = this._makeMenuItem(firstFolderMenuItemId_refreshView,
                                          _bundle.GetStringFromName("refreshView.label"),
                                          ("gPlacesViewMgr.refreshViewByIndex("
                                           + index // -1 ok
                                           + ");"));
            if (disable_item) {
                menuitem.setAttribute("disabled", "true");
            }
            newMenuItemNode = popupmenu.insertBefore(menuitem, firstCommonNode);
            if (!isRootNode) {
                var bundle_label = "rebaseFolder.label";
                menuitem = this._makeMenuItem(firstFolderMenuItemId_rebase,
                                              _bundle.GetStringFromName(bundle_label),
                                              ("gPlacesViewMgr.rebaseByIndex("
                                               + index
                                               + ");"));
                popupmenu.insertBefore(menuitem, newMenuItemNode);
            }
            menuitem = document.getElementById("placesContextMenu_newFile");
            menuitem.removeAttribute("disabled");
            menuitem.setAttribute("oncommand",
                                  ("gPlacesViewMgr.addNewFile("
                                   + index // -1 is handled for isRootNode
                                    + ");"));
            menuitem = document.getElementById("placesContextMenu_newFolder");
            menuitem.removeAttribute("disabled");
            menuitem.setAttribute("oncommand",
                                  ("gPlacesViewMgr.addNewFolder("
                                   + index // -1 is handled for isRootNode
                                    + ");"));
        } else {
            if (!isRootNode) {
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
            document.getElementById("placesContextMenu_newFile").setAttribute("disabled", 'true');
            document.getElementById("placesContextMenu_newFolder").setAttribute("disabled", 'true');
        }
        var disabledRootNodeNames = ["placesContextMenu_rename",
                                     "placesContextMenu_delete",
                                     "placesContextMenu_cut",
                                     "placesContextMenu_rename"];
        for (var nonRootNodeName, i = 0;
             nonRootNodeName = disabledRootNodeNames[i]; ++i) {
            node = document.getElementById(nonRootNodeName);
            if (isRootNode) {
                node.setAttribute("disabled", "true");
            } else {
                node.removeAttribute("disabled");
            }
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

    doStartDrag: function(event, tree) {
        var index = this._currentRow(event);
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
        this.startingLevel = this.view.getLevel(this.startingIndex);
        if (event.ctrlKey) {
            dt.effectAllowed = this.originalEffect = "copy";
            this.copying = true;
        } else {
            dt.effectAllowed = this.originalEffect = "move";
            this.copying = false;
        }
    },

    doDragEnter: function(event, tree) {
        return this._checkDrag(event);
    },

    doDragOver: function(event, tree) {
        return this._checkDrag(event);
    },

    doDragEnterRootNode: function(event, rootNode) {
        return this._checkDragToRootNode(event);
    },

    doDragOverRootNode: function(event, tree) {
        return this._checkDragToRootNode(event);
    },
    
    _checkDragSource: function(event) {
        if (!event.dataTransfer.types.contains("application/x-moz-file")) {
            if (this.complainIfNotAContainer) {
                log.debug("not a file data-transfer\n");
                this.complainIfNotAContainer = false;
            }
            return false;
        }
        return true;
    },    
    _checkDragToRootNode: function(event) {
        var inDragSource = ko.places.manager.currentPlace && this._checkDragSource(event);
        if (inDragSource) {
            inDragSource = this.startingLevel > 0;
        }
        event.dataTransfer.effectAllowed = inDragSource ? this.originalEffect : "none";
        
    },
    _checkDrag: function(event) {
        var inDragSource = this._checkDragSource(event);
        var index = this._currentRow(event);
        var retVal = false;
        if (!inDragSource) {
            // do nothing more
        } else if (index == this.startingIndex) {
            // Can't drag onto oneself
        } else if (!this.view.isContainer(index)) {
            //if (this.complainIfNotAContainer) {
            //    log.debug("Not a container\n");
            //    this.complainIfNotAContainer = false;
            //}
        } else if (this.startingLevel > 0
                   && index == this.view.getParentIndex(this.startingIndex)) {
            // Can't drop into the parent
            // If the starting index is 0, we can drop it anywhere on the tree.
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
            this._finishFileCopyOperation(from_index, {index:to_index}, this.copying);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
        this.startingIndex = -1;
        return true;
    },

    doDropOnRootNode : function(event, tree) {
        if (this.startingIndex == -1) {
            log.debug("doDropOnRootNode: startingIndex: -1: don't do anything");
            return false;
        }
        var from_index = this.startingIndex;
        try {
            var uri = ko.places.manager.currentPlace;
            if (!uri) {
                return false;
            }
            this._finishFileCopyOperation(from_index, {uri:uri}, this.copying);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
        this.startingIndex = -1;
        event.stopPropagation();
        event.cancelBubble = true;
        event.preventDefault();
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

    _finishFileCopyOperation: function(from_index, to_object, copying) {
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
                    return false;
                }
            }
        }
        var res;
        var to_index = null, to_uri = null;
        if ('index' in to_object) {
            to_index = to_object.index;
            res = this.view.treeOperationWouldConflict(from_index,
                                                       to_index,
                                                       copying,
                                                       srcFileInfo,
                                                       targetFileInfo);
        } else {
            to_uri = to_object.uri;
            res = this.view.treeOperationWouldConflictByURI(from_index,
                                                            to_uri,
                                                            copying,
                                                            srcFileInfo,
                                                            targetFileInfo);
        }
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
                    if (to_index) {
                        this.view.doTreeCopyWithDestName(from_index, to_index,
                                                         newPath, callback);
                    } else {
                        this.view.doTreeCopyWithDestNameAndURI(from_index, to_uri,
                                                         newPath, callback);
                    }
                    return true;
                } finally {
                    if (conn) {
                        conn.close();
                    }
                }
            }
        }
        if (!copying) {
            if (!to_uri) {
                to_uri = this.view.getURIForRow(to_index);
            }
            callback = {
            callback: function(result, data) {
                    if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                        ko.dialogs.alert(data);
                    } else {
                        // Update the Komodo view
                        if (from_view) {
                            g_from_view = from_view;
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
        if (to_index !== null) {
            this.view.doTreeOperation(from_index, to_index,
                                      copying, callback);
        } else {
            this.view.doTreeOperationToRootNode(from_index, to_uri,
                                                copying, callback);
        }            
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
        _globalPrefs.getPref("places").setStringPref("sortDirection",
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
                return false;
            }
        }
        return true;
    },

    _enterMRU_Place: function(destination_uri) {
        if (!this.currentPlace) {
            return;
        }
        this.pushHistoryInfo(this.currentPlace, destination_uri);
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
        this._moveToURI(uri, setThePref);
    },

    toggleRebaseFolderByIndex: function(index) {
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        this._enterMRU_Place(uri);
        this._setURI(uri, true);
    },

    _moveToURI: function(uri, setThePref) {
        if (typeof(setThePref) == "undefined") {
            setThePref = false;
        }
        var statusNode = document.getElementById("place-view-rootPath-icon");
        var busyURI = "chrome://global/skin/icons/loading_16.png";
        statusNode.src = busyURI;
        this.currentPlace = uri;
        var file = Components.classes["@activestate.com/koFileEx;1"].
        createInstance(Components.interfaces.koIFileEx);
        file.URI = uri
        widgets.rootPath.value = file.baseName;
        var tooltipText = (file.scheme == "file" ? file.displayPath : uri);
        widgets.rootPath.tooltipText = tooltipText;
        widgets.rootPath.setAttribute('class', 'someplace');
        widgets.rootPathIcon.tooltipText = tooltipText;
        var callback = {
            callback: function(result, data) {
                statusNode.src = widgets.defaultFolderIconSrc;
                if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    widgets.rootPath.value = ""
                    widgets.rootPath.tooltipText = "";
                    widgets.rootPath.setAttribute('class', 'noplace');
                    widgets.rootPathIcon.tooltipText = "";
                    ko.dialogs.alert(data);
                } else {
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
                }
            }
        };
        gPlacesViewMgr.view.setCurrentPlaceWithCallback(uri, callback);
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
    
    goUpOneFolder: function() {
        var uri = ko.places.manager.currentPlace;
        var lastSlashIdx = uri.lastIndexOf("/");
        if (lastSlashIdx == -1) return;
        var parent_uri = uri.substr(0, lastSlashIdx);
        this._enterMRU_Place(parent_uri);
        this._setURI(parent_uri, true);
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
        this._setURI(targetURI, false);
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
        return gPlacesViewMgr.view.canUndoTreeOperation();
    },

    undoTreeOperation: function() {
        try {
            gPlacesViewMgr.view.do_undoTreeOperation();
            window.updateCommands('did_tree_operation');
        } catch(ex) {
            alert(ex);
        }
    },

    addRecentLocations: function(popupMenu) {
        /*
         * Show at most 6 recent locations, and the rest in a further popup
         */
        var menuitem;
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
        var reportedURIs = {};
        var numWritten = 0;
        var innerPopupMenu = null;
        var outerPopupMenu = popupMenu;
        var innerMenu = null;
        var popupThreshold = 5;
        for (var i = 0; i < blocks.length; ++i) {
            var block = blocks[i];
            var code = codes[i];
            for (var j = block.length - 1; j >= 0; --j) {
                var uri = block[j];
                if (!uri || uri in reportedURIs) {
                    continue;
                }
                reportedURIs[uri] = true;
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
                numWritten += 1;
                if (numWritten == popupThreshold) {
                    innerMenu = document.createElement("menu");
                    innerMenu.id = "recentItems.more";
                    innerMenu.setAttribute('label', "More...");
                    popupMenu.appendChild(innerMenu);
                    innerPopupMenu = document.createElement("menupopup");
                    innerMenu.appendChild(innerPopupMenu);
                    popupMenu = innerPopupMenu;
                }
            }
        }
        if (numWritten == popupThreshold + 1) {
            // Pull out the "More..." inner menu, to avoid an inner menu with one item.
            outerPopupMenu.replaceChild(innerPopupMenu.childNodes[0], innerMenu);
        }
    },

    init_popup_parent_directories: function(event) {
        if (event.originalTarget.id != "placesParentDirectoriesMenu") {
            return;
        }
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
        //TODO: Put the project file here, however that will work.
        // Next put the recent places
        if (this.history_forwardPlaces.length
            || this.history_prevPlaces.length) {
            menuitem = document.createElementNS(XUL_NS, 'menuseparator');
            menuitem.id = "popup_parent_directories:sep:recentPlaces";
            popupMenu.appendChild(menuitem);
            this.addRecentLocations(popupMenu);
        }
        // Next put any starred places
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

    cleanPrefs: function() {
    },

    'observe': function(cancelQuit, topic, data) {
        if (topic == 'visit_directory_proposed') {
            var haveCancelQuit = !!cancelQuit;
            var handleRequest = true;
            if (haveCancelQuit) {
                cancelQuit.QueryInterface(Components.interfaces.nsISupportsPRBool);
                if (cancelQuit.data) {
                    // someone else handled it (nothing else in core komodo)
                    handleRequest = false;
                } else {
                    cancelQuit.data = true; // we handled it.
                }
            }
            if (handleRequest) {
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
    widgets.rootPathIcon = document.getElementById("place-view-rootPath-icon");
    widgets.defaultFolderIconSrc = widgets.rootPathIcon.src;
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
