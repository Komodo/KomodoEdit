/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var programmingLanguage = "Python3";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
//---- functions

// Populate the (tree) list of available Python interpreters on the current
// system.
function PrefPython3_PopulatePythonInterps(prefExecutable)
{
    // Get a list of installed Python3 interpreters.
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=" + programmingLanguage + ";1"].
        getService(Components.interfaces.koIAppInfoEx);
    var availInterps = appInfoEx.FindExecutables({});

    // Clear menu list and add "find on path".
    var availInterpList = document.getElementById("python3DefaultInterpreter");
    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.GetStringFromName("findOnPath.label"),'');

    var found = false;
    // populate the tree listing them
    if (availInterps.length == 0 && !prefExecutable) {
        // Tell the user no interpreter was found and direct them to
        // ActiveState to get one
        document.getElementById("no-avail-interps-message").removeAttribute("collapsed");
    } else {
        for (var i = 0; i < availInterps.length; i++) {
            availInterpList.appendItem(availInterps[i],availInterps[i]);
            if (availInterps[i] == prefExecutable) {
                found = true;
                availInterpList.selectedIndex = i+1;
            }
        }
    }
    if (!found && prefExecutable) {
        availInterpList.appendItem(prefExecutable, prefExecutable);
    }
}

function OnPreferencePageSaved(prefset)
{
    var prefName = programmingLanguage.toLowerCase()+"ExtraPaths";
     var extraPaths = document.getElementById(prefName);
     var paths = extraPaths.getData();
     if(paths == "")
     {
        prefset.deletePref(prefName);
        // Force the prefs to be written to file.
        Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService).saveState();
     }
}

function checkValidPythonInterpreter(exe)
{
    if (exe) {
        var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=" + programmingLanguage + ";1"].
            getService(Components.interfaces.koIAppInfoEx);
        var isValid = false;
        var version = "<unknown>";
        try {
            isValid = appInfoEx.isSupportedBinary(exe);
            if (!isValid)
                version = appInfoEx.getVersionForBinary(exe);
        } catch(ex) {
        }
        if (!isValid) {
            var resp = require("ko/dialogs").confirm("The chosen Python has version " + version +
                             ", which should not work as a Python 3 interpreter.  Do you still want to use it?",
                             {"title":"Invalid Python Interpreter", window:require("ko/windows").getMostRecent()});
            if(! resp)
                document.getElementById("pythonDefaultInterpreter").selectedIndex = 0;
            return false;
        }
        return true;
    }
    return false;
}

function loadPython3Executable()
{
    if (loadExecutableIntoInterpreterList("python3DefaultInterpreter")) {
        var exe = document.getElementById("python3DefaultInterpreter").value;
        checkValidPythonInterpreter(exe);
    }
}

function PrefPython3_OnLoad()
{
    var prefExecutable = parent.hPrefWindow.prefset.getString('python3DefaultInterpreter', '');
    PrefPython3_PopulatePythonInterps(prefExecutable);
    parent.hPrefWindow.onpageload();

    var origWindow = ko.windowManager.getMainWindow();
    var extraPaths = document.getElementById("python3ExtraPaths");
    var cwd = origWindow.ko.window.getCwd();
    extraPaths.setCwd(cwd);
    extraPaths.init(); // must happen after onpageload
    var file = getOwningFileObject();
    if (file && file.dirName) {
        extraPaths.setCwd(file.dirName);
    }
}


