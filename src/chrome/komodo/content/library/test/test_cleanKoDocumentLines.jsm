const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "views", "macros", "mru", "history", "stringutils",
          "findresults", "statusbar",
          "chrome://komodo/content/library/tabstops.js");

let logging = Components.utils.import("chrome://komodo/content/library/logging.js", {}).logging;
//let log = logging.getLogger("jstest.TestCase");

function TestCleanKoDocumentLines() {
    this.log = null;
    this.log = logging.getLogger("clean.koDocument");
    //this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestCleanKoDocumentLines.prototype = new TestCase();

TestCleanKoDocumentLines.prototype.setUp = function TestCleanKoDocumentLines_setUp() {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    this.fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    this.docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
    this.globalPrefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
    this.encodingSvc = Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices);
    this.koIDocument = Ci.koIDocument;
    var this_ = this;
    this.origPrefs = {
      ensureFinalEOL: this_.globalPrefs.getBooleanPref("ensureFinalEOL"),
      cleanLineEnds: this_.globalPrefs.getBooleanPref("cleanLineEnds"),
      cleanLineEnds_CleanCurrentLine: this_.globalPrefs.getBooleanPref("cleanLineEnds_CleanCurrentLine"),
      cleanLineEnds_ChangedLinesOnly: this_.globalPrefs.getBooleanPref("cleanLineEnds_ChangedLinesOnly")
    };
};

TestCleanKoDocumentLines.prototype.setPrefsShortcut = function TestCleanKoDocumentLines_setPrefsShortcut(prefsObj) {
    for (var p in prefsObj) {
        this.globalPrefs.setBooleanPref(p, prefsObj[p]);
    }
};

TestCleanKoDocumentLines.prototype.tearDown = function TestCleanKoDocumentLines_tearDown() {
    var prefName;
    for (prefName in this.origPrefs) {
        this.globalPrefs.setBooleanPref(prefName, this.origPrefs[prefName]);
    }
};

TestCleanKoDocumentLines.prototype.msgHandler =
function TestCleanKoDocumentLines_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestCleanKoDocumentLines.prototype.sp = function sp(len) {
    var val = "";
    var padChar = " ";
    while (val.length < len) {
        val = "" + padChar + val;
    }
    return val;
};

TestCleanKoDocumentLines.prototype.test_passed = function test_passed() {
    this.assert(true, "passed tst failed");
};

TestCleanKoDocumentLines.prototype.test_clean_changed_lines_only_01 = function test_clean_changed_lines_only_01() {
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0, no space\n"
                  + "line 1, ends with 2 spaces  \n"
                  + "line 2, ends with 4 spaces    \n"
                  + "line 3, ends with no\n"
                  + "line 4, ends with 4 spaces    \n";
    var expectedLines = ["line 0, no space\n"
                  , "line 1, ends with 2 spaces\n"  // modified, stripped
                  , "line 2, ends with 4 spaces    \n"
                  , "line 3, ends with no\n"
                  , "line 4, ends with 4 spaces\n"]; // modified, stripped
    file.puts(origBuf);
    file.close();
    this._finish_clean_changed_lines_1(file, origBuf, expectedLines, this.koIDocument.EOL_LF);
};

TestCleanKoDocumentLines.prototype.test_clean_changed_lines_only_01_crlf = function test_clean_changed_lines_only_01_crlf() {
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0, no space\r\n"
                  + "line 1, ends with 2 spaces  \r\n"
                  + "line 2, ends with 4 spaces    \r\n"
                  + "line 3, ends with no\r\n"
                  + "line 4, ends with 4 spaces    \r\n";
    var expectedLines = ["line 0, no space\r\n"
                       , "line 1, ends with 2 spaces\r\n"  // modified, stripped
                       , "line 2, ends with 4 spaces    \r\n"
                       , "line 3, ends with no\r\n"
                       , "line 4, ends with 4 spaces\r\n"]; // modified, stripped
    file.puts(origBuf);
    file.close();
    this._finish_clean_changed_lines_1(file, origBuf, expectedLines, this.koIDocument.EOL_CRLF);
};

