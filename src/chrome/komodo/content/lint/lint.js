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
    
const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
const {XPCOMUtils} = Cu.import("resource://gre/modules/XPCOMUtils.jsm", {});

var _log = ko.logging.getLogger("lint");
//_log.setLevel(ko.logging.LOG_INFO);

var lazy = {};

XPCOMUtils.defineLazyGetter(lazy, "lintSvc", function()
    Cc["@activestate.com/koLintService;1"]
        .getService(Components.interfaces.koILintService));

var _linterLanguageNames = {};
//---- The new LintBuffer class (replacement for jsLintBuffer)
//
// There is one of these for each Komodo 'editor' view. It is responsible
// for all JS-side linting handling for that view.
//

// This object belongs to ko.lint, so extensions can add their prefs to
// the observer.

const PERL_LIST = ["Perl"];
const PYTHON_LIST = ["Python", "Django"];
const PYTHON3_LIST = ["Python3"];
const PHP_LIST = ["PHP"];
const RUBY_LIST = ["Ruby"];
const JS_LIST = ["JavaScript"];
const NODEJS_LIST = ["Node.js"];
const JS_NODEJS_LIST = [JS_LIST[0], NODEJS_LIST[0]];
const HTML_LIST = ["HTML", "XML", "HTML5"];
const CSS_LIST = ["CSS", "SCSS", "Less"];
const MIN_DELAY = 200; // msec

var global_pref_observer_topics = {
    "editUseLinting" : null,
    "lintDelay": null,
    "lintEOLs" : null,
    "endOfLine" : null,
    "lintShowResultsInline" : null,
    "lintClearOnTextChange" : null,
    "nodejsDefaultInterpreter" : NODEJS_LIST,
    "perlDefaultInterpreter" : PERL_LIST,
    "perl_lintOption" : PERL_LIST,
    "perl_lintOption_perlCriticLevel" : PERL_LIST,
    "perl_lintOption_includeCurrentDirForLinter" : PERL_LIST,
    "perl_lintOption_disableBeginBlocks" : PERL_LIST,
    "pythonDefaultInterpreter" : PYTHON_LIST,
    "python3DefaultInterpreter" : PYTHON3_LIST,
    "lint_python_with_pylint" : PYTHON_LIST,
    "lint_python_with_pep8" : PYTHON_LIST,
    "lint_python_with_pyflakes" : PYTHON_LIST,
    "lint_python_with_standard_python" : PYTHON_LIST,
    "lint_python3_with_standard_python" : PYTHON3_LIST,
    "lint_python3_with_pylint3" : PYTHON3_LIST,
    "lint_python3_with_pep83" : PYTHON3_LIST,
    "lint_python3_with_pyflakes3" : PYTHON3_LIST,
    "pylint_checking_rcfile" : PYTHON_LIST,
    "pep8_checking_rcfile" : PYTHON_LIST,
    "pep83_checking_rcfile" : PYTHON3_LIST,
    "lint_python_with_pychecker" : PYTHON_LIST,
    "pychecker_checking_rcfile" : PYTHON_LIST,
    "phpDefaultInterpreter" : PHP_LIST,
    "phpConfigFile" : PHP_LIST,
    "rubyDefaultInterpreter" : RUBY_LIST,
    "ruby_lintOption" : RUBY_LIST,

    "javascriptExtraPaths": JS_LIST,
    "nodejsExtraPaths": NODEJS_LIST,
    "phpExtraPaths": PHP_LIST,
    "pythonExtraPaths": PYTHON_LIST,
    "python3ExtraPaths": PYTHON3_LIST,
    "perlExtraPaths": PERL_LIST,
    "rubyExtraPaths": RUBY_LIST,
    "tclExtraPaths": ["Tcl"],

    "lintJavaScriptEnableWarnings" : JS_NODEJS_LIST,
    "lintJavaScriptEnableStrict" : JS_NODEJS_LIST,
    "lintJavaScript_SpiderMonkey" : JS_NODEJS_LIST,
    "lintWithJSHint" : JS_NODEJS_LIST,
    "jshintOptions" : JS_NODEJS_LIST,
    "lintWithJSLint" : JS_NODEJS_LIST,
    "jslintOptions" : JS_NODEJS_LIST,
    "jslint_linter_specific" : JS_NODEJS_LIST,
    "jslint_linter_chooser" : JS_NODEJS_LIST,
    "jslint_linter_specific_version" : JS_NODEJS_LIST,
    "jshint_linter_specific" : JS_NODEJS_LIST,
    "jshint_linter_chooser" : JS_NODEJS_LIST,
    "lint_coffee_script" : ["CoffeeScript"],
    "sassLinterType" : ["Sass"],
    "sassDefaultInterpreter" : ["Sass"],
    "scssLinterType" : ["SCSS"],
    "scssDefaultInterpreter" : ["SCSS"],
    "lessLinterType" : ["Less"],
    "lessDefaultInterpreter" : ["Less"],
    "lint_css_komodo_parser_enabled": CSS_LIST,
    "lint_css_mozilla_parser_enabled": CSS_LIST,

    "lintHTMLTidy" : HTML_LIST,
    "lintHTML5Lib" : ["HTML5"],
    "lintHTML_CheckWith_Perl_HTML_Lint" : HTML_LIST,
    "lintHTML_CheckWith_Perl_HTML_Tidy" : HTML_LIST,
    "defaultHTMLDecl": HTML_LIST,
    "tidy_errorlevel" : HTML_LIST,
    "tidy_accessibility" : HTML_LIST,
    "tidy_configpath" : HTML_LIST
};

