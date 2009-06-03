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
var programmingLanguage = "Perl";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
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
            ko.dialogs.alert(_bundle.formatStringFromName("noLangInterpreterFound.alert", [programmingLanguage, defaultInterp,programmingLanguage], 3));
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
    availInterpList.appendItem(_bundle.formatStringFromName("findingInterpreters.label", [programmingLanguage], 1));

    // get a list of installed Perl interpreters
    var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
        getService(Components.interfaces.koISysUtils);
    var availInterps = new Array();
    availInterps = sysUtils.WhichAll("perl", new Object());

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


function PrefPerl_OnLoad()
{
    if (parent.hPrefWindow.prefset.hasStringPref('perlDefaultInterpreter') &&
        parent.hPrefWindow.prefset.getStringPref('perlDefaultInterpreter'))
        prefExecutable = parent.hPrefWindow.prefset.getStringPref('perlDefaultInterpreter');
    else
        prefExecutable = '';
    PrefPerl_PopulatePerlInterps();
    var appInfoEx = Components.classes["@activestate.com/koAppInfoEx?app=Perl;1"].
            getService(Components.interfaces.koIPerlInfoEx);
    _setPerlCriticSection(appInfoEx.isPerlCriticInstalled(/*forceCheck=*/true));

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("perlExtraPaths");
    extraPaths.init(); // must happen after onpageload
    extraPaths.setCwd(cwd);
}

function loadPerlExecutable()
{
    var perlExe = ko.filepicker.openExeFile();
    if (perlExe != null) {
        var availInterpList = document.getElementById("perlDefaultInterpreter");
        availInterpList.selectedItem = availInterpList.appendItem(perlExe, perlExe);
    }
}

function onPerlDefaultInterpreterChanged() {
    var availInterpList = document.getElementById("perlDefaultInterpreter");
    var newInterpreter = availInterpList.selectedItem.value;
    // We can't use koAppInfo service, because it's still pointing at
    // the old Perl interpreter value.
    var cmd = !newInterpreter ? "perl" : newInterpreter;
    cmd += " -Mcriticism -e 1";
    var runSvc = Components.classes["@activestate.com/koRunService;1"]
               .getService(Components.interfaces.koIRunService);
    var out = {}, err = {};
    var res = runSvc.RunAndCaptureOutput(cmd, null, null, null, out, err);
    _setPerlCriticSection(res == 0);
}

function _setPerlCriticSection(havePerlCritic) {
    var perlCriticLabel = document.getElementById("perl_lintOptions_perlCriticBox_label");
    var perlCriticMenu = document.getElementById("perl_lintOption_perlCriticLevel");
    var perlCriticEnableNode = document.getElementById("perl_lintOption_perlCriticEnableNote");
    perlCriticLabel.disabled = !havePerlCritic;
    perlCriticMenu.disabled = !havePerlCritic;
    if (havePerlCritic) {
        perlCriticEnableNode.setAttribute('collapsed', true);
    } else {
        perlCriticEnableNode.removeAttribute('collapsed');
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
