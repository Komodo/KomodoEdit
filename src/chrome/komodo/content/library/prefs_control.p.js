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

var gPrefs;

var gPrefHash = {};
var gPrefArray = [];
var gFastIndex = 0;
var gSortedColumn = "prefName";
var gSortFunction = null;
var gSortDirection = 1; // 1 is ascending; -1 is descending
var gConfigBundle = null;
var isOrderedPref;
var lastErrorSvc;

var view = {
    get rowCount() { return gPrefArray.length; },
    getCellText : function(k, column) {
        if (!(k in gPrefArray))
            return "";

        var value = gPrefArray[k][column.id];
        return value;
    },
    getRowProperties : function(index, prop) {},
    getCellProperties : function(index, col, prop) {},
    getColumnProperties : function(col, elt, prop) {},
    treebox : null,
    selection : null,
    isContainer : function(index) {
        var type = gPrefArray[index].type;
        switch (type) {
            case 'long':
            case 'boolean':
            case 'double':
            case 'string':
                return false;
            default:
                return true; // XXX doesn't work =(
        }},
    isContainerOpen : function(index) { return false; },
    isContainerEmpty : function(index) { return false; },
    isSorted : function() { return true; },
    canDrop : function(index, orientation) { return false; },
    drop : function(row, orientation) {},
    setTree : function(out) { this.treebox = out; },
    getParentIndex: function(rowIndex) { return -1; },
    hasNextSibling: function(rowIndex, afterIndex) { return false; },
    getLevel: function(index) { return 1; },
    getImageSrc: function(row, colID) { return ""; },
    toggleOpenState : function(index) {},
    cycleHeader: function(column, elt) {
        var index = this.selection.currentIndex;
        if (column.id == gSortedColumn)
            gSortDirection = -gSortDirection;
        if (column.id == gSortedColumn && gFastIndex == gPrefArray.length) {
            gPrefArray.reverse();
            if (index >= 0)
                index = gPrefArray.length - index - 1;
        }
        else {
            var pref = null;
            if (index >= 0)
                pref = gPrefArray[index];
            var old = document.getElementById(gSortedColumn);
            old.setAttribute("sortDirection", "");
            gPrefArray.sort(gSortFunction = gSortFunctions[column.id]);
            gSortedColumn = column.id;
            if (pref)
                index = getIndexOfPref(pref);
        }
        elt.setAttribute("sortDirection", gSortDirection > 0 ? "ascending" : "descending");
        this.treebox.invalidate();
        if (index >= 0) {
            this.selection.select(index);
            this.treebox.ensureRowIsVisible(index);
        }
        gFastIndex = gPrefArray.length;
    },
    selectionChanged : function() {},
    cycleCell: function(row, colID) {},
    isEditable: function(row, colID) {return false; },
    setCellText: function(row, colID, value) {},
    performAction: function(action) {},
    performActionOnRow: function(action, row) {},
    performActionOnCell: function(action, row, colID) {},
    isSeparator: function(index) {return false; }
};

// find the index in gPrefArray of a pref object
// either one that was looked up in gPrefHash
// or in case it was moved after sorting
function getIndexOfPref(pref)
{
    var low = -1, high = gFastIndex;
    var index = (low + high) >> 1;
    while (index > low) {
        var mid = gPrefArray[index];
        if (mid == pref)
            return index;
        if (gSortFunction(mid, pref) < 0)
            low = index;
        else
            high = index;
        index = (low + high) >> 1;
    }

    for (index = gFastIndex; index < gPrefArray.length; ++index)
        if (gPrefArray[index] == pref)
            break;
    return index;
}

function getNearestIndexOfPref(pref)
{
    var low = -1, high = gFastIndex;
    var index = (low + high) >> 1;
    while (index > low) {
        if (gSortFunction(gPrefArray[index], pref) < 0)
            low = index;
        else
            high = index;
        index = (low + high) >> 1;
    }
    return high;
}

function prefObject(prefName, prefIndex)
{
    this.prefName = prefName;
    this.prefName_lowered = prefName.toLowerCase();
}

const PREF_IS_DEFAULT_VALUE = 0;
const PREF_IS_USER_SET = 1;
const PREF_IS_LOCKED = 2;

prefObject.prototype =
{
    prefStatus: 'inherited',
    prefType: 'object',
    prefValue: ""
};