TestCleanKoDocumentLines.prototype.test_clean_changed_lines_only_01_unicode = function test_clean_changed_lines_only_01_unicode() {
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0, no space (¿ÀÑÜïŽ€๙)\n"
                  + "line 1, ends with 2 spaces (¿ÀÑÜïŽ€๙)  \n"
                  + "line 2, ends with 4 spaces (¿ÀÑÜïŽ€๙)    \n"
                  + "line 3, ends with no (¿ÀÑÜïŽ€๙)\n"
                  + "line 4, ends with 4 spaces (¿ÀÑÜïŽ€๙)    \n";
    var expectedLines = ["line 0, no space (¿ÀÑÜïŽ€๙)\n"
                       , "line 1, ends with 2 spaces (¿ÀÑÜïŽ€๙)\n"  // modified, stripped
                       , "line 2, ends with 4 spaces (¿ÀÑÜïŽ€๙)    \n"
                       , "line 3, ends with no (¿ÀÑÜïŽ€๙)\n"
                       , "line 4, ends with 4 spaces (¿ÀÑÜïŽ€๙)\n"]; // modified, stripped
    expectedLines = expectedLines.map(function(s) {
        return this.encodingSvc.encode(s, "utf-8", "")
    }, this);
    file.puts(origBuf);
    file.close();
    this._finish_clean_changed_lines_1(file, origBuf, expectedLines, this.koIDocument.EOL_LF);
};

TestCleanKoDocumentLines.prototype.test_clean_changed_lines_only_01_unicode_crlf = function test_clean_changed_lines_only_01_unicode_crlf() {
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0, no space (¿ÀÑÜïŽ€๙)\r\n"
                  + "line 1, ends with 2 spaces (¿ÀÑÜïŽ€๙)  \r\n"
                  + "line 2, ends with 4 spaces (¿ÀÑÜïŽ€๙)    \r\n"
                  + "line 3, ends with no (¿ÀÑÜïŽ€๙)\r\n"
                  + "line 4, ends with 4 spaces (¿ÀÑÜïŽ€๙)    \r\n";
    var expectedLines = ["line 0, no space (¿ÀÑÜïŽ€๙)\r\n"
                       , "line 1, ends with 2 spaces (¿ÀÑÜïŽ€๙)\r\n"  // modified, stripped
                       , "line 2, ends with 4 spaces (¿ÀÑÜïŽ€๙)    \r\n"
                       , "line 3, ends with no (¿ÀÑÜïŽ€๙)\r\n"
                       , "line 4, ends with 4 spaces (¿ÀÑÜïŽ€๙)\r\n"]; // modified, stripped
    expectedLines = expectedLines.map(function(s) {
        return this.encodingSvc.encode(s, "utf-8", "")
    }, this);
    file.puts(origBuf);
    file.close();
    this._finish_clean_changed_lines_1(file, origBuf, expectedLines, this.koIDocument.EOL_CRLF);
};

TestCleanKoDocumentLines.prototype._finish_clean_changed_lines_1 = function(file, origBuf, expectedLines, eolMode) {
    try {
        var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
        koDoc.new_line_endings = eolMode;
        // Set the buffer before assigning the view, otherwise it will fail.
        var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
        koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
        var view = new ko.views.ViewMock();
        view.koDoc = koDoc;
        koDoc.addView(view.scintilla);
        var scimoz = view.scimoz;
        
        koDoc.save(1); // Ensure original buffer content is sane - for Windows.
        //this.assertEqual(view.scintilla, koDoc.getView());
        
        // Now allow for the modifications we'll do.
        // Line 0: no change
        // Line 1: add 2 spaces to end
        // Line 2: no change
        // Line 3: add 4 spaces to end
        // Line 4: delete 1 space from end

        // Modify the lines
        var scimoz = view.scimoz;

        scimoz.currentPos = scimoz.getLineEndPosition(1);
        scimoz.addText(2, this.sp(2));
        scimoz.currentPos = scimoz.getLineEndPosition(3);
        scimoz.addText(4, this.sp(4));
        scimoz.targetEnd = scimoz.getLineEndPosition(4);
        scimoz.targetStart = scimoz.targetEnd - 1;
        scimoz.replaceTarget(0, "");

        this.setPrefsShortcut({
              cleanLineEnds: 1,
              cleanLineEnds_CleanCurrentLine: 1,
              cleanLineEnds_ChangedLinesOnly: 1});
        this._saveCheckLines(koDoc, scimoz, expectedLines);
    } finally {
        file = this.fileSvc.deleteTempFile(file.path, true);
    }
};

