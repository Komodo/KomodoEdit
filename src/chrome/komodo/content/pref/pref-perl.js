/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var _findingInterps = false;
var prefExecutable = null;

//---- functions

function OnPreferencePageOK(prefset)
{
    var ok = true;

    // ensure that the default perl interpreter is valid
    var defaultInterp = prefset.getStringPref("perlDefaultInterpreter");
    if (defaultInterp != "") {
        var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].
            getService(Components.interfaces.koISysUtils);
        if (! koSysUtils.IsFile(defaultInterp)) {
            ko.dialogs.alert("No Perl interpreter could be found at '" + defaultInterp +
                  "'. You must make another selection for the default " +
                  "Perl interpreter.\n");
            ok = false;
            document.getElementById("perlDefaultInterpreter").focus();
        }
    }
    return ok;
}

// Populate the (tree) list of available Perl interpreters on the current
// system.
function PrefPerl_PopulatePerlInterps()
{
    var availInterpList = document.getElementById("perlDefaultInterpreter");

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem("Finding available Perl interpreters...");

    // get a list of installed Perl interpreters
    var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
        getService(Components.interfaces.koISysUtils);
    var availInterps = new Array();
    availInterps = sysUtils.WhichAll("perl", new Object());

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


function PrefPerl_OnLoad()
{
    if (parent.hPrefWindow.prefset.hasStringPref('perlDefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('perlDefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('perlDefaultInterpreter');
    else
        prefExecutable = '';
    PrefPerl_PopulatePerlInterps();

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("perlExtraPaths");
    extraPaths.init() // must happen after onpageload
    extraPaths.setCwd(cwd)
}

function loadPerlExecutable()
{
    var perlExe = ko.filepicker.openExeFile();
    if (perlExe != null) {
        var availInterpList = document.getElementById("perlDefaultInterpreter");
        availInterpList.selectedItem = availInterpList.appendItem(perlExe, perlExe);
    }
}

function loadPerlLogpath()
{
    var perlLog = ko.filepicker.getFolder();
    if (perlLog != null) {
        var textbox = document.getElementById("perl_debuggerlogpath");
        textbox.value = perlLog;
    }
}
