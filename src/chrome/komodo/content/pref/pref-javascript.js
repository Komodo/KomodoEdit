/* Copyright (c) 2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
            var answer = ko.dialogs.customButtons(msg, ["Browse...", "Cancel"],
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



