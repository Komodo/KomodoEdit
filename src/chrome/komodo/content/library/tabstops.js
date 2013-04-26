/* Copyright (c) 2003-2008 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/*
 * Tabstop utilities:
 * Parsing text for tabstop information.
 * Inserts tabstops and indicators into buffers.
 * Handles moving through tabstops in a buffer.
 * Synchronizes updates to a set of linked tabstops.
 *
 * Nomenclature: this module handles sequences of text
 * and tabstops defined in both snippets and document templates.
 * For generality I call these things LiveText - a mixture
 * of literal text strings and tabstops, which appear in the
 * document as string of text with an indicator, and can be
 * linked with other tabstops.
 *
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
ko.tabstops =  {};

(function() { // ko.tabstops namespace

// Public API:

/**************** Parsing, Tabstop Insertion ****************/

/**
 * Parse a stream of pieces of text and tabstop.
 * @param {String} liveText: Unicode text to parse
 * @returns {Object}: An opaque object, used by other public methods
 *                    in this namespace
 * @throws {LiveTextParserException}
 */
this.parseLiveText = function parseLiveText(liveText) {
    var parser = new this.LiveTextParser();
    return parser.parse(liveText);
};

/**
 * Exception object.  The message field gives a specific message.
 */
this.LiveTextParserException = function(msg, snippet) { this.message = msg; this.snippet = snippet; };
this.LiveTextParserException.prototype = Error.prototype;
this.LiveTextParserException.constructor = Error.constructor;

/**
 * Inserts the contents of parsed liveText into the buffer
 * @param {Scimoz} scimoz_: The usual Scimoz object.
 * @param {Long} insertionPoint: Start writing the new text and tabstops here.
 * @param {Object} tabstopTextTree: Opaque object returned from parseLiveText()
 * @returns {Long}: Number of Unicode Characters inserted in the buffer.
 * @throws {LiveTextParserException}: Contains a message, usually with a parsing error.
 */
this.insertLiveText = function(scimoz_, insertionPoint, tabstopTextTree) {
    scimoz = scimoz_;
    pos = insertionPoint;
    return insertLiveTextParts(tabstopTextTree.nodes);
};

/**************** Tabstop Navigation and Management ****************/

/**
 * When the user presses the tab key, this method first determines
 * if there is a current set of linked tabstops to unlink, and
 * then finds the next tabstop to visit.  If that tabstop is the
 * head of a set of tabstops linked by the same backref, it colors
 * each tabstop with the TSC indicator ("Tabstop Current"), and also
 * places an invisible TSCZW indicator to the right of each one, to
 * allow the user to delete TSC-indicated text.
 * @param {Object} view: A Komodo view object
 * @returns {Boolean}: A true return value means this routine handled
 * the tab key, and there's no more to do.  A false value means that
 * the tab key event needs to be handled elsewhere.
 */
this.moveToNextTabstop = function(view) {
    if (!view.koDoc.hasTabstopInsertionTable) {
        return false;
    }
    var tabstopInsertionTable = view.koDoc.getTabstopInsertionTable({});
    var startingPos = 0;
    var lim = tabstopInsertionTable.length;
    var scimoz = view.scimoz;
    var containsLinks = this._containsActiveLink(scimoz, TSCZW);
    if (containsLinks) {
        this.clearLinkedTabstops(scimoz, view);
    }
    if (lim === 0) {
        view.koDoc.clearTabstopInsertionTable();
        // Assume the last selected region was due to hitting a tabstop,
        // and move off it.  Otherwise we're stuck selecting it forever.
        if (scimoz.selectionStart < scimoz.selectionEnd) {
            scimoz.selectionStart = scimoz.selectionEnd;
        }
        return containsLinks; // further process the tab unless we turned off tabbing this time
    }
    var tsInfo, spos = startingPos, epos, finalSPos = -1, finalEPos, idx = 0;
    // Look for an entry we can use
    var sawBackref0 = false;
    for (idx = 0; idx < lim; idx++) {
        tsInfo = tabstopInsertionTable[idx];
        // Backref #0 is visited last.  If it floats to the top, ignore it.
        if (tsInfo.isBackref) {
            if (tsInfo.backrefNumber === 0) {
                sawBackref0 = true;
                if (idx === 0) {
                    startingPos = 0; // gotta move to the start
                }
                [spos, epos] = this.findByIndicator(scimoz, tsInfo.indicator, startingPos);
                if (spos == -1) {
                    log.error("Komodo internal error: In: moveToNextTabstop:: Couldn't find indicator " + tsInfo.indicator  + " after pos "
                         + startingPos);
                    continue;
                }
                startingPos = epos;
                continue;
            }
            break;
        }
        this._deleteTabstopItem(view, tabstopInsertionTable, idx);
        var indicator = tsInfo.indicator;
        [spos, epos] = this.findByIndicator(scimoz, indicator, startingPos);
        if (spos == -1) {
            log.error("Komodo internal error: In: moveToNextTabstop:: Couldn't find indicator " + indicator  + " after pos "
                 + startingPos);
            return false;
        }
        this._useIndicator(view, scimoz, indicator, spos, epos);
        scimoz.selectionStart = spos;
        scimoz.selectionEnd = indicator == TSZW ? spos : epos;
        scimoz.scrollCaret();
        this._ensureInsertMode();
        return true;
    }
    if (idx == lim && sawBackref0) {
        idx = 0;
        tsInfo = tabstopInsertionTable[idx];
        spos = 0; // gotta move to the start yet again
    }
    if (!tsInfo.isBackref) {
        log.error("Komodo internal error: In: moveToNextTabstop:: Expecting tsInfo["
             + idx
             + "], '!tsInfo.isBackref' = "
             + (!tsInfo.isBackref)
             + " but it's not a backref\n");
        return false;
    }
    var backrefNumber = tsInfo.backrefNumber;
    var searchIndicator;
    var hasOtherLinks = this._hasOtherLinks(tabstopInsertionTable, backrefNumber, idx + 1);
    // sparse array - where to resume a search for a particular indicator.
    // Do this because indicated regions can nest.
    var lastPointByIndicator = [];
    var setupLinkedSet = false;
    epos = startingPos;
    while (idx < lim) {
        tsInfo = tabstopInsertionTable[idx];
        searchIndicator = tsInfo.indicator;
        if (!(searchIndicator in lastPointByIndicator)) {
            lastPointByIndicator[searchIndicator] = spos;
        }
        startingPos = lastPointByIndicator[searchIndicator];
        [spos, epos] = this.findByIndicator(scimoz, searchIndicator, startingPos);
        if (finalSPos == -1) {
            [finalSPos, finalEPos] = [spos, searchIndicator == TSZW ? spos : epos];
        }
        if (spos == -1) {
            log.error("Komodo internal error: In: moveToNextTabstop:: Couldn't find indicator " + tsInfo.indicator  + " after pos "
                 + startingPos);
            // break;
            idx += 1;
        }
        lastPointByIndicator[searchIndicator] = epos;
        if (tsInfo.backrefNumber == backrefNumber) {
            this._useIndicator(view, scimoz, tsInfo.indicator, spos, epos, hasOtherLinks);
            this._deleteTabstopItem(view, tabstopInsertionTable, idx);
            if (!hasOtherLinks) {
                break;
            }
            setupLinkedSet = true;
            lim -= 1;
        } else {
            idx += 1;
        }
    }
    if (finalSPos != -1) {
        scimoz.selectionStart = finalSPos;
        scimoz.selectionEnd = finalEPos;
        scimoz.scrollCaret();
    }
    if (setupLinkedSet) {
        view.scintilla.inLinkedTabstop = true;
        scimoz.beginUndoAction();
        view.addEventListener('current_view_linecol_changed',
                              this.checkForObsoleteTabstopsHandler, false);
    }
    this._ensureInsertMode();
    return true;
};

