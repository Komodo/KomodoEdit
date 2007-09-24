/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * Komodo's Find and Replace dialog (see find.xul as well)
 *
 * The desired starting tab is passed in via "gFindDialogTabName" (it should
 * be one of "find" or "replace") global variable set in the openning window.
 * 'window.arguments' cannot be used because it is not set when the dialog
 * is launched with an existing instance.
 *
 * If the variable gFindSearchTerm is non-null, it is used as the
 * starting value for the search term.
 *
 * The core find functionality is in find_functions.js. Just the GUI stuff
 * resides here.
 *
 * TODO:
 *  - find and replace in files
 *  - look at perf for large files (both forward and back)
 *  - hook up a help button?
 *  - other regex syntaxes?
 *  - more search contexts
 *  - interpret the inputBuffer better, capture and appropriate handle a "tab",
 *    say, for launching the replace dialog
 *  - possibly allow multiline search terms (prefable)
 */


//---- globals

var log = ko.logging.getLogger("find");
//log.setLevel(ko.logging.LOG_DEBUG);

var parentWindow = opener;    // a hook back to the parent window

var gFindSvc = null; // the find XPCOM service that does all the grunt work
var _gFindContext; // the context in which to search

var widgets = null; // object storing interesting XUL element references

// find context types
var FCT_CURRENT_DOC = null;
var FCT_SELECTION = null;
var FCT_ALL_OPEN_DOCS = null;


//--- internal support routines

