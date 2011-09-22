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

this._getIndicMask = function(scimoz) {
    if (scimoz.styleBits < 6) {
        return scimoz.INDICS_MASK;
    } else if (scimoz.styleBits == 6) {
        return scimoz.INDIC1_MASK | scimoz.INDIC2_MASK;
    } else {
        return scimoz.INDIC2_MASK;
    }
};

this.displayClear = function(scimoz) {
    // Clear all lint results from this scimoztilla.
    var mask = this._getIndicMask(scimoz);
    this._in_display = 1;
    [DECORATOR_ERROR, DECORATOR_WARNING].forEach(function(val) {
            scimoz.indicatorCurrent = val;
            scimoz.indicatorClearRange(0, scimoz.length);
        });
    this._in_display = 0;
};
    
this.display = function(scimoz, lintResults, numBits, startPos, styleLen) {
    // numBits no longer used, but part of xpcom interface.
    var res = null;
    if (this._in_display) {
        return res;
    }
    this._in_display = 1;
    try {
        res = this._display(scimoz, lintResults, startPos, styleLen);
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

this._display = function(scimoz, lintResults, startPos, styleLen) {
    if (!lintResults) {
        log.error("Should always have results to display");
        return;
    }
    if (scimoz.length == 0) {
        return;
    }

    // stash these for efficiency
    var firstLine = scimoz.lineFromPosition(startPos);
    var endLine = scimoz.lineFromPosition(startPos + styleLen);

    var displayableResults = {};
    lintResults.getResultsInLineRange(firstLine + 1, endLine + 1, displayableResults, {});
    displayableResults = displayableResults.value;
    var offsetsAndValues = [];
    var r, lim = displayableResults.length, newValue;
    var existingIndicators = [];
    var doclen = startPos + styleLen;
    for each (var indicType in [DECORATOR_ERROR, DECORATOR_WARNING]) {
            var pos = startPos;
            while (pos < doclen) {
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
            
    if (prevEndStyled != scimoz.endStyled) {
        log.error("unexpected end styled prevEndStyled:"
                  + prevEndStyled
                  + "/ scimoz.endStyled:"
                  + scimoz.endStyled);
    }
};

}).apply(ko.lint.displayer);
