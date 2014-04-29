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

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import("resource://gre/modules/Services.jsm"); // for Services

var fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);

const ciKoDoc = Ci.koIDocument;

const CHANGES_NONE = ciKoDoc.CHANGES_NONE;
const CHANGES_INSERT = ciKoDoc.CHANGES_INSERT;
const CHANGES_DELETE = ciKoDoc.CHANGES_DELETE;
const CHANGES_REPLACE = ciKoDoc.CHANGES_REPLACE;

const SHOW_CHANGES_NONE = 0;
const SHOW_UNSAVED_CHANGES = 1;

const ENDS_WITH_EOL_RE = /(?:\n|\r\n?)$/;

const CHANGE_TRACKER_TIMEOUT_DELAY = 500; // msec

this.ChangeTracker = function ChangeTracker(view) {
    this.view = view;
    this.scimoz = view.scimoz;
    this.marginController = new ko.changeTracker.MarginController(view); 
    this.showChangesInMargin = this.view.prefs.getLong('showChangesInMargin', SHOW_CHANGES_NONE);
    if (!this.showChangesInMargin) {
        this.marginController.hideMargin();
    }
    var numLines = this.onDiskTextLines ? this.onDiskTextLines.length : 0;
    this._referenceEndsWithEOL = (numLines
                                  ? ENDS_WITH_EOL_RE.test(this.onDiskTextLines[numLines - 1])
                                  : false);
    this.viewPrefObserverService = view.prefs.prefObserverService;
    this.viewPrefObserverService.addObserver(this, 'showChangesInMargin', false);
    this.onBlurHandlerBound = this.onBlurHandler.bind(this);
    this.escapeHandlerBound = this.escapeHandler.bind(this);
};

this.ChangeTracker.prototype.QueryInterface = XPCOMUtils.generateQI([Ci.koIChangeTracker]);

this.ChangeTracker.prototype.close = function() {
    this.changeTrackingOff();
    this.marginController.close();
    this.marginController = null;
    this.viewPrefObserverService.removeObserver(this, 'showChangesInMargin', false);
    this.viewPrefObserverService = null;
    this.view = null;
    this.scimoz = null;
};

this.ChangeTracker.prototype.onSchemeChanged = function() {
    this.marginController.refreshMarginProperies();
};

this.ChangeTracker.prototype.setupTracker = function(changeTrackerEnabled) {
    this.changeTrackerEnabled = changeTrackerEnabled;
    if (changeTrackerEnabled) {
        this.changeTrackingOn();
    }
};

this.ChangeTracker.prototype.getTooltipText = function(lineNo) {
    if (!this.changeTrackerEnabled ||
        !this.lineBarIsActive(lineNo)) {
        return null;
    }
    var panel = document.getElementById('changeTracker_panel');
    if (panel && panel.state == "closed") {
        if (!('viewsPropertiesBundle' in this)) {
            this.viewsPropertiesBundle = Cc["@mozilla.org/intl/stringbundle;1"].
                    getService(Ci.nsIStringBundleService).
                createBundle("chrome://komodo/locale/views.properties");
        }
        return this.viewsPropertiesBundle.GetStringFromName(
            "Click on the changebar for details");
    }
    return null;
};


this.ChangeTracker.prototype.onBlurHandler = function(event) {
    // Have we shown the panel and moved to a different document?
    let panel = document.getElementById('changeTracker_panel');
    if (panel.state != "closed" && panel.view != ko.views.manager.currentView) {
        panel.hidePopup();
        this.onPanelHide();
    }
};

this.ChangeTracker.prototype.changeTrackingOn = function() {
    this.clearOldMarkers();
    this.marginController.showMargin();
    this.view.addEventListener("blur", this.onBlurHandlerBound, false);
};

this.ChangeTracker.prototype.changeTrackingOff = function() {
    this.marginController.hideMargin();
    this.view.removeEventListener("blur", this.onBlurHandlerBound, false);
};

