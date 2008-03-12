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

/* JavaScript-side support for Komodo's linting
 *
 * Usage:
 *  - This module is initialized at Komodo startup: lint_initialize().
 *  - A LintBuffer instance is lazily created for each view and attached
 *    to that view.
 *  - lintBuffer.request() is called to request a lint at some point
 *  - lintBuffer.reportResults() is called from the backend after processing
 *    a lint request
 *  - lintBuffer.destructor() is called when destroying it
 *  - This module is finalized at Komodo shutdown: lint_finalize().
 *
 * Notes on the various states of lint requests:
 * - Requests are made to lint when a view changes in some significant way
 *   (content changed, language changed, etc.). For optimization reasons
 *   a lint request is not made of the backend until a certain delay has
 *   expired. Until then the lint requests is known as a "delayed" request.
 *   The back end is basically a queue of lint requests and a thread
 *   processing them one at a time. If a lint request is in the queue it
 *   is known as a "pending" request. If the thread is currently processing
 *   a request it is known as the "current" request.
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}

ko.lint = {};
(function() {
    
var _lintDisplayer = null;
var _obsSvc = null;
var _lintSvc = null;
var _log = ko.logging.getLogger("lint");
//_log.setLevel(ko.logging.LOG_INFO);

var _prefs = Components.classes["@activestate.com/koPrefService;1"].
                        getService(Components.interfaces.koIPrefService).prefs;


//---- The new LintBuffer class (replacement for jsLintBuffer)
//
// There is one of these for each Komodo 'editor' view. It is responsible
// for all JS-side linting handling for that view.
//

this.lintBuffer = function LintBuffer(view) {
    _log.info("LintBuffer["+view.title+"].constructor()");
    try {
        this.view = view;
        this.lintingEnabled = this.view.prefs.getBooleanPref("editUseLinting");
        this.lintResults = null;
        this.errorString = null;
        this._lastRequestId = 0; // used to ensure only the last request is used

        _prefs.prefObserverService.addObserver(this, "editUseLinting", false);
        _prefs.prefObserverService.addObserver(this, "perl_lintOption", false);
        this.view.prefs.prefObserverService.addObserver(this,
                                                        "editUseLinting",
                                                        false);

        this._lintTimer = null; // used to control when lint requests are issued
    } catch(ex) {
        _log.exception(ex);
    }
}
this.lintBuffer.prototype.constructor = this.lintBuffer;


this.lintBuffer.prototype.QueryInterface = function (iid)
{
    if (!iid.equals(Components.interfaces.nsIObserver) &&
        !iid.equals(Components.interfaces.koILintBuffer) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}


this.lintBuffer.prototype.destructor = function()
{
    _log.info("LintBuffer["+this.view.title+"].destructor()");
    try {
        _lintSvc.cancelPendingRequests(this.view.uid);
        this._cancelDelayedRequest();
        this._clearResults();

        this.view.prefs.prefObserverService.removeObserver(this,
                                                           "editUseLinting");
        _prefs.prefObserverService.removeObserver(this, "editUseLinting");
        _prefs.prefObserverService.removeObserver(this, "perl_lintOption");

        this.view = null; // drop reference to the view
    } catch(ex) {
        _log.exception(ex);
    }
}


// nsIObserver.observe()
this.lintBuffer.prototype.observe = function(subject, topic, data)
{
    //_log.debug("LintBuffer["+this.view.title+"].observe: subject="+
    //               subject+", topic="+topic+", data="+data);
    try {
        var lintingEnabled;
        switch (topic) {
        case "perl_lintOption":
            lintingEnabled = this.view.prefs.getBooleanPref("editUseLinting");
            _log.info("LintBuffer["+this.view.title+
                           "].observe: lintingEnabled="+lintingEnabled);
            if (lintingEnabled && this.view.languageObj.name == "Perl") {
                this.request();
            }
            break;
        case "editUseLinting":
            lintingEnabled = this.view.prefs.getBooleanPref("editUseLinting");
            _log.info("LintBuffer["+this.view.title+
                           "].observe: lintingEnabled="+lintingEnabled);
            if (lintingEnabled != this.lintingEnabled) {
                // Do whatever must be done when the lintingEnabled state changes.
                this.lintingEnabled = lintingEnabled;
                if (lintingEnabled) {
                    this.request();
                } else {
                    _lintSvc.cancelPendingRequests(this.view.uid);
                    this._cancelDelayedRequest();
                    this._clearResults();
                    this._notify();
                }
            }
        }
    } catch(ex) {
        _log.exception(ex);
    }
}


// Called to request that the view be linted sometime soon.
//
// Note: To attempt to avoid a flurry of lints when the user is typing into
// the document (because lints can be expensive) every .request() does not
// necessarily result in a lint. Lint requests are only forwarded to the
// linting backend after a delay 
//
this.lintBuffer.prototype.request = function(reason /* = "" */)
{
    if (typeof(reason) == "undefined" || reason == null) reason = "";
    _log.info("LintBuffer["+this.view.title+"].request(reason='"+
                  reason+"')");
    try {
        _lintSvc.cancelPendingRequests(this.view.uid);
        this._clearResults();

        // Increment this here instead of in ._issueRequest() to ensure that
        // a request issued at time T1 is not considered current when its
        // results are reported at time T2 if the buffer has changed between
        // those two times.
        this._lastRequestId += 1;

        // cancel the pending timeout if the request comes
        // in before the request timeout has expired
        if (this._lintTimer) {
            this._lintTimer.stopTimeout();
        }
        this._lintTimer = new objectTimer(this, this._issueRequest, []);
        var delay;
        if (! _prefs.getBooleanPref('editUseLinting')) {
            delay = 0;
        } else {
            delay = _prefs.getLongPref('lintDelay'); // lint request delay (in ms)
        }
        this._lintTimer.startTimeout(delay);

        this._notify();
    } catch(ex) {
        _log.exception(ex);
    }
}


