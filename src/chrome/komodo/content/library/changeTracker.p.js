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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2014
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

/* Track changes: show how editor buffers have changed
 *
 * See KD 295: Track Changes
 */

if (typeof(ko) === 'undefined') {
    var ko = {};
}

if (typeof(ko.changeTracker) === 'undefined') {
    ko.changeTracker = {};
}
(function() {
var log = ko.logging.getLogger("changeTracker");
//log.setLevel(ko.logging.LOG_INFO);

var escapeLines = function(textLines) {
    return textLines.map(function(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    })
}

Components.utils.import("resource://gre/modules/Services.jsm"); // for Services

const CHANGES_NONE = 0;
const CHANGES_INSERT = 1;
const CHANGES_DELETE = 2;
const CHANGES_REPLACE = 3;

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
    this.firstInterestingLine = {}; // Map lineNo => first line (for insert & change)
    this.lastInsertions = {}; // Map firstLine => [lastLine]
    this.lastNewChanges = {}; // Map firstLine => [lastLine]
    this.deletedTextLineRange = {}; // Map firstLine(new) => [firstLine(old), lastLine(old)]
    this.changedTextLineRange = {}; // Like deletedTextLines:  new(first) => old range
    this.insertedOldLineRange = {}; // Map firstLine => oldLineRange (insert only)
    this.showChangesInMargin = this.view.prefs.getLong('showChangesInMargin', SHOW_CHANGES_NONE);
    if (this.showChangesInMargin) {
        this._activateObservers();
    } else {
        this.marginController.hideMargin();
    }
    //TODO: Make a lazy getter for onDiskTextLines
    this.onDiskTextLines = null;
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
                this.marginController.showMargin();
                this.onModified();
                this._activateObservers();
            } else {
                this._deactivateObservers();
                this.marginController.hideMargin();
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
    // These vars are documented in init() for their this.X counterparts
    var lastInsertions = {};
    var lastNewChanges = {};
    var deletedTextLineRange = {};
    this.firstInterestingLine = {};
    this.changedTextLineRange = {};
    this.insertedOldLineRange = {};
    var change, lim = changes.length;
    var delta;
    for (var i = 0; i < lim; ++i) {
        let { tag, i1, i2, j1, j2 } = changes[i];
        switch(tag) {
        case 'equal':
            break;
        case 'replace':
            lastNewChanges[j1] = j2;
            this.changedTextLineRange[j1] = [i1, i2];
            delta = j2 - j1;
            for (let idx = 0; idx < delta; ++idx) {
                this.firstInterestingLine[j1 + idx] = j1;
            }
            break;
            
        case 'delete':
            deletedTextLineRange[j1] = [i1, i2];
            break;
            
        case 'insert':
            lastInsertions[j1] = j2;
            delta = j2 - j1;
            for (let idx = 0; idx < delta; ++idx) {
                this.firstInterestingLine[j1 + idx] = j1;
            }
            this.insertedOldLineRange[j1] = [i1, i2];
            break;
            
        default:
            log.error("Unexpected getUnsavedChangeInstructions tag: " + tag);
        }
    }
    
    this.marginController.updateMargins(lastInsertions,
                                        deletedTextLineRange, lastNewChanges);
    this.lastInsertions = lastInsertions;
    this.deletedTextLineRange = deletedTextLineRange;
    this.lastNewChanges = lastNewChanges;
};

this.ChangeTracker.prototype._refreshOnDiskLines = function _refreshOnDiskLines() {
    if (this.onDiskTextLines !== null) {
        return;
    }
    this.onDiskTextLines = this.view.koDoc.getOnDiskTextLines();
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

this.ChangeTracker.prototype._getDeletedTextLines =
                    function(firstLineNo, lastLineNo) {
    this._refreshOnDiskLines();
    if (lastLineNo >= this.onDiskTextLines.length) {
        log.error("**** _getDeletedTextLines: can't get lines "
                  + [firstLineNo, lastLineNo]
                  + " from a file with only "
                  + this.onDiskTextLines.length
                  + " lines");
        return null;
    }
    return this.onDiskTextLines.slice(firstLineNo, lastLineNo).
           map(function(line) line.replace(/\n|\r\n?/, ""));
};

this.ChangeTracker.prototype.lineBarIsActive = function(lineNo) {
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return false;
    }
    var changeMask = this.marginController.activeMarkerMask(lineNo);
    return changeMask !== 0;
};

this.ChangeTracker.prototype.showChanges = function(lineNo) {
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    var changeMask = this.marginController.activeMarkerMask(lineNo);
    if (changeMask === 0) {
        return;
    }
    var oldLines = [], newLines = [];
    const DEL_MASK = 1 << CHANGES_DELETE;
    const INS_MASK = 1 << CHANGES_INSERT;
    const REP_MASK = 1 << CHANGES_REPLACE;
    const firstLineNo  = ((changeMask & DEL_MASK) ? lineNo :
                          this.firstInterestingLine[lineNo]);
    var oldLineRange = null, newLineRange;
    if (changeMask & (DEL_MASK|REP_MASK)) {
        let linesToUse = ((changeMask & REP_MASK) ? this.changedTextLineRange
                          : this.deletedTextLineRange);
        if (!(firstLineNo in linesToUse)) {
            log.warn("Can't find an entry for line "
                      + firstLineNo
                      + " in this."
                      + ((changeMask & REP_MASK) ? "changedTextLineRange"
                         : "deletedTextLineRange")
                      + "\n");
            return;
        }
        oldLineRange = linesToUse[firstLineNo];
        newLineRange = [firstLineNo, firstLineNo]; // If a deletion
        oldLines = this._getDeletedTextLines(oldLineRange[0], oldLineRange[1]);
        if (oldLines === null) {
 // Failed to get those lines
            return;
        }
    }
    if (changeMask & (INS_MASK|REP_MASK)) {
        if (!(lineNo in this.firstInterestingLine)) {
            log.warn("Can't find an entry for line "
                      + lineNo
                      + " in this.firstInterestingLine ("
                     + Object.keys(this.firstInterestingLine)
                     + ")");
            return;
        }
        let linesToUse = ((changeMask & REP_MASK) ? this.lastNewChanges
                          : this.lastInsertions);
        if (!(firstLineNo in linesToUse)) {
            log.warn("Can't find an entry for line "
                     + firstLineNo
                     + " in this."
                     + ((changeMask & REP_MASK) ? "changedTextLineRange"
                          : "lastInsertions")
                     + Object.keys(linesToUse));
            return;
        }
        if (!oldLineRange) {
            oldLineRange = this.insertedOldLineRange[firstLineNo];
        }
        newLineRange = [firstLineNo, linesToUse[firstLineNo]];
        let scimoz = this.view.scimoz;
        let firstPos = scimoz.positionFromLine(newLineRange[0]);
        let lastPos = scimoz.getLineEndPosition(newLineRange[1] - 1);
        let text = firstPos < lastPos ? scimoz.getTextRange(firstPos, lastPos) : "";
        newLines = text.split(/\n|\r\n?/);
    }
    // Write htmlLines to a temp file, get the URL, and then create a panel
    // with that iframe/src
    var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    var htmlFile = fileSvc.makeTempFile(".html", 'wb')
    var htmlURI = htmlFile.URI;
    var lastDot = htmlURI.lastIndexOf('.');
    //var jsURI = htmlURI.replace(/\.[^\.]+$/, ".js");
    
    //TODO:
    // Build up diffCodes = this.view.koDoc.diffStringsAsChangeInstructions(lineBefore, lineAfter);
    // and use that info to show how lines differ internally.
    var htmlLines = [
        '<html>',
        '<head>',
        '<style>',
        'body {',
        '    color: black;',
        '    background-color: white;',
        '    font-family: sans-serif;',
        '    font-size: medium;',
        '}',
        'pre.header {',
        '    margin-bottom: 0px;',
        '}',
        'pre.old {',
        '    background-color: #ffbbbb; /* light red */',
        '    margin-top: 4px;',
        '    margin-bottom: 0px;',
        '    padding-top: 0px;',
        '    padding-bottom: 0px;',
        '}',
        'pre.new {',
        '    background-color: #c1fdbb; /* light green */',
        '    margin-top: 4px;',
        '    margin-bottom: 0px;',
        '    padding-top: 0px;',
        '    padding-bottom: 0px;',
        '}',
        '</style>',
        //TODO: The JS code will be needed later, when the panel/iframe needs JavaScript to apply changes.
        //('<script src="' + jsURI + '">'),
        //'</script>',
        '<body>',
        '<pre class="header">',
        ('@@ -'
         + (oldLineRange[0] + 1)
         + ','
         + (oldLineRange[1] + 1)
         + ' +'
         + (newLineRange[0] + 1)
         + ','
         + (newLineRange[1] + 1)
         + ' @@'),
        '</pre>',
        '<pre class="old">'].
    concat(escapeLines(oldLines)).
    concat([
        '</pre>',
        '<pre class="new">',]).
    concat(escapeLines(newLines)).
    concat([
            '</pre>',
            '</html>',
            '']);
    htmlFile.puts(htmlLines.join("\n"));
    htmlFile.close();
    
    //var jsFile = Cc["@activestate.com/koFileEx;1"].getService(Ci.koIFileEx);
    //jsFile.URI = jsURI;
    //jsFile.open("wb");
    //var jsLines = ['alert("Loading file ' + jsFile.path.replace(/\\/g, '/') + '")', ''];
    //var text = jsLines.join("\n");
    //jsFile.puts(text);
    //jsFile.close();

    // Now make a panel with an iframe, point the iframe to htmlURI, and go
    this._createPanel(htmlFile);//, jsFile);
};

this.ChangeTracker.prototype._createPanel = function(htmlFile) {//, jsFile) {
    var panel = document.getElementById('changeTracker_panel');
    panel.hidePopup();
    var iframe = panel.childNodes[0];
    iframe.setAttribute("src", htmlFile.URI);
    var [x, y] = this.view._last_mousemove_xy;
    iframe.addEventListener("load", function(event) {
        panel.openPopup(this.view, "after_pointer", x, y, false, false);
        panel.width = 600;
        panel.height = 400;
        var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
        fileSvc.deleteTempFile(htmlFile.path, true);
        //fileSvc.deleteTempFile(jsFile.path, true);
    }.bind(this), true);
};

this.ChangeTracker.prototype.onDwellStart = function(x, y, lineNo) {
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    var changeMask = this.marginController.activeMarkerMask(lineNo);
    if (changeMask === 0) {
        return;
    }
    gEditorTooltipHandler.show(this.view, x, y, -1);
};

this.ChangeTracker.prototype.onDwellEnd = function onDwellEnd() {
    if (this.showChangesInMargin === SHOW_CHANGES_NONE) {
        return;
    }
    gEditorTooltipHandler.hide();
};

const MARGIN_POSN_DELETE = 0;
const MARGIN_POSN_INSERT = 1;
const MARGIN_POSN_REPLACE = 2;

const MARGIN_TEXT_LENGTH = 1;
const MARGIN_CHANGEMARGIN = 3;

this.MarginController = function MarginController(changeTracker, view) {
    this.changeTracker = changeTracker; // Don't think we'll need this
    this.view = view;
    this.refreshMarginProperies();
    this.lastInsertions = {};
    this.deletedTextLines = {};
    this.lastNewChanges = {};
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
        scimoz.setMarginTypeN(MARGIN_CHANGEMARGIN,
                              scimoz.SC_MARGIN_RTEXT); // right-justified text
        this.marginWidth = scimoz.textWidth(this.clearStyleNum, " "); // 1 space
        // Note: If we try to set the margin Width to a smaller value,
        // Scintilla will display the rest of the space in the previous margin,
        // and clicking on that will trigger the previous margin's handler
        scimoz.setMarginWidthN(MARGIN_CHANGEMARGIN, this.marginWidth);
        scimoz.setMarginSensitiveN(MARGIN_CHANGEMARGIN, true);
    },

    showMargin: function() {
        this.view.scimoz.setMarginWidthN(MARGIN_CHANGEMARGIN, this.marginWidth);
    },

    hideMargin: function() {
        this.view.scimoz.setMarginWidthN(MARGIN_CHANGEMARGIN, 0);
    },
    
    activeMarkerMask: function(lineNo) {
        if (this._getMarginText(lineNo).length != MARGIN_TEXT_LENGTH) {
            return 0;
        }
        const currStyle = this._getMarginStyles(lineNo)[0].charCodeAt(0);
        if (currStyle == this.deleteStyleNum) {
            return 1 << CHANGES_DELETE;
        }
        if (currStyle == this.replaceStyleNum) {
            return 1 << CHANGES_REPLACE;
        }
        if (currStyle == this.insertStyleNum) {
            return 1 << CHANGES_INSERT;
        }
        return 0;
    },
    
    _specificMarkerSet: function _specificMarkerSet(line, styleNum) {
        var chars = this._getMarginText(line);
        if (chars.length != MARGIN_TEXT_LENGTH) {
            this.setupMarker(line);
        }
        var styles = this._getMarginStyles(line);
        styles[0] = String.fromCharCode(styleNum);
        this._setMarginStyles(line, styles);
    },
    
    delMarkerSet: function(line) {
        this._specificMarkerSet(line, this.deleteStyleNum);
    },
    
    insMarkerSet: function(line) {
        this._specificMarkerSet(line, this.insertStyleNum);
    },
    
    replaceMarkerSet: function(line) {
        this._specificMarkerSet(line, this.replaceStyleNum);
    },
    
    setupMarker: function(line) {
        this._setMarginText(line, " ");
        var defaultStyle = String.fromCharCode(this.clearStyleNum);
        this._setMarginStyles(line, [defaultStyle]);
    },
    
    _getMarginText: function(line) {
        try {
            var text = {};
            this.view.scimoz.marginGetText(line, text);
            text = text.value;
        } catch(e) {
            log.exception(e, "Problem in _getMarginText");
            text = "";
        }
        return text;
    },
    
    _setMarginText: function(line, chars) {
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
    
    _doUpdateMargins: function _doUpdateMargins(lastInsertions, deletedTextLines, lastNewChanges) {
        var scimoz = this.view.scimoz;
        this.clearOldMarkers(scimoz);
        // Now go through the insertions and deletions
        for (let lineNo in deletedTextLines) {
            this.delMarkerSet(lineNo);
        }
        for (let [lineStartNo, lineEndNo] in Iterator(lastNewChanges)) {
            for (let lineNo = lineStartNo; lineNo < lineEndNo; lineNo++) {
                this.replaceMarkerSet(lineNo);
            }
        }
        for (let [lineStartNo, lineEndNo] in Iterator(lastInsertions)) {
            for (let lineNo = lineStartNo; lineNo < lineEndNo; lineNo++) {
                this.insMarkerSet(lineNo);
            }
        }
    },
    
    updateMargins: function updateMargins(lastInsertions, deletedTextLines, lastNewChanges) {
        this._doUpdateMargins(lastInsertions, deletedTextLines, lastNewChanges);
        this.lastInsertions = lastInsertions;
        this.deletedTextLines = deletedTextLines;
        this.lastNewChanges = lastNewChanges;
    },

    refreshMargins: function updateMargins() {
        this._doUpdateMargins(this.lastInsertions, this.deletedTextLines, this.lastNewChanges);
    },
    
    clearOldMarkers: function clearOldMarkers(scimoz) {
        // We can't use the held deletion/insertion lists because the line numbers
        // could have changed.
        for (let lineNo = 0; lineNo < scimoz.lineCount; lineNo++) {
            if (this._getMarginText(lineNo).length != MARGIN_TEXT_LENGTH) {
                continue;
            }
            var styles = this._getMarginStyles(lineNo);
            styles[0] = String.fromCharCode(this.clearStyleNum);
            this._setMarginStyles(lineNo, styles);
        }
    },
    
    __EOF__: null
};
        
}).apply(ko.changeTracker);
