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
}
TestCleanKoDocumentLines.prototype = new TestCase();

TestCleanKoDocumentLines.prototype.setUp = function TestCleanKoDocumentLines_setUp() {
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    this.scope = { ko: ko, __noSuchMethod__: function() {}};
    this.fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
    this.docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
    this.globalPrefs = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService).prefs;
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
    var file = this.fileSvc.makeTempFile(".txt", 'w');
    try {
        ("file's path: " + file.path + "\n");
        var origBuf   = "line 0, no space\n"
                      + "line 1, ends with 2 spaces  \n"
                      + "line 2, ends with 4 spaces    \n"
                      + "line 3, ends with no\n"
                      + "line 4, ends with 4 spaces    \n";
        var resultBuf = "line 0, no space\n"
                      + "line 1, ends with 2 spaces\n"  // modified, stripped
                      + "line 2, ends with 4 spaces    \n"
                      + "line 3, ends with no\n"
                      + "line 4, ends with 4 spaces\n"; // modified, stripped
        file.puts(origBuf);
        file.close();
        var koDoc = this.docSvc.createNewDocumentFromURI(file.URI);
        // Set the buffer before assigning the view, otherwise it will fail.
        koDoc.setBufferAndEncoding(origBuf, "utf-8");
        var view = new ko.views.ViewMock();
        view.koDoc = koDoc;
        koDoc.addView(view.scintilla);
        //koDoc.save(1);
        //this.assertEqual(view.scintilla, koDoc.getView());
        var expectedLines = resultBuf.split(/\r?\n/);
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
        //koDoc.save(1);
        //this.assertEqual(view.scintilla, koDoc.getView());
        var expectedLines = origBuf.split(/\r?\n/).map(function(s) s.replace(/\s*$/, ''));
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

TestCleanKoDocumentLines.prototype.test_clean_no_lines_03 = function test_clean_all_lines_02() {
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
        var expectedLines = origBuf.split(/\r?\n/);

        // Modify the lines
        var scimoz = view.scimoz;
        scimoz.currentPos = scimoz.getLineEndPosition(1);
        scimoz.addText(1, this.sp(1));
        expectedLines[1] += " ";
        scimoz.targetEnd = scimoz.getLineEndPosition(2);
        scimoz.targetStart = scimoz.targetEnd - 1;
        expectedLines[2] = expectedLines[2].substr(0, expectedLines[2].length - 1);
        scimoz.replaceTarget(0, "");

        this.setPrefsShortcut({
              cleanLineEnds: false,
                    cleanLineEnds_CleanCurrentLine: 1,
                    cleanLineEnds_ChangedLinesOnly: 1});
        this._saveCheckLines(koDoc, scimoz, expectedLines);
    } finally {
        //file = this.fileSvc.deleteTempFile(file.path, true);
    }
};

TestCleanKoDocumentLines.prototype._saveCheckLines = function _saveCheckLines(koDoc, scimoz, expectedLines) {
    koDoc.save(true);

    var postSaveLines = scimoz.text.split(/\r?\n/);
    this.assertEquals(expectedLines.length, postSaveLines.length,
                      ("Expected "
                       + expectedLines.length
                       + " lines, got "
                       + postSaveLines.length));
    for (var i = 0; i < postSaveLines.length; i++) {
        this.assertEquals(expectedLines[i], postSaveLines[i],
                          ("String mismatch at line "
                           + i
                           + ", expected <"
                           + expectedLines[i]
                           + ">, got <"
                           + postSaveLines[i]
                           + ">"));
    }
};


var JS_TESTS = ["TestCleanKoDocumentLines"];
