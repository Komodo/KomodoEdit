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
const CURRENT_PROJECT_FILTER_NAME = _bundle.GetStringFromName("currentProject.filterName");
const DEFAULT_FILTER_NAME = _bundle.GetStringFromName("default.filterName");
const VIEW_ALL_FILTER_NAME = _bundle.GetStringFromName("viewAll.filterName");
const VERSION = 1;

var _placePrefs;
var filterPrefs;
var uriSpecificPrefs;
var projectSpecificFilterPrefs;
const MAX_URI_PREFS_TO_TRACK = 60;
const MAX_PROJECT_URI_PREFS_TO_TRACK = 20;
var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

var widgets = {};
var osPathSvc;

const DEFAULT_EXCLUDE_MATCHES = "*~;#*;CVS;*.bak;*.pyo;*.pyc;.svn;.git;.hg;.bzr;.DS_Store";
const DEFAULT_INCLUDE_MATCHES = "";

const PROJECT_URI_REGEX = /^.*\/(.+?)\.(?:kpf|komodoproject)$/;

var log = getLoggingMgr().getLogger("places_js");
log.setLevel(LOG_DEBUG);

// Yeah, not really a class per se, but it acts like one, so
// give it an appropriate name.
// This object will manage the JS side of the tree view.
function viewMgrClass() {
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
        //  _arrowKeys used by onTreeKeyPress, easier to init here.
        var nsIDOMKeyEvent = Components.interfaces.nsIDOMKeyEvent;
        this._arrowKeys = [nsIDOMKeyEvent.DOM_VK_UP,
                           nsIDOMKeyEvent.DOM_VK_DOWN,
                           nsIDOMKeyEvent.DOM_VK_LEFT,
                           nsIDOMKeyEvent.DOM_VK_RIGHT];
        var prefsToWatch = ["import_exclude_matches", "import_include_matches"];
        _globalPrefs.prefObserverService.addObserverForTopics(this,
                                                              prefsToWatch.length,
                                                              prefsToWatch, false);
    },

    observe: function(subject, topic, data) {
        var project;
        if (["import_exclude_matches", "import_exclude_matches"].indexOf(topic)
            >= 0
            && (widgets.placeView_currentProject_menuitem.getAttribute('checked')
                == 'true')
            && (project = ko.projects.manager.currentProject)) {
            this._updateViewPrefsFromProjectPrefs(project);
        }
    },

    _updateViewPrefsFromProjectPrefs: function(project) {
        var prefset = project.prefset;
        try {
            gPlacesViewMgr.view.setMainFilters(prefset.getStringPref('import_exclude_matches'),
                                           prefset.getStringPref('import_include_matches'));
        } catch(ex) {
            log.exception("getting prefs failed: " + ex + "\n");
            this.placeView_defaultView();
        }
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
        var index = ko.places.manager._clickedOnRoot() ? -1 : this.view.selection.currentIndex;
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFileName"));
        if (!name) return;
        try {
            this.view.addNewFileAtParent(name, index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        }
    },

    addNewFolder: function() {
        var index = ko.places.manager._clickedOnRoot() ? -1 : this.view.selection.currentIndex;
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
        if (index == -1) {
            this.view.selection.clearSelection();
        } else {
            this.view.markRow(index);
        }
    },

    handleReturnKeyPress: function(event) {
        // Either open one file or rebase one folder. Mixtures not allowed.
        var folderIndexToUse = null;
        var urisToOpen = [];
        var selectedIndices = ko.treeutils.getSelectedIndices(this.view, false);
        var selectedURIs = ko.places.manager.getSelectedUris();
        for (var index, i = 0; i < selectedIndices.length; i++) {
            index = selectedIndices[i];
            if (this.view.isContainer(index)) {
                if (folderIndexToUse !== null) {
                    ko.dialogs.alert(_bundle.GetStringFromName("selectOnlyOneFolder.prompt"));
                    return;
                }
                folderIndexToUse = index;
            } else {
                urisToOpen.push(this.view.getURIForRow(index));
            }
        }
        if (urisToOpen.length && folderIndexToUse !== null) {
            ko.dialogs.alert(_bundle.GetStringFromName("selectionContainsMixtureOfFilesAndFolders.prompt"));
            return;            
        }
        if (urisToOpen.length) {
            ko.open.multipleURIs(urisToOpen);
        } else if (folderIndexToUse !== null) {
            ko.places.manager.toggleRebaseFolderByIndex(index);
        }
    },

    onTreeKeyPress: function(event) {
        var t = event.originalTarget;
        if (t.localName != "treechildren" && t.localName != 'tree') {
            return false;
        }
        if (this._arrowKeys.indexOf(event.keyCode) >= 0) {
            // Nothing to do but squelch the keycode
            event.stopPropagation();
            event.preventDefault();
            return false;
        }
        //dump("TODO: viewMgrClass.onTreeKeyPress\n");
        if (event.shiftKey || event.ctrlKey || event.altKey) {
            return false;
        }
        if (event.keyCode == event.DOM_VK_ENTER
            || event.keyCode == event.DOM_VK_RETURN) {
            // ENTER/RETURN should be handled by xbl bindings.
            event.stopPropagation();
            event.preventDefault();
            return true;
        } else if (event.keyCode == event.DOM_VK_DELETE) {
            ko.places.manager.doDeletePlace();
        } else {
            return false;
        }
        event.cancelBubble = true;
        event.stopPropagation();
        event.preventDefault();
        return true;
    },

    allowed_click_nodes: ["places-files-tree-body",
                          "placesRootButton",
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
        var selectedIndices = ko.treeutils.getSelectedIndices(this.view, false /*rootsOnly*/);
        if (index == -1) {
            clickedNodeId = "placesRootButton";
        }
        var selectedIndices = ko.treeutils.getSelectedIndices(this.view, false /*rootsOnly*/);
        var isRootNode;
        var itemTypes = null;
        if (clickedNodeId == "placesRootButton") {
            index = -1;
            isRootNode = true;
            itemTypes = ["project"];
        } else {
            index = this._currentRow(event);
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
        var disableAll = (isRootNode && widgets.rootButton.label == "");
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
                dt.mozSetDataAt("text/x-moz-url", uri, i);
                dt.mozSetDataAt("text/uri-list", uri, i);
                dt.mozSetDataAt('text/plain', ko.uriparse.URIToLocalPath(uri), i);
            } else {
                dt.mozSetDataAt("text/x-moz-url", uri, i);
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
        if (!dt) {
            log.info("_checkDragSource: No dataTransfer");
            return false;
        }
        for (var i = 0; i < dt.mozItemCount; i++) {
            if (!event.dataTransfer.mozTypesAt(i).contains("text/uri-list")
                && !event.dataTransfer.mozTypesAt(i).contains("text/x-moz-url")) {
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
        } else {
            retVal = true;
            //dump("this.originalEffect: " + this.originalEffect + "\n");
        }
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "copyMove";
        } else {
            log.debug("_checkDrag: no event.dataTransfer");
        }
        return retVal;
    },
    _addTrailingSlash: function(uri) {
        if (uri[uri.length - 1] != "/") {
            return uri + "/";
        }
        return uri;
    },

    _removeTrailingSlash: function(uri) {
        if (uri[uri.length - 1] == "/") {
            return uri.substring(0, uri.length - 1);
        }
        return uri;
    },

    _getDraggedURIs: function(event) {
        var dt = event.dataTransfer;
        var koDropDataList = ko.dragdrop.unpackDropData(dt);
        var from_uris = [];
        for (var i = 0; i < koDropDataList.length; i++) {
            var koDropData = koDropDataList[i];
            from_uris.push(koDropData.value);
            
        }
        var dropEffect = dt.dropEffect;
        return [from_uris, dropEffect];
    },

    doDrop : function(event, tree) {
        var index = this._currentRow(event);
        if (index == -1) {
            this.doDropOnRootNode(event, tree);
            return true;
        }
        var treeView = gPlacesViewMgr.view;
        var target_uri;
        if (treeView.isContainer(index)) {
            target_uri = treeView.getURIForRow(index);
        } else if (treeView.getLevel(index) == 0) {
            target_uri = ko.places.manager.currentPlace;
        } else {
            var parentIndex = treeView.getParentIndex(index);
            if (parentIndex == -1) {
                log.error("Can't find a parent index for index:" + index);
                return true;
            }
            index = parentIndex;
            target_uri = treeView.getURIForRow(index);
        }
        if (!this._finishDrop(event, target_uri, index)) {
            event.stopPropagation();
            event.preventDefault();
            return false;
        }
        return true;
    },

    _dropProblem: function(msg) {
        log.error(msg);
        ko.statusBar.AddMessage(msg, "editor", 10 * 1000, true);
        return false;
    },
    
    _finishDrop : function(event, target_uri, index) {
        var dt = event.dataTransfer;
        var from_uris, dropEffect, copying;
        [from_uris, dropEffect] = this._getDraggedURIs(event);
        if (from_uris.length == 0) {
            return this._dropProblem("_finishDrop: no from_uris");
        } else if (dropEffect == "none") {
            return this._dropProblem("_finishDrop: no drag/drop here");
        } else if (dropEffect == "link") {
            return this._dropProblem("don't know how to drag/drop a link");
        }
        var target_uri_no_slash = this._removeTrailingSlash(target_uri);
        for (var i = 0; i < from_uris.length; i++) {
            var source_uri = from_uris[i];
            var source_uri_no_slash = this._removeTrailingSlash(source_uri);
            if (target_uri_no_slash == source_uri_no_slash) {
                return this._dropProblem("places.doDrop: can't drop directory "
                                    + source_uri_no_slash
                                    + " onto itself");
                return false;
            }
            var source_uri_parent_no_slash = source_uri_no_slash.substr(0, source_uri_no_slash.lastIndexOf("/"));
            if (target_uri_no_slash == source_uri_parent_no_slash) {
                return this._dropProblem("places.doDrop: can't drop the item "
                                    + source_uri_no_slash
                                    + " onto its parent.");
                return false;
            }
            else if (target_uri.indexOf(this._addTrailingSlash(source_uri_no_slash)) == 0) {
                return this._dropProblem("places.doDrop: can't drop the item "
                                    + source_uri
                                    + " onto its  descendant "
                                    + target_uri);
                return false;
            }
        }

        // See bug 87924
        copying = (dropEffect != 'none' ? dropEffect == "copy" : event.ctrlKey);
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
        if (!this._finishDrop(event, target_uri, -1)) {
            event.stopPropagation();
            event.preventDefault();
            return false;
        }
        return true;
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
        prefSet.setStringPref('timestamp', new Date().valueOf());

        // And do project-specific views
        var project = ko.projects.manager.currentProject;
        if (project) {
            if (!projectSpecificFilterPrefs.hasPref(project.url)) {
                prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
                projectSpecificFilterPrefs.setPref(project.url, prefSet);
            } else {
                prefSet = projectSpecificFilterPrefs.getPref(project.url);
            }
            prefSet.setStringPref("viewName", viewName);
            prefSet.setStringPref('timestamp', new Date().valueOf());
        }
    },

    _getCurrentFilterPrefName: function() {
        var uri = ko.places.manager.currentPlace;
        if (!uri) return null;
        var prefSet;
        if (uriSpecificPrefs.hasPref(uri)) {
            prefSet = uriSpecificPrefs.getPref(uri);
            if (!prefSet.hasStringPref('viewName')) {
                return null;
            }
            prefSet.setStringPref('timestamp', new Date().valueOf());
            return prefSet.getStringPref('viewName');
        } else {
            return null;
        }
    },                

    placeView_defaultView: function() {
        var pref = filterPrefs.getPref(DEFAULT_FILTER_NAME);
        var exclude_matches = pref.getStringPref("exclude_matches");
        var include_matches = pref.getStringPref("include_matches");
        gPlacesViewMgr.view.setMainFilters(pref.getStringPref("exclude_matches"),
                                           pref.getStringPref("include_matches"));
        gPlacesViewMgr._uncheckAll();
        widgets.placeView_defaultView_menuitem.setAttribute('checked', 'true');
        this._updateCurrentUriViewPref("Default");
    },

    placeView_currentProject: function() {
        var project = ko.projects.manager.currentProject;
        if (!project) {
            this.placeView_defaultView();
            return;
        }
        gPlacesViewMgr._uncheckAll();
        widgets.placeView_currentProject_menuitem.setAttribute('checked', 'true');
        this._updateCurrentUriViewPref(CURRENT_PROJECT_FILTER_NAME);
        this._updateViewPrefsFromProjectPrefs(project);
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
            log.exception("Can't find prefName '"
                          + prefName
                          + "' in menu:: " + ex + "\n");
            return false;
        }
    },

    placeView_customView: function() {
        // Use the same format as managing the list of servers.
        var currentFilterName = this._getCurrentFilterPrefName();
        var resultObj = {needsChange:false,
                         currentFilterName:currentFilterName,
                         version:VERSION};
        ko.windowManager.openDialog("chrome://places/content/manageViewFilters.xul",
                                    "_blank",
                                    "chrome,all,dialog=yes,modal=yes",
                                    resultObj);
        if (resultObj.needsChange) {
            ko.places.updateFilterViewMenu();
            var viewName = resultObj.currentFilterName;
            if (viewName) {
                ko.places.viewMgr.placeView_updateView(viewName);
            }
        }
    },
    
    placeView_updateView: function(viewName) {
        if (viewName == null || viewName == DEFAULT_FILTER_NAME) {
            this.placeView_defaultView();
            return DEFAULT_FILTER_NAME;
        } else if (viewName == VIEW_ALL_FILTER_NAME) {
            this.placeView_viewAll();
            return viewName;
        } else if (viewName == CURRENT_PROJECT_FILTER_NAME) {
            this.placeView_currentProject();
            return viewName;
        } else if (!filterPrefs.hasPref(viewName)) {
            // do default.
        } else {
            if (this.placeView_selectCustomView(viewName)) {
                return viewName;
            }
        }
        this.placeView_defaultView();
        return DEFAULT_FILTER_NAME;
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
    
    document.getElementById("places-files-tree").addEventListener('keypress',
                            this.handle_keypress_setup, true);
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
        try {
            this.openDirectory(dir);
        } catch(ex) {
            _notify(ex.message || ex);
            return;
        }
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
        this.openDirURI(uri);
    },

    /* Set the given local directory path as the root in places
     *
     * @param dir {String} The directory to open.
     * @param baseName {String} Optional file basename in the directory
     *      to select.
     * @exception {"message": <error-message>} if the dir doesn't exist or isn't
     *      a directory.
     */
    openDirectory: function(dir, baseName) {
        var err;
        if (!osPathSvc.exists(dir)) {
            throw {
                "message": _bundle.formatStringFromName(
                    'doesNotExist', [dir], 1)
            };
        } else if (!osPathSvc.isdir(dir)) {
            throw {
                "message": _bundle.formatStringFromName(
                    'isNotADirectory', [dir], 1)
            };
        }
        var dirURI = ko.uriparse.localPathToURI(dir);
        this.openDirURI(dirURI, baseName);
        this._enterMRU_Place(dirURI);
    },

    /* Set the given directory URI as the root in places.
     *
     * @param dirURI {String} The directory URI to open.
     * @param baseName {String} Optional file base name in the directory
     *      to select.
     */
    openDirURI: function(dirURI, baseName) {
        this._enterMRU_Place(dirURI);
        this._setDirURI(dirURI,
                        {save:true,
                                baseName:baseName,
                                onSuccess:this._setDirURI_successFunc_show_tab});
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
        this._setDirURI(uri, {save:true});
    },

    _checkProjectMatch: function() {
        var classValue =  (this.currentPlaceIsLocal ? "normal" : "remote");
        widgets.rootButton.setAttribute('class', classValue);
    },

    _currentPlaceMatchesCurrentProject: function() {
        var uri = this.currentPlace;
        var project = ko.projects.manager.currentProject;
        if (!uri || !project) {
            return false;
        }
        var targetDirURI = project.importDirectoryURI;
        return uri == targetDirURI;
    },
    
    /* Change places to the given dir.
     *
     * @param dirURI {string} The directory to which to switch, as a URI.
     *      This is presumed to be a directory (i.e. not a file) and to
     *      exist.
     * @param args {Object} Can contain the following fields
     *        save {Boolean} Whether to save this dir in the places dir history.
     *      Default is false.
     *        onSuccess {void(void)}: function to call from callback on success
     *      Default is null.
     *        onFailure {void(void)}: function to call from callback on failure
     *      Default is null.
     *        baseName {String} Optional file base name in the dir to select.
     *      If the base name cannot be found in the directory, no error is
     *      raised.
     */
    _setDirURI: function(dirURI, args) {
        var save = args.save === undefined ? false : args.save;
        var baseName = args.baseName === undefined ? null : args.baseName;
        var onSuccess = args.onSuccess === undefined ? null : args.onSuccess;
        var onFailure = args.onFailure === undefined ? null : args.onFailure;

        var this_ = this;
        var statusNode = document.getElementById("placesRootButton");
        var busyURI = "chrome://global/skin/icons/loading_16.png";
        statusNode.setAttribute('image', busyURI);

        var koFile = Components.classes["@activestate.com/koFileEx;1"].
                createInstance(Components.interfaces.koIFileEx);
        koFile.URI = dirURI;
        this.currentPlaceIsLocal = koFile.isLocal;

        this.currentPlace = dirURI;
        var file = Components.classes["@activestate.com/koFileEx;1"].
            createInstance(Components.interfaces.koIFileEx);
        file.URI = dirURI;
        // watch out: baseName("/") => ""
        widgets.rootButton.label = file.baseName || file.path;
        this._checkProjectMatch();
        widgets.rootButton.tooltipText = (
            file.scheme == "file" ? file.displayPath : dirURI);

        var this_ = this;
        var callback = {    // koIAsyncCallback
            callback: function(result, data) {
                statusNode.setAttribute('image', widgets.defaultFolderIconSrc);
                if (data != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    widgets.rootButton.label = "";
                    widgets.rootButton.tooltipText = "";
                    this_.currentPlace = null;
                    ko.dialogs.alert(data);
                    if (onFailure) {
                        try {
                            onFailure.apply(this_);
                        } catch(ex) {
                            log.exception("_setDirURI::onFailure: " + ex);
                        }
                    }
                } else {
                    if (baseName) {
                        var uri = dirURI + '/' + baseName;
                        ko.places.viewMgr.view.selectURI(uri);
                    }
                    window.setTimeout(window.updateCommands, 1,
                                      "current_place_opened");
                    if (save) {
                        _placePrefs.setStringPref(window._koNum, dirURI);
                    }
                    var viewName = null;
                    var prefSet;
                    var project = ko.projects.manager.currentProject;
                    if (project) {
                        if (!projectSpecificFilterPrefs.hasPref(project.url)) {
                            viewName = CURRENT_PROJECT_FILTER_NAME;
                            prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
                            projectSpecificFilterPrefs.setPref(project.url, prefSet);
                            prefSet.setStringPref("viewName", viewName);
                        } else {
                            prefSet = projectSpecificFilterPrefs.getPref(project.url);
                            viewName = prefSet.getStringPref("viewName");
                            prefSet.setStringPref('timestamp', new Date().valueOf());
                        }
                        gPlacesViewMgr.placeView_updateView(viewName);
                    }
                    if (viewName === null) {
                        if (uriSpecificPrefs.hasPref(dirURI)) {
                            prefSet = uriSpecificPrefs.getPref(dirURI);
                            try {
                                viewName = prefSet.getStringPref('viewName')
                                    } catch(ex) {}
                            var finalViewName = gPlacesViewMgr.placeView_updateView(viewName);
                            if (finalViewName != viewName) {
                                prefSet.setStringPref('viewName', finalViewName);
                                prefSet.setStringPref('timestamp', new Date().valueOf());
                                    }
                        } else {
                            var finalViewName = gPlacesViewMgr.placeView_updateView(null);
                            prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
                            prefSet.setStringPref('viewName', finalViewName);
                            prefSet.setStringPref('timestamp', new Date().valueOf());
                            uriSpecificPrefs.setPref(dirURI, prefSet);
                        }
                    }
                    if (onSuccess) {
                        try {
                            onSuccess.apply(this_);
                        } catch(ex) {
                            log.exception("_setDirURI::onSuccess: " + ex);
                        }
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
        var uriList;
        if (this._clickedOnRoot()) {
            uriList = this.currentPlace;
        } else {
            var uris = gPlacesViewMgr.getSelectedURIs(true);
            uriList = uris.join("\n");
        }
        var transferable = xtk.clipboard.addTextDataFlavor("text/unicode", uriList);
        xtk.clipboard.addTextDataFlavor("x-application/komodo-places",
                                        isCopying ? "1" : "0" , transferable);
        xtk.clipboard.copyFromTransferable(transferable);
        window.setTimeout(window.updateCommands, 1, "clipboard");
    },

    doPastePlaceItem: function() {
        var srcURIs = null;
        if (xtk.clipboard.containsFlavors(['text/uri-list'])) {
            srcURIs = xtk.clipboard.getTextFlavor('text/uri-list').split(/\n/);
        } else {
            srcURIs = xtk.clipboard.getText().split(/\n/);
        }
        var isCopying = true;
        if (xtk.clipboard.containsFlavors(["x-application/komodo-places"])) {
            isCopying = parseInt(xtk.clipboard.getTextFlavor("x-application/komodo-places"));
        }
        var target_uri;
        var index;
        if (this._clickedOnRoot()) {
            index = -1;
            target_uri = this.currentPlace;
        } else {
            index = gPlacesViewMgr.view.selection.currentIndex;
            target_uri = gPlacesViewMgr.view.getURIForRow(index);
        }
        var koTargetFileEx = Components.classes["@activestate.com/koFileEx;1"].
                             createInstance(Components.interfaces.koIFileEx);
        koTargetFileEx.URI = target_uri;
        if (koTargetFileEx.isFile) {
            target_uri = target_uri.substr(0, target_uri.lastIndexOf("/"));
            var parent_index = gPlacesViewMgr.view.getRowIndexForURI(target_uri);
            if (parent_index == -1) {
                // Are we at top-level?
                if (gPlacesViewMgr.view.getLevel(index) == 0) {
                    index = -1;
                } else {
                    var prompt = _bundle.formatStringFromName('cantFindFilesParentInTree.prompt',
                                                              [koTargetFileEx.displayPath], 1);
                    ko.dialogs.alert(prompt);
                    return;
                }
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
        if (document.popupNode == widgets.rootButton) return true;
        return (document.popupNode.id == "places-files-tree-body"
                && gPlacesViewMgr.view.selection.count == 0);
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
                       : _bundle.formatStringFromName("selectedPluralFolders.piece",
                                                      [nonEmptyFolders.length], 1)));
        }
        if (otherItemCount) {
            if (nonEmptyFolders.length) {
                msg += " " + _bundle.GetStringFromName("and.piece") + " ";
            } else {
                msg = _bundle.GetStringFromName("youHaveSelected.piece") + " ";
            }
            msg += (otherItemCount == 1
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
                var successFunc = function() {
                    // If we're moving to a URI that's in the history list,
                    // pull it out.
                    var names = {'history_prevPlaces':null,
                                 'history_forwardPlaces':null};
                    for (var name in names) {
                        var index = this[name].indexOf(uri);
                        if (index > -1) {
                            this[name].splice(index, 1);
                        }
                    }
                };
                this._setDirURI(uri, {save:false, onSuccess:successFunc});
            } catch(ex) {}
        }
        try {
            var placesPrefs = _globalPrefs.getPref("places");
            var name_list = ['lastLocalDirectoryChoice', 'lastRemoteDirectoryChoice', 'lastHomePlace'];
            name_list.map(function(name) {
                if (placesPrefs.hasStringPref(name)) {
                    this[name] = placesPrefs.getStringPref(name);
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
        document.getElementById("places-files-tree").removeEventListener('keypress',
                                   this.handle_keypress_setup, true);
    },
    
    goUpOneFolder: function() {
        var uri = ko.places.manager.currentPlace;
        var lastSlashIdx = uri.lastIndexOf("/");
        if (lastSlashIdx == -1) return;
        var parent_uri = uri.substr(0, lastSlashIdx);
        this._enterMRU_Place(parent_uri);
        this._setDirURI(parent_uri, {save:true});
    },

    can_goPreviousPlace: function() {
        return this.history_prevPlaces.length > 0;
    },

    _setDirURI_successFunc_history_changed: function() {
        window.updateCommands('place_history_changed');
    },

    _setDirURI_successFunc_show_tab: function() {
        // Don't cause a focus change triggered from workspace restore - bug 87868.
        if (ko.projects.manager._project_opened_during_workspace_restore) {
            ko.uilayout.ensureTabShown("places_tab", false);
            ko.projects.manager._project_opened_during_workspace_restore = false;
        } else {
            ko.uilayout.ensureTabShown("places_tab", true);
        }
    },
    
    goPreviousPlace: function() {
        if (this.history_prevPlaces.length == 0) {
            return;
        }
        var currentURI = this.currentPlace;
        var targetURI = this.history_prevPlaces.pop();
        if (currentURI) {
            this.history_forwardPlaces.unshift(currentURI);
        }
        var failureFunc = function() {
            if (this.history_prevPlaces.length) {
                targetURI = this.history_prevPlaces.pop();
                this._setDirURI(targetURI, {save:false,
                                            onSuccess:this._setDirURI_successFunc_history_changed,
                                            onFailure:failureFunc});
            } else {
                // Go back to the starting place
                this.history_forwardPlaces.shift();
                this._setDirURI(currentURI,
                                {save:false, onSuccess:this._setDirURI_successFunc_history_changed});
            }
        };
        this._setDirURI(targetURI,
                        {save:false, onSuccess:this._setDirURI_successFunc_history_changed,
                         onFailure:failureFunc});
    },

    can_goNextPlace: function() {
        return this.history_forwardPlaces.length > 0;
    },

    goNextPlace: function() {
        if (this.history_forwardPlaces.length == 0) {
            return;
        }
        var currentURI = this.currentPlace;
        var targetURI = this.history_forwardPlaces.shift();
        if (currentURI) {
            this.history_prevPlaces.push(currentURI);
        }
        var failureFunc = function() {
            if (this.history_forwardPlaces.length) {
                targetURI = this.history_forwardPlaces.shift();
                this._setDirURI(targetURI, {save:false,
                                            onSuccess:this._setDirURI_successFunc_history_changed,
                                            onFailure:failureFunc});
            } else {
                // Go back to the starting place
                this.history_prevPlaces.pop();
                this._setDirURI(currentURI,
                                {save:false, onSuccess:this._setDirURI_successFunc_history_changed});
            }
        };
        this._setDirURI(targetURI,
                        {save:false, onSuccess:this._setDirURI_successFunc_history_changed,
                         onFailure:failureFunc});
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
        var currentURI = this.currentPlace;
        var blocks = [this.history_forwardPlaces,
                      currentURI ? [currentURI] : [],
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
        var isUNC = new RegExp('^file://[^/]+/$');
        if (isUNC.test(uriLeader)) {
            parts.shift();
        }
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
                                      ('ko.places.manager.openDirURI("'
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
        }
        var failureFunc = null;
        var currentURI = this.currentPlace;
        var partsToShift = [];
        if (blockCode == 'B') {
            uri = this.history_prevPlaces[index];
            this.history_prevPlaces.splice(index, 1);
            partsToShift = this.history_prevPlaces.splice(index);
            if (currentURI) {
                partsToShift.push(currentURI);
            }
            if (partsToShift.length) {
                this.history_forwardPlaces = partsToShift.concat(this.history_forwardPlaces);
            }
            failureFunc = function() {
                var partsToShiftBack = this.history_forwardPlaces.splice(0, partsToShift.length);
                this.history_prevPlaces = this.history_prevPlaces.concat(partsToShiftBack);
                // remove the currentURI from the forward block
                if (currentURI) {
                    this.history_forwardPlaces.shift();
                    this._setDirURI(currentURI, {save:false});
                } // else no place to go back to
            }
        } else {
            var uri = this.history_forwardPlaces[index];
            var shiftBackIndex = this.history_prevPlaces.length;
            this.history_forwardPlaces.splice(index, 1);
            if (currentURI) {
                this.history_prevPlaces.push(currentURI);
                shiftBackIndex += 1;
            }
            if (index > 0) {
                partsToShift = this.history_forwardPlaces.splice(0, index);
                this.history_prevPlaces = this.history_prevPlaces.concat(partsToShift);
            }
            failureFunc = function() {
                var partsToShiftBack = this.history_prevPlaces.splice(shiftBackIndex);
                this.history_forwardPlaces = partsToShiftBack.concat(this.history_forwardPlaces.concat);
                // remove the currentURI from the prev block
                if (currentURI) {
                    this.history_prevPlaces.pop();
                    this._setDirURI(currentURI, {save:false});
                } else {
                    // No place to go back to.
                }
            }
        }
        this._setDirURI(uri, {save:true,
                              onSuccess:this._setDirURI_successFunc_history_changed,
                              onFailure:failureFunc});
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
        var sorter = function(a, b) {
            var t1 = a[2];
            var t2 = b[2];
            if (t1.length == t2.length) {
                var s1 = t1.toLowerCase();
                var s2 = t2.toLowerCase();
                return s1 < s2 ? -1 : s1 > s2 ? +1 : 0;
            }
            return t1.length - t2.length;
        }
        var removeOldestViewTrackers = function(prefName, maxArraySize) {
            var ids = {};
            var uriPrefs = _placePrefs.getPref(prefName);
            uriPrefs.getPrefIds(ids, {});
            ids = ids.value;
            if (ids.length > maxArraySize) {
                var nameValueTimeArray = ids.map(function(id) {
                        var pref = uriPrefs.getPref(id);
                        return [id,
                                pref.getStringPref("viewName"),
                                (pref.hasPref("timestamp")
                                 ? pref.getStringPref("timestamp") : "0")];
                    });
                nameValueTimeArray.sort(sorter);
                var numToExcise = nameValueTimeArray.length - maxArraySize;
                for (var i = 0; i < numToExcise; i++) {
                    uriPrefs.deletePref(nameValueTimeArray[i][0]);
                }
            }
        }
        removeOldestViewTrackers("current_filter_by_uri",
                                 MAX_URI_PREFS_TO_TRACK);
        removeOldestViewTrackers("current_project_filter_by_uri",
                                 MAX_PROJECT_URI_PREFS_TO_TRACK);
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
                try {
                    ko.places.manager.openDirectory(data);
                } catch(ex) {
                    _notify(ex.message || ex);
                    return;
                }
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
    
    handle_keypress_setup: function(event) {
        return ko.places.viewMgr.onTreeKeyPress(event);
    },
    
    handle_project_opened: function(event) {
        var project = ko.projects.manager.currentProject;
        if (project) {
            var targetDirURI = project.importDirectoryURI;
            if (targetDirURI) {
                // Delay, because at startup the tree might not be
                // fully initialized.
                setTimeout(function() {
                        var currentProjectFilterPrefs = filterPrefs.getPref(CURRENT_PROJECT_FILTER_NAME);
                        ["include_matches", "exclude_matches"].map(function(name) {
                                currentProjectFilterPrefs.setStringPref(name,
                                                                        project.prefset.getStringPref("import_" + name));
                });
                        ko.places.manager.openDirURI(targetDirURI);
                    }, 100);
            }
        }
    },

    placeIsAtProjectDir: function(project) {
        return this.currentPlace == project.importDirectoryURI;
    },

    moveToProjectDir: function(project) {
        var projectDirURI = project.importDirectoryURI;
        ko.places.manager.openDirURI(projectDirURI);
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
    if (type == 'project') {
        this.project = ko.projects.manager.currentProject;
    }
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
    if (widgets.rootButton.getAttribute('class') == 'normal') {
        var view = ko.views.manager.getViewForURI(this.uri);
        if (view) {
            return view.prefs;
        }        
    }
    return this.project && this.project.prefset;
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

// In this function 'this' is top (window)
this.onLoad = function places_onLoad() {
    ko.main.addWillCloseHandler(ko.places.onUnload);
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
    if (!filterPrefs.hasPref(DEFAULT_FILTER_NAME)) {
        //dump("global/places/filters prefs has no " + DEFAULT_FILTER_NAME + "\n");
        var prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        prefSet.setStringPref("exclude_matches", DEFAULT_EXCLUDE_MATCHES);
        prefSet.setStringPref("include_matches", DEFAULT_INCLUDE_MATCHES);
        prefSet.setBooleanPref("builtin", true);
        prefSet.setBooleanPref("readonly", false);
        prefSet.setLongPref("version", VERSION);
        filterPrefs.setPref(DEFAULT_FILTER_NAME, prefSet);
    } else {
        //Fix a pre-6.0.0 mistake, making this readonly, and removing the old default (it it's there)
        var defaultPrefs = filterPrefs.getPref(DEFAULT_FILTER_NAME);
        if (!defaultPrefs.hasPref("version")) {
            defaultPrefs.setStringPref("include_matches", DEFAULT_INCLUDE_MATCHES);
            defaultPrefs.setBooleanPref("readonly", false);
            defaultPrefs.setLongPref("version", VERSION);
        }
    }
    if (!filterPrefs.hasPref(VIEW_ALL_FILTER_NAME)) {
        prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        prefSet.setStringPref("exclude_matches", "");
        prefSet.setStringPref("include_matches", "");
        prefSet.setBooleanPref("readonly", true);
        prefSet.setBooleanPref("builtin", true);
        prefSet.setLongPref("version", VERSION);
        filterPrefs.setPref(VIEW_ALL_FILTER_NAME, prefSet);
    }
    if (!filterPrefs.hasPref(CURRENT_PROJECT_FILTER_NAME)) {
        prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        // These filters aren't actually used, but it's easier if this
        // filter is fully built up for the menus.
        prefSet.setStringPref("exclude_matches", "");
        prefSet.setStringPref("include_matches", "");
        prefSet.setBooleanPref("builtin", true);
        prefSet.setBooleanPref("readonly", false);
        prefSet.setLongPref("version", VERSION);
        filterPrefs.setPref(CURRENT_PROJECT_FILTER_NAME, prefSet);
    } else {
        //Fix a pre-6.0.0 mistake, making this readonly.
        filterPrefs.getPref(DEFAULT_FILTER_NAME).setBooleanPref("readonly", false);
    }
    
    if (!_placePrefs.hasPref('current_filter_by_uri')) {
        uriSpecificPrefs = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        _placePrefs.setPref('current_filter_by_uri', uriSpecificPrefs);
    } else {
        uriSpecificPrefs = _placePrefs.getPref('current_filter_by_uri');
    }
    if (!_placePrefs.hasPref('current_project_filter_by_uri')) {
        projectSpecificFilterPrefs = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
        _placePrefs.setPref('current_project_filter_by_uri', projectSpecificFilterPrefs);
    } else {
        projectSpecificFilterPrefs = _placePrefs.getPref('current_project_filter_by_uri');
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
    widgets.rootButton = document.getElementById("placesRootButton");
    widgets.defaultFolderIconSrc = widgets.rootButton.getAttribute('image');
    widgets.placeView_defaultView_menuitem =
        document.getElementById("placeView_defaultView");
    widgets.placeView_currentProject_menuitem =
        document.getElementById("placeView_currentProject");
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
    }
    return true;
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

this.removeProjectListing = function() {
    var index = this.projectsTreeView.selection.currentIndex;
    if (index == -1) {
        log.debug("removeProjectListing: No index");
        return;
    }
    var uri = this.projectsTreeView.getCellValue(index);
    if (!uri) {
        log.debug("removeProjectListing: No uri at index:" + index);
        return;
    }
    ko.mru.deleteValue('mruProjectList', uri, true/*notify */);
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
    var item = ko.places.getItemWrapper(ko.projects.manager.currentProject.url, 'project');
    ko.projects.fileProperties(item, null, true);
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
    var sep = document.getElementById("places_manage_view_separator");
    var menuitem;
    var addedCustomFilter = false;
    var nextId = document.getElementById("placeView_viewAll").nextSibling.id;
    var willNeedCustomSeparator = (nextId == "places_manage_view_separator");
    ids.map(function(prefName) {
        if (!filterPrefs.getPref(prefName).hasBooleanPref("builtin")) {
            menuitem = document.createElementNS(XUL_NS, 'menuitem');
            menuitem.setAttribute("id", "places_custom_filter_" + prefName);
            menuitem.setAttribute('label',  prefName);
            menuitem.setAttribute("type", "checkbox");
            menuitem.setAttribute("checked", "false");
            menuitem.setAttribute("oncommand", "ko.places.viewMgr.placeView_selectCustomView('" + prefName + "');");
            menupopup.insertBefore(menuitem, sep);
            addedCustomFilter = true;
        }
    });
    if (addedCustomFilter && willNeedCustomSeparator) {
        menuitem = document.createElementNS(XUL_NS, 'menuseparator');
        menuitem.id = "popup_parent_directories:sep:customViews";
        menupopup.insertBefore(menuitem,
                               document.getElementById("placeView_viewAll").nextSibling);
    } else if (!addedCustomFilter && !willNeedCustomSeparator) {
        var sepNode = document.getElementById("popup_parent_directories:sep:customViews");
        if (sepNode) {
            sepNode.parentNode.removeChild(sepNode);
        }
    }
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
    try {
        observerSvc.removeObserver(this, "mru_changed");
    } catch(ex) {
        // Sometimes during shutdown this throws a 0x80004005 exception
    }
};

this.recentProjectsTreeView.prototype._resetRows = function() {
    var rows = ko.mru.getAll("mruProjectList").map(function(uri) {
            var m = PROJECT_URI_REGEX.exec(uri);
            if (m) {
                return [uri, decodeURIComponent(m[1])];
            }
            var lastSlash = uri.lastIndexOf('/');
            var extStart = uri.lastIndexOf('.komodoproject');
            if (extStart == -1) {
                extStart = uri.lastIndexOf('.kpf');
            }
            var name = uri.substring(lastSlash + 1, extStart);
            return [uri, decodeURIComponent(name)];
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
this.recentProjectsTreeView.prototype.getCellText = function(index, column) {
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
this.recentProjectsTreeView.prototype.getCellValue = function(index, column) {
    return this.rows[index][0];
};
this.recentProjectsTreeView.prototype.getImageSrc = function(index, column) {
    return 'chrome://komodo/skin/images/project_icon.png'
};
this.recentProjectsTreeView.prototype.getCellProperties = function(index, column, properties) {
    var row = this.rows[index];
    var currentProject = ko.projects.manager.currentProject;
    if (currentProject && currentProject.url == row[0]) {
        properties.AppendElement(this._atomService.getAtom("projectActive"));
    }
};


//---- internal support stuff

function _notify(label, value, image, priority, buttons) {
    var notificationBox = document.getElementById("komodo-notificationbox");
    value = value || 'places-warning';
    // Other interesting ones: information.png, exclamation.png
    image = image || "chrome://famfamfamsilk/skin/icons/error.png";
    priority = priority || notificationBox.PRIORITY_WARNING_LOW;
    buttons = buttons || [];
    
    var existing;
    while (true) {
        existing = notificationBox.getNotificationWithValue(value);
        if (!existing) {
            break;
        }
        notificationBox.removeNotification(existing);
    }

    notificationBox.appendNotification(label, value, image, priority, buttons);
}

}).apply(ko.places);
