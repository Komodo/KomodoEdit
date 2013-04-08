/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo-places/locale/places.properties");
const DEFAULT_FILTER_NAME = _bundle.GetStringFromName("default.filterName");
var g_defaultFilterPrefs;
var log = ko.logging.getLogger("pref_places_js");

function prefPlacesOnLoad()  {
    try {
        parent.initPanel();
    } catch (e) {
        log.error(e);
    }
}

function OnPreferencePageInitalize(prefset) {
    try {
        var placePrefs = prefset.getPref("places");
        g_defaultFilterPrefs =
            placePrefs.getPref("filters").getPref(DEFAULT_FILTER_NAME);
        document.getElementById("places_default_include_matches").value =
            g_defaultFilterPrefs.getStringPref("include_matches");
        document.getElementById("places_default_exclude_matches").value =
            g_defaultFilterPrefs.getStringPref("exclude_matches");
        document.getElementById("pref_places_dblClickRebases").checked =
            placePrefs.getBoolean('dblClickRebases', false);
        document.getElementById("pref_places_showProjectPath").checked =
            placePrefs.getBoolean('showProjectPath', false);
        document.getElementById("pref_places_show_fullPath_tooltip").checked =
            placePrefs.getBoolean('show_fullPath_tooltip', true);
        document.getElementById("pref_places_showProjectPathExtension").checked =
            placePrefs.getBoolean('showProjectPathExtension', false);
        //// This pref has doNotAsk dependents, so it has to be a global pref.
        //document.getElementById("places.allowDragDropItemsToFolders").checked =
        //    prefset.getBoolean("placesAllowDragDropItemsToFolders", false);
    } catch(ex) {
        alert("Places prefs: " + ex);
    }
}

function OnPreferencePageOK(prefset) {
    try {
        var placePrefs = prefset.getPref("places");
        placePrefs.setBooleanPref('dblClickRebases',
                                  document.getElementById("pref_places_dblClickRebases").checked);
        placePrefs.setBooleanPref('showProjectPath',
                                  document.getElementById("pref_places_showProjectPath").checked);
        placePrefs.setBooleanPref('show_fullPath_tooltip',
                                  document.getElementById("pref_places_show_fullPath_tooltip").checked);
        placePrefs.setBooleanPref('showProjectPathExtension',
                                  document.getElementById("pref_places_showProjectPathExtension").checked);
        //prefset.setBooleanPref("placesAllowDragDropItemsToFolders",
        // document.getElementById("places.allowDragDropItemsToFolders").checked);
        g_defaultFilterPrefs = placePrefs.getPref("filters").
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
