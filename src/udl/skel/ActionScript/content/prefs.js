/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

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
