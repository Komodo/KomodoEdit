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
},
_EOD_: null
};

this.onLoad = function() {
    window.addEventListener("unload", ko.toolbox2.onUnload, false);
    this.manager = new Toolbox2Manager();
    this.manager.initialize();
}

this.onUnload = function() {
    this.manager.terminate();
}

}).apply(ko.toolbox2);

window.addEventListener("load", ko.toolbox2.onLoad, false);
