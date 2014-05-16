/**
 * Copyright (c) 2006-2014 ActiveState Software Inc.
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Contributors:
 *   Todd Whiteman <toddw@activestate.com>
 *   Shane Caraveo <shanec@activestate.com>
 */

/**
 * Common functions for color processing
 */

function StandardizeHexString(hexstring) {
    if (!hexstring.startsWith("#") || (hexstring.length != 4 && hexstring.length != 7)) {
        throw Error("Invalid hex color string '" + hexstring + "', expected a string in the form: '#abc' or '#aabbcc'");
    }
    if (hexstring.length == 4) {
        return "#" + hexstring[1] + hexstring[1] +
                     hexstring[2] + hexstring[2] +
                     hexstring[3] + hexstring[3];
    }
    return hexstring;
}

/**
 * RGB
 *
 * convert rgb value into a long int
 *
 * WARNING: This actually returns a BGR value which works fine for
 * Scintilla, but won't work for most other targets.
 *
 * @param {Long} red
 * @param {Long} green
 * @param {Long} blue
 * @return {Long} color value
 */
exports.RGB = function(r,g,b) {
    return r + g * 256 + b * 256 * 256;
}

/**
 * hexToLong
 *
 * Converts a hexadecimal string color of the form #ffaabb to a long
 *
 * @param {String} hexstring
 * @return {Long} color value
 */
exports.hexToLong =function(hexstring) {
    hexstring = StandardizeHexString(hexstring);
    try {
        var r, g, b;
        r = parseInt(hexstring.substring(1, 3), 16);
        g = parseInt(hexstring.substring(3, 5), 16);
        b = parseInt(hexstring.substring(5, 7), 16);
        return exports.RGB(r, g, b);
    } catch (e) {
        require("ko/logging").getLogger("color").exception(e);
    }
    return null;
}

/**
 * BGR
 *
 * Converts a hexadecimal string color of the form #ffaabb to #bbaaff.
 *
 * @param {String} hexstring
 * @return {String} hexstring
 */
exports.BGR =function(hexstring) {
    hexstring = StandardizeHexString(hexstring);
    try {
        return "#" + hexstring.substring(5, 7) +
                     hexstring.substring(3, 5) +
                     hexstring.substring(1, 3);
    } catch (e) {
        require("ko/logging").getLogger("color").exception(e);
    }
    return null;
}

exports.yellow = exports.RGB(0xff, 0xff, 0x00);
exports.red = exports.RGB(0xff, 0x00, 0x00);
exports.green = exports.RGB(0x00, 0xff, 0x00);
exports.blue = exports.RGB(0x00, 0x00, 0xff);
exports.black = exports.RGB(0x00, 0x00, 0x00);
exports.white = exports.RGB(0xff, 0xff, 0xff);

// Functions for converting a scale between 0 and 1
// into a web RGB value.
// Adapted from Bill Chadwick's http://www.bdcc.co.uk/Gmaps/Rainbow.js
// That code is under no license, claims no copyright.

exports.scaler = function() {
    this.gamma = 0.8;
    this.brightness = 0.9;  // must be between 0.0 and 1.0 inclusive
    // Chadwick uses 645.  Using 780 causes a range of 1
    // to show up as black.
    this.topScale = 680.0
}

exports.scaler.prototype.Adjust = function(color, factor) {
    // determine the color intensity
    return Math.floor(255.0 * Math.pow(color * factor * this.brightness, this.gamma));
}

exports.scaler.prototype.NanometerToRGB = function(nanoMetres) {
    var Red = 0.0;
    var Green = 0.0;
    var Blue = 0.0;
    var factor = 0.0;
            
    if (nanoMetres < 510) {
        if (nanoMetres >= 490) {
            // Cyan to green
            Green = 1.0;
            Blue  = (510.0 - nanoMetres) / (510.0 - 490.0);
        } else {
            Blue = 1.0;            
            if (nanoMetres >= 440) {
                // Blue to cyan
                Green = (nanoMetres - 440.0) / (490.0 - 440.0);
            } else {
                // Ultra-violet to blue
                Red  = (440.0 - nanoMetres) / (440.0 - 380.0);
            }
        }
    } else if (nanoMetres < 580) {
        // Green to yellow-orange
        Green = 1.0;
        Red  = (nanoMetres - 510.0) / (580.0 - 510.0);
    } else {
        // Yellow-orange to full red
        Red = 1.0;
        Green = (nanoMetres < 644 ?
                 (645.0 - nanoMetres) / (645.0 - 580.0) : 0.0);
    }
    
    // Condition RGB according to limits of vision
    if (nanoMetres <= 700) {
        factor = ((nanoMetres >= 420) ? 1.0 :
                  (0.3 + (0.7 * (nanoMetres - 380.0)
                           / (420.0 - 380.0))));
    } else {
	factor = ((nanoMetres <= 780.0) ?
		  0.3 + 0.7 * (780.0 - nanoMetres) / (780.0 - 700.0) :
		  0.0);
    }

    Red = this.Adjust(Red, factor);
    Green = this.Adjust(Green, factor);
    Blue = this.Adjust(Blue, factor);

    var r = "#";
    if(Red < 16)
	    r += "0";
    r += Red.toString(16);

    if(Green < 16)
	    r += "0";
    r += Green.toString(16);

    if(Blue < 16)
	    r += "0";
    r += Blue.toString(16);

    return r;
}

