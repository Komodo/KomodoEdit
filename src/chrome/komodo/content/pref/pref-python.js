/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var _findingInterps = false;
var prefExecutable = null;

//---- functions

function OnPreferencePageOK(prefset)
{
    var ok = true;

    // ensure that the default python interpreter is valid
    var defaultInterp = prefset.getStringPref("pythonDefaultInterpreter");
    if (defaultInterp != "") {
        var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].
            getService(Components.interfaces.koISysUtils);
        if (! koSysUtils.IsFile(defaultInterp)) {
            alert("No Python interpreter could be found at '" +
                  defaultInterp + "'. You must make another selection " +
                  "for the default Python interpreter.\n");
            ok = false;
            document.getElementById("pythonDefaultInterpreter").focus();
        }
    }

    return ok;
}

// Populate the (tree) list of available Python interpreters on the current
// system.
function PrefPython_PopulatePythonInterps()
{
    var availInterpList = document.getElementById("pythonDefaultInterpreter");
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                      getService(Components.interfaces.koIInfoService);

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem("Finding available Python interpreters...");

    // get a list of installed Python interpreters
    var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
        getService(Components.interfaces.koISysUtils);
    var availInterps = new Array();
    availInterps = sysUtils.WhichAll("python", new Object());
    if (infoSvc.platform == 'darwin') {
        availInterps = availInterps.concat(sysUtils.WhichAll("pythonw", new Object()));
    }

    availInterpList.removeAllItems();
    availInterpList.appendItem("Find on Path",'');

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


function PrefPython_OnLoad()
{
    if (parent.hPrefWindow.prefset.hasStringPref('pythonDefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('pythonDefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('pythonDefaultInterpreter');
    else
        prefExecutable = '';
    PrefPython_PopulatePythonInterps();

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("pythonExtraPaths");
    extraPaths.setCwd(cwd)
    extraPaths.init() // must happen after onpageload
}

function loadPythonExecutable()
{
    var pythonExe = ko.filepicker.openExeFile();
    if (pythonExe != null) {
        var availInterpList = document.getElementById("pythonDefaultInterpreter");
        availInterpList.selectedItem = availInterpList.appendItem(pythonExe, pythonExe);
    }
}


