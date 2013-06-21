/* Copyright (c) 2000-2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Implement the multi-caret editing API for Scintilla
 *
 * These objects get created and are associated with each view,
 * so just because the user switches views doesn't mean that a
 * multi-caret session has to end.
 * 
 * The API:
 * 
 * Definition:
 * ** A "range" is a generalized editing area in the document.
 * ** It's either a selected piece of the document, or a single
 * ** point between two characters (which Scintilla calls a "caret").
 * 
 * Methods:
 * 
 * ko.selections.MultiCaretSession(koIView) 
 * - returns an instance of a MultiCaretSession
 * 
 * boolean readonly property isDormant => boolean: whether session is dormant
 * 
 * boolean readonly property isGatheringCarets => boolean: whether session 
 *   is gathering carets and selections, but no characters have been typed
 * 
 * boolean readonly property isActive => boolean: whether session 
 *   is processing characters
 * 
 * void addRangesAtomically(ranges)
 * - Call this when you have a list of carets and selections you want
 *   to edit concurrently.  No need to call startAddingRanges() or
 *   doneAddingRanges() when this is used.
 * 
 * void startAddingRanges(void)
 * - Call this at the start of an interactive session
 * 
 * void addRange(startPos[, endPos])
 * - Add a selection or caret (endPos isn't specified, or is 
 *   equal to startPos) to the list of ranges being gathered.
 * 
 * void doneAddingRanges()
 * - Call this when it's time to apply modifications to each range.
 * 
 * void endSession()
 * - Call this when it's time to remove the multiple selections,
 *   remove any multi-caret indicators, and resume single-selection typing.
 * 
 * void destroy()
 * - Removes the view's reference to the multiCaretSession, and the
 *   multiCaretSession's reference to the view.  Needed only if we
 *   find memory leak problems due to the circular references.
 * 
 * boolean isTypingEvent(event)
 * - Returns true if the typing event shouldn't end a multi-caret
 *   session, false if it should.
 * 
 *
 * There are two ways to use this API.
 *
 * The simplest is in batch mode:
 * Collect a set of ranges (2-tuples of the startPosition and endPosition)
 * Call multiCaretSession.addRangesAtomically(ranges);
 *
 * To support interactive editing on a set of carets/selections:
 * When the user first invokes the command to add the current caret or selection
 * as an additional caret, get the view's multiCaret session via
 *    ko.selections.getMultiCaretSession(view)
 *
 * A multi-caret session object can have three states, represented by
 * the boolean properties isDormant, isGatheringCarets, and isActive.
 * If session.isDormant is true, call
 * multiCaretSession.startAddingRanges(scimoz=undefined)
 * and then for each selection or caret you want to edit at, call
 * multiCaretSession.addRange(selectionStart, selectionEnd=undefined).
 *
 * When you're done gathering carets, call multiCaretSession.doneAddingRanges()
 * This will typically be done when multiCaretSession.isTypingEvent(event)
 * returns false, but of course can be done under other circumstances.
 *
 * Normally a multi-caret session will end itself when the user presses
 * ESC, an arrow key, clicks elsewhere in the document, etc.  But it
 * can be ended explicitly by calling multiCaretSession.endSession()
 *
 * Each view has its own multiCaretSession, which means the user can
 * switch from one tab to another without ending the session.  Multiple
 * views on the same document all share the same session.
 * 
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.selections)=='undefined') {
    ko.selections = {};
}

(function() {
    
const { classes: Cc, interfaces: Ci } = Components;
const CHANGE_INDICATOR = Ci.koILintResult.INDICATOR_MULTIPLE_CARET_AREAS;

// States

const INACTIVE = 0;
const SETTING_CARETS = 1;
const PROCESSING_CHARS = 2;


var log = ko.logging.getLogger("multipleCaret");
//log.setLevel(ko.logging.LOG_DEBUG);

/*
 * MultiCaretSession
 * @param view
 */
this.MultiCaretSession = function MultiCaretSession(view) {
    /*
     * Each of these objects lives on a particular view
     */
    this.view = view;
    this._state = INACTIVE;
    this._inUndoSession = false;
    this._ranges = [];
};

