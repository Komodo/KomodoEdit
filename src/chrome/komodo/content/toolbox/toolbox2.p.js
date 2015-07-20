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

/* New Toolbox Manager
 *
 * Implementation of Komodo's new toolbox manager.
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.toolbox2)=='undefined') {
    ko.toolbox2 = {};
}
(function() {
var _prefs = Components.classes["@activestate.com/koPrefService;1"].
                getService(Components.interfaces.koIPrefService).prefs;
var widgets = {};
var log = ko.logging.getLogger("ko.toolbox2");
var XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";

function Toolbox2Manager() {
    this.widgets = widgets; // for ease of access?
}

Toolbox2Manager.prototype = {
bindComponents: function() {
    this.toolbox2Svc = Components.classes["@activestate.com/koToolbox2Service;1"]
            .getService(Components.interfaces.koIToolbox2Service);
    if (!this.toolbox2Svc) {
        throw new Error("couldn't create a koIToolbox2Service");
    }
    this.toolsMgr = Components.classes["@activestate.com/koToolbox2ToolManager;1"]
        .getService(Components.interfaces.koIToolbox2ToolManager);
    if (!this.toolsMgr) {
        throw new Error("couldn't create a koIToolbox2ToolManager");
    }
    this.view = Components.classes["@activestate.com/KoToolbox2HTreeView;1"]
        .createInstance(Components.interfaces.koIToolbox2HTreeView);
    if (!this.view) {
        throw new Error("couldn't create a koIToolbox2HTreeView");
    }
},
initialize: function() {
    // Create the component fields first before initializing,
    // as callbacks to the JS code will need all three components
    this.bindComponents();
    widgets.tree = document.getElementById("toolbox2-hierarchy-tree");
    widgets.filterTextbox = document.getElementById("toolbox2-filter-textbox");
    this.tree = widgets.tree;
    this.tree.treeBoxObject
                    .QueryInterface(Components.interfaces.nsITreeBoxObject)
                    .view = this.view;
    this.view.setTree(this.tree.treeBoxObject);
    try {
        this.toolbox2Svc.migrateVersion5Toolboxes();
        this.toolbox2Svc.initialize();
        // Inform the macro system the toolbox has been loaded.
        if (ko.macros) {
            ko.macros.onToolboxInitialized();
        }
    } catch(ex) {
        log.exception("Failed to create toolboxes: " + ex);
    }
    var currentProject;
    try {
        currentProject = ko.projects.manager.currentProject;
    } catch(ex) {
        currentProject = null;
    }
    this.view.initialize(currentProject);

    this._fixCogPopupmenu();
        
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
    getService(Components.interfaces.nsIObserverService);
    obsSvc.addObserver(this, 'toolbox-tree-changed', 0);
    obsSvc.addObserver(this, 'toolbox-reload-view', 0);
    // Give the toolbox observers time to have started up before
    // notifying them that the toolbox has changed.
    setTimeout(function() {
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
        var koDirSvc = Components.classes["@activestate.com/koDirs;1"].getService();
        // Same definition as in koToolbox2.py
        const DEFAULT_TARGET_DIRECTORY = "tools";
        var stdToolboxDir = osPathSvc.join(koDirSvc.userDataDir,
                                 DEFAULT_TARGET_DIRECTORY);
        var sharedToolboxDir = osPathSvc.join(koDirSvc.commonDataDir,
                                    DEFAULT_TARGET_DIRECTORY);
        // This fixes bug 88569
        // TODO: Make sure all extensions are loaded as well.
        // Don't pass empty-string, because then project trigger macros
        // will be loaded in all windows, should only be in the window
        // the project is active in.
        [stdToolboxDir, sharedToolboxDir].map(function(dir) {
        try {
            obsSvc.notifyObservers(null, 'toolbox-loaded-global', dir);
        } catch(ex) {
            dump("Failed to notifyObservers(toolbox-loaded-global): " + ex + "\n");
        }});
        }, 1000);
},
terminate: function() {
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
    getService(Components.interfaces.nsIObserverService);
    obsSvc.removeObserver(this, 'toolbox-tree-changed');
    obsSvc.removeObserver(this, 'toolbox-reload-view');
    this.view.terminate();
},

addProject: function(project) {
    this.view.addProject(project);
    this.toolbox2Svc.activateProjectToolbox(project);
},

removeProject: function(project) {
    this.view.removeProject(project);
    this.toolbox2Svc.deactivateProjectToolbox(project);
},

deleteCurrentItem: function() {
    var index = this.view.selection.currentIndex;
    try {
        this.view.deleteToolAt(index);
    } catch(ex) {
        dump(ex + "\n");
    }
},

_fixCogPopupmenu: function() {
    var popupmenu = document.getElementById("toolbox2-cog-popup");
    var mi, childNode, i;
    // Pull these nodes out of the root menu
    var src_popupmenu  = document.getElementById("tb2ContextMenu_addPopupMenu");
    var childNodes = src_popupmenu.childNodes;
    for (i = 0; i <  childNodes.length; i++) {
        childNode = childNodes[i];
        if (!childNode) {
            continue;
        }
        if (childNode.nodeName == "menuseparator"
            || childNode.nodeName == "menuitem") {
            mi = document.createElementNS(XUL_NS, childNode.nodeName);
            mi.id = childNode.id + "_cog_contextMenu";
            if (childNode.nodeName == "menuitem") {
                ["label", "class", "accesskey", "image"].map(function(attr) {
                        mi.setAttribute(attr, childNode.getAttribute(attr));
                    });
                var cmd = childNode.getAttribute("oncommand");
                var fixedCmd = cmd.replace('addToolboxItem', 'addToolboxItemToStdToolbox');
                mi.setAttribute("oncommand", fixedCmd);
            }
            popupmenu.appendChild(mi);
        }
    }
    popupmenu.appendChild(document.createElementNS(XUL_NS, 'menuseparator'));
    var src_popupmenu  = document.getElementById("tb2ContextMenu_importPopupMenu");
    var childNodes = src_popupmenu.childNodes;
    for (i = 0; i < childNodes.length; i++) {
        childNode = childNodes[i];
        if (!childNode || childNode.getAttribute('disableIfInMenu') == 'standardToolbox') {
            continue;
        }
        mi = document.createElementNS(XUL_NS, childNode.nodeName);
        mi.id = childNode.id + "_cog_contextMenu";
        if (childNode.nodeName == "menuitem") {
            ["label", "class", "accesskey", "image"].map(function(attr) {
                    mi.setAttribute(attr, childNode.getAttribute(attr));
                });
            var cmd = childNode.getAttribute("oncommand");
            var fixedCmd = cmd.replace('(event)', '_toStdToolbox(event)');
            mi.setAttribute("oncommand", fixedCmd);
        }
        popupmenu.appendChild(mi);
    }
},

updateFilter: function(event) {
    var textbox = this.widgets.filterTextbox;
    var filterPattern = textbox.value;
    this.view.setFilter(filterPattern);
},

observe: function(subject, topic, data) {
    var manager = ko.toolbox2.manager;
    if (topic == 'toolbox-tree-changed') {
        manager.view.redoTreeView(ko.projects.manager.currentProject);
    } else if (topic == 'toolbox-reload-view') {
        var path = data;
        var tool = manager.toolsMgr.getToolFromPath(path);
        if (tool) {
            var index = manager.view.getIndexByTool(tool);
            if (index >= 0) {
                manager.view.reloadToolsDirectoryView(index);
            } else {
                manager.view.refreshFullView();
            }
        }
    }
},

_EOD_: null
};

this.onload = function() {
    this.log = log;
    ko.main.addWillCloseHandler(this.onUnload, this);
    widgets.sortNatural = document.getElementById("toolbox2-cog_sortNatural");
    widgets.sortAscending = document.getElementById("toolbox2-cog_sortAscending");
    widgets.sortDescending = document.getElementById("toolbox2-cog_sortDescending");
    this._sortDirection = "natural";
    if (_prefs.hasPref("toolbox2")) {
        var toolboxPrefs = _prefs.getPref("toolbox2");
        if (toolboxPrefs.hasPref("sortDirection")) {
            this._sortDirection = toolboxPrefs.getStringPref("sortDirection");
        }
    }
    var sortTypeCamelCase = ('sort'
                             + this._sortDirection.substr(0, 1).toUpperCase()
                             + this._sortDirection.substr(1));
    widgets[sortTypeCamelCase].setAttribute('checked', 'true');
    this.manager = new Toolbox2Manager();
    this.manager.initialize();
    widgets.tree.addEventListener('keypress',
                                  this.handle_keypress_setup, true);
    //  _arrowKeys used by onTreeKeyPress, easier to init here.
    var nsIDOMKeyEvent = Components.interfaces.nsIDOMKeyEvent;
    this._arrowKeys = [nsIDOMKeyEvent.DOM_VK_UP,
                       nsIDOMKeyEvent.DOM_VK_DOWN,
                       nsIDOMKeyEvent.DOM_VK_LEFT,
                       nsIDOMKeyEvent.DOM_VK_RIGHT];
};

this.onUnload = function() {
    widgets.tree.removeEventListener('keypress',
                                     this.handle_keypress_setup, true);
    var this_ = ko.toolbox2;
    this_.manager.terminate();
    try {
        _prefs.getPref("toolbox2").setStringPref("sortDirection", this._sortDirection);
    } catch(ex) {
        dump("toolbox2.p.js: terminate: " + ex + "\n");
    }
    ko.main.removeWillCloseHandler(this.onUnload);
};

this._sortValuesByName = {
    'natural': Components.interfaces.koIToolbox2HTreeView.SORT_BY_NATURAL_ORDER,
    'ascending': Components.interfaces.koIToolbox2HTreeView.SORT_BY_NAME_ASCENDING,
    'descending': Components.interfaces.koIToolbox2HTreeView.SORT_BY_NAME_DESCENDING
};

this.sortRows = function(sortDirection) {
    this._sortDirection = sortDirection;
    this.manager.view.sortDirection = this._sortValuesByName[sortDirection];
};

this.updateContextMenu = function(event, menupopup) {
    if (!event.explicitOriginalTarget) {
        dump("No event.explicitOriginalTarget\n");
        return;
    }
    var clickedNodeId = event.explicitOriginalTarget.id;
    //dump("updateContextMenu: clickedNodeId: " + clickedNodeId + "\n");
    if (clickedNodeId == "tb2ContextMenu_addPopupMenu"
        || clickedNodeId == "tb2ContextMenu_importPopupMenu") {
        // No further checking needed -- we're in a secondary menu for a
        // container, and we accept everything.
        return;
    }
    var row = {};
    var manager = this.manager;
    manager.tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    var toolType;
    if (index == -1) {
        toolType = "standardToolbox";
        this.multipleNodesSelected = false;
        this.raggedMultipleSelection = false;
    } else {
        toolType = manager.view.get_toolType(index);
        if (!toolType) {
            dump("Awp -- updateContextMenu -- no tooltype\n");
            event.stopPropagation();
            event.preventDefault();
            return;
        }
        this.multipleNodesSelected = manager.view.selection.count > 1;
        this.raggedMultipleSelection = (this.multipleNodesSelected
                                        && !manager.view.selectedItemsHaveSameParent());
    }
    this.processMenu(menupopup, toolType);
};

this.processMenu = function(menuNode, toolType) {
    //todo: testHideIf
    var hideUnless = menuNode.getAttribute('hideUnless');
    if (hideUnless && hideUnless.indexOf(toolType) == -1) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
    }
    var hideIf = menuNode.getAttribute('hideIf');
    if (hideIf && hideIf.indexOf(toolType) != -1) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
    }
    var multipleNodesSelected = this.multipleNodesSelected;
    var raggedMultipleSelection = this.raggedMultipleSelection;
    var testHideIf = menuNode.getAttribute('testHideIf');
    if (testHideIf) {
        testHideIf = testHideIf.split(/\s+/);
        var leave = false;
        testHideIf.map(function(s) {
                if (s == 't:multipleSelection' && multipleNodesSelected) {
                    menuNode.setAttribute('collapsed', true);
                    leave = true;
                } else if (s == 't:singleSelection' && !multipleNodesSelected) {
                    menuNode.setAttribute('collapsed', true);
                    leave = true;
                }
            });
        if (leave) {
            return;
        }
    }
    
    menuNode.removeAttribute('collapsed');
    var disableNode = false;
    var disableIf = menuNode.getAttribute('disableIf');
    if (disableIf.indexOf(toolType) != -1) {
        disableNode = true;
    } else {
        var disableIfInMenu = menuNode.getAttribute('disableIfInMenu');
        if (disableIfInMenu && disableIfInMenu.indexOf(toolType) >= 0) {
            //Comment on TODO: Check to see if we're in a menubar already
            // The processMenu routine only does this for top-level menus.
            disableNode = true;
        }
        if (!disableNode) {
            var disableUnless = menuNode.getAttribute('disableUnless');
            if (disableUnless && disableUnless.indexOf(toolType) == -1) {
                disableNode = true;
            }
            if (!disableNode) {
                var testDisableIf = menuNode.getAttribute('testDisableIf');
                if (testDisableIf) {
                    testDisableIf = testDisableIf.split(/\s+/);
                    testDisableIf.map(function(s) {
                            if (disableNode) {
                                // Don't bother with further tests
                            } else if (s == 't:multipleSelection' && multipleNodesSelected) {
                                disableNode = true;
                            } else if (s == 't:singleSelection' && !multipleNodesSelected) {
                                disableNode = true;
                            } else if (s == 't:raggedMultipleSelection' && raggedMultipleSelection) {
                                // disable unless all nodes have the same parent
                                disableNode = true;
                            } else if (s == 't:clipboardHasNoURI'
                                       && !xtk.clipboard.containsFlavors(["text/uri-list"])) {
                                // This could be more sophisticated:
                                // Distinguish snippet-pasting vs. URI-pasting.
                                disableNode = true;
                            }
                        });
                }
            }
            if (!disableNode) {
                var testDisableUnless = menuNode.getAttribute('testDisableUnless');
                if (testDisableUnless) {
                    testDisableUnless = testDisableUnless.split(/\s+/);
                    var cmdPrefix = 'cmd:';
                    testDisableUnless.map(function(s) {
                            if (s.indexOf(cmdPrefix) == 0) {
                                var cmdName = s.substring(cmdPrefix.length);
                                var controller = top.document.commandDispatcher.getControllerForCommand(cmdName);
                                if (controller && !controller.isCommandEnabled(cmdName)) {
                                    disableNode = true;
                                }
                            }
                        });
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
        this.processMenu(childNodes[i], toolType);
    }
};

this.getSelectedIndices = function(rootsOnly /*=false*/) {
    if (typeof(rootsOnly) == "undefined") rootsOnly = false;
    var view = this.manager.view;
    return ko.treeutils.getSelectedIndices(view, rootsOnly);
};

