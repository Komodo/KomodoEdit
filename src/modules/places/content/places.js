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
    .createBundle("chrome://komodo-places/locale/places.properties");
const CURRENT_PROJECT_FILTER_NAME = _bundle.GetStringFromName("currentProject.filterName");
const DEFAULT_FILTER_NAME = _bundle.GetStringFromName("default.filterName");
const VIEW_ALL_FILTER_NAME = _bundle.GetStringFromName("viewAll.filterName");
const VERSION = 3;

var _placePrefs;
var filterPrefs;
var uriSpecificPrefs;
var projectSpecificFilterPrefs;
const MAX_URI_PREFS_TO_TRACK = 60;
const MAX_PROJECT_URI_PREFS_TO_TRACK = 20;
var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

var widgets = {};
var osPathSvc;


const DEFAULT_EXCLUDE_MATCHES_PART1 = "*~;#*;CVS;*.bak;*.pyo;*.pyc";
const DEFAULT_EXCLUDE_MATCHES_PART2 = ".svn;.git;.hg;.bzr;.DS_Store;.komodotools;.tools;__pycache__";
const DEFAULT_EXCLUDE_MATCHES_PART3 = "hg-checklink-*;hg-checkexec-*";
const DEFAULT_EXCLUDE_MATCHES = [DEFAULT_EXCLUDE_MATCHES_PART1,
                                 DEFAULT_EXCLUDE_MATCHES_PART2,
                                 DEFAULT_EXCLUDE_MATCHES_PART3].join(";");
const DEFAULT_INCLUDE_MATCHES = "";

const PROJECT_URI_REGEX = /^.*\/(.+?)\.(?:kpf|komodoproject)$/;

