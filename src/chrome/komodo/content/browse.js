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

/*
 * This file contains the functions that launch browsers for e.g.
 * the language reference pages.
 *
 * A utility function ko.browse.openUrlInDefaultBrowser(url)
 * is also provided, which can be used from elsewhere in Komodo.
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}

ko.browse = {};
(function() {

var {logging} = Components.utils.import("chrome://komodo/content/library/logging.js", {});
var log = logging.getLogger("browse");
var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/browse.properties");
/**
 * open the given url or complain appropriately
 *
 * @param {String} url
 * @param {String} browser optional, retreived from prefs if not used
 */
this.openUrlInDefaultBrowser = function browse_OpenUrlInDefaultBrowser(url, browser) {
    var koWebbrowser = Components.classes['@activestate.com/koWebbrowser;1'].
                       getService(Components.interfaces.koIWebbrowser);
    var prefs = Components.classes['@activestate.com/koPrefService;1'].
            getService(Components.interfaces.koIPrefService).prefs;

    if (typeof(browser) == 'undefined' || !browser) {
        browser = prefs.getStringPref('browser');
    }
    var infoService = Components.classes['@activestate.com/koInfoService;1'].
                      getService(Components.interfaces.koIInfoService);
    var platform = infoService.platform;
    if (!platform.match(/^win/) && !platform.match(/^darwin/)
        && browser == '')
    {
        // Don't guess, since launching e.g. Mozilla can have side effects
        var browsers = koWebbrowser.get_possible_browsers(new Object());
        var answer = ko.dialogs.selectFromList(
                bundle.GetStringFromName("chooseDefaultBrowser.message"),
                bundle.GetStringFromName("selectTheBrowserToOpen.message"),
                browsers,
                "one"); // selectionCondition
        if (answer == null) {
            return;
        }
        prefs.setStringPref("browser", answer[0]);
        browser = answer[0];
    }
    var ret = false;
    try {
        if (browser) {
            ret = koWebbrowser.open_new_browser(url,browser);
        } else {
            ret = koWebbrowser.open_new(url);
        }
    } catch (e) {
        log.exception(e);
    }
    if (!ret) {
        if (browser) {
            ko.dialogs.alert(bundle.formatStringFromName(
                "couldNotOpenTheBrowserAt.alert", [browser], 1));
        } else {
            ko.dialogs.alert(bundle.formatStringFromName(
                "couldNotFindAGraphicalBrowser.alert", [url], 1));
        }
    }
}

/**
 * show a list of keybindings in the browser
 */
this.showKeybindings = function browse_ShowKeybindings()
{
    try {
        var text = ko.keybindings.manager.makeCurrentKeyBindingTable();
        var tmpFileSvc = Components.classes["@activestate.com/koFileService;1"]
                         .getService(Components.interfaces.koIFileService)
        var outputTmpFile = tmpFileSvc.makeTempFile(".html","w");
        //dump('outputTmpFile name is '+outputTmpFile.URI+'\n');
        outputTmpFile.puts(text);
        outputTmpFile.flush();
        outputTmpFile.close();
        ko.browse.openUrlInDefaultBrowser(outputTmpFile.URI);
    } catch(e) {
        log.exception(e);
    }
}

/**
 * show a list of command id's in the browser
 */
this.showCommandIds = function browse_ShowCommandIds()
{
    try {
        var text = ko.keybindings.manager.makeCommandIdTable();
        var tmpFileSvc = Components.classes["@activestate.com/koFileService;1"]
                         .getService(Components.interfaces.koIFileService)
        var outputTmpFile = tmpFileSvc.makeTempFile(".html","w");
        //dump('outputTmpFile name is '+outputTmpFile.URI+'\n');
        outputTmpFile.puts(text);
        outputTmpFile.flush();
        outputTmpFile.close();
        ko.browse.openUrlInDefaultBrowser(outputTmpFile.URI);
    } catch(e) {
        log.exception(e);
    }
}

/**
 * show the url defined in "localHelpFile" in an instance of koIAppInfoEx
 *
 * @param {String} app the app identifier from the CID of a koIAppInfoEx
 *                 implementation (eg. @activestate.com/koAppInfoEx?app=Perl)
 */
this.localHelp = function(app) {
    var info = Components.classes["@activestate.com/koAppInfoEx?app="+app+";1"]
                      .getService(Components.interfaces.koIAppInfoEx);
    ko.browse.openUrlInDefaultBrowser(info.localHelpFile);
}

/**
 * show the url defined in "webHelpURL" in an instance of koIAppInfoEx
 *
 * @param {String} app the app identifier from the CID of a koIAppInfoEx
 *                 implementation (eg. @activestate.com/koAppInfoEx?app=Perl)
 */
this.webHelp = function(app) {
    var info = Components.classes["@activestate.com/koAppInfoEx?app="+app+";1"]
                      .getService(Components.interfaces.koIAppInfoEx);
    ko.browse.openUrlInDefaultBrowser(info.webHelpURL);
}

/**
 * show mailing list archives on ASPN that are related to the topic
 *
 * @param {String} topic
 */
this.aspnMailingList = function(topic) {
    var url = "http://code.activestate.com/lists/#"+topic;
    ko.browse.openUrlInDefaultBrowser(url);
}

/**
 * Hide or show the local help entries in the Help->Languages popup
 * depending on whether an actual help file to launch can be found.
 */
