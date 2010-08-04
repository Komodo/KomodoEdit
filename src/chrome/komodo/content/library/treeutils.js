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

this.getSelectedIndices = function(view, rootsOnly) {
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

}).apply(ko.treeutils);
