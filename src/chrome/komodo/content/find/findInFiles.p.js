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

/* Komodo's Find and Replace in Files dialog.
 *
 * Usage:
 *  Normally "window.arguments" is used to pass arguments into a dialog,
 *  however (last time I check) this is not sent in when the dialog is
 *  launched with an existing instance. So... global variables on the
 *  calling namespace are used to pass in arguments:
 *      .gFindInFilesCwd
 *          is a current working directory to be used for relative paths
 *          where necessary. If there is no appropriate such cwd it should
 *          be null.
 *      .gFindInFilesSearchTerm
 *          the search term that should be used by default (if null,
 *          then use the word under the cursor).
 *      .gFindInFilesFolders (TODO: fix this, it isn't picked up)
 *          The default value for the folders to search in.  If null,
 *          then get from prefs.
 *
 * The core find functionality is in find_functions.js. Just the GUI stuff
 * resides here.
 */


//---- globals

var log = ko.logging.getLogger("find_in_files");
//log.setLevel(ko.logging.LOG_DEBUG);

var parentWindow = opener; // a hook back to the parent window
var gFindSvc = null; // the find XPCOM service that does all the grunt work
var gFindContext; // the context in which to search
var gWidgets = null; // object storing interesting XUL element references
var gOsSvc = Components.classes["@activestate.com/koOs;1"].getService();

//--- internal support routines

function _Initialize()
{
    log.debug("_Initialize()");
    try {
        // Set 'gWidgets' object, which contains references to interesting elements
        // in the dialog.
        gWidgets = new Object();
        gWidgets.panel = {"name": "find",
             "tab": document.getElementById("find-tab"),
             "findAll": document.getElementById("find-findall-button"),
             "defaultButton": document.getElementById("find-findall-button"),
             "pattern": document.getElementById("find-pattern"),
             "shortcuts": document.getElementById("find-shortcuts"),
             "useMenulist": document.getElementById("find-use-menulist"),
             "caseMenulist": document.getElementById("find-case-menulist"),
             "matchWord": document.getElementById("find-match-word"),
             "folders": document.getElementById("find-folders"),
             "searchInSubfolders": document.getElementById("find-search-in-subfolders"),
             "includeFiletypes": document.getElementById("find-include-filetypes"),
             "excludeFiletypes": document.getElementById("find-exclude-filetypes"),
             "displayInFindResults2": document.getElementById("find-display-in-find-results-2")
        }

        gFindContext = Components.classes[
            "@activestate.com/koFindInFilesContext;1"]
            .createInstance(Components.interfaces.koIFindInFilesContext);
        gFindContext.type = Components.interfaces.koIFindContext.FCT_IN_FILES;
        gFindContext.cwd = parentWindow.gFindInFilesCwd;

        // See if we have a current view scimoz to work with. And, if so,
        // a selection to work with.
        var scimoz = null;
        var selectedText = null;
        var curLine = null;
        var currentView = parentWindow.ko.views.manager.currentView;
        if (currentView
            && currentView.scintilla) {
            scimoz = currentView.scintilla.scimoz;
            selectedText = scimoz.selText;
            var curLineObj = new Object;
            scimoz.getCurLine(curLineObj);
            curLine = curLineObj.value;
        }
        //XXX WARNING: ISciMoz.getCurLine() returns the whole line minus the
        //             last char. If the EOL is two chars then you only get
        //             last part. I.e. 'foo\r\n' -> 'foo\r'.
        var useSelectedTextAsDefaultPattern = (
            selectedText
            && selectedText.search(/\n/) == -1
            && selectedText != curLine.substring(0,curLine.length-1));

        // The default pattern:
        var defaultPattern = "";
        if (typeof(parentWindow.gFindInFilesSearchTerm) != "undefined"
            && parentWindow.gFindInFilesSearchTerm != null)
        {
            defaultPattern = parentWindow.gFindInFilesSearchTerm;
            // Need to clear this, else it will never stop being used.
            // See bug 68918.
            parentWindow.gFindInFilesSearchTerm = null;
        } else if (useSelectedTextAsDefaultPattern) {
            defaultPattern = selectedText;
        } else if (scimoz) {
            defaultPattern = ko.interpolate.getWordUnderCursor(scimoz);
        }

        // Preload with input buffer contents if any and then give focus to the
        // pattern textbox.
        // Notes:
        //   - The pattern textbox will automatically select all its contents
        //     on focus. If there are input buffer contents then we do *not*
        //     want this to happen, because this will defeat the purpose of
        //     the input buffer if the user is part way through typing in
        //     characters.
        //   - Have to set focus in a timer because this could be called within
        //     an onfocus handler, in which Mozilla does not like .focus() calls.
        var inputBufferContents = null;
        try {
            parentWindow.InputBuffer_Finish();
        } catch(ex) {
            /* ignore */
        }
        var patternWidget = gWidgets.panel.pattern;
        if (inputBufferContents) {
            patternWidget.setAttribute('value', inputBufferContents);
            patternWidget.focus();
            //XXX bogus?
            patternWidget.setSelectionRange(patternWidget.text.length,
                                            patternWidget.text.length);
        } else {
            patternWidget.setAttribute('value', defaultPattern);
            patternWidget.focus();
        }

        _UpdateOptionsUi();
        UpdateButtons();

        // The act of opening the find dialog should reset the find session. This
        // is the behaviour of least surprise.
        //log.debug("Reset find session, because opening the 'Find in Files' dialog.");
        gFindSession.Reset();
    } catch(ex) {
        log.exception(ex);
    }
}


