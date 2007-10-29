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
var _addMessageTimer = null;

//_log.setLevel(ko.logging.LOG_DEBUG);


//---- helper functions

function _updateEncoding(view) {
    if (typeof(view)=='undefined' || !view || !view.document)
        return;
    try {
        //XXX It would probably be cleaner to add an "encoding_name"
        //    attribute to koIView and then let each view type override that.
        //    Then the view-startpage could return null to indicate N/A.
        if (view.getAttribute("type") == "startpage") {
            _clearEncoding();
        } else {
            var encoding = view.document.encoding.short_encoding_name;
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
    if (typeof(view)=='undefined' || !view || !view.document)
        return;
    try {
        //XXX It would probably be cleaner to handle the "startpage language
        //    is N/A" logic in the view system, but I don't know how to
        //    easily do that right now.
        if (view.getAttribute("type") == "startpage") {
            _clearLanguage();
        } else {
            var language = view.document.language;
            var languageWidget = document.getElementById('statusbar-language');
            languageWidget.setAttribute("label", language);
        }
    } catch(e) {
        _clearLanguage();
    }
}


function _clearLanguage() {
    var languageWidget = document.getElementById('statusbar-language');
    languageWidget.removeAttribute("label");
}

function _updateLintMessage(view) {
    // The timeout has been called, remove the setTimeout id
    _updateLintMessageTimer = null;

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
        var msg = [];  // Used to create the selectionLabel
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
        if (selectionMode == scimoz.SC_SEL_STREAM) {
            count = selectionEnd - selectionStart;
            selection = scimoz.getTextRange(selectionStart, selectionEnd);
        } else if (selectionMode == scimoz.SC_SEL_RECTANGLE) {
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
            // Line selection mode uses different settings from scimoz API
            lineStart = scimoz.lineFromPosition(selectionStart);
            lineEnd = scimoz.lineFromPosition(selectionEnd);
            selectionStart = scimoz.getLineSelStartPosition(lineStart);
            selectionEnd = scimoz.getLineSelEndPosition(lineEnd);
            msg.push((Math.abs(lineEnd - lineStart) + 1) + " lines");
            count = selectionEnd - selectionStart;
            selection = scimoz.getTextRange(selectionStart, selectionEnd);
        }

        if (selectionStart != selectionEnd) {
            msg.push(selection.length + " chars");
            if (selection.length != count) {
                msg.push(count + " bytes");
            }
            selectionLabel = "Sel: " + msg.join(",  ");
        }
    }
    document.getElementById("statusbar-selection").label = selectionLabel;
}

function _updateLineCol(view) {
    if (typeof(view)=='undefined' || !view)
        return;

    try {
        var lineColText = "Ln: " + view.currentLine + " Col: " + view.currentColumn;
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
    checkWidget.setAttribute('src',
        "chrome://komodo/skin/images/icon_check_ok.png");
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
        checkWidget.removeAttribute("src");
        checkWidget.setAttribute("tooltiptext", "Syntax Checking Status");
        return;
    }

    // Is linting enabled?
    var checkingEnabled = view.prefs.getBooleanPref("editUseLinting");

    if (typeof(view.lintBuffer)=='undefined' || !view.lintBuffer)
        return;

    // Is there an error in the linter?
    var lintError = view.lintBuffer.errorString;
    if (lintError) {
        checkWidget.setAttribute('src',
            "chrome://komodo/skin/images/icon_check_error.png");
        checkWidget.setAttribute("tooltiptext",lintError);
        return;
    }

    // If so, get the lintResults.
    //   lintResults == null        -> inprogress
    //   lintResults.length == 0    -> ok
    //   lintResults.length > 0     -> errors/warnings
    var lintResults = view.lintBuffer.lintResults;
    if (!lintResults) {
        if (checkingEnabled) {
            checkWidget.setAttribute("tooltiptext",
                                     "Syntax Checking Status: in progress");
            checkWidget.setAttribute('src',
                "chrome://komodo/skin/images/icon_check_inprogress.png");
        } else {
            checkWidget.setAttribute("tooltiptext",
                                     "Automatic syntax checking disabled: shift-click to start");
            checkWidget.setAttribute('src',
                "chrome://komodo/skin/images/icon_check_ok.png");
        }
    } else {
        var resultsObj = new Object();
        var numResultsObj = new Object();
        lintResults.getResults(resultsObj, numResultsObj);
        if (numResultsObj.value == 0) {
            checkWidget.setAttribute('src',
                "chrome://komodo/skin/images/icon_check_ok.png");
            checkWidget.setAttribute("tooltiptext",
                                     "Syntax Checking Status: ok");
        } else {
            checkWidget.setAttribute('src',
                "chrome://komodo/skin/images/icon_check_error.png");
            checkWidget.setAttribute("tooltiptext",
                "Syntax Checking Status: " +
                lintResults.getNumErrors() + " error(s), "+
                lintResults.getNumWarnings() + " warning(s)");
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
    if (_addMessageTimer) {
        clearTimeout(_addMessageTimer);
    }
    _addMessageTimer = setTimeout(_updateMessage, 200);
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
    _addMessageTimer = null;
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
        messageWidget.setAttribute("label", sm.msg);
        messageWidget.setAttribute("tooltiptext", sm.msg);
        if (sm.highlight) {
            messageWidget.setAttribute("highlite","true");
        } else {
            messageWidget.removeAttribute("highlite");
        }
    } else {
        messageWidget.setAttribute("label","Ready");
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
    obsSvc.addObserver(this, 'view_opened',false);
    obsSvc.addObserver(this, 'view_closed',false);
    obsSvc.addObserver(this, 'current_view_changed',false);
    obsSvc.addObserver(this, 'status_bar_reset',false);
    obsSvc.addObserver(this, 'current_view_encoding_changed',false);
    obsSvc.addObserver(this, 'current_view_language_changed',false);
    obsSvc.addObserver(this, 'current_view_linecol_changed',false);
    obsSvc.addObserver(this, 'current_view_check_status',false);
    obsSvc.addObserver(this, 'status_message',false);
};
StatusBarObserver.prototype.destroy = function()
{
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                       getService(Components.interfaces.nsIObserverService);
    obsSvc.removeObserver(this, 'view_opened');
    obsSvc.removeObserver(this, 'view_closed');
    obsSvc.removeObserver(this, 'current_view_changed');
    obsSvc.removeObserver(this, 'status_bar_reset');
    obsSvc.removeObserver(this, 'current_view_encoding_changed');
    obsSvc.removeObserver(this, 'current_view_language_changed');
    obsSvc.removeObserver(this, 'current_view_linecol_changed');
    obsSvc.removeObserver(this, 'current_view_check_status');
    obsSvc.removeObserver(this, 'status_message');
}
StatusBarObserver.prototype.observe = function(subject, topic, data)
{
    // Unless otherwise specified the 'subject' is the view, and 'data'
    // arguments are expected to be empty for all notifications.
    _log.debug("StatusBar observed '"+topic+"': ");
    var view = subject;

    switch (topic) {
    case 'view_opened':
    case 'view_closed':
        _clear();
        break;
    case 'current_view_changed':
        if (!ko.views.manager.batchMode) {
            _updateEncoding(view);
            _updateLanguage(view);
            _updateLineCol(view);
            _updateCheck(view);
        }
        break;
    case 'current_view_encoding_changed':
        _updateEncoding(ko.views.manager.currentView);
        break;
    case 'current_view_language_changed':
        _updateLanguage(ko.views.manager.currentView);
        break;
    case 'current_view_linecol_changed':
        _updateLineCol(ko.views.manager.currentView);
        break;
    case 'current_view_check_status':
        _updateCheck(ko.views.manager.currentView);
        break;
    case 'status_message':
        // "subject" is expected to be a koIStatusMessage object.
        _addMessageObject(subject);
        break;
    }
}


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
    if (prefName == "editUseLinting") {
        var view = ko.views.manager.currentView;
        if (view) {
            _updateCheck(view);
        }
    }
};

_observer = new StatusBarObserver();
_prefObserver = new StatusBarPrefObserver();

window.addEventListener("unload", function() {
    _observer.destroy();
    _observer = null;
    _prefObserver.destroy();
    _prefObserver = null;
    _messageStack = null;
}, false);

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


