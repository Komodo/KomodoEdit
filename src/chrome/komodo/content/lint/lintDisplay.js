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
        return;
    } else if (lim > 50) {
        // Do only the indicators in the current view
        this.doConstrainedUpdate(scimoz, lintResults, lintBuffer);
        var this_ = this;
        var handleScroll = function(event) {
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
    //var time1 = new Date();
    for each (var indicType in [DECORATOR_ERROR, DECORATOR_WARNING]) {
        scimoz.indicatorCurrent = indicType;
        scimoz.indicatorClearRange(startPos, docLen);
    }

    var startLine = scimoz.lineFromPosition(startPos);
    var endLine = scimoz.lineFromPosition(startPos + docLen);
    var displayableResults = {};
    lintResults.getResultsInLineRange(startLine + 1, endLine + 1, displayableResults, {});
    displayableResults = displayableResults.value;
    var lim = displayableResults.length;
    var offsetsAndValues = [];
    var r, newValue;

    for (var i = 0; i < lim; i++) {
        r = displayableResults[i];
        if (!r) continue;
        // sanity check lint results
        //if ((r.columnStart >= 1 && r.columnEnd >= 1
        //     && r.lineStart >= 1 && r.lineEnd >= 1
        //     && (r.lineEnd > r.lineStart
        //         || (r.lineEnd == r.lineStart
        //             && r.columnEnd >= r.columnStart)))) {

            var linepos = scimoz.positionFromLine(r.lineStart - 1);
            var offsetStart = scimoz.positionAtChar(linepos, r.columnStart - 1);
            linepos = scimoz.positionFromLine(r.lineEnd - 1);
            var offsetEnd = scimoz.positionAtChar(linepos, r.columnEnd - 1);
            if (offsetEnd > scimoz.getLineEndPosition(r.lineEnd - 1)) {
                // This can happen when there are high-bit characters in a line
                // of code that a linter has flagged.
                offsetEnd = scimoz.getLineEndPosition(r.lineEnd - 1);
            }

            if (offsetEnd <= scimoz.length && offsetEnd >= offsetStart) {
                if (r.lineEnd > scimoz.lineCount) {
                    offsetEnd = scimoz.length;
                }
                newValue = (r.severity == r.SEV_ERROR
                            ? DECORATOR_ERROR
                            : DECORATOR_WARNING);
                offsetsAndValues.push([offsetStart, offsetEnd - offsetStart,
                                       newValue]);
            } else {
                log.error("Suspicious lint result discarded (offsetEnd "
                          + "> scimoz.length || offsetStart > offsetEnd): "
                          + "lineStart="
                          + r.lineStart
                          + ", columnStart="
                          + r.columnStart
                          + ", lineEnd="
                          + r.lineEnd
                          + ", columnEnd="
                          + r.columnEnd
                          + "\n");
            }
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
    var currentLine = scimoz.lineFromPosition(scimoz.currentPos);
    var lastLine = scimoz.lineCount - 1;
    var onLastLine = currentLine == lastLine;
    for each (var offsetAndValue in offsetsAndValues) {
        [start, length, value] = offsetAndValue;
        if (length > 0) {
            if (start + length > scimoz.length) { // one last sanity check, as if that's not true it can cause a lockup
                length = scimoz.length - start;
            }
            if (onLastLine
                && scimoz.lineFromPosition(start) == lastLine) {
                continue;
            }
            //log.debug("Draw squiggle:%d at pos[%d:%d], line %d:%d => %d:%d",
            //          value, start, start + length,
            //          scimoz.lineFromPosition(start),
            //          start - scimoz.positionFromLine(scimoz.lineFromPosition(start)),
            //          scimoz.lineFromPosition(start + length - 1),
            //          start + length - 1 - scimoz.positionFromLine(scimoz.lineFromPosition(start + length - 1)))
            scimoz.indicatorCurrent = value;
            scimoz.indicatorFillRange(start, length);
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
