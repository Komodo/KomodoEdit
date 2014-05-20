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
    var find_regex = /#(([0-9a-f]{3}){1,2})\b|(rgba?|hsla?)\(\s*(\d+\%?)\s*,\s*(\d+\%?)\s*,\s*(\d+\%?)\s*(,\s*(\d|\d?\.\d+)\s*)?\)/i;
    var fn = null;   /* unnecessary, as it's over-riden by the "jump" method */
    var replace_str = null;
    var lang_names = ["CSS", "Less", "SCSS", "HTML", "HTML5"];   /* Language types */
    //var indic_style = Components.interfaces.ISciMoz.INDIC_ROUNDBOX;
    var indic_style = Components.interfaces.ISciMoz.INDIC_PLAIN;
    var indic_color = require("ko/color").RGBToBGR(0xd0,0x40,0xff);
        
    var regex_args = [name, find_regex, fn, replace_str, lang_names, indic_style, indic_color];
    ko.hyperlinks.RegexHandler.apply(this, regex_args);
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
ko.hyperlinks.ColorPickerHandler.prototype = new ko.hyperlinks.RegexHandler();
ko.hyperlinks.ColorPickerHandler.prototype.constructor = ko.hyperlinks.ColorPickerHandler;

ko.hyperlinks.ColorPickerHandler.named_css_colors = [
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "black",
    "blanchedalmond",
    "blue",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgreen",
    "darkgrey",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkslategrey",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dimgrey",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "gold",
    "goldenrod",
    "gray",
    "green",
    "greenyellow",
    "grey",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgray",
    "lightgreen",
    "lightgrey",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightslategrey",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orange",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "purple",
    "red",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "slategrey",
    "snow",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "white",
    "whitesmoke",
    "yellow",
    "yellowgreen"
];

/**
 * Try and show a hyperlink at the current position in the view.
 *
 * @param view {Components.interfaces.koIScintillaView}  View to check.
 * @param scimoz {Components.interfaces.ISciMoz}  Scimoz for the view.
 * @param {int} pos  Position in the scimoz editor.
 * @param {string} line  The current line from the editor.
 * @param {int} lineStartPos Scimoz position for the start of the line.
 * @param {int} lineEndPos   Scimoz position for the end of the line.
 * @param {string} reason  What the triggering event reason was, can be one
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
        (ko.hyperlinks.ColorPickerHandler.named_css_colors.indexOf(scimoz.getTextRange(start, end).toLowerCase()) >= 0)) {
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
            // Windows can go either way, though the "tooltip" gives a
            // nicer looking border.
            // For the Mac, it's better as a "tooltip", otherwise there can be
            // problems clicking on the hyperlink whilst the color swatch is
            // shown.
            popup = document.createElement('tooltip');
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
        if (color.substr(0, 4) == "rgba" || color.substr(0, 3) == "hsl") {
            div.style.background = color;
        } else {
            color = this.colorToHex(color);
            div.style.background = color;
        }

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
 * @param {string} reason  What the triggering event reason was, can be one
 *        of "keyup", "mousemove", "mouseup" or "blur".
 */
ko.hyperlinks.ColorPickerHandler.prototype.remove = function(view, hyperlink, reason)
{
    ko.hyperlinks.RegexHandler.prototype.remove.apply(this, arguments);
    var popup = document.getElementById("colorpicker_swatch_popup");
    if (popup) {
        popup.hidePopup();
    }
    return true;
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
    this.showColorPicker(view, hyperlink);
}

/**
 * Convert a CSS color specification to hexidecimal representation
 *
 * @param   {String} color Any CSS color value
 *
 * @returns {String} A color, as "#nnnnnn" (no alpha, leading hash)
 */
ko.hyperlinks.ColorPickerHandler.prototype.colorToHex = function(color) {
    // If color is not in hexa format (#XXXXXX, #XXX with/without hash)
    // convert the color to hexa format before passing it to color picker
    return this.constructor.rgb2hex(this.colorToRGB(color));
}

/**
 * Convert a CSS color specification to rgb() representation
 *
 * @param   {String} color Any CSS color value
 *
 * @returns {String} A color, as "rgb(x,x,x)" or "rgba(x,x,x,x)".
 */
ko.hyperlinks.ColorPickerHandler.prototype.colorToRGB = function(color) {
    var span = document.createElement('span');
    span.style.color = color;
    return window.getComputedStyle(span, null).color;
}

