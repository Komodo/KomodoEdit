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
ko.launch = {};
ko.help = {};


(function () {
var _log = ko.logging.getLogger("ko.help");

/* XXX duplicated from help/content/contextHelp.js.  We do NOT want
   alwaysRaised attribute on the window, that's obnoxious! */

function openHelp(topic, contentPack)
{
  var helpFileURI = contentPack || helpFileURI;

  var topWindow = locateHelpWindow(helpFileURI);

  if ( topWindow ) {
    topWindow.focus();
    topWindow.displayTopic(topic);
  } else {
    const params = Components.classes["@mozilla.org/embedcomp/dialogparam;1"]
                             .createInstance(Components.interfaces.nsIDialogParamBlock);
    params.SetNumberStrings(2);
    params.SetString(0, helpFileURI);
    params.SetString(1, topic);
    window.openDialog("chrome://help/content/help.xul", "_blank", "chrome,all,close=yes", params);
  }
}

function locateHelpWindow(contentPack) {
    const windowManagerInterface = Components
        .classes['@mozilla.org/appshell/window-mediator;1'].getService()
        .QueryInterface(Components.interfaces.nsIWindowMediator);
    const iterator = windowManagerInterface.getEnumerator("mozilla:help");
    var topWindow = null;
    var aWindow;

    while (iterator.hasMoreElements()) {
        aWindow = iterator.getNext();
        if (aWindow.getHelpFileURI() == contentPack) {
            topWindow = aWindow;
        }
    }
    return topWindow;
}
/* end of contextHelp.js duplication */

/**
 * open
 *
 * open Komodo help window
 *
 * @param {String} page  a page tag as defined in toc.xml
 */
this.open = function(page) {
    openHelp(page, 'chrome://komododoc/locale/komodohelp.rdf');
}

/**
 * language
 *
 * open language specific help for the current buffer.
 */
this.language = function() {
    // Get the current document's language.
    var language = null;
    var view = ko.window.focusedView();
    if (!view) view = ko.views.manager.currentView;
    if (view != null) {
        if (view.document) {
            language = view.document.subLanguage;
            if (language == "XML") {
                // use the primary language, not the sublanguage
                language = view.document.language
            }
        } else {
            language = view.language;
        }
    }

    // Get the help command appropriate for that language.
    var command=null, name=null;
    if (language) {
        if (gPrefs.hasStringPref(language+'HelpCommand')) {
            command = gPrefs.getStringPref(language+'HelpCommand');
        } else {
            // try to get from the language service
            var langRegistrySvc = Components.classes['@activestate.com/koLanguageRegistryService;1'].
                              getService(Components.interfaces.koILanguageRegistryService);
            var languageObj = langRegistrySvc.getLanguage(language);
            if (languageObj.searchURL) {
// #if PLATFORM == "darwin"
                command = "open "+languageObj.searchURL;
// #else
                command = "%(browser) "+languageObj.searchURL;
// #endif
            }
        }
        if (command) {
            name = language + " Help";
        }
    }
    if (!command) {
        // Couldn't find language-specific help command -- use the default one.
        command = gPrefs.getStringPref('DefaultHelpCommand');
        name = "Help";
    }

    ko.run.runCommand(window,
                   command,
                   null, // cwd
                   null, // env
                   false, // insertOutput
                   false, // operateOnSelection
                   true, // doNotOpenOutputWindow
                   'no-console', // runIn
                   0, // parseOutput
                   '', // parseRegex
                   0, // showParsedOutputList
                   name); // name
}


/**
 * alternate
 *
 * uses the alternate help preference
 */
this.alternate = function() {
    var command = gPrefs.getStringPref('OtherHelpCommand');
    ko.run.runCommand(window,
                   command,
                   null, // cwd
                   null, // env
                   false, // insertOutput
                   false, // operateOnSelection
                   true, // doNotOpenOutputWindow
                   'no-console', // runIn
                   0, // parseOutput
                   '', // parseRegex
                   0, // showParsedOutputList
                   "Alternate Help"); // name
}

}).apply(ko.help);

