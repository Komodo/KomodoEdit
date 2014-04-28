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
//      Note that status messages sent this way will appear in all windows.
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

const Cc = Components.classes;
const Ci = Components.interfaces;
Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

var _log = ko.logging.getLogger('statusbar');
//_log.setLevel(ko.logging.LOG_DEBUG);

var lazy = {
};

XPCOMUtils.defineLazyGetter(lazy, "log", function() ko.logging.getLogger("find.functions"));
//locals.log.setLevel(ko.logging.LOG_DEBUG);

// The find XPCOM service that does all the grunt work.
XPCOMUtils.defineLazyGetter(lazy, "bundle", function()
    Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/statusbar.properties"));

var _messageStack = Components.classes["@activestate.com/koStatusMessageStack;1"].
                          createInstance(Components.interfaces.koIStatusMessageStack);
var _observer = null;
var _prefObserver = null;
var _updateLintMessageTimer = null;
var updateMessageRequestID = 0;

var _lastNotification = null; // last non-statusbar notification
var _lastNotificationTime = 0; // last time user interacted with statusbar notifications

var _deckIndex = {
    messages: 0
};


//---- helper functions

/**
 * Handler for auto-update notification messages.
 */
function _handle_notification(data) {
    try {
        if (!ko.prefs.getBoolean("message_notifications_enabled", true)) {
            return;
        }
        var notificationDetails = JSON.parse(data);
        if (notificationDetails.type != "notification") {
            return;
        }

        // Ensure this message hasn't been seen before - saved in local storage.
        var msgStorage;
        try {
            msgStorage = localStorage;
        } catch(ex) {
            // LocalStorage access from chrome not available until FF13.
            msgStorage = globalStorage['komodo.message_notifications'];
        }
        if (msgStorage.getItem(notificationDetails.id)) {
            return;
        }
        // Remember seeing this message.
        // TODO: It would be better if this was only set when sticky is removed.
        msgStorage.setItem(notificationDetails.id, "1");

        var options  = {
            severity: Ci.koINotification.SEVERITY_INFO,
            details: notificationDetails.message,
            sticky: true,
        };
        if (notificationDetails.action_label) {
            options.actions = [
                {
                    label: notificationDetails.action_label,
                    identifier: notificationDetails.action_url,
                    handler: function(notification, url) {
                              ko.browse.openUrlInDefaultBrowser(url);
                              notification.sticky = false;
                           },
                }
            ];
        }
        ko.notifications.add(notificationDetails.title,
                             ["notification"],
                             "notification-" + notificationDetails.id,
                             options);
    } catch(ex) {
        _log.exception(ex, "_handle_notification:: error with notification '" +
                           data + "'");
    }
}


function _updateEncoding(view) {
    if (!view || view.getAttribute("type") != "editor") {
        _clearEncoding();
        return;
    }
    try {
        var encoding = view.koDoc.encoding.short_encoding_name;
        var encodingWidget = document.getElementById('statusbar-encoding');
        var encodingLabel = document.getElementById('statusbar-encoding-label');
        encodingWidget.removeAttribute("collapsed");
        encodingLabel.setAttribute("label", encoding);
    } catch(e) {
        _clearEncoding();
    }
}

function _clearEncoding() {
    var encodingWidget = document.getElementById('statusbar-encoding');
    var encodingLabel = document.getElementById('statusbar-encoding-label');
    encodingWidget.setAttribute("collapsed", "true");
    encodingLabel.removeAttribute("label");
}


function _updateLanguage(view) {
    if (!view || view.getAttribute("type") != "editor") {
        _clearLanguage();
        return;
    }
    try {
        var languageWidget = document.getElementById('statusbar-language');
        var languageMenu = document.getElementById('statusbar-language-menu');
        var language = view.koDoc.language;
        languageMenu.setAttribute("label", language);
        languageMenu.setAttribute('language', language);
        languageWidget.removeAttribute('collapsed');
    } catch(e) {
        _clearLanguage();
    }
}


function _clearLanguage() {
    var languageWidget = document.getElementById('statusbar-language');
    var languageMenu = document.getElementById('statusbar-language-menu');
    languageWidget.setAttribute("collapsed", "true");
    languageMenu.setAttribute("label", "");
    languageMenu.setAttribute("language", "");
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
            selectionLabel = lazy.bundle.formatStringFromName(
                "selection.label", [selection.length], 1);
            if (selection.length != count) {
                // byte count
                selectionLabel += lazy.bundle.formatStringFromName(
                    "selectionByteCount.label", [count], 1);
            }
            // line count
            selectionLabel += lazy.bundle.formatStringFromName(
                "selectionLineCount.label", [(Math.abs(lineEnd - lineStart) + 1)], 1);
        }
// #if BUILD_FLAVOUR == "dev"
        if (!selectionLabel) {
            selectionLabel = "Pos: " + scimoz.currentPos;
        }
// #endif
    }
    var selectionWidget = document.getElementById("statusbar-selection");
    selectionWidget.label = selectionLabel;
    selectionWidget.removeAttribute("collapsed");
}

