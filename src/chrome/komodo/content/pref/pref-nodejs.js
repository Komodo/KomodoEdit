/* Copyright (c) 2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var log = ko.logging.getLogger("pref-nodejs");
//log.setLevel(ko.logging.LOG_INFO);

//---- globals
var prefExecutable = null;
var programmingLanguage = "Nodejs";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
//---- functions

function OnPreferencePageOK(prefset)
{
    // ensure that the default perl interpreter is valid
    return checkValidInterpreterSetting(prefset,
                                        "nodejsDefaultInterpreter",
                                        programmingLanguage);
}

function PrefNodejs_OnLoad() {
    parent.prefLog.setLevel(ko.logging.LOG_DEBUG);

    var availInterpList = document.getElementById("nodejsDefaultInterpreter");

    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.GetStringFromName("findOnPath.label"),'');

    var found = false;
    // populate the tree listing them
    if (parent.hPrefWindow.prefset.hasStringPref('nodejsDefaultInterpreter')) {
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('nodejsDefaultInterpreter');
        if (prefExecutable) {
            availInterpList.appendItem(prefExecutable, prefExecutable);
        } else {
            document.getElementById("no-avail-interps-message").removeAttribute("collapsed");
        }
    }

    parent.hPrefWindow.onpageload();
}

function loadNodejsExecutable()
{
    if (loadExecutableIntoInterpreterList("nodejsDefaultInterpreter"))
        document.getElementById("no-avail-interps-message").setAttribute("collapsed", true);
}
