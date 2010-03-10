/* Copyright (c) 2000-2010 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var _findingInterps = false;
var prefExecutable = null;
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

// Populate the (tree) list of available Python interpreters on the current
// system.
function PrefPython3_PopulatePythonInterps()
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
    if (infoSvc.platform == 'darwin') {
        availInterps = availInterps.concat(sysUtils.WhichAll("python3w", new Object()));
    }

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
    if (parent.hPrefWindow.prefset.hasStringPref('python3DefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('python3DefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('python3DefaultInterpreter');
    else
        prefExecutable = '';
    PrefPython3_PopulatePythonInterps();

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("python3ExtraPaths");
    extraPaths.setCwd(cwd)
    extraPaths.init() // must happen after onpageload
}

function loadPython3Executable()
{
    loadExecutableIntoInterpreterList("python3DefaultInterpreter");
}