this.checkForObsoleteTabstopsHandler = function(event) {
    return ko.tabstops.checkForObsoleteTabstops(event);
};

this.checkForObsoleteTabstops = function(event) {
    var view = event.target;
    var scimoz = view.scimoz;
    if (!scimoz) {
        view.removeEventListener('current_view_linecol_changed',
                                   this.checkForObsoleteTabstopsHandler, false);
        // No more scimoz
        return;
    }
    if (!scimoz.indicatorAllOnFor(scimoz.selectionStart, TS_BITMASK)) {
        // Bailing out of the current tabstop, as we've moved away\n");
        view.removeEventListener('current_view_linecol_changed',
                                 this.checkForObsoleteTabstopsHandler, false);
        scimoz.endUndoAction();
    }
};

this._hasOtherLinks = function(tabstopInsertionTable, backrefNumber, idx) {
    for (var lim = tabstopInsertionTable.length; idx < lim; ++idx) {
        var tsInfo = tabstopInsertionTable[idx];
        if (tsInfo.isBackref && tsInfo.backrefNumber == backrefNumber) {
            return true;
        }
    }
    return false;
};

/**
 * Watches for backspace at the start of a tabstop.  Further
 * comments in the code.
 * 
 * @param {Scimoz} scimoz_: The usual Scimoz object.
 */
this.handleBackspace = function(scimoz) {
    /* If we're deleting at the beginning of a linked region,
     * we need to unlink -- we're leaving the boundary.
     * Otherwise it's ambiguous which chars to add to other
     * linked regions.
     *
     * Example:
     * my $[foo] = 3;
     * print "$[foo]\n";
     *
     * Now backspace the '$' in the first line:
     * my [foo] = 3;
     * print "$[foo]\n";
     *
     * Now type it back. We'll end up with this:
     * my [$foo] = 3;
     * print "$[$foo]\n";
    */
    if (scimoz.selectionStart < scimoz.selectionEnd) {
        // We're only interested in cases where we're deleting the char to the left.
        return;
    }
    var pos = scimoz.currentPos;
    if (pos > 0) {
        var followingSet = scimoz.indicatorAllOnFor(pos) & LINKED_TABSTOP_BITMASK;
        if (followingSet) {
            var prevSet = scimoz.indicatorAllOnFor(scimoz.positionBefore(pos)) & LINKED_TABSTOP_BITMASK;
            if (!prevSet) {
                this.clearLinkedTabstops(scimoz, ko.views.manager.currentView);
            }
        }
    }
};


/**
 * Similar to handleBackspace, but watches for delete actions
 * at the right of the indicator.  This routine is simpler:
 * if we're about to step on the TSCZW indicator at the end of
 * a linked tabstop, it's time to unlink them.
 * 
 * @param {Scimoz} scimoz_: The usual Scimoz object.
 */
this.handleDelete = function(scimoz) {
    if (scimoz.selectionStart < scimoz.selectionEnd) {
        // We're only interested in cases where we're deleting the char to the right.
        return;
    }
    if (scimoz.indicatorAllOnFor(scimoz.currentPos) & (1 << TSCZW)) {
        // If we're stepping on the boundary indicator, unlink them
        this.clearLinkedTabstops(scimoz, ko.views.manager.currentView);
    }
};

/**
 * If we're removing a full TSC, but not the trailing TSCZW, remove the linked
 * items anyway.  Otherwise we end up in a state where modifying the parent
 * text doesn't affect the linked tabstops, but if we append at this point,
 * the other tabstops get the update.  It's asymmetrical, so we'll unlink.
 */
this.handleDeleteByUndo = function(view, scimoz, position, length) {
    if (view.scintilla.inLinkedTabstop
        && !this._containsActiveLink(scimoz, TSC)) {
        // This has to be done in a timeout because it modifies the undo-stack.
        setTimeout(this.clearLinkedTabstops, 0, scimoz, view);
    }
};
    

/**
 * When the user makes a modification in a document with tabstops, this routine
 * handles the change.  It handles two main events:
 * 1. The first linked tabstop has changed.  All other linked tabstops are
 *    updated with the new value.
 * 2. Text containing indicators is about to be deleted.  This routine
 *    removes the appropriate entries from the view's tabstopIndicatorTable.
 *    
 * @param {Long} modificationType: SC_MOD_BEFOREDELETE|SC_MOD_INSERTTEXT|SC_MOD_DELETETEXT
 * @param {Object} view: Komodo view object
 * @param {Long} position: Position of the start of the changed region
 * @param {String} text: For SC_MOD_INSERTTEXT, utf-16 encoding of added text
 * @param {Long} length: Length of the change to be made, based on utf-8 encoding of the text
 * ]]
 */