// koILintBuffer.reportResults()
this.lintBuffer.prototype.reportResults = function(request)
{
    if (!this.view) {
        _log.debug("lineBuffer.reportResults: this.view is null");
        return;
    }
    _log.info("LintBuffer["+this.view.title+"].reportResults(request)");
    try {
        // Ignore results that are not the last one issued (it means there
        // is another one in the pipe).
        if (request.rid == this._lastRequestId) {
            this.lintResults = request.results;
            this.errorString = request.errorString;
            if (this.lintResults) {
                _lintDisplayer.display(this.view.scimoz, this.lintResults,
                                       this.view.document.languageObj.indicatorBits,
                                       0, this.view.scimoz.length);
            }
            this._notify();
        }
    } catch(ex) {
        _log.exception(ex);
    }
}


// Actually issue a lint request to the linting backend.
this.lintBuffer.prototype._issueRequest = function()
{
    _log.info("LintBuffer["+this.view.title+"]._issueRequest()");
    try {
        var linterCID = this._getLinterCID();
        var lr = this._createLintRequest(linterCID);
        _lintSvc.addRequest(lr);
        this._cancelDelayedRequest();
    } catch(ex) {
        if (ex.message.indexOf("Internal Error creating a linter with CID") >= 0) {
            _log.debug("No linter for component " + linterCID);
        } else {
            _log.exception(ex);
        }
    }
}


// Cancel the delayed request if there is one.
this.lintBuffer.prototype._cancelDelayedRequest = function()
{
    _log.debug("LintBuffer["+this.view.title+"]._cancelDelayedRequest()");
    try {
        if (this._lintTimer) {
            this._lintTimer.stopTimeout();
            this._lintTimer.free();
            this._lintTimer = null;
        }
    } catch(ex) {
        _log.exception(ex);
    }
}


// Clear the current lint results, if there are any.
this.lintBuffer.prototype._clearResults = function()
{
    _log.debug("LintBuffer["+this.view.title+"]._clearResults()");
    try {
        if (this.lintResults) {
            // .displayClear() has to be called in a timeout to avoid
            // re-entrance into scintilla: we are already mostly likely in
            // a scintilla onModified event handler (linting is most
            // common requested for a buffer modification).
            window.setTimeout(
                function(lintDisplayer, view) {
                    if (view && view.document) {
                        lintDisplayer.displayClear(view.scimoz,
                            view.document.languageObj.indicatorBits);
                    }
                },
                0, _lintDisplayer, this.view
            );
            this.lintResults = null;
        }
        this.errorString = null;
    } catch(ex) {
        _log.exception(ex);
    }
}



// Notify of a change in this view's check status/state.
this.lintBuffer.prototype._notify = function()
{
    _log.debug("LintBuffer["+this.view.title+"]._notify()");
    try {
        if (this.view == ko.views.manager.currentView) {
            try {
                _obsSvc.notifyObservers(
                    this.view, "current_view_check_status","");
            } catch(ex1) {
                // ignore
            }
        }
    } catch(ex2) {
        _log.exception(ex2);
    }
}

// Create a new koILintRequest instance and return it.
this.lintBuffer.prototype._createLintRequest = function(linterType)
{
    _log.debug("LintBuffer["+this.view.title+
                   "]._createLintRequest(linterType="+linterType+")");
    try {
        // Linters can't chdir to a remote URL, so don't pass in a working
        // directory unless it's local.
        var cwd = null;
        if (!this.view.document.isUntitled &&
            this.view.document.file.isLocal)
        {
            cwd = this.view.document.file.dirName;
        }

        var lr = Components.classes["@activestate.com/koLintRequest;1"].
                    createInstance(Components.interfaces.koILintRequest);
        lr.rid = this._lastRequestId;
        lr.document = this.view.document;
        lr.linterType = linterType;
        lr.uid = this.view.uid;
        lr.cwd = cwd;
        lr.lintBuffer = this;

        return lr;
    } catch(ex) {
        _log.exception(ex);
    }
    return null;
}