TestCleanKoDocumentLines.prototype.test_clean_all_lines_02 = function test_clean_all_lines_02() {
    var file = this.fileSvc.makeTempFile(".txt", 'w');
    // This time make sure all blank lines are trimmed, not just changed ones.
    try {
        var origLines = ["line 0, no space\n"
                       , "line 1, ends with 2 spaces  \n"
                       , "line 2, ends with 4 spaces    \n"];
        var origBuf = origLines.join("");
        file.puts(origBuf);
        file.close();
        var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
        koDoc.new_line_endings = koDoc.EOL_LF;
        // Set the buffer before assigning the view, otherwise it will fail.
        koDoc.setBufferAndEncoding(origBuf, "utf-8");
        var view = new ko.views.ViewMock({text: origBuf});
        view.koDoc = koDoc;
        koDoc.addView(view.scintilla);
        //koDoc.save(1);
        //this.assertEqual(view.scintilla, koDoc.getView());
        var expectedLines = origLines.map(function(s) s.replace(/[ \t]*(?=\r?\n|$)/, ''));
        // All lines should be trimmed this time.

        // Modify the lines
        var scimoz = view.scimoz;
        scimoz.currentPos = scimoz.getLineEndPosition(1);
        scimoz.addText(1, this.sp(1));
        //scimoz.targetEnd = scimoz.getLineEndPosition(2);
        //scimoz.targetStart = scimoz.targetEnd - 1;
        scimoz.replaceTarget(0, "");

        this.setPrefsShortcut({
              cleanLineEnds: 1,
              cleanLineEnds_CleanCurrentLine: 1,
              cleanLineEnds_ChangedLinesOnly: false});
        this._saveCheckLines(koDoc, scimoz, expectedLines);
    } finally {
        file = this.fileSvc.deleteTempFile(file.path, true);
    }
};

TestCleanKoDocumentLines.prototype.splitlines = function splitlines(s) {
    var lines = s.split(/(\r?\n)/).reduce(function(prev, curr, index, array) {
        if (index % 2 === 1) {
            prev[prev.length - 1] += curr;
        } else {
            prev.push(curr);
        }
        return prev;
    }, []);
    if (lines.length > 0 & lines[lines.length - 1].length == 0) {
        lines.splice(lines.length - 1, 1);
    }
    return lines;
}

TestCleanKoDocumentLines.prototype.test_clean_no_lines_03 = function test_clean_all_lines_03() {
    var file = this.fileSvc.makeTempFile(".txt", 'w');
    // This time don't trim any lines.
    try {
        var origBuf = ("line 0, no space\n"
                       + "line 1, ends with 2 spaces  \n"
                       + "line 2, ends with 4 spaces    \n");
        file.puts(origBuf);
        file.close();
        var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
        // Set the buffer before assigning the view, otherwise it will fail.
        koDoc.setBufferAndEncoding(origBuf, "utf-8");
        var view = new ko.views.ViewMock({text: origBuf});
        view.koDoc = koDoc;
        koDoc.addView(view.scintilla);
        var expectedLines = this.splitlines(origBuf);

        // Modify the lines
        var scimoz = view.scimoz;
        scimoz.currentPos = scimoz.getLineEndPosition(1);
        scimoz.addText(1, this.sp(1));
        scimoz.targetEnd = scimoz.getLineEndPosition(2);
        scimoz.targetStart = scimoz.targetEnd - 1;
        scimoz.replaceTarget(0, "");
        expectedLines[1] = expectedLines[1].replace(/\n/, " \n");
        expectedLines[2] = expectedLines[2].replace(/ \n/, "\n");

        this.setPrefsShortcut({
              cleanLineEnds: false,
                    cleanLineEnds_CleanCurrentLine: 1,
                    cleanLineEnds_ChangedLinesOnly: 1});
        this._saveCheckLines(koDoc, scimoz, expectedLines);
    } finally {
        //file = this.fileSvc.deleteTempFile(file.path, true);
    }
};

function visString(s) {
    return s.split("").map(function(c) {
        var num = c.charCodeAt(0);
        if (num > 127 || num < 32) {
            return  "(" + c.charCodeAt(0) + ")";
        }
        return c;
    }).join("");
}

