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
var programmingLanguage = "Python";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
//---- functions

// Populate the (tree) list of available Python interpreters on the current
// system.
function PrefPython_PopulatePythonInterps(prefExecutable)
{
    // Get a list of installed Python3 interpreters.
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=" + programmingLanguage + ";1"].
        getService(Components.interfaces.koIAppInfoEx);
    var availInterps = appInfoEx.FindExecutables({});

    // Clear menu list and add "find on path".
    var availInterpList = document.getElementById("pythonDefaultInterpreter");
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
            ko.dialogs.alert("The chosen Python has version " + version +
                             ", which will not work as a Python interpreter.",
                             exe, "Invalid Python Interpreter")
            return false;
        }
        return true;
    }
    return false;
}

function loadPythonExecutable()
{
    if (loadExecutableIntoInterpreterList("pythonDefaultInterpreter")) {
        var exe = document.getElementById("pythonDefaultInterpreter").value;
        checkValidPythonInterpreter(exe);
    }
}

function PrefPython_OnLoad()
{
    var prefExecutable = parent.hPrefWindow.prefset.getString('pythonDefaultInterpreter', '');
    PrefPython_PopulatePythonInterps(prefExecutable);
    parent.hPrefWindow.onpageload();

    var origWindow = ko.windowManager.getMainWindow();
    var extraPaths = document.getElementById("pythonExtraPaths");
    var cwd = origWindow.ko.window.getCwd();
    extraPaths.setCwd(cwd);
    extraPaths.init(); // must happen after onpageload
    var file = getOwningFileObject();
    if (file && file.dirName) {
        extraPaths.setCwd(file.dirName);
    }
}

