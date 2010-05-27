/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
initialize: function() {
    widgets.tree = document.getElementById("toolbox2-hierarchy-tree");
    this.tree = widgets.tree;
    this.view = Components.classes["@activestate.com/KoToolbox2HTreeView;1"]
        .createInstance(Components.interfaces.koIToolbox2HTreeView);
    if (!this.view) {
        throw("couldn't create a koIToolbox2HTreeView");
    }
    this.tree.treeBoxObject
                    .QueryInterface(Components.interfaces.nsITreeBoxObject)
                    .view = this.view;
    this.view.initialize();
},
terminate: function() {
    dump("**************** Closing Toolbox2Manager...\n");
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
_EOD_: null
};

this.onLoad = function() {
    var this_ = ko.toolbox2;
    window.addEventListener("unload", this_.onUnload, false);
    var this_ = ko.toolbox2;
    this_.manager = new Toolbox2Manager();
    this_.manager.initialize();
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
    var toolType = manager.view.get_toolType(index);
    if (!toolType) {
        dump("Awp -- updateContextMenu -- no tooltype\n");
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

this.addNewItemToParent = function(item, parent) {
    this.manager.view.addNewItemToParent(parent, item);
};

this.findToolById = function(id) {
    return this.manager.view.getToolById(id);
};

this.getTriggerMacros = function() {
    var obj = {};
    this.manager.view.getTriggerMacros(obj, {});
    return obj.value;
};

this.getToolsWithKeyboardShortcuts = function() {
    var obj = {};
    this.manager.view.getToolsWithKeyboardShortcuts(obj, {});
    return obj.value;
};

}).apply(ko.toolbox2);

window.addEventListener("load", ko.toolbox2.onLoad, false);