//pass in a number between 0 and 1 to get a color between Violet and Red
exports.scaler.prototype.scaleToRGB = function(w) {
    return this.NanometerToRGB(Math.round(380.0 + (w * (this.topScale - 380.0))));
}

/**
 * Return whether this is a dark color.
 * @param {string} hexstring - Hexadecimal string of the color.
 * @returns {Boolean}
 */
exports.isDark = function color_isDark(hexstring) {
    if (hexstring[0] == "#") {
        hexstring = hexstring.slice(1);
    }
    if (hexstring.length == "3") {
        // Support short hex strings like "fff"
        hexstring = hexstring[0] + hexstring[0] +
                    hexstring[1] + hexstring[1] +
                    hexstring[2] + hexstring[2];
    }
    var color_parts = [parseInt(hexstring.slice(0, 2), 16),
                       parseInt(hexstring.slice(2, 4), 16),
                       parseInt(hexstring.slice(4, 6), 16)];
    var hsv = exports.rgb2hsv(color_parts);
    return hsv[2] <= 0.5;
}

/**
 * Return whether this is a light color.
 * @param {string} hexstring - Hexadecimal string of the color.
 * @returns {Boolean}
 */
exports.isLight = function color_isLight(hexstring) {
    return !(exports.isDark(hexstring));
}

exports.rgb2hsv = function(r, g, b) {
    // Algorithm in taken from http://en.wikipedia.org/wiki/HSL_and_HSV
    // Code adapted from C code found at http://search.cpan.org/~tonyc/Imager-0.98/
    // Licensed under the Artistic License (1)
    // http://dev.perl.org/licenses/artistic.html
    // This method, and h2v2rgb below adapted for JS from C by EP
    //
    // Input: 3 integers, representing r,g,b, each in [0 .. 255]
    // Output: Array of float in [0 .. 1)
    if ([r, g, b].some(function(c) c < 0 || c > 255)) {
        throw new Error("color.rgb2hsv: input '" + [r, g, b] + "' not three values in 0:255");
    }
    [r, g, b] = [r, g, b].map(function(c) c / 255.0);
    const minRGB = Math.min(r, g, b);
    const maxRGB = Math.max(r, g, b);
    if (minRGB == maxRGB) {
        return [0, 0, minRGB]; // neutral/grey, sat and hue both 0
    }
    const colorSpan = maxRGB - minRGB;
    const cR = (maxRGB - r)/colorSpan;
    const cG = (maxRGB - g)/colorSpan;
    const cB = (maxRGB - b)/colorSpan;
    var h;
    if (maxRGB == r) {
       h = cB - cG;
    } else if (maxRGB == g) {
       h = 2 + cR - cB;
    } else {
        h = 4 + cG - cR;
    }
    h *= 60;
    if (h < 0) {
        h += 360;
    }
    const H = h/360.0;
    const S = colorSpan / maxRGB;
    const V = maxRGB;
    return [H, S, V];
};

exports.hsv2rgb = function(h, s, v) {
    // Input: 3 values in [0 .. 1]
    // Output: 3 integers in [0 .. 255] representing an RGB value.
    if ([h, s, v].some(function(c) c < 0 || c >= 1)) {
        throw new Error("color.rgb2hsv: input '" + [h, s, v] + "' not three values in [0 .. 1)");
    }
    if (s == 0) {
        return [v, v, v];
    }
    h *= 6;
    const i = Math.floor(h);
    const f = h - i;
    const m = v * (1 - s);
    const n = v * (1 - s * f);
    const k = v * (1 - s * (1 - f));
    var r, g, b;
    switch(i) {
        case 0:
           [r, g, b] = [v, k, m];
           break;
        case 1:
           [r, g, b] = [n, v, m];
           break;
        case 2:
           [r, g, b] = [m, v, k];
           break;
        case 3:
           [r, g, b] = [m, n, v];
           break;
        case 4:
           [r, g, b] = [k, m, v];
           break;
        default:
           [r, g, b] = [v, m, n];
           break;
    }
    return [r, g, b].map(function(c) Math.round(c * 255));
}
