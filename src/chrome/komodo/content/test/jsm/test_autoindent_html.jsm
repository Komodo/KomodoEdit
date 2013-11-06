// Run tests on HTML autoindenting

const {classes: Cc, interfaces: Ci, utils: Cu, results: Cr} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://gre/modules/Services.jsm");

var ko = {};
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "logging", "views", "stringutils");

function TestHTMLAutoIndent() {
    this.log = ko.logging.getLogger("HTMLAutoIndent.test");
    this.log.setLevel(ko.logging.LOG_DEBUG);
}


var htmlLangSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("HTML");

TestHTMLAutoIndent.prototype = new TestCase();

TestHTMLAutoIndent.prototype.setUp = function TestHTMLAutoIndent_setUp() {
};

TestHTMLAutoIndent.prototype.tearDown = function TestHTMLAutoIndent_tearDown() {
};

TestHTMLAutoIndent.prototype._get_scimoz_and_koDoc_from_string = function(buf) {
    var view = new ko.views.ViewMock({text:buf});
    var scimoz = view.scimoz;
    this.assertIn('@activestate.com/ISciMozHeadless;1', Cc,
                  "Headless SciMoz is required");
    //this.log.debug("We have a headless scimoz");
    // Set up the real HTML lexer (for styling information)
    var lexerSvc = Cc["@activestate.com/koLanguageRegistryService;1"]
                     .getService(Ci.koILanguageRegistryService)
                     .getLanguage("HTML5")
                     .getLanguageService(Ci.koILexerLanguageService);
    lexerSvc.setCurrent(scimoz);
    scimoz.useTabs = false;
    scimoz.colourise(0, scimoz.length);
    return [scimoz, view.koDoc, view];
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent01 =
function test_startTagCloseIndent01() {
    var buf_01  = ['<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"'
                 ,'    "http://www.w3.org/TR/html4/loose.dtd">'
                 ,'<html>'
                 ,'<head>'
                 ,'    <title>Page Title</title>'
                 ,'</head>'
                 ,''
                 ,'<body>'
                ];
    var text_01 = buf_01.join("\r\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.currentPos = text_01.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(" ".repeat(scimoz.indent), indent,
                      "Indent " + escape(indent) +
                      " does not match expected indent " +
                      escape(" ".repeat(scimoz.indent)));

    // Test inner tag, assume all spaces
    var buf_02 = buf_01.concat("    <div id='1'>");
    var text_02 = buf_02.join("\r\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_02);
    scimoz.currentPos = text_02.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(" ".repeat(8), indent,
                      "Indent " + escape(indent) +
                      " does not match expected indent " + escape(" ".repeat(8)));

    // Test inner tag, now move to tabs
    buf_02 = buf_01.concat("    <div id='1'>")
    text_02 = buf_02.join("\r\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_02);
    scimoz.currentPos = text_02.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(" ".repeat(8), indent);
    scimoz.useTabs = true;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals("\t", indent,
                      "Indent " + escape(indent) +
                      " does not match expected indent " + escape("\t"));

    // <body>\n....<div1>\n        <div2>|
    var buf_03 = buf_02.concat("        <div id='2'>") // 8 spaces
    var text_03 = buf_03.join("\r\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_03);
    scimoz.currentPos = text_03.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = true;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(5, indent.length);
    this.assertEquals("\t    ", indent);

    // <body>\n....<div1>\n\t<div2>
    buf_03 = buf_02.concat("\t<div id='2'>") // 1 tab
    text_03 = buf_03.join("\r\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_03);
    scimoz.currentPos = text_03.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = true;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(5, indent.length);
    this.assertEquals("\t    ", indent);
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent03_LargeAttr =
function test_startTagCloseIndent03_LargeAttr() {
    // Add 6k characters in the attribute string
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                ];
    var attrPart = "abcdefghi ";
    var limNumChars = 6000;
    var numParts = Math.ceil(limNumChars / attrPart.length);
    var attrParts = attrPart.repeat(numParts + 1);
    var lastLine = '        <div class="y' + attrParts + '">';
    buf_01.push(lastLine);
    buf_01.push('');
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.currentPos = 66 + attrParts.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(12, indent.length);
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent04_LargeAttr =
function test_startTagCloseIndent04_LargeAttr() {
    // Add 6k characters in the attribute string
    // But this time the tag is split on two lines, so we get the
    // autoindent wrong
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x"'
                ];

    const attrPart = "abcdefghi ";
    const attrLineSize = 80;//1000;
    const numAttrParts = Math.ceil((attrLineSize - 12 - 1)/attrPart.length);
    const attrLinePrev = ' '.repeat(12) + "attr";
    const attrLineAfter = '="' + attrPart.repeat(numAttrParts) + '"'

    const limNumChars = 100;//6000;
    const numAttrLines = Math.ceil(limNumChars / (attrLinePrev.length + 2 + attrLineAfter.length + 1));
    var i = 0;
    for (var i = 0; i < numAttrLines - 1; i++) {
        let fullLineParts = [attrLinePrev];
        if (i < 10) {
            fullLineParts.push("0");
        }
        fullLineParts.push(i.toString(10));
        fullLineParts.push(attrLineAfter);
        buf_01.push(fullLineParts.join(''));
    }
    // Last line is slightly different
    let fullLineParts = [attrLinePrev];
    if (numAttrLines < 10) {
        fullLineParts.push("0");
    }
    fullLineParts.push(numAttrLines.toString(10));
    fullLineParts.push(attrLineAfter);
    fullLineParts.push(">")
    buf_01.push(fullLineParts.join(''));

    var text_01 = buf_01.join("\n");
    //this.log.debug("text_01: " + text_01.length + " chars");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.currentPos = text_01.length;
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(8, indent.length);
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent05_LargeAttr =
function test_startTagCloseIndent05_LargeAttr() {
    // Add 6k characters in the attribute string
    // But this time the tag is split on two lines, so we get the
    // autoindent wrong
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x"'
                ];

    const attrPart = "abcdefghi ";
    const attrLineSize = 1000;
    const numAttrParts = Math.ceil((attrLineSize - 12 - 1)/attrPart.length);
    const attrLinePrev = ' '.repeat(12) + "attr";
    const attrLineAfter = '="' + attrPart.repeat(numAttrParts) + '"'

    const limNumChars = 6000;
    const numAttrLines = Math.ceil(limNumChars / (attrLinePrev.length + 2 + attrLineAfter.length + 1));
    var i = 0;
    for (var i = 0; i < numAttrLines - 1; i++) {
        let fullLineParts = [attrLinePrev];
        if (i < 10) {
            fullLineParts.push("0");
        }
        fullLineParts.push(i.toString(10));
        fullLineParts.push(attrLineAfter);
        buf_01.push(fullLineParts.join(''));
    }
    // Last line is slightly different
    let fullLineParts = [attrLinePrev];
    if (numAttrLines < 10) {
        fullLineParts.push("0");
    }
    fullLineParts.push(numAttrLines.toString(10));
    fullLineParts.push(attrLineAfter);
    fullLineParts.push(">")
    buf_01.push(fullLineParts.join(''));

    var text_01 = buf_01.join("\n");
    //this.log.debug("text_01: " + text_01.length + " chars");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.currentPos = text_01.length;
    scimoz.indent = 12;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(12, indent.length);
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent03_FollowedBySpaces =
function test_startTagCloseIndent03_FollowedBySpaces() {
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                   ,'        <div class="y">  	  '
                ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 71;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    this.assertEquals(12, indent.length);
    this.assertEquals(" ".repeat(12), indent);
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent03_FollowedByNonSpace =
function test_startTagCloseIndent03_FollowedByNonSpace() {
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                   ,'        <div class="y">  x	  '
                ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 72;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    var expNumSpaces = 8;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
};

TestHTMLAutoIndent.prototype.test_startTagCloseIndent04_PrecededByText =
function test_startTagCloseIndent04_PrecededByText() {
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                   ,'  f     <div class="y">'
                ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 66;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    var expNumSpaces = 2;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
};

TestHTMLAutoIndent.prototype.test_endTagCloseIndent01 =
function test_endTagCloseIndent01() {
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                   ,'        <div class="y">'
                   ,'            some text...'
                   ,'            </div>'
                   ,''
                ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 110;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    var expNumSpaces = 8;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
};

TestHTMLAutoIndent.prototype.test_endTagCloseIndent02_NoMatchingTag =
function test_endTagCloseIndent02_NoMatchingTag() {
    var buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                   ,'        <div class="y">'
                   ,'            some text...'
                   ,'            </oops>'
                   ,''
                ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 111;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
    var expNumSpaces = 12;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
};

TestHTMLAutoIndent.prototype.addContent =
    function addContent(buf_a, leadingWS, limNumChars) {
    var buf_new = [].concat(buf_a);
    var desiredFullLength = 72;
    var lineLength = desiredFullLength - leadingWS.length;
    var attrPart = "abcdefghi ";
    var numLines = Math.ceil(limNumChars / desiredFullLength);
    var numParts = Math.ceil(lineLength / attrPart.length);
    var attrParts = attrPart.repeat(numParts + 1);
    var i;
    var fullLineLength = leadingWS.length + attrParts.length + 1; // 1 for \n
    //this.log.debug("numLines; "
    //               + numLines
    //               + ", fullLineLength:"
    //               + fullLineLength
    //               );
    var newCharsAdded = 0;
    for (var i = 0; i < numLines; i++) {
        buf_new.push(leadingWS + attrParts);
    }
    return [buf_new, numLines * fullLineLength, numLines];
}

TestHTMLAutoIndent.prototype.test_endTagCloseIndent03_largeContent =
function test_endTagCloseIndent03_largeContent() {
    const buf_01  = [ '<!DOCTYPE HTML>'
                   ,'<body>'
                   ,'    <div class="x">'
                   ,'        <div class="y">'];
    const leadingWS = ' '.repeat(12);
    const lastLine = leadingWS + '</div>';
    var buf_02, numExtraChars_02, numTextLines;
    var extraCharCount, text_02, indent, expNumSpaces = 8;
    const extraCounts = [0, 1000, 4000, 8000, 12000, 20000, 40000, 100000];
    var i, extraCharCount;
    var numTestsRan = 0;
    for (i = 0; i < extraCounts.length; ++i, numTestsRan++) {
        extraCharCount = extraCounts[i];
        [buf_02, numExtraChars_02, numTextLines] = this.addContent(buf_01, leadingWS, extraCharCount, 0);
        //this.log.debug("numExtraChars_02: " + numExtraChars_02);
        buf_02.push(lastLine);
        buf_02.push('');

        var text_02 = buf_02.join("\n");
        //this.log.debug("text_02: " + text_02.length + "\n\n\n");
        [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_02);
        scimoz.indent = 4;
        scimoz.tabWidth = 8;
        scimoz.useTabs = false;
        scimoz.currentPos = 85 + numExtraChars_02;
        //this.log.debug("scimoz.currentPos: " + scimoz.currentPos);
        var t1 = (new Date()).valueOf();
        var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
        var t2 = (new Date()).valueOf();
        //this.log.debug("Time to process " + extraCharCount
        //               + " chars: " + (t2 - t1) + " msec");
        this.assertEquals(expNumSpaces, indent.length);
        this.assertEquals(" ".repeat(expNumSpaces), indent);
    }
    this.assertEquals(extraCounts.length, numTestsRan,
                      "Didn't run all the tests we expected to see");
};

TestHTMLAutoIndent.prototype.test_emptyStartTagCloseIndent01 =
function test_emptyStartTagCloseIndent01() {
    // Test the indentation for various points in the empty tag on the last line
    var buf_01 = [ '<!DOCTYPE HTML>'
             ,'<body>'
             ,'    <div class="x">'
             ,'        <div class="y">'
             ,'            <img src="abc" />'
             ,''
            ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;

    // And test pressing newlines at various points
    // First entry: currentPos.  Second entry: # expected spaces in the indent.
    var expectedPairs = [[83, 16],
                         [84, 17],
                         [85, 17],
                         [86, 17],
                         [87, 17],
                         [88, 17],
                         [89, 12],
                         [90, 12],
                         [91, 12],
                         [92, 12],
                         [93, 17],
                         [94, 17],
                         [95, 12],
                         [96, 12]
                         ];
    var i, pair, currentPos, expNumSpaces;
    for (i = 0; pair = expectedPairs[i]; ++i) {
        [currentPos, expNumSpaces] = pair;
        scimoz.currentPos = currentPos;
        //this.log.debug("lineEnd(5): " + scimoz.getLineEndPosition(5));
        var indent = htmlLangSvc.computeIndent(scimoz, "XML", true);
        var expNumSpaces = expNumSpaces;
        this.assertEquals(expNumSpaces, indent.length,
                          "For currentPos: " + currentPos + ", expNumSpaces: " + expNumSpaces);
        this.assertEquals(" ".repeat(expNumSpaces), indent);
    }
};

TestHTMLAutoIndent.prototype.test_emptyStartTagCloseIndent02_LargeContent =
function test_emptyStartTagCloseIndent02_LargeContent() {
    // Test the indentation for various points in the empty tag on the last line
    const buf_01 = [ '<!DOCTYPE HTML>'
             ,'<body>'
             ,'    <div class="x">'
             ,'        <div class="y">'
             ,'            <img src="'
            ];
    //this.log.debug("buf len: "
    //               + buf_01.reduce(function(sum, item) sum + item.length,  0)
    //               + ", buf parts: ["
    //               + buf_01.map(function(s) s.length)
    //               + "]");
    const leadingWS = ' '.repeat(12);
    const lastLine = leadingWS + '" />';
    var buf_02, numExtraChars_02, numTextLines;
    var extraCharCount, text_02, indent, expNumSpaces = 8;
    const extraCounts = [0, 1000, 4000, 8000, 12000, 20000, 40000, 100000];
    var i, extraCharCount;
    var numTestsRan = 0;

    // And test pressing newlines at various points
    // First entry: currentPos.  Second entry: # expected spaces in the indent.
    const expectedPairs = [];
    for (i = 0; i < 12; ++i) {
        expectedPairs.push([90 + i, i]);
    }
    expectedPairs.push([102, 12]);
    expectedPairs.push([103, 12]);
    const AFTER_QUOTE = expectedPairs.length;
    expectedPairs.push([104, 17]);
    expectedPairs.push([105, 12]);
    for (i = 0; i < extraCounts.length; ++i) {
    //for (i = 3; i < 4; ++i) {
        extraCharCount = extraCounts[i];
        [buf_02, numExtraChars_02, numTextLines] =
            this.addContent(buf_01, leadingWS, extraCharCount, 8);
        if (numExtraChars_02 > 6000) {
            expectedPairs[AFTER_QUOTE][1] = 12;
        } else {
            expectedPairs[AFTER_QUOTE][1] = 17;
        }
        //this.log.debug("expectedPairs[" + AFTER_QUOTE + "][1] = " + expectedPairs[AFTER_QUOTE][1]);
        //this.log.debug("numExtraChars_02: " + numExtraChars_02);
        buf_02.push(lastLine);
        buf_02.push('');

        var text_02 = buf_02.join("\n");
        //this.log.debug("text_02: " + text_02.length + "");
        [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_02);
        scimoz.indent = 4;
        scimoz.tabWidth = 8;
        scimoz.useTabs = false;
        let j, pair, currentPos, expNumSpaces;
        for (j = 0; pair = expectedPairs[j]; ++j) {
        //for (j = 14; pair = expectedPairs[j]; ++j) {
        //    if (j == 15) {
        //        break;
        //    }
            [currentPos, expNumSpaces] = pair;
            let adjustedCurrentPos = currentPos + numExtraChars_02;
            scimoz.currentPos = adjustedCurrentPos;
            //this.log.debug("text_02: " + text_02.substring(0, adjustedCurrentPos)
            //               + "<|>"
            //               + text_02.substring(adjustedCurrentPos) + "\n");
            //this.log.debug("scimoz.currentPos: " + adjustedCurrentPos);
            //var t1 = (new Date()).valueOf();
            //let t1 = new Date().valueOf();
            var indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
            //let t2 = new Date().valueOf();
            //this.log.debug("Time to indent at pos "
            //               + adjustedCurrentPos
            //               + "/" + text_02.length
            //               + " chars: "
            //               + ((t2 - t1))
            //               + " msec"
            //               )
            if (indent === null) {
                // Make this change due to bug 100858
                indent = "";
            }
            //var t2 = (new Date()).valueOf();
            //this.log.debug("Time to process " + extraCharCount
            //               + " chars: " + (t2 - t1) + " msec");
            this.assertEquals(expNumSpaces, indent.length,
                              ("failure on extraCharIndex: " + i
                               + ", extraCharCount: " + extraCharCount
                               + ", adjustedPos index: " + j
                               + ", adjustedCurrentPos: " + adjustedCurrentPos
                               + ", expected " + expNumSpaces + " spaces"
                               + ", got indent length " + indent.length));
            this.assertEquals(" ".repeat(expNumSpaces), indent);
            numTestsRan += 1;
        }
    }
    this.assertEquals(extraCounts.length * expectedPairs.length, numTestsRan,
                      "Didn't run all the tests we expected to see");
};

TestHTMLAutoIndent.prototype.test_endCommentIndent01 =
function test_endCommentIndent01() {
    // We should go back to column #4
    var buf_01 = [ '<!DOCTYPE HTML>'
             ,'<body>'
             ,'    <!-- some comment'
             ,'        blah'
             ,'        -->'
             ,''
            ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 69;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
    var expNumSpaces = 4;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
    // At end of 'blah', indent should continue on same line
    scimoz.currentPos = 57;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
    expNumSpaces = 8;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
};

TestHTMLAutoIndent.prototype.test_endCommentIndent02_LargeContent =
function test_endCommentIndent02_LargeContent() {
    // We should go back to column #4
    var buf_01 = [ '<!DOCTYPE HTML>'
             ,'<body>'
             ,'    <!-- some comment'
             ,'        blah'
            ];
    const leadingWS = ' '.repeat(8);
    const lastLine = leadingWS + '-->';
    var buf_02, numExtraChars_02, numTextLines;
    var extraCharCount, text_02, indent, expNumSpaces = 8;
    const extraCounts = [0, 1000, 4000, 8000, 12000, 20000, 40000, 100000];
    var i, extraCharCount;
    var numTestsRan = 0;

    // And test pressing newlines at various points
    // First entry: currentPos.  Second entry: # expected spaces in the indent.
    const expectedPairs = [];
    const startingPoint = 58;
    const startingLim = 8;
    for (i = 0; i < startingLim; ++i) {
        expectedPairs.push([58 + i, i]);
    }
    expectedPairs.push([startingPoint + startingLim, 8]);
    expectedPairs.push([startingPoint + startingLim + 1, 8]);
    expectedPairs.push([startingPoint + startingLim + 2, 8]);
    const AFTER_QUOTE = expectedPairs.length;
    expectedPairs.push([startingPoint + startingLim + 3, 4]);

    for (i = 0; i < extraCounts.length; ++i) {
    //for (i = 3; i < 4; ++i) {
        extraCharCount = extraCounts[i];
        [buf_02, numExtraChars_02, numTextLines] =
            this.addContent(buf_01, leadingWS, extraCharCount,
                            8);
        if (numExtraChars_02 > 7000) {
            expectedPairs[AFTER_QUOTE][1] = 8;
        }
        buf_02.push(lastLine);
        buf_02.push('');

        var text_02 = buf_02.join("\n");
        [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_02);
        scimoz.indent = 4;
        scimoz.tabWidth = 8;
        scimoz.useTabs = false;
        let j, pair, currentPos, expNumSpaces;
        for (j = 0; pair = expectedPairs[j]; ++j) {
            [currentPos, expNumSpaces] = pair;
            let adjustedCurrentPos = currentPos + numExtraChars_02;
            scimoz.currentPos = adjustedCurrentPos;
            let indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
            if (indent === null) {
                indent = ""
            }
            this.assertEquals(expNumSpaces, indent.length,
                              ("failure on extraCharIndex: "
                               + i
                               + ", extraCharCount: " + extraCharCount
                               + ", adjustedPos index: "
                               + j
                               + ", adjustedCurrentPos: " + adjustedCurrentPos));
            this.assertEquals(" ".repeat(expNumSpaces), indent);
            numTestsRan += 1;
        }
    }
    this.assertEquals(extraCounts.length * expectedPairs.length, numTestsRan,
                      "Didn't run all the tests we expected to see");
};

TestHTMLAutoIndent.prototype.test_endPI01 =
function test_endPI01() {
    // We should go back to column #4
    var buf_01 = [ '<!DOCTYPE HTML>'
                  ,'<body>'
                  ,'    <?fli a="abcd"'
                  ,'          b="efghij"'
                  ,'          c="klmno" ?>'
                  ,''
                 ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;
    scimoz.currentPos = 85;
    var indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
    var expNumSpaces = 4;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
    // At end of 'efghij', indent should continue on same line
    scimoz.currentPos = 62;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
    expNumSpaces = 10;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
    // Anywhere on first line, just snap back to column where <? starts.
    scimoz.currentPos = 41;
    indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
    expNumSpaces = 4;
    this.assertEquals(expNumSpaces, indent.length);
    this.assertEquals(" ".repeat(expNumSpaces), indent);
};

TestHTMLAutoIndent.prototype.test_endCDATA_01 =
function test_endCDATA_01() {
    // We should go back to column #4
    var buf_01 = [ '<!DOCTYPE HTML>'
                  ,'<body>'
                  ,'    <![CDATA['
                  ,'    Some text'
                  ,'           continue here'
                  ,'  and here'
                  ,'  ]]>'
                  ,'    Should go here.'
                  ,''
                 ];
    var text_01 = buf_01.join("\n");
    [scimoz, koDoc] = this._get_scimoz_and_koDoc_from_string(text_01);
    scimoz.indent = 4;
    scimoz.tabWidth = 8;
    scimoz.useTabs = false;

    var expectedPairs = [[35, 4],
                         [50, 4],
                         [75, 11],
                         [86, 2],
                         [92, 4]
                         ];
    var i, pair, currentPos, expNumSpaces, indent;
    for (i = 0; pair = expectedPairs[i]; ++i) {
        [currentPos, expNumSpaces] = pair;
        scimoz.currentPos = currentPos;
        indent = htmlLangSvc.computeIndent(scimoz, "XML", false);
        this.assertEquals(expNumSpaces, indent.length,
                          "Pos " + currentPos + ", expected "
                          + expNumSpaces
                          + " spaces, got "
                          + indent.length);
        this.assertEquals(" ".repeat(expNumSpaces), indent);
    }
};
const JS_TESTS = ["TestHTMLAutoIndent"];