this.updateLinkedBackrefs = function updateLinkedBackrefs(
    modificationType,
    view,
    position,
    unicodeText,
    utf8Length
) {
    /*
     * 1. On a delete-text: get the new contents of the current TSC region, and
     *    set all other TSC regions to the same.  If the whole region is deleted,
     *    we still have a TSCZW follower marker.
     * 2. On an insert-text: if there's a TSC region to the left, extend it.  If
     *    there's a TSCZW region to the right, copy the current text to the
     *    left of each TSCZW, and set each copy to a TSC.
    */
    var spos, epos, newUnicodeText, prevPosition, finalByteCount, scimoz = view.scimoz;
    switch (modificationType & 0x0c03) {
        case SC_MOD_BEFOREDELETE:
            // Remove any indicators from the tabstop table that we're
            // about to delete.
            this._removeIndicatorsBeforeDelete(view, position, position + utf8Length);
            return;
        case SC_MOD_DELETETEXT:
            if (position > 0 && scimoz.indicatorValueAt(TSC, position - 1)) {
                prevPosition = scimoz.positionBefore(position);
                spos = scimoz.indicatorStart(TSC, prevPosition);
                epos = scimoz.indicatorEnd(TSC, prevPosition);
                newUnicodeText = scimoz.getTextRange(spos, epos);
                finalByteCount = epos - spos;
                this._updateAllHits(scimoz, position + finalByteCount, TSC,
                                    newUnicodeText, finalByteCount);
            } else if (scimoz.indicatorValueAt(TSC, position)
                       && ((spos = scimoz.indicatorStart(TSC, position))
                            == position)) {
                epos = scimoz.indicatorEnd(TSC, position);
                newUnicodeText = scimoz.getTextRange(spos, epos);
                this._updateAllHits(scimoz, epos, TSC, newUnicodeText, epos - spos);
            } else if (scimoz.indicatorValueAt(TSCZW, position)) {
                // Need to delete all the other TSCs
                this._clearAllCurrentHits(scimoz, position);
            }
            return;
        case SC_MOD_INSERTTEXT:
            var currentUnicodeText;
            if (position > 0 && scimoz.indicatorValueAt(TSC, (prevPosition =
                                                              scimoz.positionBefore(position)))) {
                spos = scimoz.indicatorStart(TSC, prevPosition);
                epos = scimoz.indicatorEnd(TSC, prevPosition);
                currentUnicodeText = scimoz.getTextRange(spos, epos);
                finalByteCount = epos - spos;
                if (!scimoz.indicatorValueAt(TSC, position)) {
                    // Text was added to the right of the indicated buffer
                    finalByteCount += utf8Length;
                    currentUnicodeText += unicodeText;
                    scimoz.indicatorCurrent = TSC;
                    scimoz.indicatorFillRange(spos, finalByteCount);
                }
                this._updateAllHits(scimoz, spos + finalByteCount, TSC,
                                    currentUnicodeText,
                                    finalByteCount);
            } else if (scimoz.indicatorValueAt(TSC, position)) {
                // Text was added inside, or to the left of the indicated region
                spos = scimoz.indicatorStart(TSC, position);
                epos = scimoz.indicatorEnd(TSC, position);
                currentUnicodeText = unicodeText + scimoz.getTextRange(spos, epos);
                scimoz.indicatorCurrent = TSC;
                var newWordStartPos = position - utf8Length;
                finalByteCount = epos - newWordStartPos;
                scimoz.indicatorFillRange(newWordStartPos, finalByteCount);
                this._updateAllHits(scimoz, newWordStartPos, TSC, currentUnicodeText, finalByteCount);
            } else if (scimoz.indicatorValueAt(TSC, position + utf8Length)) {
                // We moved to the start of the region, and typed something.
                spos = scimoz.indicatorStart(TSC, position + utf8Length);
                epos = scimoz.indicatorEnd(TSC, position + utf8Length);
                currentUnicodeText = unicodeText + scimoz.getTextRange(spos, epos);
                finalByteCount = utf8Length + epos - spos;
                scimoz.indicatorCurrent = TSC;
                scimoz.indicatorFillRange(position, epos - position);
                this._updateAllHits(scimoz, epos, TSC, currentUnicodeText, finalByteCount);
            } else if (scimoz.indicatorValueAt(TSCZW, position + utf8Length)) {
                // Update all the TSCZW indicators to TSC ones
                scimoz.indicatorCurrent = TSC;
                scimoz.indicatorFillRange(position, utf8Length);
                this._updateAllZeroWidthHits(scimoz, scimoz.indicatorEnd(TSCZW, position + utf8Length),
                                             unicodeText, utf8Length);
            }
            return;
    }
};


/**
 * Are we the first string to be added in a linked tabstop?
 */
this.atEmptyLinkedTabstop = function(scimoz,
                                     position,
                                     utf8Length) {
    if (!scimoz.indicatorValueAt(TSCZW, position + utf8Length)) {
        return false;
    }
    if (position == 0) {
        return true;
    }
    return !scimoz.indicatorValueAt(TSC, scimoz.positionBefore(position));
};

/**
 * This method creates non-empty tabstops where only a zero-width indicator
 * link was found.  It's necessary because the indicator might be detected
 * when 'a' is typed like so:
 *
 * a<*>
 *
 * but by the time it's processed, the user has typed 'sd', leading to this
 * situation:
 *
 * asd<*>
 *
 * In this case, only the 'd' is found to be next to a zero-width indicator,
 * so the 'a' and 's' don't appear in the other tabstops.  This function
 * fixes that.
 */

this.forceUpdateAllZeroWidthLinks = function(view,
                                             scimoz,
                                             position,
                                             text,
                                             utf8Length) {
    if (scimoz.indicatorValueAt(TSC, position)) {
        this.updateLinkedBackrefs(SC_MOD_INSERTTEXT, view, position, text, utf8Length);
    } else {
        var tcszw_posn = scimoz.indicatorStart(TSCZW,
                                               scimoz.indicatorEnd(TSCZW, position));
        // Update all the TSCZW indicators to TSC ones
        scimoz.indicatorCurrent = TSC;
        scimoz.indicatorFillRange(position, tcszw_posn - position);
        var newText = scimoz.getTextRange(scimoz.indicatorStart(TSC, position),
                                          scimoz.indicatorEnd(TSC, position));
        this._updateAllZeroWidthHits(scimoz, scimoz.indicatorEnd(TSCZW, tcszw_posn),
                                     newText, ko.stringutils.bytelength(newText));
    }    
};