function fetchPref(prefName, prefIndex)
{
    var pref = new prefObject(prefName);

    gPrefHash[prefName] = pref;
    gPrefArray[prefIndex] = pref;
    if (! isOrderedPref && gPrefs.hasPrefHere(prefName)) {
        pref.prefStatus = 'set';
    } else {
        pref.prefStatus = 'inherited';
    }
        var type = gPrefs.getPrefType(prefName)
    switch (type) {
        case 'boolean':
        pref.prefType = 'boolean';
        // convert to a string
        pref.prefValue = gPrefs.getBooleanPref(prefName).toString();
        break;
        case 'long':
        pref.prefType = 'long';
        // convert to a string
        pref.prefValue = gPrefs.getLongPref(prefName).toString();
        break;
        case 'double':
        pref.prefType = 'double';
        // convert to a string
        pref.prefValue = gPrefs.getDoublePref(prefName).toString();
        break;
        case 'string':
        pref.prefType = 'string';
        pref.prefValue = gPrefs.getStringPref(prefName);
        break;
        default:
        pref.prefType = 'object';
        var p = gPrefs.getPref(prefName);
        pref.prefValue = '<unknown>';
        try {
            p.QueryInterface(Components.interfaces.koIPreferenceSet);
            pref.prefValue = '<preference-set: '+ p.id ? p.id : prefName +'>';
        } catch (e) {};
        try {
            p.QueryInterface(Components.interfaces.koIOrderedPreference);
            pref.prefValue = '<ordered-preference: '+ p.id ? p.id : prefName +'>';
        } catch (e) {};
        break;
    }
}

function prefsControl_OnUnload()
{
    if (! isOrderedPref) {
        gPrefs.removeObserver(gPrefListener);
    }
    document.getElementById("configTree").view = null;
    var p = gPrefs.parent;
    while (p) {
        p.removeObserver(gPrefListener);
        p = p.parent;
    }
}


function prefsControl_OnLoad() {
    //gPrefSvc = Components.classes["@activestate.com/koPrefService;1"].
    //                getService(Components.interfaces.koIPrefService);
    //gPrefs = gPrefSvc.prefs;
    gPrefs = window.arguments[0].prefs;
    document.title = window.arguments[0].title;
    if (typeof(window.arguments[0].screenX) != "undefined")
        window.screenX += window.arguments[0].screenX;
    if (typeof(window.arguments[0].screenY) != "undefined")
        window.screenY += window.arguments[0].screenY;
    lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                   getService(Components.interfaces.koILastErrorService);
    var prefs = new Array();
    var i;

    try {
        gPrefs.QueryInterface(Components.interfaces.koIPreferenceSet);
        isOrderedPref = false;
    } catch (e) {
        isOrderedPref = true;
    }
    if (! isOrderedPref) {
        gPrefs.addObserver(gPrefListener);
        // We also need to add observers to all the parents
        var p = gPrefs.parent;
        while (p) {
            p.addObserver(gPrefListener);
            p = p.parent;
        }

        prefs = gPrefs.getAllPrefIds();
        for (i = 0; i < prefs.length; ++i) {
            var prefName = prefs[i];
            fetchPref(prefName, gPrefArray.length);
        }
    } else {
        for (i = 0; i < gPrefs.length; ++i) {
            fetchPref(String(i), gPrefArray.length);
        }
        document.getElementById('prefStatus').setAttribute('collapsed', 'true');
        document.getElementById('prefName').setAttribute('label', 'Index');
    }

    var descending = document.getElementsByAttribute("sortDirection", "descending");
    if (descending.length) {
        gSortedColumn = descending[0].id;
        gSortDirection = -1;
    }
    else {
        var ascending = document.getElementsByAttribute("sortDirection", "ascending");
        if (ascending.length)
            gSortedColumn = ascending[0].id;
        else
            document.getElementById(gSortedColumn).setAttribute("sortDirection", "ascending");
    }
    gSortFunction = gSortFunctions[gSortedColumn];
    gPrefArray.sort(gSortFunction);
    gFastIndex = gPrefArray.length;

    document.getElementById("configTree").view = view;
}

function onConfigUnload()
{
}

function prefNameSortFunction(x, y)
{
    if (isOrderedPref) {
        var xn, yn;
        xn = eval(x.prefName);
        yn = eval(y.prefName);
        if (xn > yn)
            return gSortDirection;
        if (xn < yn)
            return -gSortDirection;
        return 0;
    } else {
        if (x.prefName_lowered > y.prefName_lowered)
            return gSortDirection;
        if (x.prefName_lowered < y.prefName_lowered)
            return -gSortDirection;
        return 0;
    }
}

function prefStatusSortFunction(x, y)
{
    if (x.prefStatus > y.prefStatus)
        return gSortDirection;
    if (x.prefStatus < y.prefStatus)
        return -gSortDirection;
    return 0;
}

function prefTypeSortFunction(x, y)
{
    if (x.prefType == 'object') {
        if (y.prefType == 'object') {
            return prefValueSortFunction(x,y)
        } else {
            return -gSortDirection;
        }
    }
    if (y.prefType == 'object') return gSortDirection;
    if (x.prefType > y.prefType)
        return gSortDirection;
    if (x.prefType < y.prefType)
        return -gSortDirection;
    return 0;
}

