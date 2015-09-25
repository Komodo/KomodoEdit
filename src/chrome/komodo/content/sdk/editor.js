/**
 * The editor module is loosely based on the CodeMirror(.net) API to make it
 * easier for developers who used that API and because their API has been proven
 * to work well for developers. It is not intended to be fully backwards or
 * forward compatible with CodeMirror.
 */

var scimoz = function()
{
    if ( ! window.ko.views.manager.currentView) return undefined;
    return window.ko.views.manager.currentView.scimoz;
}

var scintilla = function()
{
    if ( ! window.ko.views.manager.currentView) return undefined;
    return window.ko.views.manager.currentView.scintilla;
}

/**
 * @module editor
 */
module.exports = {

    log: require("ko/logging").getLogger("ko/editor"),

    available: function() {
        return ( !! scimoz() && !! scintilla() );
    },

    /** ****** Commands ****** **/

    /**
     * Empty the undo buffer.
     *
     * @returns {Void}
     */
    emptyUndoBuffer: function() {
        return scimoz().emptyUndoBuffer();
    },

    /**
     * Undo the last action
     *
     * @returns {Void}
     */
    undo: function() {
        return scimoz().undo();
    },

    /**
     * Cut current selection to clipboard
     *
     * @returns {Void}
     */
    cut: function() {
        return scimoz().cut();
    },

    /**
     * Copy current selection to clipboard
     *
     * @returns {Void}
     */
    copy: function() {
        return scimoz().copy();
    },

    /**
     * Replace current selection with the clipboard contents
     *
     * @returns {Void} 
     */
    paste: function() {
        return scimoz().paste();
    },
    
    /**
     * Select all the text in the buffer
     *
     * @returns {Void}
     */
    selectAll: function()
    {
        this.setSelection(0, this.scimoz().textLength);
    },

    /**
     * Deletes the whole line under the cursor, including newline at the end
     */
    deleteLine: function()
    {
        this.scimoz().lineDelete();
    },

    /**
     * Delete the part of the line before the cursor
     */
    delLineLeft: function()
    {
        this.scimoz().delLineLeft();
    },

    /**
     * Delete the part of the line after the cursor
     */
    delLineRight: function()
    {
        this.scimoz().delLineRight();
    },

    /**
     * Move the cursor to the start of the document
     */
    goDocStart: function()
    {
        scimoz().documentStart();
    },

    /**
     * Move the cursor to the end of the document.
     */
    goDocEnd: function()
    {
        scimoz().documentEnd();
    },

    /**
     * Move the cursor to the start of the line.
     */
    goLineStart: function()
    {
        scimoz().home();
    },

    /**
     * Move to the start of the text on the line, or if we are already there, to the actual start of the line (including whitespace).
     */
    goLineStartSmart: function()
    {
        var curPos = this.getCursorPosition();
        var lineText = this.getLine();
        
        var firstChar = lineText.search(/\S/);
        if (firstChar == -1 || firstChar == curPos.ch)
            firstChar = 0;

        this.setCursorPosition({line: this.getLineNumber(), ch: firstChar});
    },

    /**
     * Move the cursor to the end of the line.
     */
    goLineEnd: function()
    {
        scimoz().lineEnd();
    },

    /**
     * Move the cursor to the left side of the visual line it is on. If this line is wrapped, that may not be the start of the line.
     */
    goLineLeft: function()
    {
        scimoz().homeDisplay();
    },

    /**
     * Move the cursor to the right side of the visual line it is on.
     */
    goLineRight: function()
    {
        scimoz().lineEndDisplay();
    },

    /**
     * Move the cursor up one line.
     */
    goLineUp: function()
    {
        scimoz().lineUp();
    },

    /**
     * Move down one line.
     */
    goLineDown: function()
    {
        scimoz().lineDown();
    },

    /**
     * Move the cursor up one screen, and scroll up by the same distance.
     */
    goPageUp: function()
    {
        scimoz().pageUp();
    },

    /**
     * Move the cursor down one screen, and scroll down by the same distance.
     */
    goPageDown: function()
    {
        scimoz().pageDown();
    },

    /**
     * Move the cursor one character left, going to the previous line when hitting the start of line.
     */
    goCharLeft: function()
    {
        scimoz().charLeft();
    },

    /**
     * Move the cursor one character right, going to the next line when hitting the end of line.
     */
    goCharRight: function()
    {
        scimoz().charRight();
    },

    /**
     * Move the cursor one character left, but don't cross line boundaries.
     */
    goColumnLeft: function()
    {
        var pos = this.getCursorPosition();
        if (pos.ch == 0) return;
        this.goCharLeft();
    },

    /**
     * Move the cursor one character right, don't cross line boundaries.
     */
    goColumnRight: function()
    {
        var pos = this.getCursorPosition();
        if (pos.ch == this.getLineSize()) return;
        this.goCharRight();
    },

    /**
     * Move the cursor to the start of the previous word.
     */
    goWordLeft: function()
    {
        scimoz().wordLeft();
    },

    /**
     * Move the cursor to the end of the next word.
     */
    goWordRight: function()
    {
        scimoz().wordRight();
    },

    /**
     * Delete the character before the cursor.
     */
    delCharBefore: function()
    {
        var pos = this.getCursorPosition("absolute");
        if ( ! pos) return;
        
        this.deleteRange(pos-1, 1);
    },

    /**
     * Delete the character after the cursor.
     */
    delCharAfter: function()
    {
        var pos = this.getCursorPosition("absolute");
        if (pos == this.getLength()) return;

        this.deleteRange(pos, 1);
    },

    /**
     * Delete up to the start of the word before the cursor.
     */
    delWordBefore: function()
    {
        scimoz().delWordLeft();
    },

    /**
     * Delete up to the end of the word after the cursor.
     */
    delWordAfter: function()
    {
        scimoz().delWordRight();
    },

    /** ****** Buffer Information ****** **/

    /**
     * Get the current buffer's content
     *
     * @returns {String}
     */
    getValue: function()
    {
        return scimoz().text;
    },

    /**
     * Get the character length of the current buffer
     *
     * @returns {Int} 
     */
    getLength: function()
    {
        return scimoz().textLength;
    },

    /**
     * Retrieve the given range of text
     *
     * @param   {Object|Int} from   Absolute or relative position
     * @param   {Object|Int} to     Absolute or relative position
     *
     * @returns {String}
     */
    getRange: function(from, to)
    {
        [from, to] = this._posFormat([from, to], "absolute");
        return scimoz().getTextRange(from, to);
    },

    /**
     * Get the contents of the given line
     *
     * @param   {Int|Undefined} line
     *
     * @returns {String}
     */
    getLine: function(line)
    {
        if ( ! line) line = this.getLineNumber();
        return this.getRange({line: line, ch: 0}, {line: line, ch: this.getLineSize(line)}).replace(/(\r\n|\n|\r)/gm,"");
    },

    /**
     * Get the position of the cursor
     *
     * @param   {String} format  absolute | relative (default)
     *
     * @returns {Object|Int} Absolute: Int, Relative: {line, ch, absolute}
     */
    getCursorPosition: function(format = "relative")
    {
        return this._posFormat(scimoz().currentPos, format);
    },

    /**
     * Get the position of the cursor relative to the Komodo window
     *
     * @returns {Object} {x: .., y: ..}
     */
    getCursorWindowPosition: function(relativeToScreen = false)
    {
        var _scintilla = scintilla();
        var _scimoz = scimoz();
        if ( ! _scintilla || ! _scimoz) return {x: 0, y: 0};

        var scx, scy;
        if ( ! relativeToScreen)
        {
            scx = _scintilla.boxObject.x;
            scy = _scintilla.boxObject.y;
        }
        else
        {
            scx = _scintilla.boxObject.screenX;
            scy = _scintilla.boxObject.screenY;
        }

        var currentPos = _scimoz.currentPos;
        var curx = _scimoz.pointXFromPosition(currentPos);
        var cury = _scimoz.pointYFromPosition(currentPos);

        return {x: (scx + curx), y: (scy + cury)};
    },

    /**
     * Get the default line height (all lines are currently the same height)
     *
     * @returns {Int} Height in pixels
     */
    defaultTextHeight: function()
    {
        return scimoz().textHeight(0);
    },
    
    /**
     * Get the default text width (Based on first character, not very useful
     * if someone is using a proportional font -- who would do such a thing?!)
     *
     * @returns {Int} Width in pixels
     */
    defaultTextWidth: function()
    {
        return scimoz().textWidth(0,1);
    },

    /**
     * Get the current line number
     *
     * @returns {Int}
     */
    getLineNumber: function()
    {
        var pos = this.getCursorPosition("relative");
        return pos.line;
    },

    /**
     * Get the given line start position
     *
     * @returns {Int}
     */
    getLineStartPos: function(line, format ="absolute")
    {
        if ( ! line) line = this.getLineNumber();
        return this._posFormat(this._posToAbsolute({line: line, ch: 0}),format);
    },

    /**
     * Get the given line end position
     *
     * @returns {Int}
     */
    getLineEndPos: function(line, format = "absolute")
    {
        if ( ! line) line = this.getLineNumber();
        
        return this._posFormat(scimoz().getLineEndPosition(line-1),format);
    },

    /**
     * Get the current column (character | ch) number
     *
     * @returns {Int}
     */
    getColumnNumber: function()
    {
        var pos = this.getCursorPosition("relative");
        return pos.ch;
    },

    /**
     * Get the size of the line
     *
     * @param   {Int} line
     *
     * @returns {Int}
     */
    getLineSize: function(line)
    {
        if ( ! line) line = this.getLineNumber();
        return this.getLineEndPos(line) - this.getLineStartPos(line);
    },

    /**
     * Get the number of lines in the current buffer
     *
     * @returns {Int}
     */
    lineCount: function()
    {
        return scimoz().lineCount;
    },

    /** ****** Buffer Manipulation ****** **/

    /**
     * Set the current buffer's content
     *
     * @param   {String} value
     *
     * @returns {Void} 
     */
    setValue: function(value)
    {
        return scimoz().text = value;
    },

    /**
     * Insert text at the current cursor position
     *
     * Any existing selections will be replaced with the given text
     *
     * @param   {String} text
     *
     * @returns {Void}
     */
    insert: function(text)
    {
        var selection = this.getSelectionRange();
        if (selection.start != selection.end && selection.end)
        {
            scimoz().deleteBack();
        }

        scimoz().addText(text);
    },

    /**
     * Move cursor to a specific line
     *
     * @param   (number) line number 
     */
    gotoLine: function(lineNum)
    {
        this.setCursor({line:lineNum});
    },
    
    /**
     * Set the position of the cursor
     *
     * @param   {Int|Object} pos  relative or absolute position
     *
     * @returns {Void}
     */
    setCursor: function(pos)
    {
        pos = this._posFormat(pos, "absolute");
        scimoz().setSel(pos, pos);
    },

    /**
     * Delete the given range of characters
     *
     * @param   {Object|Int} start Position
     * @param   {Object|Int} end   Position
     *
     * @returns {Void} 
     */
    deleteRange: function(start, end)
    {
        [start, end] = this._posFormat([start, end], "absolute");
        scimoz().deleteRange(start, end);
    },

    /** ****** Selections ****** **/

    /**
     * Get the currently selected text
     *
     * @returns {String}
     */
    getSelection: function()
    {
        return scimoz().selText;
    },

    /**
     * Set the selection
     *
     * @param   {Object} start {line, ch}
     * @param   {Object} end   {line, ch}
     *
     * @returns {Void}
     */
    setSelection: function(start, end)
    {
        scimoz().setSel(this._posToAbsolute(start), this._posToAbsolute(end));
    },

    /**
     * Get the current selection range
     *
     * @param   {String} format  absolute | relative (default)
     *
     * @returns {Object} {start: formattedPost, end: formattedPos}
     */
    getSelectionRange: function(format = "relative")
    {
        return {
            start: this._posFormat(scimoz().anchor, format),
            end: this._posFormat(scimoz().currentPos, format)
        }
    },

    /**
     * Clear the current selection
     *
     * @returns {Void} 
     */
    clearSelection: function()
    {
        return scimoz().clearSelection();
    },

    /**
     * Replace the current selection with the given text
     *
     * @param   {String} replacement
     * @param   {Object} select      What to select after insertion
     *                                - around: select inserted text
     *                                - start: set cursor to start of insertion
     *                                - {undefined}: set cursor at end of insertion
     *
     * @returns {Void}
     */
    replaceSelection: function(replacement, select)
    {
        this.insert(replacement);

        switch (select)
        {
            case "around":
                var currentPos = this.getCursorPosition("absolute");
                this.setSelection(currentPos - replacement.length, currentPos);
                break;
            case "start":
                this.setCursorPosition(this.getCursorPosition("absolute") - replacement.length);
                break;
        }
    },

    /**
     * Get the current programming language used
     *
     * @returns {string}
     */
    getLanguage: function()
    {
        return scintilla().language;
    },

    /**
     * Set focus on the editor
     */
    focus: function()
    {
        scintilla().focus();
    },

    /** ****** Bookmarks ****** **/

    /**
     * Get all registered bookmarks
     * 
     * @param   {Long} type     See ko.markers
     * 
     * @returns {Array}
     */
    getAllMarks: function(type = ko.markers.MARKNUM_BOOKMARK)
    {
        if ( ! scimoz()) return [];

        var lineNo = 0;
        var bookmarkLines = {};
        var marker_mask = 1 << type;
        if (type == ko.markers.MARKNUM_BOOKMARK) {
            for (let i = 0; i < 10; i++) {
                marker_mask |= 1 << ko.markers['MARKNUM_BOOKMARK' + i];
            }
        }

        while (lineNo != -1)
        {
            var lineNo = scimoz().markerNext(lineNo, marker_mask);

            if (lineNo != -1)
            {
                bookmarkLines[lineNo+1] = this.getLine(lineNo+1);
                lineNo++;
            }
            else
                break;
        }

        return bookmarkLines;
    },

    /**
     * Toggle a bookmark on a given line
     *
     * @param {number} line number. default is current line
     * Line number is decremented by one if passed in to match scimoz lines
     * starting from 0.
     */
    toggleBookmark: function(lineNum)
    {
        if (this.bookmarkExists(lineNum))
        {
            this.unsetBookmarkByLine(lineNum);
        }
        else
        {
            this.setBookmark(lineNum);
        }
    },
    
    /**
    * Retrieve the line a bookmark is at by handle
    *
    * @param {number} markerid,  Default is current line.  
    *
    * @return {number} line number from scintilla perspective
    * (eg, starting from 0)
    */
    getBookmarkLineFromHandle: function(handle)
    {
        return scimoz().markerLineFromHandle(handle) + 1;
    },
    
    /**
     * Create a bookmark at a given line if one doesn't exist.
     *
     * @param {number} line number.  Default is current line.  Line is decremented
     *   when passed in.
     * @param {number} Optional type of bookmark. See ko.markers.
     *
     * @return {number} ID of marker according to Scimoz
     */
    setBookmark: function(lineNum, type = ko.markers.MARKNUM_BOOKMARK)
    {
        if ( ! lineNum )
        {
            lineNum = scimoz().lineFromPosition(scimoz().currentPos);
        }
        else
        {
            --lineNum;
        }

        var markerId=0;
        let mainWindow = require("ko/windows").getMain();
        let bookMarknum = type
        let data = {
                      'line': lineNum,
                   }
        // Clean the line of old markers and re-set it
        this.unsetBookmarkByLine();
        markerId = scimoz().markerAdd(lineNum, bookMarknum);
        return markerId;
    },
    
    /**
     * Unset breakpoint by Marker handle
     *
     * param {number} A marker handle
     */
    unsetBookmarkByHandle: function(handle)
    {
        // Does nothing if handle doesn't exist.
        scimoz().markerDeleteHandle(handle);
    },

    
    /**
     * Remove a bookmark at a given line
     *
     * @param {number} line number. default is current line
     * Note, if using this
     */
    unsetBookmarkByLine: function(lineNum)
    {
        if ( ! lineNum )
        {
            lineNum = scimoz().lineFromPosition(scimoz().currentPos);
        }
        else
        {
            --lineNum;
        }
        
        var bookMarknum = ko.markers.MARKNUM_BOOKMARK;
        var data = {
                      'line': lineNum,
                    }  
        var mainWindow = require("ko/windows").getMain();

        scimoz().markerDelete(lineNum, bookMarknum);
        for (let i = 0; i < 10; i++) {
            scimoz().markerDelete(lineNum, ko.markers['MARKNUM_BOOKMARK' + i]);
        }
        mainWindow.dispatchEvent(new mainWindow.CustomEvent("bookmark_deleted",{
                                                bubbles: true, detail: data }));
    },

    /**
     * Check if there is already a bookmark set on a given line
     *
     * @param {number} line number, defaults to current line
     */
    bookmarkExists: function(lineNum)
    {
        if ( ! lineNum )
        {
            lineNum = scimoz().lineFromPosition(scimoz().currentPos);
        }
        else
        {
            --lineNum;
        }
        
        var lineMarkerState = scimoz().markerGet(lineNum);
        var bookMarknum = ko.markers.MARKNUM_BOOKMARK;
        var bookmarkMask = (1 << bookMarknum)
        for (let i = 0; i < 10; i++) {
            bookmarkMask |= 1 << ko.markers['MARKNUM_BOOKMARK' + i];
        }
        // bitwise-AND to see if a marker is on the line
        // using
        return(lineMarkerState & bookmarkMask)
    },
    
    /** ****** Helpers ****** **/
    
    /**
     * Access to the scimoz object
     */
    scimoz: scimoz,
    
    /**
     * Access to the scintilla object
     */
    scintilla: scintilla,

    /**
     * Convert the given position(s) into the given format, regardless of what
     * format the input is in
     *
     * @param   {Array|Object|Int} positions Either a single position or an array
     *                             of positions
     *
     * @param   {String} format
     *
     * @returns {Array|Object|Int} Returns a single position or an array of positions
     *                              if the input was an array
     */
    _posFormat: function(positions, format)
    {
        var result = [];

        if ( ! (positions instanceof Array))
            positions = [positions];

        for (let x in positions)
        {
            let pos = positions[x];

            if (format == "absolute")
            {
                if ((typeof pos) != "number")
                    pos = this._posToAbsolute(pos)
            }
            else if ((typeof pos) == "number")
            {
                pos = this._posToRelative(pos)
            }

            result.push(pos);
        }

        return result.length == 1 ? result[0] : result;
    },

    /**
     * Converts an absolute position to a relative position
     *
     * @param   {Int} abs
     *
     * @returns {Object} {line, ch}
     */
    _posToRelative: function(abs)
    {
        return {
            line: scimoz().lineFromPosition(abs)+1,
            ch: scimoz().getColumn(abs),
            absolute: abs
        }
    },

    /**
     * Converts a relative position to an absolute position
     *
     * @param   {Object} pos {line, ch}
     *
     * @returns {Int}
     */
    _posToAbsolute: function(pos)
    {
        if ( ! pos.line ) pos.line = this.getLineNumber();
        return scimoz().positionFromLine(pos.line-1) + (pos.ch || 0);
    }

}
