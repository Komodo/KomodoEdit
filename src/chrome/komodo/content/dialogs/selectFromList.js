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

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Generic OK/Cancel dialog from which the user can select from a list of
 * items.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments, except "items"
 *  are optional. See ko.dialogs.selectFromList() documentation for details.
 *      .title          the dialog title
 *      .prompt         the question to ask
 *      .items          is the list of items from which the user can choose
 *      .selectionCondition is a string defining how selection behaves
 *      .stringifier    a function that, if non-null, will be called to
 *                      stringify each item for display.
 *      .doNotAskUI     show the "Don't ask me again" UI
 *      .yesNoCancel    is a boolean to make this a Yes/No/Cancel dialog
 *  On return window.arguments[0] has:
 *      .retval         "OK" or "Cancel"
 *      .selected       (only iff .retval=="OK") a list of selected items
 *      .doNotAsk       (iff .doNotAskUI) a boolean indicating if this question
 *                      need be asked again.
 *
 */

var log = ko.logging.getLogger("dialogs.selectFromList");
//log.setLevel(ko.logging.LOG_DEBUG);

var gItems = null;          // List of items from which user is to select.
var gSelectionCondition = null;
var gDoNotAskUI = false;    // true iff "Don't ask me again" UI is being used.
var gStringifier = null;
var gArgObj = null;


var gItemsTreeView = {  // The nsITreeView object for the list of items.
    getCellText : function(row, column) {
        if (gStringifier) {
            return gStringifier(gItems[row]);
        } else if (typeof(gItems[row]) == 'string') {
            return gItems[row];
        } else {
            return gItems[row].text;
        }
    },
    rowCount : function() { return gItems.length; },

    // Everything below here is just to satisfy the interface, and not all of it may
    // be required.
    tree : null,
    isSeparator : function(index) {return false;},
    setTree : function(out) { this.tree = out; },
    getRowProperties : function(row,prop){},
    getColumnProperties : function(column,prop){},
    getCellProperties : function(row,prop){},
    isContainer : function(row) {return false;},
    isContainerOpen: function(index) { return false;},
    isContainerEmpty: function(index) { return false; },
    cycleCell: function(row, colId) {},
    setRowCount : function(rowCount) {
        this.rowCount = rowCount;
        this.tree.beginUpdateBatch();
        this.tree.rowCountChanged(0, this.rowCount);
        this.tree.invalidate();
        this.tree.endUpdateBatch();
    },
    selectionChanged : function() {},
    performAction : function(action) {},
    isSorted : function() {return true;},
    getImageSrc : function() {return null;},
    cycleHeader : function() {},
    /* our own defined methods */
    sort: function() {}
};


//---- interface routines for XUL

function OnLoad()
{
    var dialog = document.getElementById("dialog_selectFromList")
    var acceptButton = dialog.getButton("accept");
    var noButton = dialog.getButton("extra1");
    var cancelButton = dialog.getButton("cancel");
    var itemsTree = document.getElementById("items");
    var msg;
    gArgObj = window.arguments[0];
    // .title
    if (typeof gArgObj.title != "undefined" &&
        gArgObj.title != null) {
        document.title = gArgObj.title;
    } else {
        document.title = "Komodo";
    }

    // .prompt
    var descWidget = document.getElementById("prompt");
    var desc = gArgObj.prompt;
    if (typeof desc != "undefined" && desc != null) {
        var textUtils = Components.classes["@activestate.com/koTextUtils;1"]
                            .getService(Components.interfaces.koITextUtils);
        desc = textUtils.break_up_words(desc, 50);
        var textNode = document.createTextNode(desc);
        descWidget.appendChild(textNode);
    } else {
        descWidget.setAttribute("collapsed", "true");
    }

    // .items
    gItems = gArgObj.items;
    if (typeof gItems == "undefined" || gItems == null) {
        //XXX Is this the kind of error handling we want to do in onload
        //    handlers?
        msg = "Internal Error: illegal 'items' value for "
                  +"Select From List dialog: '"+gItems+"'.";
        log.error(msg);
        alert(msg);
        window.close();
    }

    itemsTree.treeBoxObject.view = gItemsTreeView;
    gItemsTreeView.setRowCount(gItems.length);

    // .selectionCondition
    if (typeof gArgObj.selectionCondition == "undefined" ||
        gArgObj.selectionCondition == null) {
        gSelectionCondition = "one-or-more";
    } else {
        gSelectionCondition = gArgObj.selectionCondition;
    }
    var selectedIndex = gArgObj.selectedIndex;
    if (selectedIndex === null || gSelectionCondition == "one") {
        switch (gSelectionCondition) {
            case "one-or-more":
                SelectAll();
                break;
            case "zero-or-more":
                SelectAll();
                break;
            case "zero-or-more-default-none":
                break;
            case "one":
                itemsTree.setAttribute("seltype", "single");
                gItemsTreeView.selection.select(selectedIndex || 0);
                document.getElementById("select-all").setAttribute("collapsed", true);
                document.getElementById("clear-all") .setAttribute("collapsed", true);
                break;
            default:
                //XXX Is this the kind of error handling we want to do in onload
                //    handlers?
                msg = "Internal Error: illegal selection condition value for "
                    +"Select From List dialog: '"+gSelectionCondition+"'.";
                log.error(msg);
                alert(msg);
                window.close();
        }
    } else {
        gItemsTreeView.selection.select(selectedIndex);
    }

    // .stringifier
    if (typeof gArgObj.stringifier != "undefined" &&
        gArgObj.stringifier != null) {
        gStringifier = gArgObj.stringifier;
    }

    // .doNotAskUI
    if (typeof gArgObj.doNotAskUI != "undefined" &&
        gArgObj.doNotAskUI != null) {
        gDoNotAskUI = gArgObj.doNotAskUI;
    }
    if (gDoNotAskUI) {
        document.getElementById("doNotAsk-checkbox")
                .removeAttribute("collapsed");
    }

    // .yesNoCancel
    var yesNoCancel = gArgObj.yesNoCancel;
    if (typeof yesNoCancel == "undefined" || yesNoCancel == null) {
        yesNoCancel = false;
    }
    var buttonNames = gArgObj.buttonNames;
    if (typeof buttonNames == "undefined" || buttonNames == null) {
        if (yesNoCancel) {
            buttonNames = ["Yes", "No", "Cancel"];
        } else {
            buttonNames = ["OK", "Cancel"];
        }
    }
    if (yesNoCancel) {
        if (gSelectionCondition.indexOf("zero-or-more") == -1) {
            msg = "Internal Error: Attempted to use yesNoCancel=true "+
                      "and selectionCondition='"+gSelectionCondition+
                      "' for a Select From List dialog. This does not make "+
                      "sense and is illegal.";
            log.error(msg);
            alert(msg);
            window.close();
        }
        acceptButton.setAttribute("label", buttonNames[0]);
        acceptButton.setAttribute("accesskey", buttonNames[0][0].toLowerCase());
        noButton.setAttribute("label", buttonNames[1]);
        noButton.setAttribute("accesskey", buttonNames[1][0].toLowerCase());
        cancelButton.setAttribute("label", buttonNames[2]);
        cancelButton.setAttribute("accesskey", buttonNames[2][0].toLowerCase());
    } else {
        acceptButton.setAttribute("label", buttonNames[0]);
        acceptButton.setAttribute("accesskey", buttonNames[0][0].toLowerCase());
        noButton.setAttribute("collapsed", "true");
        cancelButton.setAttribute("label", buttonNames[1]);
        cancelButton.setAttribute("accesskey", buttonNames[1][0].toLowerCase());
    }

}


