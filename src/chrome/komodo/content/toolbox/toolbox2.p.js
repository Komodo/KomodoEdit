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
function Toolbox2Manager() {
    this.widgets = widgets; // for ease of access?
}

Toolbox2Manager.prototype = {
bindComponents: function() {
    this.toolbox2Svc = Components.classes["@activestate.com/koToolBox2Service;1"]
            .getService(Components.interfaces.koIToolBox2Service);
    if (!this.toolbox2Svc) {
        throw("couldn't create a koIToolBox2Service");
    }
    this.toolsMgr = Components.classes["@activestate.com/koToolbox2ToolManager;1"]
        .getService(Components.interfaces.koIToolbox2ToolManager);
    if (!this.toolsMgr) {
        throw("couldn't create a koIToolbox2ToolManager");
    }
    this.view = Components.classes["@activestate.com/KoToolbox2HTreeView;1"]
        .createInstance(Components.interfaces.koIToolbox2HTreeView);
    if (!this.view) {
        throw("couldn't create a koIToolbox2HTreeView");
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
    this.toolbox2Svc.migrateVersion5Toolboxes();
    this.toolbox2Svc.initialize();
    this.view.initialize();
    // Give the toolbox observers time to have started up before
    // notifying them that the toolbox has changed.
    setTimeout(function() {
        var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
               getService(Components.interfaces.nsIObserverService);
        try {
            obsSvc.notifyObservers(null, 'toolbox-loaded', '');
        } catch(ex) {
            dump("Failed to notifyObservers(toolbox-loaded): " + ex + "\n");
        }
        }, 1000);
},
terminate: function() {
    this.view.terminate();
},
deleteCurrentItem: function() {
    var index = this.view.selection.currentIndex;
    try {
        this.view.deleteToolAt(index);
    } catch(ex) {
        dump(ex + "\n");
    }
},

updateFilter: function(event) {
    var textbox = this.widgets.filterTextbox;
    var filterPattern = textbox.value;
    this.view.setFilter(filterPattern);
    if (filterPattern && this.view.rowCount) {
        this.view.selection.select(0);
    }
},

_EOD_: null
};

this.onload = function() {
    ko.main.addWillCloseHandler(this.onUnload, this);
    this.manager = new Toolbox2Manager();
    this.manager.initialize();
};

this.onUnload = function() {
    var this_ = ko.toolbox2;
    this_.manager.terminate();
};

this.updateContextMenu = function(event, menupopup) {
    if (!event.explicitOriginalTarget) {
        dump("No event.explicitOriginalTarget\n");
        return;
    }
    var clickedNodeId = event.explicitOriginalTarget.id;
    //dump("updateContextMenu: clickedNodeId: " + clickedNodeId + "\n");
    if (clickedNodeId == "tb2ContextMenu_addPopupMenu") {
        // No further checking needed -- we're in a secondary menu for a
        // container, and we accept everything.
        return;
    }
    var row = {};
    var manager = this.manager;
    manager.tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    if (index == -1) {
        // Means that we're clicking in white-space below.
        // Item should work on the most recent folder.
        var selection = manager.view.selection;
        if (selection.count == 0) {
            // Use the Standard Toolbox
            index = 0; //XXX: Watch out: the "Standard Toolbox" folder might be implicit
            manager.view.selection.select(index);
        } else {
            // This will be the last item clicked on in a multi-item selection.
            index = selection.currentIndex; 
        }
    }
    var toolType = manager.view.get_toolType(index);
    if (!toolType) {
        dump("Awp -- updateContextMenu -- no tooltype\n");
        event.cancelBubble = true;
        event.stopPropagation();
        event.preventDefault();
        return;
    }
    this.multipleNodesSelected = manager.view.selection.count > 1;
    if (!this.multipleNodesSelected) {
        this.raggedMultipleSelection = false;
    } else {
        this.raggedMultipleSelection = !manager.view.selectedItemsHaveSameParent();
    }
    this.processMenu(menupopup, toolType);
};

this.processMenu = function(menuNode, toolType) {
    //todo: testHideIf
    var hideUnless = menuNode.getAttribute('hideUnless');
    var multipleNodesSelected = this.multipleNodesSelected;
    var raggedMultipleSelection = this.raggedMultipleSelection;
    if (hideUnless && hideUnless.indexOf(toolType) == -1) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
    }
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
            //TODO: Check to see if we're in a menubar already
            //disableNode = true;
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
                            if (s == 't:multipleSelection' && multipleNodesSelected) {
                                disableNode = true;
                            } else if (s == 't:singleSelection' && !multipleNodesSelected) {
                                disableNode = true;
                            } else if (s == 't:raggedMultipleSelection' && raggedMultipleSelection) {
                                // disable unless all nodes have the same parent
                                disableNode = true;
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
    var treeSelection = view.selection;
    var selectedIndices = [];
    var numRanges = treeSelection.getRangeCount();
    var min = {}, max = {};
    for (var i = 0; i < numRanges; i++) {
        treeSelection.getRangeAt(i, min, max);
        var mx = max.value;
        for (var j = min.value; j <= mx; j++) {
            selectedIndices.push(j);
            if (rootsOnly && view.isContainerOpen(j)) {
                var nextSiblingIndex = view.getNextSiblingIndex(j);
                if (nextSiblingIndex <= mx) {
                    j = nextSiblingIndex -1;
                } else {
                    if (nextSiblingIndex == -1
                        && i < numRanges - 1) {
                        throw new Error("node at row "
                                        + j
                                        + " supposedly at end, but we're only at range "
                                        + (i + 1)
                                        + " of "
                                        + numRanges);
                    }
                    j = mx;
                }
            }
        }
    }
    return selectedIndices;
};

this.getSelectedItem = function() {
     var selection = this.manager.view.selection;
     if (!selection) {
         return null;
     }
     var index = selection.currentIndex;
     if (index == -1) {
         return null;
     }
     return this.manager.view.getTool(index);
};

this.getStandardToolbox = function() {
    return this.findToolById(this.manager.toolbox2Svc.getStandardToolboxID());
}

this.addItem = function(/* koITool */ tool, /* koITool */ parent) {
    if (typeof(parent)=='undefined' || !parent) {
        parent = this.getStandardToolbox();
    }
    this.manager.view.addNewItemToParent(parent, tool);
}

this.addNewItemToParent = function(item, parent) {
    this.manager.view.addNewItemToParent(parent, item);
};

this.createPartFromType = function(toolType) {
    return this.manager.toolsMgr.createToolFromType(toolType);
};

this.findToolById = function(id) {
    return this.manager.toolsMgr.getToolById(id);
};

this.getAbbreviationSnippet = function(abbrev, subnames) {
    return this.manager.toolsMgr.getAbbreviationSnippet(abbrev, subnames,
                                                        subnames.length);
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

this.updateFilter = function(event) {
    return this.manager.updateFilter();
};

}).apply(ko.toolbox2);
