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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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
