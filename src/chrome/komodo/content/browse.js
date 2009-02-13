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
        var text = gKeybindingMgr.makeCurrentKeyBindingTable();
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
        var text = gKeybindingMgr.makeCommandIdTable();
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
    var url = "http://aspn.activestate.com/ASPN/Mail?topic="+topic;
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

/**
 * show our about dialog
 * XXX DEPRECATE, this should be dialog.about or ko.about
 */
this.about = function browse_About() {
  window.open("chrome://komodo/content/about.xul",
              "komodo_about",
              "chrome,dialog,modal");
}

// XXX move these to a properties file or prefs.js
var tag2uri = {
    'mailLists': "http://aspn.activestate.com/ASPN/Mail/Browse/Threaded/komodo-discuss",
    'community': "http://community.activestate.com/products/Komodo",
    
    'bugs': "http://bugs.activestate.com/query.cgi?format=specific&product=Komodo"
};

/**
 * browse to a predefined url on activestate.com  see tag2uri in ko.browse
 */
this.browseTag = function(tag) {
    if (tag in tag2uri) {
        ko.browse.openUrlInDefaultBrowser(tag2uri[tag]);
    } else {
        ko.statusBar.AddMessage(
            "ko.browse.browseTag error: unknown tag '"+tag+"'",
            "browse", 3000, true);
    }
}
}).apply(ko.browse);