this.ChangeTracker.prototype.onPanelShow = function() {
    this.view.addEventListener("keypress", this.escapeHandlerBound, false);
};

this.ChangeTracker.prototype.onPanelHide = function() {
    this.view.removeEventListener("keypress", this.escapeHandlerBound, false);
};

this.ChangeTracker.prototype.escapeHandler = function(event) {
    var panel = document.getElementById('changeTracker_panel');
    // If the panel's visible should we close it on any keystroke,
    // when the target is the view?
    if (event.keyCode == event.DOM_VK_ESCAPE || panel.state == "closed") {
        panel.hidePopup();
        this.onPanelHide();
        event.stopPropagation();
        event.preventDefault();
    }
};

this.ChangeTracker.prototype.observe = function(doc, topic, data) {
    if (topic == 'showChangesInMargin') {
        let view = this.view;
        let oldVal = view.showChangesInMargin;
        view.showChangesInMargin = view.prefs.getLongPref(topic);
        this.onPrefChanged(topic, oldVal, view.showChangesInMargin);
        view.changeTrackerEnabled = view.showChangesInMargin > 0;
    }
};
        
this.ChangeTracker.prototype.setScimoz = function(scimoz) {
    this.marginController.scimoz = this.scimoz = scimoz;
};

this.ChangeTracker.prototype.onPrefChanged = function(prefName, oldVal, newVal) {
    if (prefName == 'showChangesInMargin') {
        let oldMarginType = this.showChangesInMargin;
        this.showChangesInMargin = newVal;
        this.marginController.clearOldMarkers();
        if (this.showChangesInMargin !== SHOW_CHANGES_NONE) {
            this.changeTrackingOn();
            //@@!!! show updates immediately.
            this._handleOnModifiedForChangeTracker();
        } else {
            this.changeTrackingOff();
        }
    }
};