this.MultiCaretSession.prototype = {
    //isDormant: function() this._state == INACTIVE,
    //isActive: function() this._state == PROCESSING_CHARS,
    //isGatheringCarets: function() this._state == SETTING_CARETS,
    get isDormant() this._state == INACTIVE,
    get isActive() this._state == PROCESSING_CHARS,
    get isGatheringCarets() this._state == SETTING_CARETS,
    
    startAddingRanges: function startAddingRanges() {
        var scimoz = this.view.scimoz;
        this._clearSelections_preservePos(scimoz);
        scimoz.multipleSelection = true;
        scimoz.additionalSelectionTyping = true;
        scimoz.multiPaste = scimoz.SC_MULTIPASTE_EACH;
        this._state = SETTING_CARETS;
        this._ranges = [];
    },
    
    addRange: function addRange(startPos, endPos) {
        var scimoz = this.view.scimoz;
        if (typeof(endPos) == undefined) {
            endPos = startPos;
        }
        if (startPos > endPos) {
            [startPos, endPos] = [endPos, startPos];
        }
        this._ranges.push([startPos, endPos]);
        if (this._ranges.length > 1) {
            scimoz.addSelection(startPos, endPos);
            scimoz.indicatorCurrent = CHANGE_INDICATOR;
            scimoz.indicatorFillRange(startPos, endPos - startPos);
        }
    },

    _addRanges: function _addRanges(ranges) {
        var scimoz = this.view.scimoz;
        // Now we're about to start using the multiple-carets,
        // but it turns out the easiest way to do it is to clear
        // the current set and re-add them.
        this._clearSelections_preservePos(scimoz);
        
        // If we don't explicitly set scimoz.anchor and
        // scimoz.currentPos we'll have an extra random selection being
        // modified, usually at the start of the buffer.
        // So set them to the first range, and add selections for the others.
        var startPos = ranges[0][0];
        var endPos = ranges[0][1];
        scimoz.currentPos = startPos;
        scimoz.anchor = endPos;
        this.firstSelectionStartPos = startPos;
        scimoz.indicatorCurrent = CHANGE_INDICATOR;
        scimoz.indicatorClearRange(0, scimoz.length);
        scimoz.indicatorFillRange(startPos, endPos - startPos);
        for each ([startPos, endPos] in ranges.slice(1)) {
            if (startPos > endPos) {
                throw new Error("multipleCaret.js: _addRanges: startPos:"
                                + startPos + " > endPos:" + endPos);
            }
            //log.debug("startPos: " + startPos + ", endPos: " + endPos);
            scimoz.addSelection(startPos, endPos);
            scimoz.indicatorFillRange(startPos, endPos - startPos);
        }
        scimoz.mainSelection = 0;
        this._state = PROCESSING_CHARS;
        this._startUndoBlock(this.view, scimoz);
        //log.debug("scimoz.selectionStart: "
        //          + scimoz.selectionStart
        //          + ", scimoz.selectionEnd:"
        //          + scimoz.selectionEnd);
    },
    
    addRangesAtomically: function addRangesAtomically(ranges) {
        /*
         * Call this when everything is done in one shot.
         */
        this.startAddingRanges();
        this._addRanges(ranges);
    },

    doneAddingRanges: function doneAddingRanges() {
        var ranges = this._ranges;
        if (!ranges.length) {
            log.warn("no ranges to add\n");
            this.endSession();
            return;
        }
        var i;
        if (0) {
            var scimoz = this.view.scimoz;
            // There's a problem here: although I call scimoz.clearSelections(),
            // the first selection in the previous session keeps bouncing
            // back, and I'm not sure why.
            //
            // 
            for (i = 0; i < scimoz.selections; i++) {
                ranges.push([scimoz.getSelectionNCaret(i),
                             scimoz.getSelectionNAnchor(i)]);
                //dump("Add scimoz.caret/anchor "
                //     + ranges[ranges.length - 1]
                //     + "\n");
            }
        }
        ranges.sort(function(a, b) (a[0] - b[0]) || (a[1] - b[1]) );
        
        // Remove duplicates and overlaps from this._ranges
        var r1, r2;
        for (i = ranges.length - 2; i >= 0; --i) {
            r2 = ranges[i + 1];
            r1 = ranges[i];
            if (r1[0] == r2[0]) {
                ranges.splice(i, 1);
            } else if (r1[1] > r2[0]) {
                // The two adjacent ranges overlap, so just combine
                // them into r[i + 1], and delete r[i]
                r2[0] = r1[0];
                ranges.splice(i, 1);
            }
        }
        this._addRanges(ranges);
        this._ranges = [];
    },

    _clearSelections_preservePos: function _clearSelections_preservePos(scimoz) {
        var currentPos = scimoz.currentPos;
        var anchor = scimoz.anchor;
        scimoz.clearSelections();
        scimoz.currentPos = currentPos;
        scimoz.anchor = anchor;
    },
    
    endSession: function endSession() {
        var view = this.view;
        var scimoz = view.scimoz;
        this._endUndoBlock(view, scimoz);
        scimoz.multiPaste = scimoz.SC_MULTIPASTE_ONCE;
        scimoz.additionalSelectionTyping = false;
        scimoz.multipleSelection = false;
        this._clearSelections_preservePos(scimoz);
        scimoz.indicatorCurrent = CHANGE_INDICATOR;
        scimoz.indicatorClearRange(0, scimoz.length);
        this._state = INACTIVE;
    },
    
    _startUndoBlock: function _startUndoBlock(view, scimoz) {
        this._inUndoSession = true;
        scimoz.beginUndoAction();
        view.addEventListener('click',
                              this._watchClick, false);
        view.addEventListener('keypress',
                              this._watchMultipleSelectionKeypress,
                              true);
    },
    
    _endUndoBlock: function _endUndoBlock(view, scimoz) {
        if (this._inUndoSession) {
            scimoz.endUndoAction();
            this._inUndoSession = false;
            view.removeEventListener('click',
                                     this._watchClick, false);
            view.removeEventListener('keypress',
                                     this._watchMultipleSelectionKeypress, true);
        }
    },
    
    destroy: function destroy() {
        var view = this.view;
        delete this.view;
        delete view._multiCaretSession;
    },
    
    _watchClick: function _watchClick(event) {
        var this_ = event.currentTarget._multiCaretSession;
        this_.endSession();
    },
    
    //XXX: Bug 99366
    _textEventCommands: ["cmd_paste", "cmd_deleteWordLeft"],

    isTypingEvent: function isTypingEvent(event) {
        // Whitelist the keys and commands that will not
        // cause the multi-selection edit session to end.
        
        // Consider this: if we backspace before the first pos,
        // end the multi-edit session?  Maybe not...
        if (event.keyCode == event.DOM_VK_BACK_SPACE) {
            switch(this._state) {
            case INACTIVE: // Shouldn't happen
                return false;
            case SETTING_CARETS: // This should end the session
                return false;
            case PROCESSING_CHARS:
                // If we're about to move to the left of the caret,
                // end this multi-caret session.
                return (this.view.scimoz.getSelectionNCaret(0)
                        > this.firstSelectionStartPos);
            }
        } else if ((event.charCode && !event.ctrlKey
                    && !event.altKey && !event.metaKey)
                   || event.keyCode == event.DOM_VK_TAB) {
            return true;
        } else {
            var keylabel = ko.keybindings.manager.event2keylabel(event,
                                                                 undefined,
                                                                 true);
            if (keylabel) {
                var command = ko.keybindings.manager.key2command[keylabel];
                if (this._textEventCommands.indexOf(command) !== -1) {
                    return true;
                }
            }
        }
        return false;
    },
    
    _watchMultipleSelectionKeypress: function _watchMultipleSelectionKeypress(event) {
        var view = event.currentTarget;
        var this_ = view._multiCaretSession;

        if (this_.isTypingEvent(event)) {
            // We need to use a setTimeout handler because the
            // keypress bubbling event is usually consumed
            // XXX: Bug 99366: Use an onModified handler instead of this:
            setTimeout(this_._watchMultipleSelectionKeypress_bubble.bind(this_),
                       0);
            return;
        }
        if (view.scintilla.autocomplete.active) {
            return;
        }
        this_.endSession();
    },
    
    _watchMultipleSelectionKeypress_bubble: function() {
        /** The distance between the first caret and the recorded
          * first selection lets us know how long each active
          * indicator needs to be.
          */
        var scimoz = this.view.scimoz;
        // Check for the indicator at the first selection
        var pos = this.firstSelectionStartPos;
        var caret = scimoz.getSelectionNCaret(0);
        if (caret == pos) {
            // Back at start, nothing to do
            return;
        } else if (caret < pos) {
            throw new Error("multipleCaret.js: Unexpected occurrence: caret = "
                            + caret
                            + " < pos: "
                            + pos);
        }
        
        var numChars = caret - pos;
        // Re-highlight all the selections.
        var lim = scimoz.selections;
        scimoz.indicatorCurrent = CHANGE_INDICATOR;
        for (var i = lim - 1; i >= 0; i--) {
            var startPos = scimoz.getSelectionNAnchor(i);
            scimoz.indicatorFillRange(startPos - numChars, numChars);
        }
    },

    __END__: null    
};

this.getMultiCaretSession = function getMultiCaretSession(view) {
    if ('_multiCaretSession' in view) {
        return view._multiCaretSession;
    }
    var session = new this.MultiCaretSession(view);
    view._multiCaretSession = session;
    session.view = view;
    return session;
};

}).apply(ko.selections);
