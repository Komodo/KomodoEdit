/* Copyright (c) 2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/*
 * CodeIntel defnitions choice dialog. Used when multiple definitions have
 * been found.
 *
 * Requires: komodoBaseTreeView.js
 *
 * Contributers:
 *  - Todd Whiteman (ToddW@ActiveState.com)
 */


//----------------------------
//       globals            //
//----------------------------
xtk.include("treeview");

var _ciDefChoice_log = ko.logging.getLogger("CI_Definition_Choice");
//_ciDefChoice_log.setLevel(ko.logging.LOG_DEBUG);
var gCIDefChoiceObj = null;


//----------------------------
//     internal routines    //
//----------------------------

//
// Definition Choice tree view
//
function _ciDefinitionChoiceTreeView(initial_rows) {
    if (!initial_rows) {
        // Default value then
        this._rows = [];
    } else {
        this._rows = initial_rows;
    }
}
// The following two lines ensure proper inheritance (see Flanagan, p. 144).
_ciDefinitionChoiceTreeView.prototype = new xtk.dataTreeView();
_ciDefinitionChoiceTreeView.prototype.constructor = _ciDefinitionChoiceTreeView;

// Override getCellText method for assigning the celltext
_ciDefinitionChoiceTreeView.prototype.getCellText = function(row, column) {
    // forRow is a koICodeIntelDefinition XPCOM object
    var forRow = this._rows[row];
    switch (column.id) {
        case 'ciDefinitionChoice_treecol_name':
            return forRow.name;
        case 'ciDefinitionChoice_treecol_type':
            return forRow.ilk;
        case 'ciDefinitionChoice_treecol_path':
            return forRow.path;
    }
    return "(Unknown column: " + column.id + ")";
};


//
// Definition Choice main class
//
function _ciDefinitionChoice() {
    try {
        //ko.trace.get().enter('_ciDefinitionChoice()');
        // Get handle on needed xul elements
        this.tree = document.getElementById('ciDefinitionChoice_requestHeadersTree');
        this.treeColumn_name = document.getElementById('ciDefinitionChoice_treecol_name');
        this.treeColumn_type = document.getElementById('ciDefinitionChoice_treecol_type');
        this.treeColumn_path = document.getElementById('ciDefinitionChoice_treecol_path');

        if (!this.tree) {
            this.log.error("Couldn't find all required xul elements for a CI Definition Choice.");
            alert("ciDefinitionChoice load failed");
            return;
        }

        // Load the tree view and assign it to the tree
        this.treeView = new _ciDefinitionChoiceTreeView();
        this.tree.treeBoxObject.view = this.treeView;

        //ko.trace.get().leave('_ciDefinitionChoice()');
    } catch (e) {
        _ciDefChoice_log.exception(e);
    }
}

_ciDefinitionChoice.prototype.NAME = 'Code Intelligence Definition Choice Dialog';

_ciDefinitionChoice.prototype.xyz = function()
{
}


//----------------------------
//    public routines       //
//----------------------------

function ciDefinitionChoice_onLoad() {
    try {
        // Init the ciDefinitionChoice
        if (!gCIDefChoiceObj) {
            gCIDefChoiceObj = new _ciDefinitionChoice();
        }

        // Get the definitions passed in
        var defns = window.arguments[0].defns;
        if (typeof defns == "undefined" || defns == null) {
            defns = [];
        }

        // Load the defns into the tree view
        gCIDefChoiceObj.treeView.setTreeRows(defns);
    } catch (e) {
        _ciDefChoice_log.exception(e);
    }
}

function ciDefinitionChoice_onUnload() {
    if (gCIDefChoiceObj && gCIDefChoiceObj.tree.currentIndex >= 0) {
        var row = gCIDefChoiceObj.tree.currentIndex;
        window.arguments[0].selectedDefn = gCIDefChoiceObj.treeView._rows[row];
    } else {
        window.arguments[0].selectedDefn = null;
    }
}

function ciDefinitionChoice_onOK() {
    window.arguments[0].retval = "OK";
    return true;
}

function ciDefinitionChoice_onCancel() {
    window.arguments[0].retval = "Cancel";
    return true;
}

function ciDefinitionChoice_onTreeDblClick() {
    window.arguments[0].retval = "OK";
    window.close();
}