function OnSelectionChange()
{
    var dialog = document.getElementById("dialog_selectFromList");
    var acceptButton = dialog.getButton("accept");
    var noButton = dialog.getButton("extra1");

    if (gSelectionCondition == "one-or-more") {
        if (gItemsTreeView.selection.count == 0) {
            acceptButton.setAttribute("disabled", "true");
            noButton.setAttribute("disabled", "true");
        } else if (acceptButton.hasAttribute("disabled")) {
            acceptButton.removeAttribute("disabled");
            noButton.removeAttribute("disabled");
        }
    }
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        if (gSelectionCondition == "one-or-more"
            && gItemsTreeView.selection.count == 0) {
            checkbox.setAttribute("disabled", "true");
            checkbox.setAttribute("checked", "false");
        } else {
            if (checkbox.hasAttribute("disabled"))
                checkbox.removeAttribute("disabled");
        }
    }
}

// The onclick handler on the <tree> is to allow on to double-click on one of
// the selection options to select it and close the dialog. This is only
// allowed for gSelectionCondition=="one".
function OnClick(event)
{
    if (gSelectionCondition != "one") return;

    // c.f. mozilla/mailnews/base/resources/content/threadPane.js
    var t = event.originalTarget;

    // single-click on a column
    if (t.localName == "treecol") return;

    // double-click in the tree body
    if (event.detail == 2 && t.localName == "treechildren") {
        if (Accept()) {
            window.close();
        }
    }
}


function SelectAll()
{
    gItemsTreeView.selection.selectAll();
    OnSelectionChange();
    document.getElementById("items").focus();
}


function ClearAll()
{
    gItemsTreeView.selection.clearSelection();
    OnSelectionChange();
    document.getElementById("items").focus();
}


function Accept()
{
    var acceptButton = document.getElementById("dialog_selectFromList").getButton("accept");
    gArgObj.retval = acceptButton.getAttribute("label");

    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        if (! checkbox.getAttribute("disabled")) {
            gArgObj.doNotAsk = checkbox.checked;
        } else {
            gArgObj.doNotAsk = false;
        }
    }

    // Get the list of selected items.
    var selected = new Array();
    var i, item;
    for (i = 0; i < gItems.length; ++i) {
        if (gItemsTreeView.selection.isSelected(i)) {
            item = gItems[i];
            selected.push(item);
        }
    }
    gArgObj.selected = selected;

    return true;
}


function No()
{
    var noButton = document.getElementById("dialog_selectFromList").getButton("extra1");
    gArgObj.retval = noButton.getAttribute("label");

    ClearAll(); // do this first because it might affect the checkbox state
    if (gDoNotAskUI) {
        var checkbox = document.getElementById("doNotAsk-checkbox");
        if (! checkbox.getAttribute("disabled")) {
            gArgObj.doNotAsk = checkbox.checked;
        } else {
            gArgObj.doNotAsk = false;
        }
    }

    gArgObj.selected = [];

    window.close();
    return true;
}


function Cancel()
{
    gArgObj.retval = "Cancel";
    if (gDoNotAskUI) {
        // Don't skip this dialog next time if it was cancelled this time.
        gArgObj.doNotAsk = false;
    }
    return true;
}

