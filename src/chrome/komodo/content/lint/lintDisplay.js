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
this._segmenting_updates = false;

this.cancelPendingItems = function(lintBuffer) {
    if (this._segmenting_updates) {
        this._segmenting_updates = false;
        lintBuffer.view.removeEventListener("current_view_linecol_changed", lintBuffer.handleScroll, false);
        lintBuffer.view.removeEventListener("current_view_scroll_changed", lintBuffer.handleScroll, false);
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
    var startPos = 0;
    var styleLen = scimoz.length;
    if (scimoz.length == 0) {
        return;
    }

    // stash these for efficiency
    //var time1 = new Date();
    var firstLine = scimoz.lineFromPosition(startPos);
    var doclen = startPos + styleLen;
    var endLine = scimoz.lineFromPosition(doclen);

    var displayableResults = {};
    lintResults.getResultsInLineRange(firstLine + 1, endLine + 1, displayableResults, {});
    displayableResults = displayableResults.value;
    var lim = displayableResults.length;
    // optimization: if there aren't any lint results, clear the indicators and leave.
    //var time2 = new Date();
    //dump("lintDisplay.js display: time spent deciding: " + (time2 - time1) + "msec\n");
    if (lim === 0) {
        for each (var indicType in [DECORATOR_ERROR, DECORATOR_WARNING]) {
            scimoz.indicatorCurrent = indicType;
            scimoz.indicatorClearRange(startPos, doclen);
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
        lintBuffer.processedLines = [firstLine, endLine];
        this._segmenting_updates = true;
        view.addEventListener("current_view_linecol_changed", handleScroll, false);
        view.addEventListener("current_view_scroll_changed", handleScroll, false);
    } else {
        // No change
        this.updateDisplayedIndicators(scimoz, 0, scimoz.length, lintResults,
                                       displayableResults);
    }
};

this.updateDisplayedIndicators = function(scimoz, startPos, docLen,
                                          lintResults, displayableResults) {
    //var time1 = new Date();
    var offsetsAndValues = [];
    var r, newValue;
    var existingIndicators = [];
    for each (var indicType in [DECORATOR_ERROR, DECORATOR_WARNING]) {
        var pos = startPos;
        while (pos < docLen) {
            var iStart = scimoz.indicatorStart(indicType, pos);
            var iEnd = scimoz.indicatorEnd(indicType, pos);
            if (iEnd > iStart && scimoz.indicatorValueAt(indicType, iStart)) {
                existingIndicators.push([iStart, iEnd, indicType]);
            }
            if (iEnd <= pos) {
                break;
            }
            pos = iEnd;
        }
    }
    existingIndicators.sort(this._compareIndicators);
    var lim = displayableResults.length;
    for (var i = 0; i < lim; i++) {
        r = displayableResults[i];
        if (!r) continue;
        // sanity check lint results
        if ((r.columnStart >= 1 && r.columnEnd >= 1
             && r.lineStart >= 1 && r.lineEnd >= 1
             && (r.lineEnd > r.lineStart
                 || (r.lineEnd == r.lineStart
                     && r.columnEnd >= r.columnStart)))) {
                
            var linepos = scimoz.positionFromLine(r.lineStart - 1);
            var offsetStart = scimoz.positionAtChar(linepos, r.columnStart - 1);
            linepos = scimoz.positionFromLine(r.lineEnd - 1);
            var offsetEnd = scimoz.positionAtChar(linepos, r.columnEnd - 1);

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
        } else {
            log.error("Suspicious lint result discarded (sanity "
                      + "check failed): lineStart="
                      + r.lineStart
                      + ", columnStart="
                      + r.columnStart
                      + ", lineEnd="
                      + r.lineEnd
                      + ", columnEnd="
                      + r.columnEnd
                      + "\n");
        }
    }

    if (!offsetsAndValues.length && !existingIndicators.length) {
        return;
    }
    offsetsAndValues.sort(this._compareIndicators);
    offsetsAndValues = this._uniquify(offsetsAndValues);

    //var time2 = new Date();
    //dump("                                   calculating: " + (time2 - time1) + "msec\n");
    var prevEndStyled = scimoz.endStyled;
    var start, length, value;
    var indicIndex = 0;
    var indicLength = existingIndicators.length;
    var thisIndic;
    var finalNewIndicators = [];
    for each (var offsetAndValue in offsetsAndValues) {
        [start, length, value] = offsetAndValue;
        if (length > 0 && start + length < scimoz.length) { // one last sanity check, as if that's not true it can cause a lockup
            //log.debug("Draw squiggle:%d at pos[%d:%d], line %d:%d => %d:%d",
            //          value, start, start + length,
            //          scimoz.lineFromPosition(start),
            //          start - scimoz.positionFromLine(scimoz.lineFromPosition(start)),
            //          scimoz.lineFromPosition(start + length - 1),
            //          start + length - 1 - scimoz.positionFromLine(scimoz.lineFromPosition(start + length - 1)))
            
            // Look at the current indicator to decide what to do
            var drawIndicator = true;
            for (; indicIndex < indicLength; indicIndex++) {
                thisIndic = existingIndicators[indicIndex];
                if (thisIndic[0] == start
                    && thisIndic[1] == start + length
                    && thisIndic[2] == value) {
                    drawIndicator = false;
                    indicIndex++;
                    break;
                } else if (thisIndic[0] > start + length) {
                    // The current indicator will come later
                    break;
                } else {
                    // It's before or overlaps with the current one, so we need
                    // to clear it and redraw it
                    scimoz.indicatorCurrent = thisIndic[2];
                    scimoz.indicatorClearRange(thisIndic[0], thisIndic[1]);
                }
            }
            if (drawIndicator) {
                finalNewIndicators.push([start, length, value]);
            }
        }
    }
    // Clear any old indicators from last time
    for (; indicIndex < indicLength; indicIndex++) {
        thisIndic = existingIndicators[indicIndex];
        // It's before or overlaps with the current one, so we need
        // to clear it and redraw it
        scimoz.indicatorCurrent = thisIndic[2];
        scimoz.indicatorClearRange(thisIndic[0], thisIndic[1]);
    }
    for each (var finalNewIndicator in finalNewIndicators) {
        [start, length, value] = finalNewIndicator;
        scimoz.indicatorCurrent = value;
        scimoz.indicatorFillRange(start, length);
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
    var time1 = new Date();
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
    var displayableResults = {};
    lintResults.getResultsInLineRange(firstActualLine + 1, lastActualLine + 1, displayableResults, {});
    displayableResults = displayableResults.value;
    var time2 = new Date();
    //dump("                                regathering: " + (time2 - time1) + "msec\n");
    this.updateDisplayedIndicators(scimoz, firstActualPos, lastActualPos, lintResults, displayableResults);
};

}).apply(ko.lint.displayer);
