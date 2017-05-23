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

// Implementation:
//
// The Status Bar observes various status notification messages (e.g.
// 'current_view_encoding_changed') via Mozilla's nsIObserver mechanism.
// Because some of the
// status bar segments are specific to the currently focused view ((b)-(f)),
// the preference is that notifications only be sent for changes to the current
// view. This is not always easy, so in some cases the logic in this module
// must ensure that notifications are for the current view.

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

// The find XPCOM service that does all the grunt work.
XPCOMUtils.defineLazyGetter(lazy, "bundle", function()
    Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/statusbar.properties"));

var _observer = null;
var _prefObserver = null;
var _updateLintMessageTimer = null;

//---- helper functions

function getXulView(view)
{
    view = view || ko.views.manager.currentView;
    if ( ! view || view.getAttribute("type") != "editor") return;
    var $ = require("ko/dom");
    return $(view);
}

function _updateEncoding(view) {
    if (!view || view.getAttribute("type") != "editor") {
        return;
    }
    var xv = getXulView(view);
    
    try {
        var encoding = view.koDoc.encoding.short_encoding_name;
        var encodingWidget = xv.findAnonymous('anonid', 'statusbar-encoding').element();
        var encodingLabel = xv.findAnonymous('anonid', 'statusbar-encoding-label').element();
        encodingWidget.removeAttribute("collapsed");
        encodingLabel.setAttribute("label", encoding);
    } catch(e) {
    }
}

function _updateLanguage(view) {
    if (!view || view.getAttribute("type") != "editor") {
        return;
    }
    var xv = getXulView(view);
    try {
        var languageWidget = xv.findAnonymous('anonid', 'statusbar-language').element();
        var languageMenu = xv.findAnonymous('anonid', 'statusbar-language-menu').element();
        var language = view.koDoc.language;
        languageMenu.setAttribute("label", language);
        languageMenu.setAttribute('language', language);
        languageMenu.setAttribute('style', `list-style-image: url("koicon://ko-language/${language}")`);
        languageWidget.removeAttribute('collapsed');
    } catch(e) {
    }
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
    var xv = getXulView(view);
    var selectionWidget = xv.findAnonymous('anonid', "statusbar-selection").element();
    selectionWidget.value = selectionLabel;
    selectionWidget.removeAttribute("collapsed");
}

function _updateLineCol(view, currentLine, currentColumn) {
    if (!view || view.getAttribute("type") != "editor") {
        _clearSelection();
        return;
    }
    var xv = getXulView(view);
    
    if (typeof(currentLine)=='undefined')
        currentLine = view.currentLine;
    if (typeof(currentColumn)=='undefined')
        currentColumn = view.currentColumn;

    try {
        var lineColText = lazy.bundle.formatStringFromName("lineColCount.label",
            [currentLine, currentColumn], 2);
        var lineColWidget = xv.findAnonymous('anonid', 'statusbar-line-col').element();
        lineColWidget.setAttribute('value', lineColText);
        lineColWidget.removeAttribute("collapsed");
    } catch(ex) {
        // not a view that supports these
        _clearSelection();
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


function _clearSelection() {
    var view = getXulView();
    if ( ! view) return;
    var sel = view.findAnonymous("anonid", "statusbar-selection").element();
    sel.attr("collapsed", "true")
}

function _clear() {
    _clearSelection();
}

//---- local classes

function StatusBarObserver() {
    window.addEventListener('current_view_changed',
                            this.handle_current_view_changed, false);
    window.addEventListener('current_view_encoding_changed',
                            this.handle_current_view_encoding_changed, false);
    window.addEventListener('current_view_language_changed',
                            this.handle_current_view_language_changed, false);
    window.addEventListener('current_view_linecol_changed',
                            this.handle_current_view_linecol_changed, false);
    ko.main.addWillCloseHandler(this.destroy, this);
};

StatusBarObserver.prototype.destroy = function()
{
    if (_updateLintMessageTimer) {
        clearTimeout(_updateLintMessageTimer);
        _updateLintMessageTimer = null;
    }

    window.removeEventListener('current_view_changed',
                               this.handle_current_view_changed, false);
    window.removeEventListener('current_view_encoding_changed',
                               this.handle_current_view_encoding_changed, false);
    window.removeEventListener('current_view_language_changed',
                               this.handle_current_view_language_changed, false);
    window.removeEventListener('current_view_linecol_changed',
                               this.handle_current_view_linecol_changed, false);

    _observer = null;
    _prefObserver = null;
}

function update_view_information(view) {
    if (!view) {
        view = ko.views.manager.currentView;
    }
    _updateEncoding(view);
    _updateLanguage(view);
    _updateLineCol(view);
}

StatusBarObserver.prototype.handle_current_view_changed = function(event) {
    if (ko.views.manager.batchMode) {
        // Update it later on.
        setTimeout(update_view_information, 10);
    } else {
        update_view_information(event.originalTarget);
    }
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

function _addMessage(msg, category, timeout, highlight,
                              interactive /* false */, log /* true */)
{
    require("ko/logging").getLogger("").deprecated(
        "ko.statusbar.AddMessage is deprecated, please use require(\"notify/notify\").send() instead");

    require("notify/notify").send(msg, category, {
        priority: highlight ? 'warning' : 'info'
    });
}

//---- public functions


this.AddMessage = function(msg, category, timeout, highlight, interactive, log /* true */) {
    _addMessage(msg, category, timeout, highlight, interactive, log);
};

/**
 * Clear
 *
 * clear all statusbar elements
 */
this.Clear = function() { _clear(); }

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
    
    var xv = getXulView(view);
    
    if (!('_encodingWidget' in view)) {
        var encodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                           getService(Components.interfaces.koIEncodingServices);
    
        //var encodingName = view.koDoc.encoding.short_encoding_name;
        var encodingMenupopup = xv.findAnonymous('anonid', 'statusbar-encoding-menupopup').element();
        // Build the menupopup.
        var tempMenupopup = ko.widgets.getEncodingPopup(encodingSvc.encoding_hierarchy,
                                                        true /* toplevel */,
                                                        'ko.statusBar.changeEncoding(this)'); // action
        while (tempMenupopup.childNodes.length > 0) {
            encodingMenupopup.appendChild(tempMenupopup.removeChild(tempMenupopup.firstChild));
        }
        view._encodingWidget = true;
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

window.addEventListener("komodo-ui-started", function() {
    _observer = new StatusBarObserver();
    // Update for the current view.
    update_view_information();
    
    // TODO
    //document.getElementById("context_lint").addEventListener("popupshowing", updateLinterPopup.bind(ko.statusbar));
});

}).apply(ko.statusBar);


/**
 * @deprecated since 7.0, but kept around because it's common in macros
 */
ko.logging.globalDeprecatedByAlternative("StatusBar_AddMessage", "ko.statusBar.AddMessage", null, this);
