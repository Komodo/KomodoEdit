/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

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
