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
 * A CSS color picker, custom hyperlink handler.
 *
 * @class
 * @base ko.hyperlinks.RegexHandler
 */
ko.hyperlinks.ColorPickerHandler = function()
{
    var name = "Color picker";
    var find_regex = /#(([0-9a-f]{3}){1,2})\b|rgb\(\s*(\d+\%?)\s*,\s*(\d+\%?)\s*,\s*(\d+\%?)\s*\)/i;
    var fn = null;   /* unnecessary, as it's over-riden by the "jump" method */
    var replace_str = null;
    var lang_names = ["CSS", "HTML"];   /* Language types */
    //var indic_style = Components.interfaces.ISciMoz.INDIC_ROUNDBOX;
    var indic_style = Components.interfaces.ISciMoz.INDIC_PLAIN;
    var indic_color = RGB(0xd0,0x40,0xff);
        
    var regex_args = [name, find_regex, fn, replace_str, lang_names, indic_style, indic_color];
    ko.hyperlinks.RegexHandler.apply(this, regex_args);
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
ko.hyperlinks.ColorPickerHandler.prototype = new ko.hyperlinks.RegexHandler();
ko.hyperlinks.ColorPickerHandler.prototype.constructor = ko.hyperlinks.ColorPickerHandler;

ko.hyperlinks.ColorPickerHandler.named_css_colors = [
    "aqua",
    "black",
    "blue",
    "fuchsia",
    "gray",
    "green",
    "lime",
    "maroon",
    "navy",
    "olive",
    "purple",
    "red",
    "silver",
    "teal",
    "white",
    "yellow",
];

/**
 * Try and show a hyperlink at the current position in the view.
 *
 * @param view {Components.interfaces.koIScintillaView}  View to check.
 * @param scimoz {Components.interfaces.ISciMoz}  Scimoz for the view.
 * @param pos {int}  Position in the scimoz editor.
 * @param line {string}  The current line from the editor.
 * @param lineStartPos {int} Scimoz position for the start of the line.
 * @param lineEndPos {int}   Scimoz position for the end of the line.
 * @param reason {string}  What the triggering event reason was, can be one
 *        of "keypress" or "mousemove".
 * @returns {ko.hyperlinks.Hyperlink} - The hyperlink instance shown.
 */
ko.hyperlinks.ColorPickerHandler.prototype.show = function(
                view, scimoz, position, line, lineStartPos, lineEndPos, reason)
{
    var start = scimoz.wordStartPosition(position, true);
    var end = scimoz.wordEndPosition(position, true);
    var hyperlink;
    // Check if it's a named css color, else try the regex matching.
    if ((start < end) &&
        (ko.hyperlinks.ColorPickerHandler.named_css_colors.indexOf(scimoz.getTextRange(start, end)) >= 0)) {
        hyperlink = this.setHyperlink(view, start, end, null);
    } else {
        hyperlink = ko.hyperlinks.RegexHandler.prototype.show.apply(this, arguments);
    }

    if (hyperlink) {
        // Show a color swatch element (as well as the hyperlink).
        var popup = document.getElementById("colorpicker_swatch_popup");
        var div;
        if (popup == null) {
            var os_prefix = window.navigator.platform.substring(0, 3).toLowerCase();
            // This swatch element works better as a "tooltip" on Linux, as the
            // "popup" element causes mouse cursor flickering on mouseover.
            // For the Mac, it's better as a "panel", otherwise there can be
            // focus issues causing the popup to stop moving around.
            // Windows can go either way, though the "tooltip" gives a
            // nicer looking border.
            if (os_prefix == "mac") {
                popup = document.createElement('panel');
                popup.setAttribute("noautofocus", "true");
            } else {
                popup = document.createElement('tooltip');
            }
            popup.setAttribute('id', 'colorpicker_swatch_popup');
            div = document.createElement('div');
            div.setAttribute("id", "colorpicker_swatch");
            div.setAttribute("class", "colorpicker_swatch");
            div.setAttribute("width", "100");
            div.setAttribute("height", "50");
            popup.appendChild(div);
            document.documentElement.appendChild(popup);
        } else {
            div = popup.firstChild;
        }

        var sm = view.scimoz;
        var color = sm.getTextRange(hyperlink.startPos, hyperlink.endPos);
        color = this.colorToHex(color);
        div.style.background = "#" + color;

        var x, y;
        [x,y] = view._last_mousemove_xy;
        popup.openPopup(view, "after_pointer", x, y, false, false);
    }
    return hyperlink;
}

/**
 * Remove this hyperlink instance.
 *
 * @param view {Components.interfaces.koIScintillaView}  The view instance.
 * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
 * @param reason {string}  What the triggering event reason was, can be one
 *        of "keyup", "mousemove", "mouseup" or "blur".
 */
ko.hyperlinks.ColorPickerHandler.prototype.remove = function(view, hyperlink, reason)
{
    ko.hyperlinks.RegexHandler.prototype.remove.apply(this, arguments);
    var popup = document.getElementById("colorpicker_swatch_popup");
    if (popup) {
        popup.hidePopup();
    }
}

/**
 * Activate this hyperlink instance.
 *
 * @param view {Components.interfaces.koIScintillaView}  The view instance.
 * @param hyperlink {ko.hyperlinks.Hyperlink} The hyperlink instance.
 */
ko.hyperlinks.ColorPickerHandler.prototype.jump = function(view, hyperlink)
{
    // Remove the color swatch tooltip if it's still showing.
    var popup = document.getElementById("colorpicker_swatch_popup");
    if (popup) {
        popup.hidePopup();
    }
    // XXX: This is a hack, used to stop hyperlinks from continuing to be shown
    //      after the color picker window gets closed, as the color picker
    //      window is stealing the keyup events, so the view thinks the ctrl
    //      key is still down. Required on Linux and Mac, Windows doesn't seem
    //      to capture the keypresses but no harm in doing it there as well.
    view.clearKeyDownValues();
    this.showColorPicker(view, hyperlink);
}

ko.hyperlinks.ColorPickerHandler.prototype.colorToHex = function(color) {
    // If color is not in hexa format (#XXXXXX, #XXX with/without hash)
    // convert the color to hexa format before passing it to color picker
    var span = document.createElement('span');
    span.style.color = color;
    var color_rgb = window.getComputedStyle(span, null).color;
    var color_hex = ko.hyperlinks.ColorPickerHandler.rgb2hex(color_rgb);
    delete span;
    return color_hex;
}

ko.hyperlinks.ColorPickerHandler.prototype.showColorPicker = function(view, hyperlink) {
    var scimoz = view.scimoz;
    var color = scimoz.getTextRange(hyperlink.startPos, hyperlink.endPos);
    color = this.colorToHex(color);

    // This function must be called in a setTimeout for the Mac, otherwise
    // the scimoz editor does not receive the mouseup event, which results
    // in Komodo scrolling/selecting text when the mouse if moved over the
    // just opened color picker dialog.
    window.setTimeout(function(view_, hyperlink_, color_) {
        var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
                        getService(Components.interfaces.koISysUtils);
        var x, y;
        [x,y] = view_._last_mousemove_xy;
        // The X and Y positions are relative to the scimoz top-left corner,
        // but we need screen positions.
        x += view_.boxObject.screenX;
        y += view_.boxObject.screenY;
        var newcolor = sysUtils.pickColorWithPositioning("#" + color_, x, y);
        if (newcolor) {
            var sm = view_.scimoz;
            sm.targetStart = hyperlink_.startPos;
            sm.targetEnd = hyperlink_.endPos;
            sm.replaceTarget(newcolor.length, newcolor);
            // Move cursor position to end of the inserted color
            // Note: currentPos is a byte offset, so we need to corrext the length
            var newCurrentPos = sm.currentPos + ko.stringutils.bytelength(newcolor);
            sm.currentPos = newCurrentPos;
            // Move the anchor as well, so we don't have a selection
            sm.anchor = newCurrentPos;
        }
    }, 1, view, hyperlink, color);
}

ko.hyperlinks.ColorPickerHandler.rgb2hex = function(rgb_color)
{
    var match = rgb_color.match(/rgb\((\d+\%?),\s*(\d+\%?),\s*(\d+\%?)\)/i);
    if (!match)
        return "#000000";
    match.shift();
    var val;
    for(var i = 0; i < match.length; ++i) {
        val = parseInt(match[i]);
        if (match[i][match[i].length -1] == "%") {
            val *= 2.55;
        }
        match[i] = (val < 16 ? '0' : '') + val.toString(16).toLowerCase();
    }
   
    return match.join('');
}

ko.hyperlinks.addHandler(new ko.hyperlinks.ColorPickerHandler());
