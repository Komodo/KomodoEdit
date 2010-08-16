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

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

// The status bar API for Komodo.
//
// Here is an excerpt from the status bar requirements document:
//  --------------------------------------------------------------------------
//  |  <message>                  | <ck> | <enc.> | <pos.> | <sel.> | <lang.> /,
//  --------------------------------------------------------------------------
//     ^--(a) Message                ^       ^        ^         ^       ^    ^
//        (b) Linter/Checker status -'       |        |         |       |    |
//        (c) Encoding ----------------------'        |         |       |    |
//        (d) Position (line and column) -------------'         |       |    |
//        (e) Selection (lines and chars) ----------------------'       |    |
//        (f) Language -------------------------------------------------'    |
//        (z) Grippy --------------------------------------------------------'
//
// Implementation:
//
// The Status Bar observes various status notification messages (e.g.
// 'current_view_encoding_changed') via Mozilla's nsIObserver mechanism.
// Because some of the
// status bar segments are specific to the currently focused view ((b)-(f)),
// the preference is that notifications only be sent for changes to the current
// view. This is not always easy, so in some cases the logic in this module
// must ensure that notifications are for the current view.
//
// How to make a status message:
// Method 1.
//      If you are in JavaScript code you can just issue a
//      ko.statusBar.AddMessage(...) call. See that function for a description
//      of the arguments.
// Method 2.
//      You can send a 'status_message' notification via the nsIObserver
//      mechanism where the 'subject' argument of the Notify() is a
//      koIStatusMessage object. Here is an example in Python code:
//
//        obsSvc = components.classes["@mozilla.org/observer-service;1"]\
//                 .getService(components.interfaces.nsIObserverService)
//        sm = components.classes["@activestate.com/koStatusMessage;1"]\
//             .createInstance(components.interfaces.koIStatusMessage)
//        sm.category = "<some string>"
//        sm.msg = "<some string>"
//        sm.timeout = 0    # 0 for no timeout, else a number of milliseconds
//        sm.highlight = 0  # boolean, whether or not to highlight
//        try:
//            obsSvc.notifyObservers(sm, "status_message", None)
//        except COMException, ex:
//            pass
//
// TODO:
//  - double-click and right-click functionality as per the requirements doc
//  - read-only status icon
//  - better icons for showing check status (more obvious, the inprogress one
//    must at least be replaced)


