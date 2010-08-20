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

/**
 * A regular expression hyperlink handler.
 *
 * @class
 * @base ko.hyperlinks.BaseHandler
 * @param name {string} A unique name of the hyperlink handler.
 * @param findRegex {regexp} Regular expression used to find the hyperlink.
 * @param fn {function} Will be called when the user clicks on the jump
 *        point. The matching (or replaced) hyperlink value is the only
 *        argument passed to this function.
 * @param replace_str {string|null} Optional - If set, will be used to
 *        change the matching text into a different value, similar to
 *        str.replace(findRegex, replace_str), so you can use the JavaScript
 *        regular expression positions: $1, $2, etc... in the string.
 * @param lang_names {array|null} Optional - If set, the handler will
 *        only show hyperlinks when the editor language is one of these
 *        language names.
 * @param indic_style {int} Optional - Indicator style, see scimoz.INDIC_*
 * @param indic_color {int} Optional - Indicator color (BGR), i.e. 0xFFCC33
 */
ko.hyperlinks.RegexHandler = function(name, findRegex, fn, replace_str, lang_names,
                                      indic_style, indic_color)
{
    var base_args = [name, fn, lang_names, indic_style, indic_color];
    ko.hyperlinks.BaseHandler.apply(this, base_args);
    this.findRegex = findRegex;
    this.replace_str = replace_str;
    this.regex_match = null;
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
ko.hyperlinks.RegexHandler.prototype = new ko.hyperlinks.BaseHandler();
ko.hyperlinks.RegexHandler.prototype.constructor = ko.hyperlinks.RegexHandler;

/**
 * Try and show a hyperlink at the current position in the view.
 *
 * @param view {Components.interfaces.koIScintillaView}  View to check.
 * @param scimoz {Components.interfaces.ISciMoz}  Scimoz for the view.
 * @param position {int}  Position in the scimoz editor.
 * @param line {string}  The current line from the editor.
 * @param lineStartPos {int} Scimoz position for the start of the line.
 * @param lineEndPos {int}   Scimoz position for the end of the line.
 * @param reason {string}  What the triggering event reason was, can be one
 *        of "keypress" or "mousemove".
 * @returns {ko.hyperlinks.Hyperlink} - The hyperlink instance shown.
 */
ko.hyperlinks.RegexHandler.prototype.show = function(view, scimoz, position, line,
                                            lineStartPos, lineEndPos, reason)
{
    var match = this.findRegex.exec(line);
    var start = lineStartPos;
    var end;
    while (match) {
        this.regex_match = match;
        //dump("RegexHandler:: '" + this.name + "' matched: " + match[0] + "\n");
        // The match must overlap the given position.
        start += ko.stringutils.bytelength(line.substr(0, match.index));
        if (start > position) {
            break;
        }
        end = start + ko.stringutils.bytelength(match[0]);
        if (end >= position) {
            var arg = match[0];
            if (this.replace_str) {
                arg = arg.replace(this.findRegex, this.replace_str);
            }
            //dump('Function arg: ' + arg + '\n');
            return this.setHyperlink(view, start, end, [arg]);
        }
        // Move past this match in the line, we'll check for
        // another match with on the rest of the line.
        line = line.substr(match.index + match[0].length);
        start = end;
        match = this.findRegex.exec(line);
    }
    return null;
}

// Add some basic hyperlink handlers.

// XXX: These regex handlers need to become Komodo preference settings.

ko.hyperlinks.addHandler(
    new ko.hyperlinks.RegexHandler(
        "Hyperlinks",
        new RegExp("(https?|ftps?|sftp|scp):[^'\"<>()[\\]\\s]+", "i"),
        ko.browse.openUrlInDefaultBrowser,
        null,  /* Use the found string instead of a replacement. */
        null,  /* All language types */
        Components.interfaces.ISciMoz.INDIC_PLAIN,
        RGB(0x60,0x90,0xff))
);

ko.hyperlinks.addHandler(
    new ko.hyperlinks.RegexHandler(
        "ActiveState bugs",
        new RegExp("chrome:[^'\"<>()[\\]\\s]+", "i"),
        ko.open.URI,
        null,  /* Use the found string instead of a replacement. */
        null   /* All language types */,
        Components.interfaces.ISciMoz.INDIC_PLAIN,
        RGB(0x60,0x90,0xff))
);

ko.hyperlinks.addHandler(
    new ko.hyperlinks.RegexHandler(
        "ActiveState bugs",
        new RegExp("bug\\s+(\\d{4,5})", "i"),
        ko.browse.openUrlInDefaultBrowser,
        "http://bugs.activestate.com/show_bug.cgi?id=$1",
        null   /* All language types */,
        Components.interfaces.ISciMoz.INDIC_PLAIN,
        RGB(0x60,0x90,0xff))
);
