/* Copyright (c) 2000-2007 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


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
 *      textbox.searchParam = stringutils_updateSubAttr(
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
    var parts = value.split(";");
    var part, colon, name;
    var i;
    for (i = 0; i < parts.length; i++) {
        part = parts[i];
        colon = part.indexOf(':');
        if (colon == -1) {
            throw("no colon in supposedly CSS-like part: '"+part+"'");
        }
        name = part.slice(0, colon).replace(/^\s*/, '').replace(/\s*$/, '');
        if (name == subattrname) {
            value = part.slice(colon+1).replace(/^\s*/, '').replace(/\s*$/, '');
            return value;
        }
    }
    return null;
}


}).apply(ko.stringutils);

var stringutils_escapeWhitespace = ko.stringutils.escapeWhitespace;
var stringutils_unescapeWhitespace = ko.stringutils.unescapeWhitespace;
var stringutils_bytelength = ko.stringutils.bytelength;
var stringutils_charIndexFromPosition = ko.stringutils.charIndexFromPosition;
var stringutils_updateSubAttr = ko.stringutils.updateSubAttr;
var stringutils_getSubAttr = ko.stringutils.getSubAttr;