function _updateLineCol(view, currentLine, currentColumn) {
    if (!view || view.getAttribute("type") != "editor") {
        _clearLineColAndSelection();
        return;
    }
    if (typeof(currentLine)=='undefined')
        currentLine = view.currentLine;
    if (typeof(currentColumn)=='undefined')
        currentColumn = view.currentColumn;

    try {
        var lineColText = lazy.bundle.formatStringFromName("lineColCount.label",
            [currentLine, currentColumn], 2);
        var lineColWidget = document.getElementById('statusbar-line-col');
        lineColWidget.setAttribute('label', lineColText);
        lineColWidget.removeAttribute("collapsed");
    } catch(ex) {
        // not a view that supports these
        _clearLineColAndSelection();
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


function _clearLineColAndSelection() {
    var lineColWidget = document.getElementById('statusbar-line-col');
    lineColWidget.setAttribute("collapsed", "true");
    lineColWidget.removeAttribute("label");
    _addMessage(null, "check", 0, false);
    document.getElementById("statusbar-selection").setAttribute("collapsed", "true");
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
    if (typeof(view.lintBuffer) == "undefined"
        || !view.lintBuffer
        || !view.lintBuffer.canLintLanguage()) {
        checkWidget.setAttribute('collapsed', 'true');
        checkWidget.setAttribute("tooltiptext",
                lazy.bundle.GetStringFromName("syntaxCheckingStatus.tooltip"));
        return;
    }
    checkWidget.removeAttribute('collapsed');

    // Is linting enabled?
    var checkingEnabled = view.koDoc.getEffectivePrefs().getBooleanPref("editUseLinting");

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
                lazy.bundle.GetStringFromName("syntaxCheckingStatusInProgress.tooltip"));
            checkWidget.setAttribute('class', 'syntax-in-progress');
        } else {
            checkWidget.setAttribute("tooltiptext",
                lazy.bundle.GetStringFromName("automaticSyntaxCheckingDisabled.tooltip"));
            checkWidget.setAttribute('class', 'syntax-okay');
        }
    } else {
        var numErrors = lintResults.getNumErrors();
        var numWarnings = lintResults.getNumWarnings();
        if (numErrors <= 0 && numWarnings <= 0) {
            checkWidget.setAttribute('class', 'syntax-okay');
            checkWidget.setAttribute("tooltiptext",
                lazy.bundle.GetStringFromName("syntaxCheckingStatusOk.tooltip"));
        } else {
            if (numErrors > 0) {
                checkWidget.setAttribute('class', 'syntax-error');
            } else {
                checkWidget.setAttribute('class', 'syntax-warning');
            }
            checkWidget.setAttribute("tooltiptext",
                lazy.bundle.formatStringFromName("syntaxCheckingStatusErrors.tooltip",
                    [numErrors, numWarnings], 2));
        }
    }
} catch(ex) {
    _log.exception(ex);
}
}

function _addMessageObject(sm)
{
    if (sm.log && sm.msg) {
        ko.notifications.addNotification(sm);
    }

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
        updateMessageRequestID = setTimeout(_updateMessage, sm.timeout+epsilon);
    }

    return sm;
}

