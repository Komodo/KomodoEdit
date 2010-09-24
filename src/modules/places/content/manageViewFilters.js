
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

var filterPrefs, globalPrefs, placePrefs;
var filterPrefValues = {};
var widgets = {};
var currentFilterName;
var prefsToDelete = [];
var g_ResultObj;

var log = ko.logging.getLogger("manageViewFilters");
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://places/locale/places.properties");
    
function onLoad() {
    try { wrapOnLoad(); } catch(ex) { dump(ex + "\n"); }
}
function wrapOnLoad() {
    // dump("** onLoad...\n");
    g_ResultObj = window.arguments[0];
    widgets.configNameMenu = document.getElementById("filter-configuration");
    widgets.configNameMenu.removeAllItems();
    widgets.exclude_matches = document.getElementById("exclude_matches");
    widgets.include_matches = document.getElementById("include_matches");
    widgets.deleteButton = document.getElementById("deleteButton");
        
    globalPrefs = (Components.classes["@activestate.com/koPrefService;1"].
                   getService(Components.interfaces.koIPrefService).prefs);
    placePrefs = globalPrefs.getPref("places");
    filterPrefs = placePrefs.getPref("filters");
    var obj = {};
    filterPrefs.getPrefIds(obj, {});
    var defaultName = _bundle.GetStringFromName("default.filterName");
    var prefNames = obj.value;
    prefNames.map(function(prefName) {
        var filter = filterPrefs.getPref(prefName);
        filterPrefValues[prefName] = {
            exclude_matches: filter.getStringPref("exclude_matches"),
            include_matches: filter.getStringPref("include_matches"),
            readonly:     filter.getBooleanPref("readonly"),
            dirty:            false,
            isNew:            false,
            __EOF_:           null // allow comma on last real item.
        };
        if (filter.hasPref("builtin")
            && filter.getBooleanPref("builtin")
            && prefName == _bundle.GetStringFromName("currentProject.filterName")
            && !opener.ko.projects.manager.currentProject) {
            // Don't add the currentProject filter.
            delete filterPrefValues[prefName];
        } else {
            widgets.configNameMenu.appendItem(prefName, prefName);
        }
    });
    currentFilterName = (g_ResultObj.currentFilterName
                         || widgets.configNameMenu.childNodes[0].childNodes[0].label);
    var currentFilter = filterPrefValues[currentFilterName];
    setup_widgets(currentFilter);
    var currentViewName = g_ResultObj.currentFilterName;
    var elts = widgets.configNameMenu.
        getElementsByAttribute("value", currentViewName);
    if (elts.length == 1) {
        widgets.configNameMenu.value = currentViewName;
    } else {
        widgets.configNameMenu.selectedIndex = 0;
    }
    doChangeFilter(widgets.configNameMenu);
}

function setup_widgets(filter) {
    widgets.exclude_matches.value = filter.exclude_matches;
    widgets.include_matches.value = filter.include_matches;
    var status = filter.readonly;
    widgets.deleteButton.disabled = status;
    if (status) {
        widgets.exclude_matches.setAttribute("readonly", status);
        widgets.include_matches.setAttribute("readonly", status);
    } else {
        widgets.exclude_matches.removeAttribute("readonly");
        widgets.include_matches.removeAttribute("readonly");
    }
}

function doChangeFilter(target) {
    try { wrap_doChangeFilter(target) } catch(ex) { dump(ex + "\n")}
}

function wrap_doChangeFilter(target) {
    var newFilterName = target.value;
    if (newFilterName == currentFilterName) {
        //dump("no change\n");
        return;
    } else if (!(newFilterName in filterPrefValues)) {
        ko.dialogs.alert("Internal error: Can't find filter '" + newFilterName + "'");
        return;
    }
    var oldFilter = grabCurrentWidgetValues(currentFilterName);
    if (oldFilter.dirty) {
        var prompt = _bundle.formatStringFromName('saveChangesToChangedFilters.format',
                                                  [currentFilterName], 1);
        var res = opener.ko.dialogs.yesNoCancel(prompt, "Yes");
        if (res == "Cancel") {
            return;
        } else if (res == "Yes") {
            prefSet = filterPrefs.getPref(currentFilterName);
            prefSet.setStringPref("exclude_matches", oldFilter.exclude_matches);
            prefSet.setStringPref("include_matches", oldFilter.include_matches);
            prefSet.setLongPref("version", g_ResultObj.version);
        }
    }
    var i = 0;
    var newFilter = filterPrefValues[currentFilterName = newFilterName];
    setup_widgets(newFilter);
    for (var name in filterPrefValues) {
        if (name == newFilterName) {
            widgets.configNameMenu.selectedIndex = i;
            break;
        }
        i++;
    }
    //dump("Leaving doChangeFilter\n");
}

