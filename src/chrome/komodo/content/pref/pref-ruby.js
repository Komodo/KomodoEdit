/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals
var _findingInterps = false;
var prefExecutable = null;
var appInfoEx = null;
//---- functions

function OnPreferencePageOK(prefset)
{
    var ok = true;

    // ensure that the default ruby interpreter is valid
    var defaultInterp = prefset.getStringPref("rubyDefaultInterpreter");
    if (defaultInterp != "") {
        var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].
            getService(Components.interfaces.koISysUtils);
        if (! koSysUtils.IsFile(defaultInterp)) {
            alert("No Ruby interpreter could be found at '" +
                  defaultInterp + "'. You must make another selection " +
                  "for the default Ruby interpreter.\n");
            ok = false;
            document.getElementById("rubyDefaultInterpreter").focus();
        }
    }

    return ok;
}

// Populate the (tree) list of available Ruby interpreters on the current
// system.
function PrefRuby_PopulateRubyInterps()
{
    var availInterpList = document.getElementById("rubyDefaultInterpreter");

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem("Finding available Ruby interpreters...");

    // get a list of installed Ruby interpreters
    var numFound = new Object();
    var availInterps = appInfoEx.FindInstallationExecutables(numFound);
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
    if (!found && prefExecutable) {
        availInterpList.appendItem(prefExecutable,prefExecutable);
        appInfoEx.executablePath = prefExecutable;
    }
    PrefRuby_checkVersion();
    _findingInterps = false;
}

function PrefRuby_checkVersion()
{
    var availInterpList = document.getElementById('rubyDefaultInterpreter');
    var interpreter = availInterpList.value;
    var numFound = new Object();
    var availInterps = appInfoEx.FindInstallationExecutables(numFound);
    if (availInterpList.selectedItem && typeof(availInterpList.selectedItem.value) != 'undefined') {
        interpreter = availInterpList.selectedItem.value;
    }
    if (!interpreter && availInterps.length > 1) {
        interpreter = availInterps[1];
    }
    appInfoEx.executablePath = interpreter;
    //dump("check version interpreter "+interpreter+" ver "+appInfoEx.version+" valid? "+appInfoEx.valid_version+"\n");
    if (!appInfoEx.valid_version) {
        document.getElementById("invalid-version-message").removeAttribute("collapsed");
    } else {
        document.getElementById("invalid-version-message").setAttribute("collapsed", "true");
    }
}

function PrefRuby_OnLoad()
{
    appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Ruby;1"].
            createInstance(Components.interfaces.koIRubyInfoEx);
    if (parent.hPrefWindow.prefset.hasStringPref('rubyDefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('rubyDefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('rubyDefaultInterpreter');
    else
        prefExecutable = '';
    PrefRuby_PopulateRubyInterps();

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("rubyExtraPaths");
    extraPaths.setCwd(cwd)
    extraPaths.init() // must happen after onpageload
}

function loadRubyExecutable()
{
    var rubyExe = ko.filepicker.openExeFile();
    if (rubyExe != null) {
        var availInterpList = document.getElementById("rubyDefaultInterpreter");
        availInterpList.selectedItem = availInterpList.appendItem(rubyExe, rubyExe);
        PrefRuby_checkVersion();
    }
}

function loadRubyLogpath()
{
    var rubyLog = ko.filepicker.getFolder();
    if (rubyLog != null) {
        var textbox = document.getElementById("ruby_debuggerlogpath");
        textbox.value = rubyLog;
    }
}