function _updateMessage()
{
    //dump("StatusBar: update message: current stack:\n");
    //_messageStack.Dump();

    // Get the latest message and show it in the UI.
    updateMessageRequestID = 0;
    if (!_messageStack) {
        // This shouldn't happen, since I'm doing a clearTimeout on
        // updateMessageRequestID at shutdown, but allow for it anyway.
        return;
    }
    var sm = _messageStack.Top();
    var internalDeck = document.getElementById('statusbar-message-internal-deck');
    var messageWidget = document.getElementById('statusbar-message');
    if (sm) {
        _log.debug("StatusBar: update message: top: msg='"+sm.msg+"', category='"+
             sm.category+"', timeout='"+sm.timeout+"', highlight='"+
             sm.highlight+"'");

        internalDeck.selectedIndex = _deckIndex.messages;
        messageWidget.setAttribute("category", sm.category);
        messageWidget.setAttribute("label", sm.msg);
        messageWidget.setAttribute("tooltiptext", sm.msg);
        if (sm.iconURL) {
            messageWidget.setAttribute("image", sm.iconURL);
        } else {
            messageWidget.removeAttribute("image");
        }
        if (sm.highlight) {
            messageWidget.setAttribute("highlite","true");
        } else {
            messageWidget.removeAttribute("highlite");
        }
        _lastNotification = sm;
    } else {
        var all_notifications = ko.notifications.getNotifications([ko.notifications.context, null], 2);
        all_notifications = all_notifications.filter(function (notification) !(notification instanceof(Ci.koIStatusMessage)));
        var notifications = all_notifications.filter(function (notification) notification.time > _lastNotificationTime)
                                             .sort(function(a, b) b.time - a.time)
                                             .sort(function(a, b) b.severity - a.severity);

        var notification = null;

        if (notifications.length > 0) {
            // notifications can last a maximum of 10 seconds
            const MAX_NOTIFICATION_TIMEOUT = 10 * 1000;
            notification = notifications[0];
            var endTime = notification.time / 1000 + MAX_NOTIFICATION_TIMEOUT;
            if (endTime < Date.now()) {
                // notification expired; don't show it in the status bar
                notification = null;
            }
        }

        if (!notification) {
            // Sticky notifications hang around until the user has interacted
            // with it.
            var sticky_notifications = all_notifications.filter(function (notification) notification.sticky)
                                                        .sort(function(a, b) b.time - a.time)
                                                        .sort(function(a, b) b.severity - a.severity);
            if (sticky_notifications.length > 0) {
                notification = sticky_notifications[0];
            }
        }

        if (notification) {
            var names = {};
            for each (let name in Object.getOwnPropertyNames(Ci.koINotification)) {
                if (/^SEVERITY_/.test(name)) {
                    names[Ci.koINotification[name]] =
                        name.replace(/^SEVERITY_/, "").toLowerCase();
                }
            }

            messageWidget.setAttribute("category", "notification-" + names[notification.severity]);
            var label = [notification.summary, notification.description]
                        .filter(function(x)!!x)
                        .join(": ");
            messageWidget.setAttribute("label", label);
            messageWidget.setAttribute("tooltiptext", label);
            if (notification.iconURL) {
                messageWidget.setAttribute("image", notification.iconURL);
            } else {
                messageWidget.removeAttribute("image");
            }
            _lastNotification = notification;
        } else {
            internalDeck.selectedIndex = 0;
            messageWidget.setAttribute("label", lazy.bundle.GetStringFromName("ready.label"));
            messageWidget.removeAttribute("tooltiptext");
            messageWidget.removeAttribute("category");
            messageWidget.removeAttribute("image");
        }
        messageWidget.removeAttribute("highlite");
    }
}


function _statusBarDblClick(event) {
    _log.debug(event.type + ": " + _lastNotification);
    if (_lastNotification) {
        _lastNotification.sticky = false;
        _lastNotificationTime = Date.now() * 1000; // usec_per_msc
        _lastNotification = null;
        ko.uilayout.ensureTabShown("notifications-widget");
        _updateMessage();
    }
}

function _clear() {
    _clearEncoding();
    _clearLanguage();
    _clearLineColAndSelection();
    _clearCheck();
}

//---- local classes

function StatusBarObserver() {
    var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    obsSvc.addObserver(this, 'status_message',false);
    obsSvc.addObserver(this, 'autoupdate-notification', false);
    Cc["@activestate.com/koNotification/manager;1"]
      .getService(Ci.koINotificationManager)
      .addListener(this);
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
    window.addEventListener('current_view_lint_results_done',
                            this.handle_current_lint_results_done, false);
    window.addEventListener('view_closed',
                            this.handle_current_view_open_or_closed, false);
    document.getElementById('statusbar-message')
            .addEventListener("dblclick", _statusBarDblClick, false);
    if (document.getElementById('breadcrumbbarWrap'))
    {
        _deckIndex.messages++;
    }
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
    obsSvc.removeObserver(this, 'autoupdate-notification');

    Cc["@activestate.com/koNotification/manager;1"]
      .getService(Ci.koINotificationManager)
      .removeListener(this);

    window.removeEventListener('current_view_changed',
                               this.handle_current_view_changed, false);
    window.removeEventListener('current_view_lint_results_done',
                               this.handle_current_lint_results_done, false);
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

    document.getElementById('statusbar-message')
            .removeEventListener("dblclick", _statusBarDblClick, false);

    if (updateMessageRequestID) {
        clearTimeout(updateMessageRequestID);
        updateMessageRequestID = 0;
    }    
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
    case 'autoupdate-notification':
        setTimeout(_handle_notification, 5000, data);
        break;
    }
}