function _Initialize()
{
    // Set 'widgets' object, which contains references to interesting elements
    // in the dialog. The "panel" attribute is set the current panel (by
    // SwitchedToPanel()) so that the code in this module can refer to, say:
    //      widgets.panel.pattern
    // without having to worry about what tab is actually the current one.
    widgets = new Object();
    widgets.tabs = document.getElementById("tabs");
    widgets.panels = [
        // elements on the "find" panel
        {"name": "find",
         "tab": document.getElementById("find-tab"),
         "defaultButton": document.getElementById("find-findnext-button"),
         "panel": document.getElementById("find-panel"),
         "pattern": document.getElementById("find-pattern"),
         "replacement": null,
         "shortcuts": document.getElementById("find-shortcuts"),
         "context": document.getElementById("find-context"),
         "contextCurrDoc": document.getElementById("find-context-currentdoc"),
         "contextSelection": document.getElementById("find-context-selection"),
         "contextAllOpenDocs": document.getElementById("find-context-allopendocs"),
         "useMenulist": document.getElementById("find-use-menulist"),
         "caseMenulist": document.getElementById("find-case-menulist"),
         "searchBackward": document.getElementById("find-search-backward"),
         "matchWord": document.getElementById("find-match-word"),
         "displayInFindResults2": document.getElementById("find-display-in-find-results-2")
        },
        // elements on the "replace" panel
        {"name": "replace",
         "tab": document.getElementById("replace-tab"),
         "defaultButton": document.getElementById("replace-replace-button"),
         "panel": document.getElementById("replace-panel"),
         "pattern": document.getElementById("replace-pattern"),
         "replacement": document.getElementById("replace-replacement"),
         "shortcuts": document.getElementById("replace-shortcuts"),
         "context": document.getElementById("replace-context"),
         "contextCurrDoc": document.getElementById("replace-context-currentdoc"),
         "contextSelection": document.getElementById("replace-context-selection"),
         "contextAllOpenDocs": document.getElementById("replace-context-allopendocs"),
         "useMenulist": document.getElementById("replace-use-menulist"),
         "caseMenulist": document.getElementById("replace-case-menulist"),
         "searchBackward": document.getElementById("replace-search-backward"),
         "matchWord": document.getElementById("replace-match-word"),
         "showReplaceResults": document.getElementById("replace-show-results"),
         "displayInFindResults2": document.getElementById("replace-display-in-find-results-2")
        },
    ];

    SwitchToPanel(parentWindow.gFindDialogPanel);

    FCT_CURRENT_DOC = Components.interfaces.koIFindContext.FCT_CURRENT_DOC;
    FCT_SELECTION = Components.interfaces.koIFindContext.FCT_SELECTION;
    FCT_ALL_OPEN_DOCS = Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS;

    //---- Preload some of the UI fields as appropriate
    // If there is selected text then preload the find pattern with it. Unless
    // it spans a line, then set the search context to the selection.
    var preferredContextType = gFindSvc.options.preferredContextType;
    if (preferredContextType == FCT_ALL_OPEN_DOCS) {
        // See http://bugs.activestate.com/Komodo/show_bug.cgi?id=20003
        preferredContextType = FCT_CURRENT_DOC;
    }
    if (preferredContextType == FCT_CURRENT_DOC) {
        widgets.panel.context.selectedItem = widgets.panel.contextCurrDoc;
    } else {
        throw("unexpected preferredContextType preference setting: " +
              preferredContextType);
    }

    var scimoz = null;
    var selectedText = null;
    var useSelectedTextAsDefaultPattern = false;
    try {
        scimoz = parentWindow.ko.views.manager.currentView.scintilla.scimoz;
        selectedText = scimoz.selText;
    } catch(ex) {
        /* pass: just don't have a current editor view */
    }
    if (selectedText) {
        // If the selected text has newline characters in it or *is* an entire
        // line (without the end-of-line) then "search within selection".
        //XXX WARNING: ISciMoz.getCurLine() returns the whole line minus the
        //             last char. If the EOL is two chars then you only get
        //             last part. I.e. 'foo\r\n' -> 'foo\r'.
        var curLineObj = new Object;
        scimoz.getCurLine(curLineObj);
        var curLine = curLineObj.value;
        if (selectedText.search(/\n/) != -1
            || selectedText == curLine.substring(0,curLine.length-1))
        {
            widgets.panel.context.selectedItem = widgets.panel.contextSelection;
            // If a user does a search within a selection then the "prefered"
            // context is the current document (rather than across multiple
            // docs).
            gFindSvc.options.preferredContextType = FCT_CURRENT_DOC;
        }
        // Otherwise, use the current selection as the first search pattern
        // completion.
        else {
            useSelectedTextAsDefaultPattern = true;
        }
    }

    UpdateContext();

    // Determine the default pattern.
    var defaultPattern = "";
    if (parentWindow.gFindSearchTerm != null) {
        defaultPattern = parentWindow.gFindSearchTerm;
        parentWindow.gFindSearchTerm = null;
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
    var inputBufferContents = parentWindow.InputBuffer_Finish();
    var patternWidget = widgets.panel.pattern;
    patternWidget.setAttribute('value', '');
    if (inputBufferContents) {
        patternWidget.value = inputBufferContents;
        // we have to timeout the focus call, and do a second
        // timeout for the selection call to get the events to happen correctly
        window.setTimeout('_setFindSelectionFocus();',0);
    } else {
        patternWidget.setAttribute('value', defaultPattern);
        patternWidget.focus();
    }

    _UpdateOptionsUi();

    // The act of opening the find dialog should reset the find session. This
    // is the behaviour of least surprise.
    //log.debug("Reset find session, because opening the find dialog.");
    gFindSession.Reset();
}

function _setFindSelectionFocus()
{
    widgets.panel.pattern.focus();
    window.setTimeout('_setFindSelectionRange();',0);
}

function _setFindSelectionRange()
{
    var patternWidget = widgets.panel.pattern;
    patternWidget.setSelectionRange(patternWidget.textLength,
                                    patternWidget.textLength);
}

function _UpdateOptionsUi()
{
    var opts = gFindSvc.options;
    var i;
    //XXX Is there a way to select the right menulist item without hardcoding 3 here?
    //XXX Yes, use the DOM and check the number of children
    switch (opts.caseSensitivity) {
    case opts.FOC_INSENSITIVE:
        for (i = 0; i < 3; i++) {
            widgets.panel.caseMenulist.selectedIndex = i;
            if (widgets.panel.caseMenulist.value == "insensitive") {
                break;
            }
        }
        break;
    case opts.FOC_SENSITIVE:
        for (i = 0; i < 3; i++) {
            widgets.panel.caseMenulist.selectedIndex = i;
            if (widgets.panel.caseMenulist.value == "sensitive") {
                break;
            }
        }
        break;
    case opts.FOC_SMART:
        for (i = 0; i < 3; i++) {
            widgets.panel.caseMenulist.selectedIndex = i;
            if (widgets.panel.caseMenulist.value == "smart") {
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
            widgets.panel.useMenulist.selectedIndex = i;
            if (widgets.panel.useMenulist.value == "simple") {
                break;
            }
        }
        break;
    case opts.FOT_WILDCARD:
        for (i = 0; i < 3; i++) {
            widgets.panel.useMenulist.selectedIndex = i;
            if (widgets.panel.useMenulist.value == "wildcard") {
                break;
            }
        }
        break;
    case opts.FOT_REGEX_PYTHON:
        for (i = 0; i < 3; i++) {
            widgets.panel.useMenulist.selectedIndex = i;
            if (widgets.panel.useMenulist.value == "regex-python") {
                break;
            }
        }
        break;
    }
    if (opts.patternType == opts.FOT_REGEX_PYTHON) {
        if (widgets.panel.shortcuts.hasAttribute("disabled"))
            widgets.panel.shortcuts.removeAttribute("disabled");
    } else {
        widgets.panel.shortcuts.setAttribute("disabled", "true");
    }

    widgets.panel.searchBackward.checked = opts.searchBackward;
    widgets.panel.matchWord.checked = opts.matchWord;
    widgets.panel.displayInFindResults2.checked = opts.displayInFindResults2;
}



//---- interface routines for find.xul

function OnLoad()
{
    try {
        gFindSvc = Components.classes["@activestate.com/koFindService;1"].
                   getService(Components.interfaces.koIFindService);
        window.focus();
        _Initialize();
    } catch (ex) {
        log.exception(ex);
    }
}


function OnUnload()
{
}


function UpdateContext()
{
    switch (widgets.panel.context.selectedItem) {
    case widgets.panel.contextCurrDoc:
        _gFindContext = Components.classes[
            "@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
        _gFindContext.type = FCT_CURRENT_DOC;
        gFindSvc.options.preferredContextType = FCT_CURRENT_DOC;
        break;
    case widgets.panel.contextSelection:
        _gFindContext = Components.classes[
            "@activestate.com/koRangeFindContext;1"]
            .createInstance(Components.interfaces.koIRangeFindContext);
        _gFindContext.type = FCT_SELECTION;
        var scimoz = parentWindow.ko.views.manager.currentView.scintilla.scimoz;
        _gFindContext.startIndex = scimoz.charPosAtPosition(scimoz.selectionStart);
        _gFindContext.endIndex = scimoz.charPosAtPosition(scimoz.selectionEnd);
        break;
    case widgets.panel.contextAllOpenDocs:
        _gFindContext = Components.classes[
            "@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
        _gFindContext.type = FCT_ALL_OPEN_DOCS;
        gFindSvc.options.preferredContextType = FCT_ALL_OPEN_DOCS;
        break;
    default:
        log.error("unexpected current context widget setting: "
                  + widgets.panel.context.selectedItem.getAttribute("label"));
    }
    _UpdateOptionsUi();
}

function UpdateOption(optName)
{
    // Update a specific find service option from the UI state.
    var opts = gFindSvc.options;

    switch (optName) {
    case "case":
        var caseValue = widgets.panel.caseMenulist.value;
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
        var useValue = widgets.panel.useMenulist.value;
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

    case "searchBackward":
        opts.searchBackward = widgets.panel.searchBackward.checked;
        break;

    case "matchWord":
        opts.matchWord = widgets.panel.matchWord.checked;
        break;

    case "displayInFindResults2":
        opts.displayInFindResults2 = widgets.panel.displayInFindResults2.checked;
        break;

    default:
        throw("Don't know how to update option '" + optName + "'");
    }
}


function SwitchToPanel(name)
{
    if (!widgets) return;

    for (var i = 0; i < widgets.panels.length; ++i) {
        var panel = widgets.panels[i];
        if (panel.name == name) {
            widgets.tabs.selectedIndex = i;
            SwitchedToPanel(name);
            return;
        }
    }
    throw("Could not switch to panel '"+name+"' -- unknown panel name.");
}


function SwitchedToPanel(name)
{
    log.debug("SwitchedToPanel(name="+name+")");
    var i, j, panel, lastPanel;

    // Skip this processing if we've already done it for this panel
    // (in some cases we can call this for a given name twice in a row).
    if (widgets.panel && widgets.panel.name == name) {
        return;
    }
    
    if ("panel" in widgets)
        lastPanel = widgets.panel;
    else
        lastPanel = null;

    // set "widgets.panel" appropriately
    for (i = 0; i < widgets.panels.length; ++i) {
        panel = widgets.panels[i];
        if (panel.name == name) {
            widgets.panel = widgets.panels[i];
            break;
        }
    }

    // reset the default button
    for (i = 0; i < widgets.panels.length; ++i) {
        panel = widgets.panels[i];
        if (panel.name == name) {
            panel.defaultButton.setAttribute("default", "true");
        } else {
            if (panel.defaultButton.hasAttribute("default"))
                panel.defaultButton.removeAttribute("default");
        }
    }

    // reset accesskeys
    // Accesskey attributes on the "from" tab are removed and are added on the
    // new tab. The working set is defined by elements that have a
    // uses-accesskey="true" attribute. The data is in that element's
    // _accesskey attribute.
    var element, elements, accesskey;
    for (i = 0; i < widgets.panels.length; ++i) {
        panel = widgets.panels[i];
        if (panel.name == name) {
            elements = panel.panel.getElementsByAttribute("uses-accesskey",
                                                          "true");
            for (j = 0; j < elements.length; ++j) {
                element = elements[j];
                accesskey = element.getAttribute("_accesskey");
                //dump("adding accesskey='"+accesskey+"' to "+
                //     element.tagName+" element\n");
                element.setAttribute("accesskey", accesskey);
            }
        } else {
            elements = panel.panel.getElementsByAttribute("uses-accesskey",
                                                          "true");
            for (j = 0; j < elements.length; ++j) {
                element = elements[j];
                if (element.hasAttribute("accesskey")) {
                    //dump("removing accesskey='"+
                    //     element.getAttribute("accesskey")+"' from "+
                    //     element.tagName+" element\n");
                    element.removeAttribute("accesskey");
                }
            }
        }
    }


    // copy transferable settings
    if (lastPanel) {
        // to transfer: pattern, context, options
        var currPanel = widgets.panel;
        currPanel.pattern.setAttribute("value", lastPanel.pattern.value);
        if (lastPanel.context.selectedItem == lastPanel.contextCurrDoc) {
            currPanel.context.selectedItem = currPanel.contextCurrDoc;
        } else if (lastPanel.context.selectedItem ==
                   lastPanel.contextSelection) {
            currPanel.context.selectedItem = currPanel.contextSelection;
        } else if (lastPanel.context.selectedItem ==
                   lastPanel.contextAllOpenDocs) {
            currPanel.context.selectedItem = currPanel.contextAllOpenDocs;
        } else {
            throw("unexpected find context radio group setting");
        }
        _UpdateOptionsUi();
    }

    // give the "Find what" entry the focus
    widgets.panel.pattern.focus();
}


function CheckDefaultKeys(event, onOK) {
    if (event.keyCode == 13) {
        // fire given function for "Enter" key
        onOK();
        event.preventDefault();
    }
}

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
        var textbox = widgets.panel.pattern;
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
        var textbox = widgets.panel.pattern;

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


function doFindNext() {
    //XXX if the context is "selection" and there isn't one, then should say so
    //XXX perhaps find_functions.js should be responsible for that
    var pattern = widgets.panel.pattern.value;
    if (pattern != "") {
        ko.mru.addFromACTextbox(widgets.panel.pattern);
        var foundOne = null;
        try {
            foundOne = Find_FindNext(parentWindow, _gFindContext, pattern,
                                     widgets.panel.name);
        } catch (ex) {
            log.exception(ex, "Error in Find_FindNext");
        }
        if (!foundOne) {
            // If no match was hilighted then it is likely that the user will
            // now want to enter a different pattern. (Copying Word's behaviour
            // here.)
            widgets.panel.pattern.focus();
        }
    }
}


function doFindAll() {
    // Find all occurrences of the current pattern in the current context.
    var pattern = widgets.panel.pattern.value;
    if (pattern != "") {
        ko.mru.addFromACTextbox(widgets.panel.pattern);
//XXX These break with the following and I don't know why:
//    Komodo: Debug: chrome://komodo/content/library/common.js(12): reference to undefined property window.setCursor
//        parentWindow.setCursor("spinning");
        var foundSome = null;
        try {
            foundSome = Find_FindAll(parentWindow, _gFindContext, pattern);
        } catch (ex) {
            log.exception(ex, "Error in Find_FindAll");
        }
//        parentWindow.setCursor("auto");
        if (foundSome) {
            window.close();
        }
    }
}


function doMarkAll() {
    // Find all occurrences of the current pattern in the current context.
    var pattern = widgets.panel.pattern.value;
    if (pattern != "") {
        ko.mru.addFromACTextbox(widgets.panel.pattern);
//XXX These break with the following and I don't know why:
//    Komodo: Debug: chrome://komodo/content/library/common.js(12): reference to undefined property window.setCursor
//        parentWindow.setCursor("spinning");
        var foundSome = null;
        try {
            foundSome = Find_MarkAll(parentWindow, _gFindContext, pattern);
        } catch (ex) {
            log.exception(ex, "Error in Find_MarkAll");
        }
//        parentWindow.setCursor("auto");
        if (foundSome) {
            window.close();
        }
    }
}


function doReplace() {
    var pattern = widgets.panel.pattern.value;
    var replacement = widgets.panel.replacement.value;
    if (pattern != "") {
        ko.mru.addFromACTextbox(widgets.panel.pattern);
        if (replacement)
            ko.mru.addFromACTextbox(widgets.panel.replacement);

        var foundOne = null;
        try {
            foundOne = Find_Replace(parentWindow, _gFindContext, pattern,
                                    replacement);
        } catch (ex) {
            log.exception(ex, "Error in Find_Replace");
        }
        if (!foundOne) {
            // If no match was hilighted then it is likely that the user will
            // now want to enter a different pattern. (Copying Word's behaviour
            // here.)
            widgets.panel.pattern.focus();
        }
    }
}

function doReplaceAll() {
    var pattern = widgets.panel.pattern.value;
    var replacement = widgets.panel.replacement.value;
    if (pattern != "") {
        ko.mru.addFromACTextbox(widgets.panel.pattern);
        if (replacement)
            ko.mru.addFromACTextbox(widgets.panel.replacement);
//XXX These break with the following and I don't know why:
//    Komodo: Debug: chrome://komodo/content/library/common.js(12): reference to undefined property window.setCursor
//        parentWindow.setCursor("spinning");
        var foundSome = null;
        try {
            foundSome = Find_ReplaceAll(parentWindow, _gFindContext, pattern,
                                        replacement,
                                        widgets.panel.showReplaceResults.checked);
        } catch (ex) {
            log.exception(ex, "Error in Find_ReplaceAll");
        }
//        parentWindow.setCursor("auto");
        if (foundSome) {
            window.close();
        } else {
            widgets.panel.pattern.focus();
        }
    }
}




