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

xtk.include('controller');

if (typeof(ko)=='undefined') {
    var ko = {};
}


ko.isearch = {};
(function() {

var _log = ko.logging.getLogger('isearch');


function ISController(viewManager) {
    this._incrementalSearchPattern = '';
    this._lastIncrementalSearchText = '';
    this.inRepeatCounterAccumulation = false;
    this.repeatCounter = 0;
    this.defaultRepeatCounter = 0;
    this.findSvc = Components.classes["@activestate.com/koFindService;1"].
                getService(Components.interfaces.koIFindService);
    window.controllers.appendController(this);
    var prefName = "defaultRepeatFactor";
    var default_defaultRepeatFactor = 4; // Like in Emacs
    try {
        var prefsSvc = Components.classes["@activestate.com/koPrefService;1"].
                                getService(Components.interfaces.koIPrefService);
        var prefs = prefsSvc.prefs;
        if (prefs.hasPref(prefName)) {
            var candidate = prefs.getLongPref(prefName);
            // Sanity-check it
            if (!candidate || candidate <= 0) {
                // The ! part includes NaN as well as 0
                // Undefined prefs should throw an exception
                dump("new ISController: rejecting pref " + prefName + " setting of " + candidate + "\n");
                candidate = default_defaultRepeatFactor;
            }
            this[prefName] = candidate;
        } else {
            this[prefName] = default_defaultRepeatFactor;
        }
    } catch(ex) {
        _log.error(ex + "\n");
        this[prefName] = default_defaultRepeatFactor;
    }
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
ISController.prototype = new xtk.Controller();
ISController.prototype.constructor = ISController;

ISController.prototype.destructor = function() {
}

ISController.prototype.is_cmd_startIncrementalSearch_enabled = function() {
    return ko.views.manager.currentView != null;
}

ISController.prototype.do_cmd_startIncrementalSearch= function() {
    this._startIncrementalSearch(false);
}

ISController.prototype.is_cmd_startIncrementalSearchBackwards_enabled = function() {
    return ko.views.manager.currentView != null;
}

ISController.prototype.do_cmd_startIncrementalSearchBackwards= function() {
    this._startIncrementalSearch(true);
}

function key_event_handler_for_isearch(e) {
    ko.isearch.controller.keyPressForSearch(e); // doesn't take into account focus shifts in other scintillas
}

function mouse_event_handler_for_isearch(e) {
    // If called from <scintilla>, 'this' will be the XBL widget.  Weird JS.
    if (this.key_handler) {
        this.key_handler = null;
    }
    if (this.mouse_handler) {
        this.mouse_handler = null;
    }
    this.removeEventListener('blur', mouse_event_handler_for_isearch, false);

    ko.isearch.controller._stopIncrementalSearch("Clicked away", false);
}

ISController.prototype._startIncrementalSearch = function(backwards) {
    var scintilla = ko.views.manager.currentView.scintilla; // XXX fixme?
    if (!scintilla) {
        _log.error("Couldn't start incremental search with no focused scintilla");
        return;
    }
    var scimoz = scintilla.scimoz;
    ko.statusBar.AddMessage("Incremental Search:", "isearch", 0, false, true)
    scintilla.key_handler = key_event_handler_for_isearch;
    scintilla.mouse_handler = mouse_event_handler_for_isearch;
    scintilla.addEventListener('blur', mouse_event_handler_for_isearch, false);
    this._incrementalSearchStartPos = Math.min(scimoz.currentPos, scimoz.anchor);
    var pattern = scimoz.selText;
    this._incrementalSearchContext = Components.classes["@activestate.com/koFindContext;1"]
        .createInstance(Components.interfaces.koIFindContext);

    // Save original find settings
    this._origFindOptions = new Object();
    this._origFindOptions.searchBackward = this.findSvc.options.searchBackward;
    this._origFindOptions.matchWord= this.findSvc.options.matchWord;
    this._origFindOptions.patternType = this.findSvc.options.patternType;
    this._origFindOptions.caseSensitivity = this.findSvc.options.caseSensitivity;

    this.findSvc.options.searchBackward = backwards;
    this.findSvc.options.matchWord = false;
    this.findSvc.options.patternType = Number(gPrefs.getStringPref('isearchType'));
    this.findSvc.options.caseSensitivity = Number(gPrefs.getStringPref('isearchCaseSensitivity'));
    this._incrementalSearchContext.type = this.findSvc.options.FCT_CURRENT_DOC;
    this._incrementalSearchPattern = pattern;
    if (pattern) {
        // we don't want to find the current selection, dummy.
        scimoz.currentPos = this._incrementalSearchStartPos + pattern.length;
        this._lastIncrementalSearchText = pattern;
        ko.statusBar.AddMessage("Incremental Search: " + pattern, "isearch", 0, false, true)
        Find_FindNext(window, this._incrementalSearchContext,
                      pattern, null, true,
                      true);  // useMRU: add this pattern to the find MRU
    }
}

ISController.prototype._stopIncrementalSearch = function(why, highlight) {
    ko.statusBar.AddMessage("Incremental Search Stopped: " + why, "isearch", 3000, highlight, true)
    if (this._origFindOptions) {
        // Restore original find settings
        this.findSvc.options.searchBackward = this._origFindOptions.searchBackward;
        this.findSvc.options.matchWord = this._origFindOptions.matchWord;
        this.findSvc.options.patternType = this._origFindOptions.patternType;
        this.findSvc.options.caseSensitivity = this._origFindOptions.caseSensitivity;
        this._origFindOptions = null;
    }
    ko.mru.add("find-patternMru", this._incrementalSearchPattern, true);
    this._incrementalSearchPattern = '';
}

ISController.prototype.is_cmd_rawKey_enabled = function() {
    return ko.views.manager.currentView != null;
}

ISController.prototype.do_cmd_rawKey= function() {
    var scintilla = ko.views.manager.currentView.scintilla;
    scintilla.key_handler = this.rawHandler;
    scintilla.addEventListener('blur', gCancelRawHandler, false);
    scintilla.scimoz.focus = true;
    ko.statusBar.AddMessage("Enter Control Character:", "raw_input", 0, true, true)
}

function gCancelRawHandler(event) {
    if (this.key_handler) {
        this.key_handler = null;
        ko.views.manager.currentView.scintilla.
            removeEventListener('blur', gCancelRawHandler, false);
    }
    ko.statusBar.AddMessage(null, "raw_input", 0, false, true)
}

ISController.prototype.rawHandler= function(event) {
    try {
        if (event.type != 'keypress') return;
        var scintilla = ko.views.manager.currentView.scintilla;
        scintilla.key_handler = null;
        var scimoz = scintilla.scimoz;
        event.cancelBubble = true;
        event.preventDefault();
        // XXX handle meta key here?
        if (event.ctrlKey) {
            // Need to convert from charCode to ASCII value
            scimoz.replaceSel(String.fromCharCode(event.charCode-96));
        } else {
            if (event.charCode != 0) {  // not sure why space doesn't work.
                scimoz.replaceSel(String.fromCharCode(event.charCode));
            } else {
                switch (event.keyCode) {
                    case event.DOM_VK_ESCAPE:
                    case event.DOM_VK_ENTER:
                    case event.DOM_VK_RETURN:
                    case event.DOM_VK_TAB:
                    case event.DOM_VK_BACK_SPACE:
                        scimoz.replaceSel(String.fromCharCode(event.keyCode));
                        break;
                    default:
                        // do nothing
                }
            }
        }
        ko.statusBar.AddMessage(null, "raw_input", 0, false, true)
    } catch (e) {
        _log.error(e);
    }
};

ISController.prototype.do_cmd_repeatNextCommandBy= function() {
    try {
        var scintilla = ko.views.manager.currentView.scintilla;
        scintilla.key_handler = this.multiHandler;
        scintilla.addEventListener('blur', ko.isearch.controller.cancelMultiHandler, false);
        scintilla.scimoz.focus = true;
        ko.isearch.controller.inRepeatCounterAccumulation = true;
        ko.isearch.controller.repeatCounter = 0;
        ko.isearch.controller.defaultRepeatCounter = ko.isearch.controller.defaultRepeatFactor;
        ko.statusBar.AddMessage("Number of Repeats: "
                                + ko.isearch.controller.defaultRepeatCounter
                                + "|", "multi_input", 0, true, true)
    } catch (e) {
        _log.exception(e);
    }
};

ISController.prototype.getCount = function() {
    var count;
    if (ko.isearch.controller.defaultRepeatCounter > 0) {
        count = ko.isearch.controller.defaultRepeatCounter;
    } else {
        count = ko.isearch.controller.repeatCounter;
    }
    return count;
}

ISController.prototype.cancelMultiHandler = function(event) {
    ko.isearch.controller.inRepeatCounterAccumulation = false;
    var scintilla = ko.views.manager.currentView.scintilla;
    scintilla.removeEventListener('blur', ko.isearch.controller.cancelMultiHandler, false);
    scintilla.key_handler = null;
    ko.statusBar.AddMessage(null, "multi_input", 0, false, true)
};

/* _lookingAtRepeatCommand -
 * @param {Object} event - the keypress event object
 *
 * The single-key variant implement emacs-style Ctrl-U universal-argument
 * key.  This avoids ambiguity of what Ctrl-U means in the
 * sequence Ctrl-K, Ctrl-U, Ctrl-U
 *
 * Emacs documentation:
 *
 ** Begin a numeric argument for the following command.
 ** Digits or minus sign following C-u make up the numeric argument.
 ** C-u following the digits or minus sign ends the argument.
 ** C-u without digits or minus sign provides 4 as argument.
 ** (Note that "4" is configurable via the unexposed pref defaultRepeatFactor)
 ** Repeating C-u without digits or minus sign
 **  multiplies the argument by 4 each time.
 ** For some commands, just C-u by itself serves as a flag
 ** which is different in effect from any particular numeric argument.
 ** These commands include C-@ and C-x (.
 *
 * Negative arguments don't make sense yet -- see bug
 * http://bugs.activestate.com/show_bug.cgi?id=72910
 */

ISController.prototype._lookingAtRepeatCommand = function(event) {
    var actual_key = gKeybindingMgr.event2keylabel(event);
    var expected_key_sequences = gKeybindingMgr.command2key['cmd_repeatNextCommandBy'];
    for (var i in expected_key_sequences) {
        // Reject multi-character keylabels like Ctrl-K, Ctrl-Home
        // to eliminate any ambiguity.
        // to distinguish it from keys that *use* the comma
        var acceptable_key_seq = expected_key_sequences[i].split(/,[\s]+/);
        if (acceptable_key_seq.length == 1
            && acceptable_key_seq[0] == actual_key) {
            return true;
        }
    }
    return false;
}

ISController.prototype.multiHandler= function(event) {
    try {
        if (event.type != 'keypress') return;
        if (event.charCode >= 48 && event.charCode <= 57) {
            ko.isearch.controller.defaultRepeatCounter = 0;
            ko.isearch.controller.repeatCounter = ko.isearch.controller.repeatCounter * 10 + (event.charCode - 48);
            ko.statusBar.AddMessage("Number of Repeats: " + String(ko.isearch.controller.repeatCounter) + '|',
                                    "multi_input", 0, false, true);
            return;
        } else if (ko.isearch.controller._lookingAtRepeatCommand(event)) {
            event.cancelBubble = true;
            event.preventDefault();
            ko.isearch.controller.defaultRepeatCounter *= ko.isearch.controller.defaultRepeatFactor;
            ko.statusBar.AddMessage("Number of Repeats: " + String(ko.isearch.controller.defaultRepeatCounter) + '|',
                                    "multi_input", 0, false, true);
            return;
        }
        var key = gKeybindingMgr.event2keylabel(event);
        // If the key corresponds to the cmd_cancel command, cancel.
        if (gKeybindingMgr.command2key['cmd_cancel'] == key) {
            event.cancelBubble = true;
            ko.isearch.controller.cancelMultiHandler();
            return;
        }
        if (event.charCode && !event.ctrlKey && !event.altKey && !event.metaKey) {
            ko.isearch.controller.cancelMultiHandler();
            // it's just a simple keystroke, do that.
            key = String.fromCharCode(event.charCode);
            var txt = '';
            var count = ko.isearch.controller.getCount();
            for (var i = 0; i < count; i++) {
                txt += key;
            }
            var scintilla = ko.views.manager.currentView.scintilla;
            scintilla.scimoz.replaceSel(txt);
        }
    } catch (e) {
        _log.error(e);
    }
}
ISController.prototype.keyPressForSearch = function(event) {
    try {
        if (event.type != 'keypress') return;
        var v = ko.views.manager.currentView;
        var scintilla = v.scintilla;
        var scimoz = v.scintilla.scimoz;
        var pos = scimoz.selectionStart < scimoz.selectionEnd ? scimoz.selectionStart : scimoz.selectionEnd;
        var eventkey = gKeybindingMgr.event2keylabel(event);
        var triggerkeys = gKeybindingMgr.command2keysequences('cmd_startIncrementalSearch');
        var backwardstriggerkeys = gKeybindingMgr.command2keysequences('cmd_startIncrementalSearchBackwards');

        // If the key sequence associated with incremental search is more than
        // one key long (i.e. the user has customized from the default <Ctrl+I>
        // to, say, <Ctrl+K, I>):
        // - if the last key is a Ctrl or Alt key, use it
        // - otherwise, disable the 'multiple hits' feature
        var triggerkey;
        if (triggerkeys) {
            triggerkey = triggerkeys[triggerkeys.length-1];
        }
        var backwardstriggerkey = '';
        if (backwardstriggerkeys) {
            backwardstriggerkey = backwardstriggerkeys[backwardstriggerkeys.length-1];
        }
        if ((triggerkeys.length == 1 
             || triggerkey.indexOf('Ctrl') != -1
             || triggerkey.indexOf('Meta') != -1
             || triggerkey.indexOf('Alt') != -1)
            && (eventkey == triggerkey || eventkey == backwardstriggerkey))
        {
            // we're hitting the same key as was used to start the search,
            // so we just want to redo the search
            event.cancelBubble = true;
            event.preventDefault();
            if (this._lastIncrementalSearchText == '')
                return;
            if (this._incrementalSearchPattern == "") {
                // Second <Ctrl+I> after a non-search action
                this._incrementalSearchPattern = this._lastIncrementalSearchText;
                gFindSession.Reset();
            }
            if (eventkey == backwardstriggerkey) {
                this.findSvc.options.searchBackward = true;
            } else {
                this.findSvc.options.searchBackward = false;
            }
            var findres = Find_FindNext(window, this._incrementalSearchContext,
                                        this._incrementalSearchPattern,
                                        null, true,
                                        true); // add pattern to find MRU
            if (findres == false) {
                ko.statusBar.AddMessage("Incremental Search: No more occurrences of "
                    + this._incrementalSearchPattern +' found',
                    "isearch", 0, false, true)
            } else {
                this._incrementalSearchStartPos = scimoz.currentPos;
                ko.statusBar.AddMessage("Incremental Search: "
                    + this._incrementalSearchPattern,
                    "isearch", 0, false, true)
            }
            return;
        }

        var isShiftLeftKey = event.shiftKey && event.keyCode == event.DOM_VK_LEFT;
        var isShiftRightKey = event.shiftKey && event.keyCode == event.DOM_VK_RIGHT;
        var isBS = event.keyCode == event.DOM_VK_BACK_SPACE;
        var isRegularKey = event.keyCode == 0;
        var isSlash = event.keyCode == event.DOM_VK_SLASH;
        if (!event.ctrlKey
            && !event.altKey && !event.metaKey 
            && (isRegularKey || isShiftRightKey || isShiftLeftKey || isBS || isSlash))
        {
            var pattern = this._incrementalSearchPattern;
            event.cancelBubble = true;
            event.preventDefault();
            if (isShiftRightKey) {
                var nextChar = scimoz.getWCharAt(scimoz.currentPos);
                pattern = pattern + nextChar;
                event.stopPropagation();  // We don't want normal shift-arrow behavior to occur
            } else if (isShiftLeftKey || isBS) {
                if (pattern == '') return; // nothing left to backtrack
                pattern = pattern.substr(0, pattern.length-1);
                event.stopPropagation();  // We don't want normal shift-arrow behavior to occur
            } else if (isSlash) {
                // do nothing;  The "real" slash charCode-bearing event will come later.
                event.stopPropagation();
                return;
            } else {
                pattern = pattern + String.fromCharCode(event.charCode);
            }
            this._lastIncrementalSearchText = pattern;
            this._incrementalSearchPattern = pattern;
            var oldStart = scimoz.selectionStart;
            var oldEnd = scimoz.selectionEnd;
            scimoz.gotoPos(this._incrementalSearchStartPos-1);
            if (this._incrementalSearchPattern == '') {
                ko.statusBar.AddMessage("Interactive Search: |", "isearch",
                                     0, false, true);
                return;
            }
            ko.macros.recorder.undo();
            findres = Find_FindNext(
                window, this._incrementalSearchContext,
                this._incrementalSearchPattern, null,
                true,
                // Do NOT add this pattern to find MRU
                //  http://bugs.activestate.com/show_bug.cgi?id=27350
                // that will be done on stopping of interactive search.
                false,
                null,   // msgHandler
                false); // don't use highlighting
            if (! findres) {
                ko.statusBar.AddMessage("Interactive Search: No occurrences of "
                    + this._incrementalSearchPattern + " found.",
                    "isearch", 3000, true, true);
                scimoz.setSel(oldStart, oldEnd);
            } else {
                ko.statusBar.AddMessage("Interactive Search: "
                    + this._incrementalSearchPattern + '|',
                    "isearch", 0, false, true)
            }
            return;
        }
        else {
            scintilla.key_handler = null;
            scintilla.mouse_handler = null;
            scintilla.removeEventListener('blur',
                mouse_event_handler_for_isearch, false);
            // Anything, not just escape, cancels incremental search
            this._stopIncrementalSearch("Search canceled.");
            var key = gKeybindingMgr.event2keylabel(event);
            if (gKeybindingMgr.command2key['cmd_cancel'] == key) {
                event.cancelBubble = true;
            }
            return;
        }
    } catch (e) {
        _log.error(e);
    }
}

this.controller = new ISController();

}).apply(ko.isearch);

