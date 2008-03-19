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
    // Note: These numbers *must* match the correstponding values used in
    //       src/koRunTerminal.py.
    MARKNUM_STDERR: 12, // used in terminal view
    MARKNUM_STDOUT: 11, // used in terminal view
    MARKNUM_CURRENT_LINE_BACKGROUND: 10,
    MARKNUM_STDIN_PROMPT: 9, // used in terminal view
    MARKNUM_BOOKMARK: 6,
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