/**
 * Remove linked tabstops from the document.
 * @param {Scimoz} scimoz_: The usual Scimoz object.
 */
this.clearLinkedTabstops = function(scimoz, view) {
    if (typeof(view) == "undefined") {
        view = ko.views.manager.currentView;
    }
    if (view.scintilla.inLinkedTabstop) {
        // Guard multiple sequential undo's.
        view.removeEventListener('current_view_linecol_changed',
                                 this.checkForObsoleteTabstopsHandler, false);
        scimoz.endUndoAction();
        view.scintilla.inLinkedTabstop = false;
        scimoz.indicatorCurrent = TSC;
        scimoz.indicatorClearRange(0, scimoz.textLength);
        scimoz.indicatorCurrent = TSCZW;
        scimoz.indicatorClearRange(0, scimoz.textLength);
    }
};

/**
 * Remove all traces of tabstops from the view and document.
 * @param {Object} view: Komodo view object
 */
this.clearTabstopInfo = function(view) {
    var scimoz = view.scimoz;
    if (this._containsActiveLink(scimoz, TSCZW)
        || this._containsActiveLink(scimoz, TSC)) {
        this.clearLinkedTabstops(scimoz, view);
    }
    view.koDoc.setTabstopInsertionTable(0, []);
    var docLength = scimoz.length; // XXX: wrong with utf8?
    for (var indicator = TSZW; indicator <= TS5; indicator++) {
        scimoz.indicatorCurrent = indicator;
        scimoz.indicatorClearRange(0, docLength);
    }
};

this.textHasTabstops = function(text) {
    return tabstop_re.test(text);
};

/**************** Private: ****************/

// Local vars and constants:

var scimoz, pos;
const TS1 = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TS1;
const TS2 = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TS2;
const TS3 = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TS3;
const TS4 = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TS4;
const TS5 = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TS5;
const TSZW = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TSZW;
const TSC = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TSC;
const TSCZW = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TSCZW;
const TS_BITMASK = Components.interfaces.koILintResult.DECORATOR_TABSTOP_BITMASK;
const DECORATOR_SOFT_CHAR = Components.interfaces.koILintResult.DECORATOR_SOFT_CHAR;
const LINKED_TABSTOP_BITMASK = (1 << TSC)|(1 << TSCZW);

