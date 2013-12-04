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

const SHOW_CHANGES_NONE = 0;
const SHOW_UNSAVED_CHANGES = 1;
const SHOW_SCC_CHANGES = 2;

this.ChangeTracker = function ChangeTracker(view) {
    this.view = view;
    this.handleFileSaved = this.handleFileSaved.bind(this);
    this.deletedAnnotationLineNo = null;
};

//this.ChangeTracker.prototype.constructor = this.ChangeTracker;

const prefTopics = ['editor-scheme', 'showChangesInMargin'];
this.ChangeTracker.prototype.init = function init() {
    this.timeoutId = null;
    this.timeoutDelay = 500; // msec
    this.marginController = new ko.changeTracker.MarginController(this, this.view); 
    this.prefObserverSvc = ko.prefs.prefObserverService;
    this.prefObserverSvc.addObserverForTopics(this, prefTopics.length, prefTopics, false);
    this.lastInsertions = {};
    this.deletedTextLines = [];
    this.showChangesInMargin = this.view.prefs.getLong('showChangesInMargin', SHOW_CHANGES_NONE);
    if (this.showChangesInMargin) {
        this._activateObservers();
    }
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

this.ChangeTracker.prototype.destructor = function destructor() {
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

this.ChangeTracker.prototype._handleOnModified = function _handleOnModified() {
    this.timeoutId = null;
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    if (this.showChangesInMargin === SHOW_SCC_CHANGES) {
        dump("SCC changes aren't yet supported\n");
        return;
    }
            
    var koDoc = this.view.koDoc;
    var changeLines = koDoc.getUnsavedChanges().split(/\n|\r\n?/);
    var insertions = [];
    var firstInsertions = {}; // map anyLine => [firstLine]
    var lastInsertions = {}; // map firstLine => [lastLine]
    var deletions = [];
    var firstDeletions = [];
    var deletedTextLines = {}; // firstLine => array of textLines (no EOLs)
    var currentDeletedTextLines;
    
    var oldFileStart = -1;
    var oldFileCount;
    var newFileStart = -1;
    var newFileCount;
    var oldFileIdx, newFileIdx;
    
    var idx = 0, currLine;
    var lim = changeLines.length;
    for (; idx < lim; ++idx) {
        currLine = changeLines[idx];
        if (currLine.indexOf('@@') === 0) {
            break;
        }
    }
    // Now run through all the changes
    
    var firstDeletionLine = -1, firstInsertionLine = -1;
    
    for (; idx < lim; ++idx) {
        currLine = changeLines[idx];
        if (currLine.length === 0) {
            continue;
        }
        if (currLine.indexOf('@@') === 0) {
            var m = /@@\s*-(\d+),(\d+)\s*\+(\d+),(\d+)\s*@@/.exec(currLine);
            if (m) {
                // Sub 1 to make the line numbers 0-based
                oldFileIdx = oldFileStart = parseInt(m[1], 10) - 1;
                oldFileCount = parseInt(m[2], 10);
                newFileIdx = newFileStart = parseInt(m[3], 10) - 1;
                newFileCount = parseInt(m[4], 10);
            }
        } else {
            switch(currLine[0]) {
                case '+':
                    insertions.push(newFileIdx);
                    if (firstInsertionLine == -1) {
                        firstInsertionLine = newFileIdx;
                    }
                    firstInsertions[newFileIdx] = firstInsertionLine;
                    newFileIdx += 1;
                    firstDeletionLine = -1;
                    break;
                case '-':
                    //deletions.push(oldFileIdx);
                    deletions.push(oldFileIdx);
                    if (firstInsertionLine !== -1) {
                        lastInsertions[firstInsertions[firstInsertionLine]] = newFileIdx - 1;
                        firstInsertionLine = -1;
                    }
                    if (firstDeletionLine == -1) {
                        firstDeletionLine = newFileIdx; // not oldFileIdx
                        currentDeletedTextLines = deletedTextLines[firstDeletionLine] = [];
                    }
                    firstDeletions[oldFileIdx] = firstDeletionLine;
                    currentDeletedTextLines.push(currLine);
                    oldFileIdx += 1;
                    break;
                case ' ':
                    if (firstInsertionLine !== -1) {
                        lastInsertions[firstInsertions[firstInsertionLine]] = newFileIdx - 1;
                        firstInsertionLine = -1;
                    }
                    oldFileIdx += 1;
                    newFileIdx += 1;
                    firstDeletionLine = -1;
                    break;
                default:
                    log.error("Unexpected line: [" + currLine + "] at line " + idx + "\n"
                              + ", first charcode: " + currLine.charCodeAt(0)
                              + "currLine len: " + currLine.length);
            }
        }
    }
    if (firstInsertionLine !== -1) {
        lastInsertions[firstInsertions[firstInsertionLine]] = newFileIdx - 1;
        firstInsertionLine = -1;
    }
    
    this.marginController.updateMargins(lastInsertions, deletedTextLines);
    this.firstInsertions = firstInsertions;
    this.lastInsertions = lastInsertions;
    this.deletedTextLines = deletedTextLines;
};

this.ChangeTracker.prototype._getInsertedLineBounds = function _getInsertedLineBounds(lineNo) {
    if (!(lineNo in this.firstInsertions)) {
        log.error("**** Can't find " + lineNo + " in this.firstInsertions:\n"
                  + Object.keys(this.firstInsertions));
        
        return null;
    }
    let insertionStartLine = this.firstInsertions[lineNo];
    if (!(insertionStartLine in this.lastInsertions)) {
        log.error("**** Can't find " + insertionStartLine + " in this.lastInsertions:\n"
                  + Object.keys(this.lastInsertions));
        return null;
    }
    return [insertionStartLine, this.lastInsertions[insertionStartLine]];
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
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    var scimoz = this.view.scimoz;
    var changeMask = this.marginController.activeMarkerMask(lineNo);
    if (!(changeMask & (1 << CHANGES_DELETE))) {
        // Nothing to do here
        return;
    }
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
    var eol = ["\r\n", "\r", "\n"][scimoz.eOLMode];
    var text = lines.join(eol);
    
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

        var mutedGreen, mutedRed;
        try {
            mutedGreen = this._fix_rgb_color(this.view.scheme.getColor("changeMarginInserted"));
        } catch(ex) {
            mutedGreen = 0xa3dca6; // BGR for a muted green
        }
        try {
            mutedRed = this._fix_rgb_color(this.view.scheme.getColor("changeMarginDeleted"));
        } catch(ex) {
            mutedRed = 0x5457e7; // BGR for a muted red
        }
        
        /* Don't use 0 as a style number. marginGetStyles and marginSetStyles
        uses byte-strings of concatenated style numbers, but the implementation
        can't handle null bytes */
        this.clearStyleNum = 1;
        const defaultBackColor = scimoz.styleGetBack(scimoz.STYLE_LINENUMBER);
        scimoz.styleSetBack(this.clearStyleNum + styleOffset, defaultBackColor);
        scimoz.styleSetSize(this.clearStyleNum + styleOffset, marginCharacterSize);
        
        this.insertStyleNum = this.clearStyleNum + 1;
        const insertBackColor = mutedGreen;
        scimoz.styleSetBack(this.insertStyleNum + styleOffset, insertBackColor);
        scimoz.styleSetSize(this.insertStyleNum + styleOffset, marginCharacterSize);
        
        this.deleteStyleNum = this.clearStyleNum + 2;
        const deleteBackColor = mutedRed;
        scimoz.styleSetBack(this.deleteStyleNum + styleOffset, deleteBackColor);
        scimoz.styleSetSize(this.deleteStyleNum + styleOffset, marginCharacterSize);
    },
    
    _initMargins: function() {
        var scimoz = this.view.scimoz;
        scimoz.setMarginTypeN(3, scimoz.SC_MARGIN_RTEXT); // right-justified text
        var marginWidth = scimoz.textWidth(this.clearStyleNum, "  ");
        marginWidth += 4; // Provide some padding between the markers and the editor text.
        scimoz.setMarginWidthN(3, marginWidth);
        scimoz.setMarginSensitiveN(3, true);
    },
    
    insMarkerSet: function(line) {
        var chars = this._getMarginText(line);
        if (chars.length != 2) {
            this.setupMarker(line);
        }
        var styles = this._getMarginStyles(line);
        styles[1] = String.fromCharCode(this.insertStyleNum);
        this._setMarginStyles(line, styles);
    },
    
    activeMarkerMask: function(line) {
        var retVal = 0;
        const chars = this._getMarginText(line);
        if (chars.length != 2) {
            return retVal;
        }
        const styles = this._getMarginStyles(line);
        if (styles[0].charCodeAt(0) === this.deleteStyleNum) {
            retVal |= 1 << CHANGES_DELETE;
        }
        if (styles[1].charCodeAt(0) === this.insertStyleNum) {
            retVal |= 1 << CHANGES_INSERT;
        }
        return retVal;
    },
    
    delMarkerSet: function(line) {
        var chars = this._getMarginText(line);
        if (chars.length != 2) {
            this.setupMarker(line);
        }
        var styles = this._getMarginStyles(line);
        styles[0] = String.fromCharCode(this.deleteStyleNum);
        this._setMarginStyles(line, styles);
    },
    
    setupMarker: function(line) {
        this._setMarginText(line, [" ", " "]);
        var defaultStyle = String.fromCharCode(this.clearStyleNum);
        this._setMarginStyles(line, [defaultStyle, defaultStyle]);
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
    
    _doUpdateMargins: function _doUpdateMargins(lastInsertions, deletedTextLines) {
        var scimoz = this.view.scimoz;
        this.clearOldMarkers(scimoz);
        // Now go through the insertions and deletions
        for (let lineNo in deletedTextLines) {
            this.delMarkerSet(lineNo);
        }
        for (let [lineStartNo, lineEndNo] in Iterator(lastInsertions)) {
            for (let lineNo = lineStartNo; lineNo <= lineEndNo; lineNo++) {
                this.insMarkerSet(lineNo);
            }
        }
    },
    
    updateMargins: function updateMargins(lastInsertions, deletedTextLines) {
        this._doUpdateMargins(lastInsertions, deletedTextLines);
        this.lastInsertions = lastInsertions;
        this.deletedTextLines = deletedTextLines;
    },

    refreshMargins: function updateMargins() {
        this._doUpdateMargins(this.lastInsertions, this.deletedTextLines);
    },
    
    clearOldMarkers: function clearOldMarkers(scimoz) {
        // We can't use the held deletion/insertion lists because the line numbers
        // could have changed.
        for (let lineNo = 0; lineNo < scimoz.lineCount; lineNo++) {
            var chars = this._getMarginText(lineNo);
            if (chars.length != 2) {
                continue;
            }
            var styles = this._getMarginStyles(lineNo);
            styles[0] = String.fromCharCode(this.clearStyleNum);
            styles[1] = String.fromCharCode(this.clearStyleNum);
            this._setMarginStyles(lineNo, styles);
        }
    },
    
    __EOF__: null
};
        
}).apply(ko.changeTracker);