this.ChangeTracker.prototype.showChangesOnFileLoad = function() {
    return false;
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
    var oldLines = {}, newLines = {}, oldLineRange = {}, newLineRange = {};
    var oldEndsWithEOL = {}, newEndsWithEOL = {};
    this.view.koDoc.trackChanges_getOldAndNewLines(lineNo, changeMask,
                                                   oldEndsWithEOL,
                                                   newEndsWithEOL,
                                                   {}, oldLineRange,
                                                   {}, newLineRange,
                                                   {}, oldLines,
                                                   {}, newLines);
    oldLineRange = oldLineRange.value;
    newLineRange = newLineRange.value;
    oldLines = oldLines.value;
    newLines = newLines.value;
    if (!oldLines.length && !newLines.length) {
        return;

    }
    // Write htmlLines to a temp file, get the URL, and then create a panel
    // with that iframe/src
    var htmlFile = fileSvc.makeTempFile(".html", 'wb')
    var htmlURI = htmlFile.URI;
    var lastDot = htmlURI.lastIndexOf('.');

    const missingNewline = "<span class='comment'>\\ No newline at end of file</span>";
    var noNewlineAtEndOfOldLines  = !oldEndsWithEOL ? [missingNewline] : [];
    var noNewlineAtEndOfNewLines  = !newEndsWithEOL ? [missingNewline] : [];
    var oldColor = this.marginController.getColorAsHexRGB('delete');
    var newColor = this.marginController.getColorAsHexRGB('insert');
    
    //TODO:
    // Build up diffCodes = this.view.koDoc.diffStringsAsChangeInstructions(lineBefore, lineAfter);
    // and use that info to show how lines differ internally.
    var htmlLines = [
        '<html>',
        '<head>',
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />',
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
        '    background-color: ' + oldColor + ' ; /* default: #ffbbbb: light red */',
        '    margin-top: 4px;',
        '    margin-bottom: 0px;',
        '    padding-top: 0px;',
        '    padding-bottom: 0px;',
        '}',
        'pre span.comment {',
        '    font-style: italic;',
        '    color: #808080;',
        '}',
        'pre.new {',
        '    background-color: ' + newColor + '; /* default: #c1fdbb: light rgb[1] */',
        '    margin-top: 4px;',
        '    margin-bottom: 0px;',
        '    padding-top: 0px;',
        '    padding-bottom: 0px;',
        '}',
        '</style>',
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
    concat(noNewlineAtEndOfOldLines).
    concat([
        '</pre>',
        '<pre class="new">',]).
    concat(escapeLines(newLines)).
    concat(noNewlineAtEndOfNewLines).
    concat([
            '</pre>',
            '</html>',
            '']);
    htmlFile.puts(htmlLines.join("\n"));
    htmlFile.close();

    var scimoz = this.scimoz;
    var undoTextFunc = function(event) {
        // Find the (j2 - j1) new lines at j2, remove them, and
        // replace with the (i2 - i1) old lines.
        scimoz.beginUndoAction();
        try {
            let j1Pos = scimoz.positionFromLine(newLineRange[0]);
            if (newLineRange[0] < newLineRange[1]) {
                let j2Pos = scimoz.positionFromLine(newLineRange[1]);
                // Verify that the lines in the editor correspond to the
                // lines we have here before zapping them.
                scimoz.targetStart = j1Pos;
                scimoz.targetEnd = j2Pos;
                scimoz.replaceTarget(0, "");
            }
            if (oldLineRange[0] < oldLineRange[1]) {
                let eol = ["\r\n", "\r", "\n"][scimoz.eOLMode];
                let oldText = oldLines.join(eol);
                if (oldEndsWithEOL) {
                    oldText += eol;
                }
                scimoz.targetStart = j1Pos;
                scimoz.targetEnd = j1Pos;
                scimoz.replaceTarget(oldText);
            }
            document.getElementById('changeTracker_panel').hidePopup();
        } catch(ex) {
            log.exception(ex, "Can't undo a change");
        } finally {
            scimoz.endUndoAction();
        }
    };
    // Now make a panel with an iframe, point the iframe to htmlURI, and go
    this._createPanel(htmlFile, undoTextFunc);
};

this.ChangeTracker.prototype._createPanel = function(htmlFile, undoTextFunc) {
    var panel = document.getElementById('changeTracker_panel');
    panel.hidePopup();
    var iframe = panel.getElementsByTagName("iframe")[0];
    var undoButton = document.getElementById('changeTracker_undo');
    iframe.setAttribute("src", htmlFile.URI);
    var [x, y] = this.view._last_mousemove_xy;
    var escapeHandler = function(event) {
        if (event.keyCode == event.DOM_VK_ESCAPE) {
            panel.hidePopup();
            event.stopPropagation();
            event.preventDefault();
        }
    };
    var iframeLoadedFunc = function(event) {
        try {
        panel.openPopup(this.view, "after_pointer", x, y, false, false);
        panel.sizeTo(600, 400);
        fileSvc.deleteTempFile(htmlFile.path, true);
        undoButton.addEventListener("command", undoTextFunc, false);
        this.onPanelShow();
        } catch(ex) {
            log.exception(ex, "problem in iframeLoadedFunc\n");
        }
    }.bind(this);
    var panelHiddenFunc = function(event) {
        undoButton.removeEventListener("command", undoTextFunc, false);
        iframe.removeEventListener("load", iframeLoadedFunc, true);
        panel.removeEventListener("popuphidden", panelHiddenFunc, false);
        panel.removeEventListener("keypress", escapeHandler, false);
        panel.removeEventListener("blur", panelBlurHandler, false);
        this.onPanelHide();
    }.bind(this);
    var panelBlurHandler = function(event) {
        panel.hidePopup();
    };
    iframe.addEventListener("load", iframeLoadedFunc, true);
    panel.addEventListener("popuphidden", panelHiddenFunc, true);
    panel.addEventListener("keypress", escapeHandler, false);
    panel.addEventListener("blur", panelBlurHandler, false);
    panel.view = this.view;
};

this.ChangeTracker.prototype.clearOldMarkers = function () {
    this.marginController.clearOldMarkers();
};

this.ChangeTracker.prototype.updateMarkers_deleteAtLine = function (lineNo) {
    this.marginController.updateMarkers_deleteAtLine(lineNo);
};

this.ChangeTracker.prototype.updateMarkers_insertByRange = function (lineStartNo, lineEndNo) {
    this.marginController.updateMarkers_insertByRange(lineStartNo, lineEndNo);
};

this.ChangeTracker.prototype.updateMarkers_replaceByRange = function (lineStartNo, lineEndNo) {
    this.marginController.updateMarkers_replaceByRange(lineStartNo, lineEndNo);
};

const MARGIN_POSN_DELETE = 0;
const MARGIN_POSN_INSERT = 1;
const MARGIN_POSN_REPLACE = 2;

const MARGIN_TEXT_LENGTH = 1;
// TODO: Move const for margin number to core editor file.
const MARGIN_CHANGEMARGIN = 3;

this.MarginController = function MarginController(view) {
    this.view = view;
    this.scimoz = view.scimoz;
    this.refreshMarginProperies();
    this.lastInsertions = {};
    this.deletedTextLines = {};
    this.lastNewChanges = {};
};

this.MarginController.prototype = {
    constructor: this.MarginController,

    close: function() {
        this.view = null;
        this.scimoz = null;
        this.lastInsertions = {};
        this.deletedTextLines = {};
        this.lastNewChanges = {};
    },

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

    getColorAsHexRGB: function(colorAction) {
        return this[colorAction + "RGBColor"];
    },

    _initMarkerStyles: function(markerStyleSteps) {
        const styleOffset = 255;
        const marginCharacterSize = 6;
        const scimoz = this.scimoz;
        scimoz.marginStyleOffset = styleOffset;

        var insertColor, deleteColor, replaceColor;
        var bgr_string_to_rgb_array = function(cssColor) {
            var red, green, blue, x;
            if (typeof(cssColor) == "string") {
                if (cssColor[0] == "#") {
                    cssColor = cssColor.substring(1);
                }
                if (cssColor.length == 3) {
                    x = parseInt(cssColor[0], 16);
                    blue = x << 8 + x;
                    x = parseInt(cssColor[1], 16);
                    green = x << 8 + x;
                    x = parseInt(cssColor[2], 16);
                    red = x << 8 + x;
                } else {
                    blue = parseInt(cssColor.substring(0, 2), 16);
                    green = parseInt(cssColor.substring(2, 4), 16);
                    red = parseInt(cssColor.substring(4, 6), 16);
                }
            } else {
                blue = (cssColor & 0xff0000) >> 16;
                green = (cssColor & 0x00ff00) >> 8;
                red = (cssColor & 0x0000ff);
            }
            return [red, green, blue];
        };
        var num_to_hex2 = function(v) {
            var s = v.toString(16);
            if (s.length == 2) {
                return s;
            }
            return "0" + s;
        };
        var bgr_to_desaturated_rgb_for_css = function(bgrColor) {
            var [red, green, blue] = bgr_string_to_rgb_array(bgrColor);
            // And now reduce the saturation.
            const [H, S, V] = xtk.color.rgb2hsv(red, green, blue);
            // Reduce the intensity of the color by 30%
            const S1 = S * 0.7;
            const [R2, G2, B2] = xtk.color.hsv2rgb(H, S1, V);
            return "#" + num_to_hex2(R2) + num_to_hex2(G2) + num_to_hex2(B2);
        };
        try {
            insertColor = this._fix_rgb_color(this.view.scheme.getColor("changeMarginInserted"));
        } catch(ex) {
            log.exception(ex, "couldn't get the insert-color");
            insertColor = 0xa3dca6; // BGR for a muted green
        }
        try {
            deleteColor = this._fix_rgb_color(this.view.scheme.getColor("changeMarginDeleted"));
        } catch(ex) {
            log.exception(ex, "couldn't get the delete-color");
            deleteColor = 0x5457e7; // BGR for a muted red
        }
        try {
            replaceColor = this._fix_rgb_color(this.view.scheme.getColor("changeMarginReplaced"));
        } catch(e) {
            log.exception(ex, "couldn't get the change-color");
            replaceColor = 0xe8d362; // BGR for a muted blue
        }
        try {
            this.insertRGBColor = bgr_to_desaturated_rgb_for_css(insertColor);
            this.deleteRGBColor = bgr_to_desaturated_rgb_for_css(deleteColor);
            this.replaceRGBColor = bgr_to_desaturated_rgb_for_css(replaceColor);
        } catch(e) {
            log.exception(e, "Failed to convert a color from bgr to rgb");
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
        var scimoz = this.scimoz;
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
        this.scimoz.setMarginWidthN(MARGIN_CHANGEMARGIN, this.marginWidth);
    },

    hideMargin: function() {
        this.scimoz.setMarginWidthN(MARGIN_CHANGEMARGIN, 0);
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
    
    _specificMarkerSet: function(line, styleNum) {
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
            this.scimoz.marginGetText(line, text);
            text = text.value;
        } catch(e) {
            log.exception(e, "Problem in _getMarginText");
            text = "";
        }
        return text;
    },
    
    _setMarginText: function(line, chars) {
        this.scimoz.marginSetText(line, chars);
    },
    
    _getMarginStyles: function(line) {
        try {
            var styles = {};
            this.scimoz.marginGetStyles(line, styles);
            styles = styles.value;
        } catch(e) {
            styles = "";
        }
        return styles.split("");
    },
    
    _setMarginStyles: function(line, styles) {
        styles = styles.join("");
        this.scimoz.marginSetStyles(line, styles);
    },

    refreshMarginProperies: function refreshMarginProperies() {
        this._initMarkerStyles(10); // maximum is 128
        this._initMargins();
    },

    updateMarkers_deleteAtLine: function(lineNo) {
        this.delMarkerSet(lineNo);
    },

    updateMarkers_insertByRange: function(lineStartNo, lineEndNo) {
        for (var lineNo = lineStartNo; lineNo < lineEndNo; lineNo++) {
            this.insMarkerSet(lineNo);
        }
    },

    updateMarkers_replaceByRange: function(lineStartNo, lineEndNo) {
        for (var lineNo = lineStartNo; lineNo < lineEndNo; lineNo++) {
            this.replaceMarkerSet(lineNo);
        }
    },
    
    _doUpdateMargins: function _doUpdateMargins(lastInsertions, deletedTextLines, lastNewChanges) {
        this.clearOldMarkers();
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
    
    updateMargins: function(lastInsertions, deletedTextLines, lastNewChanges) {
        this._doUpdateMargins(lastInsertions, deletedTextLines, lastNewChanges);
    },

    refreshMargins: function() {
        this._doUpdateMargins(this.lastInsertions, this.deletedTextLines, this.lastNewChanges);
    },
    
    clearOldMarkers: function() {
        // We can't use the held deletion/insertion lists because the line numbers
        // could have changed.
        const lim = this.scimoz.lineCount;
        const clearStyle = String.fromCharCode(this.clearStyleNum);
        for (let lineNo = 0; lineNo < lim; lineNo++) {
            if (this._getMarginText(lineNo).length != MARGIN_TEXT_LENGTH) {
                continue;
            }
            var styles = this._getMarginStyles(lineNo);
            styles[0] = clearStyle;
            this._setMarginStyles(lineNo, styles);
        }
    },
    
    __EOF__: null
};
  
/**
 * ChangeTrackerManager: singleton class responsible for creating
 * and deleting ChangeTracker objects, and associating each one
 * with a view.
 */

this.ChangeTrackerManager = function ChangeTrackerManager() {
};

this.ChangeTrackerManager.prototype.init = function() {
    this.onViewOpenedHandlerBound = this.onViewOpenedHandler.bind(this);
    this.onViewClosedHandlerBound = this.onViewClosedHandler.bind(this);
    this.onWindowClosingHandlerBound = this.onWindowClosingHandler.bind(this);
    this.onEditorTextModifiedBound = this.onEditorTextModified.bind(this);
    this.onEditorMarginClickedBound = this.onEditorMarginClicked.bind(this);
    this.onMarginGetTooltipTextBound = this.onMarginGetTooltipText.bind(this);
    window.addEventListener('editor_margin_get_tooltiptext', this.onMarginGetTooltipTextBound, true);
    window.addEventListener('editor_margin_clicked', this.onEditorMarginClickedBound, true);
    window.addEventListener("editor_text_modified", this.onEditorTextModifiedBound, false);
    window.addEventListener('view_document_attached', this.onViewOpenedHandlerBound, false);
    window.addEventListener('view_document_detaching', this.onViewClosedHandlerBound, false);
    window.addEventListener('unload', this.onWindowClosingHandlerBound, false);

    Services.obs.addObserver(this, "file_status", false);

    this._changeTrackerTimeoutId = null;
    // And because this method might have been called after documents
    // were loaded, we need to set up the changeTracker for each of them
    ko.views.manager.getAllViews('editor').forEach(function(view) {
            if (view.koDoc && view.koDoc.file
                && !('showChangesInMargin' in view)) {
                //log.debug(">> force an open view for " + view.koDoc.displayPath);
                this.onViewOpenedHandler({originalTarget: view});
            }
        }.bind(this));
};

this.ChangeTrackerManager.prototype.onWindowClosingHandler = function() {
    window.removeEventListener('editor_margin_get_tooltiptext', this.onMarginGetTooltipTextBound, false);
    window.removeEventListener('editor_margin_clicked', this.onEditorMarginClickedBound, false);
    window.removeEventListener('editor_text_modified', this.onEditorTextModifiedBound, false);
    window.removeEventListener('view_document_attached', this.onViewOpenedHandlerBound, false);
    window.removeEventListener('view_document_detaching', this.onViewClosedHandlerBound, false);
    window.removeEventListener('unload', this.onWindowClosingHandlerBound, false);

    Services.obs.removeObserver(this, "file_status");
};

this.ChangeTrackerManager.prototype.observe = function(subject, topic, data) {
    var urllist = data.split('\n');
    var view, views;
    for (var u=0; u < urllist.length; ++u) {
        views = ko.views.manager.topView.findViewsForURI(urllist[u]);
        for (var i=0; i < views.length; ++i) {
            view = views[i];
            if (view.koDoc && 'showChangesInMargin' in view) {
                view.koDoc.refreshChangedLines(view.showChangesInMargin);
            }
        }
    }
}

this.ChangeTrackerManager.prototype.onViewOpenedHandler = function(event) {
    var view = event.originalTarget;
    if (view.koDoc.file) {
        view.showChangesInMargin = view.prefs.getLongPref("showChangesInMargin");
        view.changeTrackerEnabled = view.showChangesInMargin > 0;
        view.changeTracker = new ko.changeTracker.ChangeTracker(view);
        view.showChangesInMargin = view.koDoc.prefs.getLongPref('showChangesInMargin');
        view.changeTrackerEnabled = view.showChangesInMargin > 0;
        view.changeTracker.setupTracker(view.changeTrackerEnabled);
        if (view.changeTrackerEnabled && view.changeTracker.showChangesOnFileLoad()) {
            if (ko.views.manager.batchMode) {
                // Let the SCC stuff get initialized at startup
                // Why do I have to wait 5 seconds?  I don't see
                // an event I can listen on for when a given file's
                // status is updated.
                setTimeout(function() {
                        this.startOnModifiedHandler(view);
                    }.bind(this), 5000);
            } else {
                this.startOnModifiedHandler(view);
            }
        }
        if (ko.views.manager.batchMode) {
            // Let the SCC stuff get initialized at startup
            // Why do I have to wait 5 seconds?  I don't see
            // an event I can listen on for when a given file's
            // status is updated.
            setTimeout(function() {
                this.startOnModifiedHandler(view);
            }.bind(this), 5000);
        } else {
            this.startOnModifiedHandler(view);
        }
    } else {
        view.showChangesInMargin = false;
        view.changeTrackerEnabled = false;
        view.changeTracker = null;
    }
};

this.ChangeTrackerManager.prototype.onViewClosedHandler = function(event) {
    var view = event.originalTarget;
    if (view.changeTracker) {
        view.changeTrackerEnabled = false;
        view.changeTracker.close();
        view.changeTracker = null;
    }
};

const AllowedModifications = (Components.interfaces.ISciMoz.SC_MOD_INSERTTEXT
                             |Components.interfaces.ISciMoz.SC_MOD_DELETETEXT);
this.ChangeTrackerManager.prototype.onEditorTextModified = function(event) {
    try {
        var data = event.data;
        var view = data.view;
        if ((data.modificationType & AllowedModifications) == 0) {
            return;
        }
        var changeTracker = view.changeTracker;
        if (!changeTracker || !changeTracker.showChangesInMargin) {
            //log.debug("Not interested in changes on " + view.koDoc.displayPath);
            return;
        }
        this.startOnModifiedHandler(view);
    } catch(ex) {
        log.exception(ex, "changeTracker error: onEditorTextModified");
    }
};

this.ChangeTrackerManager.prototype.onEditorMarginClicked = function(event) {
    try {
        if (event.detail.margin != MARGIN_CHANGEMARGIN) {
            return;
        }
        var view = event.detail.view;
        if (view.changeTracker && view.changeTrackerEnabled) {
            view.changeTracker.showChanges(event.detail.line);
            // Mark the event as handled.
            event.preventDefault();
        }
    } catch(ex) {
        log.exception(ex, "changeTracker error: onEditorMarginClicked");
    }
};

this.ChangeTrackerManager.prototype.onMarginGetTooltipText = function(event) {
    try {
        // Hovering over a change-margin?
        if (event.detail.margin == MARGIN_CHANGEMARGIN) {
            var view = event.detail.view;
            if (view.changeTracker) {
                let text = view.changeTracker.getTooltipText(event.detail.line);
                if (text) {
                    event.detail.text = text;
                    // Mark the event as handled.
                    event.preventDefault();
                }
            }
        }
    } catch(ex) {
        log.exception(ex, "changeTracker error: onMarginGetTooltipText");
    }
};

this.ChangeTrackerManager.prototype.startOnModifiedHandler = function(view) {
    if (this._changeTrackerTimeoutId !== null) {
        clearTimeout(this._changeTrackerTimeoutId);
    }
    this._changeTrackerTimeoutId = 
            setTimeout(function() {
                           this._handleOnModifiedForChangeTracker(view);
                       }.bind(this),
                       CHANGE_TRACKER_TIMEOUT_DELAY);
};

this.ChangeTrackerManager.prototype._handleOnModifiedForChangeTracker = function(view) { 
    try {
        this._changeTrackerTimeoutId = null;
        if (ko.views.manager.batchMode) {
            return;
        }
        view.koDoc.updateChangeTracker(view.changeTracker.showChangesInMargin);
    } catch(ex) {
        log.exception(ex, "_handleOnModifiedForChangeTracker failure");
    }
};


function changeTracker_onLoad(event) {
    try {
        ko.changeTrackerManager = new ko.changeTracker.ChangeTrackerManager();
        ko.changeTrackerManager.init();
    } catch(ex) {
        log.exception(ex, "problem in changeTracker_onLoad")
    }
}
window.addEventListener("komodo-ui-started", changeTracker_onLoad, false);

}).apply(ko.changeTracker);
