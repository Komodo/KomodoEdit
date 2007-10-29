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

/* * *
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
