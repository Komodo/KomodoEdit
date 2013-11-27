const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "views",
          "findresults" // findresults makes logging work (?)
          );

let logging = Components.utils.import("chrome://komodo/content/library/logging.js", {}).logging;
//let log = logging.getLogger("jstest.TestCase");

var TestTransposeWords = function TestTransposeWords() {
    this.log = logging.getLogger("lint.transposeWords");
    // To activate debugging run  the tests like:
    //   bk test -L lint.transposeWords:DEBUG ....
    //this.log.setLevel(ko.logging.LOG_DEBUG);
}
TestTransposeWords.prototype = new TestCase();

const koIDocument = Ci.koIDocument;
const fileSvc = Cc["@activestate.com/koFileService;1"].getService(Ci.koIFileService);
const docSvc = Cc["@activestate.com/koDocumentService;1"].getService(Ci.koIDocumentService);
const encodingSvc = Cc["@activestate.com/koEncodingServices;1"].getService(Ci.koIEncodingServices);

TestTransposeWords.prototype.msgHandler =
function TestTransposeWords_msgHandler(level, context, message) {
    this.fail("Message handler called in quiet mode: " +
              "level=" + level + " context=" + context +
              " message=" + message + "\n");
};

TestTransposeWords.prototype._setupScimoz = function(buf) {
    var view = new ko.views.ViewMock({text:buf});
    var scimoz = view.scimoz;
    this.assertIn('@activestate.com/ISciMozHeadless;1', Cc,
                  "Headless SciMoz is required");
    var controller = Cc['@ActiveState.com/scintilla/controller;1'].
                        createInstance(Ci.ISciMozController);
    controller.init( scimoz );
    return [scimoz, view, controller];
};

const IS_ARRAY = 1;
const IS_FUNC = 2;
const IS_OTHER = 3;

var convertFunc = function convertFunc(posThing, scimoz, posKind) {
    if (posKind == IS_ARRAY) {
        return scimoz.positionFromLine(posThing[0]) + (posThing[1] || 0);
    }
    if (posKind == IS_FUNC) {
        return posThing(scimoz);
    }
    return posThing;
};

function getPositionKind(posThing) {
    return (Array.isArray(posThing)
            ? IS_ARRAY
            : (typeof(posThing) === "function"
               ? IS_FUNC : IS_OTHER));
}

TestTransposeWords.prototype._runTheTest = function(origBufLines, origPosFunc,
                                                    expectedBufLines, expectedPosFunc, msg ) {
    var eol, eolType;
    const map = {
        "\r\n": "CRLF",
        "\n": "LF",
        "\r": "CR"
    };
    const origKind = getPositionKind(origPosFunc);
    const expectedKind = getPositionKind(expectedPosFunc);
    for ([eol, eolType] in Iterator(map)) {
        if (msg) {
            msg += ", eolType: eolType"
        }
        let bufText = origBufLines.join(eol);
        let scimoz, view, controller;
        [scimoz, view, controller] = this._setupScimoz(bufText);
        view.koDoc.new_line_endings = koIDocument["EOL_" + eolType];
        origPos = convertFunc(origPosFunc, scimoz, origKind);
        let pos = origPos;
        scimoz.setSel(pos, pos);
        controller.doCommand("cmd_transposeWords");
        expectedPos = convertFunc(expectedPosFunc, scimoz, expectedKind);
        this.assertEqual(scimoz.currentPos, expectedPos, msg);
        this.assertEqual(scimoz.text, expectedBufLines.join(eol), msg);
    }
};

TestTransposeWords.prototype.test_transpose_empty_doc = function test_transpose_empty_doc() {
    var bufLines  = ['' ];
    this._runTheTest(bufLines, 0, bufLines, 0);
};

TestTransposeWords.prototype.test_transpose_no_words = function test_transpose_no_words() {
    var bufLines  = [' *&^ %$# &*( ' ];
    var line1 = bufLines[0];
    for (var i = 0; i < line1.length - 1; i++) {
        this._runTheTest(bufLines, i, bufLines, i);
    }
};

TestTransposeWords.prototype.test_transpose_one_word = function test_transpose_one_word() {
    var bufLines  = [' *&^ abc %$# ' ];
    var line1 = bufLines[0];
    for (var i = 0; i < line1.length - 1; i++) {
        this._runTheTest(bufLines, i, bufLines, i);
    }
};

TestTransposeWords.prototype.test_transpose_two_words_simple = function test_transpose_two_words_simple() {
    var bufLines  = ['abc def' ];
    var expLinesChanged = ['def abc' ];
    
    var line1 = bufLines[0];
    for (var i = 0; i < 5; i++) {
        this._runTheTest(bufLines, i, expLinesChanged, 7, "Failed with i = " + i);
    }
    for (var i = 5; i < line1.length; i++) {
        // Nothing can change
        this._runTheTest(bufLines, i, bufLines, i, "Failed with i = " + i);
    }
};

