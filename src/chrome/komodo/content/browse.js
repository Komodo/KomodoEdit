/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
                "Choose Default Browser",
                "Select the browser that Komodo should use to open URLs:",
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
            ko.dialogs.alert("Could not open the browser at "+browser+".");
        } else {
            ko.dialogs.alert("Could not file a graphical browser on the "+
                         "PATH with which to open '" + url + "'.");
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
    'community': "http://www.openkomodo.com/",
    'bugs': "http://bugs.ActiveState.com/OpenKomodo/"
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

