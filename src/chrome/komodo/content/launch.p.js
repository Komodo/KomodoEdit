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
 * This file contains the functions that launch new windows such as
 * the help system, Rx, etc.
 *
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (!("help" in ko)) {
ko.help = {};
(function () {
var _log = ko.logging.getLogger("ko.help");

/* XXX duplicated from help/content/contextHelp.js.  We do NOT want
   alwaysRaised attribute on the window, that's obnoxious! */

function openHelp(topic, path = 'Manual/')
{
    var url = ko.prefs.getString('doc_site');
    if (topic) url += path + topic;
    ko.browse.openUrlInDefaultBrowser(url);
}

/* end of contextHelp.js duplication */

/**
 * Open the Komodo help window.
 *
 * @param {String} page A page tag as defined in toc.xml
 */
this.open = function(page, path) {
    openHelp(page, path);
}

/**
 * Opens language specific help for the current buffer.
 *
 * @param {string} searchTerm  Open language help for this search term.
 */
this.language = function(searchTerm) {
    // Get the current document's language.
    var language = null;
    var view = ko.window.focusedView();
    if (!view) view = ko.views.manager.currentView;
    if (view != null) {
        if (view.koDoc) {
            language = view.koDoc.subLanguage;
            if (language == "XML") {
                // use the primary language, not the sublanguage
                language = view.koDoc.language
            }
        } else {
            language = view.language;
        }
    }

    // Get the help command appropriate for that language.
    var command=null, name=null;
    if (language) {
        if (ko.prefs.hasStringPref(language+'HelpCommand')) {
            command = ko.prefs.getStringPref(language+'HelpCommand');
        } else {
            // try to get from the language service
            var langRegistrySvc = Components.classes['@activestate.com/koLanguageRegistryService;1'].
                              getService(Components.interfaces.koILanguageRegistryService);
            var languageObj = langRegistrySvc.getLanguage(language);
            if (languageObj.searchURL) {
                var searchURL = languageObj.searchURL;
                if (searchURL.indexOf("?") == -1) {
                    // search with google, encode URL correctly.
                    searchURL = ("http://www.google.com/search?q="
                                 + encodeURIComponent("site:" + searchURL)
                                 + "+%W");
                }
// #if PLATFORM == "darwin"
                command = "open " + searchURL;
// #else
                command = "%(browser) " + searchURL;
// #endif
            }
        }
        if (command) {
            name = language + " Help";
        }
    }
    if (!command) {
        // Couldn't find language-specific help command -- use the default one.
        command = ko.prefs.getStringPref('DefaultHelpCommand');
        name = "Help";
    }

    if (searchTerm && command.indexOf("%W") >= 0) {
        command = command.replace("%W", searchTerm);
    }

    ko.run.command(command,
                   {
                    "runIn": 'no-console',
                    "openOutputWindow": false,
                    "name": name,
                   });
}


/**
 * Launches the alternate help command.
 */
this.alternate = function() {
    var command = ko.prefs.getStringPref('OtherHelpCommand');
    ko.run.command(command,
                   {
                    "runIn": 'no-console',
                    "openOutputWindow": false,
                    "name": "Alternate Help",
                   });
}


/**
 * Open the Komodo error log for viewing.
 */
this.viewErrorLog = function() {
    var osSvc = Components.classes['@activestate.com/koOs;1'].getService(Components.interfaces.koIOs);
    var dirsSvc = Components.classes['@activestate.com/koDirs;1'].getService(Components.interfaces.koIDirs);
    var sysUtilsSvc = Components.classes['@activestate.com/koSysUtils;1'].getService(Components.interfaces.koISysUtils);
    var logPath = osSvc.path.join(dirsSvc.userDataDir, 'pystderr.log');

    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/komodo.properties");

    if (osSvc.path.exists(logPath)) {
        sysUtilsSvc.FlushStderr();
        var windowOpts = "centerscreen,chrome,resizable,scrollbars,dialog=no,close";
        try {
            ko.windowManager.openDialog('chrome://komodo/content/tail/tail.xul',
                                        "komodo:errorlog", windowOpts, logPath);
        } catch(e) {
            var msg = _bundle.formatStringFromName("logFileOpenFailure.alert", [e], 1);
            ko.dialogs.alert(msg);
        }
    } else {
        var msg = _bundle.formatStringFromName("logFileDoesNotExist.alert", [logPath], 1);
        ko.dialogs.alert(msg);
    }
}

/**
 * Open the Komodo memory usage report.
 */
this.memoryUsage = function() {
    ko.open.URI("about:memory", "browser");
}

}).apply(ko.help);
}

