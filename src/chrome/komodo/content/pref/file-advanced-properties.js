/* Copyright (c) 2000-2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var log = ko.logging.getLogger("pref.file-advanced-properties");
var dialog = {};
var local_prefset = {};
var global_codeintel_enabled;

function OnPreferencePageLoading(prefset) {
    local_prefset = prefset;
    dialog.codeintel_enabled = window.document.getElementById("codeintel_enabled");
    dialog.colorizing_enabled = window.document.getElementById("colorizing_enabled");

    // Set up the values for the codeintel and linting settings,
    // and decide which make sense to show.

    // According to prefs.p.xml, pref("codeintel_enabled") shouldn't be
    // used on a per-file basis.  Not sure of consequences of doing this.

    // I also haven't found a setting for a language that indicates
    // whether a particlar language supports codeintel  Most likely
    // because of the fire-and-forget way codeintel works.

    global_codeintel_enabled = Components.classes["@activestate.com/koPrefService;1"]
        .getService(Components.interfaces.koIPrefService)
        .prefs.getBooleanPref("codeintel_enabled");
    update_state();
}

function update_state() {
    if (!global_codeintel_enabled || !dialog.colorizing_enabled.checked) {
        dialog.codeintel_enabled.checked = false;
        dialog.codeintel_enabled.disabled = true;
    } else {
        dialog.codeintel_enabled.checked = local_prefset.getBooleanPref("codeintel_enabled");
        dialog.codeintel_enabled.disabled = false;
    }
}