var global_pref_observer_topic_names = [];
for (var key in global_pref_observer_topics) {
    if (global_pref_observer_topics.hasOwnProperty(key)) {
        global_pref_observer_topic_names.push(key);
    }
}

this.updateDocLintPreferences = function(prefset, preferenceName) {
    try {
        var views = ko.views.manager.getAllViews();
        for (var i = 0; i < views.length; i++) {
            var view = views[i];
            if (view.prefs === prefset && view.lintBuffer) {
                // Add all prefs in case the buffer's language changes
                prefset.prefObserverService.
                    addObserverForTopics(view.lintBuffer, 1,
                                         [preferenceName],
                                         false);
            }
        }
    } catch(ex) {
        _log.exception("updateLintPreferences: error: " + ex);
    }
};

this.addLintPreference = function(preferenceName, subLanguageNameList) {
    // This function gives extensions access to the lint pref observer system
    // @param preferenceName String
    // @param subLanguageNameList [array of String], like ["Python", "Django"]
    // returns: nothing
    global_pref_observer_topics[preferenceName] = subLanguageNameList;
    global_pref_observer_topic_names.push(preferenceName);
    
    try {
        var views = ko.views.manager.getAllViews();
        for (var i = 0; i < views.length; i++) {
            var view = views[i];
            if (view.lintBuffer) {
                // Add all prefs in case the buffer's language changes
                ko.prefs.prefObserverService.
                    addObserverForTopics(view.lintBuffer, 1,
                                         [preferenceName],
                                         false);
                view.prefs.prefObserverService.
                    addObserverForTopics(view.lintBuffer, 1,
                                         [preferenceName],
                                         false);
            }
        }
    } catch(ex) {
        _log.exception("addLintPreference: error: " + ex);
    }
};

this.lintBuffer = function LintBuffer(view) {
    _log.info("LintBuffer["+view.title+"].constructor()");
    try {
        this.view = view;
        var effectivePrefs = this.view.koDoc.getEffectivePrefs();
        this.lintingEnabled = effectivePrefs.getBooleanPref("editUseLinting");
        this.lintDelay = effectivePrefs.getLongPref("lintDelay");
        if (this.lintDelay < MIN_DELAY) {
            this.lintDelay = MIN_DELAY;
        }
        this._lintClearOnTextChange = effectivePrefs.getBooleanPref("lintClearOnTextChange");
        this.lintResults = null;
        this.errorString = null;
        // Bug 97965: Let the displayer know when we're recalculating
        // the current set of lint markers.
        this.recalculatingResults = false;
        this._lastRequestId = 0; // used to ensure only the last request is used
        this._lastTimeoutId = 0;
        // this._lastTimeoutId is always set to the current setTimeout function
        // this._lastRequestId is set to any setTimeout IDs that get to fire.

        var globalPrefObserverService = ko.prefs.prefObserverService;
        globalPrefObserverService.addObserverForTopics(this,
                                                       global_pref_observer_topic_names.length,
                                                       global_pref_observer_topic_names, false);

        var viewPrefObserverService = this.view.prefs.prefObserverService;
        viewPrefObserverService.addObserverForTopics(this,
                                                     global_pref_observer_topic_names.length,
                                                     global_pref_observer_topic_names, false);

        // Used by the lintDisplayer
        this.handleScroll = null;
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
        lazy.lintSvc.cancelPendingRequests(this.view.uid);
        this._clearResults();

        var viewPrefObserverService = this.view.prefs.prefObserverService;
        viewPrefObserverService.removeObserverForTopics(this,
                                                        global_pref_observer_topic_names.length,
                                                        global_pref_observer_topic_names);

        var globalPrefObserverService = ko.prefs.prefObserverService;
        globalPrefObserverService.removeObserverForTopics(this,
                                                          global_pref_observer_topic_names.length,
                                                          global_pref_observer_topic_names);

        this.view = null; // drop reference to the view
    } catch(ex) {
        _log.exception(ex);
    }
}

