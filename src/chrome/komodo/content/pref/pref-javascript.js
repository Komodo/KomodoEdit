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

var log = ko.logging.getLogger("pref-javascript");
//log.setLevel(ko.logging.LOG_INFO);


function PrefJavaScript_OnLoad()
{
    parent.initPanel();
}

function OnPreferencePageLoading() {
    var extraPaths = document.getElementById("javascriptExtraPaths");
    extraPaths.init() // must happen after onpageload
}

// Find the user's Firefox installation and install the Komodo JavaScript
// Debugger support extension (and any of its dependencies).
function PrefJavaScript_InstallFFExtension()
{
    log.debug("PrefJavaScript_InstallFFExtension");
    try {
        var koWebbrowser = Components.classes['@activestate.com/koWebbrowser;1'].
                getService(Components.interfaces.koIWebbrowser);
        var firefoxes = koWebbrowser.get_firefox_paths(new Object());
        
        var firefox_path = null;
        if (firefoxes.length == 0) {
            var msg = "Could not find a Firefox installation on your system. "
                      +"Would you like to browse for a Firefox "
                      +"installation with which to install the extensions?";
            var answer = ko.dialogs.customButtons(msg, ["&Browse...", "Cancel"],
                                              "Browse...");
            if (answer == "Browse...") {
                var infoSvc = Components.classes["@activestate.com/koInfoService;1"].getService();
                var platform = infoSvc.platform;
                var firefox_exe_name = null;
                if (platform.match(/^win/)) {
                    firefox_exe_name = "firefox.exe";
                } else if (platform.match(/^darwin/)) {
                    firefox_exe_name = "Firefox.app";
                } else {
                    firefox_exe_name = "firefox";
                }
                firefox_path = ko.filepicker.openExeFile(null, firefox_exe_name,
                                                      "Browse for Firefox");
                if (firefox_path == null) {
                    return false;
                }
            }
        }
        //else if (firefoxes.length > 1) {
        //    //XXX Should we select from list? For now will pick the first one.
        //}
        else {
            firefox_path = firefoxes[0];
        }

        var koDirSvc = Components.classes["@activestate.com/koDirs;1"].getService();
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService();
        var jslib_xpi = osPathSvc.joinlist(3,
                [koDirSvc.supportDir, "modules", "jslib.xpi"]);
        var kjsd_xpi = osPathSvc.joinlist(3,
                [koDirSvc.supportDir, "modules",
                 "komodo_javascript_debugger.xpi"]);
        
        koWebbrowser.install_firefox_xpis(firefox_path, 2,
                                          [jslib_xpi, kjsd_xpi]);
        
        // - It would be nice to popup a dialog on pass/fail doing an
        //   appropriate thing. XXX
    } catch(ex) {
        log.exception(ex);
    }
    return true;
}

function _pref_lint_setElementEnabledState(elt, enabled) {
    if (enabled) {
        if (elt.hasAttribute('disabled')) {
            elt.removeAttribute('disabled');
        }
    } else {
        elt.setAttribute('disabled', true);
    }
}

function pref_lint_doWarningEnabling() {
    var warningsEnabledCheckbox = document.getElementById('lintJavaScriptEnableWarnings');
    var strictEnabledCheckbox = document.getElementById('lintJavaScriptEnableStrict');
    var enabled = warningsEnabledCheckbox.checked;
    _pref_lint_setElementEnabledState(strictEnabledCheckbox, enabled);
}
