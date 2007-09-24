/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var _findingInterps = false;
var availInterps = [];
//---- functions
var phpAppInfoEx = null;
var prefExecutable = null;

/* Functions Related to pref-phpini.xul */
function PrefPhp_OnLoad()  {
    phpAppInfoEx = Components.classes["@activestate.com/koPHPInfoInstance;1"].
            createInstance(Components.interfaces.koIPHPInfoEx);

    if (parent.hPrefWindow.prefset.hasStringPref('phpDefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('phpDefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('phpDefaultInterpreter');
    else
        prefExecutable = '';
    PrefPhp_PopulatePHPInterps();

    parent.hPrefWindow.onpageload();
}

function OnPreferencePageLoading() {
    var extraPaths = document.getElementById("phpExtraPaths");
    extraPaths.init() // must happen after onpageload
}

var _lastIniPath = null;
var _lastInterpreterPath = null;

function OnPreferencePageOK(prefset)
{
    var ok = true;

    // ensure that the default PHP interpreter is valid
    var defaultInterp = prefset.getStringPref("phpDefaultInterpreter");
    if (defaultInterp != "") {
        var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].
            getService(Components.interfaces.koISysUtils);
        if (! koSysUtils.IsFile(defaultInterp)) {
            alert("No PHP interpreter could be found at '" + defaultInterp +
                  "'. You must make another selection for the default " +
                  "PHP interpreter.\n");
            ok = false;
            document.getElementById("phpDefaultInterpreter").focus();
        }
    }

    return ok;
}

// Populate the (tree) list of available PHP interpreters on the current
// system.
function PrefPhp_PopulatePHPInterps()
{
    var availInterpList = document.getElementById("phpDefaultInterpreter");

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem("Finding available PHP interpreters...");

    // get a list of installed PHP interpreters
    var numFound = new Object();
    availInterps = phpAppInfoEx.FindInstallationExecutables(numFound);

    availInterpList.removeAllItems();
    availInterpList.appendItem("Find on Path",'');

    var found = false;
    var item = null;
    // populate the tree listing them
    if (availInterps.length == 0) {
        // tell the user no interpreter was found and direct them to
        // ActiveState to get one
        document.getElementById("no-avail-interps-message").removeAttribute("collapsed");
    } else {
        for (var i = 0; i < availInterps.length; i++) {
            item = availInterpList.appendItem(availInterps[i],availInterps[i]);
            if (availInterps[i] == prefExecutable) {
                availInterpList.selectedItem = item;
                found = true;
            }
        }
    }
    if (!found && prefExecutable) {
        availInterpList.selectedItem =
            availInterpList.appendItem(prefExecutable,prefExecutable);
    }
    _findingInterps = false;
}

/* Functions Related to pref-phpini.xul */

function PrefPhpIni_OnLoad()  {
    parent.initPanel();
}

function PrefPhp_SelectIni() {
}

function loadIniFile() {
    var current = document.getElementById("phpConfigFile").value;
    var path = ko.filepicker.openFile(null, current, null, "INI", ["INI", "All"]);
    if (path != null) {
        document.getElementById("phpConfigFile").value = path;
    }
}

function loadPHPExecutable() {
    var path = ko.filepicker.openExeFile();
    if (path != null) {
        var availInterpList = document.getElementById("phpDefaultInterpreter");
        availInterpList.selectedItem = availInterpList.appendItem(path,path);
    }
}