function update_view_information(view) {
    if (!view) {
        view = ko.views.manager.currentView;
    }
    _updateEncoding(view);
    _updateLanguage(view);
    _updateLineCol(view);
    _updateCheck(view);
}

StatusBarObserver.prototype.handle_current_view_changed = function(event) {
    if (ko.views.manager.batchMode) {
        // Update it later on.
        setTimeout(update_view_information, 10);
    } else {
        update_view_information(event.originalTarget);
    }
};

StatusBarObserver.prototype.handle_current_view_check_status = function(event) {
    _updateCheck(ko.views.manager.currentView);
};

StatusBarObserver.prototype.handle_current_lint_results_done = function(event) {
    _updateCheck(ko.views.manager.currentView);
};

StatusBarObserver.prototype.handle_current_view_encoding_changed = function(event) {
    _updateEncoding(ko.views.manager.currentView);
};

StatusBarObserver.prototype.handle_current_view_language_changed = function(event) {
    _updateLanguage(ko.views.manager.currentView);
};

StatusBarObserver.prototype.handle_current_view_linecol_changed = function(event) {
    _updateLineCol(event.originalTarget,
                   event.detail["line"]+1,    // Human line num start at 1.
                   event.detail["column"]+1); // Human column num start at 1.
};

StatusBarObserver.prototype.handle_current_view_open_or_closed = function(event) {
    _clear()
};

StatusBarObserver.prototype.onNotification = function(notif, oldIndex, newIndex, reason) {
    _updateMessage();
};

function _addMessage(msg, category, timeout, highlight,
                              interactive /* false */, log /* true */)
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
    // "log" is a boolean indicating whether the message should be logged in the
    //      notification manager.  By default, messages are logged if they are
    //      not interactive.
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
        "', timeout='"+timeout+"', highlight='"+highlight+"', log='"+log+"'");

    // create a status message component and insert it into the stack
    var sm = ko.notifications
               .createNotification("status-message-" + category,
                                   ["status"], 1,
                                   ko.notifications.context,
                                   Ci.koINotificationManager.TYPE_STATUS)
               .QueryInterface(Ci.koIStatusMessage);
    sm.msg = msg;
    sm.category = category;
    sm.timeout = timeout;
    sm.highlight = highlight;
    if (typeof(interactive) == 'undefined') {
        interactive = false;
    }
    sm.interactive = interactive;
    sm.log = (typeof(log) == 'undefined') ? !interactive : log;
    return _addMessageObject(sm);
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
 * "log" is a boolean indicating whether the message should be logged. This is
 *      set by default.
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
this.AddMessage = function(msg, category, timeout, highlight, interactive, log /* true */) {
    if (msg && (msg instanceof Ci.koIStatusMessage)) {
        // this is already a message object
        return _addMessageObject(msg);
    }
    if (typeof(log) == "undefined") log = !interactive;
    return _addMessage(msg, category, timeout, highlight, interactive, log);
};

this.clearMessage = function() {
    // Create a new message stack (effectively the same as clearing one).
    _messageStack = Components.classes["@activestate.com/koStatusMessageStack;1"].
                          createInstance(Components.interfaces.koIStatusMessageStack);
    // Clear any existing message timeouts.
    if (updateMessageRequestID) {
        clearTimeout(updateMessageRequestID);
        updateMessageRequestID = 0;
    }
    _updateMessage();
};

/**
 * Clear
 *
 * clear all statusbar elements
 */
this.Clear = function() { _clear(); }

var _encodingMenuInitialized = false;

/**
 * Set the encoding menu for the current view.
 * @param {DOMElement} menupopup
 */
