/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://places/locale/places.properties");
const DEFAULT_FILTER_NAME = _bundle.GetStringFromName("default.filterName");
var g_defaultFilterPrefs;

function prefPlacesOnLoad()  {
    try {
        parent.initPanel();
    } catch (e) {
        log.error(e);
    }
}

function OnPreferencePageInitalize(prefset) {
    try {
        g_defaultFilterPrefs =
            prefset.getPref("places").getPref("filters").getPref(DEFAULT_FILTER_NAME);
        document.getElementById("places_default_include_matches").value =
            g_defaultFilterPrefs.getStringPref("include_matches");
        document.getElementById("places_default_exclude_matches").value =
            g_defaultFilterPrefs.getStringPref("exclude_matches");
    } catch(ex) {
        alert("Places prefs: " + ex);
    }
}

function OnPreferencePageOK(prefset) {
    try {
        g_defaultFilterPrefs = prefset.getPref("places").getPref("filters").
            getPref(DEFAULT_FILTER_NAME);
        g_defaultFilterPrefs.setStringPref("include_matches",
            document.getElementById("places_default_include_matches").value);
        g_defaultFilterPrefs.setStringPref("exclude_matches",
            document.getElementById("places_default_exclude_matches").value);
    } catch(ex) {
        alert("Places prefs: " + ex);
    }
    return true;
}