//---- globals
if (typeof(ko) == 'undefined') {
    var ko = {};
}
ko.statusBar = {};
(function() { /* ko.statusBar */

var _log = ko.logging.getLoggingMgr().getLogger('statusbar');
var _messageStack = Components.classes["@activestate.com/koStatusMessageStack;1"].
                          createInstance(Components.interfaces.koIStatusMessageStack);
var _observer = null;
var _prefObserver = null;
var _updateLintMessageTimer = null;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/statusbar.properties");

//_log.setLevel(ko.logging.LOG_DEBUG);


//---- helper functions

function _updateEncoding(view) {
    if (typeof(view)=='undefined' || !view || !view.koDoc)
        return;
    try {
        //XXX It would probably be cleaner to add an "encoding_name"
        //    attribute to koIView and then let each view type override that.
        //    Then the view-startpage could return null to indicate N/A.
        if (view.getAttribute("type") == "startpage") {
            _clearEncoding();
        } else {
            var encoding = view.koDoc.encoding.short_encoding_name;
            var encodingWidget = document.getElementById('statusbar-encoding');
            encodingWidget.setAttribute("label", encoding);
        }
    } catch(e) {
        _clearEncoding();
    }
}


function _clearEncoding() {
    var encodingWidget = document.getElementById('statusbar-encoding');
    encodingWidget.removeAttribute("label");
}


function _updateLanguage(view) {
    if (typeof(view)=='undefined' || !view || !view.koDoc)
        return;
    try {
        //XXX It would probably be cleaner to handle the "startpage language
        //    is N/A" logic in the view system, but I don't know how to
        //    easily do that right now.
        var languageWidget = document.getElementById('statusbar-language-menu');
        if (view.getAttribute("type") == "startpage") {
            _clearLanguage();
            languageWidget.setAttribute('collapsed', 'true');
        } else {
            var language = view.koDoc.language;
            languageWidget.setAttribute("label", language);
            languageWidget.removeAttribute('collapsed');
        }
    } catch(e) {
        _clearLanguage();
    }
}


function _clearLanguage() {
    var languageWidget = document.getElementById('statusbar-language-menu');
    languageWidget.setAttribute("label", "");
}

function _updateLintMessage(view) {
    // The timeout has been called, remove the setTimeout id
    _updateLintMessageTimer = null;
    if (!view || !view.koDoc || !view.lintBuffer) {
        return;
    }

    // If there are lint result messages for the current line then display
    // them.
    var lintResults = view.lintBuffer.lintResults;
    var lintError = view.lintBuffer.errorString;
    var lintMessage = null;
    if (!lintError && lintResults) {
        var resultsObj = new Object();
        var numResultsObj = new Object();
        lintResults.getResultsAtPosition(view.currentLine,
                                         view.currentColumn,
                                         resultsObj,
                                         numResultsObj);
        var results = resultsObj.value;
        var numResults = numResultsObj.value;

        for (var i = 0; i < numResults; i++) {
            if (lintMessage) {
                lintMessage += "\n" + results[i].description;
            } else {
                lintMessage = results[i].description;
            }
        }
    }

    if (lintMessage) {
        _addMessage(lintMessage, "check", 0, false);
    } else {
        _addMessage(null, "check", 0, false);
    }
}

function _updateSelectionInformation(view) {
    var selectionLabel = "";
    if (view.scintilla) {
        /**
         * @type view {Components.interfaces.ISciMoz}
         */
        var scimoz = view.scintilla.scimoz;
        var selectionStart = scimoz.anchor;
        var selectionEnd = scimoz.currentPos;
        var selectionMode = scimoz.selectionMode;

        if (selectionEnd < selectionStart) {
            // Swap the values around
            var tmp = selectionStart;
            selectionStart = selectionEnd;
            selectionEnd = tmp;
        }

        var count = 0;
        var selection;
        var lineStart, lineEnd;
        if (selectionMode == scimoz.SC_SEL_RECTANGLE) {
            // Block selection mode uses different settings from scimoz API
            selection = [];
            lineStart = scimoz.lineFromPosition(selectionStart);
            lineEnd = scimoz.lineFromPosition(selectionEnd);
            for (var i=lineStart; i <= lineEnd; i++) {
                selectionStart = scimoz.getLineSelStartPosition(i);
                selectionEnd = scimoz.getLineSelEndPosition(i);
                count += (selectionEnd - selectionStart);
                selection.push(scimoz.getTextRange(selectionStart, selectionEnd));
            }
            selection = selection.join("");
            if (count) {
                // Just ensure the selection start and end are different,
                // otherwise we won't update the selection label below.
                // Note: it does not matter what the values are from here on.
                selectionEnd = selectionStart + 1;
            }
        } else {
            lineStart = scimoz.lineFromPosition(selectionStart);
            //Components.interfaces.ISciMoz
            if (selectionMode == scimoz.SC_SEL_LINES) {
                // Line selection mode uses different settings from scimoz API
                lineEnd = scimoz.lineFromPosition(selectionEnd);
                selectionStart = scimoz.getLineSelStartPosition(lineStart);
                selectionEnd = scimoz.getLineSelEndPosition(lineEnd);
            } else {
                // With stream selection, need to check from the position
                // before the end character in order to get the line numbering
                // correct when the cursor is at the start of a line (but the
                // selection does not include this line!)
                lineEnd = scimoz.lineFromPosition(scimoz.positionBefore(selectionEnd));
            }
            count = selectionEnd - selectionStart;
            selection = scimoz.getTextRange(selectionStart, selectionEnd);
        }

        if (selectionStart != selectionEnd) {
            // character count
            selectionLabel = _bundle.formatStringFromName(
                "selection.label", [selection.length], 1);
            if (selection.length != count) {
                // byte count
                selectionLabel += _bundle.formatStringFromName(
                    "selectionByteCount.label", [count], 1);
            }
            // line count
            selectionLabel += _bundle.formatStringFromName(
                "selectionLineCount.label", [(Math.abs(lineEnd - lineStart) + 1)], 1);
        }
// #if BUILD_FLAVOUR == "dev"
        if (!selectionLabel) {
            selectionLabel = "Pos: " + scimoz.currentPos;
        }
// #endif
    }
    document.getElementById("statusbar-selection").label = selectionLabel;
}

function _updateLineCol(view) {
    if (typeof(view)=='undefined' || !view)
        return;

    try {
        var lineColText = _bundle.formatStringFromName("lineColCount.label",
            [view.currentLine, view.currentColumn], 2);
        var lineColWidget = document.getElementById('statusbar-line-col');
        lineColWidget.setAttribute('label', lineColText);
    } catch(ex) {
        // not a view that supports these
        _clearLineCol();
        return;
    }

    _updateSelectionInformation(view);

    // Add the lint message updating in a timeout
    if (_updateLintMessageTimer) {
        // Clear the old timer and then we'll start a new one
        clearTimeout(_updateLintMessageTimer);
    }

    // Don't bother updating lint messages if there is no lintBuffer element
    if (typeof(view.lintBuffer)=='undefined' || !view.lintBuffer)
        return;

    _updateLintMessageTimer = setTimeout(_updateLintMessage, 500, view);
}


function _clearLineCol() {
    var lineColWidget = document.getElementById('statusbar-line-col');
    lineColWidget.removeAttribute("label");
    _addMessage(null, "check", 0, false);
}


function _clearCheck() {
    var checkWidget = document.getElementById('statusbar-check');
    checkWidget.setAttribute('class', 'syntax-okay');
}

function _updateCheck(view) {
try {
    if (typeof(view)=='undefined' || !view || !view.prefs)
        return;

    // Update the status bar for the current check status.
    var checkWidget = document.getElementById('statusbar-check');

    // Only have linting for some view types (currently only 'editor').
    if (typeof(view.lintBuffer) == "undefined" || !view.lintBuffer)
    {
        checkWidget.setAttribute('collapsed', 'true');
        checkWidget.setAttribute("tooltiptext",
                _bundle.GetStringFromName("syntaxCheckingStatus.tooltip"));
        return;
    }
    checkWidget.removeAttribute('collapsed');

    // Is linting enabled?
    var checkingEnabled = view.prefs.getBooleanPref("editUseLinting");

    if (typeof(view.lintBuffer)=='undefined' || !view.lintBuffer)
        return;

    // Is there an error in the linter?
    var lintError = view.lintBuffer.errorString;
    if (lintError) {
        checkWidget.setAttribute('class', 'syntax-error');
        checkWidget.setAttribute("tooltiptext",lintError);
        return;
    }

    // If so, get the lintResults.
    //   lintResults == null        -> inprogress
    //   lintResults.length == 0    -> ok
    //   lintResults.length > 0     -> errors/warnings
    /** @type {Components.interfaces.koILintResults} */
    var lintResults = view.lintBuffer.lintResults;
    if (!lintResults) {
        if (checkingEnabled) {
            checkWidget.setAttribute("tooltiptext",
                _bundle.GetStringFromName("syntaxCheckingStatusInProgress.tooltip"));
            checkWidget.setAttribute('class', 'syntax-in-progress');
        } else {
            checkWidget.setAttribute("tooltiptext",
                _bundle.GetStringFromName("automaticSyntaxCheckingDisabled.tooltip"));
            checkWidget.setAttribute('class', 'syntax-okay');
        }
    } else {
        var resultsObj = new Object();
        var numResultsObj = new Object();
        lintResults.getResults(resultsObj, numResultsObj);
        if (numResultsObj.value == 0) {
            checkWidget.setAttribute('class', 'syntax-okay');
            checkWidget.setAttribute("tooltiptext",
                _bundle.GetStringFromName("syntaxCheckingStatusOk.tooltip"));
        } else {
            var numErrors = lintResults.getNumErrors();
            var numWarnings = lintResults.getNumWarnings();
            if (numErrors > 0) {
                checkWidget.setAttribute('class', 'syntax-error');
            } else {
                checkWidget.setAttribute('class', 'syntax-warning');
            }
            checkWidget.setAttribute("tooltiptext",
                _bundle.formatStringFromName("syntaxCheckingStatusErrors.tooltip",
                    [numErrors, numWarnings], 2));
        }
    }
} catch(ex) {
    _log.exception(ex);
}
}

function _addMessageObject(sm)
{
    _messageStack.Push(sm);
    //dump("StatusBar: add message: current stack:\n");
    //_messageStack.Dump();

    // Get the latest message and show it in the UI.
    _updateMessage();
    // If this new message timesout then schedule an update for then as well.
    if (sm.timeout > 0) {
        // Allow for some inaccuracy in timeout scheduling to ensure that
        // the message has actually timed-out before updating.
        var epsilon = 300;
        setTimeout(_updateMessage, sm.timeout+epsilon);
    }
}

function _updateMessage()
{
    //dump("StatusBar: update message: current stack:\n");
    //_messageStack.Dump();

    // Get the latest message and show it in the UI.
    var sm = _messageStack.Top();
    var messageWidget = document.getElementById('statusbar-message');
    if (sm) {
        _log.debug("StatusBar: update message: top: msg='"+sm.msg+"', category='"+
             sm.category+"', timeout='"+sm.timeout+"', highlight='"+
             sm.highlight+"'");

        messageWidget.setAttribute("category", sm.category);
        messageWidget.setAttribute("value", sm.msg);
        messageWidget.setAttribute("tooltiptext", sm.msg);
        if (sm.highlight) {
            messageWidget.setAttribute("highlite","true");
        } else {
            messageWidget.removeAttribute("highlite");
        }
    } else {
        messageWidget.setAttribute("value", _bundle.GetStringFromName("ready.label"));
        messageWidget.removeAttribute("tooltiptext");
        messageWidget.removeAttribute("highlite");
    }
}


function _clear() {
    _clearEncoding();
    _clearLanguage();
    _clearLineCol();
    _clearCheck();
}

//---- local classes

function StatusBarObserver() {
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    obsSvc.addObserver(this, 'status_message',false);
    window.addEventListener('current_view_changed',
                            this.handle_current_view_changed, false);
    window.addEventListener('current_view_check_status',
                            this.handle_current_view_check_status, false);
    window.addEventListener('current_view_encoding_changed',
                            this.handle_current_view_encoding_changed, false);
    window.addEventListener('current_view_language_changed',
                            this.handle_current_view_language_changed, false);
    window.addEventListener('current_view_linecol_changed',
                            this.handle_current_view_linecol_changed, false);
    window.addEventListener('view_closed',
                            this.handle_current_view_open_or_closed, false);
    ko.main.addWillCloseHandler(this.destroy, this);
};

StatusBarObserver.prototype.destroy = function()
{
    if (_updateLintMessageTimer) {
        clearTimeout(_updateLintMessageTimer);
        _updateLintMessageTimer = null;
    }
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    obsSvc.removeObserver(this, 'status_message');
    window.removeEventListener('current_view_changed',
                               this.handle_current_view_changed, false);
    window.removeEventListener('current_view_check_status',
                               this.handle_current_view_check_status, false);
    window.removeEventListener('current_view_encoding_changed',
                               this.handle_current_view_encoding_changed, false);
    window.removeEventListener('current_view_language_changed',
                               this.handle_current_view_language_changed, false);
    window.removeEventListener('current_view_linecol_changed',
                               this.handle_current_view_linecol_changed, false);
    window.removeEventListener('view_closed',
                               this.handle_current_view_open_or_closed, false);
    _messageStack = null;
    _observer = null;
    _prefObserver = null; 
}
StatusBarObserver.prototype.observe = function(subject, topic, data)
{
    // Unless otherwise specified the 'subject' is the view, and 'data'
    // arguments are expected to be empty for all notifications.
    _log.debug("StatusBar observed '"+topic+"': ");
    var view = subject;

    switch (topic) {
    case 'status_message':
        // "subject" is expected to be a koIStatusMessage object.
        _addMessageObject(subject);
        break;
    }
}

StatusBarObserver.prototype.handle_current_view_changed = function(event) {
    if (!ko.views.manager.batchMode) {
        var view = event.originalTarget;
        _updateEncoding(view);
        _updateLanguage(view);
        _updateLineCol(view);
        _updateCheck(view);
    }
};

StatusBarObserver.prototype.handle_current_view_check_status = function(event) {
    _updateCheck(ko.views.manager.currentView);
};

StatusBarObserver.prototype.handle_current_view_encoding_changed = function(event) {
    _updateEncoding(ko.views.manager.currentView);
};
StatusBarObserver.prototype.handle_current_view_language_changed = function(event) {
    _updateLanguage(ko.views.manager.currentView);
}; 

StatusBarObserver.prototype.handle_current_view_linecol_changed = function(event) {
    _updateLineCol(ko.views.manager.currentView);
}; 

StatusBarObserver.prototype.handle_current_view_open_or_closed = function(event) {
    _clear()
}; 

function _addMessage(msg, category, timeout, highlight,
                              interactive /* false */)
{
    // Post a message to the status bar message area.
    // "msg" is the message string. An empty string or null indicates
    //      that the message (of the given category) should be cleared.
    // "category" is the message group to which the message belongs. It
    //      is an arbitrary string (it must be at least one character).
    // "timeout" is the amount of time, in milliseconds, that the message
    //      should appear. A value of 0 indicates that the message does
    //      not timeout.
    // "highlight" is a boolean indicating whether the message should be
    //      highlighted on the status bar.
    // "interactive" is a boolean indicating whether the message corresponds
    //      to an interactive prompt (such as interactive search).  These
    //      have higher 'priority' over non-interactive messages in case of
    //      conflict.
    //
    // A structure similar to a stack of status messages is maintained.
    // The latest message is always shown. When/if it timesout then the
    // previous message is the stack is displayed. There can only be one
    // message per category, so reusing a category allows for removal of
    // status messages that are no longer appropriate.
    //
    // To add a message that does not timeout:
    //  _addMessage("hello there", "my_category", 0, false)
    // To remove that message:
    //  _addMessage(null, "my_category", 0, false)
    // To add a highlighted message for three seconds:
    //  _addMessage("hello there", "my_category", 3000, true)
    _log.debug("StatusBar: add message: msg='"+msg+"', category='"+category+
        "', timeout='"+timeout+"', highlight='"+highlight+"'");

    // create a status message component and insert it into the stack
    var sm = Components.classes["@activestate.com/koStatusMessage;1"].
          createInstance(Components.interfaces.koIStatusMessage);
    sm.msg = msg;
    sm.category = category;
    sm.timeout = timeout;
    sm.highlight = highlight;
    if (typeof(interactive) == 'undefined') {
        interactive = false;
    }
    sm.interactive = interactive;
    _addMessageObject(sm);
}

function StatusBarPrefObserver()
{
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    prefSvc.prefs.prefObserverService.addObserver(this,'editUseLinting',0);
    ko.main.addWillCloseHandler(this.destroy, this);
};

StatusBarPrefObserver.prototype.destroy = function()
{
    var prefSvc = Components.classes["@activestate.com/koPrefService;1"].
                  getService(Components.interfaces.koIPrefService);
    prefSvc.prefs.prefObserverService.removeObserver(this,'editUseLinting');
}
StatusBarPrefObserver.prototype.observe = function(prefSet, prefName, prefSetID)
{
    _log.debug("StatusBar: observed pref '"
            + prefName + "' change (prefSet="
            + prefSet + ", prefSetID="
            + prefSetID)
    switch (prefName) {
    case 'editUseLinting':
        var view = ko.views.manager.currentView;
        if (view) {
            _updateCheck(view);
        }
        break;
    }
};

_observer = new StatusBarObserver();
_prefObserver = new StatusBarPrefObserver();

//---- public functions

/**
 * dump
 *
 * dump the current message stack to stdout
 */
this.dump = function() { _messageStack.Dump(); }

/**
 * ClearCheck
 *
 * clear the syntax checking status
 */
this.ClearCheck = function() { _clearCheck(); }

/**
 * AddMessage
 *
 * Post a message to the status bar message area.
 * "msg" is the message string. An empty string or null indicates
 *      that the message (of the given category) should be cleared.
 * "category" is the message group to which the message belongs. It
 *      is an arbitrary string (it must be at least one character).
 * "timeout" is the amount of time, in milliseconds, that the message
 *      should appear. A value of 0 indicates that the message does
 *      not timeout.
 * "highlight" is a boolean indicating whether the message should be
 *      highlighted on the status bar.
 * "interactive" is a boolean indicating whether the message corresponds
 *      to an interactive prompt (such as interactive search).  These
 *      have higher 'priority' over non-interactive messages in case of
 *      conflict.
 *
 * A structure similar to a stack of status messages is maintained.
 * The latest message is always shown. When/if it timesout then the
 * previous message is the stack is displayed. There can only be one
 * message per category, so reusing a category allows for removal of
 * status messages that are no longer appropriate.
 *
 * To add a message that does not timeout:
 *  ko.statusBar.addMessage("hello there", "my_category", 0, false)
 * To remove that message:
 *  ko.statusBar.addMessage(null, "my_category", 0, false)
 * To add a highlighted message for three seconds:
 *  ko.statusBar.addMessage("hello there", "my_category", 3000, true)
 */
this.AddMessage = function(msg, category, timeout, highlight, interactive)
    { _addMessage(msg, category, timeout, highlight, interactive); }

/**
 * Clear
 *
 * clear all statusbar elements
 */
this.Clear = function() { _clear(); }

}).apply(ko.statusBar);


// backwards compatible APIs
var StatusBar = ko.statusBar;
var StatusBar_AddMessage = ko.statusBar.AddMessage;


