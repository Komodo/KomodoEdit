/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var _findingInterps = false;
var programmingLanguage = "Python3";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
//---- functions

function OnPreferencePageOK(prefset)
{
    return checkValidInterpreterSetting(prefset,
                                        "python3DefaultInterpreter",
                                        programmingLanguage);
}

function checkValidPythonInterpreter(menulist)
{
    if (menulist.value) {
        var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Python;1"].
            getService(Components.interfaces.koIAppInfoEx);
        appInfoEx.executablePath = menulist.value;
        if (appInfoEx.version.substr(0, 2) != "3.") {
            ko.dialogs.alert("The chosen Python has version " + appInfoEx.version +
                             ", which will not work as a Python 3 interpreter.",
                             appInfoEx.executablePath, "Invalid Python 3 Interpreter")
        }
    }
}

// Populate the (tree) list of available Python interpreters on the current
// system.
function PrefPython3_PopulatePythonInterps(prefExecutable)
{
    var availInterpList = document.getElementById("python3DefaultInterpreter");
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                      getService(Components.interfaces.koIInfoService);

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.formatStringFromName("findingInterpreters.label", [programmingLanguage], 1));

    // get a list of installed Python3 interpreters
    var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
        getService(Components.interfaces.koISysUtils);
    var availInterps = new Array();
    availInterps = sysUtils.WhichAll("python3", new Object());
    // Include any that are explicitly labelled as "python" - as the specific
    // versions will be filtered next.
    availInterps = availInterps.concat(sysUtils.WhichAll("python", new Object()));
    if (infoSvc.platform == 'darwin') {
        availInterps = availInterps.concat(sysUtils.WhichAll("python3w", new Object()));
    }
    // Only include Python 3.x interpreters.
    var availPy3Interps = [];
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Python;1"].
        getService(Components.interfaces.koIAppInfoEx);
    for (var i = 0; i < availInterps.length; i++) {
        appInfoEx.executablePath = availInterps[i];
        if (appInfoEx.version.substr(0, 2) == "3.") {
            availPy3Interps.push(availInterps[i]);
        }
    }
    availInterps = availPy3Interps;

    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.GetStringFromName("findOnPath.label"),'');

    var found = false;
    // populate the tree listing them
    if (availInterps.length == 0) {
        // tell the user no interpreter was found and direct them to
        // ActiveState to get one
        document.getElementById("no-avail-interps-message").removeAttribute("collapsed");
    } else {
        for (var i = 0; i < availInterps.length; i++) {
            availInterpList.appendItem(availInterps[i],availInterps[i]);
            if (availInterps[i] == prefExecutable) found = true;
        }
    }
    if (!found && prefExecutable)
        availInterpList.appendItem(prefExecutable,prefExecutable);
    _findingInterps = false;
}


function PrefPython3_OnLoad()
{
    var prefExecutable = '';
    if (parent.hPrefWindow.prefset.hasStringPref('python3DefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('python3DefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('python3DefaultInterpreter');
    PrefPython3_PopulatePythonInterps(prefExecutable);

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("python3ExtraPaths");
    extraPaths.setCwd(cwd)
    extraPaths.init() // must happen after onpageload
    var file = getOwningFileObject();
    if (file && file.dirName) {
        extraPaths.setCwd(file.dirName);
    }
}

function loadPython3Executable()
{
    loadExecutableIntoInterpreterList("python3DefaultInterpreter");
}