this.setupEncodingMenu = function(menupopup)
{
    var view = ko.views.manager.currentView;
    if (typeof(view)=='undefined' || !view || !view.koDoc) {
        return;
    }
    if (!_encodingMenuInitialized) {
        var encodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                           getService(Components.interfaces.koIEncodingServices);
    
        //var encodingName = view.koDoc.encoding.short_encoding_name;
        var encodingMenupopup = document.getElementById('statusbar-encoding-menupopup');
        // Build the menupopup.
        var tempMenupopup = ko.widgets.getEncodingPopup(encodingSvc.encoding_hierarchy,
                                                        true /* toplevel */,
                                                        'ko.statusBar.changeEncoding(this)'); // action
        while (tempMenupopup.childNodes.length > 0) {
            encodingMenupopup.appendChild(tempMenupopup.removeChild(tempMenupopup.firstChild));
        }
        _encodingMenuInitialized = true;
    }
}

/**
 * Set the encoding menu for the current view.
 * @param {DOMElement} menupopup
 */
this.changeEncoding = function(menuitem)
{
    var view = ko.views.manager.currentView;
    if (typeof(view)=='undefined' || !view || !view.koDoc) {
        return;
    }

    var encodingName = menuitem.getAttribute("data");
    if (encodingName == view.koDoc.encoding.python_encoding_name) {
        // No change.
        return;
    }

    var _file_pref_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/file-properties.properties");
    var enc = Components.classes["@activestate.com/koEncoding;1"].
                     createInstance(Components.interfaces.koIEncoding);
    enc.python_encoding_name = encodingName;
    enc.use_byte_order_marker = view.koDoc.encoding.use_byte_order_marker;

    var warning = view.koDoc.languageObj.getEncodingWarning(enc);
    var question = _file_pref_bundle.formatStringFromName(
        "areYouSureThatYouWantToChangeTheEncoding.message", [warning], 1);
    if (warning == "" || ko.dialogs.yesNo(question, "No") == "Yes") {
        try {
            view.koDoc.encoding = enc;
            // and reset the linting
            view.lintBuffer.request();
        } catch(ex) {
            var err;
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                               getService(Components.interfaces.koILastErrorService);
            var errno = lastErrorSvc.getLastErrorCode();
            var errmsg = lastErrorSvc.getLastErrorMessage();
            if (errno == Components.results.NS_ERROR_UNEXPECTED) {
                // koDocument.set_encoding() says this is an internal error
                err = _file_pref_bundle.formatStringFromName("internalErrorSettingTheEncoding.message",
                        [view.koDoc.displayPath, encodingName], 2);
                ko.dialogs.internalError(err, err+"\n\n"+errmsg, ex);
            } else {
                question = _file_pref_bundle.formatStringFromName("force.conversion.message", [errmsg], 1);
                var choice = ko.dialogs.customButtons(question,
                        [_file_pref_bundle.GetStringFromName("force.message.one"),
                         _file_pref_bundle.GetStringFromName("cancel.message")],
                         _file_pref_bundle.GetStringFromName("cancel.message")); // default
                if (choice == _file_pref_bundle.GetStringFromName("force.message.two")) {
                    try {
                        view.koDoc.forceEncodingFromEncodingName(encodingName);
                    } catch (ex2) {
                        err = _file_pref_bundle.formatStringFromName(
                                "theSampleProjectCouldNotBeFound.message",
                                [view.koDoc.baseName, encodingName], 2);
                        ko.dialogs.internalError(err, err+"\n\n"+errmsg, ex);
                    }
                }
            }
        }
    }
}

this.browserStatusHandler = {
    QueryInterface : XPCOMUtils.generateQI([Ci.nsISupportsWeakReference,
                                            Ci.nsIXULBrowserWindow]),
    setJSStatus : function(status) {
        _addMessage(status, "browser-status", 0, false, true);
    },
    setJSDefaultStatus : function(status) {},
    setOverLink : function(link, context) {
        _addMessage(link, "browser-status", 0, false, true);
    },
    onBeforeLinkTraversal: function(originalTarget, linkURI, linkNode, isAppTab) {}
};
window.QueryInterface(Ci.nsIInterfaceRequestor)
      .getInterface(Ci.nsIWebNavigation)
      .QueryInterface(Ci.nsIDocShellTreeItem)
      .treeOwner.QueryInterface(Ci.nsIInterfaceRequestor)
      .getInterface(Ci.nsIXULWindow)
      .XULBrowserWindow = this.browserStatusHandler;

window.addEventListener("komodo-ui-started", function() {
    _observer = new StatusBarObserver();
    _prefObserver = new StatusBarPrefObserver();
    // Update for the current view.
    update_view_information();
});

}).apply(ko.statusBar);


/**
 * @deprecated since 7.0, but kept around because it's common in macros
 */
ko.logging.globalDeprecatedByAlternative("StatusBar_AddMessage", "ko.statusBar.AddMessage", null, this);