TestTransposeWords.prototype.test_transpose_two_words_near_stuff = function test_transpose_two_words_near_stuff() {
    var parts = [' ', '*&^', 'abc', ' ', 'def', '%$#', ' '];
    var bufLines  = [parts.join("")];
    var expLinesNoChange = bufLines;
    var partsClone = parts.concat([]);
    // Swap 'abc' and 'def'
    [partsClone[2], partsClone[4]] = [partsClone[4], partsClone[2]];
    var expLinesChanged = [partsClone.join("")];
    var lengths = parts.map(function(x) x.length);
    var i;
    // No change when to left of 'abc'
    for (i = 0; i < lengths[0] + lengths[1]; ++i) {
        this._runTheTest(bufLines, i, expLinesNoChange, i, "exp no change on iter" + i);
    }
    var soFar = i;
    const afterChangePosn = lengths.slice(0, 5).reduce(function(x, y) x + y);
    for (i = soFar; i < soFar + lengths[2] + lengths[3] + 1; ++i) {
        this._runTheTest(bufLines, i, expLinesChanged, afterChangePosn, "should be a change on iter:" + i);
    }
    // No change when to right of 'def'
    soFar = i;
    for (i = soFar; i < bufLines[0].length; ++i) {
        this._runTheTest(bufLines, i, expLinesNoChange, i, "exp no change on iter" + i);
    }
};

TestTransposeWords.prototype.test_transpose_words_over_lines = function test_transpose_words_over_lines() {
    const bufLines = ['abc def',
                    '    ',
                    ' ghi ',
                    '++ jkl mno'];
    // Swap abc & def, end at end of abc
    const changedLines_1 = ['def abc'].concat(bufLines.slice(1));
    var i;
    for (i = 0; i < 5; i++) {
        this._runTheTest(bufLines, i, changedLines_1, [0, 7], "exp no change on round 1, iter" + i);
    }
    // Swap def & ghi, end at end of def
    const changedLines_2 = ['abc ghi', bufLines[1], ' def ', bufLines[3]];
    for (i = 5; i < 7; i++) {
        this._runTheTest(bufLines, i, changedLines_2, [2, 4], "exp no change on round 2, iter" + i);
    }
    for (i = 0; i < bufLines[1].length; i++) {
        this._runTheTest(bufLines, [1, i], changedLines_2, [2, 4], "exp no change on round 3, iter" + i);
    }
    this._runTheTest(bufLines, [2, 0], changedLines_2, [2, 4], "exp no change on round 4, iter [2,0]");
    this._runTheTest(bufLines, [2, 1], changedLines_2, [2, 4], "exp no change on round 5, iter [2,1]");
    // Swap ghi & jkl, end at end of ghi
    const changedLines_3 = [bufLines[0], bufLines[1], ' jkl ', '++ ghi mno'];
    for (i = 2; i < bufLines[2].length; i++) {
        this._runTheTest(bufLines, [2, i], changedLines_3, [3, 6], "exp no change on round 6, iter" + i);
    }
    // Swap jkl & mno, end at end of jkl
    const changedLines_4 = [bufLines[0], bufLines[1], bufLines[2], '++ mno jkl'];
    for (; i < bufLines[2].length; i++) {
        this._runTheTest(bufLines, [2, i], changedLines_4, [3, 10], "exp no change on round 7, iter" + i);
    }
};


// Can't run this because headless scimoz.wordChars isn't implemented
TestTransposeWords.prototype.test_verify_perl_wordChar = function test_verify_perl_wordChar() {
    // Verify that in Perl, '$abc' and '@def' switch, but in Text mode '$' and '@' stay put.
    const bufLines = ['my ($abc, @def, %ghi) = "flounder"'];
    var file = fileSvc.makeTempFile(".pl", 'wb');
    var eol = "\n";
    var origBuf = bufLines.join(eol);
    var view = new ko.views.ViewMock({text:origBuf});
    file.puts(origBuf);
    file.close();
    var koDoc = docSvc.createNewDocumentFromURI(file.URI);
    koDoc.new_line_endings = koIDocument.EOL_LF;
    koDoc.language = "Perl";
    var origBugUTF = encodingSvc.encode(origBuf, "utf-8", "");
    koDoc.setBufferAndEncoding(origBugUTF, "utf-8");
    view.koDoc = koDoc;
    //koDoc.addView(view.scintilla);
    var scimoz = view.scimoz;
    // Set the word characters for some reason.
    const perlLangObj = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("Perl");
    const varInd = perlLangObj.variableIndicators;
    const bothChars = varInd + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    try {
        //this.log.debug("Set wordChars to [" + bothChars + "]")
        scimoz.wordChars = bothChars;
    } catch(ex) {
        throw SkipTest("scimoz.wordChars setter not implemented in headless scintilla")
    }
    this.assertIn('@activestate.com/ISciMozHeadless;1', Cc,
                  "Headless SciMoz is required");
    var controller = Cc['@ActiveState.com/scintilla/controller;1'].
                        createInstance(Ci.ISciMozController);
    controller.init( scimoz );
    var pos = bufLines[0].indexOf("@def");
    scimoz.setSel(pos, pos);
    var expectedLines_1 = ['my (@def, $abc, %ghi) = "flounder"'];
    controller.doCommand("cmd_transposeWords");
    this.assertEqual(scimoz.currentPos, expectedLines_1[0].indexOf("abc") + 3);
    this.assertEqual(scimoz.text, expectedLines_1.join(eol));
};
    
var JS_TESTS = ["TestTransposeWords"];