function _UpdateOptionsUi()
{
    log.debug("_UpdateOptionsUi()");
    var opts = gFindSvc.options;
    var i;

    //XXX Is there a way to select the right menulist item without hardcoding 3 here?
    //XXX Yes, use the DOM and check the number of children
    switch (opts.caseSensitivity) {
    case opts.FOC_INSENSITIVE:
        for (i = 0; i < 3; i++) {
            gWidgets.panel.caseMenulist.selectedIndex = i;
            if (gWidgets.panel.caseMenulist.value == "insensitive") {
                break;
            }
        }
        break;
    case opts.FOC_SENSITIVE:
        for (i = 0; i < 3; i++) {
            gWidgets.panel.caseMenulist.selectedIndex = i;
            if (gWidgets.panel.caseMenulist.value == "sensitive") {
                break;
            }
        }
        break;
    case opts.FOC_SMART:
        for (i = 0; i < 3; i++) {
            gWidgets.panel.caseMenulist.selectedIndex = i;
            if (gWidgets.panel.caseMenulist.value == "smart") {
                break;
            }
        }
        break;
    }

    //XXX Is there a way to select the right menulist item without hardcoding 3 here?
    //XXX Yes, use the DOM and check the number of children
    switch (opts.patternType) {
    case opts.FOT_SIMPLE:
        for (i = 0; i < 3; i++) {
            gWidgets.panel.useMenulist.selectedIndex = i;
            if (gWidgets.panel.useMenulist.value == "simple") {
                break;
            }
        }
        break;
    case opts.FOT_WILDCARD:
        for (i = 0; i < 3; i++) {
            gWidgets.panel.useMenulist.selectedIndex = i;
            if (gWidgets.panel.useMenulist.value == "wildcard") {
                break;
            }
        }
        break;
    case opts.FOT_REGEX_PYTHON:
        for (i = 0; i < 3; i++) {
            gWidgets.panel.useMenulist.selectedIndex = i;
            if (gWidgets.panel.useMenulist.value == "regex-python") {
                break;
            }
        }
        break;
    }
    if (opts.patternType == opts.FOT_REGEX_PYTHON) {
        if (gWidgets.panel.shortcuts.hasAttribute("disabled"))
            gWidgets.panel.shortcuts.removeAttribute("disabled");
    } else {
        gWidgets.panel.shortcuts.setAttribute("disabled", "true");
    }

    gWidgets.panel.matchWord.checked = opts.matchWord;
    gWidgets.panel.displayInFindResults2.checked = opts.displayInFindResults2;

    gWidgets.panel.folders.value = opts.encodedFolders;
    gWidgets.panel.searchInSubfolders.checked = opts.searchInSubfolders;
    gWidgets.panel.includeFiletypes.value = opts.encodedIncludeFiletypes;
    gWidgets.panel.excludeFiletypes.value = opts.encodedExcludeFiletypes;
}


