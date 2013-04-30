/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/*
 * The Komodo version of EJS.js also puts EJS in the ko.snippets namespace
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.snippets)=='undefined') {
    ko.snippets = {};
}
(function() {
    this.invokedExplicitly = true;
    // Throw one of these objects in any EJS snippet if the snippet
    // should be rejected, as in
    // <% throw new ko.snippets.RejectedSnippet() %>
    this.RejectedSnippet = function ko_snippet_RejectedSnippet(message, ex) {
        if (!ex) {
            ex = new Error();
        }
        this.fileName = ex.fileName;
        this.lineNumber = ex.lineNumber;
        this.stack = ex.stack;
        this.name = "ko.snippets.RejectedSnippet";
        this.message = message;
    };
    this.RejectedSnippet.prototype.toString = function() {
        return ("Exception: [" + this.message + "\n"
                + "name: " + this.name + "\n"
                + "fileName: " + this.fileName + "\n"
                + "lineNumber: " + this.lineNumber + "\n"
                + "stack: " + this.stack + "]\n");
    };

    this.getTextLine = function ko_snippet_getTextLine(scimoz, currentLine) {
        if (typeof(scimoz) == "undefined") {
            scimoz = ko.views.manager.currentView.scimoz;
        }
        if (typeof(currentLine) == "undefined") {
            currentLine = scimoz.lineFromPosition(scimoz.currentPos);
        }
        var startPos = scimoz.positionFromLine(currentLine);
        var endPos = scimoz.getLineEndPosition(currentLine);
        return scimoz.getTextRange(startPos, endPos);
    };

    this._leadingKeywordRE = /(?:^|[;=])\s*\w+$/;
    this._leadingKeywordRE_invokedExplicitly = /(?:^|[;=])\s*$/;
    this.rightOfFirstKeyword =  function ko_snippet_rightOfFirstKeyword() {
        var text = this.getTextLine();
        return (this.invokedExplicitly
                ? this._leadingKeywordRE_invokedExplicitly
                : this._leadingKeywordRE).test(text);
    };
    this.verifyAtRightOfFirstKeyword = function ko_snippet_verifyAtRightOfFirstKeyword() {
        if (!this.rightOfFirstKeyword()) {
            throw new ko.snippets.RejectedSnippet("not at start of line");
        }
    };
    // Bug 98056: these checks are for Perl, not just Ruby, so use a
    // more generic name, but support the old name for compatibility.
    this.rightOfFirstRubyKeyword = this.rightOfFirstKeyword;
    this.verifyAtRightOfFirstRubyKeyword = this.verifyAtRightOfFirstKeyword;

    this.inPythonClass =  function ko_snippet_inPythonClass() {
        // Move up, looking for a line that starts with 'class', but not 'def'
        var view = ko.views.manager.currentView;
        var scimoz = view.scimoz;
        var currentPos = scimoz.currentPos;
        var currentLine = scimoz.lineFromPosition(currentPos);
        var text = this.getTextLine(scimoz, currentLine);
        var getIndentLen = function(s) {
            return s.replace(/\t/g, "    ").length;
        };
        var m;
        var indentPtn = /^([ \t]*)(.*)/;
        var currIndentLen = getIndentLen(indentPtn.exec(text)[1]);
        if (currIndentLen === 0) {
            return false;
        }
        var thisIndentLen;
        while (--currentLine >= 0) {
            text = this.getTextLine(scimoz, currentLine);
            m = indentPtn.exec(text);
            thisIndentLen = getIndentLen(m[1]);
            if (thisIndentLen < currIndentLen) {
                var style = scimoz.getStyleAt(scimoz.positionFromLine(currentLine));
                if (!m[2] || m[2][0] == '#' || style == scimoz.SCE_P_TRIPLE || style == scimoz.SCE_P_TRIPLEDOUBLE) {
                    continue;
                } else if (/^class\b/.test(m[2])) {
                    if (style == scimoz.SCE_P_DEFAULT
                        || style == scimoz.SCE_P_WORD) {
                        return true;
                    }
                } else {
                    return false;
                }
            }
        }
        return false;
    };

    this.snippetPathShortName = function(snippet) {
        var pieces = [snippet.name];
        var parent = snippet;
        var name;
        while (parent.parent) {
            parent = parent.parent;
            name = parent.name;
            pieces.push(name);
            if (name == "Abbreviations") {
                break;
            }
        }
        pieces.reverse();
        return pieces.join("/");
    };
    
    this.consumeLeadingNumericFactor = function(delimiter) {
        if (typeof(delimiter) == "undefined") delimiter = ":";
        try {
            var currentView = ko.views.manager.currentView;
            var scimoz = currentView.scimoz;
            var numReps = 0;
            var anchor = scimoz.anchor;
            var currentPos = scimoz.currentPos;
            if (anchor < currentPos) {
                [currentPos, anchor] = [anchor, currentPos];
            }
            currentPos = scimoz.positionBefore(currentPos);
            var p = scimoz.getWCharAt(currentPos);
            var prevPos;
            if (p === delimiter) {
                var numStartPos, numEndPos;
                numStartPos = numEndPos = currentPos;
                while (numStartPos > 0) {
                    prevPos = scimoz.positionBefore(numStartPos);
                    if (prevPos < 0) break;
                    if (!/\d/.test(scimoz.getWCharAt(prevPos))) break;
                    numStartPos = prevPos;
                    //dump("numStartPos now: " + numStartPos + "\n");
                }
                if (numStartPos < numEndPos) {
                    numReps = parseInt(scimoz.getTextRange(numStartPos, numEndPos));
                    var targetStart = scimoz.targetStart, targetEnd = scimoz.targetEnd;
                    scimoz.targetStart = numStartPos;
                    scimoz.targetEnd = scimoz.positionAfter(currentPos);
                    scimoz.replaceTarget(0, "");
                    scimoz.targetStart = targetStart;
                    scimoz.targetEnd = targetEnd;
                }
            }
        } catch(e) {
            dump("ko.snippets.consumeLeadingNumericFactor exception: " + e + "\n");
            throw e;
        }
        return numReps;
    };

    this.HTML_checkIsLessThanPresent = function () {
        // In abbrev.js, ko.abbrev._checkOpenTag verifies that if we're
        // in an HTML/XML document, the char to the left of the
        // cursor is either plain-text (SCE_UDL_M_DEFAULT),
        // or that it's SCE_UDL_M_TAGNAME preceded by a "<"
        var scimoz = ko.views.manager.currentView.scimoz;
        var lastPos = scimoz.positionBefore(scimoz.selectionEnd);
        return scimoz.getStyleAt(lastPos) === scimoz.SCE_UDL_M_TAGNAME;
    };

    this.HTML_emitLessThanIfNeeded = function () {
        return this.HTML_checkIsLessThanPresent() ? "" : "<";
    };

}).apply(ko.snippets);