this.lintBuffer.prototype.usingSubLanguage = function(subLanguageList) {
    var currentSubLanguages = this.view.languageObj.getSubLanguages({});
    var langName = this.view.koDoc.language;
    if (currentSubLanguages.indexOf(langName) === -1) {
        currentSubLanguages.push(langName);
    }
    return subLanguageList.
        map(function(langName) currentSubLanguages.indexOf(langName)).
        filter(function(val) val >= 0).length > 0;
}

// nsIObserver.observe()
this.lintBuffer.prototype.observe = function(subject, topic, data)
{
    //_log.debug("LintBuffer["+this.view.title+"].observe: subject="+
    //               subject+", topic="+topic+", data="+data);
                
    try {
        var setupRequest = false;
        if (this.lintingEnabled
            && global_pref_observer_topics[topic]) {
            if (this.usingSubLanguage(global_pref_observer_topics[topic])) {
                // Generic way of determining if the current buffer is affected
                // by the changed pref.
                _log.info("LintBuffer[" + this.view.title
                          + "].observed "
                          + global_pref_observer_topics[topic].join("/")
                          + "pref change, re-linting");
                setupRequest = true;
            }
        } else {
            switch (topic) {
                case "lintDelay":
                this.lintDelay = this.view.koDoc.getEffectivePrefs().getLongPref("lintDelay");
                if (this.lintDelay <= 0) {
                    this.lintDelay = MIN_DELAY;
                }
                // FALLTHRU
                case "lintEOLs":
                case "lintShowResultsInline":
                case "endOfLine":
                _log.info("LintBuffer["+this.view.title+
                          "].observed EOL pref change, re-linting");
                if (this.lintingEnabled) {
                    setupRequest = true;
                }
                break;
                case "editUseLinting":
                _log.info("LintBuffer["+this.view.title+
                          "].observe: lintingEnabled="+lintingEnabled);
                var lintingEnabled = this.view.koDoc.getEffectivePrefs().getBooleanPref("editUseLinting");
                if (lintingEnabled != this.lintingEnabled) {
                    // Do whatever must be done when the lintingEnabled state changes.
                    this.lintingEnabled = lintingEnabled;
                    if (lintingEnabled) {
                        setupRequest = true;
                    } else {
                        lazy.lintSvc.cancelPendingRequests(this.view.uid);
                        this._clearResults();
                        this._notify();
                    }
                }
                break;
                case "lintClearOnTextChange":
                this._lintClearOnTextChange = this.view.koDoc.getEffectivePrefs().getBooleanPref("lintClearOnTextChange");
                break;
            }
        }
        if (setupRequest && this.view == ko.views.manager.currentView) {
            this.request("language changed");
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
    if (!this.lintingEnabled) {
        //dump("<< lintBuffer.request, !this.lintingEnabled\n");
        return;
    }
    if (!this._lastTimeoutId) {
        // Bug 97965: don't update markers until a new set is created.
        this.recalculatingResults = true;
        if (this._lintClearOnTextChange || reason == "language changed") {
            // Bug 97965: clear the markers at the start of an editing session,
            // not when the new set of markers are ready.
            this._clearResults();
        }
    }
    // clearTimeout ignores timeout ID 0
    clearTimeout(this._lastTimeoutId);
    this._lastTimeoutId = setTimeout(this._continueRequest.bind(this),
                                     this.lintDelay, reason);
};

this.lintBuffer.prototype._continueRequest = function(reason /* = "" */) {
    this._lastRequestId = this._lastTimeoutId;
    this._lastTimeoutId = 0;
    if (!this.view) {
        // buffer has been closed.
        return;
    }
    if (typeof(reason) == "undefined" || reason == null) reason = "";
    _log.info("LintBuffer["+this.view.title+"].request(reason='"+
                  reason+"')");
    try {
        lazy.lintSvc.cancelPendingRequests(this.view.uid);
        ko.lint.displayer.cancelPendingItems(this);

        this._notify();
        this._issueRequest();
    } catch(ex) {
        _log.exception(ex);
    }
}


// koILintBuffer.reportResults()
this.lintBuffer.prototype.reportResults = function(request)
{
    if (!this.view || !this.view.koDoc) {
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
                ko.lint.displayer.display(this, this.lintResults);
                this.recalculatingResults = false;
            }
            if (this.view == ko.views.manager.currentView) {
                // Bug 100198: At startup the editor is sometimes ready before
                // klint is receiving events, so verify that klint has been loaded.
                ko.widgets.getWidgetAsync('klint_tabpanel',
                    function() {
                        xtk.domutils.fireEvent(window, "current_view_lint_results_done");
                    });
            }
        }
    } catch(ex) {
        _log.exception(ex);
    }
}


