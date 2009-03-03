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
 * A goto defintion hyperlink handler.
 *
 * @class
 * @base ko.hyperlinks.BaseHandler
 */
ko.hyperlinks.GotoDefinitionHandler = function() {
    var name = "Goto Defintion";
    var fn = function(args) {
        ko.views.manager.do_cmd_goToDefinition.apply(null, args);
    };
    var lang_names = null;  /* All language types */
    var indic_style = Components.interfaces.ISciMoz.INDIC_PLAIN;
    //var indic_color = RGB(0xff,0x80,0x20);
    var indic_color = RGB(0xA0,0x00,0xF0);
    var base_args = [name, fn, lang_names, indic_style, indic_color];
    ko.hyperlinks.BaseHandler.apply(this, base_args);
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
ko.hyperlinks.GotoDefinitionHandler.prototype = new ko.hyperlinks.BaseHandler();
ko.hyperlinks.GotoDefinitionHandler.prototype.constructor = ko.hyperlinks.GotoDefinitionHandler;

/**
 * Try and show a hyperlink at the current position in the view.
 *
 * @param view {Components.interfaces.koIScintillaView}  View to check.
 * @param scimoz {Components.interfaces.ISciMoz}  Scimoz for the view.
 * @param pos {int}  Position in the scimoz editor.
 * @param line {string}  The current line from the editor.
 * @param lineStartPos {int} Scimoz position for the start of the line.
 * @param lineEndPos {int}   Scimoz position for the end of the line.
 * @returns {ko.hyperlinks.Hyperlink} - The hyperlink instance shown.
 */
ko.hyperlinks.GotoDefinitionHandler.prototype.show = function(
                view, scimoz, position, line, lineStartPos, lineEndPos)
{
    // For goto definition, if this view does not support codeintel
    // citadel stuff, then goto definition is not supported and
    // there is no need to mark any hyperlinks.
    if (!view.isCICitadelStuffEnabled) {
        return null;
    }

    var start = scimoz.wordStartPosition(position, true);
    var end = scimoz.wordEndPosition(position, true);
    if (start < end) {
        var next_start;
        while (1) {
            next_start = scimoz.wordStartPosition(start, false);
            if (next_start < start) {
                // XXX: This needs to use language specific separators.
                if ([".", "->", "::"].indexOf(scimoz.getTextRange(next_start, start)) >= 0) {
                    start = scimoz.wordStartPosition(next_start, true);
                    continue;
                }
            }
            break;
        }
        return this.setHyperlink(view, start, end);
    }
    return null;
}

ko.hyperlinks.addHandler(new ko.hyperlinks.GotoDefinitionHandler());