this.getSelectedItem = function() {
     var selection = this.manager.view.selection;
     if (!selection || !selection.count) {
         return null;
     }
     var index = selection.currentIndex;
     if (index == -1) {
         return null;
     }
     return this.manager.view.getTool(index);
};

this.getContainerFromIndex = function(index) {
    var item;
    if (index == -1) {
        item = this.getStandardToolbox();
    } else if (this.manager.view.isContainer(index)) {
        item = this.manager.view.getTool(index);
    } else if (this.manager.view.getLevel(index) == 0) {
            // It's a top-level non-container, so it lies in the std toolbox
        item = this.getStandardToolbox();
    } else {
        index = this.manager.view.getParentIndex(index);
        if (index == -1) {
            log.warn("toolbox2.p.js.getContainerFromIndex: Tool has no parent");
            item = this.getStandardToolbox();
        } else if (!this.manager.view.isContainer(index)) {
            log.warn("toolbox2.p.js.getContainerFromIndex: Tool's parent ("
                     + index
                     + ") isn't a container");
            item = this.getStandardToolbox();
        } else {
            item = this.manager.view.getTool(index);
        }
    }
    return item;
};

this.getSelectedContainer = function() {
    var item = this.getSelectedItem();
    if (!item) {
        item = this.getStandardToolbox();
    } else {
        var index = this.manager.view.getIndexByTool(item);
        return this.getContainerFromIndex(index);
    }
    return item;
};

