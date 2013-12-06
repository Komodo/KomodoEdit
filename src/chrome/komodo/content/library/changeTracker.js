/* Copyright (c) 2000 - 2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Track changes: show how editor buffers have changed
 *
 * See KD 295: Track Changes
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.changeTracker)=='undefined') {
    ko.changeTracker = {};
}
(function() {
var log = ko.logging.getLogger("changeTracker");
//log.setLevel(ko.logging.LOG_INFO);

Components.utils.import("resource://gre/modules/Services.jsm"); // for Services

const CHANGES_NONE = 0;
const CHANGES_INSERT = 1;
const CHANGES_DELETE = 2;
const CHANGES_REPLACE = 3;

const MARGIN_POSN_DELETE = 0;
const MARGIN_POSN_INSERT = 1;
const MARGIN_POSN_REPLACE = 2;

const SHOW_CHANGES_NONE = 0;
const SHOW_UNSAVED_CHANGES = 1;
const SHOW_SCC_CHANGES = 2;

this.ChangeTracker = function ChangeTracker(view) {
    this.view = view;
    this.handleFileSaved = this.handleFileSaved.bind(this);
};

const prefTopics = ['editor-scheme', 'showChangesInMargin'];
this.ChangeTracker.prototype.init = function init() {
    this.timeoutId = null;
    this.timeoutDelay = 500; // msec
    this.marginController = new ko.changeTracker.MarginController(this, this.view); 
    this.prefObserverSvc = ko.prefs.prefObserverService;
    this.prefObserverSvc.addObserverForTopics(this, prefTopics.length, prefTopics, false);
    this.lastInsertions = {};
    this.deletedTextLines = [];
    this.lastChangedLines = {}; // Map lineNo => [oldLine, newLine]
    this.showChangesInMargin = this.view.prefs.getLong('showChangesInMargin', SHOW_CHANGES_NONE);
    if (this.showChangesInMargin) {
        this._activateObservers();
    }
    //TODO: Make a lazy getter for onDiskTextLines
    this.onDiskTextLines = null;
    this.deletedAnnotationLineNo = null;
};

this.ChangeTracker.prototype._activateObservers = function _activateObservers() {
    const flags = (Components.interfaces.ISciMoz.SC_MOD_INSERTTEXT
                   |Components.interfaces.ISciMoz.SC_MOD_DELETETEXT);
    Services.obs.addObserver(this, 'scheme-changed', false);
    window.addEventListener('file_saved', this.handleFileSaved, false);
    this.view.addModifiedHandler(this.onModified, this, 2000, flags);
}

this.ChangeTracker.prototype._deactivateObservers = function _deactivateObservers() {
    this.view.removeModifiedHandler(this.onModified);
    window.removeEventListener('file_saved', this.handleFileSaved, false);
    Services.obs.removeObserver(this, 'scheme-changed', false);
}

this.ChangeTracker.prototype.finalize = function finalize() {
    if (!('onDiskTextLines' in this)) {
        // This changeTracker was never init'ed\n");
        return;
    }
    if (this.prefObserverSvc) {
        this.prefObserverSvc.removeObserverForTopics(this, prefTopics.length, prefTopics);
    }
    if (this.showChangesInMargin !== SHOW_CHANGES_NONE) {
        this._deactivateObservers();
        if (this.timeoutId !== null) {
            clearTimeout(this.timeoutId);
        }
    }
};

this.ChangeTracker.prototype.observe = function(subject, topic, data) {
    if (topic == 'scheme-changed' || topic == 'editor-scheme') {
        this.marginController.refreshMarginProperies();
    } else if (topic == 'showChangesInMargin') {
        let oldMarginType = this.showChangesInMargin;
        this.showChangesInMargin = this.view.prefs.getLong('showChangesInMargin', SHOW_CHANGES_NONE);
        if (oldMarginType === this.showChangesInMargin) {
            return; // No change
        }
        try {
            if (oldMarginType !== SHOW_CHANGES_NONE) {
                this.marginController.clearOldMarkers(this.view.scimoz);
            }
            if (this.showChangesInMargin !== SHOW_CHANGES_NONE) {
                this.onModified();
                this._activateObservers();
            } else {
                this._deactivateObservers();
            }
        } catch(ex) {
            log.exception(ex, "Problem observing showChangesInMargin");
        }
    }
};

this.ChangeTracker.prototype.handleFileSaved = function handleFileSaved(event) {
    var view = event.getData("view");
    if (view == this.view) {
        this.onModified();
        this.onDiskTextLines = null;
    }
};

this.ChangeTracker.prototype.onModified = function onModified() {
    if (this.timeoutId !== null) {
        clearTimeout(this.timeoutId);
    }
    // For now, don't bother handling any of the arguments
    // and recalc the whole margin.
    this.timeoutId = setTimeout(this._handleOnModified.bind(this), this.timeoutDelay);
};

this.ChangeTracker.prototype._getChangeInfo = function _getChangeInfo() {
    var koDoc = this.view.koDoc;
    var scimoz = this.view.scimoz;
    var changes = koDoc.getUnsavedChangeInstructions({});
    var lastInsertions = {}; // map firstLine => [lastLine]
    var deletedTextLines = {}; // firstLine => array of textLines (no EOLs)
    var lastChangedLines = {}; // Map current lineNo => [oldLine, newLine]
    var change, lim = changes.length;
    for (var i = 0; i < lim; ++i) {
        let { tag, i1, i2, j1, j2 } = changes[i];
        switch(tag) {
        case 'equal':
            break;
        case 'replace':
            {
                this._refreshOnDiskLines();
                let delta = i2 - i1;
                for (let idx = 0; idx < delta; ++idx) {
                    lastChangedLines[j1 + idx] = [this.onDiskTextLines[i1 + idx],
                                                  this._getLine(scimoz, j1 + idx)];
                }
            }
            break;
            
        case 'delete':
            this._refreshOnDiskLines();
            deletedTextLines[j1] = this.onDiskTextLines.slice(i1, i2);
            break;
        case 'insert':
            lastInsertions[j1] = j2;
            break;
        default:
            log.error("Unexpected getUnsavedChangeInstructions tag: " + tag);
        }
    }
    
    this.marginController.updateMargins(lastInsertions, deletedTextLines, lastChangedLines);
    this.lastInsertions = lastInsertions;
    this.deletedTextLines = deletedTextLines;
    this.lastChangedLines = lastChangedLines;
};

this.ChangeTracker.prototype._refreshOnDiskLines = function _refreshOnDiskLines() {
    if (this.onDiskTextLines !== null) {
        return;
    }
    this.onDiskTextLines = this.view.koDoc.getOnDiskTextLines();
};

this.ChangeTracker.prototype._getLine = function(scimoz, lineNo) {
    var val = {};
    scimoz.getLine(lineNo, val);
    return val.value;
};

this.ChangeTracker.prototype._handleOnModified = function _handleOnModified() {
    this.timeoutId = null;
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    if (this.showChangesInMargin === SHOW_SCC_CHANGES) {
        log.error("SCC changes aren't yet supported");
        return;
    }
    this._getChangeInfo();
};

this.ChangeTracker.prototype._getDeletedTextLines = function _getDeletedTextLines(lineNo) {
    if (!(lineNo in this.deletedTextLines)) {
        log.error("**** Can't find " + lineNo + " in this.deletedTextLines:\n"
                  + Object.keys(this.deletedTextLines));
        return null;
    }
    return this.deletedTextLines[lineNo];
};

const ADDED_TEXT_DECORATOR = Components.interfaces.koILintResult.DECORATOR_TABSTOP_TS1;
this.ChangeTracker.prototype.onDwellStart = function onDwellStart(x, lineNo) {
    // x: x field of the point(x,y) in scintilla view coordinates
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    var changeMask = this.marginController.activeMarkerMask(x, lineNo);
    if (changeMask & (1 << CHANGES_DELETE)) {
        this._showDeletions(lineNo);
    }
    else if (changeMask & (1 << CHANGES_REPLACE)) {
        this._showReplacements(lineNo);
    }
};

this.ChangeTracker.prototype._showDeletions = function _showDeletions(lineNo) {
    this.deletedAnnotationLineNo = null;
    
    // Put up an annotation of the missing lines.
    var lines = this._getDeletedTextLines(lineNo);
    if (lines === null) {
        return;
    }
    if (lineNo > 0) {
        // Deleted-line annotations look better above the current line.
        lineNo -= 1;
    }
    var scimoz = this.view.scimoz;
    var eol = "";  // not: ["\r\n", "\r", "\n"][scimoz.eOLMode];
    var text = lines.map(function(s) "-" + s).join(eol).replace(/(?:\n|\r\n?)$/, '');
    
    scimoz.annotationSetText(lineNo, text);
    scimoz.annotationVisible = scimoz.ANNOTATION_STANDARD;
    let styleNo;
    try {
        styleNo = this.view.koDoc.languageObj.getCommentStyles()[0];
    } catch(e) {
        log.exception(e, "Failed to get a comment style");
        styleNo = 0;
    }
    scimoz.annotationSetStyle(lineNo, styleNo);
    this.deletedAnnotationLineNo = lineNo;
};

this.ChangeTracker.prototype._showReplacements = function _showReplacements(lineNo) {
    this.deletedAnnotationLineNo = null;
    if (!(lineNo in this.lastChangedLines)) {
        log.error("Can't find line " + lineNo + " in lastChangedLines");
        return;
    }
    let [lineBefore, lineAfter] = this.lastChangedLines[lineNo];
    var eolBefore, eolAfter;
    const ptn = /(.*)(\n|\r?\n)$/;
    var m = ptn.exec(lineBefore);
    if (m) {
        lineBefore = m[1];
        eolBefore = m[2];
    } else {
        eolBefore = "";
    }
    m = ptn.exec(lineAfter);
    if (m) {
        lineAfter = m[1];
        eolAfter = m[2];
    } else {
        eolAfter = "";
    }
    var diffCodes = this.view.koDoc.diffStringsAsChangeInstructions(lineBefore, lineAfter);
    
    var fixedLineBeforeParts = ['-'], fixedLineAfterParts = ['+'];
    //TODO: Replace this part with styling the annotation box.
    diffCodes.forEach(function(diffCode) {
        const { tag:tag, i1:i1, i2:i2, j1:j1, j2:j2 } = diffCode;
        switch(tag) {
            case 'equal':
                fixedLineBeforeParts.push(lineBefore.substring(i1, i2));
                fixedLineAfterParts.push(lineAfter.substring(j1, j2));
                break;
            case 'insert':
                fixedLineAfterParts.push(">+>" + lineAfter.substring(j1, j2) + "<+<");
                break;
            case 'delete':
                fixedLineBeforeParts.push(">->" + lineBefore.substring(i1, i2) + "<-<");
                break;
            case 'replace':
                fixedLineBeforeParts.push(">->" + lineBefore.substring(i1, i2) + "<-<");
                fixedLineAfterParts.push(">+>" + lineAfter.substring(j1, j2) + "<+<");
                break;
            default:
                log.error("Unrecognized diff tag of " + tag);
        }
    })
    
    var text = fixedLineBeforeParts.join("") + eolBefore + fixedLineAfterParts.join("");
    
    var scimoz = this.view.scimoz;
    scimoz.annotationSetText(lineNo, text);
    scimoz.annotationVisible = scimoz.ANNOTATION_STANDARD;
    let styleNo;
    try {
        styleNo = this.view.koDoc.languageObj.getCommentStyles()[0];
    } catch(e) {
        log.exception(e, "Failed to get a comment style");
        styleNo = 0;
    }
    scimoz.annotationSetStyle(lineNo, styleNo);
    this.deletedAnnotationLineNo = lineNo;
};

this.ChangeTracker.prototype.onDwellEnd = function onDwellEnd() {
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    var scimoz = this.view.scimoz;
    if (this.deletedAnnotationLineNo !== null) {
        //TODO: Come up with a better way of managing annotations.  This way
        // we can't scroll large annotations into view, and we can't click on
        // them to select deleted text.
        scimoz.annotationRemoveAtLine(this.deletedAnnotationLineNo);
        this.deletedAnnotationLineNo = null;
    }
};

this.MarginController = function MarginController(changeTracker, view) {
    this.changeTracker = changeTracker; // Don't think we'll need this
    this.view = view;
    this.refreshMarginProperies();
    this.lastInsertions = {};
    this.deletedTextLines = {};
    this.lastChangedLines = {};
};

this.MarginController.prototype = {
    constructor: this.MarginController,

    _fix_rgb_color: function _fix_rgb_color(cssColor) {
        if (cssColor[0] == "#") {
            if (cssColor.length == 4) {
                return parseInt(cssColor[1] + cssColor[1] +
                                cssColor[2] + cssColor[2] +
                                cssColor[3] + cssColor[3], 16);
            }
            // Strip off the '#' and parse as is.
            // Most of the time there will be 6 hexdigits.
            return parseInt(cssColor.substring(1), 16);
        }
        return cssColor;
    },

    _initMarkerStyles: function(markerStyleSteps) {
        const styleOffset = 255;
        const marginCharacterSize = 6;
        const scimoz = this.view.scimoz;
        scimoz.marginStyleOffset = styleOffset;

        var insertColor, deleteColor, replaceColor;
        try {
            insertColor = this._fix_rgb_color(this.view.scheme.getColor("changeMarginInserted"));
        } catch(ex) {
            insertColor = 0xa3dca6; // BGR for a muted green
        }
        try {
            deleteColor = this._fix_rgb_color(this.view.scheme.getColor("changeMarginDeleted"));
        } catch(ex) {
            deleteColor = 0x5457e7; // BGR for a muted red
        }
        try {
            replaceColor = this._fix_rgb_color(this.view.scheme.getColor("changeMarginReplaced"));
        } catch(e) {
            replaceColor = 0xe8d362; // BGR for a muted yellow (maybe...., looks like RGB to me)
        }
        
        /* Don't use 0 as a style number. marginGetStyles and marginSetStyles
        uses byte-strings of concatenated style numbers, but the implementation
        can't handle null bytes */
        this.clearStyleNum = 1;
        const defaultBackColor = scimoz.styleGetBack(scimoz.STYLE_LINENUMBER);
        scimoz.styleSetBack(this.clearStyleNum + styleOffset, defaultBackColor);
        scimoz.styleSetSize(this.clearStyleNum + styleOffset, marginCharacterSize);
        
        this.insertStyleNum = this.clearStyleNum + 1;
        const insertBackColor = insertColor;
        scimoz.styleSetBack(this.insertStyleNum + styleOffset, insertBackColor);
        scimoz.styleSetSize(this.insertStyleNum + styleOffset, marginCharacterSize);
        
        this.deleteStyleNum = this.clearStyleNum + 2;
        const deleteBackColor = deleteColor;
        scimoz.styleSetBack(this.deleteStyleNum + styleOffset, deleteBackColor);
        scimoz.styleSetSize(this.deleteStyleNum + styleOffset, marginCharacterSize);
        
        this.replaceStyleNum = this.clearStyleNum + 3;
        const replaceBackColor = replaceColor;
        scimoz.styleSetBack(this.replaceStyleNum + styleOffset, replaceBackColor);
        scimoz.styleSetSize(this.replaceStyleNum + styleOffset, marginCharacterSize);
    },
    
    _initMargins: function() {
        var scimoz = this.view.scimoz;
        scimoz.setMarginTypeN(3, scimoz.SC_MARGIN_RTEXT); // right-justified text
        var marginWidth = scimoz.textWidth(this.clearStyleNum, "   "); // 3 spaces for del/ins/replace
        marginWidth += 4; // Provide some padding between the markers and the editor text.
        scimoz.setMarginWidthN(3, marginWidth);
        scimoz.setMarginSensitiveN(3, true);
    },
    
    activeMarkerMask: function(x, lineNo) {
        // x: x field of the point(x,y) in scintilla view coordinates
        const scimoz = this.view.scimoz;
        const chars = this._getMarginText(lineNo);
        if (chars.length != 3) {
            return 0;
        }
        const styles = this._getMarginStyles(lineNo);
        // The margin of interest has 3 sub-margins, corresponding to delete, insert,
        // and replace, in that order.
        // currSubMargin is the sub-margin the cursor is associated with
        var currSubMargin;
        var widthSoFar = 0;

        // Also, this margin's text is right-aligned, so the value of x
        // is including the unused text to the left of the marker's text.
        // We need to find the unused part of the margin, and subtract
        // that from x.

        // There's a left offset in the margin due to right-aligning
        // the margin text, so we need to figure out what it is.
        for (var i = 0; i < styles.length; i++) {
            widthSoFar += scimoz.textWidth(styles[i].charCodeAt(0), " ");
        }
        let delta = scimoz.getMarginWidthN(3) - widthSoFar;
        if (delta > 0 && x > delta) {
            x -= delta;
        }

        widthSoFar = 0;
        for (var i = 0; i < styles.length; i++) {
            // Invariant: widthSoFar <= x
            let thisWidth = scimoz.textWidth(styles[i].charCodeAt(0), " ");
            let nextWidth = widthSoFar + thisWidth;
            if (nextWidth >= x) {
                currSubMargin = i;
                // If the current sub-margin is clear, and the cursor is close to a
                // non-clear sub-margin, go with that instead.
                if (styles[i].charCodeAt(0) === this.clearStyleNum) {
                    const slopWidth = thisWidth / 2;
                    if (widthSoFar + slopWidth >= x && i > 0) {
                        currSubMargin = i - 1;
                    } else if (nextWidth - slopWidth <= x && i < styles.length - 1) {
                        currSubMargin = i + 1;
                    }
                }
                break;
            }
            widthSoFar = nextWidth;
        }
        let styleCheck = function(pos, styleNum) {
            return (styles[pos].charCodeAt(0) === styleNum && currSubMargin === pos);
        }
        if (styleCheck(MARGIN_POSN_DELETE, this.deleteStyleNum)) {
            return 1 << CHANGES_DELETE;
        }
        if (styleCheck(MARGIN_POSN_REPLACE, this.replaceStyleNum)) {
            return 1 << CHANGES_REPLACE;
        }
        if (styleCheck(MARGIN_POSN_INSERT, this.insertStyleNum)) {
            return 1 << CHANGES_INSERT;
        }
        return 0;
    },
    
    _specificMarkerSet: function _specificMarkerSet(line, styleNum, stylePosn) {
        var chars = this._getMarginText(line);
        if (chars.length != 3) {
            this.setupMarker(line);
        }
        var styles = this._getMarginStyles(line);
        styles[stylePosn] = String.fromCharCode(styleNum);
        this._setMarginStyles(line, styles);
    },
    
    delMarkerSet: function(line) {
        this._specificMarkerSet(line, this.deleteStyleNum, MARGIN_POSN_DELETE);
    },
    
    insMarkerSet: function(line) {
        this._specificMarkerSet(line, this.insertStyleNum, MARGIN_POSN_INSERT);
    },
    
    replaceMarkerSet: function(line) {
        this._specificMarkerSet(line, this.replaceStyleNum, MARGIN_POSN_REPLACE);
    },
    
    setupMarker: function(line) {
        this._setMarginText(line, [" ", " ", " "]);
        var defaultStyle = String.fromCharCode(this.clearStyleNum);
        this._setMarginStyles(line, [defaultStyle, defaultStyle, defaultStyle]);
    },
    
    _getMarginText: function(line) {
        try {
            var text = {};
            this.view.scimoz.marginGetText(line, text);
            text = text.value;
        } catch(e) {
            text = "";
        }
        return text.split("");
    },
    
    _setMarginText: function(line, chars) {
        chars = chars.join("");
        this.view.scimoz.marginSetText(line, chars);
    },
    
    _getMarginStyles: function(line) {
        try {
            var styles = {};
            this.view.scimoz.marginGetStyles(line, styles);
            styles = styles.value;
        } catch(e) {
            styles = "";
        }
        return styles.split("");
    },
    
    _setMarginStyles: function(line, styles) {
        styles = styles.join("");
        this.view.scimoz.marginSetStyles(line, styles);
    },

    refreshMarginProperies: function refreshMarginProperies() {
        this._initMarkerStyles(10); // maximum is 128
        this._initMargins();
    },
    
    _doUpdateMargins: function _doUpdateMargins(lastInsertions, deletedTextLines, lastChangedLines) {
        var scimoz = this.view.scimoz;
        this.clearOldMarkers(scimoz);
        // Now go through the insertions and deletions
        for (let lineNo in deletedTextLines) {
            this.delMarkerSet(lineNo);
        }
        for (let lineNo in lastChangedLines) {
            this.replaceMarkerSet(lineNo);
        }
        for (let [lineStartNo, lineEndNo] in Iterator(lastInsertions)) {
            for (let lineNo = lineStartNo; lineNo < lineEndNo; lineNo++) {
                this.insMarkerSet(lineNo);
            }
        }
    },
    
    updateMargins: function updateMargins(lastInsertions, deletedTextLines, lastChangedLines) {
        this._doUpdateMargins(lastInsertions, deletedTextLines, lastChangedLines);
        this.lastInsertions = lastInsertions;
        this.deletedTextLines = deletedTextLines;
        this.lastChangedLines = lastChangedLines;
    },

    refreshMargins: function updateMargins() {
        this._doUpdateMargins(this.lastInsertions, this.deletedTextLines, this.lastChangedLines);
    },
    
    clearOldMarkers: function clearOldMarkers(scimoz) {
        // We can't use the held deletion/insertion lists because the line numbers
        // could have changed.
        for (let lineNo = 0; lineNo < scimoz.lineCount; lineNo++) {
            var chars = this._getMarginText(lineNo);
            if (chars.length != 3) {
                continue;
            }
            var styles = this._getMarginStyles(lineNo);
            styles[0] = String.fromCharCode(this.clearStyleNum);
            styles[1] = String.fromCharCode(this.clearStyleNum);
            styles[2] = String.fromCharCode(this.clearStyleNum);
            this._setMarginStyles(lineNo, styles);
        }
    },
    
    __EOF__: null
};
        
}).apply(ko.changeTracker);
