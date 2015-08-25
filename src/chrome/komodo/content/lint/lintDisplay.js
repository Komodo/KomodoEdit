/* Copyright (c) 2000-2011 ActiveState Software Inc.
 * See the file LICENSE.txt for licensing information.
 *
 */

/** lintDisplay.js -
 * Reimplement the lint displayer in JavaScript so we can use
 * setTimeout to delay painting indicators outside the current view.
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.lint)=='undefined') {
    ko.lint = {};
}
if (typeof(ko.lint.displayer)=='undefined') {
    ko.lint.displayer = {};
}

(function() {
var _log = ko.logging.getLogger("lint.displayer");
var log = _log;
_log.setLevel(ko.logging.LOG_INFO);

const DECORATOR_ERROR = Components.interfaces.koILintResult.DECORATOR_ERROR;
const DECORATOR_WARNING = Components.interfaces.koILintResult.DECORATOR_WARNING;
const ANNOTATION_ERROR = Components.interfaces.koILintResult.ANNOTATION_ERROR;
const ANNOTATION_WARNING = Components.interfaces.koILintResult.ANNOTATION_WARNING;
const SEV_ERROR = Components.interfaces.koILintResult.SEV_ERROR;

this._in_display = 0; // recursion protection.

this.cancelPendingItems = function(lintBuffer) {
    if (lintBuffer.handleScroll) {
        lintBuffer.view.removeEventListener("current_view_linecol_changed", lintBuffer.handleScroll, false);
        lintBuffer.view.removeEventListener("current_view_scroll_changed", lintBuffer.handleScroll, false);
        lintBuffer.handleScroll = null;
    }
};

this.displayClear = function(scimoz) {
    // Clear all lint results from this scimoz.
    this._in_display = 1;
    [DECORATOR_ERROR, DECORATOR_WARNING].forEach(function(val) {
            scimoz.indicatorCurrent = val;
            scimoz.indicatorClearRange(0, scimoz.length);
        });
    scimoz.annotationClearAll();
    this._in_display = 0;
};

this.continueDisplay = function(lintBuffer, lintResults) {
};

this.display = function(lintBuffer, lintResults) {
    var res = null;
    if (this._in_display) {
        return res;
    }
    this._in_display = 1;
    try {
        res = this._display(lintBuffer, lintResults);
    } finally {
        this._in_display = 0;
    }
    return res; // stupid js return requirement....
};

this._compareIndicators = function(a, b) {
    return a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
};

this._uniquify = function(a) {
    var newArray = [];
    var prevItem = [-1, -1, -1];
    var lim = a.length;
    for (var i = 0; i < lim; i++) {
        if (this._compareIndicators(prevItem, a[i])) {
            newArray.push(a[i]);
            prevItem = a[i];
        }
    }
    return newArray;
};

this._display = function(lintBuffer, lintResults) {
    if (!lintResults) {
        log.error("Should always have results to display");
        return;
    }
    var view = lintBuffer.view;
    var scimoz = view.scimoz;
    var doclen = scimoz.length;
    if (scimoz.length == 0) {
        return;
    }

    // stash these for efficiency
    //var time1 = new Date();
    var lim = lintResults.getNumResults();
    // optimization: if there aren't any lint results, clear the indicators and leave.
    //var time2 = new Date();
    //dump("lintDisplay.js display: time spent deciding: " + (time2 - time1) + "msec\n");
    if (lim === 0) {
        for each (var indicType in [DECORATOR_ERROR, DECORATOR_WARNING]) {
            scimoz.indicatorCurrent = indicType;
            scimoz.indicatorClearRange(0, doclen);
        }
        scimoz.annotationClearAll();
        return;
    } else if (lim > 50) {
        // Do only the indicators in the current view
        this.doConstrainedUpdate(scimoz, lintResults, lintBuffer);
        var this_ = this;
        var handleScroll = function(event) {
            // Bug 97965:
            // Sometimes when text has changed, the coordinates for the
            // current set of markers are now out-of-date.  The point of
            // this handler is to show the markers in other viewports,
            // since we create them on-demand.  But if the text changed,
            // the markers will sometimes be incorrect.  Better to just
            // let scintilla shove existing markers around than update
            // against an older set of markers.
            if (lintBuffer.recalculatingResults) {
                return;
            }
            this_.doConstrainedUpdate(scimoz, lintResults, lintBuffer);
        };
        lintBuffer.handleScroll = handleScroll;
        view.addEventListener("current_view_linecol_changed", handleScroll, false);
        view.addEventListener("current_view_scroll_changed", handleScroll, false);
    } else {
        // No change
        this.updateDisplayedIndicators(scimoz, 0, scimoz.length, lintResults);
    }
};

this.updateDisplayedIndicators = function(scimoz, startPos, docLen,
                                          lintResults) {
  //var time_start = performance.now();
  //try {
    //var time1 = new Date();
    for each (var indicType in [DECORATOR_ERROR, DECORATOR_WARNING]) {
        scimoz.indicatorCurrent = indicType;
        scimoz.indicatorClearRange(startPos, docLen);
    }
    scimoz.annotationClearAll();

    var startLine = scimoz.lineFromPosition(startPos);
    var endLine = scimoz.lineFromPosition(startPos + docLen);
    var displayableResults = {};
    lintResults.getResultsInLineRange(startLine + 1, endLine + 1, displayableResults, {});
    displayableResults = displayableResults.value;
    var lim = displayableResults.length;
    var offsetsAndValues = [];
    var r, newValue;

    var scimoz_length = scimoz.length;
    var scimoz_lineCount = scimoz.lineCount;

    for (var i = 0; i < lim; i++) {
        r = displayableResults[i];
        if (!r) continue;

        // sanity check lint results
        //if ((r.columnStart >= 1 && r.columnEnd >= 1
        //     && r.lineStart >= 1 && r.lineEnd >= 1
        //     && (r.lineEnd > r.lineStart
        //         || (r.lineEnd == r.lineStart
        //             && r.columnEnd >= r.columnStart)))) {

            // Convert linter line positions into scimoz doc positions.
            var lineStart = r.lineStart - 1;
            var linepos = scimoz.positionFromLine(lineStart);
            var indicStart = scimoz.positionAtChar(linepos, r.columnStart - 1);
            var lineEnd = r.lineEnd - 1;
            if (lineEnd > scimoz_lineCount) {
                if (lineStart > scimoz_lineCount) {
                    // It's on a line beyond the end of the document!?
                    continue;
                }
                lineEnd = scimoz_lineCount;
            }
            linepos = scimoz.positionFromLine(lineEnd);
            var indicEnd = scimoz.positionAtChar(linepos, r.columnEnd - 1);
            // Ensure offsetEnd does not extend beyond the end of the line. This
            // can happen if there are high-bit characters in a line of code
            // that has been flagged by a linter.
            indicEnd = Math.min(indicEnd, scimoz.getLineEndPosition(lineEnd));

            var indic = (r.severity == SEV_ERROR ? DECORATOR_ERROR : DECORATOR_WARNING);
            var indicLen = indicEnd - indicStart;
            if (indicLen <= 0) {
                // Ignore zero-length results.
                continue;
            }
            var style = (r.severity == SEV_ERROR ? ANNOTATION_ERROR : ANNOTATION_WARNING);
            offsetsAndValues.push([indicStart, indicLen, indic, lineEnd, style, r.description]);

        //} else {
        //    log.error("Suspicious lint result discarded (sanity "
        //              + "check failed): lineStart="
        //              + r.lineStart
        //              + ", columnStart="
        //              + r.columnStart
        //              + ", lineEnd="
        //              + r.lineEnd
        //              + ", columnEnd="
        //              + r.columnEnd
        //              + "\n");
        //}
    }

    if (!offsetsAndValues.length) {
        return;
    }
    offsetsAndValues.sort(this._compareIndicators);
    offsetsAndValues = this._uniquify(offsetsAndValues);

    //var time2 = new Date();
    //dump("                                   calculating: " + (time2 - time1) + "msec\n");
    var prevEndStyled = scimoz.endStyled;
    var start, length, value;
    var finalNewIndicators = [];
    for each (var offsetAndValue in offsetsAndValues) {
        [start, length, value, line, style, description] = offsetAndValue;
        //log.debug("Draw squiggle:%d at pos[%d:%d], line %d:%d => %d:%d",
        //          value, start, start + length,
        //          scimoz.lineFromPosition(start),
        //          start - scimoz.positionFromLine(scimoz.lineFromPosition(start)),
        //          scimoz.lineFromPosition(start + length - 1),
        //          start + length - 1 - scimoz.positionFromLine(scimoz.lineFromPosition(start + length - 1)))
        scimoz.indicatorCurrent = value;
        scimoz.indicatorFillRange(start, length);
        if (ko.prefs.getBoolean("lintShowResultsInline")) {
            scimoz.annotationSetText(line, description);
            scimoz.annotationSetStyle(line, style);
        }
    }
    //var time3 = new Date();
    //dump("                                       drawing: " + (time3 - time2) + "msec\n");
            
    if (prevEndStyled != scimoz.endStyled) {
        log.error("unexpected end styled prevEndStyled:"
                  + prevEndStyled
                  + "/ scimoz.endStyled:"
                  + scimoz.endStyled);
    }
  //} finally {
  //  dump("lint updateDisplayedIndicators took: " + (performance.now() - time_start) + " ms\n");
  //}
};

this.doConstrainedUpdate = function(scimoz, lintResults, lintBuffer) {
    //var time1 = new Date();
    var firstVisibleLine = scimoz.firstVisibleLine;
    var firstActualLine = scimoz.docLineFromVisible(firstVisibleLine);
    var firstActualPos = scimoz.positionFromLine(firstActualLine);
    var lastVisibleLine = firstVisibleLine + scimoz.linesOnScreen;
    var lastActualLine = scimoz.docLineFromVisible(lastVisibleLine);
    var lastActualPos;
    if (lastActualLine < scimoz.lineCount + 1) {
        lastActualPos = scimoz.positionFromLine(lastActualLine + 1);
    } else {
        lastActualPos = scimoz.length;
    }
    //var time2 = new Date();
    //dump("                                regathering: " + (time2 - time1) + "msec\n");
    this.updateDisplayedIndicators(scimoz, firstActualPos, lastActualPos - firstActualPos, lintResults);
};

}).apply(ko.lint.displayer);
