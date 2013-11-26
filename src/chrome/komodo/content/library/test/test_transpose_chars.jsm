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

var TestTransposeChars = function TestTransposeChars() {
    this.log = null;
    this.log = logging.getLogger("lint.transposeChars");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestTransposeChars.prototype = new TestCase();

koIDocument = Ci.koIDocument;

TestTransposeChars.prototype.setUp = function TestTransposeChars_setUp() {
};

TestTransposeChars.prototype.tearDown = function TestTransposeChars_tearDown() {
};


TestTransposeChars.prototype.msgHandler =
function TestTransposeChars_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestTransposeChars.prototype._setupScimoz = function(buf) {
    var view = new ko.views.ViewMock({text:buf});
    var scimoz = view.scimoz;
    this.assertIn('@activestate.com/ISciMozHeadless;1', Cc,
                  "Headless SciMoz is required");
    var controller = Cc['@ActiveState.com/scintilla/controller;1'].
                        createInstance(Ci.ISciMozController);
    controller.init( scimoz );
    return [scimoz, view, controller];
};

TestTransposeChars.prototype._runTheTest = function(origBufLines, origPosFunc,
                                                    expectedBufLines, expectedPosFunc ) {
    var eol, eolType;
    var map = {
        "\r\n": koIDocument.EOL_CRLF,
        "\n": koIDocument.EOL_LF,
        "\r": koIDocument.EOL_CR
    };
    for ([eol, eolType] in Iterator(map)) {
        //this.log.debug("eol first char: " + eol.charCodeAt(0));
        //this.log.debug("eolType: " + eolType);
        
        let bufText = origBufLines.join(eol);
        let scimoz, view, controller;
        [scimoz, view, controller] = this._setupScimoz(bufText);
        view.koDoc.new_line_endings = eolType;
        if (typeof(origPosFunc) === "function") {
            origPos = origPosFunc(scimoz);
        } else {
            origPos = origPosFunc;
        }
        let pos = origPos;
        scimoz.setSel(pos, pos);
        controller.doCommand("cmd_transpose");
        if (typeof(expectedPosFunc) === "function") {
            expectedPos = expectedPosFunc(scimoz);
        } else {
            expectedPos = expectedPosFunc;
        }
        this.assertEqual(scimoz.currentPos, expectedPos);
        this.assertEqual(scimoz.text, expectedBufLines.join(eol));
    }
}

// For the tests with only one line we shouldn't need to care what kind of EOL the doc uses.
TestTransposeChars.prototype.test_transpose_empty_doc = function test_transpose_empty_doc() {
    var bufLines  = ['' ];
    this._runTheTest(bufLines, 0, bufLines, 0);
};

TestTransposeChars.prototype.test_transpose_1_char_doc = function test_transpose_1_char_doc() {
    var bufLines  = ['x' ];
    this._runTheTest(bufLines, 1, bufLines, 1);
};

TestTransposeChars.p_doc = function test_transpose_1_char_doc() {
    var bufLines  = ['xy' ];
    this._runTheTest(bufLines, 2, ["yx"], 2);
};

TestTransposeChars.prototype.test_transpose_n_charse_n_char_pos_0 = function test_transpose_n_charse_n_char_pos_0() {
    var bufLines  = ['abcdef' ];
    this._runTheTest(bufLines, 0, bufLines, 0);
};

TestTransposeChars.prototype.test_transpose_in_word = function test_transpose_in_word() {
    var bufLines = ['abcdef' ];
    var bufText = bufLines.join("\r\n");
    var scimoz, view, controller;
    [scimoz, view, controller] = this._setupScimoz(bufText);
    var line1 = bufLines[0];
    for (var i = 1; i < line1.length - 1; i++) {
        scimoz.text = bufLines;
        let expectedWord = line1.substr(0, i - 1) + line1[i] + line1[i - 1] + line1.substr(i + 1);
        scimoz.setSel(i, i);
        controller.doCommand("cmd_transpose");
        this.assertEqual(scimoz.text, expectedWord, "Failed on round " + i);
        this.assertEqual(scimoz.currentPos, i + 1);
    }
};

TestTransposeChars.prototype.test_transpose_at_end_of_doc = function test_transpose_at_end_of_doc() {
    var bufLines  = ['abcdef' ];
    this._runTheTest(bufLines, 6, ['abcdfe'], 6);
};

TestTransposeChars.prototype.test_transpose_at_eol = function test_transpose_at_eol() {
    ['\r\n', "\n", "\r"].forEach(function(eol) {
            var bufLines  = ['abcdef' + eol]; // Hardwired EOL, doesn't matter
            this._runTheTest(bufLines, 6, ['abcdfe' + eol], 6);
        }.bind(this));
};
// Time for some multi-line tests now

// At end of a short line (0 or 1 chars):
// No prev line: do nothing
TestTransposeChars.prototype.test_transpose_at_eol__0_char_line_first_line = function test_transpose_at_eol__0_char_line_first_line() {
    var bufLines  = ['',
                   'efgh',
                ];
    this._runTheTest(bufLines, 0, bufLines, 0);
};

// No prev line: do nothing
TestTransposeChars.prototype.test_transpose_at_eol__1_char_line_first_line = function test_transpose_at_eol__1_char_line_first_line() {
    var bufLines  = ['a',
                   'efgh',
                ];
    this._runTheTest(bufLines, 1, bufLines, 1);
};

// Current line and prev line are both empty, so do nothing
TestTransposeChars.prototype.test_transpose_both_lines_empty = function test_transpose_both_lines_empty() {
    var bufLines  = ['abcd',
                   '',
                   '',
                   'efgh',
                ];
    var posFunc = function(scimoz) scimoz.positionFromLine(2); // both funcs
    this._runTheTest(bufLines, posFunc, bufLines, posFunc);
};

TestTransposeChars.prototype.test_transpose_from_empty_line = function test_transpose_from_empty_line() {
    var bufLines  = ['abcd',
                   'xyz',
                   '',
                   'efgh',
                ];
    var expectedLines = [bufLines[0],
                          'xy',
                          'z',
                          bufLines[3]];
    var posFunc = function(scimoz) scimoz.positionFromLine(2);
    var expectedPosFunc = function(scimoz) scimoz.positionFromLine(2) + 1;
    this._runTheTest(bufLines, posFunc, expectedLines, expectedPosFunc);
};

TestTransposeChars.prototype.test_transpose_from_empty_line_at_eof = function test_transpose_from_empty_line_at_eof() {
    var bufLines  = ['abcd',
                   'xyz',
                   '',
                ];
    var expectedLines = [bufLines[0],
                          'xy',
                          'z'];
    var posFunc = function(scimoz) scimoz.positionFromLine(2);
    var expectedPosFunc = function(scimoz) scimoz.positionFromLine(2) + 1;
    this._runTheTest(bufLines, posFunc, expectedLines, expectedPosFunc);
};

TestTransposeChars.prototype.test_transpose_from_col_1_to_empty = function test_transpose_from_col_1_to_empty() {
    var bufLines  = ['abcd',
                   '',
                   'x',
                   'efgh',
                ];
    var expectedLines = [bufLines[0],
                          'x',
                          '',
                          bufLines[3]];
    var posFunc = function(scimoz) scimoz.positionFromLine(2);
    var expectedPosFunc = function(scimoz) scimoz.positionFromLine(2);
    this._runTheTest(bufLines, posFunc, expectedLines, expectedPosFunc);
};

TestTransposeChars.prototype.test_transpose_from_col_1_to_empty_at_eof = function test_transpose_from_col_1_to_empty_at_eof() {
    var bufLines  = ['abcd',
                   '',
                   'x',
                ];
    var expectedLines = [bufLines[0],
                          'x',
                          ''];
    var posFunc = function(scimoz) scimoz.positionFromLine(2) + 1;
    var expectedPosFunc = function(scimoz) scimoz.positionFromLine(2);
    this._runTheTest(bufLines, posFunc, expectedLines, expectedPosFunc);
};

TestTransposeChars.prototype.test_transpose_from_col_0_to_prevLine = function test_transpose_from_col_0_to_prevLine() {
    var bufLines  = ['abcd',
                   'efgh',
                   'jklm',
                   'nopq',
                ];
    var expectedLines = [bufLines[0],
                          bufLines[1] + 'j',
                          'klm',
                          bufLines[3]];
    var posFunc = function(scimoz) scimoz.positionFromLine(2);
    var expectedPosFunc = function(scimoz) scimoz.positionFromLine(2);
    this._runTheTest(bufLines, posFunc, expectedLines, expectedPosFunc);
};

TestTransposeChars.prototype.test_transpose_from_col_0_to_prevLine_at_eof = function test_transpose_from_col_0_to_prevLine_at_eof() {
    var bufLines  = ['abcd',
                   'efgh',
                   'jklm',
                   'n',
                ];
    var expectedLines = [bufLines[0],
                          bufLines[1],
                          bufLines[2] + 'n',
                          ''];
    var posFunc = function(scimoz) scimoz.positionFromLine(3);
    var expectedPosFunc = function(scimoz) scimoz.positionFromLine(3);
    this._runTheTest(bufLines, posFunc, expectedLines, expectedPosFunc);
};

var JS_TESTS = ["TestTransposeChars"];