function doSaveNewFilter() {
    try { wrap_doSaveNewFilter(); } catch(ex) { dump(ex+ "\n")}
}
function wrap_doSaveNewFilter() {
    var newName;
    var msg = _bundle.formatStringFromName('enterNewFilterName.format',
                                           [currentFilterName], 1);
    while (true) {
        newName = ko.dialogs.prompt(msg, "Filter Name", "", "Filter Name");
        if (!newName) {
            return;
        } else if (newName in filterPrefValues || filterPrefs.hasPref(newName)) {
            msg = _bundle.formatStringFromName('filterNameExists.format',
                                                   [newName], 1);
        } else {
            break;
        }
    }
    var oldFilter = grabCurrentWidgetValues(currentFilterName);
    var newFilter = {
        exclude_matches: oldFilter.exclude_matches,
        include_matches: oldFilter.include_matches,
        readonly:         false,
        dirty:            true,
        isNew:            true,
        __EOF_:           null // allow comma on last real item.
    };
    currentFilterName = newName;
    filterPrefValues[currentFilterName] = newFilter;
    setup_widgets(newFilter);
    var newMenuItem = widgets.configNameMenu.appendItem(currentFilterName, currentFilterName)
    widgets.configNameMenu.selectedItem = newMenuItem;
}

function doDeleteFilter() {
    try { wrap_doDeleteFilter(); } catch(ex) { dump(ex+ "\n")}
}
function wrap_doDeleteFilter() {
    // Move up one, unless it's the first, and then move down one.
    prefsToDelete.push(currentFilterName);
    filterPrefs.deletePref(currentFilterName);
    delete filterPrefValues[currentFilterName];
    var index = widgets.configNameMenu.selectedIndex;
    widgets.configNameMenu.removeItemAt(index);
    if (index >= widgets.configNameMenu.itemCount) {
        index = widgets.configNameMenu.itemCount - 1;
    }
    widgets.configNameMenu.selectedIndex = index;
    currentFilterName = widgets.configNameMenu.value;
    setup_widgets(filterPrefValues[currentFilterName]);
}

function grabCurrentWidgetValues(filterName) {
    var filter = filterPrefValues[filterName];
    var items = {
        exclude_matches: null,
        include_matches: null };
    for (var prefName in items) {
        //dump("grabCurrentWidgetValues: prefName(1): [" + prefName + "]\n");
        filter[prefName] = widgets[prefName].value;
    }
    if (!filter.readonly && !filter.isNew) {
        // Did it change?
        var oldPref = filterPrefs.getPref(filterName);
        for (var prefName in items) {
            //dump("grabCurrentWidgetValues: prefName(2): [" + prefName + "]\n");
            if (widgets[prefName].value != oldPref.getStringPref(prefName)) {
                //dump("val " + prefName + " changed\n");
                filter.dirty = true;
            }
        }
    }
    return filter;
}

function OK() {
    //dump("OK...\n");
    try {
        wrap_OK();
    } catch(ex) {
        dump(ex + "\n");
    }
}
function wrap_OK() {
    var madeChange = false;
    var currentFilter = grabCurrentWidgetValues(currentFilterName);
    var prefSet = null;
    var isNew = false;
    if (currentFilter.dirty) {
        if (!currentFilter.isNew) {
            try {
                prefSet = filterPrefs.getPref(currentFilterName);
            } catch(ex) {
                dump(ex + "\n");
                log.exception(ex);
            }
        }
        if (!prefSet) {
            var prefSet = Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
            isNew = true;
        }
        prefSet.setStringPref("exclude_matches", currentFilter.exclude_matches);
        prefSet.setStringPref("include_matches", currentFilter.include_matches);
        prefSet.setBooleanPref("readonly", false);
        prefSet.setLongPref("version", g_ResultObj.version);
        if (isNew) {
            filterPrefs.setPref(currentFilterName, prefSet);
        }
        madeChange = true;
    }
    prefsToDelete.map(function(filterName) {
        filterPrefs.deletePref(filterName);
    });
    //if (madeChange) {
    //    placePrefs.setPref("filters", filterPrefs);
    //}
    if (!madeChange && g_ResultObj.currentFilterName != currentFilterName) {
        madeChange = true;
    }
    if (madeChange) {
        g_ResultObj.needsChange = madeChange;
        g_ResultObj.currentFilterName = currentFilterName;
    }
    return true;
}

function Cancel() {
    // Nothing to do
    return true;
}