this.getProjectToolbox = function(uri) {
    var id = this.manager.toolbox2Svc.getProjectToolboxId(uri);
    if (id == -1) return null;
    return this.manager.toolsMgr.getToolById(id);
}

this.getStandardToolbox = function() {
    return this.manager.toolbox2Svc.getStandardToolbox();
    //return this.findToolById(this.manager.toolbox2Svc.getStandardToolboxID());
}

this.getExtensionToolbox = function(extensionName) {
    return this.manager.toolbox2Svc.getExtensionToolbox(extensionName);
    //return this.findToolById(this.manager.toolbox2Svc.getStandardToolboxID());
}

 this.addItem = function(/* koITool */ tool, /* koITool */ parent,
                         selectItem /*false*/) {
    if (typeof(selectItem) == 'undefined') selectItem = false;
    if (typeof(parent)=='undefined' || !parent) {
        parent = this.getStandardToolbox();
    }
    var view = this.manager.view;
    view.addNewItemToParent(parent, tool);
    if (selectItem) {
        var index = view.getIndexByTool(tool);
        if (index != -1) {
            view.selection.currentIndex = index;
            view.selection.select(index);
        }
    }
}

this.addNewItemToParent = function(item, parent) {
    this.manager.view.addNewItemToParent(parent, item);
};

