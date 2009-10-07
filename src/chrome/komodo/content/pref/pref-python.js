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
var _findingInterps = false;
var prefExecutable = null;
var programmingLanguage = "Python";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
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
            alert(_bundle.formatStringFromName("noLangInterpreterFound.alert", [programmingLanguage, defaultInterp,programmingLanguage], 3));
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
    availInterpList.appendItem(_bundle.formatStringFromName("findingInterpreters.label", [programmingLanguage], 1));

    // get a list of installed Python interpreters
    var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
        getService(Components.interfaces.koISysUtils);
    var availInterps = new Array();
    availInterps = sysUtils.WhichAll("python", new Object());
    if (infoSvc.platform == 'darwin') {
        availInterps = availInterps.concat(sysUtils.WhichAll("pythonw", new Object()));
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
    loadExecutableIntoInterpreterList("pythonDefaultInterpreter");
}


