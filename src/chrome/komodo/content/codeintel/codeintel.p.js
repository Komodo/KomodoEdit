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

    const {classes: Cc, interfaces: Ci, results: Cr, utils: Cu} = Components;
    var {XPCOMUtils} = Cu.import("resource://gre/modules/XPCOMUtils.jsm", {});

    var log = ko.logging.getLogger("codeintel.komodo.js");
    //log.setLevel(ko.logging.LOG_DEBUG);

    XPCOMUtils.defineLazyGetter(this, "_codeintelSvc", function()
        Cc["@activestate.com/koCodeIntelService;1"]
            .getService(Components.interfaces.koICodeIntelService));

    // ko.codeintel.isActive is true iff the Code Intel system is enabled,
    // initialized, and active.
    var _isActive = false;
    Object.defineProperty(this, "isActive", {
        get: function() _isActive,
        set: function(val) {
            if (val != _isActive) {
                if (val) {
                    _CodeIntel_ActivateWindow();
                } else {
                    _CodeIntel_DeactivateWindow();
                }
            }
        },
        enumerable: true,
        configurable: false,
    });


    // Internal helper routines.

    function _CodeIntel_ActivateWindow()
    {
        log.debug("_CodeIntel_ActivateWindow()");
        try {
            // Setup services.
            if (_isActive) {
                return;
            }
            if (ko.codeintel._codeintelSvc.isBackEndActive) {
                _isActive = true;
                window.dispatchEvent(new CustomEvent("codeintel_status_changed", { detail: { isActive: true } }));
            } else {
                try {
                    log.debug("Attempting to activate codeintel service");
                    // bug 100448: automatically wipe db if necessary.
                    ko.codeintel._codeintelSvc.activate(true);
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
        } catch(ex) {
            log.exception(ex);
        }
    }
    
    function _CodeIntel_activate_callback(result, data) {
        log.debug("codeintel activate callback: " + result.toString(16));
        if (result === Ci.koIAsyncCallback.RESULT_SUCCESSFUL) {
            _CodeIntel_ActivateWindow();
        } else if (result === Ci.koIAsyncCallback.RESULT_STOPPED) {
            // recoverable error
            _CodeIntel_DeactivateWindow();
        } else {
            // unrecoverable error
            _CodeIntel_DeactivateWindow();
            let message = String(data);
            if (data instanceof Ci.koIErrorInfo) {
                message = String(data.koIErrorInfo.message);
            }
            ko.dialogs.internalError("Failed to start codeintel",
                                     message);
        }
        if (!ko.main.windowIsClosing) {
            window.updateCommands("codeintel_enabled");
        }
    }

    function _CodeIntel_DeactivateWindow()
    {
        log.debug("_CodeIntel_DeactivateWindow()");
        try {
            if (!_isActive) {
                return;
            }
            _isActive = false;
            if (!ko.main.windowIsClosing) {
                window.updateCommands("codeintel_enabled");
                window.dispatchEvent(new CustomEvent("codeintel_status_changed", { detail: { isActive: false } }));
            }
        } catch(ex) {
            log.exception(ex);
        }
    }

    function handleError(msg) {
        require("notify/notify").send(msg, "codeintel", {priority: "error"});
    };


    //---- public routines
    
    const kObservedPrefNames = ["codeintel_highlight_variables_auto_mouse",
                                "codeintel_highlight_variables_auto_keyboard",
                                "codeintel_highlight_variables_auto_delay"];

    this.handleError = handleError;
    this.initialize = (function CodeIntel_InitializeWindow()
    {
        log.debug("initialize()");
        try {
            this._codeintelSvc.addActivateCallback(_CodeIntel_activate_callback);
            if (ko.prefs.getBooleanPref("codeintel_enabled")) {
                _CodeIntel_ActivateWindow();
            } else {
                _CodeIntel_DeactivateWindow();
            }
            ko.main.addWillCloseHandler(ko.codeintel.finalize);
            ko.prefs.prefObserverService
              .addObserverForTopics(this,
                                    kObservedPrefNames.length,
                                    kObservedPrefNames,
                                    true);
            for each (let pref in kObservedPrefNames) {
                // hook up things if necessary
                this.observe(null, pref, null);
            }
            this._controller = new CodeIntelController();
            window.controllers.appendController(this._controller);
        } catch(ex) {
            log.exception(ex);
        }
    }).bind(this);

    this.finalize = (function CodeIntel_FinalizeWindow()
    {
        log.debug("finalize()");
        try {
            this._codeintelSvc.removeActivateCallback(_CodeIntel_activate_callback);
            _CodeIntel_DeactivateWindow();
            let topView = ko.views.manager.topView;
            topView.removeEventListener("click",
                                        this._triggerHighlightVariableFromMouse,
                                        false);
            window.removeEventListener("editor_text_modified",
                                       this._triggerHighlightVariableFromKeyboard,
                                       false);
            if ("_triggerHighlightVariableFromKeyboard_timeout" in this) {
                clearTimeout(this._triggerHighlightVariableFromKeyboard_timeout);
            }
            window.controllers.removeController(this._controller);
            try {
                ko.prefs.prefObserverService
                  .removeObserverForTopics(this,
                                           kObservedPrefNames.length,
                                           kObservedPrefNames);
            } catch (ex) {
                /* ignore - this throws if things are not registered, which is a
                 * silly thing to be doing, since all we care is that they are
                 * no longer registered
                 */
            }
            if (this._last_highlight_async) {
                this._last_highlight_async.cancel(Cr.NS_ERROR_ABORT);
            }
        } catch(ex) {
            log.exception(ex);
        }
    }).bind(this);

    this.is_cpln_lang = function CodeIntel_is_cpln_lang(lang)
    {
        return this._codeintelSvc.is_cpln_lang(lang);
    }

    this.is_citadel_lang = function CodeIntel_is_citadel_lang(lang)
    {
        return this._codeintelSvc.is_citadel_lang(lang);
    }

    this.is_xml_lang = function CodeIntel_is_xml_lang(lang)
    {
        return this._codeintelSvc.is_xml_lang(lang);
    }

    this.scan_document = function CodeIntel_scan_document(koDoc, linesAdded, forcedScan)
    {
        log.debug("scan_document()");
        try {
            this._codeintelSvc.scan_document(koDoc, linesAdded, !forcedScan);
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

        log.debug("ko.codeintel.trigger: " + view);
        var scimoz = view.scimoz;
        var pos = scimoz.currentPos;

        if (view.scintilla.autocomplete.active) {
            // No need to trigger if it's already open (bug 100035)
            return;
        }

        var ciBuf = this._codeintelSvc.buf_from_koIDocument(view.koDoc);
        this.linkCurrentProjectWithBuffer(ciBuf);
        log.debug("Got buffer " + ciBuf);
        ciBuf.trg_from_pos(pos, true, function(trg) {
            if (!trg) {
                // Can't make a trigger from the buffer
                log.debug("No trigger found");
                return;
            }
            if (view.scintilla.autocomplete.active && view._ciLastTrg &&
                trg.is_same(view._ciLastTrg))
            {
                // Bug 55378: Don't re-eval trigger if same one is showing.
                // PERF: Consider passing _ciLastTrg to trg_from_pos() if
                //       autoCActive to allow to abort early if looks like
                //       equivalent trigger will be generated.
                log.debug("Not re-evaluating trigger");
                return;
            }
            view._ciLastTrg = trg;

            // Check if the trigger form is enabled:
            switch (trg.form) {
                case Ci.koICodeIntelTrigger.TRG_FORM_CPLN:
                    if (!ko.prefs.getBoolean("codeintel_completions_enabled", true)) {
                        return;
                    }
                    break;
                case Ci.koICodeIntelTrigger.TRG_FORM_CALLTIP:
                    if (!ko.prefs.getBoolean("codeintel_calltips_enabled", true)) {
                        return;
                    }
                    break;
                case Ci.koICodeIntelTrigger.TRG_FORM_DEFN:
                    if (!ko.prefs.getBoolean("codeintel_goto_definition_enabled", true)) {
                        return;
                    }
                    break;
            }

            // Evaluate the trigger.
            ciBuf.async_eval_at_trg(trg, view.ciCompletionUIHandler);
        }, handleError);

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

    this.CompletionUIHandler.prototype.done = function() {};

    /**
     * A mapping of autocomplete type -> image url
     * Note that this is public and expected to be modified by extensions/scripts
     */
    this.CompletionUIHandler.prototype.types = {
        "class":        "chrome://komodo/skin/images/codeintel/cb_class.svg",
        "function":     "chrome://komodo/skin/images/codeintel/cb_function.svg",
        "module":       "chrome://komodo/skin/images/codeintel/cb_module.svg",
        "interface":    "chrome://komodo/skin/images/codeintel/cb_interface.svg",
        "namespace":    "chrome://komodo/skin/images/codeintel/cb_namespace.svg",
        "trait":        "chrome://komodo/skin/images/codeintel/cb_trait.svg",
        "variable":     "chrome://komodo/skin/images/codeintel/cb_variable.svg",
        "$variable":    "chrome://komodo/skin/images/codeintel/cb_variable_scalar.svg",
        "@variable":    "chrome://komodo/skin/images/codeintel/cb_variable_array.svg",
        "%variable":    "chrome://komodo/skin/images/codeintel/cb_variable_hash.svg",
        "directory":    "chrome://komodo/skin/images/codeintel/cb_directory.svg",
        "constant":     "chrome://komodo/skin/images/codeintel/cb_constant.svg",
        // XXX: Need a better image (a dedicated keyword image)
        "keyword":      "chrome://komodo/skin/images/codeintel/cb_interface.svg",

        "element":      "chrome://komodo/skin/images/codeintel/cb_xml_element.svg",
        "attribute":    "chrome://komodo/skin/images/codeintel/cb_xml_attribute.svg",

        // Added for CSS, may want to have a better name/images though...
        "value":        "chrome://komodo/skin/images/codeintel/cb_variable.svg",
        "property":     "chrome://komodo/skin/images/codeintel/cb_class.svg",
        "pseudo-class": "chrome://komodo/skin/images/codeintel/cb_interface.svg",
        "rule":         "chrome://komodo/skin/images/codeintel/cb_function.svg",
        "id":           "chrome://komodo/skin/images/codeintel/cb_namespace.svg",
    };

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
            var ciBuf = ko.codeintel._codeintelSvc.buf_from_koIDocument(this.view.koDoc);
            ko.codeintel.linkCurrentProjectWithBuffer(ciBuf);
            // Hand off to language service to find and display.
            ciBuf.preceding_trg_from_pos(startPos, scimoz.currentPos, function(trg) {
                if (trg) {
                    this._setLastRecentPrecedingCompletionAttemptPos(trg.pos);
                    ciBuf.async_eval_at_trg(trg, this);
                } else if (typeof(ko.statusBar.AddMessage) != "undefined") {
                    this._setLastRecentPrecedingCompletionAttemptPos(null);
                    var msg = "No preceding trigger point within range of current position.";
                    require("notify/notify").send(msg, "codeintel", {priority: "warning"});
                }
            }.bind(this), handleError);
        } catch(ex) {
            log.exception(ex);
        }
    
    }

    this.CompletionUIHandler.prototype.onAutoCompleteEvent = function CUIH_onAutoCompleteEvent(controller, event)
    {
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
                if (curPos <= triggerPos) {
                    // We have reached the trigger position; close the trigger
                    // since none of the trigger text still exist.
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
                    let endPos = Math.max(this._lastTriggerPos + this._lastTriggerExtentLength,
                                          scimoz.currentPos);
                    autoc.applyCompletion(this._lastTriggerPos, endPos,
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
            let endPos = Math.max(this._lastTriggerPos + this._lastTriggerExtentLength,
                                  scimoz.currentPos);
            autoc.applyCompletion(this._lastTriggerPos, endPos);
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

        var completionKeyCodes = [KeyEvent.DOM_VK_RETURN, KeyEvent.DOM_VK_TAB];
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
                setTimeout((function() {
                    let endPos = Math.max(this._lastTriggerPos + this._lastTriggerExtentLength,
                                          scimoz.currentPos);
                    autoc.applyCompletion(this._lastTriggerPos, endPos,
                                          autoc.selectedText);
                }).bind(this), 0);
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
            let endPos = Math.max(this._lastTriggerPos + this._lastTriggerExtentLength,
                                  scimoz.currentPos);
            autoc.applyCompletion(this._lastTriggerPos, endPos,
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
            this.view.dispatchEvent(new CustomEvent("codeintel_autocomplete_showing", { bubbles: true, detail: data }));

            // Show the completions UI.
            this._lastTriggerPos = triggerPos;
            this._retriggerOnCompletion = trg.retriggerOnCompletion;
            this._lastTriggerExtentLength = trg.extentLength;
            var autoc = scintilla.autocomplete;
            autoc.listener = this;
            autoc.reset();
            autoc.addColumn(Ci.koIScintillaAutoCompleteController.COLUMN_TYPE_IMAGE,
                            types.map((function(t)this.types[t]||null).bind(this)),
                            types.length);
            autoc.addColumn(Ci.koIScintillaAutoCompleteController.COLUMN_TYPE_TEXT,
                            completions, completions.length, true);
            var typedAlready = (triggerPos >= curPos) ? "" : scimoz.getTextRange(triggerPos, curPos);
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

            var show_calltip = function (start, end) {
                log.debug("showing calltip at " + start + ", " + end);
                var curPos = scimoz.currentPos;
                // If the trigger is no longer relevant, then drop the calltip.
                // - if the current position is before the trigger pos
                if (curPos < triggerPos) {
                    log.info("aborting calltip at "+triggerPos+
                                         ": cursor is before trigger position");
                    return;
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
                var textUtils = Cc["@activestate.com/koTextUtils;1"]
                                    .getService(Ci.koITextUtils);
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
                scimoz.callTipSetHlt(start, end);
                var callTipItem = {"triggerPos": triggerPos, "calltip": calltip};
                this.callTipStack.push(callTipItem);
            }.bind(this);

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
                var ciBuf = this.view.koDoc.ciBuf;
                var callback = function(start, end) {
                    log.debug("Got calltip arg range: " + start + ", " + end);
                    if (start == -1) {
                        log.info("aborting calltip at "+triggerPos+
                                             ": cursor is outside call region");
                    } else {
                        show_calltip(start, end);
                    }
                }.bind(this);
                ciBuf.get_calltip_arg_range(triggerPos, calltip, curPos, callback, handleError);
            } else {
                show_calltip(0, 0);
            }

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
    
            var cancel = function () {
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
            }.bind(this);

            // Determine if we should cancel the calltip.
            if (curPos < triggerPos) {
                cancel();
                return;
            }

            var region;
            var ciBuf = this.view.koDoc.ciBuf;
            var callback = function(start, end) {
                if (start < 0) {
                    cancel();
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
                scimoz.callTipSetHlt(start, end);

            }.bind(this);
            ciBuf.get_calltip_arg_range(triggerPos, calltip, curPos, callback,
                                        handleError);
        } catch(ex) {
            log.exception(ex);
        }
    }
    
    this.CompletionUIHandler.prototype._setDefinitionsInfo = function(
          defns, trg)
    {
        var msg;
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
                    msg = "Cannot show definition: symbol is defined in the stdlib or in an API catalog.";
                    require("notify/notify").send(msg, "codeintel", {priority: "warning"});
                }
            } else {
                log.info("goto definition at "+triggerPos+
                                     ": no results found.");
                msg = "No definition was found.'";
                require("notify/notify").send(msg, "codeintel",
                                              {priority: "warning"});
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
            require("notify/notify").send(
                msg, "codeintel-verbose",
                {priority: highlight ? "warning" : "info"});
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


    /**
     * Highlight a variable
     * @param scimoz {Components.interfaces.koIScintillaView} The view to look in
     * @param reason {String} The reason for highlighting; one of "mouse",
     *      "keyboard", "manual".
     * @returns {Boolean} Whether highlight has _started_.  The actual
     *      highlighting is asynchronous and therefore whether any results have
     *      been found is unknown.
     */
    this.highlightVariable = (function CodeIntel_HighlightVariable(view, reason)
    {
        log.debug("ko.codeintel.highlightVariable: view=" + view + " reason=" + reason);
        if (this._last_highlight_async) {
            this._last_highlight_async.cancel(Cr.NS_ERROR_ABORT);
        }
        this._last_highlight_async = null;

        const INDICATOR = Ci.koILintResult.DECORATOR_TAG_MATCH_HIGHLIGHT;

        if (!view) {
            view = ko.views.manager.currentView;
        }
        if (!(view instanceof Ci.koIScintillaView)) {
            log.error("view is not a koIScintillaView");
            throw new Error("view is not a koIScintillaView");
        }
        var scimoz = view.scimoz;
        if (scimoz.selections > 1) {
            log.info("highlightVariable: multiple selections");
            return false;
        }
        if (["mouse", "keyboard", "manual"].indexOf(reason) == -1) {
            log.info("highlightVariable: invalid reason " + reason);
            reason = "manual";
        }

        var varStyles = view.languageObj.getVariableStyles({});
        var rangeStart = scimoz.wordStartPosition(scimoz.currentPos, true);
        var rangeEnd = scimoz.wordEndPosition(scimoz.currentPos, true);
        if (scimoz.selectionStart != scimoz.selectionEnd &&
            (scimoz.selectionStart != rangeStart || scimoz.selectionEnd != rangeEnd))
        {
            // have selection, but it doesn't match scimoz's idea of a word
            return false;
        }
        if (reason != "manual") {
            let indicStart = scimoz.indicatorStart(INDICATOR, rangeStart);
            let indicEnd = scimoz.indicatorEnd(INDICATOR, rangeStart);
            if (indicStart == rangeStart && indicEnd == rangeEnd &&
                scimoz.indicatorValueAt(INDICATOR, rangeStart))
            {
                log.debug("variable highlighting already active, skipping");
                return false;
            }
            // check variable styles
            let styles = scimoz.getStyleRange(rangeStart, rangeEnd);
            if (styles.some(function(s) varStyles.indexOf(s) == -1)) {
                log.debug("variable highlighting: found word char with non-var style")
                return false;
            }
        }

        var matchPrefix = reason == "keyboard" &&
                          scimoz.selectionStart == rangeEnd &&
                          ko.prefs.getBoolean("codeintel_highlight_variables_match_prefix", false);


        // At this point, we have rangeStart / rangeEnd
        if (reason != "manual") {
            let minLength =
                ko.prefs.getLong("codeintel_highlight_variables_min_auto_length", 3);
            if (rangeEnd - rangeStart < minLength) {
                log.debug("auto-highlight found too short search text");
                return false;
            }
        }
        var searchText = scimoz.getTextRange(rangeStart, rangeEnd);

        // Bug 95389: Tcl isn't a true citadel language, but registers itself as one.
        let useScopes = (view.language !== "Tcl"
            && ko.prefs.getBoolean("codeintel_highlight_variables_use_scope",
                                    true)
            && ko.codeintel.isActive
            && ko.codeintel.is_citadel_lang(view.language));
        // don't use scopes on manual triggers, so we can show things in comments too
        useScopes &= (reason != "manual");
        var findHitCallback = {
            hasHit: false,
            // batch up the indicator painting to avoid excessive repaints
            ranges: [],
            pending: 0,
            done: false,
            addHighlight: function(start, length)
                this.ranges.push([start, length]),
            doHighlight: function doHighlight() {
                scimoz.indicatorCurrent = INDICATOR;
                scimoz.indicatorValue = 1;
                if (!this.hasHit) {
                    scimoz.indicatorClearRange(0, scimoz.length);
                    this.hasHit = true;
                }
                let ranges = this.ranges.splice(0);
                for each (let [start, length] in ranges) {
                    scimoz.indicatorFillRange(start, length);
                }
            },
            onDone: function(result) {
                this.done = true;
                if (this.pending > 0) {
                    return; // wait for async defns to come back
                }
                this.doHighlight();
                if (Components.isSuccessCode(result)) {
                    do_next_range();
                }
            }
        };

        var isIdentChar;
        if (scimoz.wordChars) {
            isIdentChar = function isIdentChar(c)
                scimoz.wordChars.indexOf(c) != -1;
        } else {
            // No word chars known; attempt to emulate the scintilla default
            // see scintilla/src/CharClassify.cxx - we assume:
            // - anything over 0x80 is a word char
            // - A-Z, a-z, 0-9, _ are word chars
            isIdentChar = function isIdentChar(c)
                /\w/.test(c) || c.charCodeAt(0) > 0x80;
        }

        /**
         * Called when we have decided that a hit is good and we want to accept
         * it.  Note that this filters for definition matches and
         * looks-like-a-variable.
         */
        var acceptHit = (function acceptHit(start, end) {
            if (!matchPrefix && useScopes && sourceVarDefns.length > 0) {
                ++findHitCallback.pending;
                getDefnsAsync(end, function(defns) {
                    for each (let sourceDefn in sourceVarDefns) {
                        for each (let destDefn in defns) {
                            if (sourceDefn.equals(destDefn)) {
                                // source definition matches found definition
                                findHitCallback.addHighlight(start, end - start);
                                return;
                            }
                        }
                    }
                }, function(count) {
                    --findHitCallback.pending;
                    if (findHitCallback.done && findHitCallback.pending < 1) {
                        findHitCallback.onDone();
                    }
                });
            } else {
                if (start > 0) {
                    let text = scimoz.getTextRange(scimoz.positionBefore(start),
                                                   scimoz.positionAfter(start));
                    if (text.split("").every(isIdentChar)) {
                        return;
                    }
                }
                if (!matchPrefix && end < scimoz.length) {
                    let text = scimoz.getTextRange(scimoz.positionBefore(end),
                                                   scimoz.positionAfter(end));
                    if (text.split("").every(isIdentChar)) {
                        return;
                    }
                }
                findHitCallback.addHighlight(start, end - start);
            }
        }).bind(this);

        if (matchPrefix) {
            findHitCallback.onHit = (function(hit) {
                let start = scimoz.positionAtChar(0, hit.start_pos);
                let end = scimoz.positionAtChar(0, hit.end_pos);
                if (start > 0) {
                    let leadStyle = scimoz.getStyleAt(scimoz.positionBefore(start));
                    if (varStyles.indexOf(leadStyle) != -1) {
                        // does not _start_ a variable style run
                        return;
                    }
                }
                let styles = scimoz.getStyleRange(start, end);
                if (styles.some(function(s) varStyles.indexOf(s) == -1 )) {
                    // text in range isn't a variable style
                    return;
                }
                acceptHit(start, end);
            }).bind(findHitCallback);
        } else {
            findHitCallback.onHit = (function(hit) {
                let start = scimoz.positionAtChar(0, hit.start_pos);
                let end = scimoz.positionAtChar(0, hit.end_pos);
                if (reason != "manual") {
                    if (start > 0) {
                        let initialStyle = scimoz.getStyleAt(start);
                        let leadStyle = scimoz.getStyleAt(scimoz.positionBefore(start));
                        if (initialStyle == leadStyle) {
                            // does not _start_ a variable style run
                            // (we just ensure a change in style, not that the
                            // lead style isn't in varStyles, to deal with Perl
                            // where that's a valid variable)
                            return;
                        }
                    }
                    if (end > 0) {
                        let endStyle = scimoz.getStyleAt(scimoz.positionBefore(end));
                        let trailStyle = scimoz.getStyleAt(end);
                        if (endStyle == trailStyle) {
                            // does not _end_ a variable style run
                            // (see above on style change vs varStyles)
                            return;
                        }
                    }
                    let styles = scimoz.getStyleRange(start, end);
                    if (styles.some(function(s) varStyles.indexOf(s) == -1 )) {
                        // text in range isn't a variable style
                        return;
                    }
                }
                acceptHit(start, end);
            }).bind(findHitCallback);
        }
        var do_next_range;
        var getResults = (function getResults() {
            // everything's set up now, ready to actually do the searches
            let firstLine = scimoz.firstVisibleLine;
            let lastLine = firstLine + scimoz.linesOnScreen + 1; // last may be partial
            let startPos = Math.max(scimoz.positionFromLine(firstLine), 0);
            let endPos = scimoz.positionFromLine(lastLine);
            if (endPos < 0) endPos = scimoz.length; // happens if we're at end of file
            let ranges = [];
            if (sourceVarDefns.length > 0 && sourceVarDefns[0].scopestart > 0) {
                // We have a variable definition, and we know its scope
                let defn = sourceVarDefns[0];
                let scopeStart = scimoz.positionFromLine(defn.scopestart - 1);
                let scopeEnd = -1;
                if (defn.scopeend != 0) {
                    scopeEnd = scimoz.positionFromLine(defn.scopeend);
                }
                if (scopeEnd <= 0) {
                    scopeEnd = scimoz.length; // if it's at the last line
                }
                ranges = [[Math.max(startPos, scopeStart), Math.min(endPos, scopeEnd)],
                          [scopeStart, startPos],
                          [endPos, scopeEnd]];
                log.debug("Found defn for " + defn.name + " at " +
                          defn.scopestart + "~" + defn.scopeend + ", ranges=" +
                          JSON.stringify(ranges));
                // force lex to end of scope (the other parts should already be lexed)
                scimoz.colourise(endPos, scopeEnd);
            } else {
                ranges = [[startPos, endPos], [0, startPos], [endPos, scimoz.length]];
                log.debug("No defn found for " + searchText + "; ranges = " +
                          JSON.stringify(ranges));
                // force lex to EOF (the other parts should already be lexed)
                scimoz.colourise(endPos, -1);
            }
            do_next_range = (function do_next_range_() {
                if (ranges.length < 1) {
                    this._last_highlight_async = null;
                    return;
                }
                let [startPos, endPos] = ranges.shift();
                if (startPos >= endPos) {
                    log.debug("Skipping empty/invalid range " + startPos + "~" + endPos);
                    do_next_range();
                    return;
                }
                let text = scimoz.getTextRange(startPos, endPos);
                var opts = Cc["@activestate.com/koFindOptions;1"].createInstance();
                opts.patternType = Ci.koIFindOptions.FOT_SIMPLE;
                opts.matchWord = false;
                opts.searchBackward = false;
                opts.caseSensitivity = Ci.koIFindOptions.FOC_SENSITIVE; // TODO: depend on language
                opts.preferredContextType = Ci.koIFindContext.FCT_CURRENT_DOC;
                opts.showReplaceAllResults = false;
                opts.displayInFindResults2 = false;
                opts.multiline = false;
                if (view.language === "Tcl") {
                    // Bug 95389: Tcl is one of the few non-shell langs that
                    // defines vars without a '$', but refers to them with one.
                    opts.patternType = Ci.koIFindOptions.FOT_REGEX_PYTHON;
                    if (searchText[0] === '$') {
                        searchText = "\\$?" + searchText.substring(1);
                    } else {
                        searchText = "\\$?" + searchText;
                    }
                }
                this._last_highlight_async =
                    Cc["@activestate.com/koFindService;1"]
                      .getService(Ci.koIFindService)
                      .findallasync(searchText, text, findHitCallback, startPos, opts);
            }).bind(this);
            do_next_range();
            return true;
        }).bind(this);

        function getDefnsAsync(pos, onResult, onDone) {
            let cplnHandler = {
                count: 0,
                setAutoCompleteInfo: function() {},
                setCallTipInfo: function() {},
                setDefinitionsInfo: function(count, defns, trg) {
                    this.count += count;
                    onResult(defns);
                },
                setStatusMessage: function() {},
                updateCallTip: function() {},
                triggerPrecedingCompletion: function() {},
                done: function() onDone(this.count)
            };
            let buf = view.koDoc.ciBuf;
            buf.defn_trg_from_pos(pos, function(trg) {
                if (!trg) {
                    return;
                }
                buf.async_eval_at_trg(trg, cplnHandler,
                                      Ci.koICodeIntelBuffer.EVAL_SILENT |
                                        Ci.koICodeIntelBuffer.EVAL_QUEUE);
            }, handleError);
        }

        var sourceVarDefns = [];
        if (useScopes && !matchPrefix) {
            // If we want to use scopes, we must first figure out where the
            // original variable that invoked things lived
            getDefnsAsync(rangeEnd, function(defns) {
                sourceVarDefns = defns.filter(function(def) def.name == searchText);
            }, getResults);
        } else {
            getResults();
        }
        return true;
    }).bind(this);

    this._triggerHighlightVariableFromMouse = (function(event) {
        if ("_triggerHighlightVariableFromKeyboard_timeout" in this) {
            clearTimeout(this._triggerHighlightVariableFromKeyboard_timeout);
        }
        var view = ko.views.manager.currentView;
        if (!(view instanceof Ci.koIScintillaView)) {
            return;
        }
        this.highlightVariable(view, "mouse");
    }).bind(this);

    this._triggerHighlightVariableFromKeyboard = (function(event) {
        if ("_triggerHighlightVariableFromKeyboard_timeout" in this) {
            clearTimeout(this._triggerHighlightVariableFromKeyboard_timeout);
        }
        if (!("data") in event || !(event.data.view instanceof Ci.koIScintillaView)) {
            return; // not a scintilla view, so no text modified!?
        }
        let view = event.data.view;
        if (view !== ko.views.manager.currentView) {
            return; // wrong view
        }
        if (!(event.data.modificationType & view.MOD_TEXT_MODIFIED)) {
            return; // we only care about text insertion/removal events
        }
        if (event.data.position != view.scimoz.currentPos) {
            return; // not a keyboard action - text somewhere else changed
        }
        // this needs to wait a bit, to ensure that we won't be typing more
        this._triggerHighlightVariableFromKeyboard_timeout =
            setTimeout((function() {
                    if (!this.highlightVariable(view, "keyboard")) {
                        let scimoz = view.scimoz;
                        scimoz.indicatorCurrent =
                            Ci.koILintResult.DECORATOR_TAG_MATCH_HIGHLIGHT;
                        scimoz.indicatorClearRange(0, scimoz.length);
                    }
                }).bind(this),
                this._triggerHighlightVariableFromKeyboard_delay);
    }).bind(this);
    
    this.observe = function CodeIntel_observe(subject, topic, data)
    {
        switch (topic) {
            case "codeintel_highlight_variables_auto_mouse": {
                // always remove the listener; and put it back if we want it on.
                // this way we make sure to never accidentally hook it up twice.
                let view = ko.views.manager.topView;
                view.removeEventListener("click",
                                         this._triggerHighlightVariableFromMouse,
                                         false);
                if (ko.prefs.getBoolean(topic, false)) {
                    view.addEventListener("click",
                                          this._triggerHighlightVariableFromMouse,
                                          false);
                }
                break;
            }
            case "codeintel_highlight_variables_auto_keyboard": {
                // always remove the listener; and put it back if we want it on.
                // this way we make sure to never accidentally hook it up twice.
                let view = ko.views.manager.topView;
                window.removeEventListener("editor_text_modified",
                                           this._triggerHighlightVariableFromKeyboard,
                                           false);
                if (ko.prefs.getBoolean(topic, false)) {
                    window.addEventListener("editor_text_modified",
                                            this._triggerHighlightVariableFromKeyboard,
                                            false);
                }
                break;
            }
            case "codeintel_highlight_variables_auto_delay":
                this._triggerHighlightVariableFromKeyboard_delay =
                    Math.max(ko.prefs.getLong(topic, 250), 0);
        }
    };

    this.QueryInterface = XPCOMUtils.generateQI([Ci.nsIObserver]);

    XPCOMUtils.defineLazyGetter(this, "_bundle", function()
        Cc["@mozilla.org/intl/stringbundle;1"]
          .getService(Ci.nsIStringBundleService)
          .createBundle("chrome://komodo/locale/codeintel.properties"));

    /**
     * nsIController implementation for codeintel commands
     */
    function CodeIntelController() {}
    // The following two lines ensure proper inheritance (see Flanagan, p. 144).
    CodeIntelController.prototype = new xtk.Controller();
    CodeIntelController.prototype.constructor = CodeIntelController;

    CodeIntelController.prototype.is_cmd_findHighlightVariableManual_enabled =
        function() {
            let view = ko.views.manager.currentView;
            return view && view.getAttribute("type") == "editor";
        };

    CodeIntelController.prototype.do_cmd_findHighlightVariableManual =
        function() ko.codeintel.highlightVariable(null, 'manual');

}).apply(ko.codeintel);

window.addEventListener("komodo-ui-started", ko.codeintel.initialize, false);