const tabstop_re = /\[\[%tabstop[\d:]/;

// Parsing Internals

/**************** LiveTextPlain ****************/

this.LiveTextPlain = function(text) {
    this.text = text;
};

this.LiveTextPlain.prototype.insertLiveTextPart = function() {
    scimoz.insertText(pos, this.text);
    return ko.stringutils.bytelength(this.text);
};

this.LiveTextPlain.prototype.describe = function(indent) {
    return indent + "[Text: " + this.text + "]\n";
};
    
/**************** LiveTextSoftChars ****************/

this.LiveTextSoftChars = function(text) {
    this.text = text;
    this.indicator = DECORATOR_SOFT_CHAR;
};

this.LiveTextSoftChars.prototype.insertLiveTextPart = function() {
    var spos = pos;
    var len = ko.stringutils.bytelength(this.text);
    scimoz.insertText(pos, this.text);
    scimoz.indicatorCurrent = this.indicator;
    scimoz.indicatorFillRange(spos, len);
    return len;
};

this.LiveTextSoftChars.prototype.describe = function(indent) {
    return indent + "[SoftChars: " + this.text + "]\n";
};
    
/**************** LiveTextTabstopNested ****************/
this.LiveTextTabstopNested = function(indicator) {
    this.indicator = indicator;
};
this.LiveTextTabstopNested.prototype.insertLiveTextPart = function() {
    var spos = pos;
    var len = insertLiveTextParts(this.nodes);
    scimoz.indicatorCurrent = this.indicator;
    scimoz.indicatorFillRange(spos, len);
    return len;
};

this.LiveTextTabstopNested.prototype.describe = function(indent) {
    var parts = [];
    if (this.indicator) {
        parts.push(indent + "[Nested: " + this.indicator + "]\n");
    }
    for (var i = 0; i < this.nodes.length; i++) {
        var node = this.nodes[i];
        parts.push(node.describe(indent + "  "));
    }
    if (this.indicator) {
        parts.push(indent + "[/Nested: " + this.indicator + "]\n");
    }
    return parts.join("\n");
};
/**************** LiveTextTabstopEmpty ****************/
this.LiveTextTabstopEmpty = function() {
    this.indicator = TSZW;
};
this.LiveTextTabstopEmpty.prototype.insertLiveTextPart = function() {
    return ko.tabstops.insertEmptyIndicator(scimoz, pos, this.indicator);
};

this.LiveTextTabstopEmpty.prototype.describe = function(indent) {
    return indent + "[Empty: " + this.indicator + "]\n";
};

/**************** LiveTextTabstopText ****************/
this.LiveTextTabstopText = function(indicator, text) {
    this.indicator = indicator;
    this.text = text;
};

this.LiveTextTabstopText.prototype.insertLiveTextPart = function() {
    return insertLiveTextPartHelper(this.text, this.indicator);
};

this.LiveTextTabstopText.prototype.describe = function(indent) {
    return indent + "[TextTabstop: " + this.indicator + ", " + this.text + "]\n";
};

/**************** LiveTextTabstopBackrefDef ****************/
this.LiveTextTabstopBackrefDef = function(indicator, backrefNum, text) {
    this.indicator = indicator;
    this.backrefNum = backrefNum;
    this.text = text;
};
this.LiveTextTabstopBackrefDef.prototype.insertLiveTextPart = function() {
    return insertLiveTextPartHelper(this.text,
                                   this.indicator);
};

this.LiveTextTabstopBackrefDef.prototype.describe = function(indent) {
    return indent + "[BackrefDef: " + this.backrefNum + ", " + this.indicator + ", " + (this.text || '<none>') + "]\n";
};

/**************** LiveTextTabstopBackrefUse ****************/
this.LiveTextTabstopBackrefUse = function(indicator, backrefNum, text) {
    this.indicator = indicator;
    this.backrefNum = backrefNum;
    this.text = text;
};
this.LiveTextTabstopBackrefUse.prototype.insertLiveTextPart = function() {
    return insertLiveTextPartHelper(this.text, 
                                   this.indicator);
};

this.LiveTextTabstopBackrefUse.prototype.describe = function(indent) {
    return indent + "[BackrefUse: " + this.backrefNum + ", " + this.indicator + ", " + (this.text || '<none>') + "]\n";
};

/**************** LiveText Parser ****************/
/*
Grammar:
LiveText ::= (Text | Tabstop)*
Text ::= (.* - '[[%tabstop' | '%'x)*
Tabstop ::= '[[%tabstop' (\d+ ':'? Text ']]' | '%' | ':' Name ']]' | LiveText ']]'
Name ::= NameChar [NameChar | digit | '_']*
*/
// Globals:
var backrefTable, tabstopInsertionTable, tabstopTextTree;

const TARGET_START = '[[%tabstop';
const TARGET_END = ']]';

const SOFT_CHAR_START = '[[%soft:';
const SOFT_CHAR_START_LEN = SOFT_CHAR_START.length;

function parseLiveText_clear() {
    backrefTable = {}; // sparse array
    tabstopInsertionTable = [];
    tabstopTextTree = [];  // Array of LiveTextTabStop nodes (see above)
    
}

this.TabstopInsertionNode = function(indicator, isBackref, backrefNumber, isBackrefAnchor) {
    this.indicator = indicator;
    if (typeof(isBackref) == 'undefined') isBackref = false;
    this.isBackref = isBackref;
    if (isBackref) {
        this.backrefNumber = backrefNumber;
        this.isBackrefAnchor = isBackrefAnchor;
    }
};
this.TabstopInsertionNode.prototype.describe = function() {
    var s = "Ind:" + this.indicator;
    if (this.isBackref) {
        s += ", Backref:" + this.backrefNumber;
        if (this.isBackrefAnchor) {
            s += ", anchor";
        }
    }
    return s;
};

this.dumpParseResult = function(tree) {
    var b = tree.backrefTable;
    dump("backrefTable:\n");
    for (var p in b) {
        dump("  " + p + ": " + b[p] + "\n");
    }
    dump("\n" + "tabstopInsertionTable:");
    b = tree.tabstopInsertionTable;
    for (var node, i = 0; node = b[i]; i++) {
        dump("  " + b[i].describe() + "\n");
    }
    dump("\n" + "tree:\n");
    dump(tree.describe("") + "\n");
};


this.LiveTextParser = function() {
};

this.LiveTextParser.prototype.parse = function(liveText) {
    parseLiveText_clear();
    this.idx = 0;
    this.subjectText = liveText;
    this.lim = liveText.length;
    /* Indicators:
     * If two overalapping regions have the same indicator, Scintilla
     * treats them as one single region.  So we need to apply the indicators
     * so, when they're applied, no two continguous or nested regions have
     * the same indicator.  We can reuse an indicator afterwards though.
     */
    this.availIndicators = [TS5, TS4, TS3, TS2, TS1];
    this.lastIndicatorInUse = null;
    this.nestedIndicatorsInUse = [];
    // This list tracks cascading tabstops (unlikely, but...), like the following:
    // [[%ts:first[[%ts:second[[%ts:third]]]]]][[%ts:cont]]
    // If we assign the first three tabstops with indicators
    // ts1, ts2, and ts3, then the continuation tabstop can only take ts4 or ts5.
    // After the continuation, ts1, ts2, and ts3 are all available again.
    this.endingIndicatorsInUse = [];
    var node = new ko.tabstops.LiveTextTabstopNested(-1);
    this.parseNestedLiveText(node);
    node.backrefTable = backrefTable;
    node.tabstopInsertionTable = tabstopInsertionTable;
    return node;
};

this.LiveTextParser.prototype.parseNestedLiveText = function(parentNode, isInner) {
    if (typeof(isInner) == 'undefined') isInner = false;
    parentNode.nodes = [];
    var node;
    while (this.idx < this.lim) {
        if (isInner && this.subjectText.substr(this.idx, 2) == TARGET_END) {
            this.idx += TARGET_END.length;
            if (this.lastIndicatorInUse) {
                this.endingIndicatorsInUse.push(this.lastIndicatorInUse);
                this.lastIndicatorInUse = null;
            }
            return;
        } else if (this.lookingAtTabstop()) {
            node = this.parseTabstop();
        } else if (this.lookingAtSoftChar()) {
            node = this.parseSoftCharShortcut();
        } else {
            node = this.parseTextBlock(isInner);
            this._releaseIndicators();
        }
        parentNode.nodes.push(node);
    }
    if (isInner) {
        this.throwParseException(TARGET_END, "Parsing error");
    }
};

this.LiveTextParser.prototype.throwParseException = function(expecting, reason) {
    var snippetText = this.subjectText;
    var droppedText = '!@#_currentPos!@#_anchor';
    var droppedPos = snippetText.indexOf(droppedText);
    var idxPos = this.idx;
    if (droppedPos >= 0) {
        if (idxPos > droppedPos) {
            idxPos -= droppedText.length;
        }
        snippetText = (snippetText.substr(0, droppedPos)
                       + snippetText.substr(droppedPos + droppedText.length));
    }
    var lineNumber = (snippetText.substr(0, idxPos).match(/\n/g) || []).length + 1;
    var msg = ("Snippet parsing error: " + reason + ": "
               + " expecting " + expecting
               + " at line " + lineNumber + ":");
    throw new ko.tabstops.LiveTextParserException(msg, snippetText);
};

this.LiveTextParser.prototype._availableIndicatorCheck = function() {
    if (!this.availIndicators.length) {
        throw new ko.tabstops.LiveTextParserException("The snippet is too complex: ", this.subjectText);
    }
};

this.LiveTextParser.prototype._releaseIndicators = function() {
    if (this.lastIndicatorInUse) {
        this.availIndicators.push(this.lastIndicatorInUse);
        this.lastIndicatorInUse = null;
    }
    while(this.endingIndicatorsInUse.length) {
        this.availIndicators.push(this.endingIndicatorsInUse.pop());
    }
};

this.LiveTextParser.prototype._shuffleIndicators = function(indicator) {
    this._releaseIndicators();
    this.lastIndicatorInUse = indicator;
};

this.LiveTextParser.prototype.lookingAtTabstop = function() {
    return this.subjectText.substr(this.idx, TARGET_START.length) == TARGET_START;
};

this.LiveTextParser.prototype.lookingAtSoftChar = function() {
    return this.subjectText.substr(this.idx, SOFT_CHAR_START_LEN) == SOFT_CHAR_START;
};

this.LiveTextParser.prototype.parseTextBlock = function(isInner) {
    var targetPoint = this.subjectText.indexOf(TARGET_START, this.idx);
    var softCharStart = this.subjectText.indexOf(SOFT_CHAR_START, this.idx);
    var endPoint = !isInner ? -1 : this.subjectText.indexOf(TARGET_END, this.idx);
    var text;
    if ((softCharStart != -1)
        && (targetPoint == -1 || softCharStart < targetPoint)
        && (endPoint == -1 || softCharStart < endPoint)) {
        text = this.subjectText.substring(this.idx, softCharStart);
        this.idx = softCharStart;
        return new ko.tabstops.LiveTextPlain(text);
    }
    if (targetPoint == -1) {
        if (endPoint == -1) {
            text = this.subjectText.substring(this.idx);
            this.idx = this.lim;
        } else {
            text = this.subjectText.substring(this.idx, endPoint);
            this.idx = endPoint;
        }
    } else if (endPoint == -1) {
        text = this.subjectText.substring(this.idx, targetPoint);
        this.idx = targetPoint;
    } else {
        // Stop at the punctuation block
        var finalPoint = Math.min(targetPoint, endPoint);
        text = this.subjectText.substring(this.idx, finalPoint);
        this.idx = finalPoint;
    }
    return new ko.tabstops.LiveTextPlain(text);
};

this.LiveTextParser.prototype._parseTabstopNameSequence = function() {
    var retStrParts = [];
    var prevStart = this.idx;
    for (; this.idx < this.lim; this.idx += 1) {
        var p1 = this.subjectText.indexOf('\\', this.idx);
        var p2 = this.subjectText.indexOf(TARGET_END, this.idx);
        if (p1 == -1) {
            if (p2 == -1) {
                this.throwParseException(TARGET_END, "Parsing error");
            }
            this.idx = p2 + TARGET_END.length;
            retStrParts.push(this.subjectText.substring(prevStart, p2));
            break;
        } else {
            if (p1 < p2 || p2 == -1) {
                // Escape only ']' and '\'.  Everywhere else, a backslash is a backslash
                var nextChar = this.subjectText.substr(p1 + 1, 1);
                if (nextChar == ']' || nextChar == '\\') {
                    retStrParts.push(this.subjectText.substring(prevStart, p1));
                    prevStart = this.idx = p1 + 1;
                }
            } else {
                retStrParts.push(this.subjectText.substring(prevStart, p2));
                this.idx = p2 + TARGET_END.length;
                break;
            }
        }
    }
    return retStrParts.join("");
};

this.LiveTextParser.prototype.parseTabstop = function() {
    if (this.subjectText.substr(this.idx, TARGET_START.length) != TARGET_START) {
        this.throwParseException(target, 'Internal error');
    }
    this.idx += TARGET_START.length;
    var indicator, subjectRemainder = this.subjectText.substr(this.idx);
    if (subjectRemainder.substr(0, TARGET_END.length) == TARGET_END) {
        this.idx += TARGET_END.length;
        tabstopInsertionTable.push(new ko.tabstops.TabstopInsertionNode(TSZW, false));
        return new ko.tabstops.LiveTextTabstopEmpty();
    }
    var text, m = subjectRemainder.match(/^(\d+)/);
    if (m) {
        // numbered tabstops don't contain nested content
        var backrefStr = m[0];
        var backrefNum = parseInt(backrefStr, 10);
        this.idx += backrefStr.length;
        var nodeClass = ko.tabstops.LiveTextTabstopBackrefUse;
        var haveBackref = (backrefNum in backrefTable);
        if (this.subjectText.substr(this.idx, 1) == ':') {
            this.idx += 1;
            text = this._parseTabstopNameSequence(true); //@@@ - this allows %x => x
            if (!haveBackref) {
                backrefTable[backrefNum] = text;
                nodeClass = ko.tabstops.LiveTextTabstopBackrefDef;
            } else if (text != backrefTable[backrefNum]) {
                ko.dialogs.alert("Tabstop back-reference #"
                                 + backrefNum
                                 + " has default text "
                                 + backrefTable[backrefNum]
                                 + ", supplied value of <"
                                 + text
                                 + "> will be ignored.\n");
                text = backrefTable[backrefNum];
            }
        } else {
            if (!haveBackref) {
                text = backrefTable[backrefNum] = "";
                nodeClass = ko.tabstops.LiveTextTabstopBackrefDef;
            } else {
                text = backrefTable[backrefNum];
            }
            if (this.subjectText.substr(this.idx, TARGET_END.length) != TARGET_END) {
                this.throwParseException(TARGET_END, "Parsing error");
            }
            this.idx += TARGET_END.length;
        }
        if (text !== null && text.length) {
            this._availableIndicatorCheck();
            indicator = this.availIndicators.pop();
            this._shuffleIndicators(indicator);
        } else {
            indicator = TSZW;
        }
        tabstopInsertionTable.push(new ko.tabstops.TabstopInsertionNode(indicator, true, backrefNum, !haveBackref));
        return new nodeClass(indicator, backrefNum, text);
    }
    else if (subjectRemainder.substr(0, 1) == ':') {
        this.idx += 1;
        var targetPoint = subjectRemainder.indexOf(TARGET_START);
        var softCharStart = subjectRemainder.indexOf(SOFT_CHAR_START);
        var endPoint = subjectRemainder.indexOf(TARGET_END);
        if (endPoint == -1) this.throwParseException(TARGET_END, "Parsing error");
        if ((targetPoint == -1 || (endPoint < targetPoint))
            && (softCharStart == -1 || (endPoint < softCharStart))) {
            text = this._parseTabstopNameSequence();
            if (text.length === 0) {
                tabstopInsertionTable.push(new ko.tabstops.TabstopInsertionNode(TSZW, false));
                return new ko.tabstops.LiveTextTabstopEmpty();
            }
            this._availableIndicatorCheck();
            indicator = this.availIndicators.pop();
            this._shuffleIndicators(indicator);
            tabstopInsertionTable.push(new ko.tabstops.TabstopInsertionNode(indicator, false));
            return new ko.tabstops.LiveTextTabstopText(indicator, text);
        }
        this._availableIndicatorCheck();
        this.nestedIndicatorsInUse.push(indicator = this.availIndicators.pop());
        if (this.lastIndicatorInUse) {
            this.availIndicators.push(this.lastIndicatorInUse);
            this.lastIndicatorInUse = null;
        }
        tabstopInsertionTable.push(new ko.tabstops.TabstopInsertionNode(indicator, false));
        var node = new ko.tabstops.LiveTextTabstopNested(indicator);
        this.parseNestedLiveText(node, true);
        this.lastIndicatorInUse = this.nestedIndicatorsInUse.pop();
        return node;
    }
    else {
        this.throwParseException("a numeric sequence or ':'", "Parsing error");
    }
    return null; // languages with exceptions shouldn't complain about missing returns
};

this.LiveTextParser.prototype.parseSoftCharShortcut = function() {
    // Precondition: we matched SOFT_CHAR_START at this.idx
    if (this.idx + SOFT_CHAR_START_LEN >= this.subjectText.length + 1) {
        this.throwParseException(target, 'Invalid shortcut');
    }
    this.idx += SOFT_CHAR_START_LEN;
    // Add 1 to this.idx so we can emit a soft close-square-bracket:
    // [[%soft:]]] -- emits one ]
    // [[%soft:]]][[%soft:]>]] -- emits soft ]]>
    var softEndIndex = this.subjectText.indexOf(']]', this.idx + 1);
    if (softEndIndex == -1) {
        this.throwParseException(target, "Expected ']]'");
    }
    var softChars = this.subjectText.substring(this.idx, softEndIndex);
    this.idx = softEndIndex + 2;
    return new ko.tabstops.LiveTextSoftChars(softChars);
};

// Private Insertion Functions

function insertLiveTextPartHelper(s, indicator) {
    //if (s is empty ... set the indicator to a following early one)
    if (s === null || s.length === 0) {
        return ko.tabstops.insertEmptyIndicator(scimoz, pos, indicator);
    }
    scimoz.insertText(pos, s);
    var slen = ko.stringutils.bytelength(s);
    scimoz.indicatorCurrent = indicator;
    scimoz.indicatorFillRange(pos, slen);
    return slen;
}

function insertLiveTextParts(nodes) {
    // Insert items backwards, to handle empty indicator regions correctly.
    // Also, it means that pos never moves.
    var len = 0;
    for (var i = nodes.length - 1; i >= 0; i--) {
        len += nodes[i].insertLiveTextPart();
    }
    return len;
}


this.insertEmptyIndicator = function(scimoz, startingPos, indicator)  {
    var eolStrings = ['\r\n', '\r', '\n'];
    var eol = eolStrings[scimoz.eOLMode] || "\n";
    var slen, finalLen;
    if (startingPos == scimoz.textLength) {
        // Adding an empty tabstop at the end of the buffer
        scimoz.insertText(startingPos, eol);
        slen = finalLen = eol.length;
    } else {
        finalLen = 0;
        var ch = scimoz.getWCharAt(startingPos);
        if (ch == '\r' && scimoz.getCharAt(startingPos + 1) == 10) {
            slen = 2;
        } else {
            slen = ko.stringutils.bytelength(scimoz.getWCharAt(startingPos));
        }
    }
    scimoz.indicatorCurrent = indicator;
    scimoz.indicatorFillRange(startingPos, slen);
    return finalLen;
};

// Internal functions for handling tabstop navigation.

this.findByIndicator = function(scimoz, indicator, startingPos)  {
    var spos = scimoz.indicatorStart(indicator, startingPos);
    var epos = scimoz.indicatorEnd(indicator, spos);
    if (scimoz.indicatorValueAt(indicator, spos)) {
        return [spos, epos];
    }
    // Try the region after this region
    spos = scimoz.indicatorStart(indicator, epos);
    if (scimoz.indicatorValueAt(indicator, spos)) {
        return [spos, scimoz.indicatorEnd(indicator, spos)];
    }
    return [-1, -1];
};

this._useIndicator = function(view, scimoz, indicator, spos, epos, isBackref) {
    if (typeof(isBackref) == 'undefined') isBackref = false;
    var currentPos = scimoz.currentPos;
    var anchor = scimoz.anchor;
    if (currentPos > anchor) {
        // Clear indicators from the start of the selection
        currentPos = anchor;
    }
    if (spos > currentPos) {
        // Clear any soft-characters between one before the currentPos and 1
        // position before the new spos -- allow for the previous
        // char to be soft.
        var prevPos = scimoz.positionBefore(currentPos);
        var prevSpos = scimoz.positionBefore(spos);
        scimoz.indicatorCurrent = DECORATOR_SOFT_CHAR;
        scimoz.indicatorClearRange(prevPos, prevSpos - prevPos);
    }
    scimoz.indicatorCurrent = indicator;
    scimoz.indicatorClearRange(spos, epos - spos);
    if (isBackref) {
        var newIndicator = indicator == TSZW ? TSCZW : TSC;
        scimoz.indicatorCurrent = newIndicator;
        scimoz.indicatorFillRange(spos, epos - spos);
        if (newIndicator == TSC) {
            ko.views.wrapScintillaChange(view, function() {
                // Put a TSZW at the end of it.
                ko.tabstops.insertEmptyIndicator(scimoz, epos, TSCZW);
            });
        }
    }
};

this._ensureInsertMode = function() {
    if (gVimController && gVimController.enabled) {
        setTimeout(function() {
            gVimController.mode = VimController.MODE_INSERT;
        }, 100);
    }
};

this._containsActiveLink = function(scimoz, indicator) {
    var indicatorEnd = scimoz.indicatorEnd(indicator, 0);
    return indicatorEnd !== 0 && indicatorEnd != scimoz.textLength;
};

const SC_MOD_BEFOREDELETE = Components.interfaces.ISciMoz.SC_MOD_BEFOREDELETE;
const SC_MOD_INSERTTEXT = Components.interfaces.ISciMoz.SC_MOD_INSERTTEXT;
const SC_MOD_DELETETEXT = Components.interfaces.ISciMoz.SC_MOD_DELETETEXT;

this._updateAllHits = function(scimoz, position, indicator,
                               newUnicodeText, newUTF8Length) {
    var spos = position;
    var epos;
    var textLength = scimoz.length;
    var prevSet = null, followingSet = 0;
    while (spos < textLength) {
        [spos, epos] = this.findByIndicator(scimoz, indicator, spos);
        if (spos == -1) {
            break;
        } else if (typeof(epos) == 'undefined') {
           log.error("Komodo internal error: In: ko.tabstop._updateAllHits::  **** findByIndicator(scimoz, " + indicator
                 + ", spos) => spos="
                 + spos
                 + ", epos undefined\n");
            break;
        }
        if (spos > 0) {
            followingSet = scimoz.indicatorAllOnFor(spos);
            prevSet = scimoz.indicatorAllOnFor(scimoz.positionBefore(spos));
        }
        scimoz.targetStart = spos;
        scimoz.targetEnd = epos;
        scimoz.replaceTarget(newUnicodeText.length, newUnicodeText);
        scimoz.indicatorCurrent = indicator;
        scimoz.indicatorFillRange(spos, newUTF8Length);
        if (spos > 0) {
            this._restoreDroppedIndicators(followingSet, prevSet, scimoz, spos, newUTF8Length);
        }
        textLength += spos - epos + newUTF8Length;
        spos += newUTF8Length;
    }
};

this._updateAllZeroWidthHits = function(scimoz, position, newUnicodeText, newUTF8Length) {
    var spos, epos, textLength = scimoz.length;
    spos = position;
    var prevSet, followingSet;
    while (spos < textLength) {
        [spos, epos] = this.findByIndicator(scimoz, TSCZW, spos);
        if (spos == -1) {
            break;
        }
        prevSet = followingSet = 0;
        // Check for old text.
        if (spos > 0 && scimoz.indicatorValueAt(TSC, spos - 1)) {
            var prevSPos, prevEPos;
            [prevSPos, prevEPos] = this.findByIndicator(scimoz, TSC, spos - 1);
            if (prevEPos > 0) {
                followingSet = scimoz.indicatorAllOnFor(prevSPos);
                prevSet = scimoz.indicatorAllOnFor(scimoz.positionBefore(prevSPos));
            }
            // Replace old text with new
            scimoz.targetStart = prevSPos;
            scimoz.targetEnd = prevEPos;
            scimoz.replaceTarget(0, "");
            textLength -= prevEPos - prevSPos;
            spos -= prevEPos - prevSPos;
        } else if (spos > 0) {
            followingSet = scimoz.indicatorAllOnFor(spos);
            prevSet = scimoz.indicatorAllOnFor(scimoz.positionBefore(spos));
        }
        // Insert new text.
        scimoz.targetStart = spos;
        scimoz.targetEnd = spos;
        scimoz.replaceTarget(newUnicodeText.length, newUnicodeText);
        scimoz.indicatorCurrent = TSC;
        scimoz.indicatorFillRange(spos, newUTF8Length);
        this._restoreDroppedIndicators(followingSet, prevSet, scimoz, spos, newUTF8Length);
        textLength += newUTF8Length;
        spos = epos + newUTF8Length + 1;
    }
};

// And add indicators that were deleted when text was added to the start
// of an indicated region.  By default indicated regions grow on the right
// side towards the right, but not on the left side.
this._restoreDroppedIndicators =
function _restoreDroppedIndicators(followingSet, prevSet, scimoz, pos, utf8Len) {
    // And add indicators that were deleted above
    var neededIndicatorBitMask = (followingSet & ~prevSet) & TS_BITMASK;
    for (var indicatorCount = 0;
            neededIndicatorBitMask;
            neededIndicatorBitMask = neededIndicatorBitMask >> 1,
                indicatorCount++) {
        if (neededIndicatorBitMask & 0x01) {
            scimoz.indicatorCurrent = indicatorCount;
            scimoz.indicatorFillRange(pos, utf8Len);
        }
    }
}

//XXX Do we need to lock view.koDoc.tabstopInsertionTable? 
this._removeIndicatorsBeforeDelete = function(view, targetRangeStart, targetRangeEnd) {
    var tabstopInsertionTable = view.koDoc.getTabstopInsertionTable({});
    var lim = tabstopInsertionTable.length;
    var scimoz = view.scimoz;
    var tsInfo, spos, epos, idx = 0;
    var startingPos = 0;
    while (idx < lim) {
        tsInfo = tabstopInsertionTable[idx];
        [spos, epos] = this.findByIndicator(scimoz, tsInfo.indicator, startingPos);
        if (spos >= 0 && spos < targetRangeEnd && epos >= targetRangeStart) {
            scimoz.indicatorCurrent = tsInfo.indicator;
            scimoz.indicatorClearRange(spos, epos - spos);
            this._deleteTabstopItem(view, tabstopInsertionTable, idx);
            lim -= 1;
            if (lim === 0) {
                view.tabstopInsertionTable = null;
                break;
            }
        } else if (spos >= targetRangeEnd) {
            break;
        } else {
            idx += 1;
            // Stay here, look for next indicator.
        }
        startingPos = spos;
        // 2 different indicators can start at same spot, so don't move to end
    }
};

this._deleteTabstopItem = function(view, tabstopInsertionTable, idx) {
    tabstopInsertionTable.splice(idx, 1);
    view.koDoc.removeTabstopInsertionNodeAt(idx);
};

this._clearAllCurrentHits = function(scimoz, position) {
    var spos, epos, textLength = scimoz.length;
    for (spos = position; spos < textLength; spos = epos) {
        [spos, epos] = this.findByIndicator(scimoz, TSC, spos);
        if (spos == -1) {
            break;
        }
        scimoz.targetStart = spos;
        scimoz.targetEnd = epos;
        scimoz.replaceTarget(0, "");
        textLength -= (epos - spos);
    }
};

// Used to cache parsed snippets.

this._parseResultsById = {};

}).apply(ko.tabstops);