// Actually issue a lint request to the linting backend.
this.lintBuffer.prototype._issueRequest = function(alwaysLint)
{
    _log.info("LintBuffer["+this.view.title+"]._issueRequest()");
    if (typeof(alwaysLint) === "undefined") {
        alwaysLint = false;
    }
    try {
        var linterLanguageName = this._getLinterLanguageName();
        if (linterLanguageName === null) {
            // No linter for this language.
            return;
        }
        var lr = this._createLintRequest(linterLanguageName);
        if (lr) {
            lr.alwaysLint = alwaysLint;
            lazy.lintSvc.addRequest(lr);
        }
    } catch(ex) {
        if (ex.message.indexOf("Internal Error creating a linter with CID") >= 0) {
            _log.debug("No linter for component " + linterLanguageName);
        } else {
            _log.exception(ex);
        }
    }
}


// Clear the current lint results, if there are any.
this.lintBuffer.prototype._clearResults = function()
{
    _log.debug("LintBuffer["+this.view.title+"]._clearResults()");
    try {
        if (this.view) {
            // .displayClear() has to be called in a timeout to avoid
            // re-entrance into scintilla: we are already mostly likely in
            // a scintilla onModified event handler (linting is most
            // common requested for a buffer modification).
            window.setTimeout(
                function(view) {
                    if (view && view.koDoc) {
                        ko.lint.displayer.displayClear(view.scimoz);
                        xtk.domutils.fireEvent(window, "current_view_lint_results_done");
                    }
                },
                0, this.view
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
            xtk.domutils.fireEvent(window, "current_view_check_status");
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
        if (!this.view.koDoc.isUntitled &&
            this.view.koDoc.file.isLocal)
        {
            cwd = this.view.koDoc.file.dirName;
        }

        var lr = Components.classes["@activestate.com/koLintRequest;1"].
                    createInstance(Components.interfaces.koILintRequest);
        lr.rid = this._lastRequestId;
        lr.koDoc = this.view.koDoc;
        this._colouriseIfNecessary(this.view);
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

this.lintBuffer.prototype._colouriseIfNecessary = function(view) {
    // We have to finish lexing the doc in the main thread, because
    // if the linter is relying on styles to determine the segments,
    // it can't get scimoz to finish colourising on a background thread.
    if (this.view.koDoc.languageObj.supportsSmartIndent != "XML"
        && this.view.koDoc.language != "PHP") {
        // non-HTML linters don't use sub-language styles
        return;
    }
    // Do we need to colourise from the last line down?
    // First, are there lines after the last visible line?
    var koDoc = this.view.koDoc;
    var scimoz = this.view.scimoz;
    var bufferLength = scimoz.length;
    var lineCount = scimoz.lineCount;
    var nextActualLine = scimoz.docLineFromVisible(scimoz.firstVisibleLine
                                                   + scimoz.linesOnScreen) + 2;
    if (nextActualLine >= lineCount) {
        // All text has been colourised.
        return;
    }
    // Is there unstyled text starting on the next page?
    var pos = scimoz.positionFromLine(nextActualLine);
    var transitionPts = {}, numTransitionPts = {};
    koDoc.getLanguageTransitionPoints(pos, bufferLength, transitionPts, numTransitionPts);
    transitionPts = transitionPts.value;
    numTransitionPts = numTransitionPts.value;
    if (numTransitionPts > 3 ||
        (numTransitionPts == 3 && transitionPts[1] <  transitionPts[2])) {
        // lots of numTransitionPts below
        return;
    }
    // Are they all zero bytes?
    var stopPoint = Math.min(transitionPts[1], pos + 1000);
    if (stopPoint < pos) {
        // Not enough chars left to colourise
        return;
    }
    var styledBytes = scimoz.getStyledText(pos, stopPoint, {});
    if (styledBytes.indexOf("<".charCodeAt(0)) == -1) {
        // There are no "<" chars (or styles with that num below, so leave
        return;
    }
    // At least there's a "<" (or a non-zero style)
    // in the text we found.
    for (var i = 1; i < styledBytes.length; i += 2) {
        if (styledBytes[i] != 0) {
            return;
        }
    }
    scimoz.colourise(pos, bufferLength);
}

// If the current doc's language defines a terminal linter, return the
// name of the language.  Otherwise return null.
this.lintBuffer.prototype._getLinterLanguageName = function()
{
    var languageName = this.view.koDoc.language;
    if (!(languageName in _linterLanguageNames)) {
        var res = null;
        try {
            var cid = lazy.lintSvc.getLinter_CID_ForLanguage(languageName);
            if (cid) {
                res = languageName;
            }
        } catch(ex) {
            _log.error("_getLinterLanguageName: " + ex);
        }
        _linterLanguageNames[languageName] = res;
    }
    return _linterLanguageNames[languageName];
}

this.lintBuffer.prototype.canLintLanguage = function() {
    var languageName = this.view.koDoc.language;
    return (languageName in _linterLanguageNames
            && _linterLanguageNames[languageName] !== null);
}


//---- public lint interface

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
            require("notify/notify").send("Running syntax check...", "lint");
            ko.lint.doRequest();
        } else if (! lintResults.getNumResults()) {
            require("notify/notify").send("There are no syntax errors.", "lint");
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


// ko.lint.doRequest never delays.  Several other modules call it.
this.doRequest = function lint_doRequest(alwaysLint) {
    try {
        var view = ko.views.manager.currentView;
        if (!view || view.getAttribute("type") != "editor") {
            // Current view not lintable.
            return;
        } else if (!view.lintBuffer) {
            _log.debug("lint.doRequest: view "
                       + ((view.koDoc && view.koDoc.displayPath) || "<unnamed>")
                       + " has no lintBuffer");
            return;
        }
        if (this._lintClearOnTextChange) {
            this._clearResults();
        }
        view.lintBuffer._notify();
        view.lintBuffer._issueRequest(alwaysLint);
    } catch (e) {
        _log.exception(e);
    }
}

this.clearResults = function lint_clearResults() {
    try {
        var view = ko.views.manager.currentView;
        view.lintBuffer._clearResults();
        view.lintBuffer._notify();
    } catch (e) {
        _log.exception(e);
    }
}

this.doClick = function lint_doClick(event) {
    try {
        if (event.shiftKey) ko.lint.doRequest();
    } catch (e) {
        _log.exception(e);
    }
}

this.initializeGenericPrefs = function(prefset) {
    if (typeof(prefset) == "undefined" || prefset instanceof Event) {
        prefset = ko.prefs;
    }
    var ids = prefset.getPrefIds();
    var idNames = ids.filter(function(x) x.indexOf("genericLinter:") == 0);
    idNames.forEach(function(prefName) {
        var langName = prefName.substr(prefName.indexOf(":") + 1);
        if (!(prefName in global_pref_observer_topics)) {
            ko.lint.addLintPreference(prefName, [langName]);
        }
    });
}

}).apply(ko.lint);

window.addEventListener('komodo-ui-started', ko.lint.initializeGenericPrefs, false);
