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


if (typeof(ko)=='undefined') {
    var ko = {};
}

// Utility functions to escape and unescape whitespace
ko.stringutils = {};
(function() {
    
this.escapeWhitespace = function stringutils_escapeWhitespace(text) {
    text = text.replace(/\\/g, '\\\\'); // escape backslashes
    text = text.replace(/\r\n/g, '\\n'); // convert all different ends of lines to literal \n
    text = text.replace(/\n/g, '\\n');
    text = text.replace(/\r/g, '\\n');
    text = text.replace(/\t/g, '\\t');
    return text;
}

this.unescapeWhitespace = function stringutils_unescapeWhitespace(text, eol) {
    var i;
    var newtext = '';
    for (i = 0; i < text.length; i++) {
        switch (text[i]) {
            case '\\':
                i++;
                switch (text[i]) {
                    case 'n':
                        newtext += eol;
                        break;
                    case 't':
                        newtext += '\t';
                        break;
                    case '\\':
                        newtext += '\\';
                        break;
                    // For backward compatiblity for strings that were not
                    // escaped but are being unescaped to ensure that, e.g.:
                    //    C:\WINNT\System32
                    // ends up unchanged after unescaping.
                    default:
                        i--;
                        newtext += '\\';
                }
                break;
            default:
                newtext += text[i];
        }
    }
    return newtext;
}

// Used for managing auto-abbreviation trigger character strings.
this._endsWithEvenNumberOfBackslashes = function(s) {
    return /(?:^|[^\\])(?:\\\\)*$/.test(s);
};
this.backslashUnescape = function stringutils_backslashUnescape(text) {
    var pieces = text.split('"');
    var newPieces = [];
    var piece;
    var lim = pieces.length - 1
    for (var i = 0; i < lim; ++i) {
        piece = pieces[i];
        newPieces.push(piece);
        if (this._endsWithEvenNumberOfBackslashes(piece)) {
            newPieces.push('\\');
        }
        newPieces.push('"');
    }
    newPieces.push(pieces[lim]);
    var s = '"' + newPieces.join(newPieces) + '"';
    return eval(s);
};


var _sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
    getService(Components.interfaces.koISysUtils);

this.bytelength = function stringutils_bytelength(s)
{
    return _sysUtils.byteLength(s);
}

this.charIndexFromPosition = function stringutils_charIndexFromPosition(s,p)
{
    return _sysUtils.charIndexFromPosition(s,p);
}



/* Utility functions for working with key/value pairs in a CSS-style-like
 * string:
 *      subattr1: value1; subattr2: value2; ...
 *
 * Limitations:
 * - Does not handle quoting or escaping to deal with ':' or spaces in
 *   values.
 * 
 * This is useful, for example, for modifying the "cwd: <value>" sub-attribute
 * of the "autocompletesearchparam" attribute on an autocomplete textbox.
 *      textbox.searchParam = ko.stringutils.updateSubAttr(
 *          textbox.searchParam, "cwd", ko.window.getCwd());
 *  
 */
this.updateSubAttr = function stringutils_updateSubAttr(oldValue, subattrname, subattrvalue) {
    var nullValue = typeof(subattrvalue)=='undefined' || !subattrvalue;
    var newValue = "";
    if (oldValue) {
        var foundIt = false;
        var parts_before = oldValue.split(";");
        var parts_after = new Array();
        var part, name_and_value, name, value;
        var i;
        for (i = 0; i < parts_before.length; i++) {
            part = parts_before[i];
            name_and_value = part.split(':');
            if (subattrname == name_and_value[0]) {
                if (nullValue) {
                    // no value, remove the sub-attribute
                    continue;
                }
                parts_after.push(subattrname + ":" + subattrvalue);
                foundIt = true;
            } else {
                parts_after.push(part);
            }
        }
        if (!foundIt && !nullValue) {
            parts_after.push(subattrname + ":" + subattrvalue);
        }
        newValue = parts_after.join(";");
    } else if (!nullValue) {
        newValue = subattrname + ":" + subattrvalue;
    }

    //dump("stringutils_updateSubAttr: oldValue='" + oldValue + 
    //     "' -> newValue='" + newValue + "'\n");
    return newValue;
}

this.getSubAttr = function stringutils_getSubAttr(value, subattrname)
{
    const STATE_NAME = "NAME",
          STATE_VALUE = "VALUE",
          STATE_QUOTED = "QUOTED";
    var found = false, state = STATE_NAME;
    for (;;) {
        switch (state) {
            case STATE_NAME:
            {
                let i = value.indexOf(":");
                if (i < 0) {
                    throw new Error("no colon in supposedly CSS-like part: '"+value+"'");
                }
                let name = value.substr(0, i).replace(/^\s*|\s*$/g, "");
                found = (name == subattrname);
                value = value.substr(i).replace(/^:\s*/, "");
                state = /^["']/.test(value) ? STATE_QUOTED : STATE_VALUE;
                continue;
            }
            case STATE_QUOTED: {
                let quoteChar = value[0];
                let i = 1;
                for(;;) {
                    let escape = value.indexOf("\\", i);
                    let quote = value.indexOf(quoteChar, i);
                    if (escape != -1 && escape < quote) {
                        i = escape + 2; // skip escape and the char after it
                        continue;
                    }
                    if (quote < 0) {
                        return null; // no end quote
                    }
                    if (found) {
                        return value.substr(1, quote - 1).replace(/\\(.)/g, "$1");
                    }
                    value = value.substr(quote + 1).replace(/^\s*;\s*/, "");
                    state = STATE_NAME;
                    break;
                }
                continue;
            }
            case STATE_VALUE: {
                let index = value.indexOf(";");
                if (index < 0) index = value.length;
                if (found) {
                    return value.substr(0, index).replace(/\s*$/, "");
                }
                value = value.substr(index).replace(/^\s*;\s*/, "");
                state = STATE_NAME;
                continue;
            }
            default: {
                return null;
            }
        }
    }
    return null;
};

/**
 * Return a copy of s with the leading and trailing whitespace removed.
 * @returns {string}
 */
this.strip = function(s) {
    return s.replace(/(^\s*|\s*$)/g, ''); // strip whitespace;
}

/**
 * Return a string of length fieldSize, where the left side of the
 * string is padded with enough instances of padChar to reach the
 * target size.  The returned size is the minimum size that exceeds fieldSize.
 *
 * @param {string} text -- the text to right-align in a field
 * @param {integer} fieldSize -- minimum acceptable size of the final text
 * @param {string} padChar -- default is a space

 * Returns text if fieldSize <= 0
 * @returns {string}
 */
 this.padLeft = function(text, fieldSize, padChar) {
     if (text.length >= fieldSize) {
         return text;
     }
     if (typeof(padChar) === "undefined") {
         padChar = " ";
     }
     var numSpacesNeeded = fieldSize - text.length;
     var numItemsNeeded = Math.ceil(numSpacesNeeded / padChar.length);
     var s = [];
     while (--numItemsNeeded >= 0) {
         s.push(padChar);
     }
     return s.join("") + text;
 };

/**
 * Use koIOs.expanduser to expand a leading "~".  This contracts it.
 *
 * @param {string} path
 * @returns one of ~/..., ~name/..., or path
 */

this.contractUser = function(path) {
    var userEnvironment = Components.classes["@mozilla.org/process/environment;1"].getService(Components.interfaces.nsIEnvironment);
    var homePath = userEnvironment.get("HOME");
    if (!homePath) {
        return path;
    }
    if (path == homePath) {
	return "~";
    }
    var sep = Components.classes["@activestate.com/koOs;1"].
	      getService(Components.interfaces.koIOs).sep;
    if (path.indexOf(homePath + sep) == 0) {
        return "~" + path.substr(homePath.length);
    }
    // Try to contract paths like /home/otherGuy/dir1/dir2 to
    // ~otherGuy/dir1/dir2
    var userName = userEnvironment.get("USER");
    if (!userName) {
        return path;
    }
    // Find the dir that contains all the users.
    var idx = homePath.lastIndexOf(userName);
    if (idx == -1) {
        return path;
    }
    var userPrefix = homePath.substr(0, idx);
    // If this dir is a prefix of the current dir, assume the first part
    // is a different user, and ~-contract it.
    if (path.indexOf(userPrefix) == 0) {
        return "~" + path.substr(userPrefix.length);
    }
    return path;
};

}).apply(ko.stringutils);

if (typeof(window) == "undefined") {
    (function() {
	this.EXPORTED_SYMBOLS = ["stringutils"];
	this.stringutils = ko.stringutils;
    })();
}
