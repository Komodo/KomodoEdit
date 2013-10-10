ko.views = {
    get manager() this,
    get topView() this.currentView,
};
(function() {

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import("resource://gre/modules/XPCOMUtils.jsm");
let logging = Cu.import("chrome://komodo/content/library/logging.js", {}).logging;
let log = logging.getLogger("views.mock");

/**
 * Create a new mock scimoz
 * @param aText {String} The text to prefill
 */
function SciMozMock(aText) {
    this.text = aText || "";
    this.currentPos = this.anchor = 0;
    this.firstVisibleLine = 0;
    this.eOLMode = Ci.ISciMoz.SC_EOL_LF;
    this.indicatorValue = Ci.ISciMoz.INDIC_PLAIN;
    this.indicatorCurrent = 0;
    this.tabWidth = 8;
    this.targetStart = this.targetEnd = 0;
    this.docPointer = 1;
    this.endStyled = 0;
    this._styleMask = 0xFF;
    this.styles = [];
    this.levels = [];
    this._searchAnchor = 0;

    /**
     * Indexed by indicator id, then is an array of RLE things where the index
     * is the start of the run, and the value is a hash {length, value}.
     * (This relies on arrays being sparse.)
     */
    this._indicators = [];
}
this.SciMozMock = SciMozMock;

/**
 * Get the keys for the given indicator
 * @param start {Number} The lowest index to get
 * @param end {Number} One more than the highest index to get
 * @param indicator {Number} The indicator; default to current
 * @returns {Array of Number} The indicator keys
 */
SciMozMock.prototype._indicatorKeys =
    function SciMozMock__indicatorKeys(start, end, indicator)
        Object.keys(this._indicators[indicator === undefined ? this.indicatorCurrent : indicator]
                        .slice(start, end))
              .map(function(n) parseInt(n, 10) + start)
              .sort(function(a, b) a - b);

SciMozMock.prototype.addText =
    function SciMozMock_addText(aLength, aText) {
        this.text = this.text.substr(0, this.currentPos) + aText + this.text.substr(this.currentPos);
    }

SciMozMock.prototype.charPosAtPosition =
    function SciMozMock_charPosAtPosition(pos)
        pos < 0 ? this.currentPos : pos;

SciMozMock.prototype.getColumn =
    function SciMozMock_getColumn(aPos) {
        let lineStart = this.positionFromLine(this.lineFromPosition(aPos));
        let column = 0;
        let piece = this.text.substring(lineStart, aPos);
        for(let i = 0; i < piece.length; ++i) {
            switch (piece[i]) {
                case "\t":
                    column = (Math.floor(column / this.tabWidth) + 1) * this.tabWidth;
                    break;
                default:
                    ++column;
            }
        }
        return column;
    };

SciMozMock.prototype.getLine =
    function SciMozMock_getLine(aLineNum, o) {
        var startPos = this.positionFromLine(aLineNum),
            endPos = (aLineNum < this.lineCount
                      ? this.positionFromLine(aLineNum + 1)
                      : this.length);
        o.value = this.getTextRange(startPos, endPos);
        return endPos - startPos;
    }

SciMozMock.prototype.getLineEndPosition =
    function SciMozMock_getLineEndPosition(aLine) {
        let lines = this.text.split(/\n/);
        return (lines.slice(0, aLine).reduce(function(n, s) n + s.length, 0)
                + aLine // Include the dropped \n's for the sliced lines
                + lines[aLine].match(/^[^\r\n]*/)[0].length);
    };

SciMozMock.prototype.startStyling =
    function SciMozMock_startStyling(pos, mask) {
        this.endStyled = pos;
        this._styleMask = mask;
    };

SciMozMock.prototype.setStyling =
    function SciMozMock_setStyling(length, style) {
        let end = Math.min(this.endStyled + length, this.text.length);
        for (let i = this.endStyled; i < end; ++i) {
            this.styles[i] = (this.styles[i] & ~this._styleMask) |
                             (style & this._styleMask);
        }
        this.endStyled = end;
    };

SciMozMock.prototype.setStylingEx =
    function SciMozMock_setStylingEx(length, styles) {
        let end = Math.min(this.endStyled + length, this.text.length);
        if (typeof(styles) == "string") {
            styles = styles.split("").map(function(c) c.charCodeAt(0));
        }
        for (let i = this.endStyled; i < end; ++i) {
            this.styles[i] = (this.styles[i] & ~this._styleMask) |
                             (styles[i] & this._styleMask);
        }
        this.endStyled = end;
    };

SciMozMock.prototype.getStyledText =
function SciMozMock_getStyledText(aStart, aEnd, outCount) {
    var ret = [];
    for (var i = aStart; i < aEnd; i++) {
        ret.push(this.text.charCodeAt(i));
        ret.push(this.styles[i]);
    }
    if (outCount) {
        outCount.value = ret.length;
    }
    return ret;
};

SciMozMock.prototype.getStyleRange =
    function SciMozMock_getStyleRange(min, max, count) {
        var styles = this.styles.slice(min, max);
        if (count) {
            count.value = styles.length;
        }
        return styles;
    };

SciMozMock.prototype.getStyleAt =
    function SciMozMock_getStyleAt(aPos)
        this.styles[aPos];

SciMozMock.prototype.getWCharAt =
    function SciMozMock_getWCharAt(aPos)
        this.text[aPos];

SciMozMock.prototype.getCharAt =
    function SciMozMock_getCharAt(aPos)
        this.text[aPos];

SciMozMock.prototype.setFoldLevels =
    function SciMozMock_setFoldLevels(aLevels)
        this.levels = [].concat(aLevels);

SciMozMock.prototype.setFoldLevel = function SciMozMock_setFoldLevel(i, level) {
    if (!('levels' in this)) {
        this.levels = [];
    }
    this.levels[i] = level;
};
SciMozMock.prototype.getFoldLevel =
    function SciMozMock_getFoldLevel(i)
        this.levels[i];

SciMozMock.prototype.colourise = function SciMozMock_colourise(start, end) {
};

SciMozMock.prototype.getFoldParent = function SciMozMock_getFoldParent(i) {
    const SC_FOLDLEVELBASE = 0xf00;
    const SC_FOLDLEVELHEADERFLAG = 0x2000;
    const SC_FOLDLEVELNUMBERMASK = 0x0FFF;
    var level = this.getFoldLevel(i) & SC_FOLDLEVELNUMBERMASK;
    var lookLevel, lineLook = i - 1;
    while (lineLook > 0
           && !((lookLevel = this.getFoldLevel(lineLook)) & SC_FOLDLEVELHEADERFLAG)
           && (lookLevel & SC_FOLDLEVELNUMBERMASK) >= level) {
	lineLook--;
    }
    if (lineLook = 0) {
        lookLevel = this.getFoldLevel(lineLook);
    }
    if ((lookLevel & SC_FOLDLEVELHEADERFLAG)
        && (lookLevel & SC_FOLDLEVELNUMBERMASK) < level) {
        return lineLook;
    }
    return -1;
};

SciMozMock.prototype.getTextRange =
    function SciMozMock_getTextRange(aStart, aEnd)
        this.text.substring(aStart, aEnd);

SciMozMock.prototype.textWidth = function() 12; /* pixels */

SciMozMock.prototype.gotoPos =
    function SciMozMock_gotoPos(pos)
        this.currentPos = pos;

SciMozMock.prototype.indicatorAllOnFor =
    function SciMozMock_indicatorAllOnFor(pos) {
        let result = 0;
        for each (let [indic, runs] in Iterator(this._indicators)) {
            if (this.indicatorValueAt(indic, pos) != 0) {
                result |= 1 << indic;
            }
        }
        log.debug("indicatorAllOnFor(" + pos +")=" + result);
        return result;
    };

SciMozMock.prototype.indicatorClearRange =
    function SciMozMock_indicatorClearRange(start, length) {
        log.debug("indicatorClearRange: " + this.indicatorCurrent + " @ " +
                  start + ":" + (start + length));
        if (!(this.indicatorCurrent in this._indicators)) {
            return;
        }
        let runs = this._indicators[this.indicatorCurrent];
        let min = this._indicatorKeys(0, start).pop();
        if (min < start && (min + runs[min] >= start)) {
            // the previous run intersects start; chop it off
            if (start == min) {
                delete runs[min];
            } else {
                runs[min].length = (start - min);
            }
        }
        for each (let next in this._indicatorKeys(start, start + length)) {
            if (next + runs[next].length > start + length) {
                // this run extends past the end of the range to clear
                let run = runs[next];
                run.length = next + run.length - (start + length);
                delete runs[next];
                runs[start + length] = run;
                break;
            }
            // this run is covered by the range to clear
            delete runs[next];
        }
    };

SciMozMock.prototype.indicatorFillRange =
    function SciMozMock_indicatorFillRange(start, length) {
        if (start < 0) {
            log.debug("indicatorFillRange: invalid start " + start);
            return;
        }
        if (length < 1) {
            log.debug("indicatorFillRange: invalid length " + length);
            return;
        }
        log.debug("indicatorFillRange: " + this.indicatorCurrent + " @ " +
                  start + ":" + (start + length) + "=" + this.indicatorValue);

        if (!(this.indicatorCurrent in this._indicators)) {
            this._indicators[this.indicatorCurrent] = [];
        }
        let runs = this._indicators[this.indicatorCurrent];
        let min = this._indicatorKeys(0, start).pop();
        if (min < start && (min + runs[min] >= start)) {
            // the previous run intersects start; extend or truncate
            if (runs[min].value == this.indicatorValue) {
                // extend
                runs[min].length = start + length - min;
                let keys = this._indicatorKeys(start, start + length);
                for each (let next in keys) {
                    if (runs[next].length + next > start + length) {
                        // this run extends beyond the range
                        let run = runs[next];
                        delete runs[next];
                        run.length = next + run.length - (start + length);
                        if (run.value == this.indicatorValue) {
                            // join the runs
                            runs[min].length += run.length;
                        } else {
                            // different value, move the run
                            runs[start + length] = run;
                        }
                        break;
                    }
                    // this run is completely covered by the new range
                    delete runs[next];
                }
                return;
            }
            // reaching here means min value is different; truncate it.
            runs[min] .length = start - min;
        }
        runs[start] = {length: length, value: this.indicatorValue};
        for each (let next in this._indicatorKeys(start + 1, start + length)) {
            if (runs[next].length + next > start + length) {
                // this run extends beyond the range
                let run = runs[next];
                delete runs[next];
                run.length = next + run.length - (start + length);
                if (run.value == this.indicatorValue) {
                    // join the runs
                    runs[start].length += run.length;
                } else {
                    // different value, move the run
                    runs[start + length] = run;
                }
                break;
            }
            // this run is completely covered by the new range
            delete runs[next];
        }
    };

SciMozMock.prototype.indicatorStart =
    function SciMozMock_indicatorStart(indicator, position) {
        log.debug("indicatorStart: " + indicator + " @ " + position);
        if (!(indicator in this._indicators)) {
            return 0;
        }
        let runs = this._indicators[indicator];
        let min = this._indicatorKeys(0, position + 1, indicator).pop();
        if (min !== undefined) {
            if (min + runs[min].length > position) {
                return min; // covered by previous range
            }
            return min + runs[min].length; // after previous range
        }
        return 0; // no range before pos, it starts at 0
    };

SciMozMock.prototype.indicatorEnd =
    function SciMozMock_indicatorEnd(indicator, position) {
        log.debug("indicatorEnd: " + indicator + " @ " + position);
        if (!(indicator in this._indicators)) {
            return 0;
        }
        let runs = this._indicators[indicator];
        let min = this._indicatorKeys(0, position + 1, indicator).pop();
        if (min !== undefined && min + runs[min].length > position) {
            return min + runs[min].length; // covered by the given range
        }
        let max = this._indicatorKeys(position + 1, undefined, indicator).shift();
        if (max === undefined) {
            return this.length; // no ranges at all...
        }
        return max; // there's a following range
    };

SciMozMock.prototype.indicatorValueAt =
    function SciMozMock_indicatorValueAt(indicator, position) {
        log.debug("indicatorValueAt: " + indicator + " @ " + position);
        if (!(indicator in this._indicators)) {
            return 0;
        }
        let runs = this._indicators[indicator];
        let min = this._indicatorKeys(0, position + 1, indicator).pop();
        if (typeof(min) == "undefined") {
            return 0;
        }
        let run = runs[min];
        if (min + run.length > position) {
            return run.value;
        }
        return 0;
    };

SciMozMock.prototype.insertText =
    function SciMozMock_insertText(pos, aText) {
        this.text = this.text.substr(0, pos) + aText + this.text.substr(pos);
    }

Object.defineProperty(SciMozMock.prototype, "length", {
    get: function() this.text.length,
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "lineCount", {
    get: function() {
        if (this.text === null) {
            dump('\n\nthis.text: ' + this.text + '\n');
            ko.logging.dumpStack();
        }
        log.debug("lineCount: " + JSON.stringify(this.text) + " (" +
                  ((this.text.match(/\n(?!$)/g) || []).length + 1) + " lines)");
        return (this.text.match(/\n(?!$)/g) || []).length + 1;
    },
    enumerable: true, configurable: true});

SciMozMock.prototype.lineFromPosition =
    function SciMozMock_lineFromPosition(pos)
        (this.text.substr(0, pos).match(/\n/g) || []).length;

SciMozMock.prototype.markerGet =
    function SciMozMock_markerGet(aLineNum)
        0;

SciMozMock.prototype.markerNext =
    function SciMozMock_markerNext(lineStart, markerMask) {
        log.warn("SciMozMock: markerNext: markers not implemented");
        return -1;
    };

SciMozMock.prototype.positionAfter =
    function SciMozMock_positionAfter(pos)
        pos + 1;

SciMozMock.prototype.positionAtChar =
    function SciMozMock_positionAtChar(start, charoffset)
        start + charoffset;

SciMozMock.prototype.positionAtColumn =
    function SciMozMock_positionAtColumn(line, column) {
        let offset = this.positionFromLine(line - 1), pos = 0;
        let lines = this.text.match(new RegExp("(?:[^\n]*\n){" + (line + 1) + "}", "m")) || [""];
        let lastLine = lines.pop().replace(/\n$/, "");
        for(; column > 0; --column) {
            switch (lastLine[column]) {
                case "\t":
                    pos = (Math.floor(pos / this.tabWidth) + 1) * this.tabWidth;
                    break;
                case "\r":
                case "\n":
                    return offset + pos;
                default:
                    ++pos;
            }
        }
        return offset + pos;
    };

SciMozMock.prototype.positionBefore =
    function SciMozMock_positionBefore(pos)
        pos - 1;

SciMozMock.prototype.positionFromLine =
    function SciMozMock_positionFromLine(aLine)
        (this.text.match(new RegExp("(?:[^\n]*\n){" + aLine + "}", "m")) || [])
             .reduce(function(n, s) n + s.length, 0);

SciMozMock.prototype.replaceTarget =
    function SciMozMock_replaceTarget(length, text) {
        if (length >= 0) text = text.substring(0, length);
        this.text = this.text.substr(0, this.targetStart) + text + this.text.substr(this.targetEnd);
        this.targetEnd = this.targetStart + text.length;
        return text.length;
    };

Object.defineProperty(SciMozMock.prototype, "selectionEnd", {
    get: function() Math.max(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "selectionStart", {
    get: function() Math.min(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "selText", {
    get: function() this.text.substring(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

SciMozMock.prototype.setSelection =
SciMozMock.prototype.setSel =
    function SciMozMock_setSel(start, end) {
        if (end < 0) end = this.text.length;
        if (start < 0) start = end;
        log.debug("setSelection: [" + start + "," + end + "] = " +
                  this.getTextRange(start, end));
        [this.anchor, this.currentPos] = [start, end];
    };


SciMozMock.prototype.docLineFromVisible =
    function SciMozMock_docLineFromVisible(lineNo) lineNo;

SciMozMock.prototype.visibleFromDocLine =
    function SciMozMock_visibleFromDocLine(lineNo) lineNo;


SciMozMock.prototype.searchAnchor = function SciMozMock_searchAnchor() {
    this._searchAnchor = this.currentPos;
};

/* Flags: 
val SCFIND_WHOLEWORD=2
val SCFIND_MATCHCASE=4
val SCFIND_WORDSTART=0x00100000
val SCFIND_REGEXP=0x00200000
val SCFIND_POSIX=0x00400000
*/

// Assume flags is always 0 */
SciMozMock.prototype.searchNext = function SciMozMock_searchNext(flags, text) {
    if (flags) {
        throw new Error("searchNext: can't handle flag != 0, got" + flags);
    }
    return this.text.indexOf(text, this._searchAnchor);
};

SciMozMock.prototype.searchPrev = function SciMozMock_searchPrev(flags, text) {
    if (flags) {
        throw new Error("searchPrev: can't handle flag != 0, got" + flags);
    }
    return this.text.lastIndexOf(text, this._searchAnchor);
};

/* Unimplemented stubs */
SciMozMock.prototype.addRefDocument = function SciMozMock_addRefDocument() void(0);SciMozMock.prototype.setSavePoint = function SciMozMock_setSavePoint() void(0);
SciMozMock.prototype.releaseDocument = function SciMozMock_releaseDocument() void(0);
SciMozMock.prototype.indicSetFore = function SciMozMock_indicSetFore() void(0);
SciMozMock.prototype.indicSetStyle = function SciMozMock_indicSetStyle() void(0);
SciMozMock.prototype.setMarginWidthN = function SciMozMock_setMarginWidthN() void(0);
SciMozMock.prototype.setProperty = function SciMozMock_setProperty() void(0);
SciMozMock.prototype.setFoldFlags = function SciMozMock_setFoldFlags() void(0);
SciMozMock.prototype.setYCaretPolicy = function SciMozMock_setYCaretPolicy() void(0);
SciMozMock.prototype.setVisiblePolicy = function SciMozMock_setVisiblePolicy() void(0);
SciMozMock.prototype.ensureVisibleEnforcePolicy = function SciMozMock_ensureVisibleEnforcePolicy() void(0);
SciMozMock.prototype.chooseCaretX = function SciMozMock_chooseCaretX() void(0);
SciMozMock.prototype.setKeyWords = function SciMozMock_setKeyWords() void(0);
SciMozMock.prototype.setCharsDefault = function SciMozMock_setCharsDefault() void(0);
SciMozMock.prototype.setSavePoint = function SciMozMock_setSavePoint() void(0);
SciMozMock.prototype.beginUndoAction = function SciMozMock_beginUndoAction() void(0);
SciMozMock.prototype.endUndoAction = function SciMozMock_endUndoAction() void(0);
SciMozMock.prototype.emptyUndoBuffer = function SciMozMock_emptyUndoBuffer() void(0);
SciMozMock.prototype.hideSelection = function SciMozMock_hideSelection(aHide) void(0);
SciMozMock.prototype.lineScroll = function SciMozMock_lineScroll() void(0);


(function() {
    var interfaces = [Ci.ISciMoz, Ci.ISciMozLite];
    for (let i = 0; ("ISciMoz_Part" + i) in Ci; ++i) {
        interfaces.push(Ci["ISciMoz_Part" + i]);
    }
    SciMozMock.prototype.classInfo = XPCOMUtils.generateCI({
        classID: null,
        contractID: null,
        classDescription: "Mock SciMoz",
        interfaces: interfaces,
        flags: 0,
    });
    SciMozMock.prototype.QueryInterface = XPCOMUtils.generateQI(interfaces);
})();

/**
 * Create a new mock KoDoc
 * @note The parameters are all optional, and use a dictionary.
 * @param text {String} The text to pre-fill
 * @param url {String} The
 */
function KoDocMock(aParams) {
    if (typeof(aParams) == "undefined") {
        aParams = {};
    }
    this.displayPath = aParams.displayPath ||
        Cc["@mozilla.org/uuid-generator;1"]
          .getService(Ci.nsIUUIDGenerator)
          .generateUUID()
          .number;
}

/**
 * Create a mock <scintilla> element
 */
function ScintillaMock(aView) {
    this._view = aView;
}

Object.defineProperty(ScintillaMock.prototype, "scimoz", {
    get: function() this._view.scimoz,
    configurable: true, enumerable: true,
});


XPCOMUtils.defineLazyGetter(ScintillaMock.prototype, "scheme",
    function() Cc['@activestate.com/koScintillaSchemeService;1']
                 .getService(Ci.koIScintillaSchemeService)
                 .getScheme("Default"));

/**
 * Create a new mock view
 * @note The parameters are all optional, and use a dictionary.
 * @param text {String} The text to pre-fill
 */
function ViewMock(aParams) {
    if (typeof(aParams) == "undefined") {
        aParams = {};
    }
    this.uid = Cc["@mozilla.org/uuid-generator;1"]
                 .getService(Ci.nsIUUIDGenerator)
                 .generateUUID()
                 .number;
    this.koDoc = new KoDocMock({});
    if ('@activestate.com/ISciMozHeadless;1' in Cc) {
        // Headless SciMoz is only available on Linux.
        this.scimoz = Cc['@activestate.com/ISciMozHeadless;1']
                     .createInstance(Ci.ISciMoz);
    } else {
        this.scimoz = new SciMozMock();
    }
    this.scimoz.text = aParams.text || "";
    this.scintilla = new ScintillaMock(this);
}
this.ViewMock = ViewMock;

ViewMock.prototype.getViews = function ViewMock_getViews(aRecurse)
    [this];

function ViewBookmarkableMock(aParams) {
    ViewMock.apply(this, Array.slice(arguments));
    this.removeAllBookmarks();
}
this.ViewBookmarkableMock = ViewBookmarkableMock;

ViewBookmarkableMock.prototype = Object.create(ViewMock.prototype);
ViewBookmarkableMock.prototype.QueryInterface =
    XPCOMUtils.generateQI([Ci.koIBookmarkableView]);


ViewBookmarkableMock.prototype.addBookmark =
function ViewBookmarkableMock_addBookmark(aLineNo) {
    log.debug("ViewBookmarkable: addBookmark: " + aLineNo);
    this._bookmarks[aLineNo] = true;
}

ViewBookmarkableMock.prototype.removeBookmark =
function ViewBookmarkableMock_removeBookmark(aLineNo) {
    log.debug("ViewBookmarkable: removeBookmark: " + aLineNo);
    delete this._bookmarks[aLineNo];
}

ViewBookmarkableMock.prototype.removeAllBookmarks =
function ViewBookmarkableMock_removeAllBookmarks() {
    log.debug("ViewBookmarkable: removeAllBookmarks");
    this._bookmarks = {};
}

ViewBookmarkableMock.prototype.hasBookmark =
function ViewBookmarkableMock_hasBookmark(aLineNo)
    Object.hasOwnProperty.call(this._bookmarks, aLineNo);

Object.defineProperty(ViewBookmarkableMock.prototype, "bookmarks", {
    get: function() Object.keys(this._bookmarks).map(function(n) parseInt(n, 10)),
    configurable: true, enumerable: true,
});

}).apply(ko.views);

ko.views.currentView = new ko.views.ViewMock();
