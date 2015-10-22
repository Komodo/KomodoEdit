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

/**
 * Unified find controller - this handles both incremental search as well as
 * commands related to opening the find dialog
 */

xtk.include('controller');

ko.findcontroller = {};
(function() {

var locals = {};

XPCOMUtils.defineLazyGetter(locals, "PluralForm", function()
    Cu.import("resource://gre/modules/PluralForm.jsm").PluralForm);

XPCOMUtils.defineLazyGetter(locals, "bundle", function()
    Services.strings.createBundle("chrome://komodo/locale/library.properties"));

var _log = ko.logging.getLogger('find.controller');
//_log.setLevel(ko.logging.LOG_DEBUG);

function FindController(viewManager) {
    if (!(this instanceof FindController)) {
        // somebody called us, but not as a constructor
        _log.exception("FindController should be called as a constructor");
        throw("FindController should be called as a constructor");
    }
    this._viewManager = viewManager;
    this._incrementalSearchPattern = ''; // only used for incremental search
    this._lastIncrementalSearchText = ''; // only used for incremental search
    this._lastResult = false; // whether the last search was successful
    this._findSvc = Cc["@activestate.com/koFindService;1"]
                      .getService(Ci.koIFindService);
    var win = Components.utils.getGlobalForObject(this._viewManager);
    win.controllers.appendController(this);
    _log.debug("find controller initialized for " + viewManager);
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
FindController.prototype = new xtk.Controller();
FindController.prototype.constructor = FindController;

/**
 * Clean up
 */
FindController.prototype._destructor = function() {
    var win = Components.utils.getGlobalForObject(this._viewManager);
    win.controllers.removeController(this);
}

/**
 * Get the view we want to search in
 */
FindController.prototype.__defineGetter__("_currentView", function FindController_get__currentView() {
    var view = this._viewManager;
    if ("currentView" in this._viewManager) {
        // this may be a koIViewList with multiple views
        try {
            view = this._viewManager.currentView;
        } catch (ex) {
            if (ex == Components.results.NS_ERROR_NOT_IMPLEMENTED) {
                // This can happen if we got a basic view instead of a tabbed
                // view; ignore the exception, it's expected.
            } else {
                // unexpected
                _log.exception(ex);
                return null;
            }
        }
    }
    return view;
});

/**
 * Returns true if the view we want to search in exists and is the current view
 * in the view manager
 */
function viewIsCurrentView() {
    var currView = this._currentView;
    if (!(currView instanceof Ci.koIScintillaView)) return false;
    return currView && currView == ko.views.manager.currentView;
}

// cmd_find
FindController.prototype.is_cmd_find_enabled = function() {
    var currView = this._currentView;
    return currView &&
           currView == ko.views.manager.currentView &&
           currView.getAttribute("type") == "editor";
}

FindController.prototype.do_cmd_find = function() ko.launch.find();

// cmd_replace
FindController.prototype.is_cmd_replace_enabled = function() {
    return ko.views.manager.getAllViews().length != 0;
}

FindController.prototype.do_cmd_replace = function() ko.launch.replace();

FindController.prototype._cmd_findNextPrev = function(searchBackward) {
    if (this._currentView.findbar && this._currentView.findbar.controller === this) {
        // Special case for the incremental search - the find bar is active,
        // just do a searchAgain instead of trying to find the MRU.  See
        // bug 94120.
        this.searchAgain(searchBackward);
        return;
    }
    var pattern = ko.mru.get("find-patternMru");
    if (pattern) {
        var context = Cc["@activestate.com/koFindContext;1"]
                        .createInstance(Ci.koIFindContext);
        var findSvc = Cc["@activestate.com/koFindService;1"]
                        .getService(Ci.koIFindService);
        context.type = findSvc.options.preferredContextType;
        findSvc.options.searchBackward = searchBackward;
        ko.find.findNext(window, context, pattern);
    } else {
        ko.launch.find();
    }
};

// cmd_findNext
FindController.prototype.is_cmd_findNext_enabled = viewIsCurrentView;

FindController.prototype.do_cmd_findNext = function() {
    if (!viewIsCurrentView.call(this)) return;
    this._cmd_findNextPrev(false);
}

// cmd_findPrevious
FindController.prototype.is_cmd_findPrevious_enabled = viewIsCurrentView;

FindController.prototype.do_cmd_findPrevious = function()  {
    if (!viewIsCurrentView.call(this)) return;
    this._cmd_findNextPrev(true);
}

// cmd_findNextResult
FindController.prototype.is_cmd_findNextResult_enabled = viewIsCurrentView;

FindController.prototype.do_cmd_findNextResult = function() ko.findresults.nextResult();

// cmd_findNextFunction, cmd_findPreviousFunction, cmd_findAllFunctions

// Auxiliary function used by the find*Function(s) methods.
//
//  "searchType" is one of "next", "previous" or "all"
//
FindController.prototype._findFunction = function(searchType) {
    try {
        var language = this._currentView.koDoc.languageObj;
        var re = language.namedBlockRE;
        var namedBlockDescription = language.namedBlockDescription;
        if (re == null || re == '')
            return;

        // save some find options
        var patternType, caseSensitivity, searchBackward, matchWord;
        patternType = this._findSvc.options.patternType;
        caseSensitivity = this._findSvc.options.caseSensitivity;
        searchBackward = this._findSvc.options.searchBackward;
        matchWord = this._findSvc.options.matchWord;

        this._findSvc.options.patternType = Ci.koIFindOptions.FOT_REGEX_PYTHON;
        this._findSvc.options.caseSensitivity = Ci.koIFindOptions.FOT_SENSITIVE;
        this._findSvc.options.searchBackward = (searchType == "previous");
        this._findSvc.options.matchWord = false;

        var context = Cc["@activestate.com/koFindContext;1"]
                        .createInstance(Ci.koIFindContext);
        context.type = Ci.koIFindContext.FCT_CURRENT_DOC;
        if (searchType == "all") {
            ko.find.findAll(window, context, re, namedBlockDescription);
        } else {
            ko.find.findNext(window, context, re);
        }

        // restore saved find options
        this._findSvc.options.patternType = patternType;
        this._findSvc.options.caseSensitivity = caseSensitivity;
        this._findSvc.options.searchBackward = searchBackward;
        this._findSvc.options.matchWord = matchWord;
    }  catch (e) {
        _log.error(e);
    }
}

FindController.prototype.is_cmd_findNextFunction_enabled = function() {
    var view = this._currentView;
    return view && view.koDoc && view.koDoc.languageObj.namedBlockRE != '';
}

FindController.prototype.do_cmd_findNextFunction = function() {
    this._findFunction("next");
}

FindController.prototype.is_cmd_findPreviousFunction_enabled = function() {
    var view = this._currentView;
    return view && view.koDoc && view.koDoc.languageObj.namedBlockRE != '';
}

FindController.prototype.do_cmd_findPreviousFunction = function() {
    this._findFunction("previous");
}

FindController.prototype.is_cmd_findAllFunctions_enabled = function() {
    var view = this._currentView;
    return view && view.koDoc && view.koDoc.languageObj.namedBlockRE != '';
}

FindController.prototype.do_cmd_findAllFunctions = function() {
    this._findFunction("all");
}

/**
 * Check if incremental search is enabled
 * @see nsIController::isCommandEnabled
 */
FindController.prototype.is_cmd_startIncrementalSearch_enabled = function() {
    return this._currentView != null && this._currentView.getAttribute("type") == "editor";
}

/**
 * Find the next incremental search result
 * @see nsIController::doCommand
 */
FindController.prototype.do_cmd_startIncrementalSearch = function() {
    this._startIncrementalSearch(false);
}

/**
 * Check if incremental search (backwards) is enabled
 * @see nsIController::isCommandEnabled
 */
FindController.prototype.is_cmd_startIncrementalSearchBackwards_enabled = function() {
    return this._currentView != null && this._currentView.getAttribute("type") == "editor";
}

/**
 * Find the previous incremental search result
 * @see nsIController::doCommand
 */
FindController.prototype.do_cmd_startIncrementalSearchBackwards = function() {
    this._startIncrementalSearch(true);
}

/**
 * Set the search pattern type
 */
Object.defineProperty(FindController.prototype, "patternType", {
    get: function FindController_get_patternType() {
        return this._findSvc.options.patternType;
    },
    set: function FindController_set_patternType(val) {
        _log.debug("setting patternType to " + val +
                   "(was " + this._findSvc.options.patternType + ")");
        if (this._findSvc.options.patternType == val) {
            return;
        }
        this._findSvc.options.patternType = val;
        if (this._view) {
            // in incremental search
            this._view.findbar.patternType = val;
        }
    },
    enumerable : true,
    configurable : true
});

/**
 * mouse event handler for incremental search
 */
FindController.prototype._mouseHandlerBase = function (e) {
    var relatedTarget = null;
    if (e && e.type && e.type == "mousedown") {
        var isFindbar =
            (e.originalTarget == this._view.findbar) ||
            (e.originalTarget.compareDocumentPosition(this._view.findbar) & Node.DOCUMENT_POSITION_CONTAINS);
        if (isFindbar) {
            // The user clicked on the find bar or something in it; we don't
            // want to do anything here
            event.stopPropagation();
            return;
        }
    }
    this._stopIncrementalSearch("Clicked away", false);
};

/**
 * Focus event handler for incremental search
 * @note this should be bound to a FindController instance
 * @param event The focus event
 */
FindController.prototype._focusHandlerBase = function(e) {
    // look at the focused element, instead of what the event says, because we
    // shouldn't hide the find bar if the window itself gets focus without
    // changing the focused element
    var elem = document.commandDispatcher.focusedElement;

    if ((!this._view) ||
        (!elem) ||
        (elem == this._view.findbar) ||
        (this._view.findbar && (elem.compareDocumentPosition(this._view.findbar) & Node.DOCUMENT_POSITION_CONTAINS)))
    {
        // The user clicked on the find bar or something in it; we don't
        // want to do anything here
        return;
    }
    this._stopIncrementalSearch("Focus changed", false);
};


FindController.prototype._startIncrementalSearch = function(backwards) {
    if (!this._currentView || this._currentView.getAttribute("type") != "editor") {
        _log.error("Couldn't start incremental search with no focused scintilla", false);
        return;
    }
    _log.debug("Starting incremental search " + (backwards ? "backwards" : "forwards"));
    this._view = this._currentView;
    var scintilla = this._currentView.scintilla;
    
    var scimoz = scintilla.scimoz;
    this._view.findbar.controller = this;
    this._view.findbar.notFound = false;
    this._view.findbar.collapsed = false;
    this._view.findbar.setStatus(null);
    // canOpenDialog must be set after collapsed=false in order for the XBL
    // binding to apply early enough.
    this._view.findbar.canOpenDialog = (this._viewManager == ko.views.manager);
    this._mouseHandler = this._mouseHandlerBase.bind(this);
    scintilla.mouse_handler = this._mouseHandler;
    this._focusHandler = this._focusHandlerBase.bind(this);
    document.addEventListener("focus", this._focusHandler, true);
    this._incrementalSearchStartPos = Math.min(scimoz.currentPos, scimoz.anchor);
    var pattern = scimoz.selText;
    if (/\n/.test(pattern)) pattern = ""; // ignore multi-line selections
    this._incrementalSearchContext = Cc["@activestate.com/koFindContext;1"]
                                       .createInstance(Ci.koIFindContext);

    // bug 93040: If the pattern is empty, use the last search text
    pattern = pattern || this._lastIncrementalSearchText;

    // Save original find settings
    this._origFindOptions = {
        "searchBackward":  this._findSvc.options.searchBackward,
        "matchWord":       this._findSvc.options.matchWord,
        "patternType":     this._findSvc.options.patternType,
        "caseSensitivity": this._findSvc.options.caseSensitivity
    };

    // Clear the highlight now because we're starting a new search
    ko.find.highlightClearAll(this._view.scimoz);

    // Apply new find settings
    this._findSvc.options.searchBackward = backwards;
    this._findSvc.options.matchWord = false;
    this.patternType = Number(ko.prefs.getStringPref('isearchType'));
    this.highlightTimeout = Number(ko.prefs.getLongPref('isearchHighlightTimeout')) || undefined;
    // manually force the findbar pattern type to match reality
    this._view.findbar.patternType = this.patternType;
    this._findSvc.options.caseSensitivity = Number(ko.prefs.getStringPref('isearchCaseSensitivity'));
    this._view.findbar.caseSensitivity = this._findSvc.options.caseSensitivity;
    this._incrementalSearchContext.type = this._findSvc.options.FCT_CURRENT_DOC;
    this._incrementalSearchPattern = pattern;
    this._lastIncrementalSearchText = pattern;

    this._view.findbar.text = pattern;
    // Set focus after setting the textbox value, otherwise the history popup
    // can get confused with the old values.  See bug 93105.
    this._view.findbar.focus();

    if (pattern) {
        this._view.findbar.selectText();
        // we have something selected; highlight the other occurrences without
        // moving the cursor, please
        this._lastResult =
            ko.find.highlightAllMatches(scimoz,
                                        this._incrementalSearchContext,
                                        pattern,
                                        this.highlightTimeout);
    } else {
        this._lastResult = false;
    }
    _log.debug("_startIncrementalSearch: pattern=" +
               JSON.stringify(pattern) + ", lastResult=" + this._lastResult);
}

FindController.prototype._stopIncrementalSearch = function(why, highlight) {
    _log.debug("stopping incremental search (" + why + ")");
    if (this._incrementalSearchPattern && this._lastResult) {
        // Found something; force add to the MRU.
        ko.mru.add("find-patternMru", this._incrementalSearchPattern, true)
    }
    _log.debug("lastResult: " + this._lastResult + " pattern: " +
               JSON.stringify(this._incrementalSearchPattern));
    if (this._origFindOptions) {
        // Save the incremental search settings
        ko.prefs.setStringPref('isearchType', this.patternType);
        ko.prefs.setStringPref('isearchCaseSensitivity', this.caseSensitivity);

        // Restore original find settings
        for each (let key in Object.keys(this._origFindOptions)) {
            _log.debug("restoring " + key + " to " + this._origFindOptions[key]);
            this._findSvc.options[key] = this._origFindOptions[key];
        }
        this._origFindOptions = null;
    }
    // Don't automatically add things to the MRU; we do that in searchAgain if
    // needed, or just above if we found something last time.
    this._incrementalSearchPattern = '';

    var view = this._view;
    if (!view) return;

    // clean up event handlers
    if (view.scintilla.mouse_handler == this._mouseHandler) {
        view.scintilla.mouse_handler = null;
    }
    document.removeEventListener("focus", this._focusHandler, true);
    this._focusHandler = null;

    var elem = document.commandDispatcher.focusedElement;
    if ((!elem) ||
        (elem == view.findbar) ||
        (elem.compareDocumentPosition(this._view.findbar) & Node.DOCUMENT_POSITION_CONTAINS))
    {
        // the focus is in the find bar; it gets confused if we send more key
        // events its way, so move the focus to its scintilla instead.
        view.scintilla.focus();
    }

    // clean up the find bar
    view.findbar.controller = null;
    view.findbar.collapsed = true;
    this._view = null;
};

/**
 * Convert this incremental search to a Find dialog
 */
FindController.prototype.convertToDialog = function() {
    // throw away the original find options, it's all going into the dialog
    this._origFindOptions = null;
    // save the pattern
    var pattern = this._incrementalSearchPattern;
    // abort the incremental search
    this._stopIncrementalSearch(null, false);
    // Open the find dialog
    ko.launch.find(pattern);
};


/**
 * Start an incremental search (or update the current one with more text)
 * @param pattern The pattern to search for
 */
FindController.prototype.search = function(pattern, highlight) {
    var scimoz = this._view.scintilla.scimoz;
    this._lastIncrementalSearchText = pattern;
    this._incrementalSearchPattern = pattern;
    var oldStart = scimoz.selectionStart;
    var oldEnd = scimoz.selectionEnd;
    this._view.findbar.notFound = false;
    this._view.findbar.text = this._incrementalSearchPattern;
    scimoz.gotoPos(this._incrementalSearchStartPos-1);

    if (this._incrementalSearchPattern == '') {
        return;
    }

    ko.macros.recorder.undo();
    var findres = ko.find.findNext(
        this._view, this._incrementalSearchContext,
        this._incrementalSearchPattern, null,
        true,
        // Do NOT add this pattern to find MRU
        //  http://bugs.activestate.com/show_bug.cgi?id=27350
        // that will be done on stopping of interactive search.
        false,
        null,   // msgHandler
        highlight,
        this.highlightTimeout);
    if (! findres) {
        var prompt = locals.bundle.formatStringFromName("noOccurencesFound",
                                                  [this._incrementalSearchPattern], 1);
        scimoz.setSel(oldStart, oldEnd);
        this._view.findbar.notFound = true;
    }
    this._lastResult = findres;
};

/**
 * Find the next occurence of an incremental search result
 * @param {Boolean} isBackwards Whether the search should be conducted backwards
 */
FindController.prototype.searchAgain = function(isBackwards) {
    this._view.findbar.notFound = false;
    if (this._lastIncrementalSearchText == '')
        return;

    var findSessionSvc = Cc["@activestate.com/koFindSession;1"]
                           .getService(Ci.koIFindSession);
    var lastCount = findSessionSvc.GetNumFinds();

    if (this._incrementalSearchPattern == "") {
        // Second <Ctrl+I> after a non-search action
        this._incrementalSearchPattern = this._lastIncrementalSearchText;
        findSessionSvc.Reset();
    }
    this._view.findbar.text = this._incrementalSearchPattern;
    this._findSvc.options.searchBackward = isBackwards;
    var scimoz = this._view.scintilla.scimoz;
    var lastPos = (isBackwards ? Math.max : Math.min)(scimoz.anchor,
                                                      scimoz.currentPos);
    var findres = ko.find.findNext(this._view, this._incrementalSearchContext,
                                   this._incrementalSearchPattern,
                                   null, true,
                                   true); // add pattern to find MRU
    if (findres == false) {
        var text = locals.bundle.GetStringFromName("findNotFound");
        text = locals.PluralForm.get(lastCount, text).replace("#1", lastCount);
        this._view.findbar.setStatus("not-found", text);
        this._view.findbar.notFound = true;
    } else {
        this._incrementalSearchStartPos = this._view.scintilla.scimoz.currentPos;
        if (isBackwards) {
            var newPos = Math.max(scimoz.anchor, scimoz.currentPos);
            if (newPos > lastPos) {
                this._view.findbar.setStatus("wrapped", "findWrappedBackwards");
            } else {
                this._view.findbar.setStatus(null);
            }
        } else {
            var newPos = Math.min(scimoz.anchor, scimoz.currentPos);
            if (newPos < lastPos) {
                this._view.findbar.setStatus("wrapped", "findWrappedForwards");
            } else {
                this._view.findbar.setStatus(null);
            }
        }
    }
    this._lastResult = findres;
}

Object.defineProperty(FindController.prototype, "caseSensitivity", {
    get: function FindController_set_caseSensitivity() {
        return this._findSvc.options.caseSensitivity;
    },
    set: function FindController_set_caseSensitivity(val) {
        _log.debug("caseSensitivity := " + val +
                   " (was " + this._findSvc.options.caseSensitivity + ")");
        if (this._findSvc.options.caseSensitivity == val) {
            return;
        }
        this._findSvc.options.caseSensitivity = val;
        if (this._view) {
            // in incremental search
            this._view.findbar.caseSensitivity = val;
        }
    },
    enumerable : true,
    configurable : true
});

/**
 * keypress event handler for the find controller
 * @note this is called from the findbar's <handler>
 */
FindController.prototype._keyHandler = function FindController__keyHandler(event) {
    var keyMgr = ko.keybindings.manager;
    var eventkey = keyMgr.event2keylabel(event);
    var forwardKeys = ["cmd_startIncrementalSearch", "cmd_findNext"]
                      .map(keyMgr.command2keysequences, keyMgr);
    var backwardKeys = ["cmd_startIncrementalSearchBackwards", "cmd_findPrevious"]
                       .map(keyMgr.command2keysequences, keyMgr);

    // If the key sequence associated with incremental search is more than
    // one key long (i.e. the user has customized from the default <Ctrl+I>
    // to, say, <Ctrl+K, I>):
    // - if the last key is a Ctrl or Alt key, use it
    // - otherwise, disable the 'multiple hits' feature
    for each (var keyset in forwardKeys.concat(backwardKeys)) {
        for each (var keyseq in keyset || []) {
            // comma followed by space is a multiple key sequence delimiter
            // (as opposed to just comma, which could be the key itself)
            var keys = keyseq.split(", ");
            var lastkey = keys[keys.length - 1];
            if ((keys.length == 1 || /(?:Ctrl|Meta|Alt)\+/.test(lastkey)) &&
                eventkey == lastkey)
            {
                // we're hitting the same key as was last used to start the
                // search, so we just want to redo the search
                event.stopPropagation();
                event.preventDefault();
                this.searchAgain(backwardKeys.indexOf(keyset) > -1);
                return;
            }
        }
    }

    var cmdFindKeys = keyMgr.command2keysequences('cmd_find');
    if (cmdFindKeys.indexOf(eventkey) != -1) {
        // The user pressed the "open find dialog" key. (This will never
        // happen if it involves more than one key in the sequence,
        // because eventkey is only one key event)
        event.stopPropagation();
        event.preventDefault();
        this.convertToDialog();
        return;
    }

    // If we get here, this isn't trying to trigger a find. See if we need
    // to close the findbar.

    if (event.ctrlKey || event.altKey || event.metaKey) {
      // Some sort of chord; don't close the findbar, since it might
      // be stuff like paste.  We close on blur, anyway
      return;
    }

    switch (event.keyCode) {
      case 0:
        // regular keys have keycode 0 (and a charCode is used instead)
        // (fall through)

      // navigation
      case KeyEvent.DOM_VK_LEFT:       case KeyEvent.DOM_VK_RIGHT:
      case KeyEvent.DOM_VK_UP:         case KeyEvent.DOM_VK_DOWN:
      case KeyEvent.DOM_VK_HOME:       case KeyEvent.DOM_VK_END:
      case KeyEvent.DOM_VK_TAB:

      // editing
      case KeyEvent.DOM_VK_RETURN:
      case KeyEvent.DOM_VK_BACK_SPACE: case KeyEvent.DOM_VK_DELETE:
      case KeyEvent.DOM_VK_INSERT:

      // misc
      case KeyEvent.DOM_VK_CONTEXT_MENU:
      case KeyEvent.DOM_VK_CAPS_LOCK:

      // IME / input
      case KeyEvent.DOM_VK_CONVERT:    case KeyEvent.DOM_VK_NONCONVERT:
      case KeyEvent.DOM_VK_HANGUL:     case KeyEvent.DOM_VK_HANJA:
      case KeyEvent.DOM_VK_JUNJA:
      case KeyEvent.DOM_VK_KANA:       case KeyEvent.DOM_VK_KANJI:

        return;
    }

    // if we get here, it's a special key of some sort. Close the findbar.
    var scintilla = this._view.scintilla; // this will go away, hold on to it
    this._stopIncrementalSearch("User cancelled", false);
    scintilla.focus();
};

// expose the controller constructor
this.FindController = FindController;

// if we're the main window, wait for ko.views to be available and hook up a
// default incremental search controller
addEventListener("load", (function() {
    if (document.documentElement.id == "komodo_main") {
        setTimeout((function() {
            this.controller = new FindController(ko.views.manager);
            ko.main.addWillCloseHandler(this.controller._destructor, this.controller);
        }).bind(this), 0);
    }
}).bind(this), false);

}).apply(ko.findcontroller);
