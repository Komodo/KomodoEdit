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

/**
 * This module defines how Scintilla markers are used in Komodo.
 * http://www.scintilla.org/ScintillaDoc.html#Markers
 *
 * Marker are the images in the editor gutter for things like bookmarks,
 * breakpoints. Also line background color for current line, current line in a
 * debugger session, etc.
 */
ko.markers =  function markers_module() {
    // private vars
    var content_cache = {};
    
    return {
    
    // Marker numbers.
    // Most of the ISciMoz.marker*() methods take a marker number argument.
    // The higher the marker number the higher the marker's z-order.
    // Here are the marker numbers that Komodo uses.
    // Note: These numbers *must* match the corresponding values used in
    //       src/koRunTerminal.py.

    // 25-31 are dedicated to folding
    // 22-24 are dedicated to tracking (insert, delete, modify)
    MAX_MARKNUM: 13,
    MARKNUM_HISTORYLOC: 13,
    MARKNUM_STDERR: 12, // used in terminal view
    MARKNUM_STDOUT: 11, // used in terminal view
    MARKNUM_CURRENT_LINE_BACKGROUND: 10,
    MARKNUM_STDIN_PROMPT: 9, // used in terminal view
    MARKNUM_INTERACTIVE_PROMPT_MORE: 8, // used in interactive shell
    MARKNUM_INTERACTIVE_PROMPT: 7, // used in interactive shell
    MARKNUM_BOOKMARK: 6,
    MARKNUM_TRANSIENTMARK: 0, // used in buffer view
    
    /**
     * Read a file from disk, cache and return the contents.
     *
     * @param {String} uri file uri
     * @param {boolean} force force read from file
     * 
     * Note: The file contents are cached by URI.
     * This is used to load pixmaps for scintilla markers.
     */
    getPixmap: function(uri, force) {
        if (!force && typeof(content_cache[uri]) != 'undefined') {
            return content_cache[uri];
        }
        var file = Components.classes["@activestate.com/koFileEx;1"]
                .createInstance(Components.interfaces.koIFileEx)
        file.URI = uri;
        file.open('rb');
        content_cache[uri] = file.readfile();
        file.close();
        return content_cache[uri];
    },

    /**
     * Asynchronously load an image (e.g. png), cache the result and run the
     * given callback with the image details.
     *
     * @param {String} uri file uri
     * 
     * Note: The file contents are cached by URI.
     */
    getImageDataAsync: function(uri, callback) {
        if (uri in content_cache) {
            var cache_entry = content_cache[uri];
            if (cache_entry[0] == "pending") {
                cache_entry[1].push(callback);
                return;
            }
            // It's already loaded - fire the callback now.
            callback.apply(ko.markers, content_cache[uri]);
        }

        // Make note that this image is pending.
        content_cache[uri] = ["pending", [callback]];

        // Load the image so we can get it's size and data.
        var image = new Image();
        // Make it hidden.
        image.setAttribute("hidden", "true");
        image.onload = function(event) {
            try {
                var width = image.naturalWidth;
                var height = image.naturalHeight;
                var ctx = document.createElementNS("http://www.w3.org/1999/xhtml", "canvas").getContext("2d");
                ctx.width = width;
                ctx.height = height;
                ctx.drawImage(image, 0, 0);
                var data = ctx.getImageData(0, 0, width, height).data;
                // Turn data into a string
                data = [String.fromCharCode(x) for (x of data)].join("");
                // Cache the result and run all callbacks.
                var callbacks = content_cache[uri][1];
                content_cache[uri] = [width, height, data];
                for (var i=0; i < callbacks.length; i++) {
                    callbacks[i](width, height, data);
                }
            } finally {
                document.documentElement.removeChild(image);
            }
        }
        image.src = uri;
        // Have to add the image to the document in order to have it load.
        document.documentElement.appendChild(image);
    },

    /**
     * Setup the standard Komodo markers in the given SciMoz instance and
     * return an appropriate mask for ISciMoz.setMarginMaskN(<n>, <mask>).
     * 
     * @param {Components.interfaces.ISciMoz} scimoz - A plugin instance.
     * @param {Boolean} isDarkBackground - whether scimoz is using a dark bg.
     */
    setup: function(scimoz, isDarkBackground) {
        var color;
        if (typeof(require) == "function") {
            color = require("ko/color");
        } else {
            ko.logging.getLogger("markers.js").warn("Include globals.js for require functionality");
            xtk.include("color");
            color = xtk.color;
        }
        scimoz.markerDefine(ko.markers.MARKNUM_BOOKMARK, scimoz.SC_MARK_ARROWDOWN);
        scimoz.markerSetFore(ko.markers.MARKNUM_BOOKMARK, color.RGBToBGR(0x00, 0x00, 0x00)); // black
        scimoz.markerSetBack(ko.markers.MARKNUM_BOOKMARK, color.RGBToBGR(0x00, 0xFF, 0xFF)); // cyan
    
        scimoz.markerDefine(ko.markers.MARKNUM_STDIN_PROMPT, scimoz.SC_MARK_CHARACTER+'%'.charCodeAt(0));
        scimoz.markerSetFore(ko.markers.MARKNUM_STDIN_PROMPT, color.scintilla_red);
        scimoz.markerDefine(ko.markers.MARKNUM_STDOUT, scimoz.SC_MARK_EMPTY);
        scimoz.markerDefine(ko.markers.MARKNUM_STDERR, scimoz.SC_MARK_EMPTY);
        scimoz.markerDefine(ko.markers.MARKNUM_HISTORYLOC, scimoz.SC_MARK_EMPTY);
        scimoz.markerDefine(ko.markers.MARKNUM_TRANSIENTMARK, scimoz.SC_MARK_EMPTY);
    
        return ko.markers.MARKERS_MASK_SYMBOLS;
    }
    };

}();

// Include all markers *except* MARKNUM_CURRENT_LINE_BACKGROUND, as the
// background marker is handled independently.
// - Want the Nth bitfield for marker N to be set iff that marker should
//   be visible in the symbol margin.
ko.markers.MARKERS_MASK_SYMBOLS = ((1 << (ko.markers.MAX_MARKNUM+1)) - 1) ^ (1 << ko.markers.MARKNUM_CURRENT_LINE_BACKGROUND);