function prefValueSortFunction(x, y)
{
    if (x.prefValue > y.prefValue)
        return gSortDirection;
    if (x.prefValue < y.prefValue)
        return -gSortDirection;
    return prefNameSortFunction(x, y);
}

const gSortFunctions =
{
    prefName: prefNameSortFunction,
    prefStatus: prefStatusSortFunction,
    prefType: prefTypeSortFunction,
    prefValue: prefValueSortFunction
};

function updateContextMenu(popup) {
    if (view.selection.currentIndex < 0)
        return false;
    var pref = gPrefArray[view.selection.currentIndex];
    var reset = popup.lastChild;
    reset.setAttribute("disabled", pref.prefStatus == 'inherited');
    return true;
}

function copyName()
{
    gClipboardHelper.copyString(gPrefArray[view.selection.currentIndex].prefName);
}

function copyValue()
{
    gClipboardHelper.copyString(gPrefArray[view.selection.currentIndex].prefValue);
}

function ModifySelected()
{
    ModifyPref(gPrefArray[view.selection.currentIndex]);
}

function UnsetSelected()
{
  var entry = gPrefArray[view.selection.currentIndex];
  gPrefs.deletePref(entry.prefName);
}

function NewPref(type)
{
  var result = { value: "" };
  var dummy = { value: 0 };
  // XXX get these from a string bundle
  if (gPromptService.prompt(window,
                            gConfigBundle.getFormattedString("new_title", [type]),
                            gConfigBundle.getString("new_prompt"),
                            result,
                            null,
                            dummy)) {
    var pref;
    if (result.value in gPrefHash)
      pref = gPrefHash[result.value];
    else
      pref = { prefName: result.value, prefStatus: PREF_IS_DEFAULT_VALUE, prefType: type, prefValue: "" };
    if (ModifyPref(pref))
      setTimeout(gotoPref, 0, result.value);
  }
}

function gotoPref(prefName) {
  var index = getIndexOfPref(gPrefHash[prefName]);
  view.selection.select(index);
  view.treebox.ensureRowIsVisible(index);
}


function ModifyPref(entry)
{
    if (entry.prefType != 'object') {
        var value = ko.dialogs.prompt(
                "Enter a new "+entry.prefType+" value for '"+entry.prefName+"'.",
                null, // label
                entry.prefValue,  // default value
                null, // title
                entry.prefName+"_mru"); // mru name
        if (value == null) {
            return false;
        }
        switch (entry.prefType) {
            case 'boolean':
                gPrefs.setBooleanPref(entry.prefName, eval(value));
                break;
            case 'long':
                try {
                    gPrefs.setLongPref(entry.prefName, eval(value));
                } catch (e) {
                    alert("There was an error setting the pref: " + lastErrorSvc.getLastErrorMessage());
                    return false;
                }
                break;
            case 'double':
                gPrefs.setDoublePref(entry.prefName, parseFloat(value));
                break;
            case 'string':
                gPrefs.setStringPref(entry.prefName, value);
                break;
        }
    } else {
        var pref = gPrefs.getPref(entry.prefName);
        var obj = new Object();
        obj.prefs = pref;
        if (! isOrderedPref) {
            obj.title = document.title + '.' + pref.id;
        } else {
            obj.title = document.title + '[' + entry.prefName + ']';
        }
        obj.screenX = window.screenX + 20;
        obj.screenY = window.screenY + 20;
        window.openDialog('chrome://komodo/content/library/prefs_control.xul',
                        obj.title,
                        'titlebar,chrome,resizable,close',
                        obj);
    }
    return true;
}

var gPrefListener =
{
    observe: function(subject, topic, prefName)
    {
        var index = gPrefArray.length;
        if (prefName in gPrefHash) {
            index = getIndexOfPref(gPrefHash[prefName]);
            fetchPref(prefName, index);
            view.treebox.invalidateRow(index);
            if (gSortedColumn == "prefStatus" || gSortedColumn == "prefValue")
                gFastIndex = 1; // TODO: reinsert and invalidate range
        } else {
            fetchPref(prefName, index);
            if (index == gFastIndex) {
                // Keep the array sorted by reinserting the pref object
                var pref = gPrefArray.pop();
                index = getNearestIndexOfPref(pref);
                gPrefArray.splice(index, 0, pref);
                gFastIndex = gPrefArray.length;
            }
            view.treebox.beginUpdateBatch();
            view.treebox.rowCountChanged(index, 1);
            view.treebox.invalidate();
            view.treebox.beginUpdateBatch();
        }
    }
};