ko.hyperlinks.ColorPickerHandler.prototype.showColorPicker = function(view, hyperlink) {
    var scimoz = view.scimoz;
    var oldcolor = scimoz.getTextRange(hyperlink.startPos, hyperlink.endPos);
    var colors = this.constructor._rgbToComponents(this.colorToRGB(oldcolor));
    var alpha = colors.pop();
    var color = "#" + colors.map(function(x) ("00" + x.toString(16)).substr(-2))
                            .join("");

    // This function must be called in a setTimeout for the Mac, otherwise
    // the scimoz editor does not receive the mouseup event, which results
    // in Komodo scrolling/selecting text when the mouse if moved over the
    // just opened color picker dialog.
    window.setTimeout((function() {
        var sysUtils = Components.classes['@activestate.com/koSysUtils;1'].
                        getService(Components.interfaces.koIColorPickerAsync);
        var [x, y] = view._last_mousemove_xy;
        // The X and Y positions are relative to the scimoz top-left corner,
        // but we need screen positions.
        x += view.boxObject.screenX;
        y += view.boxObject.screenY;
        var callback = (function callback(newcolor, newalpha) {
            if (!newcolor) {
                // user cancelled
                return;
            }
            // convert colors to an array of [r, g, b]
            var colors = this.constructor._rgbToComponents(newcolor).slice(0, 3);
            if (newalpha < 1.0) {
                // alpha required; only rgba() works
                newcolor = "rgba(" + colors.concat([newalpha]).join(", ") + ")";
            } else {
                if (/^rgb/.test(oldcolor)) {
                    // previously "rgb()" or "rgba()", use rgb()
                    newcolor = "rgb(" + colors.join(", ") + ")";
                } else {
                    // it didn't used to be rgb(); prefer the #xxxxxx form
                    // (this also covers color names like "red" and "cornsilk")
                    // (do nothing, this is what we got as the first argument)
                }
            }
            scimoz.targetStart = hyperlink.startPos;
            scimoz.targetEnd = hyperlink.endPos;
            scimoz.replaceTarget(newcolor.length, newcolor);
            // replaceTarget has moved the cursor to the start of the inserted
            // color; move cursor position to end of the inserted color instead.
            // Note: currentPos is a byte offset, so we need to correct the length
            var newCurrentPos = scimoz.currentPos + ko.stringutils.bytelength(newcolor);
            scimoz.currentPos = newCurrentPos;
            // Move the anchor as well, so we don't have a selection
            scimoz.anchor = newCurrentPos;
        }).bind(this);
        sysUtils.pickColorAsync(callback, color, alpha, x, y);
    }).bind(this), 1);
}

/**
 * Convert a CSS rgb() color string to an array of [r, g, b, a]
 *
 * @param   {String} rgb_color The rgb() / rgba() string
 *
 * @returns {Array} Array of colors, as [r, g, b, a]; r, g, and b are the color
 *      components as integers between 0 and 255 inclusive; a is the alpha value
 *      as a double between 0.0 and 1.0 inclusive.  If there was an error
 *      parsing the number, returns null.
 */
ko.hyperlinks.ColorPickerHandler._rgbToComponents = function(rgb_color)
{
    if (/^#?[0-9a-f]{6}$/i.test(rgb_color)) {
        // the color was a hex string. eh, deal with it anyway
        rgb_color = rgb_color.replace(/^#/, "");
        var result = [];
        for (var i = 0; i <= rgb_color.length - 2; i += 2) {
            result.push(parseInt(rgb_color.substr(i, 2), 16));
        }
        if (result.length > 3) {
            result[3] /= 255.0; // alpha is between 0 and 1
        } else {
            result[3] = 1.0; // assume opaque
        }
        return result;
    }
    if (/\w\s+\w/.test(rgb_color)) {
        // contains words separated by space; this is never right for rgb()
        return null;
    }
    // strip whitespace, easier to deal with
    rgb_color = rgb_color.replace(/\s+/g, '');
    // match rgb(0, 0, 0) or rgba(0, 0, 0, 0)
    if (!/^rgba?\((?:\d+%?,){2}(?:\d+%?)(?:,[0-9.]+)?\)$/i.test(rgb_color)) {
        // not an rgb() / rgba() color
        return null;
    }
    // ["rgb" / "rgba", red, green, blue, alpha?]
    var colors = Array.slice(rgb_color.split(/[(,)]/), 0, -1);
    var type = colors.shift();
    if (type.length != colors.length) {
        // not "rgb", [0,0,0] / "rgba", [0,0,0,0]; malformed.
        return null;
    }
    var alpha = 1.0;
    if (type == "rgba") {
        alpha = parseFloat(colors.pop());
        if (!(alpha >= 0.0 && alpha <= 1.0)) {
            return null; // out of bounds or parse error
        }
    }
    for each (var [i, color] in Iterator(colors)) {
        if (/%$/.test(colors[i])) {
            color = parseFloat(color) * 2.55 >>> 0; // force integer
        } else {
            color = parseInt(color, 10);
        }
        if (!(color >= 0 && color <= 255)) {
            return null; // out of bounds or parse error
        }
        colors[i] = color;
    }
    return colors.concat([alpha]);
};

/**
 * Convert a CSS rgb() color string to hex "#nnnnnn"
 *
 * @param   {String} rgb_color The rgb() string
 *
 * @returns {String} The equivalent "#nnnnnn" color
 */
ko.hyperlinks.ColorPickerHandler.rgb2hex = function(rgb_color)
{
    var colors = this._rgbToComponents(rgb_color);
    if (colors === null) {
        return "#000000"; // invalid color
    }
    var val, result = "#";
    for (var i = 0; i < 3; ++i) { // NOTE: disgarding alpha
        result += ("00" + colors[i].toString(16)).substr(-2).toLowerCase();
    }
    return result;
}

ko.hyperlinks.handlers.colorPreviewHandler = new ko.hyperlinks.ColorPickerHandler();
ko.hyperlinks.addHandler(ko.hyperlinks.handlers.colorPreviewHandler);