this.applyKeybindings = function () {
    var tools = {};
    this.manager.toolsMgr.getToolsWithKeyboardShortcuts("", tools, {});
    tools = tools.value;
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    for (var i = 0; i < tools.length; i++) {
        var tool = tools[i];
        obsSvc.notifyObservers(tool, 'kb-load', tool.id);
    }
}

this.createPartFromType = function(toolType) {
    return this.manager.toolsMgr.createToolFromType(toolType);
};

this.findToolById = function(id) {
    return this.manager.toolsMgr.getToolById(id);
};

/**
 * Ensure the given tool is visible in the toolbox tree.
 *
 * Note: Does not ensure the toolbox pane is visible.
 *
 * @param {koITool} tool    The tool to make visible.
 * @param {Object} options  Optional, "select" property means to select the item.
 */
this.ensureToolVisible = function(tool, options) {
    var view = this.manager.view;
    var ensureParentOpened = function(t) {
        let i = view.getIndexByTool(t);
        if (i == -1 && t.parent) {
            ensureParentOpened(t.parent);
            i = view.getIndexByTool(t);
        }
        if (view.isContainer(i) && !view.isContainerOpen(i)) {
            view.toggleOpenState(i);
        }
    }
    let index = view.getIndexByTool(tool);
    if (index == -1 && tool.parent) {
        ensureParentOpened(tool.parent);
        index = view.getIndexByTool(tool);
    }
    this.manager.tree.treeBoxObject.ensureRowIsVisible(index);
    if (options && options["select"]) {
        view.selection.currentIndex = index;
        view.selection.select(index);
    }
};