if (!("launch" in ko)) {
ko.launch = {};
(function () {
var _log = ko.logging.getLogger("ko.launch");

this.findBrowser = function(args = {})
{
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();
    
    ko.launch.find2_dialog_args = args;

    var wrapper = document.getElementById("findReplaceWrap");
    var _findBrowser = document.getElementById("findReplaceBrowser");
    if ( ! _findBrowser.hasAttribute("src")) {
        _findBrowser.setAttribute("src", "chrome://komodo/content/find/embedded.xul");
    }
    else
        _findBrowser.contentWindow.on_load();
        
    wrapper.removeAttribute("collapsed");
    
    return _findBrowser;
}

/**
 * Open the Find dialog.
 *
 * @param {String} pattern The pattern to search for.
 */
this.find = function(pattern /* =null */) {
    if (typeof(pattern) == 'undefined') pattern = null;
    ko.launch.findBrowser({
        "pattern": pattern,
        "mode": "find"
    });
}


/**
 * Open the Find/Replace dialog.
 *
 * @param {String} pattern The pattern to search for.
 * @param {String} repl The replacement pattern.
 */
this.replace = function(pattern /* =null */, repl /* =null */) {
    ko.launch.findBrowser({
        "pattern": pattern,
        "repl": repl,
        "mode": "replace"
    });
}

/**
 * Open the find dialog for searching in a "collection" find context.
 *
 * @param {koICollectionFindContext} collection defines in what to search.
 * @param {string} pattern is the pattern to search for. Optional.
 */
this.findInCollection = function(collection, pattern /* =null */) {
    ko.launch.findBrowser({
        "collection": collection,
        "pattern": pattern,
        "mode": "findincollection"
    });
}

/**
 * Open the find dialog to find & replace in a "collection" of files.
 *
 * @param {koICollectionFindContext} collection defines in what to search.
 * @param {String} pattern The pattern to search for.
 * @param {String} repl The replacement pattern.
 */
this.replaceInCollection = function(collection, pattern /* =null */,
                                    repl /* =null */) {
    ko.launch.findBrowser({
        "collection": collection,
        "pattern": pattern,
        "repl": repl,
        "mode": "replaceincollection"
    });
}

/**
 * Open Find dialog to search in the current project.
 *
 * @param {String} pattern
 */
this.findInCurrProject = function(pattern /* =null */) {
    ko.launch.findBrowser({
        "pattern": pattern,
        "mode": "findincurrproject"
    });
}


/**
 * Open Find dialog to find & replace in the current project.
 *
 * @param {String} pattern The pattern to search for.
 * @param {String} repl The replacement pattern.
 */
this.replaceInCurrProject = function(pattern /* =null */, repl /* =null */) {
    ko.launch.findBrowser({
        "pattern": pattern,
        "repl": repl,
        "mode": "replaceincurrproject"
    });
}

/**
 * Open Find dialog to search in files.
 *
 * @param {String} pattern
 * @param {String} dirs
 * @param {Array} includes
 * @param {Array} excludes
 */
this.findInFiles = function(pattern /* =null */, dirs /* =null */,
                            includes /* =null */, excludes /* =null */) {
    // Use the current view's cwd for interpreting relative paths.
    var view = ko.views.manager.currentView;
    var cwd = null;
    if (view != null &&
        view.getAttribute("type") == "editor" &&
        view.koDoc.file &&
        view.koDoc.file.isLocal) {
        cwd = view.koDoc.file.dirName;
    }

    var mode = dirs ? "findinfiles" : "findinlastfiles";
    
    ko.launch.findBrowser({
        "pattern": pattern,
        "dirs": dirs,
        "includes": includes,
        "excludes": excludes,
        "cwd": cwd,
        "mode": mode
    });
}

/**
 * Open Find dialog to make replacements in files.
 *
 * @param {String} pattern
 * @param {String} repl
 * @param {String} dirs
 * @param {Array} includes
 * @param {Array} excludes
 */
this.replaceInFiles = function(pattern /* =null */, repl /* =null */,
                               dirs /* =null */, includes /* =null */,
                               excludes /* =null */) {
    var mode = dirs ? "replaceinfiles" : "replaceinlastfiles";

    ko.launch.findBrowser({
        "pattern": pattern,
        "repl": repl,
        "dirs": dirs,
        "includes": includes,
        "excludes": excludes,
        "mode": mode
    });
}


/**
 * Show Komodo's about dialog.
 */
this.about = function about() {
    ko.windowManager.openDialog("chrome://komodo/content/about/about.xul",
        "komodo_about",
        "chrome,centerscreen,titlebar,resizable=no");
}


/**
 * runCommand
 *
 * open the run command dialog
 */
this.runCommand = function() {
    // Transfer focus to the hidden input buffer to capture keystrokes from the
    // user while run.xul is loading.  (Get the current view before calling
    // inputbuffer start so we have the correct focus coming out of the
    // dialog.)
    ko.inputBuffer.start();
    return window.openDialog("chrome://komodo/content/run/run.xul",
                      "_blank",
                      "chrome,close=yes,centerscreen");
}


/**
 * diff
 *
 * open the diff dialog, you must provide the diff
 *
 * @param {String} diff
 * @param {String} title
 * @param {String} message
 */
this.diff = function(diff, title /* ="Diff" */, message /* =null */,
                     options /* = {} */)
{
    if (typeof(title) == "undefined") {
        title = "Diff";
    }
    if (typeof(message) == "undefined") {
        message = null;
    }
    if (typeof(options) == "undefined") {
      options = { modalChild: false };
    }

    var obj = new Object();
    obj.title = title;
    obj.diff = diff;
    obj.message = message;
    var features = "chrome,close=yes,resizable=yes,scrollbars=yes,centerscreen";
    if (options.modalChild) {
       features += ",modal=yes";
    }
    return ko.windowManager.openDialog(
        "chrome://komodo/content/dialogs/diff.xul",
        "_blank",
        features,
        obj);
}


/**
 * watchLocalFile
 *
 * prompt for a file to watch, then open a new watch window
 *
 */
this.watchLocalFile = function() {
    // Rely on default to open current project or file
    var filename = ko.filepicker.browseForFile();
    if (filename)
        return window.openDialog("chrome://komodo/content/tail/tail.xul",
                          "_blank",
                          "chrome,all,close=yes,resizable,scrollbars,centerscreen",
                          filename,
                          window);
    return null;
}


/**
 * openAddonsMgr
 *
 * open the extension/add ons manager window
 *
 */
this.openAddonsMgr = function launch_openAddonsMgr()
{
    return require('scope-packages/packages').openCategory('packages-installed', "Installed Packages");
}

this.openLegacyAddonsMgr = function launch_openAddonsMgr()
{
    return ko.windowManager.openOrFocusDialog("chrome://mozapps/content/extensions/extensions.xul",
                                       "Addons:Manager",
                                       "chrome,menubar,extra-chrome,toolbar,resizable");
}

/**
 * Opens the update manager and checks for updates to the application.
 * From http://plow/source/xref/mozilla/1.8/browser/base/content/utilityOverlay.js#452
 */
this.checkForUpdates = function checkForUpdates()
{
    var um = Components.classes["@mozilla.org/updates/update-manager;1"].
        getService(Components.interfaces.nsIUpdateManager);
    var prompter = Components.classes["@mozilla.org/updates/update-prompt;1"].
        createInstance(Components.interfaces.nsIUpdatePrompt);

    // If there's an update ready to be applied, show the "Update Downloaded"
    // UI instead and let the user know they have to restart the browser for
    // the changes to be applied. 
    if (um.activeUpdate && um.activeUpdate.state == "pending") {
        prompter.showUpdateDownloaded(um.activeUpdate);
    } else {
        // bug80785 -- if we observe "quit-application-requested", each
        // window will get called, and only the last window in the
        // workspace will be saved.  Better to save the workspace now,
        // even if it turns out there's no need to restart.
        ko.workspace.saveWorkspace(true);
        prompter.checkForUpdates();
    }
}


/**
 * Open a new window
 * @param {Array} a list of URI file paths to open in new window
 * @returns {Window} returns the window created.
 */
this.newWindow = function newWindow(uris /* =null */)
{
    var args = {};
    if (typeof(uris) != "undefined"){
        if (typeof(uris) == "string"){
            _log.deprecated("ko.launch.newWindow now takes an Array of URIs as of \
                           Komodo 9.1.  Please update.");
            uris = [uris];
        }
        args.uris = uris;
    }
    return ko.windowManager.openWindow("chrome://komodo/content",
                                "_blank",
                                "chrome,all,dialog=no",
                                args);
}

this.newWindowFromWorkspace = function newWindow(workspaceIndex)
{
    ko.windowManager.openWindow("chrome://komodo/content",
                                "_blank",
                                "chrome,all,dialog=no",
                                {workspaceIndex: workspaceIndex});
}

this.newWindowForIndex = function newWindowForIndex(workspaceIndex)
{
    ko.windowManager.openWindow("chrome://komodo/content",
                                "_blank",
                                "chrome,all,dialog=no",
                                {workspaceIndex: workspaceIndex,
                                 thisIndexOnly:true});
}

this.newTemplate = function newTemplate(obj)
{
    window.openDialog("chrome://komodo/content/templates/new.xul",
                      "_blank",
                      "chrome,modal,titlebar,resizable=yes,centerscreen",
                      obj);
}


this.newVersionCheck = function(includeMinor=false)
{
    var infoSvc = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
    var [major, minor] = infoSvc.version.split(".");
    var versionStr = major + "";
    if (includeMinor)
        versionStr += minor;

    var dontBotherPref = "versioncheck.dontask." + versionStr;

    if (ko.prefs.getBoolean(dontBotherPref, false))
        return;

    var url = ko.prefs.getString("versioncheck.url");
    url = url.replace("%s", versionStr);

    var validDomains = ko.prefs.getString("versioncheck.valid.domains").split(",");

    _log.debug("versioncheck on " + url);

    var ajax = require("ko/ajax");
    ajax.request({url: url, method: 'HEAD'}, function(code, responseText, req)
    {
        var responseURL = req.responseURL;
        responseURL = require("sdk/url").URL(responseURL);
        var domain = responseURL.host.replace(/.*?(\w+\.\w+)$/, "$1");

        _log.debug("Response: " + responseURL + " (" + code + ")");

        if (validDomains.indexOf(domain) == -1 || (code != 200 && code != 301))
        {
            if ( ! includeMinor)
                this.newVersionCheck(true);
            return;
        }

        var w = require("ko/windows").getMain();
        var dialog = w.openDialog("chrome://komodo/content/empty.xul?name=versioncheck", "Komodo Just Got Better!", "modal=true,width=600,height=800,resizable=0");
        var $ = require("ko/dom");

        dialog.addEventListener("DOMContentLoaded", function (e)
        {
            if (e.target != dialog.document)
                return;

            dialog.document.documentElement.setAttribute("id", "versioncheck");

            var de = $(dialog.document.documentElement);
            var browser = $("<browser>").attr({src: url, flex: 1, type: "content"});
            var hbox = $("<hbox>").attr({ align: "center", pack: "center" });
            var ok = $("<button>").attr({ label: "Find out More", class: "primary" });
            var cancel = $("<button>").attr({ label: "Not Interested" });
            de.append(browser);
            de.append(hbox);
            hbox.append(ok);
            hbox.append(cancel);

            ok.on("command", function()
            {
                var moreInfoUrl = ko.prefs.getString("versioncheck.moreinfo.url");
                ko.browse.openUrlInDefaultBrowser(moreInfoUrl);
                dialog.close();
            });

            cancel.on("command", function()
            {
                ko.prefs.setBoolean(dontBotherPref, true);
                dialog.close();
            });

            browser.on("DOMContentLoaded", function (e)
            {
                browser.element().contentDocument.documentElement.classList.add("native-scrollbars");
                var bde = browser.element().contentDocument;

                var nav = bde.querySelector("NAV");
                var bc = bde.querySelector(".breadcrumbs");
                var bcu = bde.querySelector("#under-breadcrumb-actions");

                if (nav)
                    nav.style.display = "none";
                if (bc)
                    bc.style.display = "none";
                if (bcu)
                    bcu.style.display = "none";

                var links = $(browser.element().contentDocument).find("a[href]");
                links.on("click", function (e)
                {
                    ko.browse.openUrlInDefaultBrowser(e.target.href);
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                });

                browser.element().contentWindow.wrappedJSObject.open = (url) =>
                {
                    if ( ! url)
                        return;

                    window.setTimeout(() =>
                    {
                        ko.browse.openUrlInDefaultBrowser(url);
                    }, 0);
                };
            });
        }.bind(this));
    }.bind(this));
}

}).apply(ko.launch);
}