var log = ko.logging.getLogger("places_js");
//log.setLevel(ko.logging.LOG_DEBUG);

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
        var placePrefs = _globalPrefs.getPref("places");
        var sortDir = placePrefs.getString("sortDirection", "") || "natural";
        this.single_project_view = !ko.projects.manager.initProjectViewPref(_globalPrefs);
        
        if (!widgets.placeView_treeViewDeck) {
            widgets.placeView_treeViewDeck = document.getElementById("placesSubpanelDeck");
            widgets.placesSubpanelProjectsTools_MPV = document.getElementById("placesSubpanelProjectsTools_MPV");
            widgets.placesSubpanelProjectsTools_SPV = document.getElementById("placesSubpanelProjectsTools_SPV");
        }
        ko.projects.manager.switchProjectView(this.single_project_view);
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
        this.view.sortBy("name", this._mozSortDirNameToKomodoSortDirValue[sortDir]);
        //  arrowKeys used by onTreeKeyPress, easier to init here.
        var nsIDOMKeyEvent = Components.interfaces.nsIDOMKeyEvent;
        this.arrowKeys = [nsIDOMKeyEvent.DOM_VK_UP,
                           nsIDOMKeyEvent.DOM_VK_DOWN,
                           nsIDOMKeyEvent.DOM_VK_LEFT,
                           nsIDOMKeyEvent.DOM_VK_RIGHT];
        var prefsToWatch = ["import_exclude_matches", "import_include_matches",
                            "places.multiple_project_view"];
        _globalPrefs.prefObserverService.addObserverForTopics(this,
                                                              prefsToWatch.length,
                                                              prefsToWatch, false);
    },

    _setupProjectView: function(single_project_view) {
        try {
            if (single_project_view) {
                widgets.placeView_treeViewDeck.selectedIndex = 1;
                ko.places.projects_SPV.activateView();
            } else {
                widgets.placeView_treeViewDeck.selectedIndex = 0;
                ko.places.projects.activateView();
            }
            widgets.placesSubpanelProjectsTools_MPV.collapsed = single_project_view;
            widgets.placesSubpanelProjectsTools_SPV.collapsed = !single_project_view;
        } catch(ex) {
            log.exception(ex, "Error in _setupProjectView");
        }
    },

    observe: function(subject, topic, data) {
        var project;
        if (["import_exclude_matches", "import_exclude_matches"].indexOf(topic)
            >= 0
            && (widgets.placeView_currentProject_menuitem.getAttribute('checked')
                == 'true')
            && (project = ko.projects.manager.currentProject)) {
            this._updateViewPrefsFromProjectPrefs(project);
        } else if (topic == "places.multiple_project_view") {
            var use_single_project_view = !_globalPrefs.getBooleanPref("places.multiple_project_view");
            if (use_single_project_view != this.single_project_view) {
                this._setupProjectView(this.single_project_view = use_single_project_view);
                ko.projects.manager.switchProjectView(use_single_project_view);
            }
        }
    },

    _updateViewPrefsFromProjectPrefs: function(project) {
        var prefset = project.prefset;
        try {
            gPlacesViewMgr.view.setMainFilters(prefset.getStringPref('import_exclude_matches'),
                                           prefset.getStringPref('import_include_matches'));
        } catch(ex) {
            log.exception(ex, "getting prefs failed");
            this.placeView_defaultView();
        }
    },
    
    sortByDirection: function(sortDirection) {
        this.view.sortBy("name", this._mozSortDirNameToKomodoSortDirValue[sortDirection]);
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
            var placePrefs = (Components.classes["@activestate.com/koPrefService;1"].
                              getService(Components.interfaces.koIPrefService).prefs.
                              getPref("places"));
            var preferDblClickRebase = placePrefs.getBoolean('dblClickRebases', false);
            if (preferDblClickRebase) {
                ko.places.manager.toggleRebaseFolderByIndex(index);
            } else {
                // Let Mozilla do the default action, even though
                // I'm trying to squelch the event handler and all that.
                // Best to let Mozilla do things the way it wants...
                return;
            }
        }
        // Don't handle this event further for both files and folders.
        event.stopPropagation();
        event.cancelBubble = true;
        event.preventDefault();
    },

  
  displayCurrentFullPath: function(event, sender) {
        var index = this._currentRow(event);
        if (index < 0) {
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
        var uri = this.view.getURIForRow(index);
        var fileObj = (Components.classes["@activestate.com/koFileService;1"].
                       getService(Components.interfaces.koIFileService).
                       getFileFromURI(uri));
        var labelValue = fileObj.isLocal ? fileObj.path : uri;
        var popup = sender;
        var label = sender.childNodes[0];
        label.setAttribute("value", labelValue);
        return true;
    },
    
    refreshViewByIndex: function(index) {
        if (index == -1) {
            this.view.refreshFullTreeView();
        } else {
            this.view.refreshView(index);
        }
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

    _openFolder: function(index) {
        if (index >= 0) {
            if (!this.view.isContainerOpen(index)) {
                this.view.toggleOpenState(index);
            }
        }
    },

    addNewFileFromTemplate: function() {
        var isLocal = ko.places.manager.currentPlaceIsLocal;
        if (!isLocal) {
            ko.dialogs.alert(_bundle.GetStringFromName("remoteTemplateNewFileNotAvailable"));
            return;
        }
        var index, uri;
        if (ko.places.manager._clickedOnRoot()) {
            index = -1;
            uri = ko.places.manager.currentPlace;
        } else {
            index = this.view.selection.currentIndex;
            uri = this.view.getURIForRow(index);
        }
        var dir = ko.uriparse.URIToLocalPath(uri);
        var callback = function(view) {
            if (index == -1) {
                this.view.refreshFullTreeView();
            } else {
                this.refreshViewByIndex(index);
                this._openFolder(index);
            }
            this.tree.treeBoxObject.invalidate();

            require("ko/dom")(window.parent).trigger("folder_touched", {path: dir});

        }.bind(this);
        ko.views.manager.newTemplateAsync(dir, callback);
    },

    addNewFile: function() {
        var index = ko.places.manager._clickedOnRoot() ? -1 : this.view.selection.currentIndex;
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFileName"));
        if (!name) return;
        try {
            this.view.addNewFileAtParent(name, index);
            this.tree.treeBoxObject.invalidate();
            var parentURI = (index >= 0
                             ? this.view.getURIForRow(index)
                             : ko.places.manager.currentPlace);
            ko.views.manager.doFileOpenAsync(parentURI + "/" + name);
            this._openFolder(index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        } finally {
            var sdkFile = require("ko/file");
            require("ko/dom")(window.parent).trigger("folder_touched",
                                                  {path: ko.uriparse.URIToPath(parentURI)});
        }

    },

    addNewFolder: function() {
        var index = ko.places.manager._clickedOnRoot() ? -1 : this.view.selection.currentIndex;
        var name = ko.dialogs.prompt(_bundle.GetStringFromName("enterFolderName"));
        if (!name) return;
        try {
            this.view.addNewFolderAtParent(name, index);
            this._openFolder(index);
        } catch(ex) {
            ko.dialogs.alert(ex);
        } finally {
            var parentURI = (index >= 0
                             ? this.view.getURIForRow(index)
                             : ko.places.manager.currentPlace);
            var sdkFile = require("ko/file");
            require("ko/dom")(window.parent).trigger("folder_touched",
                                                  {path: ko.uriparse.URIToPath(parentURI)});
        }
    },

    onTreeClick: function(event) {
        var index = this._currentRow(event);
        if (index == -1) {
            this.view.selection.clearSelection();
        } else {
            this.view.markRow(index);
        }

        if (this.view.isContainer(index) && ko.prefs.getBoolean('pref_places_singleClickExpand', false)) {
            this.view.toggleOpenState(index);
        }
    },

    handleReturnKeyPress: function(event) {
        // Either open one file or toggle/rebase one folder. Mixtures not allowed.
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
            var placePrefs = (Components.classes["@activestate.com/koPrefService;1"].
                              getService(Components.interfaces.koIPrefService).prefs.
                              getPref("places"));
            var preferDblClickRebase = placePrefs.getBoolean('dblClickRebases', false);
            if (preferDblClickRebase) {
                ko.places.manager.toggleRebaseFolderByIndex(index);
            } else {
                ko.places.viewMgr.view.toggleOpenState(index);
            }
        }
    },

    onTreeKeyPress: function(event) {
        var t = event.originalTarget;
        if (t.localName != "treechildren" && t.localName != 'tree') {
            return false;
        }
        // Special-case some commands, and then look at the keybinding set
        // to determine a command to do.
        if (!(event.shiftKey || event.ctrlKey || event.altKey)) {
            if (this.arrowKeys.indexOf(event.keyCode) >= 0) {
                // Nothing to do but squelch the keycode
                event.stopPropagation();
                event.preventDefault();
                return false;
            } else if (event.keyCode == event.DOM_VK_RETURN) {
                // ENTER/RETURN should be handled by xbl bindings.
                event.stopPropagation();
                event.preventDefault();
                return true;
            } else if (event.keyCode == event.DOM_VK_DELETE) {
                ko.places.manager.doDeletePlace();
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
                return true;
            }
        }
        var command = this._getCommandFromEvent(event);
        if (!command) {
            return false;
        }
        var newCommand = this._placeCommandsToTranslate[command];
        if (newCommand) {
            var controller = document.commandDispatcher.getControllerForCommand(newCommand);
            if (controller) {
                event.preventDefault();
                event.stopPropagation();
                controller.doCommand(newCommand);
                return true;
            }
        }
        return false;
    },
    _placeCommandsToTranslate: {
        "cmd_startIncrementalSearch": "cmd_findInPlace",
        "cmd_find": "cmd_findInPlace",
        "cmd_replaceInFiles": "cmd_replaceInPlace",
        "cmd_delete": "cmd_deletePlaceItem",
        "cmd_lineScrollUp": "cmd_places_goUpOneFolder",
        "cmd_historyForward": "cmd_goPreviousPlace",
        "cmd_historyBack": "cmd_goNextPlace",
        "cmd_undo": "cmd_undoTreeOperation",
        
        
        "__NONE__": null
    },
    _getCommandFromEvent: function(event) {
        var key = ko.keybindings.manager.event2keylabel(event, undefined, event.type == "keypress");
        if (!key) {
            dump("ko.places.keybindings._getCommandFromEvent: No key for " + event.charCode + "\n");
            return null;
        }
        var command = ko.keybindings.manager.key2command[key];
        if (!command) {
            dump("ko.places.keybindings._getCommandFromEvent: No command for key " + key + "\n");
            return null;
        }
        return command;
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

    _processMenu_TopLevel: function(menuNode) {
        var selectionInfo = this._selectionInfo;
        var itemTypes = selectionInfo.itemTypes;
        if (ko.places.matchAnyType(menuNode.getAttribute('hideIf'), itemTypes)) {
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
                log.exception(ex, "Failed to eval '" + testEval_HideIf);
            }
        }
    
        menuNode.removeAttribute('collapsed');
        ko.places.testDisableNode(menuNode, selectionInfo);
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
        var currentPlaceIsLocal = ko.places.manager.currentPlaceIsLocal;
        for (var i = 0; i < lim && (uri = uris[i]); i++) {
            if (currentPlaceIsLocal) {
                // Do this for drag/drop onto things like file managers.
                var nsLocalFile = Components.classes["@mozilla.org/file/local;1"]
                    .createInstance(Components.interfaces.nsILocalFile);
                var path = ko.uriparse.URIToLocalPath(uri);
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
            var currentPlace = ko.places.manager.currentPlace;
            for (var i = 0; i < dt.mozItemCount; i++) {
                if (dt.mozGetDataAt("text/uri-list", i) == currentPlace) {
                    inDragSource = false;
                    break;
                }
            }
        }
        if (inDragSource) {
            event.dataTransfer.effectAllowed = this.originalEffect;
            event.preventDefault();
        } else {
            event.dataTransfer.effectAllowed = "none";
        }
        
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
            event.preventDefault();
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
        if (!dt) {
            log.debug("_getDraggedURIs: event.dataTransfer is null\n");
            return [[], null];
        }
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
        require("notify/notify").send(msg, "places", {priority: "error"});
        return false;
    },
    
    _finishDrop : function(event, target_uri, index) {
        var dt = event.dataTransfer;
        var from_uris, dropEffect, copying;
        [from_uris, dropEffect] = this._getDraggedURIs(event);
        if (from_uris.length == 0) {
            return this._dropProblem(_bundle.GetStringFromName("_finishDropNoFrom_uris"));
        } else if (dropEffect == "none") {
            return this._dropProblem(_bundle.GetStringFromName("_finishDropNoDragDropHere"));
        } else if (dropEffect == "link") {
            return this._dropProblem(_bundle.GetStringFromName("_finishDropCantDragDropLink"));
        }

        // See bug 87924
        copying = (dropEffect != 'none' ? dropEffect == "copy" : event.ctrlKey);
        
        var target_uri_no_slash = this._removeTrailingSlash(target_uri);
        for (var i = 0; i < from_uris.length; i++) {
            var source_uri = from_uris[i];
            var source_uri_no_slash = this._removeTrailingSlash(source_uri);
            if (target_uri_no_slash == source_uri_no_slash) {
                return this._dropProblem(
                    _bundle.formatStringFromName("places.doDropCantDropDirectoryOntoItself",
                                                 [source_uri_no_slash], 1));
                return false;
            }
            var source_uri_parent_no_slash = source_uri_no_slash.substr(0, source_uri_no_slash.lastIndexOf("/"));
            if (target_uri_no_slash == source_uri_parent_no_slash && !copying) {
                return this._dropProblem(
                    _bundle.formatStringFromName("places.doDropCantDropItemOnParent",
                                                 [source_uri_no_slash], 1));
                return false;
            }
            else if (target_uri.indexOf(this._addTrailingSlash(source_uri_no_slash)) == 0) {
                return this._dropProblem(
                    _bundle.formatStringFromName("places.doDropCantDropItemOnItsDescendant",
                                                 [source_uri, target_uri], 2));
                return false;
            }
        }
        // Bug 98484: If we're moving, prompt the user to ask if they really want to do this
        if (!copying) {
            let basePrefName = "placesAllowDragDropItemsToFolders";
            if (!_globalPrefs.hasBooleanPref(basePrefName)) {
                // The doNotAsk system uses the global prefs widget, so put them there.
                // Make the default to *not* ask, but it writes a notification
                _globalPrefs.setBooleanPref(basePrefName, false);
                _globalPrefs.setBooleanPref("donotask_" + basePrefName, true);
                _globalPrefs.setStringPref("donotask_action_" + basePrefName,
                                           "Yes");
            }
            var target_uri_as_path = ko.uriparse.URIToPath(target_uri);
            var prompt = (from_uris.length == 1
                          ? _bundle.formatStringFromName("Drag item X to folder Y", [ko.uriparse.baseName(from_uris[0]), target_uri_as_path], 2)
                          : _bundle.formatStringFromName("Drag these N items to folder Y", [from_uris.length, target_uri_as_path], 2));
            var response = "No";
            var text = null;
            var title = "Places Drag/Drop in Progress";
            // This pref has to be stored globally to work with the doNotAsk pref system
            var thisResponse = ko.dialogs.yesNoCancel(prompt, response, text, title, basePrefName);
            if (thisResponse != "Yes") {
                if (thisResponse == "No"
                    && _globalPrefs.getBooleanPref("donotask_" + basePrefName)
                    && (_globalPrefs.getStringPref("donotask_action_" + basePrefName) == "No")) {
                    var msg = _bundle.GetStringFromName("Drag-drop suppressed due to Preferences-Places-Drag");
                    var options = {
                        severity: Components.interfaces.koINotification.SEVERITY_INFO ,
                        actions: [{ label: _bundle.GetStringFromName("PreferencesDot3"),
                                    identifier: "goToPreferences",
                             handler: function(notification) {
                                parent.prefs_doGlobalPrefs("placesPref");
                            }
                        }]
                    };
                    ko.notifications.add(msg, ["Places"], "dragDropSuppressed", options);
                }
                event.stopPropagation();
                event.cancelBubble = true;
                event.preventDefault();
                return false;
            }
        }
        try {
            this.finishFileCopyOperation(from_uris, target_uri, index, copying);
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

    finishFileCopyOperation: function(from_uris, to_uri, target_index, copying) {
        // target_index can be -1 if we're dropping on the root node
        var srcFileInfoObjs = {}, targetFileInfoObjs = {};
        var simple_callback = {
            callback: function(result, data) {
                if (result != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
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
            var prompt = _bundle.GetStringFromName("fileAlreadyExists");
            var buttons, text, title;
            if (res == Components.interfaces.koIPlaceTreeView.COPY_MOVE_WOULD_KILL_DIR) {
                existingSrcDirectories.push(srcFileInfo);
                continue;
            } else if (res == Components.interfaces.koIPlaceTreeView.MOVE_SAME_DIR) {
                selfDirectories.push(srcFileInfo);
                continue;
            }
            title = _bundle.GetStringFromName("fileAlreadyExists");
            var buttons;
            text = _bundle.formatStringFromName("forSourceAndTarget",
                                                [srcFileInfoText,
                                                 targetFileInfoText], 2);
            const overwrite_label = _bundle.GetStringFromName("overwrite.label");
            const cancel_label = _bundle.GetStringFromName("cancel.label");
            const copy_label = _bundle.GetStringFromName("copy.label");
            if (res == Components.interfaces.koIPlaceTreeView.MOVE_OTHER_DIR_FILENAME_CONFLICT) {
                prompt = _bundle.formatStringFromName("overwriteFile.prompt",
                                                     [srcFileInfo.baseName], 1);
            } else {
                prompt = _bundle.formatStringFromName("saveFileWithNewName.prompt",
                                                     [srcFileInfo.baseName], 1);
            }
            buttons = [copy_label, overwrite_label, cancel_label];
            var response = ko.dialogs.customButtons(prompt, buttons, cancel_label, text, title);
            if (!response || response == cancel_label) {
                return true;
            } else if (response == overwrite_label) {
                // Copy/move it over anyways.
                finalSrcURIs.push(srcFileInfo.URI);
                finalTargetURIs.push(targetFileInfo.URI);
            } else if (response == copy_label) {
                var newName, selectionStart, selectionEnd;
                var isLocal = ko.places.manager.currentPlaceIsLocal;
                var conn = null;
                if (!isLocal) {
                    var RCService = Components.classes["@activestate.com/koRemoteConnectionService;1"].
                        getService(Components.interfaces.koIRemoteConnectionService);
                    conn = RCService.getConnectionUsingUri(ko.places.manager.currentPlace);
                }
                var targetDirPath = targetFileInfo.dirName;
                [newName, selectionStart, selectionEnd] =
                    this._getNewSuggestedName(srcFileInfo.baseName, targetDirPath,
                                              isLocal, conn);
                var label = _bundle.GetStringFromName("fileName.prompt");
                title = _bundle.GetStringFromName("enterFileName.prompt");
                var newPath;
                var regEx = /(.*)\((\d+)\)$/;
                var idx;
                try {
                    while (true) {
                        prompt = _bundle.formatStringFromName("fileNameExists.template",
                                                              [newName], 1);
                        newName = ko.dialogs.prompt(prompt, label, newName, title,
                                                    null, // mruName
                                                    null, // validator
                                                    null, // multiline
                                                    null, // screenX
                                                    null, // screenY
                                                    null, // tacType
                                                    null, // tacParam
                                                    null, // tacShowCommentColumn
                                                    selectionStart,
                                                    selectionEnd
                                                    );
                        if (!newName) {
                            return true;
                        }
                        if (!this._universalFileExists(conn, osPathSvc, targetDirPath, newName)) {
                            newPath = this._universalNewPath(conn, osPathSvc, targetDirPath, newName);
                            break;
                        }
                        selectionStart = selectionEnd = null;
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
                    + selfDirectories.map(function(srcFileInfo) {
                            return (_bundle.GetStringFromName("sourceFilePrefix")
                                    + srcFileInfo.baseName
                                    + _bundle.GetStringFromName("directoryPrefix")
                                    + srcFileInfo.dirName);
                        }).join(", "));
            ko.dialogs.alert(prompt, text, title);
        }
        lim = finalSrcURIs.length;
        let errorCallback = {
          callback: function(result, data) {
                if (result != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    ko.dialogs.alert(data);
                }
            }
        };
                
        for (i = 0; i < lim; i++) {
            var srcURI = finalSrcURIs[i];
            let callback;
            var from_uri = from_uris[i];
            if (!copying) {
                var from_view = ko.views.manager.getViewForURI(srcURI);
                callback = {
                callback: function(result, data) {
                        if (result != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
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
                                                log.exception(ex, "Can't set " + name);
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
            } else {
                callback = errorCallback;
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
        // Bug 100160: refresh the full tree each time.  Changing the places tree
        // doesn't happen that often via direct manipulation, so this isn't costly.
        this.view.refreshFullTreeView();
        this.tree.treeBoxObject.invalidate();
        let items = finalSrcURIs.map(function(uri) ko.uriparse.URIToPath(uri)).join(", ");
        if (items.length > 1000) {
            items = finalSrcURIs.map(function(uri) ko.uriparse.baseName(uri)).join(", ");
        }
        let msg = _bundle.formatStringFromName(copying ? "Copied X to Y" : "Moved X to Y",
                                               [items, ko.uriparse.URIToPath(to_uri)], 2);
        ko.notifications.add(msg, ["Places"], "itemsMovedTo_" + (new Date()).valueOf());
        this.view.selection.clearSelection();
        return true;
    },
    _finishFileCopyOperation: function(from_uris, to_uri, target_index, copying) {
        if (!("_deprecate__finishFileCopyOperation" in this)) {
            var msg = _bundle.GetStringFromName("ko.places.viewMgr._finishFileCopyOperation is deprecated");
            log.warn(msg);
            this._deprecate__finishFileCopyOperation = null;
        }
        // This function needs to be exposed, do not change interface.
        // See http://code.activestate.com/recipes/577562-a-komodo-macro-for-duplicating-the-current-file-in/
        // This code 
        return this.finishFileCopyOperation(from_uris, to_uri, target_index, copying);
    },
    _getNewSuggestedName: function(srcBaseName, targetDirPath,
                                   isLocal, conn) {
        var newName, selectionStart, selectionEnd;
        var copyPart = " " + _bundle.GetStringFromName("Copy.label");
        var ptn = new RegExp('^(.*?)(?:(' + copyPart + ')(?: (\\d+))?)?(\\..*)?$');
        var m = ptn.exec(srcBaseName);
        if (!m) {
            newName = srcBaseName + copyPart;
            selectionStart = srcBaseName.length;
            selectionEnd = newName.length;
        } else {
            var i = 0;
            var saneLimit = 1000; // prevent runaway loop, if code hits this hard.
            while (true) {
                if (m[4] === undefined) m[4] = "";
                if (m[3] !== undefined) {
                    newName = m[1] + m[2] + " " + (parseInt(m[3]) + 1) + m[4];
                } else if (m[2] !== undefined) {
                    newName = m[1] + m[2] + " 2" + m[4];
                } else {
                    newName = m[1] + copyPart + m[4];
                }
                i += 1;
                if (i >= saneLimit || !this._universalFileExists(conn, osPathSvc, targetDirPath, newName)) {
                    selectionStart = m[1].length;
                    selectionEnd = newName.length - m[4].length;
                    break;
                }
                m = ptn.exec(newName);
                if (!m) {
                    selectionStart = newName.length;
                    newName += copyPart;
                    selectionEnd = newName.length;
                    break;
                }
            }
        }
        return [newName, selectionStart, selectionEnd];
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
            log.exception(ex, "Can't find prefName '" + prefName + "' in menu");
            return false;
        }
    },

    placeView_customView: function() {
        // Use the same format as managing the list of servers.
        var currentFilterName = this._getCurrentFilterPrefName();
        var resultObj = {needsChange:false,
                         currentFilterName:currentFilterName,
                         version:VERSION};
        ko.windowManager.openOrFocusDialog("chrome://komodo-places/content/manageViewFilters.xul",
                                    "komodo_places",
                                    "chrome,modal,titlebar,resizable=yes",
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
    parent.controllers.appendController(this.controller);
    
    var gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
        getService(Components.interfaces.nsIObserverService);
    gObserverSvc.addObserver(this, 'visit_directory_proposed', false);
    gObserverSvc.addObserver(this, 'current_project_changed', false);
    gObserverSvc.addObserver(this, 'file_changed', false);
    parent.addEventListener('project_opened',
                            this.handle_project_opened_setup, false);
    parent.addEventListener('visit_directory_proposed',
                            this.handle_visit_directory_proposed, false);
    parent.addEventListener('current_view_changed',
                            this.handle_current_view_changed, false);
    
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
        this.openNamedRemoteDirectory(uri);
    },

    openNamedRemoteDirectory: function(uri) {
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
     * @param {String} dir The directory to open.
     * @param {String} baseName Optional file basename in the directory
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
    
    _placeableSchemes: {'file':1, 'ftp':1, 'ftps':1, 'sftp':1, 'scp':1},
    _schemeIsPlaceable: function(scheme) {
        return scheme in this._placeableSchemes;
    },
    _uriIsPlaceable: function(uri) {
        var schemeEnd = uri.indexOf(":");
        if (schemeEnd === -1) {
            return false;
        }
        return this._schemeIsPlaceable(uri.substr(0, schemeEnd));
    },

    /* Set the given directory URI as the root in places.
     *
     * @param {String} dirURI The directory URI to open.
     * @param {String} baseName Optional file base name in the directory
     *      to select.
     */
    openDirURI: function(dirURI, baseName, successFunc) {
        if (typeof(successFunc) == "undefined") successFunc = this._setDirURI_successFunc_show_tab;
        if (!this._uriIsPlaceable(dirURI)) {
            return;
        };
        this._enterMRU_Place(dirURI);
        this._setDirURI(dirURI,
                        {save:true,
                                baseName:baseName,
                                onSuccess:successFunc});
    },

    showCurrentEditorTab: function(forceNewPlaceDir) {
        var view = ko.views.manager.currentView;
        if (!view
            || view.getAttribute("type") != "editor"
            || !view.koDoc) {
            return;
        }
        var scheme, file = view.koDoc.file;
        if (!file
            || !(scheme = file.scheme)
            || !this._schemeIsPlaceable(scheme)) {
            return;
        }

        this.showTreeItemByFile(file.URI, forceNewPlaceDir, view.setFocus.bind(view));
    },

    showTreeItemByFile: function(URI, forceNewPlaceDir, callback) {
        if (forceNewPlaceDir) {
            ko.uilayout.ensureTabShown("placesViewbox", true);
        }
        var showTreeItem = function(index) {
            var treeSelection = gPlacesViewMgr.view.selection;
            treeSelection.currentIndex = index;
            treeSelection.select(index);
            gPlacesViewMgr.tree.treeBoxObject.ensureRowIsVisible(index);
            if (callback) callback();
        };
        var successFunc;
        var findFileFunc = function() {
            var currentPlace = ko.places.manager.currentPlace;
            var targetURI = URI;
            var index = targetURI.indexOf(currentPlace + "/");
            if (index !== 0) {
                log.error("Expecting to see ["
                          + currentPlace
                          + "] in "
                          + targetURI
                          + ", got ["
                          + targetURI.indexOf(currentPlace + "/")
                          + "]");
                return;
            }
            var pieces = targetURI.substr(currentPlace.length + 1).split("/");
            var placesTreeView = gPlacesViewMgr.view;
            var findPiecesFunc = function(leadingURI, pieces) {
                var newURI = leadingURI + "/" + pieces[0];
                var location = placesTreeView.getRowIndexForURI(newURI);
                if (location == -1) {
                    log.warn("Can't find "
                             + newURI
                             + " in the tree");
                    return;
                }
                if (pieces.length === 1) {
                    showTreeItem(location);
                    return;
                }
                if (!placesTreeView.isContainerOpen(location)) {
                    placesTreeView.toggleOpenState(location);
                    //XXX race condition, would be better to have a callback
                    setTimeout(findPiecesFunc, 500, newURI, pieces.slice(1));
                    return;
                }
                findPiecesFunc(newURI, pieces.slice(1));
            }
            findPiecesFunc(currentPlace, pieces);
        };
        successFunc = function() {
            var index = gPlacesViewMgr.view.getRowIndexForURI(URI);
            if (index > -1) {
                showTreeItem(index);
            } else {
                findFileFunc();
            }
            // view.scintilla.focus();
        };
        try {
            var uri = URI;
            var index = uri.lastIndexOf("/");
            if (index == -1) {
                log.error("Can't find a '/' in uri [" + uri + "]\n");
                return;
            }
            
            // If the selected file lives in the current places' hierarchy,
            // don't switch.
            // If the current project contains the file,
            // switch to the project.
            // Otherwise, switch to the current file.
            if (uri.indexOf(this.currentPlace) !== 0) {
                var parentURI = null;
                var baseName = uri.substr(index + 1);
                try {
                    var project = ko.projects.manager.currentProject;
                    if (project) {
                        var projectLiveDirURI = ko.uriparse.localPathToURI(project.liveDirectory);
                        if (projectLiveDirURI
                            && uri.indexOf(projectLiveDirURI + "/") === 0) {
                                parentURI = projectLiveDirURI;
                        } else {
                            var projectURI = project.getFile().URI;
                            var projectURILastSlashIdx = projectURI.lastIndexOf("/");
                            if (projectURILastSlashIdx !== -1) {
                                var projectParentURI = projectURI.substr(0, projectURILastSlashIdx);
                                if (projectParentURI !== projectLiveDirURI
                                    && uri.indexOf(projectParentURI) === 0) {
                                    parentURI = projectParentURI;
                                }
                            }
                        }
                    }
                } catch(ex) {
                    log.exception(ex, "Error trying to get the project's URI");
                }
                if (!parentURI) {
                    if (!forceNewPlaceDir
                        && !_placePrefs.getBoolean('syncAllFiles', true)) {
                        // Don't open anything new in places.
                        return;
                    }
                    parentURI = uri.substr(0, index);
                }
                this.openDirURI(parentURI, baseName, successFunc);
            } else {
                successFunc();
            }
        } catch(ex) {
            log.exception(ex, "showTreeItemByFile: failed to open " + URI);
        }
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
        if (this.currentPlace != destination_uri) {
            this.pushHistoryInfo(this.currentPlace, destination_uri);
        }
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
     * @param {string} dirURI The directory to which to switch, as a URI.
     *      This is presumed to be a directory (i.e. not a file) and to
     *      exist.
     * @param {Object} args Can contain the following fields
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

        // Do this to update the SCC info, fixes bug 88254
        var koFile = Components.classes["@activestate.com/koFileService;1"].
                       getService(Components.interfaces.koIFileService).
                       getFileFromURI(dirURI);
        if (!koFile.dirName
            && !koFile.path
            && !dirURI[dirURI.length - 1] != "/") {
            // Bug 92121: URIs like ftp://ftp.mozilla.org have no
            // associated path info.
            dirURI += "/";
            koFile = Components.classes["@activestate.com/koFileService;1"].
                getService(Components.interfaces.koIFileService).
                getFileFromURI(dirURI);
        }
        this.currentPlaceIsLocal = koFile.isLocal;
        this.currentPlace = dirURI;
        // watch out: baseName("/") => ""
        widgets.rootButton.label = koFile.baseName || koFile.path;
        this._checkProjectMatch();
        widgets.rootButton.tooltipText = (
            koFile.scheme == "file" ? koFile.displayPath : dirURI);

        var this_ = this;
        var callback = {    // koIAsyncCallback
            callback: function(result, data) {
                statusNode.removeAttribute('image');
                if (result != Components.interfaces.koIAsyncCallback.RESULT_SUCCESSFUL) {
                    widgets.rootButton.label = "";
                    widgets.rootButton.tooltipText = "";
                    this_.currentPlace = null;
                    ko.dialogs.alert(data);
                    if (onFailure) {
                        try {
                            onFailure.apply(this_);
                        } catch(ex) {
                            log.exception(ex, "_setDirURI::onFailure");
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
                        _placePrefs.setStringPref(parent._koNum, dirURI);
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
                            log.exception(ex, "_setDirURI::onSuccess");
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
            gPlacesViewMgr.finishFileCopyOperation(srcURIs, target_uri, index,
                                                    isCopying);

        } catch(ex) {
            ko.dialogs.alert(ex);
        } finally {
            var sdkFile = require("ko/file"),
                w       = require("ko/dom")(window.parent);

            w.trigger(
                "folder_touched",
                {path: sdkFile.dirname(ko.uriparse.URIToPath(target_uri)) }),
                triggered = {};

            if ( ! isCopying)
            {
                srcURIs.forEach(function(uri) {
                    if (uri in triggered) return;

                    var path = sdkFile.dirname(ko.uriparse.URIToPath(uri));
                    w.trigger("folder_touched", {path: path });
                    triggered[uri] = true;
                });
            }
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
        var popupNode = document.popupNode;
        if (!popupNode) {
            popupNode = document.getElementById("places-files-popup").triggerNode;
            if (!popupNode) {
                return false;
            }
        }
        if (popupNode == widgets.rootButton) return true;
        return (popupNode.id == "places-files-tree-body"
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

    _doRenameItem_files_are_same_re: /renameItem failure.*indicate the same file/,

    promptForNewName: function(uri) {
        var oldname = ko.uriparse.baseName(uri);
        var newname = ko.dialogs.renameFileWrapper(oldname);
        if (!newname) return [null, null, false];
        else if (newname == oldname) {
            ko.dialogs.alert(_bundle.formatStringFromName("Old file and new basename are the same.template", [oldname, newname], 2));
            return [null, null, false];
        }
        return [oldname, newname, true];
    },

    doRenameItem: function() {
        var index = gPlacesViewMgr.view.selection.currentIndex;
        var uri = gPlacesViewMgr.view.getURIForRow(index);
        if (/\.(?:komodoproject|kpf)$/.test(uri)) {
            var project = ko.projects.manager.getProjectByURL(uri);
            if (project) {
                // Do the project's own rename project
                ko.projects.renameProject(project);
                return;
            }
        }
        var oldView = ko.views.manager.getViewForURI(uri);
        var oldname, newname, carryOn;
        if (!oldView) {
            [oldname, newname, carryOn] = this.promptForNewName(uri);
            if (!carryOn) return;
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

                            require("ko/dom")(window).trigger(
                                "file_touched",
                                {path: ko.uriparse.URIToPath(uri) });

                        } catch(ex2) {
                            if (this._doRenameItem_files_are_same_re.test(ex2.message)) {
                                ko.dialogs.alert(_bundle.formatStringFromName("Files X and X are the same, rename stopped.template", [oldname, newname], 2));
                            } else {
                                ko.dialogs.alert(_bundle.formatStringFromName("Error when trying to rename a file.template", [ex2], 1));
                            }
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
                        ko.dialogs.alert(_bundle.formatStringFromName("Error when trying to rename a file.template", [ex], 1));
                        dump("doRenameItem: " + ex + "\n");
                    }
                }
            }
        } else {
            // Just get moreKomodo to do all the renaming on the filesystem,
            // and updating the tabs.  And then the usual filesystem change
            // will cause the tree to be updated.
            var moreKomodoCommon = ko.moreKomodo.MoreKomodoCommon;
            var viewDoc = oldView.koDoc;
            if (!moreKomodoCommon.dirtyDocCheck(viewDoc)) {
                return;
            }
            [oldname, newname, carryOn] = this.promptForNewName(uri);
            if (!carryOn) return;
            moreKomodoCommon.renameFile(uri, newname);
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
        finally {
            var sdkFile = require("ko/file"),
                w       = require("ko/dom")(window.parent),
                triggered= {};
            uris.forEach(function(uri) {
                if (uri in triggered) return;

                var _path = sdkFile.dirname(ko.uriparse.URIToPath(uri));
                w.trigger("folder_touched", {path: _path});
                triggered[uri] = true;
            });
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
            window.frameElement.hookupObservers("panel-proxy-commandset");
            if (_globalPrefs.getPref("places").hasPref(parent._koNum)) {
                uri = _globalPrefs.getPref("places").getStringPref(parent._koNum);
                var file = Components.classes["@activestate.com/koFileEx;1"].
                    createInstance(Components.interfaces.koIFileEx);
                try {
                    file.URI = uri;
                    if (!file.exists) {
                        var msg = _bundle.formatStringFromName
                            ("Directory X no longer exists",
                             [ko.uriparse.baseName(uri)], 1);
                        //log.info(msg);
                        require("notify/notify").send(msg, "places", {priority: "warning"});
                        _globalPrefs.getPref("places").deletePref(parent._koNum);
                        uri = null;
                    }
                } catch(ex2) {
                    log.exception(ex2, "places.js:init: inner failure");
                    uri = null;
                }
            }
        } catch(ex) {
            log.exception(ex, "places.js:init: failure");
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
        if (uri && this._uriIsPlaceable(uri)) {
            try {
                var successFunc = function() {
                    // If we're moving to a URI that's in the history list,
                    // pull it out.
                    for each (var name in ['history_prevPlaces', 'history_forwardPlaces']) {
                        var index = this[name].indexOf(uri);
                        if (index > -1) {
                            this[name].splice(index, 1);
                        }
                    };
                };
                this._setDirURI(uri, {save:false, onSuccess:successFunc});
            } catch(ex) {}
        }
        try {
            var placesPrefs = _globalPrefs.getPref("places");
            var name_list = ['lastLocalDirectoryChoice', 'lastRemoteDirectoryChoice', 'lastHomePlace'];
            name_list.forEach(function(name) {
                this[name] = placesPrefs.getString(name, '');
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
            this.trackCurrentTab_pref = placesPrefs.getBoolean('trackCurrentTab', false);
            parent.document.getElementById("places_trackCurrentTab").
                   setAttribute('checked', this.trackCurrentTab_pref);
        } catch(ex) {
            dump("Error init'ing the viewMgrClass (2): " + ex + "\n");
        }
    },
    
    finalize: function() {
        var placesPrefs = _globalPrefs.getPref("places");
        placesPrefs.setBooleanPref('trackCurrentTab', this.trackCurrentTab_pref);
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
            } else if (placesPrefs.hasStringPref(name)) {
                placesPrefs.deletePref(name);
            }
        }, this);
        this._enterMRU_Place(null);
        this.cleanPrefs();
        this.currentPlace = null;
        window.controllers.removeController(this.controller);
        parent.controllers.removeController(this.controller);
        this.controller = null;
        var gObserverSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
        gObserverSvc.removeObserver(this, 'visit_directory_proposed');
        gObserverSvc.removeObserver(this, 'current_project_changed');
        gObserverSvc.removeObserver(this, 'file_changed');
        parent.removeEventListener('current_view_changed',
                                   this.handle_current_view_changed, false);
        parent.removeEventListener('project_opened',
                                   this.handle_project_opened_setup, false);
        parent.removeEventListener('visit_directory_proposed',
                                   this.handle_visit_directory_proposed, false);
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
        ko.uilayout.ensureTabShown("placesViewbox", true);
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
    
    trackCurrentTab : function(menuitem) {
       // On OSX with Mozilla 2.0, mi.getAttribute("checked") ==> "false",
       // which naively evaluates to true.
       this.trackCurrentTab_pref = menuitem.getAttribute('checked') == "true";
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
        var reportedURIs = {};
        var numWritten = 0;
        var innerPopupMenu = null;
        var outerPopupMenu = popupMenu;
        var innerMenu = null;
        var popupThreshold = 5;
        // uris_to_remove_by_block tracks dirs in
        // places history that have been deleted, and removes them (bug 98684)
        // Note dependency on structure of the 'blocks' array-of-arrays
        var uris_to_remove_by_block = [[], [], []];
        for (var i = 0; i < blocks.length; ++i) {
            var block = blocks[i];
            var code = codes[i];
            for (var j = block.length - 1; j >= 0; --j) {
                var uri = block[j];
                if (!uri || uri in reportedURIs) {
                    continue;
                }
                reportedURIs[uri] = true;
                let file = Components.classes["@activestate.com/koFileEx;1"].
                  createInstance(Components.interfaces.koIFileEx);
                file.URI = uri;
                if (file.isLocal && !file.exists) {
                    uris_to_remove_by_block[i].push(j);
                    continue;
                }
                menuitem = document.createElement("menuitem");
                menuitem.setAttribute("crop", "center");
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
        // No need to reverse the arrays as that was done in the "j" loop
        uris_to_remove_by_block[0].forEach(function(idx) {
            this.history_forwardPlaces.splice(idx, 1);
        }.bind(this));
        if (uris_to_remove_by_block[1].length) {
            log.warn("addRecentLocations: uris_to_remove_by_block[1] should be empty, but contains "
                     + uris_to_remove_by_block[1].length
                     + " entries");
        }
        uris_to_remove_by_block[2].forEach(function(idx) {
            this.history_prevPlaces.splice(idx, 1);
        }.bind(this));
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
            if (parts[0].length > 1 && parts[0][1] == ':') {
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
        parts.forEach(function(partName) {
                menuitem = document.createElement("menuitem");
                menuitem.setAttribute('label', unescape(partName));
                if (i == 0) {
                    menuitem.setAttribute("class", "primary_menu_item");
                    selectedItem = menuitem;
                } else {
                    menuitem.setAttribute("class", "menuitem_mru");
                }
                buildingURI = uriLeader + originalParts.slice(0, numParts - i).join("/");
                if (i == numParts - 1 && buildingURI[buildingURI.length - 1] != '/') {
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
            for (var i = 0; i < dest_fwd_idx; i++) {
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
            var uriPrefs = _placePrefs.getPref(prefName);
            var ids = uriPrefs.getPrefIds();
            if (ids.length > maxArraySize) {
                var nameValueTimeArray = ids.map(function(id) {
                        var pref = uriPrefs.getPref(id);
                        return [id,
                                pref.getStringPref("viewName"),
                                pref.getString("timestamp", "0")];
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
            if (PROJECT_URI_REGEX.test(data)
                && ko.places.multiple_project_view) {
                ko.places.projects.manager.refresh();
            }
        }
    },
    
    handle_project_opened_setup: function(event) {
        ko.places.manager.handle_project_opened(event);
    },
    
    handle_current_view_changed: function(event) {
        var manager = ko.places.manager;
        if (manager.trackCurrentTab_pref) {
            manager.showCurrentEditorTab(/*forceNewPlaceDir=*/ false);
        }
    },
    
    handle_visit_directory_proposed: function(event) {
        ko.places.manager.observe(null, 'visit_directory_proposed', event.detail.visitedPath);
    },
    
    handle_keypress_setup: function(event) {
        return ko.places.viewMgr.onTreeKeyPress(event);
    },
    
    handle_project_opened: function(event) {
        var project = ko.projects.manager.currentProject;
        if (project) {
            var targetDirURI = project.importDirectoryURI;
            if (targetDirURI) {
                var successFunction;
                if (!ko.projects.manager._ensureProjectPaneVisible) {
                    successFunction = function() { /* don't make project pane visible - bug 87868 */};
                }
                // Delay, because at startup the tree might not be
                // fully initialized.
                setTimeout(function() {
                        if (ko.places && ko.places.manager) {
                            ko.places.manager.openDirURI(targetDirURI, null,
                                                         successFunction);
                        }
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
        gPlacesViewMgr.refreshViewByIndex(index);
    },
    __ZIP__: null
};

/** ItemWrapper class -- wrap places URIs in an object
 * that implements old project icons.
 */

function ItemWrapper(uri, type) {
    this.uri = this.url = uri; // allow for both variants.
    this.type = type; // one of 'file', 'folder', or 'project'
    if (type == 'project') {
        var project = (ko.projects.manager.getProjectByURL(uri)
                       || ko.projects.manager.currentProject);
        this.project = project;
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
        var fileObj = Components.classes["@activestate.com/koFileService;1"].
                       getService(Components.interfaces.koIFileService).
                       getFileFromURI(this.uri);
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
    if (document.readyState != "complete") {
        // still loading other things
        log.debug("waiting for document complete");
        window.addEventListener("load", places_onLoad, false);
        return;
    }
    window.removeEventListener("load", places_onLoad, false);
    try {
        ko.places.onLoad_aux();
    } catch(ex) {
        log.exception(ex, "Failed onLoad");
    }
};

this._updatePrefs = function(placePrefs) {
    var filterPrefs = placePrefs.getPref("filters");
    var this_ = this;
    [DEFAULT_FILTER_NAME, CURRENT_PROJECT_FILTER_NAME].forEach(function(prefName) {
            var defaultPrefs = filterPrefs.getPref(prefName);
            if (!defaultPrefs) {
                log.error("Can't get filter prefs for " + prefName + "\n");
            } else {
                this_.updatePrefsForPref(defaultPrefs);
            }
        });
};

this.updatePrefsForPref = function(defaultPrefs) {
    // This code is an unrolled for/switch loop. See
    // http://bugs.activestate.com/show_bug.cgi?id=87813#c12
    // for an explanation.
    
    // 0 => 1: we started at version 1
    
    // 1 => 2:
    // (VERSION == 3)
    try {
        var savedVersion = defaultPrefs.getLong("version", 1);
        if (savedVersion < 2) {
            this.updateDefaultPrefsForVersion(defaultPrefs, DEFAULT_EXCLUDE_MATCHES_PART2);
        }
        if (savedVersion < 3) {
            this.updateDefaultPrefsForVersion(defaultPrefs, DEFAULT_EXCLUDE_MATCHES_PART3);
            defaultPrefs.setLongPref("version", VERSION);
        }
    } catch(ex) {
        log.exception(ex, "Failed in _updatePrefs");
    }
};

this.updateDefaultPrefsForVersion = function(defaultPrefs, newDefaultFilters) {
    var exclude_matches;
    try {
        exclude_matches = defaultPrefs.getStringPref("exclude_matches");
    } catch(ex) {
        exclude_matches = null;
    }
    if (!exclude_matches) {
        defaultPrefs.setStringPref("exclude_matches", DEFAULT_EXCLUDE_MATCHES);
    } else {
        var parts = exclude_matches.split(/;/);
        var newParts = newDefaultFilters.split(";").
            filter(function(name) parts.indexOf(name) === -1);
        if (newParts.length) {
            var updatedParts = parts.concat(newParts);
            defaultPrefs.setStringPref("exclude_matches", updatedParts.join(";"));
        }
    }
};

this.onLoad_aux = function places_onLoad_aux() {
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
    this.handle_show_fullPath_tooltip();
    _placePrefs.prefObserverService.addObserverForTopics(
        this, 1, ['show_fullPath_tooltip'], 1);
                                                         
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
        // Going into 6.1.0, make the CURRENT_PROJECT_FILTER_NAME filter
        // writable from the places filter as well.
        filterPrefs.getPref(CURRENT_PROJECT_FILTER_NAME).setBooleanPref("readonly", false);
    }

    this._updatePrefs(_placePrefs);
    
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
    var showInFinderProjectMenuItem = document.getElementById("menu_projCtxt_showInFinder");
    var platform = navigator.platform.toLowerCase();
    var bundle_id;
    if (platform.substring(0, 3) == "win") {
        bundle_id = "ShowInExplorer.label";
    } else if (platform.substring(0, 5) == "linux") {
        bundle_id = "ShowInFileManager.label";
    } else {
        bundle_id = "ShowInFinder.label";
    }
    [showInFinderMenuItem, showInFinderProjectMenuItem].map(function(elt) {
            elt.setAttribute("label",
                             _bundle.GetStringFromName(bundle_id));
        });
    
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
    if (!widgets.placeView_treeViewDeck) {
        widgets.placeView_treeViewDeck = document.getElementById("placesSubpanelDeck");
    }
    ko.places.updateFilterViewMenu();
    // The "initialize" routine needs to be in a timeout, otherwise the
    // tree will always show a pending icon and never updates.
    window.setTimeout(function() {
            ko.places.manager.initialize();
        }, 1);
    // Call this for either.
    ko.places.projects._updateSubpanelFromState();
    
    // Wait until ko.projects.manager exists before
    // init'ing the projects view tree.
    var mruProjectViewerID;
    this.single_project_view = !ko.projects.manager.initProjectViewPref(_globalPrefs);
    var launch_createProjectMRUView = function() {
        if (ko.projects && ko.projects.manager
            && ko.places.projects.PlacesProjectManager
            && ko.places.projects.ProjectCommandHelper) {
            clearInterval(mruProjectViewerID);
            try {
                ko.places.initProjectMRUCogMenu_SPV();
                ko.places.projects_SPV.createProjectMRUView();
                ko.places.projects.createPlacesProjectView();
                gPlacesViewMgr._setupProjectView(this.single_project_view = !_globalPrefs.getBooleanPref("places.multiple_project_view"));
            } catch(ex) {
                dump("Init failed: " + ex + "\n");
            }
        } else {
            dump("Delaying init SPV menu: ");
            if (!ko.projects || !ko.projects.manager) {
                dump("no projects manager");
            } else if (!ko.places.projects.PlacesProjectManager) {
                dump("no PlacesProjectManager");
            } else if (!ko.places.projects.ProjectCommandHelper) {
                dump("no ProjectCommandHelper");
            } else {
                dump(" ????");
            }
            dump("\n");                
        }
    }.bind(this);
    mruProjectViewerID = setInterval(launch_createProjectMRUView, 50);
}

this.handle_show_fullPath_tooltip = function() {
    var show_fullPath_tooltip = _placePrefs.getBoolean("show_fullPath_tooltip", false);
    var tooltip = show_fullPath_tooltip ? "places-files-tree-popup" : null;
    document.getElementById("places-files-tree-body").
             setAttribute("tooltip", tooltip);
};

this.observe = function(subject, topic, data) {
    if (topic == "show_fullPath_tooltip") {
        this.handle_show_fullPath_tooltip();
    }
}

this.initProjectMRUCogMenu_SPV = function() {
    var srcMenu = parent.document.getElementById("popup_project");
    var destMenu = document.getElementById("placesSubpanelProjectsToolsPopup_SPV");
    var srcNodes = srcMenu.childNodes;
    var node, newNode;
    var len = srcNodes.length;
    for (var i = 0; i < len; i++) {
        node = srcNodes[i];
        if (node.id == "menu_closeAllProjects") {
            // skip this -- hardwired menu item....
        } else if (node.getAttribute("skipCopyToCogMenu") != "true") {
            newNode = node.cloneNode(false);
            newNode.id = node.id + "_places_projects_cog";
            destMenu.appendChild(newNode);
        }
    }
};


this.onUnload = function places_onUnload() {
    ko.places.manager.finalize();
    ko.places.viewMgr.finalize();
    ko.places.projects.terminate();
    ko.places.manager = ko.places._viewMgr = null;
};


this.getFocusedPlacesView = function() {
    if (xtk.domutils.elementInFocus(document.getElementById('placesViewbox_places'))) {
        return this;
    }
    return null;
};

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
    var ids = filterPrefs.getPrefIds();
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

//---- internal support stuff

function _notify(label, value, image, priority, buttons) {
    var notificationBox = parent.document.getElementById("komodo-notificationbox");
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

this._possibleTypes = ['file', 'folder', 'project', 'unopened_project', 'livefolder'];
this._intersectWithPossibleTypes = function(typeListAttr) {
    if (!typeListAttr) return [];
    var targetTypeList = typeListAttr.split(/\s+/);
    var possibleTypes = this._possibleTypes;
    return targetTypeList.filter(function(typeName) possibleTypes.indexOf(typeName) != -1);
}

this.testDisableNode = function(menuNode, selectionInfo) {
    // Context menu setup for the places and both project panels in the
    // places sidebar.  Better to have all code in one area, even with overlap.
    var directive, disableNode = false;
    var itemTypes = selectionInfo.itemTypes;
    if (selectionInfo.noneSelected) {
        disableNode = true;
    } else if (!!(directive = menuNode.getAttribute('disableIf'))
        && (this.matchAnyType(directive, itemTypes)
            || ((directive in selectionInfo) && selectionInfo[directive]))) {
        disableNode = true;
    } else if (!!(directive = menuNode.getAttribute('disableUnless'))) {
        if ((directive in selectionInfo) && selectionInfo[directive]) {
            // don't disable
        } else if (!this.matchAnyType(directive, itemTypes)) {
            disableNode = true;
        }
    }
    if (!disableNode
        && !!(directive = menuNode.getAttribute('testDisableIf'))) {
        var testDisableIf = directive.split(/\s+/);
        testDisableIf.map(function(s) {
                if (s == 't:currentProject' && selectionInfo.currentProject) {
                    disableNode = true;
                } else if (s == "t:multipleSelection" && selectionInfo.multipleNodesSelected) {
                    disableNode = true;
                } else if (s == "t:isRemote" && !selectionInfo.isLocal) {
                    disableNode = true;
                } else if (s == 't:classIsntProject' && selectionInfo.classIsntProject) {
                    disableNode = true;
                }
            });
    }
    if (!disableNode
        && !!(directive = menuNode.getAttribute('testEval_DisableIf'))) {
        try {
            var res = eval(directive);
            if (res) {
                disableNode = true;
            }
        } catch(ex) {
            log.exception(ex, "Failed to eval '" + directive);
            disableNode = true;
        }
    }

    if (!disableNode
        && !!(directive = menuNode.getAttribute('testDisableUnless'))) {
        var testDisableUnless = directive.split(/\s+/);
        var anyTestPasses = false;
        testDisableUnless.map(function(s) {
                if (!anyTestPasses && s == 't:projectIsDirty' && selectionInfo.projectIsDirty) {
                    anyTestPasses = true;
                }
            });
        disableNode = !anyTestPasses;
    }
    if (disableNode) {
        menuNode.setAttribute('disabled', true);
    } else {
        menuNode.removeAttribute('disabled');
    }
    return disableNode;
};

this.matchAnyType = function(typeListAttr, typesSelectedArray) {
    var targetTypeList = this._intersectWithPossibleTypes(typeListAttr);
    return typesSelectedArray.some(function(typeName)
                                   targetTypeList.indexOf(typeName) != -1);
};

this.matchAllTypes = function(typeListAttr, typesSelectedArray) {
    var targetTypeList = this._intersectWithPossibleTypes(typeListAttr);
    return typesSelectedArray.every(function(typeName)
                                    targetTypeList.indexOf(typeName) != -1);
};

/**
 * Returns the current places directory (as a URI).
 * 
 * @returns {String} The URI of the current places directory.
 */
this.getDirectory = function() {
    return ko.places.manager.currentPlace;
};

/**
 * Set places to the given directory.
 * 
 * @param {String} uri - The path or uri of the wanted directory.
 */
this.setDirectory = function(uri) {
    var file = Components.classes["@activestate.com/koFileEx;1"].
            createInstance(Components.interfaces.koIFileEx);
    file.URI = uri;
    if (file.isLocal) {
        this.manager.openDirectory(file.path);
    } else {
        this.manager.openNamedRemoteDirectory(file.URI);
    }
};

}).apply(ko.places);

ko.places.onLoad();
