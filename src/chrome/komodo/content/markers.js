/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
xtk.include("color");

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
    MARKNUM_STDERR: 5, // used in terminal view
    MARKNUM_STDOUT: 4, // used in terminal view
    MARKNUM_CURRENT_LINE_BACKGROUND: 3,
    MARKNUM_STDIN_PROMPT: 2, // used in terminal view
    MARKNUM_BOOKMARK: 1,
    MARKNUM_TRANSIENTMARK: 0, // used in buffer view
    
    // Include all markers *except* MARKNUM_CURRENT_LINE_BACKGROUND.
    // - Want the Nth bitfield for marker N to be set iff that marker should
    //   up in the symbol margin and cleared if the line background should be
    //   colored.
    MARKERS_MASK_SYMBOLS: 0x03FF,
    
    /**
     * Read a file from disk, cache and return the contents.
     *
     * @param uri {String} file uri
     * @param force {boolean} force read from file
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
     * Setup the standard Komodo markers in the given SciMoz instance and
     * return an appropriate mask for ISciMoz.setMarginMaskN(<n>, <mask>).
     * 
     * @param scimoz {iSciMoz} scimoz plugin instsance
     */
    setup: function(scimoz) {
        scimoz.markerDefine(ko.markers.MARKNUM_BOOKMARK, scimoz.SC_MARK_ARROWDOWN);
        scimoz.markerSetFore(ko.markers.MARKNUM_BOOKMARK, xtk.color.RGB(0x00, 0x00, 0x00)); // black
        scimoz.markerSetBack(ko.markers.MARKNUM_BOOKMARK, xtk.color.RGB(0x00, 0xFF, 0xFF)); // cyan
    
        scimoz.markerDefine(ko.markers.MARKNUM_STDIN_PROMPT, scimoz.SC_MARK_CHARACTER+'%'.charCodeAt(0));
        scimoz.markerSetFore(ko.markers.MARKNUM_STDIN_PROMPT, xtk.color.red);
        scimoz.markerDefine(ko.markers.MARKNUM_STDOUT, scimoz.SC_MARK_EMPTY);
        scimoz.markerDefine(ko.markers.MARKNUM_STDERR, scimoz.SC_MARK_EMPTY);
        scimoz.markerDefine(ko.markers.MARKNUM_TRANSIENTMARK, scimoz.SC_MARK_EMPTY);
    
        return ko.markers.MARKERS_MASK_SYMBOLS;
    }
    };

}();