// Return an appropriate koILinter contract ID for the current language.
// If there isn't one, return null.
this.lintBuffer.prototype._getLinterCID = function()
{
    _log.debug("LintBuffer["+this.view.title+"]._getLinterCID()");
    try {
        var cid = null;
        var linterLanguageService = this.view.document.languageObj.
            getLanguageService(Components.interfaces.koILinterLanguageService);
        if (linterLanguageService) {
            cid = linterLanguageService.linterCID;
        }
        return cid;
    } catch(ex) {
        _log.exception(ex);
    }
    return null;
}



//---- public lint interface

// Should be called in Komodo initialization.
this.initialize = function lint_initialize() {
    _log = ko.logging.getLogger("lint");
    //_log.setLevel(ko.logging.LOG_INFO);
    _log.info("lint_initialize()");
    try {
        _lintDisplayer = Components.classes["@activestate.com/koLintDisplayer;1"].
                         getService(Components.interfaces.koILintDisplayer);
        _lintSvc = Components.classes["@activestate.com/koLintService;1"].
                       getService(Components.interfaces.koILintService);
        _obsSvc = Components.classes["@mozilla.org/observer-service;1"].
                           getService(Components.interfaces.nsIObserverService);

        ko.main.addUnloadHandler(lint_finalize);
    } catch(ex) {
        _log.exception(ex);
    }
}


// This is registered to be called on Komodo shutdown by lint_initialize().
this.finalize = function lint_finalize() {
    _log.info("lint_finalize()");
    try {
        if (_lintSvc) {
            // free the lint manager
            _lintSvc.terminate();
            _lintSvc = null;
        }
    } catch(ex) {
        _log.exception(ex);
    }
}


this.jumpToNextLintResult = function lint_jumpToNextLintResult()
{
    try {
        _log.debug("lint_jumpToNextLintResult()");

        var view = ko.views.manager.currentView;
        if (!view) return;
        if (typeof(view.lintBuffer) == "undefined") return;

        // If there are no results, then say so.
        //   lintResults == null        -> inprogress
        //   lintResults.length == 0    -> ok
        //   lintResults.length > 0     -> errors/warnings
        var lintResults = view.lintBuffer.lintResults;
        if (view.lintBuffer.errorString) {
            ko.dialogs.alert(view.lintBuffer.errorString);
        } else if (!lintResults) {
            if (view.prefs.getBooleanPref("editUseLinting")) {
                ko.dialogs.alert("Syntax checking is currently in progress.");
            } else {
                ko.dialogs.alert("Automatic syntax checking disabled: shift-click on the icon to start.");                
            }
        } else if (! lintResults.getNumResults()) {
            ko.dialogs.alert("There are no syntax errors.");
        } else {
            // Determine the current position.
            var next = lintResults.getNextResult(view.currentLine,
                                                 view.currentColumn);
            //dump("next lint result: line="+next.lineStart+", column="+
            //     next.columnStart+"\n");

            var pos = view.scimoz.positionAtColumn(next.lineStart-1,
                                                   next.columnStart-1);
            view.scimoz.ensureVisibleEnforcePolicy(next.lineStart-1);
            view.scimoz.gotoPos(pos);
            view.scimoz.selectionStart = pos;
            view.scimoz.selectionEnd = pos;
        }
    } catch(ex) {
        _log.exception(ex);
    }
}


this.doRequest = function lint_doRequest() {
    try {
        var view = ko.views.manager.currentView;
        view.lintBuffer._clearResults();
        view.lintBuffer._notify();
        view.lintBuffer._issueRequest()
    } catch (e) {
        log.exception(e);
    }
}

this.clearResults = function lint_clearResults() {
    try {
        var view = ko.views.manager.currentView;
        view.lintBuffer._clearResults();
        StatusBar.ClearCheck(view);
    } catch (e) {
        log.exception(e);
    }
}

this.doClick = function lint_doClick(event) {
    try {
        if (event.shiftKey) ko.lint.doRequest();
    } catch (e) {
        log.exception(e);
    }
}

}).apply(ko.lint);

var LintBuffer = ko.lint.lintBuffer;
var lint_initialize = ko.lint.initialize;
var lint_finalize = ko.lint.finalize;
var lint_jumpToNextLintResult = ko.lint.jumpToNextLintResult;
var lint_doRequest = ko.lint.doRequest;
var lint_clearResults = ko.lint.clearResults;
var lint_doClick = ko.lint.doClick;