//---- interface routines for XUL

function OnLoad()
{
    log.debug("OnLoad()");
    try {
        gFindSvc = Components.classes["@activestate.com/koFindService;1"].
                   getService(Components.interfaces.koIFindService);
        _Initialize();
    } catch (ex) {
        log.exception(ex);
    }
}


function OnUnload()
{
    log.debug("OnUnload()");
}


function UpdateButtons()
{
    log.debug("UpdateButtons()");
    try {
        if (gWidgets.panel.pattern.value && gWidgets.panel.folders.value) {
            if (gWidgets.panel.findAll.hasAttribute("disabled"))
                gWidgets.panel.findAll.removeAttribute("disabled");
        } else {
            gWidgets.panel.findAll.setAttribute("disabled", "true");
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function UpdateOption(optName)
{
    log.debug("UpdateOption(optName='"+optName+"')");
    // Update a specific find service option from the UI state.
    try {
        var opts = gFindSvc.options;

        switch (optName) {
        case "case":
            var caseValue = gWidgets.panel.caseMenulist.value;
            if (caseValue == "insensitive") {
                opts.caseSensitivity = opts.FOC_INSENSITIVE;
            } else if (caseValue == "sensitive") {
                opts.caseSensitivity = opts.FOC_SENSITIVE;
            } else if (caseValue == "smart") {
                opts.caseSensitivity = opts.FOC_SMART;
            } else {
                throw("unrecognized 'case sensitivity' menulist value: '" +
                      caseValue + "'");
            }
            break;

        case "use":
            var useValue = gWidgets.panel.useMenulist.value;
            if (useValue == "simple") {
                opts.patternType = opts.FOT_SIMPLE;
            } else if (useValue == "regex-python") {
                opts.patternType = opts.FOT_REGEX_PYTHON;
            } else if (useValue == "wildcard") {
                opts.patternType = opts.FOT_WILDCARD;
            } else {
                throw("unrecognized 'use' menulist value: '" + useValue + "'");
            }
            _UpdateOptionsUi();
            break;

        case "matchWord":
            opts.matchWord = gWidgets.panel.matchWord.checked;
            break;

        case "displayInFindResults2":
            opts.displayInFindResults2 = gWidgets.panel.displayInFindResults2.checked;
            break;

        case "folders":
            opts.encodedFolders = gWidgets.panel.folders.value;
            break;

        case "searchInSubfolders":
            opts.searchInSubfolders = gWidgets.panel.searchInSubfolders.checked;
            break;

        case "includeFiletypes":
            opts.encodedIncludeFiletypes = gWidgets.panel.includeFiletypes.value;
            break;

        case "excludeFiletypes":
            opts.encodedExcludeFiletypes = gWidgets.panel.excludeFiletypes.value;
            break;

        default:
            throw("Don't know how to update option '" + optName + "'");
        }

        UpdateButtons();
    } catch(ex) {
        log.exception(ex);
    }
}


function UpdateFolderTextboxCWD(textbox)
{
    log.debug("UpdateFolderTextboxCWD(textbox)");
    try {
        var cwd = ko.windowManager.getMainWindow().ko.window.getCwd();
        textbox.searchParam = stringutils_updateSubAttr(
            textbox.searchParam, 'cwd', cwd);
    } catch(ex) {
        log.exception(ex);
    }
}

function FolderOnFocus(widget, event)
{
    log.debug("FolderOnFocus(textbox, event)");
    try {
        widget.setSelectionRange(0, widget.textLength);
        if (event.target.nodeName == 'html:input') { 
            var textbox = widget.parentNode.parentNode.parentNode;
            UpdateFolderTextboxCWD(textbox);
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function BrowseForDirectories() {
    log.debug("BrowseForDirectories()");
    try {
        var obj = new Object();
        obj.encodedFolders = gWidgets.panel.folders.value;
        var origWindow = ko.windowManager.getMainWindow();
        obj.cwd = origWindow.ko.window.getCwd();
        window.openDialog("chrome://komodo/content/find/browseForDirs.xul",
                          "_blank",
                          "chrome,modal,titlebar,resizable",
                          obj);
        if (obj.retval != "Cancel") {
            gWidgets.panel.folders.value = obj.encodedFolders;
            UpdateOption("folders");
        }
    } catch(ex) {
        log.exception(ex);
    }
}


//function doFindNext() {
//    //XXX if the context is "selection" and there isn't one, then should say so
//    //XXX perhaps find_functions.js should be responsible for that
//    var pattern = gWidgets.panel.pattern.value;
//    if (pattern != "") {
//        ko.mru.addFromACTextbox(gWidgets.panel.pattern);
//        var foundOne = null;
//        try {
//            foundOne = Find_FindNext(parentWindow, gFindContext, pattern,
//                                     gWidgets.panel.name);
//        } catch (ex) {
//            log.error("Error in Find_FindNext: "+ex);
//        }
//        if (!foundOne) {
//            // If no match was hilighted then it is likely that the user will
//            // now want to enter a different pattern. (Copying Word's behaviour
//            // here.)
//            gWidgets.panel.pattern.focus();
//        }
//    }
//}


// Insert the given "shortcut" into the given "textbox" widget, focus it,
// and select the inserted text.
function _insert(textbox, shortcut)
{
    var selStart = textbox.selectionStart;
    var value = textbox.value.slice(0, selStart);
    value += shortcut;
    value += textbox.value.slice(textbox.selectionEnd);
    textbox.value = value;
    textbox.focus();
    textbox.setSelectionRange(selStart,
                              selStart + shortcut.length);
}


function RegexEscape()
{
    log.debug("RegexEscape()");
    try {
        var textbox = gWidgets.panel.pattern;
        var selection = textbox.value.slice(textbox.selectionStart,
                                            textbox.selectionEnd);
        var escaped;
        if (selection) {
            escaped = gFindSvc.regex_escape_string(selection);
            var selStart = textbox.selectionStart;
            textbox.value = textbox.value.slice(0, selStart)
                + escaped + textbox.value.slice(textbox.selectionEnd);
            textbox.focus();
            textbox.setSelectionRange(selStart,
                                      selStart + escaped.length);
        } else {
            escaped = gFindSvc.regex_escape_string(textbox.value);
            textbox.value = escaped;
            textbox.focus();
        }
    } catch (ex) {
        log.exception(ex);
    }
}


function InsertRegexShortcut(shortcutWidget)
{
    log.debug("InsertRegexShortcut()");
    try {
        var shortcut = shortcutWidget.getAttribute("shortcut");
        var ellipsisIndex = shortcut.indexOf("...");
        var textbox = gWidgets.panel.pattern;

        // For bounding shortcuts (e.g., '(...)' is a bounding shortcut):
        // if there is a selection put it in as the '...' part, otherwise
        // insert and select the '...'.
        if (ellipsisIndex != -1) {
            var selection = textbox.value.slice(textbox.selectionStart,
                                                textbox.selectionEnd);
            if (selection) {
                shortcut = shortcut.replace(/\.\.\./, selection);
                _insert(textbox, shortcut);
            } else {
                _insert(textbox, shortcut);
                textbox.setSelectionRange(
                    textbox.selectionStart + ellipsisIndex,
                    textbox.selectionStart + ellipsisIndex + 3);
            }
        }
        // For non-bounding shortcuts (e.g., '^' is a non-bounding shortcut)
        // replace the selection if there is one or just insert at the
        // current pos.
        else {
            _insert(textbox, shortcut);
        }
    } catch (ex) {
        log.exception(ex);
    }
}


function doFindAll()
{
    // Find all occurrences of the current pattern in the given folders/files.
    log.debug("doFindAll()");
    try {
        ko.mru.addFromACTextbox(gWidgets.panel.pattern);
        ko.mru.addFromACTextbox(gWidgets.panel.folders);
        if (gWidgets.panel.includeFiletypes.value)
            ko.mru.addFromACTextbox(gWidgets.panel.includeFiletypes);
        if (gWidgets.panel.excludeFiletypes.value)
            ko.mru.addFromACTextbox(gWidgets.panel.excludeFiletypes);
        if (Find_FindAllInFiles(parentWindow, gFindContext,
                            gWidgets.panel.pattern.value, null)) {
            window.close();
        }
    } catch(ex) {
        log.exception(ex);
    }
}