this.updateHelpLanguagesPopup = function browse_UpdateHelpLanguagesPopup() {
    var perlInfoSvc = Components.classes['@activestate.com/koAppInfoEx?app=Perl;1'].
                      getService(Components.interfaces.koIAppInfoEx);
    var perlWidget = document.getElementById("menu_helpPerlRef_Local");
    var perlHelpFile = perlInfoSvc.localHelpFile;
    if (perlHelpFile) {
        perlWidget.removeAttribute("hidden");
        perlWidget.removeAttribute("collapsed");
    } else {
        perlWidget.setAttribute("hidden", true);
        perlWidget.setAttribute("collapsed", true);
    }

    var pythonInfoSvc = Components.classes['@activestate.com/koAppInfoEx?app=Python;1'].
                        getService(Components.interfaces.koIAppInfoEx);
    var pythonWidget = document.getElementById("menu_helpPythonRef_Local");
    var pythonHelpFile = pythonInfoSvc.localHelpFile;
    if (pythonHelpFile) {
        pythonWidget.removeAttribute("hidden");
        pythonWidget.removeAttribute("collapsed");
    } else {
        pythonWidget.setAttribute("hidden", true);
        pythonWidget.setAttribute("collapsed", true);
    }    

    pythonInfoSvc = Components.classes['@activestate.com/koAppInfoEx?app=Python3;1'].
                        getService(Components.interfaces.koIAppInfoEx);
    pythonWidget = document.getElementById("menu_helpPython3Ref_Local");
    pythonHelpFile = pythonInfoSvc.localHelpFile;
    if (pythonHelpFile) {
        pythonWidget.removeAttribute("hidden");
        pythonWidget.removeAttribute("collapsed");
    } else {
        pythonWidget.setAttribute("hidden", true);
        pythonWidget.setAttribute("collapsed", true);
    }

    var tclInfoSvc = Components.classes['@activestate.com/koAppInfoEx?app=Tcl;1'].
                     getService(Components.interfaces.koIAppInfoEx);
    var tclWidget = document.getElementById("menu_helpTclRef_Local");
    var tclHelpFile = tclInfoSvc.localHelpFile;
    if (tclHelpFile) {
        tclWidget.removeAttribute("hidden");
        tclWidget.removeAttribute("collapsed");
    } else {
        tclWidget.setAttribute("hidden", true);
        tclWidget.setAttribute("collapsed", true);
    }
}


// About build info (copied from about.js).
function _getAboutBuildInfo() {
    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/about.properties");
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                  getService(Components.interfaces.koIInfoService);
    var buildInfo = _bundle.formatStringFromName("aboutInfo.message",
            [infoSvc.prettyProductType,
             infoSvc.version,
             infoSvc.buildNumber,
             infoSvc.buildPlatform,
             infoSvc.buildASCTime], 5);
    var brandingPhrase = infoSvc.brandingPhrase;
    if (brandingPhrase) {
        buildInfo += "\n"+brandingPhrase;
    }
    return buildInfo;
}

/**
 * Return an object containing Bugzilla HTTP query fields.
 *
 * E.g. {"op_sys": "linux", "version": "123"}.
 */
function getKomodoBugzillaQueryParams() {
    // version      - the dumbed down Komodo version e.g. "8.0.2 IDE"
    // rep_platform - the platform architecture
    // op_sys       - the operating system
    // comment      - the description of the bug
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].
                  getService(Components.interfaces.koIInfoService);

    var version = infoSvc.version.split("-")[0];
    if (infoSvc.version.indexOf("-alpha") != -1) {
        version += " Alpha " + infoSvc.version.substr(-1);
    } else if (infoSvc.version.indexOf("-beta") != -1) {
        version += " Beta " + infoSvc.version.substr(-1);
    } else {
        version += " " + infoSvc.prettyProductType;
    }

    var rep_platform = "Any";
    var op_sys;
    if (infoSvc.platform.startsWith("win32")) {
        op_sys = "Windows (Any)";
    } else if (infoSvc.platform.startsWith("linux")) {
        op_sys = "Linux";
        if (infoSvc.buildPlatform.indexOf("64")) {
            rep_platform = "PC-64 bit";
        } else {
            rep_platform = "PC-32 bit";
        }
    } else if (infoSvc.platform == "darwin") {
        op_sys = "Mac OS X / X Server";
    }

    var comment = _getAboutBuildInfo() + "\n\n";

    return {
        "version": version,
        "rep_platform": rep_platform,
        "op_sys" : op_sys,
        "comment": comment,
    };
}

// XXX move these to a properties file or prefs.js
// XXX add links in HELP menu for:
//   -home
//   -aspn
var tag2uri = {
    'mailLists': "http://code.activestate.com/lists/komodo-discuss/",
    'home': "http://komodoide.com/",  // this one
    'aspn': "http://code.activestate.com/", // This one
    'community': "http://forum.komodoide.com/",
    'contactus': "http://www.activestate.com/company/contact-us",
    'bugs': "https://github.com/Komodo/KomodoEdit/issues",
    'packages': "http://komodoide.com/resources/",
    'contribute': "http://komodoide.com/resources/submit-instructions/#pane-resources"
};

/**
 * browse to a predefined url on activestate.com  see tag2uri in ko.browse
 */
this.browseTag = function(tag) {
    if (tag in tag2uri) {
        ko.browse.openUrlInDefaultBrowser(tag2uri[tag]);
    } else {
        require("notify/notify").send(
            "ko.browse.browseTag error: unknown tag '"+tag+"'", "browser",
            "browser", {priority: "error"}
        );
    }
}
}).apply(ko.browse);