/**
 * Input buffering
 * When you need to capture user input while a slow XUL window is loading you
 * can use the input buffer. Usage:
 *  - in some JS code:
 *      ko.inputBuffer.start()
 *      // open XUL window
 *
 *  - in slow XUL window onload handler:
 *      var contents = ko.inputBuffer.finish();
 *      // use the contents somehow
 */
if (!("inputBuffer" in ko)) {
ko.inputBuffer = {};
(function() { // ko.inputBuffer

var _isActive = false;
this.id = "hidden-input-buffer";
this.start = function()
{
    _isActive = true;
    var inputBufferWidget = (parent||window).document.getElementById(ko.inputBuffer.id);
    inputBufferWidget.focus();
}

this.focus = function(event)
{
    // if it is not active the hidden input buffer should not have the focus
    if (!_isActive && ko.views.manager.currentView) {
        // This has to be in a timeout for the controllers to work right.
        window.setTimeout('ko.views.manager.currentView.setFocus();', 1)
    }
}


this.finish = function()
{
    // Return the contents of the input buffer and stop buffering.
    var inputBufferWidget = (parent||window).document.getElementById(ko.inputBuffer.id);
    var contents = inputBufferWidget.value;
    inputBufferWidget.value = "";

    _isActive = false;
    return contents;
}

}).apply(ko.inputBuffer);
}