this.getAbbreviationSnippet = function(abbrev, subnames, isAutoAbbrev/*=false*/) {
    if (typeof(isAutoAbbrev) == "undefined") {
        isAutoAbbrev = false;
    }
    return this.manager.toolsMgr.getAbbreviationSnippet(abbrev, subnames,
                                                        subnames.length,
                                                        isAutoAbbrev);
};

this.getToolsByTypeAndName = function(toolType, toolName) {
    var tools = {};
    this.manager.toolsMgr.getToolsByTypeAndName(toolType, toolName,
                                                tools, {});
    return tools.value;
};

this.getViCommand = function(commandName) {
    var folders = {};
    this.manager.toolsMgr.getToolsByTypeAndName('folder', "Vi Commands",
                                                folders, {});
    folders = folders.value;
    for (var folder, i = 0; folder = folders[i]; i++) {
        var tool = folder.getChildByName(commandName, true);
        if (tool) {
            return tool;
        }
    }
    return null;
};

this.getCustomMenus = function(dbPath) {
    var obj = {};
    this.manager.toolsMgr.getCustomMenus(dbPath, obj, {});
    return obj.value;
};

this.getCustomToolbars = function(dbPath) {
    var obj = {};
    this.manager.toolsMgr.getCustomToolbars(dbPath, obj, {});
    return obj.value;
};

this.getTriggerMacros = function(dbPath) {
    var obj = {};
    this.manager.toolsMgr.getTriggerMacros(dbPath, obj, {});
    return obj.value;
};

this.getToolsWithKeyboardShortcuts = function(dbPath) {
    var obj = {};
    this.manager.toolsMgr.getToolsWithKeyboardShortcuts(dbPath, obj, {});
    return obj.value;
};

this.handle_keypress_setup = function(event) {
    return ko.toolbox2.onTreeKeyPress(event);
}

this.onFilterKeypress = function(event) {
    try {
        if (event.keyCode == event.DOM_VK_TAB && !event.ctrlKey) {
            event.cancelBubble = true;
            event.stopPropagation();
            event.preventDefault();
            this.manager.widgets.tree.focus();
            return;
        } else if (event.keyCode == event.DOM_VK_ESCAPE) {
            if (this.widgets.filterTextbox.value != '') {
                this.widgets.filterTextbox.value = '';
                this.updateFilter();
                event.cancelBubble = true;
                event.stopPropagation();
                event.preventDefault();
            }
            return;
        }
    } catch (e) {
        log.exception(e);
    }
};

this.removeItem = function(item) {
    var index = this.manager.view.getIndexByTool(item);
    if (index != -1) {
        this.manager.view.deleteToolAt(index);
    }
};

this.updateFilter = function(event) {
    return this.manager.updateFilter();
};

}).apply(ko.toolbox2);
