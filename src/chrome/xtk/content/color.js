/**
 * Copyright (c) 2006,2007 ActiveState Software Inc.
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Contributors:
 *   Shane Caraveo <shanec@activestate.com>
 */

/**
 * Common functions for color processing
 */

if (typeof(xtk) == 'undefined') {
    var xtk = {};
}
xtk.color = {};
(function() {
/**
 * RGB
 *
 * covert rgb value into a long int
 *
 * @param {Long} red
 * @param {Long} green
 * @param {Long} blue
 * @return {Long} color value
 */
this.RGB = function(r,g,b) {
  return r + g * 256 + b * 256 * 256;
}

/**
 * hexToLong
 *
 * Converts a color of the form #ffaabb to a long
 *
 * @param {String} hexstring
 * @return {Long} color value
 */
this.hexToLong =function(hexstring) {
    try {
        var r, g, b;
        r = parseInt(hexstring.substring(1, 3), 16);
        g = parseInt(hexstring.substring(3, 5), 16);
        b = parseInt(hexstring.substring(5, 7), 16);
        return this.RGB(r, g, b);
    } catch (e) {
        xtk.logging.getLogger("xtk.color").exception(e);
    }
    return null;
}

this.yellow = this.RGB(0xff, 0xff, 0x00);
this.red = this.RGB(0xff, 0x00, 0x00);
this.green = this.RGB(0x00, 0xff, 0x00);
this.blue = this.RGB(0x00, 0x00, 0xff);
this.black = this.RGB(0x00, 0x00, 0x00);
this.white = this.RGB(0xff, 0xff, 0xff);

}).apply(xtk.color);
