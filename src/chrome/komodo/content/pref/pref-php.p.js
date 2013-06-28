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
var availInterps = [];
var programmingLanguage="PHP";
//---- functions
var phpAppInfoEx = null;
var prefExecutable = null;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");

/* Functions Related to pref-php.xul */
function PrefPhp_OnLoad()  {
    phpAppInfoEx = Components.classes["@activestate.com/koPHPInfoInstance;1"].
            createInstance(Components.interfaces.koIPHPInfoEx);

    prefExecutable = parent.hPrefWindow.prefset.getString('phpDefaultInterpreter', '');
    PrefPhp_PopulatePHPInterps();

    parent.hPrefWindow.onpageload();
}

function OnPreferencePageLoading() {
    var extraPaths = document.getElementById("phpExtraPaths");
    extraPaths.init() // must happen after onpageload
    var file = getOwningFileObject();
    if (file && file.dirName) {
        extraPaths.setCwd(file.dirName);
    }
}

function OnPreferencePageOK(prefset)
{
    return checkValidInterpreterSetting(prefset,
                                        "phpDefaultInterpreter",
                                        programmingLanguage);
}

// Populate the (tree) list of available PHP interpreters on the current
// system.
function PrefPhp_PopulatePHPInterps()
{
    var availInterpList = document.getElementById("phpDefaultInterpreter");

    // remove any existing items and add a "finding..." one
    _findingInterps = true;
    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.formatStringFromName("findingInterpreters.label", [programmingLanguage], 1));

    // get a list of installed PHP interpreters
    var numFound = new Object();
    availInterps = phpAppInfoEx.FindExecutables(numFound);

    availInterpList.removeAllItems();
    availInterpList.appendItem(_bundle.GetStringFromName("findOnPath.label"),'');
    var found = false;
    var item = null;
    // populate the tree listing them
    if (availInterps.length == 0) {
        // tell the user no interpreter was found and direct them to
        // ActiveState to get one
        document.getElementById("no-avail-interps-message").removeAttribute("collapsed");
    } else {
        for (var i = 0; i < availInterps.length; i++) {
            item = availInterpList.appendItem(availInterps[i],availInterps[i]);
            if (availInterps[i] == prefExecutable) {
                availInterpList.selectedItem = item;
                found = true;
            }
        }
    }
    if (!found && prefExecutable) {
        availInterpList.selectedItem =
            availInterpList.appendItem(prefExecutable,prefExecutable);
    }
    _findingInterps = false;
}

function PrefPhp_SelectIni() {
}

function loadIniFile() {
    var current = document.getElementById("phpConfigFile").value;
    if (!current) {
        current = getDirectoryFromTextObject(document.getElementById("phpDefaultInterpreter"));
    }
    var prefName = "php.iniLocation";
    if (!current) {
        current = ko.filepicker.internDefaultDir(prefName);
    }
    var path = ko.filepicker.browseForFile(null, current, null, "INI", ["INI", "All"]);
    if (path != null) {
        document.getElementById("phpConfigFile").value = path;
        ko.filepicker.updateDefaultDirFromPath(prefName, path);
    }
}

function loadPHPExecutable() {
    if (loadExecutableIntoInterpreterList("phpDefaultInterpreter")) {
    }
}

