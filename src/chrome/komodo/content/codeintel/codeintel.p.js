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
 * JavaScript-side control of the Code Intelligence system in Komodo
 * (code browsing, autocomplete and calltip triggering).
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (ko.codeintel) {
    ko.logging.getLogger('').warn("ko.codeintel was already loaded, re-creating it.\n");
}
ko.codeintel = {};


(function() {

    const Ci = Components.interfaces;
    const Cc = Components.classes;
    var {XPCOMUtils} = Components.utils.import("resource://gre/modules/XPCOMUtils.jsm", {});

    var log = ko.logging.getLogger("codeintel_js");
    //log.setLevel(ko.logging.LOG_DEBUG);

    var _codeintelSvc = Components.classes["@activestate.com/koCodeIntelService;1"]
                              .getService(Components.interfaces.koICodeIntelService);

    // ko.codeintel.isActive is true iff the Code Intel system is enabled,
    // initialized, and active.
    this.isActive = false;


    // Internal helper routines.

    /* Upgrade the codeintel database, if necessary.
     * This should only be done once per Komodo *app* (not once per window).
     */
    function _CodeIntel_UpgradeDBIfNecessary()
    {
        log.debug("_CodeIntel_UpgradeDBIfNecessary()");
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                            getService(Components.interfaces.koILastErrorService);
        var needToUpgrade = null;
        try {
            needToUpgrade = _codeintelSvc.needToUpgradeDB();
        } catch(ex) {
            var err = lastErrorSvc.getLastErrorMessage();
            if (!err) {
                err = "<no error message: see 'pystderr.log' error log in your Komodo user data dir>";
            }
            ko.dialogs.alert("Could not upgrade your Code Intelligence Database "+
                         "because: "+err+". Your database will be backed up "+
                         "and a new empty database will be created.", null,
                         "Code Intelligence Database");
            _codeintelSvc.resetDB();
            return;
        }
    
        if (needToUpgrade) {
            var upgrader = Components.classes["@activestate.com/koCodeIntelDBUpgrader;1"]
                            .createInstance(Components.interfaces.koIShowsProgress);
            ko.dialogs.progress(upgrader,
                            "Upgrading Code Intelligence Database.",
                            "Code Intelligence",
                            false);  // cancellable
        }
    }
    
    
    function _CodeIntel_PreloadDBIfNecessary()
    {
        log.debug("_CodeIntel_PreloadDBIfNecessary()");
        try {
            if (! ko.prefs.getBooleanPref("codeintel_have_preloaded_database")) {
                var preloader = Components.classes["@activestate.com/koCodeIntelDBPreloader;1"]
                                .createInstance(Components.interfaces.koIShowsProgress);
                ko.dialogs.progress(preloader,
                                "Pre-loading Code Intelligence Database. "
                                    +"This process will improve the speed of first "
                                    +"time autocomplete and calltips. It typically "
                                    +"takes less than a minute.",
                                "Code Intelligence",
                                true,   // cancellable
                                null,   // cancel warning
                                false); // modal
            }
        } catch(e) {
            log.exception(e);
        }
    }
    
    //function CodeIntel_UpdateCatalogZoneIfNecessary()
    //{
    //    log.debug("CodeIntel_UpdateCatalogZoneIfNecessary()");
    //    try {
    //        if (! ko.prefs.getBooleanPref("codeintel_have_preloaded_database")) {
    //            var preloader = Components.classes["@activestate.com/koCodeIntelDBPreloader;1"]
    //                            .createInstance(Components.interfaces.koIShowsProgress);
    //            ko.dialogs.progress(preloader,
    //                            "Pre-loading Code Intelligence Database. "
    //                                +"This process will improve the speed of first "
    //                                +"time autocomplete and calltips. It typically "
    //                                +"takes less than a minute.",
    //                            "Code Intelligence",
    //                            true,   // cancellable
    //                            null,   // cancel warning
    //                            false); // modal
    //        }
    //    } catch(e) {
    //        log.exception(e);
    //    }
    //}
    
    
    function _CodeIntel_ActivateWindow()
    {
        log.debug("_CodeIntel_ActivateWindow()");
        try {
            // Setup services.
            //TODO: Race condition on startup here! If two Komodo windows
            //      open quickly then they'll both start the "upgrade if
            //      necessary".
            if (! _codeintelSvc.isBackEndActive) {
                try {
                    _CodeIntel_UpgradeDBIfNecessary();
                    _codeintelSvc.activateBackEnd();
                    _CodeIntel_PreloadDBIfNecessary();
                } catch(ex2) {
                    log.exception(ex2);
                    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                        getService(Components.interfaces.koILastErrorService);
                    var err = lastErrorSvc.getLastErrorMessage();
                    ko.dialogs.internalError(err, ex2+"\n\n"+err, ex2);
                    _CodeIntel_DeactivateWindow();
                    return;
                }
            }
    
            ko.codeintel.isActive = true;
        } catch(ex) {
            log.exception(ex);
        }
    }
    
    
    function _CodeIntel_DeactivateWindow(isShuttingDown)
    {
        log.debug("_CodeIntel_DeactivateWindow()");
        try {
            ko.codeintel.isActive = false;
        } catch(ex) {
            log.exception(ex);
        }
    }

    //---- public routines
    
    this.initialize = function CodeIntel_InitializeWindow()
    {
        log.debug("initialize()");
        try {
            if (ko.prefs.getBooleanPref("codeintel_enabled")) {
                _CodeIntel_ActivateWindow();
            } else {
                _CodeIntel_DeactivateWindow();
            }
            ko.main.addWillCloseHandler(ko.codeintel.finalize);
        } catch(ex) {
            log.exception(ex);
        }
    }
    
    this.finalize = function CodeIntel_FinalizeWindow()
    {
        log.debug("finalize()");
        try {
            _CodeIntel_DeactivateWindow(true /* shutting down */);
        } catch(ex) {
            log.exception(ex);
        }
    }

    this.is_cpln_lang = function CodeIntel_is_cpln_lang(lang)
    {
        return _codeintelSvc.is_cpln_lang(lang);
    }

    this.is_citadel_lang = function CodeIntel_is_citadel_lang(lang)
    {
        return _codeintelSvc.is_citadel_lang(lang);
    }

    this.is_xml_lang = function CodeIntel_is_xml_lang(lang)
    {
        return _codeintelSvc.is_xml_lang(lang);
    }

    this.scan_document = function CodeIntel_scan_document(koDoc, linesAdded, forcedScan)
    {
        log.debug("scan_document()");
        try {
            _codeintelSvc.scan_document(koDoc, linesAdded, !forcedScan);
        } catch(ex) {
            log.exception(ex);
        }
    }

    /**
     * Link the current Komodo project with the provided codeintel buffer.
     *
     * Note: See bug 88841 for details on why this is necessary.
     */
    this.linkCurrentProjectWithBuffer = function ko_codeintel_linkProject(ciBuffer) {
        // Hack: Assign the project on this buffer. Would prefer if this was
        //       managed by the codeintel system itself, but at present there is
        //       a disconnect between projects (which are per window) and the
        //       codeintel service (which is a singleton).
        var currentProject = ko.projects.manager.currentProject;
        if (currentProject) {
            ciBuffer.project = currentProject;
        }
    }

    /**
     * Trigger a completion (i.e. an autocomplete or calltip session)
     * if appropriate.
     */
    this.trigger = function ko_codeintel_trigger(view) {

        var scimoz = view.scimoz;
        var ciBuffer = view.koDoc.ciBuf;

        this.linkCurrentProjectWithBuffer(ciBuffer);

        var trg = ciBuffer.trg_from_pos(scimoz.currentPos, true);
        if (!trg) {
            // Do nothing.
        } else if (view.scintilla.autocomplete.active && view._ciLastTrg &&
                   trg.is_same(view._ciLastTrg))
        {
            // Bug 55378: Don't re-eval trigger if same one is showing.
            // PERF: Consider passing _ciLastTrg to trg_from_pos() if
            //       autoCActive to allow to abort early if looks like
            //       equivalent trigger will be generated.
        } else {
            // PERF: Should we re-use controllers? Need a pool then?
            //       Try to save and re-use ctlr on each view.
            var ctlr = Components.classes["@activestate.com/koCodeIntelEvalController;1"].
                        createInstance(Components.interfaces.koICodeIntelEvalController);
            ctlr.set_ui_handler(view.ciCompletionUIHandler);
            view._ciLastTrg = trg;
            ciBuffer.async_eval_at_trg(trg, ctlr);
        }
    }


    //---- the UI manager for completions (autocomplete/calltip) in a view
    // NOTE: Should be able to move this completion UI handler stuff to
    //       Python-side. Hence would cleanly fit into
    //       class KoCodeIntelEvalController.

    this.CompletionUIHandler = function CodeIntelCompletionUIHandler(view)
    {
        log.debug("CompletionUIHandler(view)");
        try {
            this.view = view;
            var scimoz = view.scimoz;
            var ciBuf = this.view.koDoc.ciBuf;
            this.completionFillups = ciBuf.cpln_fillup_chars;
            this.stopChars = ciBuf.cpln_stop_chars;
            this.enableFillups = ko.prefs.getBooleanPref("codeintel_completion_auto_fillups_enabled");

            this._timeSvc = Components.classes["@activestate.com/koTime;1"].
                                getService(Components.interfaces.koITime);
            this._lastRecentPrecedingCompletionAttemptPos = null;
            this._lastRecentPrecedingCompletionAttemptTime = null;
            this._lastRecentPrecedingCompletionAttemptTimeout = 3.0;

            this.callTipStack = [];
            // Can't use scimoz.{autoC|callTip}PosStart() for this because (1)
            // there is a bug in .callTipPosStart();
            //      http://mailman.lyra.org/pipermail/scintilla-interest/2004-April/004272.html
            // and (2) the calltip display position might not be the trigger point
            // if the call region is multi-line.
            this._lastTriggerPos = null;
            this._defns = [];

            ko.prefs.prefObserverService
              .addObserver(this, "codeintel_completion_auto_fillups_enabled", 0);
        } catch(ex) {
            log.exception(ex);
        }
    }
    this.CompletionUIHandler.prototype.constructor = this.CompletionUIHandler;

    this.CompletionUIHandler.prototype.QueryInterface = XPCOMUtils.generateQI([
        Ci.koICodeIntelCompletionUIHandler,
        Ci.koIScintillaAutoCompleteListener,
        Ci.nsIObserver]);

    this.CompletionUIHandler.prototype.finalize = function() {
        log.debug("CompletionUIHandler.finalize()");
        var view = this.view;
        this.view = null;
        try {
            ko.prefs.prefObserverService
              .removeObserver(this, "codeintel_completion_auto_fillups_enabled");
            var autoc = view.scintilla.autocomplete;
            if (autoc.listener && autoc.listener === this) {
                autoc.listener = null;
            }
        } catch(ex) {
            log.exception(ex);
        }    
    }

    /**
     * A mapping of autocomplete type -> image url
     * Note that this is public and expected to be modified by extensions/scripts
     */
    Object.defineProperty(this.CompletionUIHandler.prototype, "types", {
        get: function() {
            if ("_types" in this) {
                return this._types;
            }
            this._types = {
                "class":        "chrome://komodo/skin/images/cb_class.png",
                "function":     "chrome://komodo/skin/images/cb_function.png",
                "module":       "chrome://komodo/skin/images/cb_module.png",
                "interface":    "chrome://komodo/skin/images/cb_interface.png",
                "namespace":    "chrome://komodo/skin/images/cb_namespace.png",
                "variable":     "chrome://komodo/skin/images/cb_variable.png",
                "$variable":    "chrome://komodo/skin/images/cb_variable_scalar.png",
                "@variable":    "chrome://komodo/skin/images/cb_variable_array.png",
                "%variable":    "chrome://komodo/skin/images/cb_variable_hash.png",
                "directory":    "chrome://komodo/skin/images/cb_directory.png",
                "constant":     "chrome://komodo/skin/images/cb_constant.png",
                // XXX: Need a better image (a dedicated keyword image)
                "keyword":      "chrome://komodo/skin/images/cb_interface.png",

                "element":      "chrome://komodo/skin/images/cb_xml_element.png",
                "attribute":    "chrome://komodo/skin/images/cb_xml_attribute.png",

                // Added for CSS, may want to have a better name/images though...
                "value":        "chrome://komodo/skin/images/cb_variable.png",
                "property":     "chrome://komodo/skin/images/cb_class.png",
                "pseudo-class": "chrome://komodo/skin/images/cb_interface.png",
                "rule":         "chrome://komodo/skin/images/cb_function.png",
            };
            return this._types;
        },
        configurable: true,
        enumerable: true,
    });

    this.CompletionUIHandler.prototype.observe = function(prefSet, prefName, prefSetID)
    {
        //log.debug("observe pref '"+prefName+"' change on '"+
        //                      this.view.koDoc.displayPath+"'s completion UI handler");
        try {
            if (prefName == "codeintel_completion_auto_fillups_enabled") {
                this.enableFillups = ko.prefs.getBooleanPref(prefName);
            } else {
                log.error('CompletionUIHandler: observed unexpected pref name "' +
                          prefName + '"');
            }
        } catch(ex) {
            log.exception(ex);
        }
    };
    
    
    // Helpers to determine the start pos for "triggerPrecedingCompletion".
    //
    // The Problem: For repeated triggerPrecedingCompletion() calls we want to
    // backtrack until the language service says "that's all". However, if
    // completion at one of these triggers fails we don't have an
    // autocomplete/calltip UI point and which to start the next look back.
    //
    // Solution: A time-based heuristic. If we've *recently* done a
    // triggerPrecedingCompletion() and found a trigger, then start from one
    // before that position. This is independent of the trigger evaluation
    // succeeding so should be more robust.
    this.CompletionUIHandler.prototype._setLastRecentPrecedingCompletionAttemptPos = function(pos)
    {
        this._lastRecentPrecedingCompletionAttemptPos = pos;
        this._lastRecentPrecedingCompletionAttemptTime = this._timeSvc.time();
        this._timeSvc = Components.classes["@activestate.com/koTime;1"].
                            getService(Components.interfaces.koITime);
    }
    this.CompletionUIHandler.prototype._getLastRecentPrecedingCompletionAttemptPos = function(pos)
    {
        if (this._lastRecentPrecedingCompletionAttemptPos == null)
            return null;
    
        var now = this._timeSvc.time();
        if (now - this._lastRecentPrecedingCompletionAttemptTime
            > this._lastRecentPrecedingCompletionAttemptTimeout) {
            this._lastRecentPrecedingCompletionAttemptPos = null;
            return null;
        } else {
            return this._lastRecentPrecedingCompletionAttemptPos;
        }
    }
    
    this.CompletionUIHandler.prototype.triggerPrecedingCompletion = function()
    {
        log.debug("CompletionUIHandler."+
                              "triggerPrecedingCompletion()");
        try {
            // Determine start position.
            var autoc = this.view.scintilla.autocomplete;
            var scimoz = this.view.scimoz;
            var startPos = null;
            if (scimoz.callTipActive() || autoc.active) {
                startPos = this._lastTriggerPos - 1;
            } else {
                var lastRecentAttemptPos = this._getLastRecentPrecedingCompletionAttemptPos();
                if (lastRecentAttemptPos != null) {
                    startPos = lastRecentAttemptPos - 1;
                } else {
                    startPos = scimoz.currentPos;
                }
            }
            var ciBuf = this.view.koDoc.ciBuf;
            ko.codeintel.linkCurrentProjectWithBuffer(ciBuf);
            // Hand off to language service to find and display.
            var trg = ciBuf.preceding_trg_from_pos(startPos,
                                                      scimoz.currentPos);
            if (trg) {
                this._setLastRecentPrecedingCompletionAttemptPos(trg.pos);
                var ctlr = 
                    Components.classes["@activestate.com/koCodeIntelEvalController;1"].
                    createInstance(Components.interfaces.koICodeIntelEvalController);
                ctlr.set_ui_handler(this);
                ciBuf.async_eval_at_trg(trg, ctlr);
            } else if (typeof(ko.statusBar.AddMessage) != "undefined") {
                this._setLastRecentPrecedingCompletionAttemptPos(null);
                ko.statusBar.AddMessage("No preceding trigger point within range of current position.",
                                     "codeintel", 3000, false);
            }
        } catch(ex) {
            log.exception(ex);
        }
    
    }

    this.CompletionUIHandler.prototype.onAutoCompleteEvent = function CUIH_onAutoCompleteEvent(controller, event) {
        var view = this.view;
        var scintilla = view.scintilla;
        var scimoz = view.scimoz;
        var autoc = scintilla.autocomplete;
        if (!autoc.active) {
            switch (event.type) {
                case "completion":
                case "popuphiding":
                case "popuphidden":
                    break;
                default:
                    // ignore anything else when autoc is no longer active
                    log.debug("ignoring event, autoc inactive");
                    return;
            }
        }

        var triggerPos = this._lastTriggerPos;
        var curPos = scimoz.currentPos;
        var oldText = "";
        if (curPos > triggerPos) {
            oldText = scimoz.getTextRange(triggerPos, curPos);
        }

        var doShowPopup = (function doShowPopup() {
            // Remember the currently selected item and text to compare
            var lastCompletion = autoc.selectedText;
            // Select items in the list as the user types. Do this on a
            // delay in order to let scintilla accept the key first. (Note
            // that this may also be a paste or other ways of inserting, as long as
            // it's in one of the commands listed above)
            setTimeout((function(){
                log.debug("showing popup");
                var triggerPos = this._lastTriggerPos;
                var curPos = scimoz.currentPos;
                if (curPos < triggerPos) {
                    // we went back past the trigger, let's die
                    log.debug("current position " + curPos + " is less than trigger " + triggerPos +
                              ", closing popup");
                    autoc.close();
                    return;
                }
                var typedAlready = scimoz.getTextRange(triggerPos, curPos);
                if (this.enableFillups &&
                    typedAlready.length == oldText.length + 1 &&
                    typedAlready.substr(0, oldText.length) == oldText &&
                    this.completionFillups.indexOf(typedAlready[oldText.length]) != -1)
                {
                    // only one character was added, and it was a fillup character
                    autoc.applyCompletion(this._lastTriggerPos, scimoz.currentPos,
                                          lastCompletion + typedAlready[oldText.length]);
                    return;
                }
                // abort if any of the "fillups" have been typed since
                for each (var ch in typedAlready) {
                    if (this.completionFillups.indexOf(ch) != -1) {
                        log.debug("aborting autocomplete at " + triggerPos +
                                  ": fillup character typed: '" + ch + "'");
                        autoc.close();
                        return;
                    }
                }
                // Show the completions UI.
                this._lastPrefix = typedAlready;
                autoc.show(triggerPos, curPos, triggerPos, typedAlready);
            }).bind(this), 0);
        }).bind(this);

        if (event.type === "focus") {
            // Ugly hack: scimoz needs to keep accepting key presses while the
            // autocomplete popup is actually focused.  This needs to be done in
            // the 'focus' event (instead of, say, 'popupshown') because that is
            // the first event that occurs; otherwise we can end up losing keys.
            scimoz.isFocused = true;
            // Check if the text has changed between the time we asked the popup
            // to show and when the time it did; if yes, try again.
            if (oldText !== this._lastPrefix) {
                log.debug("new text " + JSON.stringify(oldText) + " does not match old text " +
                          JSON.stringify(this._lastPrefix) + ", retriggering");
                autoc.close();
                // check for any stop characters - if there are, we should
                // give up rather than show the popup incorrectly
                for each (let ch in oldText) {
                    if (this.stopChars.indexOf(ch) !== -1) {
                        log.debug("found stop char '" + ch + "' in text, aborting");
                        return;
                    }
                }
                setTimeout(doShowPopup, 1);
                return;
            }
        } else if (event.type === "command") {
            // the user selected the item with the mouse
            autoc.applyCompletion(this._lastTriggerPos, scimoz.currentPos);
            return;
        } else if (event.type === "completion") {
            // completion was applied; re-trigger codeintel
            if (this._retriggerOnCompletion) {
                ko.codeintel.trigger(view);
            }
            return;
        } else if (event.type == "popuphiding") {
            scintilla.suppressSoftCharHardeningOnFocus = true;
            return;
        } else if (event.type == "popuphidden") {
            scintilla.suppressSoftCharHardeningOnFocus = false;
            return;
        }
        if (event.type !== "keydown" && event.type !== "keypress") {
            // we don't care about non-key events
            return;
        }

        var completionKeyCodes = [KeyEvent.DOM_VK_RETURN, KeyEvent.DOM_VK_ENTER, KeyEvent.DOM_VK_TAB];
        if (completionKeyCodes.indexOf(event.keyCode) !== -1) {
            // keys that should trigger autocompletion (but only on keydown,
            // not again in keypress)
            // log.debug(event.type + ": key " + event.keyCode + "(" +
            //           Object.keys(KeyEvent).filter(function(n)KeyEvent[n] == event.keyCode) +
            //           ") is a force-completion key; eating it");
            if (event.type === "keydown") {
                // we need to wait to apply the completion, in order to make
                // sure we don't close the popup too early - we still need to
                // capture the corresponding keypress event.
                setTimeout(autoc.applyCompletion.bind(autoc,
                                                      this._lastTriggerPos,
                                                      scimoz.currentPos,
                                                      autoc.selectedText),
                           0);
            }
            event.stopPropagation();
            event.preventDefault();
            return;
        }
        if (event.type !== "keypress") {
            return;
        }

        var keylabel = ko.keybindings.manager.event2keylabel(event,
                                                             undefined,
                                                             event.type === "keypress");
        var command = ko.keybindings.manager.key2command[keylabel];

        if (/cmd_vim_/.test(command) && gVimController && gVimController.enabled) {
            // this is a vim command; check vim state
            switch (gVimController.mode) {
                case gVimController.constructor.MODE_INSERT:
                case gVimController.constructor.MODE_OVERTYPE:
                case gVimController.constructor.MODE_REPLACE_CHAR:
                    // Ignore the command; we're in the wrong mode for Vi-mode
                    // to actually execute this command
                    command = undefined;
            }
        }

        switch (command) {
            case undefined: // no mapping, e.g. normal latin keypress
            case "cmd_backSmart":
            case "cmd_back":
            case "cmd_paste":
                // don't close autocomplete on these
                break;
            default:
                // doing something interesting - e.g. opening a dialog, cursor
                // navigation, etc
                log.debug("Unknown command " + command + ", closing");
                autoc.close();
                return;
        }

        var newChar = String.fromCharCode(event.charCode);
        // check for fillup chars
        if (this.enableFillups &&
            this.completionFillups.indexOf(newChar) != -1)
        {
            // Adding a new fillup character (and there's no command)
            log.debug("Fillup character '" + newChar +
                      "' detected, applying fillup '" + autoc.selectedText + "'");
            autoc.applyCompletion(this._lastTriggerPos, scimoz.currentPos,
                                  autoc.selectedText);
            return;
        }

        // check for stop chars
        if (this.stopChars.indexOf(newChar) !== -1) {
            autoc.close();
        } else {
            doShowPopup();
        }
    };
    
    this.CompletionUIHandler.prototype._setAutoCompleteInfo = function(
        completions, types, trg)
    {
        var triggerPos = trg.pos;
        log.debug("CompletionUIHandler.setAutoCompleteInfo"+
                              "(triggerPos="+triggerPos+")");
        try {
            // If the trigger is no longer relevant, then drop the completions.
            // - if the current position is before the trigger pos
            var scimoz = this.view.scimoz;
            var scintilla = this.view.scintilla;
            var curPos = scimoz.currentPos;
            if (curPos < triggerPos) {
                log.info("aborting autocomplete at "+triggerPos+
                                     ": cursor is before trigger position");
                return;
            }
            // - if the line changed
            var curLine = scimoz.lineFromPosition(curPos);
            var triggerLine = scimoz.lineFromPosition(triggerPos);
            if (curLine != triggerLine) {
                log.debug("aborting autocomplete at "+triggerPos+
                                      ": current line number changed");
                return;
            }
            //XXX Should also abort if the trigger character was changed, e.g.
            //       foo.<BS>bar
            //    Could do this by passing in the Trigger object (and storing
            //    what the trigger char is on it).
    
            // abort if any of the "fillups" have been typed since
            var numTypedAlready = curPos - triggerPos;
            var ch;
            for (var i = triggerPos; i < curPos; i++) {
                ch = scimoz.getWCharAt(i);
                if (this.completionFillups.indexOf(ch) != -1) {
                    log.debug("aborting autocomplete at "+triggerPos+
                                          ": fillup character typed: '"+ch+"'");
                    return;
                }
            }
    
            // Send out a DOM event.
            var data = {
                // TODO: Would like to add the array of completion items here.
                'trg': trg
            };
            xtk.domutils.fireDataEvent(this.view, "codeintel_autocomplete_showing", data);

            // Show the completions UI.
            this._lastTriggerPos = triggerPos;
            this._retriggerOnCompletion = trg.retriggerOnCompletion;
            var autoc = scintilla.autocomplete;
            autoc.listener = this;
            autoc.reset();
            autoc.addColumn(Ci.koIScintillaAutoCompleteController.COLUMN_TYPE_IMAGE,
                            types.map((function(t)this.types[t]||null).bind(this)),
                            types.length);
            autoc.addColumn(Ci.koIScintillaAutoCompleteController.COLUMN_TYPE_TEXT,
                            completions, completions.length, true);
            var typedAlready = scimoz.getTextRange(triggerPos, curPos);
            this._lastPrefix = typedAlready;
            scintilla.autocomplete.show(triggerPos, curPos, triggerPos,
                                        typedAlready);
        } catch(ex) {
            log.exception(ex);
        }
    }

    this.CompletionUIHandler.prototype._setCallTipInfo = function(
        calltip, trg, explicit)
    {
        var triggerPos = trg.pos;
        log.debug("CompletionUIHandler.setCallTipInfo"+
                              "(calltip, triggerPos="+triggerPos+
                              ", explicit="+explicit+")");
        try {
            var scimoz = this.view.scimoz;
            var curPos = scimoz.currentPos;
            if (!explicit) {
                // If the trigger is no longer relevant, then drop the calltip.
                // - if the current position is before the trigger pos
                if (curPos < triggerPos) {
                    log.info("aborting calltip at "+triggerPos+
                                         ": cursor is before trigger position");
                    return;
                }
                // - if the current position is outside the call region
                //   c.f. http://kd.nas/kd-0100.html#autocomplete-and-calltips
                var hltStartObj = new Object();
                var hltEndObj = new Object();
                var ciBuf = this.view.koDoc.ciBuf;
                ciBuf.curr_calltip_arg_range(
                    triggerPos, calltip, curPos, hltStartObj, hltEndObj);
                var hltStart = hltStartObj.value;
                var hltEnd = hltEndObj.value;
                if (hltStart == -1) {
                    log.info("aborting calltip at "+triggerPos+
                                         ": cursor is outside call region");
                    return;
                }
            }
    
            // Show the callip.
            if (scimoz.callTipActive()) {
                scimoz.callTipCancel();
            }
            this._lastTriggerPos = triggerPos;
    
            // Ensure the calltip line width and number of calltip lines shown
            // is not more than the user wants to see.
            var max_line_width = ko.prefs.getLongPref("codeintel_calltip_max_line_width");
            var max_lines = ko.prefs.getLongPref("codeintel_calltip_max_lines");
            var textUtils = Components.classes["@activestate.com/koTextUtils;1"]
                                .getService(Components.interfaces.koITextUtils);
            calltip = textUtils.break_up_lines(calltip, max_line_width);
            var calltip_lines = calltip.split(/\r\n|\n|\r/g);
            if (calltip_lines.length > max_lines) {
                calltip_lines = calltip_lines.slice(0, max_lines);
            }
            calltip = calltip_lines.join("\n");
    
            // Ensure the calltip is displayed relative to the current
            // cursor position - bug 87587.
            var curLine = scimoz.lineFromPosition(curPos);
            var callTipLine = scimoz.lineFromPosition(triggerPos);
            if (callTipLine != curLine) {
                var triggerColumn = scimoz.getColumn(triggerPos);
                triggerPos = scimoz.positionAtColumn(curLine, triggerColumn);
            }
    
            this.view.scintilla.autocomplete.close();
            scimoz.callTipShow(triggerPos, calltip);
            scimoz.callTipSetHlt(hltStart, hltEnd);
            var callTipItem = {"triggerPos": triggerPos, "calltip": calltip};
            this.callTipStack.push(callTipItem);
        } catch(ex) {
            log.exception(ex);
        }
    }
    
    this.CompletionUIHandler.prototype.updateCallTip = function() {
        log.debug("CompletionUIHandler.updateCallTip()");
        try {
            var scimoz = this.view.scimoz;
            if (! scimoz.callTipActive()) {
                // The calltip may get cancelled in various other places so
                // we have to make sure that the callTipStack here doesn't
                // grow unboundedly.
                this.callTipStack = [];
                return;
            }
    
            var curPos = scimoz.currentPos;
            var curLine = scimoz.lineFromPosition(curPos);
            var callTipItem = this.callTipStack[this.callTipStack.length-1];
            var triggerPos = callTipItem["triggerPos"];
            var calltip = callTipItem["calltip"];
            var callTipPos, triggerColumn;
    
            // Determine if we should cancel the calltip.
            var cancel = curPos < triggerPos; // cancel if cursor before trigger
            var region, hltStart, hltEnd;
            if (!cancel) {
                var hltStartObj = new Object();
                var hltEndObj = new Object();
                var ciBuf = this.view.koDoc.ciBuf;
                ciBuf.curr_calltip_arg_range(
                    triggerPos, calltip, curPos, hltStartObj, hltEndObj);
                hltStart = hltStartObj.value;
                hltEnd = hltEndObj.value;
                cancel = hltStart == -1;  // cancel if cursor out of call region
            }
    
            // Cancel if required and fallback to previous calltip, if any.
            if (cancel) {
                // Cancel the current call tip.
                scimoz.callTipCancel();
                this.callTipStack.pop();
    
                // Start the calltip one up in the stack, if there is one.
                if (this.callTipStack.length) {
                    callTipItem = this.callTipStack[this.callTipStack.length-1];
                    triggerPos = callTipItem["triggerPos"];
                    calltip = callTipItem["calltip"];
                    if (curPos >= triggerPos) {
                        triggerColumn = scimoz.getColumn(triggerPos);
                        callTipPos = scimoz.positionAtColumn(
                                curLine, triggerColumn);
                        this._lastTriggerPos = triggerPos;
                        this.view.scintilla.autocomplete.close();
                        scimoz.callTipShow(callTipPos, calltip);
                        this.updateCallTip();
                    }
                }
                return;
            }
    
            // If the cursor is on a different line from the current display
            // point then we need to move the calltip up or down.
            callTipPos = scimoz.callTipPosStart();
            var callTipLine = scimoz.lineFromPosition(callTipPos);
            if (callTipLine != curLine) {
                scimoz.callTipCancel();
                triggerColumn = scimoz.getColumn(triggerPos);
                var newCallTipPos = scimoz.positionAtColumn(curLine, triggerColumn);
                this._lastTriggerPos = triggerPos;
                this.view.scintilla.autocomplete.close();
                scimoz.callTipShow(newCallTipPos, calltip);
                //dump("XXX moved the calltip to "+newCallTipPos+
                //     ", now it is at "+scimoz.callTipPosStart()+"\n");
            }
    
            // Update the highlighting.
            scimoz.callTipSetHlt(hltStart, hltEnd);
        } catch(ex) {
            log.exception(ex);
        }
    }
    
    this.CompletionUIHandler.prototype._setDefinitionsInfo = function(
          defns, trg)
    {
        var triggerPos = trg.pos;
        log.debug("CompletionUIHandler.setDefinitionsInfo"+
                              "(triggerPos="+triggerPos+
                              ", num defns="+defns.length+")");
        try {
            if (defns && defns.length > 0) {
                /** @type {Components.interfaces.koICodeIntelDefinition} */
                var defn = defns[0];
                if (defns.length > 1) {
                    // Show choice of definitions, user can choose one
                    var args = new Object();
                    args.defns = defns;
                    window.openDialog("chrome://komodo/content/codeintel/ciDefinitionChoice.xul",
                                      "Komodo:ciDefinitionChoice",
                                      "chrome,resizable=yes,dialog=yes,close=yes,dependent=yes,modal=yes",
                                      args);
                    if (args.retval != "OK") {
                        return;
                    }
                    defn = args.selectedDefn;
                }
    
                // defn is a koICodeIntelDefinition XPCOM object
                // If it's got a path and line, open it up
                if (defn.path && defn.line) {
                    log.info("goto definition at "+triggerPos+
                                         ": found defn path '"+defn.path+
                                         "', line "+defn.line+".");
                    ko.history.note_curr_loc();
                    ko.views.manager.doFileOpenAtLineAsync(ko.uriparse.pathToURI(defn.path), defn.line);
                } else {
                    // No file, prompt to see if the user wants to view the online
                    // language help for this symbol - bug 65296.
                    var prompt = "Cannot show definition: symbol is defined " +
                                 "in the stdlib or in an API catalog. Would " +
                                 "you like to open the online language " +
                                 "help for this symbol?";
                    if (ko.dialogs.yesNo(prompt, "Yes", null, "Online Definition", "gotoDefinitionOnline") == 'Yes') {
                        ko.help.language(defn.name);
                    };
                    // No file information for ...
                    log.info("goto definition at "+triggerPos+
                                         ": no path information, as symbol is defined in a CIX.");
                    ko.statusBar.AddMessage("Cannot show definition: symbol is defined in the stdlib or in an API catalog.",
                                         "codeintel", 5000, true);
                }
            } else {
                log.info("goto definition at "+triggerPos+
                                     ": no results found.");
                ko.statusBar.AddMessage("No definition was found.'",
                                     "codeintel", 3000, true);
            }
        } catch(ex) {
            log.exception(ex);
        }
    }
    

    /**
     * a koINotification used for this completion UI
     */
    Object.defineProperty(this.CompletionUIHandler.prototype, "_notification", {
        get: function() {
            var nm = Cc["@activestate.com/koNotification/manager;1"]
                       .getService(Ci.koINotificationManager)
            var n = nm.createNotification("codeintel-status-message",
                                          ["codeintel"],
                                          1,
                                          window,
                                          Ci.koINotificationManager.TYPE_STATUS |
                                            Ci.koINotificationManager.TYPE_PROGRESS);
            n instanceof Ci.koIStatusMessage;
            n instanceof Ci.koINotificationProgress;
            n.maxProgress = Ci.koINotificationProgress.PROGRESS_NOT_APPLICABLE;
            n.log = true;
            n.timeout = 4000;
            return n;
        },
        configurable: true,
        enumerable: true,
    });
    
    // XXX WARNING these setXXX functions are called via sync proxy from a python
    // thread in koCodeIntel.py.  To prevent blocking on the ui thread, do
    // AS LITTLE AS POSSIBLE here, potentially defering to a window.timeout
    // call.
    // Bug: http://bugs.activestate.com/show_bug.cgi?id=65188
    
    this.CompletionUIHandler.prototype.setStatusMessage = function(
        msg, highlight)
    {
        setTimeout((function() {
            var n = this._notification;
            n.msg = msg;
            n.highlight = highlight;
            n.maxProgress = Ci.koINotificationProgress.PROGRESS_NOT_APPLICABLE;
            ko.statusBar.AddMessage(n);
        }).bind(this), 0);
    }
    
    this.CompletionUIHandler.prototype.setAutoCompleteInfo = function(
        completions, types, count, trg)
    {
        setTimeout((function () {this._setAutoCompleteInfo(completions, types, trg);}).bind(this),
                   0);
    }
    
    this.CompletionUIHandler.prototype.setCallTipInfo = function(
        calltip, trg, explicit)
    {
        window.setTimeout(function (me, calltip_, trg_, explicit_) {me._setCallTipInfo(calltip_, trg_, explicit_);},
                          1, this, calltip, trg, explicit);
    }
    
    this.CompletionUIHandler.prototype.setDefinitionsInfo = function(
        count, defns, trg)
    {
        window.setTimeout(function (me, defns_, trg_) {me._setDefinitionsInfo(defns_, trg_);},
                          1, this, defns, trg);
    }
    
}).apply(ko.codeintel);

window.addEventListener("load", ko.codeintel.initialize, false);

/**
 * @deprecated since 7.0
 */
ko.logging.globalDeprecatedByAlternative('gCodeIntelSvc', 'Components.classes["@activestate.com/koCodeIntelService;1"].getService(Components.interfaces.koICodeIntelService)');
ko.logging.globalDeprecatedByAlternative("gCodeIntelActive", "ko.codeintel.isActive");
ko.logging.globalDeprecatedByAlternative("CodeIntel_InitializeWindow", "ko.codeintel.initialize");
ko.logging.globalDeprecatedByAlternative("CodeIntel_FinalizeWindow", "ko.codeintel.finalize");
ko.logging.globalDeprecatedByAlternative("CodeIntelCompletionUIHandler", "ko.codeintel.CompletionUIHandler");