(function () {
var _log = ko.logging.getLogger("ko.launch");
var _findPanel = null;
var _findSearchTerm = null;

/**
 * Open the Find dialog.
 *
 * @param {String} searchTerm
 */
this.find = function(searchTerm) {
    _launch_FindTab("find", searchTerm);
}

/**
 * Open the Find & Replace dialog.
 *
 * TODO: add searchTerm/replacement arguments.
 */
this.replace = function() {
    _launch_FindTab("replace", null);
}

function _launch_FindTab(panel, searchTerm) {
    // Transfer focus to the hidden input buffer to capture keystrokes from the
    // user while find.xul is loading. The find dialog will retrieve these
    // contents when it is ready.
    ko.inputBuffer.start();
    gFindSearchTerm = searchTerm;
    gFindDialogPanel = panel; // special global to pass info to find.xul
    return ko.windowManager.openOrFocusDialog("chrome://komodo/content/find/find.xul",
                      "komodo_find",
                      "chrome,close=yes");
}

/**
 * Open Find in Files dialog.
 *
 * @param {String} searchTerm
 * @param {String} folders
 */
this.findInFiles = function(searchTerm, folders) {
    _launch_FindInFilesTab("find", searchTerm, folders);
}

function _launch_FindInFilesTab(panel, searchTerm, folders) {
    // Transfer focus to the hidden input buffer to capture keystrokes from
    // the user while findInFiles.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    gFindInFilesSearchTerm = searchTerm;
    gFindInFilesFolders = folders;
    var view = ko.views.manager.currentView;
    if (view != null &&
        view.getAttribute("type") == "editor" &&
        view.document.file &&
        view.document.file.isLocal) {
        gFindInFilesCwd = view.document.file.dirName;
    } else {
        gFindInFilesCwd = null;
    }
    return ko.windowManager.openOrFocusDialog("chrome://komodo/content/find/findInFiles.xul",
                      "komodo_find_in_files",
                      "chrome,close=yes");
}


/**
 * Open the Find2 dialog for find, replace, find in files or
 * replace in files.
 */
this.find2_dialog_args = null;

this.find2 = function(pattern /* =null */) {
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    // Special global to pass info to find2.xul. Passing in via
    // openDialog() doesn't work if the dialog is already up.
    ko.launch.find2_dialog_args = {
        "pattern": pattern,
        "mode": "find"
    };

    // WARNING: Do NOT use ko.windowManager.openOrFocusDialog() here.
    // Because that ends up causing problems when re-opening the find
    // dialog (i.e. Ctrl+F when the Find dialog is already up).
    // openOrFocusDialog() results in the onfocus event but not onload
    // to the find dialog. That *could* be worked around with an onfocus
    // handler on find2.xul, but then you run into problems attempting
    // to focus the pattern textbox. (Or at least I did when experimenting
    // on Windows.)
    return window.openDialog.apply(window, 
        ko.windowManager.fixupOpenDialogArgs([
            "chrome://komodo/content/find/find2.xul",
            "komodo_find2",
            "chrome,close=yes"
        ]));
}

this.replace2 = function(pattern /* =null */, repl /* =null */) {
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    // Special global to pass info to find2.xul. Passing in via
    // openDialog() doesn't work if the dialog is already up.
    ko.launch.find2_dialog_args = {
        "pattern": pattern,
        "repl": repl,
        "mode": "replace"
    };

    // WARNING: Do NOT use ko.windowManager.openOrFocusDialog() here.
    // (See above for why.)
    return window.openDialog.apply(window, 
        ko.windowManager.fixupOpenDialogArgs([
            "chrome://komodo/content/find/find2.xul",
            "komodo_find2",
            "chrome,close=yes"
        ]));
}

/**
 * Open the find dialog for searching in a "collection" find context.
 *
 * @param collection {koICollectionFindContext} defines in what to search.
 * @param pattern {string} is the pattern to search for. Optional.
 */
this.findInCollection2 = function(collection, pattern /* =null */) {
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    // Special global to pass info to find2.xul. Passing in via
    // openDialog() doesn't work if the dialog is already up.
    ko.launch.find2_dialog_args = {
        "collection": collection,
        "pattern": pattern,
        "mode": "findincollection"
    };

    // WARNING: Do NOT use ko.windowManager.openOrFocusDialog() here.
    // (See above for why.)
    return window.openDialog(
        "chrome://komodo/content/find/find2.xul",
        "komodo_find2",
        ko.windowManager.fixupOpenDialogArgs("chrome,close=yes"));
}
//TODO:
//this.replaceInCollection2 = function(collection, pattern /* =null */,
//                                     repl /* =null */) {
//}

this.findInCurrProject2 = function(pattern /* =null */) {
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    // Special global to pass info to find2.xul. Passing in via
    // openDialog() doesn't work if the dialog is already up.
    ko.launch.find2_dialog_args = {
        "pattern": pattern,
        "mode": "findincurrproject"
    };

    // WARNING: Do NOT use ko.windowManager.openOrFocusDialog() here.
    // (See above for why.)
    return window.openDialog(
        "chrome://komodo/content/find/find2.xul",
        "komodo_find2",
        ko.windowManager.fixupOpenDialogArgs("chrome,close=yes"));
}

this.findInFiles2 = function(pattern /* =null */, dirs /* =null */,
                             includes /* =null */, excludes /* =null */) {
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    // Use the current view's cwd for interpreting relative paths.
    var view = ko.views.manager.currentView;
    var cwd = null;
    if (view != null &&
        view.getAttribute("type") == "editor" &&
        view.document.file &&
        view.document.file.isLocal) {
        cwd = view.document.file.dirName;
    }

    // Special global to pass info to find2.xul. Passing in via
    // openDialog() doesn't work if the dialog is already up.
    ko.launch.find2_dialog_args = {
        "pattern": pattern,
        "dirs": dirs,
        "includes": includes,
        "excludes": excludes,
        "cwd": cwd,
        "mode": "findinfiles"
    };

    // WARNING: Do NOT use ko.windowManager.openOrFocusDialog() here.
    // (See above for why.)
    return window.openDialog.apply(window, 
        ko.windowManager.fixupOpenDialogArgs([
            "chrome://komodo/content/find/find2.xul",
            "komodo_find2",
            "chrome,close=yes"
        ]));
}

this.replaceInFiles2 = function(pattern /* =null */, repl /* =null */,
                                dirs /* =null */, includes /* =null */,
                                excludes /* =null */) {
    // Transfer focus to the hidden input buffer to capture keystrokes
    // from the user while find2.xul is loading. The find dialog will
    // retrieve these contents when it is ready.
    ko.inputBuffer.start();

    // Special global to pass info to find2.xul. Passing in via
    // openDialog() doesn't work if the dialog is already up.
    ko.launch.find2_dialog_args = {
        "pattern": pattern,
        "repl": repl,
        "dirs": dirs,
        "includes": includes,
        "excludes": excludes,
        "mode": "replaceinfiles"
    };

    // WARNING: Do NOT use ko.windowManager.openOrFocusDialog() here.
    // (See above for why.)
    return window.openDialog.apply(window, 
        ko.windowManager.fixupOpenDialogArgs([
            "chrome://komodo/content/find/find2.xul",
            "komodo_find2",
            "chrome,close=yes"
        ]));
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
                      "chrome,close=yes");
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
this.diff = function(diff, title /* ="Diff" */, message /* =null */)
{
    if (typeof(title) == "undefined") {
        title = "Diff";
    }
    if (typeof(message) == "undefined") {
        message = null;
    }

    var obj = new Object();
    obj.title = title;
    obj.diff = diff;
    obj.message = message;
    return window.openDialog(
        "chrome://komodo/content/dialogs/diff.xul",
        "_blank",
        "chrome,all,close=yes,resizable=yes,scrollbars=yes",
        obj);
}


/**
 * watchLocalFile
 *
 * prompt for a file to watch, then open a new watch window
 *
 */
this.watchLocalFile = function() {
    var filename = ko.filepicker.openFile();
    if (filename)
        return window.openDialog("chrome://komodo/content/tail/tail.xul",
                          "_blank",
                          "chrome,all,close=yes,resizable,scrollbars",
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
    return ko.windowManager.openOrFocusDialog("chrome://mozapps/content/extensions/extensions.xul",
                                       "Extension:Manager",
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
        prompter.checkForUpdates();
    }
}

}).apply(ko.launch);

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
ko.inputBuffer = {};
(function() { // ko.inputBuffer

var _isActive = false;
this.id = "hidden-input-buffer";
this.start = function()
{
    _isActive = true;
    var inputBufferWidget = document.getElementById(ko.inputBuffer.id);
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
    var inputBufferWidget = document.getElementById(ko.inputBuffer.id);
    var contents = inputBufferWidget.value;
    inputBufferWidget.value = "";

    _isActive = false;
    return contents;
}

}).apply(ko.inputBuffer);



// backwards compat api for ko.help
var launch_LanguageHelp = ko.help.language;
var launch_AlternateLanguageHelp = ko.help.alternate;
var launch_MainHelp = ko.help.open;

// backwards compat api for ko.launch
var InputBuffer_Start = ko.inputBuffer.start;
var InputBuffer_OnFocus = ko.inputBuffer.focus;
var InputBuffer_Finish = ko.inputBuffer.finish;

// XXX globals maintained to keep things working
var gFindDialogPanel = null;
var gFindSearchTerm = null;
var gFindInFilesCwd = null;
var gFindInFilesSearchTerm = null;
var gFindInFilesFolders = null;
var gFindInFilesFiletypes = null;

var launch_openAddonsMgr = ko.launch.openAddonsMgr;
var launch_watchLocalFile = ko.launch.watchLocalFile;
var launch_DiffWindow = ko.launch.diff;
var launch_Find = ko.launch.find;
var launch_Replace = ko.launch.replace;
var launch_RunCommand = ko.launch.runCommand;
var launch_FindInFiles = ko.launch.findInFiles;
