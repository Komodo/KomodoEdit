/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}

// Utility functions to work with trees.  Successor to partviewers.

// This requires the treeview supports and exports getNextSiblingIndexModel(idx)
// via IDL

ko.treeutils = {};
(function() {
    
this.getAllIndices = function(view) {
    var treeSelection = view.selection;
    var a = [];
    var numRanges = treeSelection.getRangeCount();
    var min = {}, max = {};
    for (var i = 0; i < numRanges; i++) {
        treeSelection.getRangeAt(i, min, max);
        var mx = max.value;
        for (var j = min.value; j <= mx; j++) {
            a.push(j);
        }
    }
    return a;
};

this.getSelectedIndices = function(view, rootsOnly) {
    var indices = this.getAllIndices(view);
    var lim = indices.length;
    var selectedIndices = [];
    for (var i = 0; i < lim; i++) {
        var index = indices[i];
        selectedIndices.push(index);
        if (rootsOnly && view.isContainerOpen(index)) {
            var nextSiblingIndex = view.getNextSiblingIndex(index);
            if (nextSiblingIndex == -1) {
                break;
            }
            while (i < lim - 1 && indices[i + 1] < nextSiblingIndex) {
                i += 1;
            }
        }
    }
    return selectedIndices;
};

}).apply(ko.treeutils);
