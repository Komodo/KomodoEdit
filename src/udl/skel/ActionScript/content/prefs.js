/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

//---- globals

var asPrefLog = getLoggingMgr().getLogger("ActionScriptInterp");
asPrefLog.setLevel(LOG_DEBUG);

function OnPreferencePageOK(prefset)
{
    var ok = true;

    // ensure that the interpreter is valid
    var defaultInterp = prefset.getStringPref("actionScriptDefaultInterpreter");
    if (defaultInterp != "") {
        var koSysUtils = Components.classes["@activestate.com/koSysUtils;1"].
            getService(Components.interfaces.koISysUtils);
        if (! koSysUtils.IsFile(defaultInterp)) {
            dialog_alert("No ActionScript interpreter could be found at '" + defaultInterp +
                  "'. You must make another selection for the default " +
                  "ActionScript interpreter.\n");
            ok = false;
            document.getElementById("actionScriptDefaultInterpreter").focus();
        }
    }
    return ok;
}

function PrefActionScript_OnLoad()
{
    var prefExecutable;
    var prefName = 'actionScriptDefaultInterpreter';
    // If there is no pref, create it
    // Otherwise trying to save a new pref will fail, because
    // it tries to get an existing one to see if the
    // pref needs updating.
    if (!parent.hPrefWindow.prefset.hasStringPref(prefName)) {
        parent.hPrefWindow.prefset.setStringPref(prefName, "");
        prefExecutable = '';
    } else {
        prefExecutable = parent.hPrefWindow.prefset.getStringPref(prefName);
        if (prefExecutable == null) {
            prefExecutable = '';
        }
    }
    _finishSpecifyingExecutable(prefExecutable);
}

function loadActionScriptExecutable()
{
    _finishSpecifyingExecutable(filepicker_openExeFile());
}

function _finishSpecifyingExecutable(path) {
    if (path != null) {
        document.getElementById("actionScript_interpreterPath").value = path;
    }
}
