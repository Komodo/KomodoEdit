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

const PROJECT_URI_REGEX = /^.*\/(.+?)\.(?:kpf|komodoproject)$/;
    
var log = getLoggingMgr().getLogger("places_js");
log.setLevel(LOG_DEBUG);

// Yeah, not really a class per se, but it acts like one, so
// give it an appropriate name.
// This object will manage the JS side of the tree view.
function viewMgrClass() {
    this.default_exclude_matches = ".*;*~;#*;CVS;*.bak;*.pyo;*.pyc";
    // overides, to include:
    this.default_include_matches = ".login;.profile;.bashrc;.bash_profile";
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
            throw new Error("couldn't create a koPlaceTreeView");
        }
        this.tree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.view;
        this.view.initialize();
        var sortDir;
        var placePrefs = _globalPrefs.getPref("places");
        if (placePrefs.hasPref("sortDirection")) {
            var sortDir = placePrefs.getStringPref("sortDirection");
        }
        if (!sortDir) {
            sortDir = 'natural';
        }
        var sortMenuPopup = document.getElementById("placeView_sortPopup");
        var childNodes = sortMenuPopup.childNodes;
        var targetSortId = "placeView_sort" + sortDir[0].toUpperCase() + sortDir.substr(1);
        var madeChange = false;
        for (var childNode, i = 0; childNode = childNodes[i]; i++) {
            if (childNode.id == targetSortId) {
                childNode.setAttribute('checked', 'true');
                madeChange = true;
            } else {
                childNode.removeAttribute('checked');
            }
        }
        if (!madeChange) {
            log.debug("Failed to find a sortDir of " + sortDir + "\n");
            sortDir = "natural";
            childNodes[0].setAttribute('checked', 'true');
        }
        this.sortDirection = sortDir;
        this.view.sortBy("Name", this._mozSortDirNameToKomodoSortDirValue[sortDir]);
    },
    
    sortByDirection: function(sortDirection) {
        this.view.sortBy("Name", this._mozSortDirNameToKomodoSortDirValue[sortDirection]);
        this.view.sortRows();
        this.sortDirection = sortDirection;
    },
    
    focus: function() {
          //dump("places: viewMgr.focus()\n");
          this.tree.focus();
      },
    updateView: function() {
          //dump("places: viewMgr.updateView()\n");
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
            var uri = this.view.getURIForRow(index);
            if (uri) {
                ko.open.URI(uri);
            }
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
    
    refreshViewByIndex: function(index) {
        this.view.refreshView(index);
    },
    
    refreshStatus: function(index) {
        var uri = this.view.getURIForRow(index);
        var fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].getService(Components.interfaces.koIFileStatusService);
        fileStatusSvc.updateStatusForUris(1, [uri],
                                          true /* forcerefresh */);
    },

    getSelectedURIs: function(rootsOnly) {
        var view = this.view;
        var selectedIndices = ko.treeutils.getSelectedIndices(view, rootsOnly);
        return selectedIndices.map(function(row) {
                return view.getURIForRow(row);
            });
    },
    
    openFilesByIndex: function(event) {
        var uris = this.getSelectedURIs(false);
        ko.open.multipleURIs(uris);
    },

    compareFileWith: function(event) {
        var index = ko.treeutils.getSelectedIndices(this.view, false)[0];
        var uri = this.view.getURIForRow(index);
        var file = Components.classes["@activestate.com/koFileEx;1"].
                createInstance(Components.interfaces.koIFileEx);
        file.URI = uri
        var pickerDir = file.isLocal? file.dirName : '';
        var otherfile = ko.filepicker.browseForFile(pickerDir);
        if (otherfile) {
            ko.fileutils.showDiffs(file.path, otherfile);
        }
    },

    compareFiles: function(event) {
        var selectedIndices = ko.treeutils.getSelectedIndices(this.view, false);
        if (selectedIndices.length != 2) {
            log.error("compareFiles: Failed: expecting 2 items, got "
                      + selectedIndices.length);
            return;
        }
        var fname = this.view.getURIForRow(selectedIndices[0]);
        var otherfile = this.view.getURIForRow(selectedIndices[1]);
        ko.fileutils.showDiffs(fname, otherfile);
    },

    addNewFile: function() {
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFileName"));
        if (!name) return;
        try {
            var index = this.view.selection.currentIndex;
            this.view.addNewFileAtParent(name, index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
    },

    addNewFolder: function() {
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFolderName"));
        if (!name) return;
        try {
            var index = this.view.selection.currentIndex;
            this.view.addNewFolderAtParent(name, index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
    },

    onTreeClick: function(event) {
        var index = this._currentRow(event);
        if (index == -1) {
            this.view.selection.clearSelection();
        } else {
            this.view.markRow(index);
        }
    },

    onTreeKeyPress: function(event) {
        //dump("TODO: viewMgrClass.onTreeKeyPress\n");
        if ((event.keyCode == event.DOM_VK_ENTER
             || event.keyCode == event.DOM_VK_RETURN)
            && !event.shiftKey && !event.ctrlKey && !event.altKey) {
            var t = event.originalTarget;
            if (t.localName == "treechildren" || t.localName == 'tree') {
                // If all the items are files, open them.
                var selectedIndices = ko.treeutils.getSelectedIndices(this.view, false);
                for (var index, i = 0; i < selectedIndices.length; i++) {
                    index = selectedIndices[0];
                    if (this.view.isContainer(index)) {
                        if (selectedIndices.length > 1) {
                            event.cancelBubble = true;
                            event.preventDefault();
                        }
                        return;
                    }
                }
                event.cancelBubble = true;
                event.preventDefault();
                this.openFilesByIndex();
            }
        }
    },
    allowed_click_nodes: ["places-files-tree-body",
                          "place-view-rootPath-icon-toolbarbutton",
                          "places-files-tree"],
    initFilesContextMenu: function(event, menupopup) {
        var clickedNodeId = event.explicitOriginalTarget.id;
        if (this.allowed_click_nodes.indexOf(clickedNodeId) == -1) {
            // We don't want to fillup this context menu (i.e. it's likely a
            // sub-menu such as the scc context menu).
            return false;
        }
        // Work on one item only, later move to multipleItems
        var row = {};
        this.tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
        var index = row.value;
        if (index == -1
            && clickedNodeId != "place-view-rootPath-icon-toolbarbutton") {
            // Means that we're clicking in white-space below.
            // Clear the selection, and return.
            this.view.selection.clearSelection();
            event.stopPropagation();
            event.preventDefault();
            return false;
        }
        var selectedIndices = ko.treeutils.getSelectedIndices(this.view, false /*rootsOnly*/);
        var isRootNode;
        var itemTypes = null;
        if (clickedNodeId == "place-view-rootPath-icon-toolbarbutton") {
            index = -1;
            isRootNode = true;
            itemTypes = ["project"];
        } else {
            index = this._currentRow(event);
            dump("Init Menu: index: " + index + "\n");
            isRootNode = (index == -1);
            if (isRootNode) {
                itemTypes = ["project"];
            } else {
                itemTypes = [];
                var sawFolder = false;
                var sawFile = false;
                var view = this.view;
                selectedIndices.map(function(index) {
                        if (view.isContainer(index)) {
                            sawFolder = true;
                        } else {
                            sawFile = true;
                        }
                    });
                if (sawFile) {
                    itemTypes.push('file');
                }
                if (sawFolder) {
                    itemTypes.push('folder');
                }
            }
        }
        var isLocal = ko.places.manager.currentPlaceIsLocal;
        var disableAll = (isRootNode
                          && widgets.rootPath.getAttribute('class') ==  'noplace');
        this._selectionInfo = {
            classIsntProject: event.explicitOriginalTarget.getAttribute('class') != 'project',
            itemTypes: itemTypes,
            index:index,
            isLocal:isLocal,
            disableAll:disableAll,
            multipleNodesSelected: selectedIndices.length > 1,
            selectedTwoItems: selectedIndices.length == 2,
            __END__:null
        };
        this._processMenu_TopLevel(menupopup);
        delete this._selectionInfo;
        return true;
    },

    _matchAnyType: function(typeListAttr, typesSelectedArray) {
        if (!typeListAttr) {
            return false;
        } else if (typesSelectedArray.length == 1) {
            return typeListAttr.indexOf(typesSelectedArray[0]) != -1;
        }
        for (var typeName, i = 0; typeName = typesSelectedArray[i]; i++) {
            if (typeListAttr.indexOf(typeName) != -1) {
                return true;
            }
        }
        return false;
    },

    _processMenu_TopLevel: function(menuNode) {
        var selectionInfo = this._selectionInfo;
        var itemTypes = selectionInfo.itemTypes;
        if (this._matchAnyType(menuNode.getAttribute('hideIf'), itemTypes)) {
            menuNode.setAttribute('collapsed', true);
            return; // No need to do anything else
        }
        var hideUnless = menuNode.getAttribute('hideUnless');
        if (hideUnless) {
            // Need to match all
            for (var typeName, i = 0; typeName = itemTypes[i]; i++) {
                if (hideUnless.indexOf(typeName) == -1) {
                    menuNode.setAttribute('collapsed', true);
                    return; // No need to do anything else
                }
            }
        }
        var testHideIf = menuNode.getAttribute('testHideIf');
        if (testHideIf) {
            testHideIf = testHideIf.split(/\s+/);
            var leave = false;
            testHideIf.map(function(s) {
                    if (s == 't:multipleSelection' && selectionInfo.multipleNodesSelected) {
                        menuNode.setAttribute('collapsed', true);
                        leave = true;
                    } else if (s == 't:singleSelection' && !selectionInfo.multipleNodesSelected) {
                        menuNode.setAttribute('collapsed', true);
                        leave = true;
                    } else if (s == 't:selectedTwoItems' && !selectionInfo.selectedTwoItems) {
                        menuNode.setAttribute('collapsed', true);
                        leave = true;
                    }
                });
            if (leave) {
                return;
            }
        }
        var testEval_HideIf = menuNode.getAttribute('testEval_HideIf');
        if (testEval_HideIf) {
            try {
                var res = eval(testEval_HideIf);
                if (res) {
                    menuNode.setAttribute('collapsed', true);
                    return;
                }
            } catch(ex) {
                log.exception("Failed to eval '"
                              + testEval_HideIf
                              + ": " + ex);
            }
        }
    
        menuNode.removeAttribute('collapsed');
        var disableNode = false;
        if (this._matchAnyType(menuNode.getAttribute('disableIf'), itemTypes)) {
            disableNode = true;
        } else {
            var testDisableIf = menuNode.getAttribute('testDisableIf');
            if (testDisableIf) {
                testDisableIf = testDisableIf.split(/\s+/);
                testDisableIf.map(function(s) {
                        if (s == 't:multipleSelection' && selectionInfo.multipleNodesSelected) {
                            disableNode = true;
                        } else if (s == 't:isRemote' && !selectionInfo.isLocal) {
                            disableNode = true;
                        } else if (s == 't:classIsntProject' && selectionInfo.classIsntProject) {
                            disableNode = true;
                        }
                    });
            }
            if (!disableNode) {
                var testEval_DisableIf = menuNode.getAttribute('testEval_DisableIf');
                if (testEval_DisableIf) {
                    try {
                        var res = eval(testEval_DisableIf);
                        if (res) {
                            disableNode = true;
                        }
                    } catch(ex) {
                        log.exception("Failed to eval '"
                                      + testEval_DisableIf
                                      + ": " + ex);
                        disableNode = true;
                    }
                }
            }
        }
        if (disableNode) {
            menuNode.setAttribute('disabled', true);
        } else {
            menuNode.removeAttribute('disabled');
        }
        var childNodes = menuNode.childNodes;
        for (var i = childNodes.length - 1; i >= 0; --i) {
            this._processMenu_TopLevel(childNodes[i]);
        }
    },

    _makeMenuItem: function(id, label, handler) {
        var menuitem = document.createElement("menuitem");
        menuitem.setAttribute("label", label);
        menuitem.setAttribute("id", id);
        menuitem.setAttribute("oncommand", handler);
        return menuitem;
    },

    doStartDrag: function(event, tree) {
        var uris = gPlacesViewMgr.getSelectedURIs(true);
        this.complainIfNotAContainer = true;  // used for internal logging only
        var dt = event.dataTransfer;
        var uri, lim = uris.length;
        for (var i = 0; i < lim && (uri = uris[i]); i++) {
            if (this.currentPlaceIsLocal) {
                // Do this for drag/drop onto things like file managers.
                var nsLocalFile = Components.classes["@mozilla.org/file/local;1"]
                    .createInstance(Components.interfaces.nsILocalFile);
                path = ko.uriparse.URIToLocalPath(uri);
                nsLocalFile.initWithPath(path);
                dt.mozSetDataAt("application/x-moz-file", nsLocalFile, i);
                dt.mozSetDataAt("text/uri-list", uri, i);
                dt.mozSetDataAt('text/plain', ko.uriparse.URIToLocalPath(uri), i);
            } else {
                dt.mozSetDataAt("text/uri-list", uri, i);
                dt.mozSetDataAt('text/plain', uri, i);
            }
        }
        dt.effectAllowed = "copymove";
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
        // All dragged items must be URIs for the drag source to be valid.
        var dt = event.dataTransfer;
        for (var i = 0; i < dt.mozItemCount; i++) {
            if (!event.dataTransfer.mozTypesAt(i).contains("text/uri-list")) {
                if (this.complainIfNotAContainer) {
                    log.debug("not a file data-transfer\n");
                    this.complainIfNotAContainer = false;
                }
                return false;
            }
        }
        return true;
    },    
    _checkDragToRootNode: function(event) {
        var inDragSource = ko.places.manager.currentPlace && this._checkDragSource(event);
        if (inDragSource) {
            var dt = event.dataTransfer;
            for (var i = 0; i < dt.mozItemCount; i++) {
                if (dt.mozGetDataAt("text/uri-list", i) == this.currentPlace) {
                    inDragSource = false;
                    break;
                }
            }
        }
        event.dataTransfer.effectAllowed = inDragSource ? this.originalEffect : "none";
        
    },
    _checkDrag: function(event) {
        var inDragSource = this._checkDragSource(event);
        var index = this._currentRow(event);
        var retVal = false;
        if (!inDragSource) {
            // do nothing more
        } else if (this._draggingOntoSelf(event, index)) {
            // Can't drag onto oneself
        } else if (!this.view.isContainer(index)) {
            //if (this.complainIfNotAContainer) {
            //    log.debug("Not a container\n");
            //    this.complainIfNotAContainer = false;
            //}
        } else if (this._draggingOntoParent(event, index)) {
            // Can't drag self into its parent.
        } else {
            retVal = true;
            //dump("this.originalEffect: " + this.originalEffect + "\n");
        }
        event.dataTransfer.effectAllowed = retVal ? this.originalEffect : "none";
        return retVal;
    },
    _draggingOntoSelf: function(event, index) {
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        var dt = event.dataTransfer;
        for (var i = 0; i < dt.mozItemCount; i++) {
            if (dt.mozGetDataAt("text/uri-list", i) == uri) {
                return true;
            }
        }
        return false;
    },

    _draggingOntoParent: function(event, index) {
        var target_uri = gPlacesViewMgr.view.getURIForRow(index);
        var dt = event.dataTransfer;
        for (var i = 0; i < dt.mozItemCount; i++) {
            var src_uri = dt.mozGetDataAt("text/uri-list", i);
            var srcParent_uri = src_uri.substring(0, src_uri.lastIndexOf("/"));
            if (srcParent_uri == target_uri) {
                return true;
            }
        }
        return false;
    },

    _getDraggedURIs: function(event) {
        var from_uris = [];
        var dt = event.dataTransfer;
        for (var i = 0; i < dt.mozItemCount; i++) {
            from_uris.push(dt.mozGetDataAt("text/uri-list", i));
        }
        var dropEffect = dt.dropEffect;
        return [from_uris, dropEffect];
    },

    doDrop : function(event, tree) {
        var index = this._currentRow(event);
        var target_uri = gPlacesViewMgr.view.getURIForRow(index);
        this._finishDrop(event, target_uri, index);
    },
    
    _finishDrop : function(event, target_uri, index) {
        var dt = event.dataTransfer;
        var from_uris, dropEffect, copying;
        [from_uris, dropEffect] = this._getDraggedURIs(event);
        if (from_uris.length == 0) {
            log.debug("_finishDrop: no from_uris\n");
            return false;
        } else if (dropEffect == "none") {
            log.debug("_finishDrop: no drag/drop here\n");
            return false;
        } else if (dropEffect == "link") {
            ko.dialogs.alert("don't know how to drag/drop a link");
            return false;
        }
        copying = (dropEffect == "copy");
        try {
            this._finishFileCopyOperation(from_uris, target_uri, index, copying);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
        event.stopPropagation();
        event.cancelBubble = true;
        event.preventDefault();
        return true;
    },

    doDropOnRootNode : function(event, tree) {
        var target_uri = ko.places.manager.currentPlace;
        this._finishDrop(event, target_uri, -1);
    },

    doEndDrag: function(event, tree) {
        var dt = event.dataTransfer;
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

    _finishFileCopyOperation: function(from_uris, to_uri, target_index, copying) {
        // target_index can be -1 if we're dropping on the root node
        var srcFileInfoObjs = {}, targetFileInfoObjs = {};
        var simple_callback = {
            callback: function(result, data) {
                if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    ko.dialogs.alert(data);
                } else {
                    window.updateCommands("did_tree_operation");
                }
            }
        };
        var dirty_paths = [];
        from_uris.map(function(uri) {
            var from_view = ko.views.manager.getViewForURI(uri);
            if (from_view && from_view.isDirty) {
                dirty_paths.push(ko.uriparse.URIToPath(uri));
            }
        });
        if (dirty_paths.length) {
            var prompt;
            operation = _bundle.GetStringFromName(copying ? "Copy.label" : "Move.label");
            if (dirty_paths.length == 1) {
                prompt = _bundle.formatStringFromName("fileSingularXHasUnsavedChanges_opWithoutSaving.prompt",
                                                      [dirty_paths[0], operation], 2);
            } else {
                prompt = _bundle.formatStringFromName("filesPluralXHaveUnsavedChanges_opWithoutSaving.prompt",
                                                      [dirty_paths.join(", "), operation], 2);
            }
            var response = _bundle.GetStringFromName("No.label");
            var title =  _bundle.GetStringFromName("saveChangesFirst.prompt");
            var res = ko.dialogs.yesNo(prompt, response, null, title);
            if (res != _bundle.GetStringFromName("Yes.label")) {
                return false;
            }
        }
        var statuses = {};
        this.view.treeOperationWouldConflict_MultipleSrc(from_uris,
                                                         from_uris.length,
                                                         to_uri,
                                                         copying,
                                                         {}, statuses,
                                                         srcFileInfoObjs,
                                                         targetFileInfoObjs);
        statuses = statuses.value;
        srcFileInfoObjs = srcFileInfoObjs.value;
        targetFileInfoObjs = targetFileInfoObjs.value;
        var lim = statuses.length;
        var finalSrcURIs = [];
        var finalTargetURIs = [];
        var existingSrcDirectories = [];
        var selfDirectories = [];
        var newPaths = [];
        for (var i = 0; i < lim; i++) {
            var res = statuses[i];
            var srcFileInfo = srcFileInfoObjs[i];
            // targetFileInfo points at the existing file
            var targetFileInfo = targetFileInfoObjs[i];
            if (!res) {
                finalSrcURIs.push(srcFileInfo.URI);
                finalTargetURIs.push(targetFileInfo.URI);
                continue;
            }
            var srcFileInfoText = this._formatFileInfo(srcFileInfo);
            var targetFileInfoText = this._formatFileInfo(targetFileInfo);
            var prompt = "File already exists";//@@@
            var buttons, text, title;
            if (res == Components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR) {
                existingSrcDirectories.push(srcFileInfo);
                continue;
            } else if (res == Components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR) {
                selfDirectories.push(srcFileInfo);
                continue;
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
                // Copy/move it over anyways.
                finalSrcURIs.push(srcFileInfo.URI);
                finalTargetURIs.push(targetFileInfo.URI);
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
                    newPaths[finalSrcURIs.length] = newPath;
                    finalSrcURIs.push(srcFileInfo.URI);
                    finalTargetURIs.push(targetFileInfo.URI);
                } finally {
                    if (conn) {
                        conn.close();
                    }
                }
            }
        }
        if (existingSrcDirectories.length > 0) {
            title = _bundle.GetStringFromName("directoryAlreadyExists.label");
            prompt = _bundle.GetStringFromName("replacingDirectoryNotSupported.label");
            text = (_bundle.GetStringFromName("forFollowingFiles.label")
                    + existingSrcDirectories.map(function(srcFileInfo) {
                            return (_bundle.GetStringFromName("sourceFilePrefix")
                                    + srcFileInfo.baseName
                                    + _bundle.GetStringFromName("directoryPrefix")
                                    + srcFileInfo.dirName);
                        }).join(", "));
            ko.dialogs.alert(prompt, text, title);
        }
        if (selfDirectories.length > 0) {
            title = _bundle.GetStringFromName("notMovingFileAnywhere.label");
            prompt = _bundle.GetStringFromName("cantMoveFileIntoItsOwnDirectory.label");
            text = (_bundle.GetStringFromName("forFollowingFiles.label")
                    + existingSrcDirectories.map(function(srcFileInfo) {
                            return (_bundle.GetStringFromName("sourceFilePrefix")
                                    + srcFileInfo.baseName
                                    + _bundle.GetStringFromName("directoryPrefix")
                                    + srcFileInfo.dirName);
                        }).join(", "));
            ko.dialogs.alert(prompt, text, title);
        }
        lim = finalSrcURIs.length;
        for (i = 0; i < lim; i++) {
            var srcURI = finalSrcURIs[i];
            var callback = null;
            var from_uri = from_uris[i];
            if (!copying) {
                var from_view = ko.views.manager.getViewForURI(srcURI);
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
            if (typeof(newPaths[i]) != "undefined") {
                this.view.doTreeCopyWithDestNameAndURI(srcURI, to_uri,
                                                       target_index,
                                                       newPaths[i],
                                                       callback);
            } else {
                this.view.doTreeOperation(srcURI, to_uri, target_index,
                                          copying,
                                          copying ? simple_callback : callback);
            }
        }
        if (to_uri == ko.places.manager.currentPlace) {
            this.view.refreshFullTreeView();
            this.tree.treeBoxObject.invalidate();
        }
        this.view.selection.clearSelection();
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
        _globalPrefs.getPref("places").setStringPref("sortDirection",
                                                     this.sortDirection);
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
    
    var gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);
    gObserverSvc.addObserver(this, 'visit_directory_proposed', false);
    gObserverSvc.addObserver(this, 'current_project_changed', false);
    gObserverSvc.addObserver(this, 'file_changed', false);
    window.addEventListener('project_opened',
                            this.handle_project_opened_setup, false);
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
        this._setDirURI(uri, true);
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
        this._setDirURI(uri, true);
    },

    openURI : function(uri) {
        this._enterMRU_Place(uri);
        this._setDirURI(uri, true);
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

    toggleRebaseFolderByIndex: function(index) {
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        this._enterMRU_Place(uri);
        this._setURI(uri, true);
    },

    _checkProjectMatch: function() {
        var classValue = this._currentPlaceMatchesCurrentProject() ? "project" : "normal";
        widgets.rootPathToolbar.setAttribute('class', classValue);
    },

    _currentPlaceMatchesCurrentProject: function() {
        var uri = this.currentPlace;
        var project = ko.projects.manager.currentProject;
        if (!uri || !project) {
            return false;
        }
        var targetDirURI = this._getActualProjectDir(project);
        return uri == targetDirURI;
    },
    
    /* Change places to the given dir.
     *
     * @param dirURI {string} The directory to which to switch, as a URI.
     *      This is presumed to be a directory (i.e. not a file) and to
     *      exist.
     * @param save {Boolean} Whether to save this dir in the places dir history.
     *      Default is false.
     */
    _setDirURI: function(dirURI, save /* =false */) {
        if (typeof(save) == "undefined") {
            save = false;
        }

        var koFile = Components.classes["@activestate.com/koFileEx;1"].
                createInstance(Components.interfaces.koIFileEx);
        koFile.URI = dirURI;
        this.currentPlaceIsLocal = koFile.isLocal;

        var statusNode = document.getElementById("place-view-rootPath-icon-toolbarbutton");
        var busyURI = "chrome://global/skin/icons/loading_16.png";
        statusNode.setAttribute('image', busyURI);
        this.currentPlace = dirURI;
        var file = Components.classes["@activestate.com/koFileEx;1"].
        createInstance(Components.interfaces.koIFileEx);
        file.URI = dirURI
        widgets.rootPath.value = file.baseName;
        widgets.rootPath.setAttribute('class', 'someplace');
        var tooltipText = (file.scheme == "file" ? file.displayPath : dirURI);
        widgets.rootPath.tooltipText = tooltipText;
        this._checkProjectMatch();
        widgets.rootPathToolbar.tooltipText = tooltipText;
        var this_ = this;
        var callback = {
            callback: function(result, data) {
                statusNode.setAttribute('image', widgets.defaultFolderIconSrc);
                if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    widgets.rootPath.value = ""
                    widgets.rootPath.tooltipText = "";
                    widgets.rootPath.setAttribute('class', 'noplace');
                    widgets.rootPathToolbar.tooltipText = "";
                    this_.currentPlace = null;
                    ko.dialogs.alert(data);
                } else {
                    window.setTimeout(window.updateCommands, 1,
                                      "current_place_opened");
                    if (save) {
                        _placePrefs.setStringPref(window._koNum, dirURI);
                    }
                    var viewName = null;
                    var prefSet;
                    if (uriSpecificPrefs.hasPref(dirURI)) {
                        var prefSet = uriSpecificPrefs.getPref(dirURI);
                        try { viewName = prefSet.getStringPref('viewName')} catch(ex) {}
                        var finalViewName = gPlacesViewMgr.placeView_updateView(viewName);
                        if (finalViewName != viewName) {
                            prefSet.setStringPref('viewName', finalViewName)
                                }
                    } else {
                        var finalViewName = gPlacesViewMgr.placeView_updateView(null);
                        prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
                        prefSet.setStringPref('viewName', finalViewName);
                        uriSpecificPrefs.setPref(dirURI, prefSet);
                    }
                }
            }
        };
        gPlacesViewMgr.view.setCurrentPlaceWithCallback(dirURI, callback);
    },

    /* doCutPlaceItem
     * Marking an item with 'cut' does nothing, until we do
     * a paste on it, and then it gets moved.
     *
     * An entry is placed on the clipboard to tell other Komodo
     * windows what to do.
     */
    doCutPlaceItem: function() {
        this._selectCurrentItems(false);
    },

    doCopyPlaceItem: function() {
        this._selectCurrentItems(true);
    },

    _selectCurrentItems: function(isCopying) {
        var rootsOnly = true;
        var uris = gPlacesViewMgr.getSelectedURIs(true);
        var uriList = uris.join("\n");
        var transferable = xtk.clipboard.addTextDataFlavor("text/unicode", uriList);
        xtk.clipboard.addTextDataFlavor("x-application/komodo-places",
                                        isCopying ? "1" : "0" , transferable);
        xtk.clipboard.copyFromTransferable(transferable);
        window.setTimeout(window.updateCommands, 1, "clipboard");
    },

    doPastePlaceItem: function() {
        var srcURIs = xtk.clipboard.getText().split(/\n/);
        var isCopying = xtk.clipboard.getTextFlavor("x-application/komodo-places");
        isCopying = parseInt(isCopying);
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var target_uri = gPlacesViewMgr.view.getURIForRow(index);
        var koTargetFileEx = Components.classes["@activestate.com/koFileEx;1"].
        createInstance(Components.interfaces.koIFileEx);
        koTargetFileEx.URI = target_uri;
        if (koTargetFileEx.isFile) {
            target_uri = target_uri.substr(0, target_uri.lastIndexOf("/"));
            index = gPlacesViewMgr.view.getRowIndexForURI(target_uri);
            if (index == -1) {
                var prompt = _bundle.formatStringFromName('cantFindFilesParentInTree.prompt',
                                          [koTargetFileEx.displayPath], 1);
                ko.dialogs.alert(prompt);
                return;
            }
        }
        try {
            gPlacesViewMgr._finishFileCopyOperation(srcURIs, target_uri, index,
                                                    isCopying);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
        if (!isCopying) {
            xtk.clipboard.emptyClipboard();
        }
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

    _clickedOnRoot: function() {
        return document.popupNode == widgets.rootPathToolbar;
    },

    _launchFindOrReplace: function(launcher, numNulls) {
        if (!this.currentPlaceIsLocal) {
            return;
        }
        var path;
        var args = [];
        for (; numNulls > 0; numNulls--) {
            args.push(null);
        }
        if (this._clickedOnRoot()) {
            path = ko.uriparse.displayPath(this.currentPlace);
        } else {
            //var findWindow = ko.launch.find(null, true);
            var index = gPlacesViewMgr.view.selection.currentIndex;
            var uri = gPlacesViewMgr.view.getURIForRow(index);
            var isFolder = gPlacesViewMgr.view.isContainer(index);
            path = isFolder ? ko.uriparse.displayPath(uri) : ko.uriparse.dirName(uri) ;
        }
        args.push(path);
        launcher.apply(ko.launch, args);
    },

    doFindInPlace: function() {
        this._launchFindOrReplace(ko.launch.findInFiles, 1);
    },

    doReplaceInPlace: function() {
        this._launchFindOrReplace(ko.launch.replaceInFiles, 2);
    },

    doShowInFinder: function() {
        if (!this.currentPlaceIsLocal) {
            return;
        }
        var path;
        if (this._clickedOnRoot()) {
            path = ko.uriparse.displayPath(this.currentPlace);
        } else {
            var index = gPlacesViewMgr.view.selection.currentIndex;
            var uri = gPlacesViewMgr.view.getURIForRow(index);
            path = ko.uriparse.displayPath(uri);
        }
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
        var indexes = ko.treeutils.getSelectedIndices(gPlacesViewMgr.view, true);
        if (indexes.length == 0) {
            return;
        }
        var deleteContents = false;
        var prompt;
        var response = _bundle.GetStringFromName("no");
        var text = null;
        var title;
        var msg = "";
        var nonEmptyFolders = [];
        var otherItemCount = 0;
        for (var i = 0; i < indexes.length; i++) {
            var index = indexes[i];
            if (gPlacesViewMgr.view.itemIsNonEmptyFolder(index)) {
                nonEmptyFolders.push(gPlacesViewMgr.view.getCellText(index, {id:'name'}));
            } else {
                otherItemCount += 1;
            }
        }
        if (nonEmptyFolders.length) {
            msg += (_bundle.GetStringFromName("youHaveSelected.piece")
                    + " "
                    + (nonEmptyFolders.length == 1
                       ? _bundle.GetStringFromName("selectedSingularFolder.piece")
                       : _bundle.formatStringFromName("selectedSingularItem.piece",
                                                      [nonEmptyFolders.length], 1)));
        }
        if (otherItemCount) {
            if (nonEmptyFolders.length) {
                msg += " " + _bundle.GetStringFromName("and.piece") + " ";
            } else {
                msg = _bundle.GetStringFromName("youHaveSelected.piece") + " ";
            }
            msg += (nonEmptyFolders.length == 1
                       ? _bundle.GetStringFromName("selectedSingularItem.piece")
                       : _bundle.formatStringFromName("selectedPluralItems.piece",
                                                      [otherItemCount], 1));
        }
        msg += (".  " +
                _bundle.GetStringFromName((nonEmptyFolders.length + otherItemCount == 1)
                                          ? "okToDeleteSingular.promptOK"
                                          : "okToDeletePlural.prompt"));
        title = _bundle.GetStringFromName("deletionCheck.prompt");
        prompt = msg;
        var response = ko.dialogs.yesNo(prompt, response, text, title);
        if (response != _bundle.GetStringFromName("yes")) {
            return;
        }
        // Loop in reverse-order so we don't have to adjust for deleted indices
        indexes.sort(function(a, b) { return b - a; });
        var uris = [];
        for (var i=0; i < indexes.length; i++) {
            uris.push(gPlacesViewMgr.view.getURIForRow(indexes[i]));
        }
        try {
            gPlacesViewMgr.view.deleteItems(indexes.length, indexes,
                                            uris.length, uris);
        } catch(ex) {
            alert(ex);
        }
    },
    /*

                 _bundle.formatStringFromName(
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
    */
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
                this._setDirURI(uri, false);
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
        gObserverSvc.removeObserver(this, 'current_project_changed');
        gObserverSvc.removeObserver(this, 'file_changed');
        window.removeEventListener('project_opened',
                                   this.handle_project_opened_setup, false);
    },
    
    goUpOneFolder: function() {
        var uri = ko.places.manager.currentPlace;
        var lastSlashIdx = uri.lastIndexOf("/");
        if (lastSlashIdx == -1) return;
        var parent_uri = uri.substr(0, lastSlashIdx);
        this._enterMRU_Place(parent_uri);
        this._setDirURI(parent_uri, true);
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
        this._setDirURI(targetURI, false);
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
        this._setDirURI(targetURI, true);
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

    _sortByDirection: function(sortDirection) {
        ko.places.viewMgr.sortByDirection(sortDirection);
    },

    sortNatural: function() {
        this._sortByDirection("natural");
    },

    sortAscending: function() {
        this._sortByDirection("ascending");
    },

    sortDescending: function() {
        this._sortByDirection("descending");
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
        this._setDirURI(uri, true);
    },

    /**
     * Return the URIs for the selected tree items.
     *
     * @returns {array} - the selected URIs.
     */
    getSelectedUris: function() {
        var indexes = ko.treeutils.getSelectedIndices(gPlacesViewMgr.view,
                                                      /*rootsOnly=*/false);
        var uris = [];
        for (var i=0; i < indexes.length; i++) {
            uris.push(gPlacesViewMgr.view.getURIForRow(indexes[i]));
        }
        return uris;
    },

    /**
     * Return the koIFileEx objects for the selected tree items.
     *
     * @returns {array} - the selected files.
     */
    getSelectedFiles: function() {
        var uris = this.getSelectedUris();
        var fileSvc = Components.classes["@activestate.com/koFileService;1"].
                           getService(Components.interfaces.koIFileService);
        var files = [];
        for (var i=0; i < uris.length; i++) {
            files.push(fileSvc.getFileFromURI(uris[i]));
        }
        return files;
    },
    
    _getItemByIndex: function(index) {
        var viewObj = gPlacesViewMgr.view;
        var uri = viewObj.getURIForRow(index);
        var itemType = viewObj.isContainer(index) ? 'folder' : 'file';
        return new ItemWrapper(uri, itemType);        
    },
    
    /** These functions return pseudo-parts for
     * files, folders, and projects, so the old API
     * can use them easily.
     */
    getSelectedItem: function() {
        var index = gPlacesViewMgr.view.selection.currentIndex;
        return this._getItemByIndex(index);
    },
    
    getSelectedItems: function(rootsOnly) {
        if (typeof(rootsOnly) == "undefined") rootsOnly = false;
        var indexes = ko.treeutils.getSelectedIndices(gPlacesViewMgr.view,
                                                      rootsOnly);
        return indexes.map(this._getItemByIndex);
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

    'observe': function(subject, topic, data) {
        if (topic == 'visit_directory_proposed') {
            var cancelQuit = subject;
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
        } else if (topic == 'current_project_changed') {
            this._checkProjectMatch();
        } else if (topic == 'file_changed') {
            if (PROJECT_URI_REGEX.text(data)) {
                ko.places.projectsTree.treeBoxObject.invalidate();
            }
        }
    },
    
    handle_project_opened_setup: function(event) {
        ko.places.manager.handle_project_opened(event);
    },
    
    handle_project_opened: function(event) {
        var project = ko.projects.manager.currentProject;
        if (project) {
            var targetDirURI = this._getActualProjectDir(project);
            if (targetDirURI) {
                // Delay, because at startup the tree might not be
                // fully initialized.
                setTimeout(function() {
                        ko.places.manager.openURI(targetDirURI);
                    }, 100);
            }
        }
    },

    placeIsAtProjectDir: function(project) {
        return this.currentPlace == this._getActualProjectDir(project);
    },

    moveToProjectDir: function(project) {
        var projectDirURI = this._getActualProjectDir(project);
        ko.places.manager.openURI(projectDirURI);
    },
    
    _getActualProjectDir: function(project) {
        try {
            var prefset = project.prefset
            var baseDir = prefset.getStringPref("import_dirname");
            if (baseDir) {
                var baseURI = ko.uriparse.localPathToURI(baseDir);
                if (baseURI) {
                    return baseURI;
                }
            } else if (prefset.hasPref("import_live")) {
                var import_live = prefset.getBooleanPref("import_live");
                if (!import_live) {
                    var importedDirs = {};
                    project.getChildrenByType('livefolder', true, importedDirs, {});
                    importedDirs = importedDirs.value;
                    if (importedDirs.length == 1) {
                        var uri = importedDirs[0].url;
                        var koFileEx = Components.classes["@activestate.com/koFileEx;1"].
                            createInstance(Components.interfaces.koIFileEx);
                        koFileEx.URI = uri;
                        if (koFileEx.exists) {
                            return uri;
                        }
                    }
                }
            }
        } catch(ex) {
            // Probably can ignore this.
            log.exception("_getActualProjectDir: " + ex + "\n");
        }
        var uri = project.url;
        return uri.substr(0, uri.lastIndexOf("/"));
    },
    
    refreshItem: function(item) {
        var index = gPlacesViewMgr.view.getRowIndexForURI(item.uri);
        if (index == -1) {
            return;
        }
        gPlacesViewMgr.refreshViewByIndex(index);
    },

    // Menu handlers
    
    rebaseFolder: function(event) {
        var view = gPlacesViewMgr.view;
        var index = view.selection.currentIndex;
        if (index == -1) {
            return;
        }
        this.toggleRebaseFolderByIndex(index);
    },
    
    refreshView: function(event) {
        var view = gPlacesViewMgr.view;
        var index = view.selection.currentIndex;
        if (index == -1) {
            return;
        }
        gPlacesViewMgr.refreshViewByIndex(index);
    },
    __ZIP__: null
};

/** ItemWrapper class -- wrap places URIs in an object
 * that implements old project icons.
 */

function ItemWrapper(uri, type) {
    this.uri = uri;
    this.type = type; // one of 'file', 'folder', or 'project'
}
ItemWrapper.prototype.__defineGetter__("file", function() {
    return this.getFile();
});
ItemWrapper.prototype.__defineGetter__("isLocal", function() {
    return ko.places.manager.currentPlaceIsLocal;
});
ItemWrapper.prototype.getFile = function() {
    if (!('_koFileEx' in this)) {
        var fileObj = Components.classes["@activestate.com/koFileEx;1"].
                      createInstance(Components.interfaces.koIFileEx);
        fileObj.URI = this.uri;
        this._koFileEx = fileObj;
    }
    return this._koFileEx;
};
ItemWrapper.prototype.__defineGetter__("name", function() {
    return this.getFile().leafName;
});
ItemWrapper.prototype.__defineGetter__("prefset", function() {
    if (widgets.rootPathToolbar.getAttribute('class') == 'normal') {
        var view = ko.views.manager.getViewForURI(this.uri);
        if (view) {
            return view.prefs;
        }        
    }
    var currentProject = ko.projects.manager.currentProject;
    return currentProject ? currentProject.prefset : null;
});

this.getItemWrapper = function(url, type) {
    return new ItemWrapper(url, type);
}

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

    var showInFinderMenuItem = document.getElementById("placesContextMenu_showInFinder");
    var platform = navigator.platform.toLowerCase();
    var bundle_id;
    if (platform.substring(0, 3) == "win") {
        bundle_id = "ShowInExplorer.label";
    } else if (platform.substring(0, 5) == "linux") {
        bundle_id = "ShowInFileManager.label";
    } else {
        bundle_id = "ShowInFinder.label";
    }
    showInFinderMenuItem.setAttribute("label",
                                      _bundle.GetStringFromName(bundle_id));
    
    ko.places._instantiateRemoteConnectionService();
    ko.places.viewMgr = gPlacesViewMgr = new viewMgrClass();
    ko.places.viewMgr.initialize();
    ko.places.manager = new ManagerClass();
    widgets.rootPath = document.getElementById("place-view-rootPath");
    widgets.rootPathToolbar = document.getElementById("place-view-rootPath-icon-toolbarbutton");
    widgets.defaultFolderIconSrc = widgets.rootPathToolbar.getAttribute('image');
    widgets.placeView_defaultView_menuitem =
        document.getElementById("placeView_defaultView");
    widgets.placeView_viewAll_menuitem =
        document.getElementById("placeView_viewAll");
    widgets.placeView_customView_menuitem =
        document.getElementById("placeView_customView");
    ko.places.updateFilterViewMenu();
    // The "initialize" routine needs to be in a timeout, otherwise the
    // tree will always show a pending icon and never updates.
    window.setTimeout(function() {
            ko.places.manager.initialize();
        }, 1);
    ko.places._updateSubpanelFromState();
    
    // Wait until ko.projects.manager exists before
    // init'ing the projects view tree.
    var mruProjectViewerID;
    var launch_createProjectMRUView = function() {
        if (ko.projects && ko.projects.manager) {
            clearInterval(mruProjectViewerID);
            ko.places.createProjectMRUView();
        }
    };
    mruProjectViewerID = setInterval(launch_createProjectMRUView, 50);
    ko.places.initProjectMRUCogMenu();
}

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

this.onUnload = function places_onUnload() {
    ko.places.manager.finalize();
    ko.places.viewMgr.finalize();
    ko.places.projectsTreeView.terminate();
    ko.places.manager = ko.places._viewMgr = null;
};

this.createProjectMRUView = function() {
    this.projectsTree = document.getElementById("placesSubpanelProjects");
    this.projectsTreeView = new this.recentProjectsTreeView();
    if (!this.projectsTreeView) {
        throw new Error("couldn't create a recentProjectsTreeView");
    }
    this.projectsTree.treeBoxObject
                        .QueryInterface(Components.interfaces.nsITreeBoxObject)
                        .view = this.projectsTreeView;
    this.projectsTreeView.initialize();    
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
        if (menuNode.hasAttribute("labelTest")) {
            var test = menuNode.getAttribute("labelTest");
            var m = this._projectTestLabelMatcher.exec(test);
            if (m) {
                menuNode.setAttribute("label",
                                  selectionInfo.currentProject ? m[1] : m[2]);
            } else {
                dump("Can't process test [" + test + "]\n");
            }
        }
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
    var index = this.projectsTreeView.selection.currentIndex;
    if (index == -1) {
        return;
    }
    var uri = this.projectsTreeView.getCellValue(index);
    if (inNewWindow) {
        ko.launch.newWindow(uri);
    } else {
        ko.projects.open(uri);
    }
};

this.editProjectProperties = function() {
    ko.projects.fileProperties(
        ko.places.getItemWrapper(
            ko.projects.manager.currentProject.url, 'project'));
};

this.getFocusedPlacesView = function() {
    if (xtk.domutils.elementInFocus(document.getElementById('placesViewbox'))) {
        return this;
    }
    return null;
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

this.updateFilterViewMenu = function() {
    // Find which node is checked.  Then update the menu, maintaining
    // the checked item.  If it was deleted, make the default view the
    // checked one.
    var menupopup = document.getElementById("placeView_toolsPopup");
    var childNodes = menupopup.childNodes;
    for (var idx = menupopup.childElementCount - 1; idx >= 0; --idx) {
        var node = childNodes[idx];
        if (node.id.indexOf("places_custom_filter_") == 0) {
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

xtk.include("treeview");
this.recentProjectsTreeView = function() {
    xtk.dataTreeView.apply(this, []);
    this._atomService = Components.classes["@mozilla.org/atom-service;1"].
                            getService(Components.interfaces.nsIAtomService);
}
this.recentProjectsTreeView.prototype = new xtk.dataTreeView();
this.recentProjectsTreeView.prototype.constructor = this.recentProjectsTreeView;

this.recentProjectsTreeView.prototype.initialize = function() {
    this._resetRows();
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
    observerSvc.addObserver(this, "mru_changed", false);
};
this.recentProjectsTreeView.prototype.terminate = function() {
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    observerSvc.removeObserver(this, "mru_changed");
};

this.recentProjectsTreeView.prototype._resetRows = function() {
    var rows = ko.mru.getAll("mruProjectList").map(function(uri) {
            var m = PROJECT_URI_REGEX.exec(uri);
            if (m) {
                return [uri, m[1]];
            }
            var lastSlash = uri.lastIndexOf('/');
            var extStart = uri.lastIndexOf('.komodoproject');
            if (extStart == -1) {
                extStart = uri.lastIndexOf('.kpf');
            }
            var name = uri.substring(lastSlash + 1, extStart);
            return [uri, name];
        });
    rows.reverse();
    this.rows = rows;
};
this.recentProjectsTreeView.prototype.observe = function(subject, topic, data) {
    if (data == "mruProjectList") {
        this._resetRows();
    }
};
// NSITreeView methods.
this.recentProjectsTreeView.prototype.getCellText = function(row, column) {
    var row = this.rows[row];
    var currentProject = ko.projects.manager.currentProject;
    if (currentProject
        && currentProject.isDirty
        && currentProject.url == row[0]) {
        return row[1] + "*";
    } else {
        return row[1];
    }
};
this.recentProjectsTreeView.prototype.getCellValue = function(row, column) {
    return this.rows[row][0];
};
this.recentProjectsTreeView.prototype.getImageSrc = function(row, column) {
    return 'chrome://komodo/skin/images/project_icon.png'
};
this.recentProjectsTreeView.prototype.getCellProperties = function(index, column, properties) {
    var row = this.rows[index];
    var currentProject = ko.projects.manager.currentProject;
    if (currentProject && currentProject.url == row[0]) {
        properties.AppendElement(this._atomService.getAtom("projectActive"));
    }
};

}).apply(ko.places);
