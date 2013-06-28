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
var appInfoEx = null;
var programmingLanguage = "Ruby";
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
//---- functions

function OnPreferencePageOK(prefset)
{
    return checkValidInterpreterSetting(prefset,
                                        "rubyDefaultInterpreter",
                                        programmingLanguage);
}

// Populate the (tree) list of available Ruby interpreters on the current
// system.
function PrefRuby_PopulateRubyInterps()
{
    var availInterpList = document.getElementById("rubyDefaultInterpreter");

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.formatStringFromName("findingInterpreters.label", [programmingLanguage], 1));

    // get a list of installed Ruby interpreters
    var numFound = new Object();
    var availInterps = appInfoEx.FindExecutables(numFound);
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
    if (!found && prefExecutable) {
        availInterpList.appendItem(prefExecutable,prefExecutable);
        appInfoEx.executablePath = prefExecutable;
    }
    PrefRuby_checkVersion();
    document.getElementById("no-avail-interps-message").setAttribute("collapsed", "true");
    _findingInterps = false;
}

function PrefRuby_checkVersion()
{
    var availInterpList = document.getElementById('rubyDefaultInterpreter');
    var interpreter = availInterpList.value;
    var numFound = new Object();
    var availInterps = appInfoEx.FindExecutables(numFound);
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
            createInstance(Components.interfaces.koIAppInfoEx);
    prefExecutable = parent.hPrefWindow.prefset.getString('rubyDefaultInterpreter', '');
    PrefRuby_PopulateRubyInterps();

    var origWindow = ko.windowManager.getMainWindow();
    var cwd = origWindow.ko.window.getCwd();
    parent.hPrefWindow.onpageload();
    var extraPaths = document.getElementById("rubyExtraPaths");
    extraPaths.setCwd(cwd)
    extraPaths.init() // must happen after onpageload
    var file = getOwningFileObject();
    if (file && file.dirName) {
        extraPaths.setCwd(file.dirName);
    }
}

function loadRubyExecutable()
{
    if (loadExecutableIntoInterpreterList("rubyDefaultInterpreter")) {
        PrefRuby_checkVersion();
    }
}

function loadRubyLogpath()
{
    var prefName = "rubyDebug.defaultDir";
    var textbox = document.getElementById("ruby_debuggerlogpath");
    var defaultDir = ko.filepicker.getExistingDirFromPathOrPref(textbox.value, prefName);
    var rubyLog = ko.filepicker.getFolder(defaultDir);
    if (rubyLog != null) {
        textbox.value = rubyLog;
        ko.filepicker.internDefaultDir(prefName, rubyLog);
    }
}


