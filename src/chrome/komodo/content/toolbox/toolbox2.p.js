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
    dump("**************** toolbox2.p.js: Clearing ko.toolbox2\n");
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
    dump("updateContextMenu: clickedNodeId: " + clickedNodeId + "\n");
    var row = {};
    var manager = this.manager;
    manager.tree.treeBoxObject.getCellAt(event.pageX, event.pageY, row, {},{});
    var index = row.value;
    var toolType = manager.view.get_toolType(index);
    if (!toolType) {
        dump("Awp -- updateContextMenu -- no tooltype\n");
        return;
    }
    this.processMenu(menupopup, toolType);
};

this.processMenu = function(menuNode, toolType) {
    var hideUnless = menuNode.getAttribute('hideUnless');
    if (hideUnless && hideUnless.indexOf(toolType) == -1) {
        menuNode.setAttribute('collapsed', true);
        return; // No need to do anything else
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

this.findToolById = function(id) {
    return this.manager.view.getToolById(id);
};

}).apply(ko.toolbox2);

window.addEventListener("load", ko.toolbox2.onLoad, false);
