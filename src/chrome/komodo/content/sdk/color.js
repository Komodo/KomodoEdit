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

/**
 * @module color
 */

/**
 * Parses hex string to a consistent format
 * 
 * @param   {String} hexstring
 * 
 * @returns {String}
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
 * WARNING: This actually returns a BGR value which works fine for
 * Scintilla, but won't work for most other targets.
 *
 * Convert separate r,g,b values into a long int.
 *
 * @deprecated since Komodo 9
 * 
 * @param {Long} red
 * @param {Long} green
 * @param {Long} blue
 *
 * @return {Long} color value
 */
exports.RGB = function(r,g,b) {
    require("ko/logging").getLogger("color")
	.deprecated("RGB is deprecated - use RGBToBGR() instead")
    return exports.BGRToLong(b,g,r);
}

/**
 * Convert separate r,g,b values, or a hex string, into a long int.
 *
 * @param {Long} red
 * @param {Long} green
 * @param {Long} blue
 *
 * @return {Long} color value
 */
exports.RGBToLong = function(r, g, b)
{
    if (typeof(value) == "string") {
        return exports.hexToLong(value);
    }
    return (r << 16) + (g << 8) + b;
}

/**
 * Convert separate b,g,r values into a long int.
 *
 * @param {Long} blue
 * @param {Long} green
 * @param {Long} red
 *
 * @return {Long} color value
 */
exports.BGRToLong = function(b, g, r) {
    return exports.RGBToLong(b, g, r);
}

/**
 * Convert rgb color value (a long, hex string, or separate r,g,b arguments) into a bgr long int.
 *
 * @param {Long|String} color value, hex string, or red component if using r,g,b arguments
 * @param {Long} green
 * @param {Long} blue
 *
 * @return {Long} color value
 */
exports.RGBToBGR = function(value)
{
    if (arguments.length == 3) {
	return exports.RGBToBGR(exports.RGBToLong.apply(this, arguments));
    }
    if (typeof(value) == "string") {
        value = exports.hexToLong(value);
    }
    return ((value & 0xFF0000) >> 16) +
	    (value & 0x00FF00) +
	   ((value & 0xFF) << 16);
}

/**
 * Convert bgr color value (a long, hex string, or separate r,g,b arguments) into a rgb long int.
 *
 * @param {Long|String} color value, hex string, or red component if using r,g,b arguments
 * @param {Long} green
 * @param {Long} blue
 *
 * @return {Long} color value
 */
exports.BGRToRGB = exports.RGBToBGR

/**
 * Converts a hexadecimal string color of the form #ffaabb to a long
 *
 * @param {String} hexstring
 * @return {Long} color value
 */
exports.hexToLong =function(hexstring) {
    hexstring = StandardizeHexString(hexstring);
    var r, g, b;
    r = parseInt(hexstring.substring(1, 3), 16);
    g = parseInt(hexstring.substring(3, 5), 16);
    b = parseInt(hexstring.substring(5, 7), 16);
    return exports.RGBToLong(r, g, b);
}

/**
 * Converts an integer into hexadecimal string color of the form #ffaabb.
 *
 * @param {Long} color value
 * @return {String} hexstring
 */
exports.longToHex =function(value) {
    return "#" + ("0" + ((value & 0xFF0000) >> 16).toString(16)).slice(-2) +
		 ("0" + ((value &   0xFF00) >>  8).toString(16)).slice(-2) +
		 ("0" + ((value &   0xFF)   >>  0).toString(16)).slice(-2);
}

/**
 * Note: Scintilla colors are BGR longs.
 */
exports.scintilla_yellow = exports.RGBToBGR(0xff, 0xff, 0x00);
exports.scintilla_red = exports.RGBToBGR(0xff, 0x00, 0x00);
exports.scintilla_green = exports.RGBToBGR(0x00, 0xff, 0x00);
exports.scintilla_blue = exports.RGBToBGR(0x00, 0x00, 0xff);
exports.scintilla_black = exports.RGBToBGR(0x00, 0x00, 0x00);
exports.scintilla_white = exports.RGBToBGR(0xff, 0xff, 0xff);

/**
 * @deprecated since Komodo 9.0
 */
Object.defineProperty(exports, "yellow", {
    get: function() {
	require("ko/logging").getLogger("color")
	    .deprecated("yellow is deprecated - use scintilla_yellow instead");
	return exports.scintilla_yellow;
    }
});
Object.defineProperty(exports, "red", {
    get: function() {
	require("ko/logging").getLogger("color")
	    .deprecated("red is deprecated - use scintilla_red instead");
	return exports.scintilla_red;
    }
});
Object.defineProperty(exports, "green", {
    get: function() {
	require("ko/logging").getLogger("color")
	    .deprecated("green is deprecated - use scintilla_green instead");
	return exports.scintilla_green;
    }
});
Object.defineProperty(exports, "blue", {
    get: function() {
	require("ko/logging").getLogger("color")
	    .deprecated("blue is deprecated - use scintilla_blue instead");
	return exports.scintilla_blue;
    }
});
Object.defineProperty(exports, "black", {
    get: function() {
	require("ko/logging").getLogger("color")
	    .deprecated("black is deprecated - use scintilla_black instead");
	return exports.scintilla_black;
    }
});
Object.defineProperty(exports, "white", {
    get: function() {
	require("ko/logging").getLogger("color")
	    .deprecated("white is deprecated - use scintilla_white instead");
	return exports.scintilla_white;
    }
});

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
    var [r,g,b] = [parseInt(hexstring.slice(0, 2), 16),
                       parseInt(hexstring.slice(2, 4), 16),
                       parseInt(hexstring.slice(4, 6), 16)];
    var hsv = exports.rgb2hsv(r,g,b);
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

/**
 * Returns an array of n distinct (and optionally random) colors in integer
 * format: 0x0AF088
 * 
 * The colors generated will be random, if you want the colors to be a
 * consistent order, pass in a 'rand' float between [0..1].
 *
 * @argument {int}   n     - The number of colors to create.
 * @argument {float} rand  - The optional starting random number.
 *
 * @returns {array} of integers.
 */
exports.create_n_distinct_colors = function(n, rand) {
    // Generate N distinct (optionally random) colors.
    // http://martin.ankerl.com/2009/12/09/how-to-create-random-colors-programmatically/
    const golden_ratio_conjugate = 0.618033988749895;
    if (typeof(rand) == "undefined" || rand === null) {
        rand = Math.random() // use random start value
    }
    var h = rand;
    var colors = [];
    for (var i=0; i < n; i++) {
        h += golden_ratio_conjugate;
        h %= 1;
	colors.push(exports.RGBToLong.apply(this, exports.hsv2rgb(h, 0.5, 0.95)));
    }
    return colors;
}