TestCleanKoDocumentLines.prototype._saveCheckLines = function _saveCheckLines(koDoc, scimoz, expectedLines) {
    koDoc.save(true);
    var postSaveLines = scimoz.text.split(/(\r?\n)/);
    postSaveLines = postSaveLines.reduce(function(prev, curr, index, array) {
        if (index % 2 === 1) {
            prev[prev.length - 1] += curr;
        } else {
            prev.push(curr);
        }
        return prev;
    }, []);
    if (!postSaveLines[postSaveLines.length - 1].length) {
        postSaveLines.splice(postSaveLines.length - 1, 1);
    }
    this.assertEquals(expectedLines.length, postSaveLines.length,
                      ("Expected "
                       + expectedLines.length
                       + " lines, got "
                       + postSaveLines.length));
    for (var i = 0; i < postSaveLines.length; i++) {
        // Can't use this.assertEquals due to non-ascii chars in the lines
        if (expectedLines[i] != postSaveLines[i]) {
            this.assertFalse("String mismatch at line "
                        + i
                        + ", expected <"
                        + visString(expectedLines[i])
                        + ">, got <"
                        + visString(postSaveLines[i])
                        + ">\n");
        }
    }
};

TestCleanKoDocumentLines.prototype._finish_clean_changed_lines_2 = function(file, origBuf, expectedLines, eolMode) {
    try {
        // Write '6' to the current position,  save, and compare
        var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
        koDoc.new_line_endings = eolMode;
        // Set the buffer before assigning the view, otherwise it will fail.
        var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
        koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
        var view = new ko.views.ViewMock();
        view.koDoc = koDoc;
        koDoc.addView(view.scintilla);
        var scimoz = view.scimoz;

        koDoc.save(1); // Ensure original buffer content is sane - for Windows.
        //this.assertEqual(view.scintilla, koDoc.getView());

        // Now allow for the modifications we'll do.
        // Line 0: no change
        // Line 1: add 2 spaces to end
        // Line 2: no change
        // Line 3: add 4 spaces to end
        // Line 4: delete 1 space from end

        // Modify the lines
        var scimoz = view.scimoz;

        scimoz.currentPos = scimoz.getLineEndPosition(1);
        scimoz.addText(2, this.sp(2));
        scimoz.currentPos = scimoz.getLineEndPosition(3);
        scimoz.addText(4, this.sp(4));
        scimoz.targetEnd = scimoz.getLineEndPosition(4);
        scimoz.targetStart = scimoz.targetEnd - 1;
        scimoz.replaceTarget(0, "");

        this.setPrefsShortcut({
              cleanLineEnds: 1,
              cleanLineEnds_CleanCurrentLine: 1,
              cleanLineEnds_ChangedLinesOnly: 1});
        this._saveCheckLines(koDoc, scimoz, expectedLines);
    } finally {
        file = this.fileSvc.deleteTempFile(file.path, true);
    }
};


TestCleanKoDocumentLines.prototype.test_bug100967_a = function test_bug100967_a() {
// Bug 100967: removes too much when a file doesn't end with a EOL
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0\n"
                  + "line 1\n"
                  + "\n"
                  + "line 3\n"
                  + "\n"
                  + "line 5\n"
                  + "line 6";
    var expectedBuf = ["line 0"
                       , "line 1"
                       , ""
                       , "line 3"
                       , ""
                       , "line 5"
                       , "line 66"].join("\n");
    file.puts(origBuf);
    file.close();
    let eolMode = this.koIDocument.EOL_LF;
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = eolMode;
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    var view = new ko.views.ViewMock();
    view.koDoc = koDoc;
    koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    scimoz.currentPos = scimoz.length;
    scimoz.addText(1, "6");
    let oldPos = scimoz.currentPos;
    scimoz.currentPos = scimoz.positionFromLine(3);
    this.assertEquals(scimoz.anchor, oldPos);
    this.assertEquals(scimoz.selectionEnd, oldPos);
    scimoz.anchor = scimoz.currentPos;
    this.setPrefsShortcut({
              cleanLineEnds: 1,
              cleanLineEnds_CleanCurrentLine: 0,
              cleanLineEnds_ChangedLinesOnly: 0,
              ensureFinalEOL: false
              });
    koDoc.save(true);
    this.assertEquals(expectedBuf, scimoz.text,
                      (" Expected <<" + expectedBuf + ">>, got\n<<"
                       + scimoz.text + ">>"));
};

