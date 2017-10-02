const w = require("ko/windows").getMain();
const legacy = w.ko;
const prefs = require("ko/prefs");
const shell = require("ko/shell");
const log = require("ko/logging").getLogger("sdk/editor");
const system = require("sdk/system");

var pixelRatio = null;

/**
 * The editor SDK
 *
 * @module ko/editor
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */
var sdkEditor = function(_scintilla, _scimoz) {
    var init = () =>
    {
        if (pixelRatio)
            return;

        // We currently only translate the position according to pixelRatio on Linux,
        // other platforms handle this at a lower level
        pixelRatio = system.platform == "linux" ? w.devicePixelRatio : 1;
        if (system.platform == "linux")
        {
            if (prefs.hasPref('pixelRatio'))
            {
                pixelRatio = parseFloat(prefs.getString('pixelRatio'));
                log.debug("Using pixelRatio: " + pixelRatio);
            }
            else
            {
                var cmd = "gsettings get org.gnome.desktop.interface text-scaling-factor";
                shell.exec(cmd, {}, (error, stdout) => {
                    if (error)
                    {
                        log.error(error);
                        return;
                    }

                    pixelRatio = parseFloat(stdout.trim().match(/\d(?:\.\d{1,2}|)/));

                    log.debug("Using pixelRatio: " + pixelRatio);
                });
            }
        }
    }

    /*
     * The editor module is loosely based on the CodeMirror(.net) API to make it
     * easier for developers who used that API and because their API has been proven
     * to work well for developers. It is not intended to be fully backwards or
     * forward compatible with CodeMirror.
     */

    var scimoz = function()
    {
        if (_scimoz !== undefined) return _scimoz;

        var sc = scintilla();
        if ( ! sc) return undefined;

        return sc.scimoz;
    }

    var scintilla = function()
    {
        if (_scintilla !== undefined) return _scintilla;

        if ( ! legacy.views.manager.currentView) return undefined;
        return legacy.views.manager.currentView.scintilla;
    }

    /**
     * Returns the editor SDK for a custom scintilla instance
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Object} sci Scintilla
     * @param   {Object} scm  Scimoz
     *
     * @returns {sdkEditor}
     */
    this.editor = function(sci, scm) {
        return new sdkEditor(sci, scm);
    };

    /**
     * Checks whether scintilla is available for the current editor
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Boolean}
     */
    this.available = function() {
        return ( !! scimoz() && !! scintilla() );
    };

    /** ****** Commands ****** **/

    /**
     * Empty the undo buffer.
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.emptyUndoBuffer = function() {
        return scimoz().emptyUndoBuffer();
    };

    /**
     * Undo the last action
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.undo = function() {
        return scimoz().undo();
    };

    /**
     * Cut current selection to clipboard
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.cut = function() {
        return scimoz().cut();
    };

    /**
     * Copy current selection to clipboard
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.copy = function() {
        return scimoz().copy();
    };

    /**
     * Replace current selection with the clipboard contents
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.paste = function() {
        return scimoz().paste();
    };

    /**
     * Select all the text in the buffer
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.selectAll = function()
    {
        this.setSelection(0, this.scimoz().textLength);
    };

    /**
     * Deletes the whole line under the cursor, including newline at the end
     *
     * @method
     * @memberof module:ko/editor
     */
    this.deleteLine = function()
    {
        this.scimoz().lineDelete();
    };

    /**
     * Delete the part of the line before the cursor
     *
     * @method
     * @memberof module:ko/editor
     */
    this.delLineLeft = function()
    {
        this.scimoz().delLineLeft();
    };

    /**
     * Delete the part of the line after the cursor
     *
     * @method
     * @memberof module:ko/editor
     */
    this.delLineRight = function()
    {
        this.scimoz().delLineRight();
    };

    /**
     * Move the cursor to the start of the document
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goDocStart = function()
    {
        scimoz().documentStart();
    };

    /**
     * Move the cursor to the end of the document.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goDocEnd = function()
    {
        scimoz().documentEnd();
    };

    /**
     * Move the cursor to the start of the line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineStart = function()
    {
        scimoz().home();
    };

    /**
     * Move to the start of the text on the line, or if we are already there, to the actual start of the line (including whitespace).
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineStartSmart = function()
    {
        var curPos = this.getCursorPosition();
        var lineText = this.getLine();

        var firstChar = lineText.search(/\S/);
        if (firstChar == -1 || firstChar == curPos.ch)
            firstChar = 0;

        this.setCursorPosition({line: this.getLineNumber(), ch: firstChar});
    };

    /**
     * Move the cursor to the end of the line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineEnd = function()
    {
        scimoz().lineEnd();
    };

    /**
     * Move the cursor to the left side of the visual line it is on. If this line is wrapped, that may not be the start of the line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineLeft = function()
    {
        scimoz().homeDisplay();
    };

    /**
     * Move the cursor to the right side of the visual line it is on.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineRight = function()
    {
        scimoz().lineEndDisplay();
    };

    /**
     * Move the cursor up one line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineUp = function()
    {
        scimoz().lineUp();
    };

    /**
     * Move down one line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goLineDown = function()
    {
        scimoz().lineDown();
    };

    /**
     * Move the cursor up one screen, and scroll up by the same distance.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goPageUp = function()
    {
        scimoz().pageUp();
    };

    /**
     * Move the cursor down one screen, and scroll down by the same distance.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goPageDown = function()
    {
        scimoz().pageDown();
    };

    /**
     * Move the cursor one character left, going to the previous line when hitting the start of line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goCharLeft = function()
    {
        scimoz().charLeft();
    };

    /**
     * Move the cursor one character right, going to the next line when hitting the end of line.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goCharRight = function()
    {
        scimoz().charRight();
    };

    /**
     * Move the cursor one character left, but don't cross line boundaries.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goColumnLeft = function()
    {
        var pos = this.getCursorPosition();
        if (pos.ch == 0) return;
        this.goCharLeft();
    };

    /**
     * Move the cursor one character right, don't cross line boundaries.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goColumnRight = function()
    {
        var pos = this.getCursorPosition();
        if (pos.ch == this.getLineSize()) return;
        this.goCharRight();
    };

    /**
     * Move the cursor to the start of the previous word.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goWordLeft = function()
    {
        scimoz().wordLeft();
    };

    /**
     * Move the cursor to the end of the next word.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.goWordRight = function()
    {
        scimoz().wordRight();
    };

    /**
     * Delete the character before the cursor.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.delCharBefore = function()
    {
        var pos = this.getCursorPosition("absolute");
        if ( ! pos) return;

        this.deleteRange(pos-1, 1);
    };

    /**
     * Delete the character after the cursor.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.delCharAfter = function()
    {
        var pos = this.getCursorPosition("absolute");
        if (pos == this.getLength()) return;

        this.deleteRange(pos, 1);
    };

    /**
     * Delete up to the start of the word before the cursor.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.delWordBefore = function()
    {
        scimoz().delWordLeft();
    };

    /**
     * Delete up to the end of the word after the cursor.
     *
     * @method
     * @memberof module:ko/editor
     */
    this.delWordAfter = function()
    {
        scimoz().delWordRight();
    };

    /** ****** Buffer Information ****** **/

    /**
     * Get the current buffer's content
     *
     * @method
     * @memberof module:ko/editor
     *
     * @returns {String}
     */
    this.getValue = function()
    {
        return scimoz().text;
    };

    /**
     * Get word to the left of the given position
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Null|Int|Object|Regexp}    pos     Absolute or relative position, if value is regex then this will be used as the match. Leave empty to use current cursor position.
     * @param   {Null|RegExp}               match   The regex to match the word agains
     */
    this.getWord = function (pos, match)
    {
        if (pos && pos.constructor.toString().indexOf("RegExp") != -1)
        {
            match = pos;
            pos = undefined;
        }

        if ( ! match)
            match = /[\w_\-]/;

        if ( ! pos)
        {
            pos = scimoz().wordEndPosition(scimoz().currentPos, true);
        }
        else
            pos = this._posFormat(pos, 'absolute');

        var lineNo = this.getLineNumber(pos);
        var word = "";

        while (pos > 0 && this.getLineNumber(pos) == lineNo)
        {
            let letter = this.getRange(--pos, pos+1)
            if ( ! letter.match(match)) break;
            word = letter + word;
        }

        return word.trim();
    };

    /**
     * Get the character length of the current buffer
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Int}
     */
    this.getLength = function()
    {
        return scimoz().textLength;
    };

    /**
     * Retrieve the given range of text
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Object|Int} from   Absolute or relative position
     * @param   {Object|Int} to     Absolute or relative position
     *
     * @returns {String}
     */
    this.getRange = function(from, to)
    {
        [from, to] = this._posFormat([from, to], "absolute");
        return scimoz().getTextRange(from, to);
    };

    /**
     * Get the contents of the given line
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Int|Undefined} line
     *
     * @returns {String}
     */
    this.getLine = function(line)
    {
        if ( ! line) line = this.getLineNumber();
        return this.getRange({line: line, ch: 0}, {line: line, ch: this.getLineSize(line)}).replace(/(\r\n|\n|\r)/gm,"");
    };

    /**
     * Get the position of the cursor
     *
     * @method
     * @memberof module:ko/editor
     * @param   {String} format  absolute | relative (default)
     *
     * @returns {Object|Int} Absolute: Int, Relative: {line, ch, absolute}
     */
    this.getCursorPosition = function(format = "relative")
    {
        return this._posFormat(scimoz().currentPos, format);
    };

    /**
     * Get the position of the cursor relative to the Komodo window
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Object} {x: .., y: ..}
     */
    this.getCursorWindowPosition = function(relativeToScreen = false)
    {
        var _scimoz = scimoz();
        return this.getWindowPosition(_scimoz.currentPos, relativeToScreen);
    };

    /**
     * Get the window position of the given character
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Object} {x: .., y: ..}
     */
    this.getWindowPosition = function(pos, relativeToScreen = false)
    {
        pos = this._posFormat(pos, "absolute");

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

        var curx = Math.round(_scimoz.pointXFromPosition(pos) / pixelRatio);
        var cury = Math.round(_scimoz.pointYFromPosition(pos) / pixelRatio);

        return {x: (scx + curx), y: (scy + cury)};
    };

    /**
     * Get the line number from the given x/y position
     *
     * @method
     * @memberof module:ko/editor
     * @param   {int} x relative to scimoz view
     * @param   {int} y relative to scimoz view
     *
     * @returns {int} Line number
     */
    this.getLineFromMousePosition = function(x, y)
    {
        var _scimoz = scimoz();

        var pos = scimoz.positionFromPoint(x, y);
        var line = scimoz.lineFromPosition(pos);

        return line+1;
    };

    /**
     * Get margin number relative to x/y position
     *
     * @method
     * @memberof module:ko/editor
     * @param   {int} x relative to scimoz view
     * @param   {int} y relative to scimoz view
     *
     * @returns {int} Margin number, see ISciMoz.template.idl
     */
    this.getMarginFromMousePosition = function(x,y)
    {
        if (x <= 0)
            return -1;

        var totalWidth = 0;
        var _scimoz = scimoz();
        for (var i=0; i <= _scimoz.SC_MAX_MARGIN; i++)
        {
            let marginWidth = _scimoz.getMarginWidthN(i);
            if (marginWidth)
            {
                totalWidth += marginWidth;
                if (x < totalWidth)
                    return i;
            }
        }

        return -1;
    };

    /**
     * Get the default line height (all lines are currently the same height)
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Int} Height in pixels
     */
    this.defaultTextHeight = function()
    {
        return Math.round(scimoz().textHeight(0) / pixelRatio);
    };

    /**
     * Get the default text width (Based on first character, not very useful
     * if someone is using a proportional font -- who would do such a thing?!)
     *
     * @returns {Int} Width in pixels
     */
    this.defaultTextWidth = function()
    {
        return Math.round(scimoz().textWidth(0,1) / pixelRatio);
    };

    /**
     * Get the current line number
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Null|Object|Int} position   relative/absolute position to look from, leave empty to use current cursor position.
     *
     * @returns {Int}
     */
    this.getLineNumber = function(pos)
    {
        if ( ! pos)
            pos = this.getCursorPosition("relative");
        else
            pos = this._posFormat(pos, "relative");

        return pos.line;
    };

    /**
     * Get the given line start position
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Int}
     */
    this.getLineStartPos = function(line, format ="absolute")
    {
        if ( ! line) line = this.getLineNumber();
        return this._posFormat(this._posToAbsolute({line: line, ch: 0}),format);
    };

    /**
     * Get the given line end position
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Int}
     */
    this.getLineEndPos = function(line, format = "absolute")
    {
        if ( ! line) line = this.getLineNumber();

        return this._posFormat(scimoz().getLineEndPosition(line-1),format);
    };

    /**
     * Get the current column (character | ch) number
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Int}
     */
    this.getColumnNumber = function()
    {
        var pos = this.getCursorPosition("relative");
        return pos.ch;
    };

    /**
     * Get the size of the line
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Int} line
     *
     * @returns {Int}
     */
    this.getLineSize = function(line)
    {
        if ( ! line) line = this.getLineNumber();
        return this.getLineEndPos(line) - this.getLineStartPos(line);
    };

    /**
     * Get the number of lines in the current buffer
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Int}
     */
    this.lineCount = function()
    {
        return scimoz().lineCount;
    };

    /** ****** Buffer Manipulation ****** **/

    /**
     * Set the current buffer's content
     *
     * @method
     * @memberof module:ko/editor
     * @param   {String} value
     * @returns {Void}
     */
    this.setValue = function(value)
    {
        return scimoz().text = value;
    };

    /**
     * Insert text at the current cursor position
     *
     * Any existing selections will be replaced with the given text
     *
     * @method
     * @memberof module:ko/editor
     * @param   {String} text
     *
     * @returns {Void}
     */
    this.insert = function(text)
    {
        var selection = this.getSelectionRange();
        if (selection.start.absolute != selection.end.absolute && selection.end)
        {
            scimoz().deleteBack();
        }

        scimoz().addText(text);
    };

    this.insertLine = function(line, position = "after")
    {
        this.setCursor({line: line});

        if (position == "before")
            this.goLineStart();
        else
            this.goLineEnd();

        this.insertLineBreak();
    };

    this.insertLineBreak = function()
    {
        this.scimoz().newLine();
    };

    /**
     * Move cursor to a specific line
     *
     * @method
     * @memberof module:ko/editor
     * @param   (number) line number
     */
    this.gotoLine = function(lineNum)
    {
        this.setCursor({line: lineNum});
    };

    /**
     * Set the position of the cursor
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Int|Object} pos  relative or absolute position
     *
     * @returns {Void}
     */
    this.setCursor = function(pos)
    {
        pos = this._posFormat(pos, "absolute");
        scimoz().setSel(pos, pos);
    };

    /**
     * Delete the given range of characters
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Object|Int} start Position
     * @param   {Int} length
     *
     * @returns {Void}
     */
    this.deleteRange = function(start, length)
    {
        start = this._posFormat(start, "absolute");
        scimoz().deleteRange(start, length);
    };

    /** ****** Selections ****** **/

    /**
     * Get the currently selected text
     *
     * @method
     * @memberof module:ko/editor
     * @returns {String}
     */
    this.getSelection = function()
    {
        return scimoz().selText;
    };

    /**
     * Set the selection
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Object} start {line, ch}
     * @param   {Object} end   {line, ch}
     *
     * @returns {Void}
     */
    this.setSelection = function(start, end)
    {
        scimoz().setSel(this._posToAbsolute(start), this._posToAbsolute(end));
    };

    /**
     * Get the current selection range
     *
     * @method
     * @memberof module:ko/editor
     * @param   {String} format  absolute | relative (default)
     *
     * @returns {Object} {start: formattedPost, end: formattedPos}
     */
    this.getSelectionRange = function(format = "relative")
    {
        return {
            start: this._posFormat(scimoz().anchor, format),
            end: this._posFormat(scimoz().currentPos, format)
        }
    };

    /**
     * Clear the current selection
     *
     * @method
     * @memberof module:ko/editor
     * @returns {Void}
     */
    this.clearSelection = function()
    {
        return scimoz().clearSelection();
    };

    /**
     * Replace the current selection with the given text
     *
     * @method
     * @memberof module:ko/editor
     * @param   {String} replacement
     * @param   {Object} select      What to select after insertion
     *                                - around: select inserted text
     *                                - start: set cursor to start of insertion
     *                                - {undefined}: set cursor at end of insertion
     *
     * @returns {Void}
     */
    this.replaceSelection = function(replacement, select)
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
    };

    /**
     * Get the current programming language used
     *
     * @method
     * @memberof module:ko/editor
     * @returns {string}
     */
    this.getLanguage = function()
    {
        return scintilla().language;
    };

    /**
     * Set focus on the editor
     *
     * @method
     * @memberof module:ko/editor
     */
    this.focus = function()
    {
        scintilla().focus();
    };

    /** ****** Bookmarks ****** **/

    /**
     * Get all registered bookmarks
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Long} type     See legacy.markers
     *
     * @returns {Array}
     */
    this.getAllMarks = function(type = legacy.markers.MARKNUM_BOOKMARK)
    {
        if ( ! scimoz()) return [];

        var lineNo = 0;
        var bookmarkLines = {};
        var marker_mask = 1 << type;
        if (type == legacy.markers.MARKNUM_BOOKMARK) {
            for (let i = 0; i < 10; i++) {
                marker_mask |= 1 << legacy.markers['MARKNUM_BOOKMARK' + i];
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
    };

    /**
     * Toggle a bookmark on a given line
     *
     * @method
     * @memberof module:ko/editor
     * @param {number} line number. default is current line
     * Line number is decremented by one if passed in to match scimoz lines
     * starting from 0.
     */
    this.toggleBookmark = function(lineNum)
    {
        if (this.bookmarkExists(lineNum))
        {
            this.unsetBookmarkByLine(lineNum);
        }
        else
        {
            this.setBookmark(lineNum);
        }
    };

    /**
    * Retrieve the line a bookmark is at by handle
    *
    * @method
    * @memberof module:ko/editor
    * @param {number} markerid,  Default is current line.
    *
    * @return {number} line number
    */
    this.getBookmarkLineFromHandle = function(handle)
    {
        return scimoz().markerLineFromHandle(handle) + 1;
    };

    /**
     * Create a bookmark at a given line if one doesn't exist.
     *
     * @method
     * @memberof module:ko/editor
     * @param {number} line number.  Default is current line.  Line is decremented
     *   when passed in.
     * @param {number} Optional type of bookmark. See legacy.markers.
     *
     * @return {number} ID of marker according to Scimoz
     */
    this.setBookmark = function(lineNum, type = legacy.markers.MARKNUM_BOOKMARK)
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
    };

    /**
     * Unset breakpoint by Marker handle
     *
     * @method
     * @memberof module:ko/editor
     * @param {number} A marker handle
     */
    this.unsetBookmarkByHandle = function(handle)
    {
        // Does nothing if handle doesn't exist.
        scimoz().markerDeleteHandle(handle);
    };


    /**
     * Remove a bookmark at a given line
     *
     * @method
     * @memberof module:ko/editor
     * @param {number} line number. default is current line
     * Note, if using this
     */
    this.unsetBookmarkByLine = function(lineNum)
    {
        if ( ! lineNum )
        {
            lineNum = scimoz().lineFromPosition(scimoz().currentPos);
        }
        else
        {
            --lineNum;
        }

        var bookMarknum = legacy.markers.MARKNUM_BOOKMARK;
        var data = {
                      'line': lineNum,
                    }
        var mainWindow = require("ko/windows").getMain();

        scimoz().markerDelete(lineNum, bookMarknum);
        for (let i = 0; i < 10; i++) {
            scimoz().markerDelete(lineNum, legacy.markers['MARKNUM_BOOKMARK' + i]);
        }
        mainWindow.dispatchEvent(new mainWindow.CustomEvent("bookmark_deleted",{
                                                bubbles: true, detail: data }));
    };

    /**
     * Check if there is already a bookmark set on a given line
     *
     * @method
     * @memberof module:ko/editor
     * @param {number} line number, defaults to current line
     */
    this.bookmarkExists = function(lineNum)
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
        var bookMarknum = legacy.markers.MARKNUM_BOOKMARK;
        var bookmarkMask = (1 << bookMarknum)
        for (let i = 0; i < 10; i++) {
            bookmarkMask |= 1 << legacy.markers['MARKNUM_BOOKMARK' + i];
        }
        // bitwise-AND to see if a marker is on the line
        // using
        return(lineMarkerState & bookmarkMask)
    };

    /**
     * Find a string in the current buffer
     *
     * @method
     * @memberof module:ko/editor
     * @param   {String} text           String of text to find
     * @param   {Object|Int} startPos   Start position (optional)
     * @param   {Int} maxResults        Maximum number of results, -1 for unlimited (optional)
     *
     * @returns {Array} Returns an array of relative positions
     */
    this.findString = function(text, startPos = 0, maxResults = -1)
    {
        startPos = this._posFormat(startPos, "absolute");
        var sc = scimoz();

        if ( ! sc)
            return [];

        var results = [];
        var pos;

        while (startPos < sc.length && (results.length <= maxResults || maxResults == -1))
        {
            sc.setTargetRange(startPos, sc.length);
            pos = sc.searchInTarget(text.length, text);

            if ( ! pos)
                break;

            results.push(this._posToRelative(pos));

            startPos += pos + text.length;
        }

        return results;
    };

    /** ****** Helpers ****** **/

    /**
     * Access to the scimoz object
     */
    this.scimoz = scimoz,

    /**
     * Access to the scintilla object
     */
    this.scintilla = scintilla,

    /**
     * Convert the given position(s) into the given format, regardless of what
     * format the input is in
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Array|Object|Int} positions Either a single position or an array
     *                             of positions
     *
     * @param   {String} format
     *
     * @returns {Array|Object|Int} Returns a single position or an array of positions
     *                              if the input was an array
     */
    this._posFormat = function(positions, format = "relative")
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
                    pos = this._posToAbsolute(pos);
            }
            else if ((typeof pos) == "number")
            {
                pos = this._posToRelative(pos);
            }
            // Don't assume that already defined relative pos gives proper values
            else if (format == "relative")
            {
                pos = this._sanitizeRelativePos(pos);
            }

            result.push(pos);
        }

        return result.length == 1 ? result[0] : result;
    };

    this._sanitizeRelativePos = function(pos)
    {
        var _scimoz = scimoz();
        var linePos = _scimoz.positionFromLine(pos.line-1);
        var maxCh = _scimoz.getLineEndPosition(pos.line-1) - linePos;

        pos.ch = Math.min(pos.ch, maxCh) || 0;

        return pos;
    };

    /**
     * Converts an absolute position to a relative position
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Int} abs
     *
     * @returns {Object} {line, ch}
     */
    this._posToRelative = function(abs)
    {
        var lineNo = scimoz().lineFromPosition(abs);
        var linePos = scimoz().positionFromLine(lineNo);

        return {
            line: lineNo+1,
            ch: abs - linePos,
            absolute: abs
        };
    };

    /**
     * Converts a relative position to an absolute position
     *
     * @method
     * @memberof module:ko/editor
     * @param   {Object} pos {line, ch}
     *
     * @returns {Int}
     */
    this._posToAbsolute = function(pos)
    {
        pos.line = pos.line || this.getLineNumber();
        pos.ch = pos.ch || 0;
        pos = this._sanitizeRelativePos(pos);

        return scimoz().positionFromLine(pos.line-1) + pos.ch;
    };

    try
    {
        init();
    }
    catch (e)
    {
        log.exception(e, "init failed, continuing without");
    }

};

module.exports = new sdkEditor();
