/* Copyright (c) 2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var log = ko.logging.getLogger("pref-nodejs");
//log.setLevel(ko.logging.LOG_INFO);

//---- globals
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
    PrefNodejs_PopulateInterps();
    parent.hPrefWindow.onpageload();
}

function PrefNodejs_PopulateInterps()
{
    var availInterpList = document.getElementById("nodejsDefaultInterpreter");
    // remove any existing items and add a "finding..." one
    availInterpList.removeAllItems();

    // get a list of installed Node interpreters
    var nodeAppInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=NodeJS;1"].
                            createInstance(Components.interfaces.koIAppInfoEx);
    var numFound = new Object();
    var availInterps = nodeAppInfoEx.FindExecutables(numFound);

    availInterpList.appendItem(_bundle.GetStringFromName("findOnPath.label"),'');
    var found = false;
    // populate the tree listing them
    if (availInterps.length == 0) {
        // tell the user no interpreter was found and direct them to
        // ActiveState to get one
        document.getElementById("no-avail-interps-message").removeAttribute("collapsed");
    } else {
        availInterpList.selectedIndex = 0;
        for (var i=0; i < availInterps.length; i++) {
            availInterpList.appendItem(availInterps[i], availInterps[i]);
        }
        // First one on the list is either the preferenced interpreter or the
        // first one found on the path.
        availInterpList.selectedIndex = 1;
    }
}

function loadNodejsExecutable()
{
    if (loadExecutableIntoInterpreterList("nodejsDefaultInterpreter"))
        document.getElementById("no-avail-interps-message").setAttribute("collapsed", true);
}
