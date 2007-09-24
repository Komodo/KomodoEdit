// window.open('chrome://navigator/content/navigator.xul', 'chrome=yes');
var i, j, pos;
var i;
var hexstr;

function pad(padChar, len, str) {
    while (str.length < len) {
        str = padChar + str;
    }
    return str;
}

var letters="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()-=[]{};:,./<>?".split("");
var leadString = pad(" ", 16, "")
var posEnd;


function makeHexString(numVal, targetLen) {
    return '0x' + pad ('0', targetLen, numVal.toString(16));
}

// Some stuff about where we are.
var len = editor.length;
var curPos = editor.currentPos;
var indentation = editor.indent;
var firstVisLine = editor.firstVisibleLine;
var lineCount = editor.lineCount;
dump("len: " + len + "\n");
dump("curPos: " + curPos + "\n");
dump("indentation: " + indentation + "\n");
dump("firstVisLine: " + firstVisLine + "\n");
dump("lineCount: " + lineCount + "\n");

var startLine =  firstVisLine > 2 ? firstVisLine - 2 : 0;
var endLine = firstVisLine + 35 >= lineCount ? lineCount : firstVisLine + 35;

var i1;
for (i = startLine; i < endLine; i++) {
    pos = editor.positionFromLine(i);
    if (pos >= editor.length || i > endLine) {
        break;
    }
    hexstr = makeHexString(editor.getFoldLevel(i).toString(16), 4);
    i1 = i + 1;
    posEnd = editor.positionFromLine(i1);
    if (i1 < endLine) posEnd -= 2;
    dump(pad(' ', 3, i1.toString()) + " --> " + hexstr + "  ");
    for (j = pos; j < posEnd; j++) {
        dump(editor.getWCharAt(j));
    }
    dump("{" + editor.getCharAt(posEnd) + "}");
    dump("{" + editor.getCharAt(posEnd + 1) + "}");
    dump("\n");
    dump(leadString);
    posEnd += 2;
    for (j = pos; j < posEnd; j++) {
        var styleVal = editor.getStyleAt(j);
        if (styleVal < 0 || styleVal > letters.length) {
          dump("{" + styleVal + "}");
        } else {
        dump (letters[editor.getStyleAt(j)]);
        }
    }
    dump("\n");
}



// end