TestCleanKoDocumentLines.prototype.test_bug100967_b = function test_bug100967_b() {
// Bug 100967: removes too much when a file doesn't end with a EOL
// Similar to previous case, but modify an earlier line.
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0\n"
                  + "line 1\n"
                  + "\n"
                  + "line 3\n"
                  + "\n"
                  + "line 5\n"
                  + "line 6";
    var expectedBuf = ["line 0"
                       , "line 1"
                       , ""
                       , "xline 3"
                       , ""
                       , "line 5"
                       , "line 6"].join("\n");
    file.puts(origBuf);
    file.close();
    let eolMode = this.koIDocument.EOL_LF;
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = eolMode;
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    var view = new ko.views.ViewMock();
    view.koDoc = koDoc;
    koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    scimoz.currentPos = scimoz.positionFromLine(3);
    var newStr = "x";
    scimoz.addText(newStr.length, newStr);
    scimoz.currentPos = scimoz.positionFromLine(3);
    this.setPrefsShortcut({
              cleanLineEnds: 1,
              cleanLineEnds_CleanCurrentLine: 0,
              cleanLineEnds_ChangedLinesOnly: 0,
              ensureFinalEOL: false
              });
    koDoc.save(true);
    this.assertEquals(expectedBuf, scimoz.text,
                      (" Expected <<" + expectedBuf + ">>, got\n<<"
                       + scimoz.text + ">>"));
};

TestCleanKoDocumentLines.prototype.test_ok_clean_obv_ws = function test_ok_clean_obv_ws() {
// A case where we don't see Bug 100967:
// All the whitespace added after the line starting with "line 6" is handled
// correctly.
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0\n"
                  + "line 1\n"
                  + "\n"
                  + "line 3\n"
                  + "\n"
                  + "line 5\n"
                  + "line 6";
    var expectedBuf = ["line 0"
                       , "line 1"
                       , ""
                       , "line 3"
                       , ""
                       , "line 5"
                       , "line 66\n"].join("\n");
    file.puts(origBuf);
    file.close();
    let eolMode = this.koIDocument.EOL_LF;
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = eolMode;
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    var view = new ko.views.ViewMock();
    view.koDoc = koDoc;
    koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    scimoz.currentPos = scimoz.length;
    var newStr = "6\n \n  \n   \n    \n";
    scimoz.addText(newStr.length, newStr);
    scimoz.currentPos = scimoz.positionFromLine(3);
    this.setPrefsShortcut({
              cleanLineEnds: 1,
              cleanLineEnds_CleanCurrentLine: 1,
              cleanLineEnds_ChangedLinesOnly: 0,
              ensureFinalEOL: false
              });
    koDoc.save(true);
    this.assertEquals(expectedBuf, scimoz.text,
                      (" Expected <<" + expectedBuf + ">>, got\n<<"
                       + scimoz.text + ">>"));
};

TestCleanKoDocumentLines.prototype.test_headless_anchor_cp = function test_headless_anchor_cp() {
// Bug 100967: removes too much when a file doesn't end with a EOL
// Similar to previous case, but modify an earlier line.
    var file = this.fileSvc.makeTempFile(".txt", 'wb');
    var origBuf   = "line 0\n"
                  + "line 1";
    file.puts(origBuf);
    file.close();
    let eolMode = this.koIDocument.EOL_LF;
    var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = eolMode;
    // Set the buffer before assigning the view, otherwise it will fail.
    var origBugUTF = this.encodingSvc.encode(origBuf, "utf-8", "")
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    var view = new ko.views.ViewMock();
    view.koDoc = koDoc;
    koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    scimoz.currentPos = scimoz.length;
    scimoz.addText(1, "6");
    this.assertEquals("line 0\nline 16", scimoz.text);
    this.assertEquals(origBuf.length + 1, scimoz.currentPos);
    this.assertEquals(origBuf.length + 1, scimoz.anchor);
}

var JS_TESTS = ["TestCleanKoDocumentLines"];
