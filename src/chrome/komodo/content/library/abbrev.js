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

/* Abbreviations: insert toolbox snippets by name.
 *
 * See KD 196 (TODO: should move to KIPs).
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.abbrev)=='undefined') {
    ko.abbrev = {};
}

(function() {

/**
 * Expands the abbreviation, if any, at the current cursor position.
 *
 * @param abbrev {String} Optional. The abbreviation to expand. If not
 *      given, then the current selection or word before the cursor is
 *      used.
 * @param lang {String} The language name to scope the search. Optional.
 * @param sublang {String} The sub-language name top scope the search.
 *      Optional.
 * @returns {Boolean} True if the snippet was found and inserted, false
 *      otherwise.
 */
this.expandAbbrev = function expandAbbrev(abbrev /* =null */,
                                          lang /* =null */,
                                          sublang /* =null */) {
    if (typeof(abbrev) == 'undefined') abbrev = null;
    if (typeof(lang) == 'undefined') lang = null;
    if (typeof(sublang) == 'undefined') sublang = null;

    var currView = ko.views.manager.currentView;
    var origPos = null;
    var origAnchor = null;
    
    // Determine the abbrev to look for.
    var scimoz = currView.scimoz;
    if (abbrev != null) {
        // pass
    } else {
        if (scimoz.anchor == scimoz.currentPos) {
            // Only do abbreviation expansion if next to a word char,
            // i.e. valid abbrev chars.
            var pos = scimoz.currentPos;
            if (pos == 0 || !is_abbrev(scimoz.getTextRange(pos-1, pos))) {
                ko.statusBar.AddMessage(
                    "No abbreviation at the current position.",
                    "abbrev", 5000, false);
                return false;
            }
            origPos = pos;
            origAnchor = scimoz.anchor;
            scimoz.wordLeftExtend();
        }
        abbrev = scimoz.selText;
    }

    // Find the snippet for this abbrev, if any, and insert it.
    var snippet = ko.abbrev.findAbbrevSnippet(abbrev, lang, sublang);
    if (snippet) {
        ko.abbrev.insertAbbrevSnippet(snippet, currView);
        return true;
    } else {
        if (origPos != null) { // Restore state.
            scimoz.currentPos = origPos;
            scimoz.anchor = origAnchor;
        }
        var msg = "No '"+abbrev+"' abbreviation was found.";
        ko.statusBar.AddMessage(msg, "abbrev", 5000, true);
        return false;
    }
}


/**
 * Find a snippet for the given abbreviation name.
 *
 * Abbreviations used for snippets are in looked for in
 * "Abbreviations" groups in these places:
 * 1. the current project (if any)
 * 2. the toolbox
 * 3. the shared toolbox (if any)
 *
 * And for these languages:
 * A. the current buffer sub-lang (for multi-lang files)
 * B. the current buffer lang (if different than A)
 * C. the "General" lang (i.e. not language-specific)
 *
 * @param abbrev {String} The abbreviation name.
 * @param lang {String} The language name to scope the search. Optional.
 *      If not given, then the language of the current view is used.
 *      Specify "General" to *not* search for a lang-specific
 *      abbreviation.
 * @param sublang {String} The sub-language name top scope the search.
 *      This can be relevant for multi-language files (e.g. HTML can have
 *      HTML and JavaScript and CSS). Optional. If not given, then
 *      the sub-lang of the current cursor position in the current view is
 *      used. Specify "General" to *not* search for a sub-lang-specific
 *      abbreviation.
 * @returns {Components.interfaces.koIPart_snippet} the relevant snippet,
 *      or null if no snippet is found.
 */
this.findAbbrevSnippet = function(abbrev, lang /* =<curr buf lang> */,
                                  sublang /* =<curr pos sublang> */) {
    if (typeof(lang) == 'undefined') lang = null;
    if (typeof(sublang) == 'undefined') sublang = null;
    
    // Determine 'lang' and 'sublang', if not provided.
    var currView = ko.views.manager.currentView;
    if (lang == null && currView && currView.document) {
        lang = currView.document.language;
    }
    if (sublang == null && currView && currView.document) {
        sublang = currView.document.subLanguage;
    }
    
    // The list of sub-folder names under an "Abbreviations" folder in
    // which to look for the snippet.
    var subnames = Array();
    if (sublang) subnames.push(sublang);
    if (lang && subnames.indexOf(lang) == -1) subnames.push(lang);
    if (subnames.indexOf("General") == -1) subnames.push("General");
    
    // Look in all "Abbreviations" folders for the first appropriate
    // snippet.
    var partSvc = Components.classes["@activestate.com/koPartService;1"]
            .getService(Components.interfaces.koIPartService);
    var abbrev_folders = partSvc.getParts(
            "folder", "name", "Abbreviations", "*", partSvc.currentProject,
            new Object());
    var subfolder, snippet;
    for (var i = 0; i < abbrev_folders.length; i++) {
        var abbrev_folder = abbrev_folders[i];
        for (var j = 0; j < subnames.length; j++) {
            subfolder = abbrev_folder.getChildWithTypeAndStringAttribute(
                "folder", "name", subnames[j], false);
            if (subfolder) {
                //dump("findAbbrevSnippet: look in "+abbrev_folder.project.name
                //     +"/.../Abbreviations/"+subnames[j]);
                snippet = subfolder.getChildWithTypeAndStringAttribute(
                    "snippet", "name", abbrev, true);
                if (snippet) {
                    //dump(" (found it)\n");
                    return snippet;
                } else {
                    //dump(" (not here)\n");
                }
            }
        }
    }
    return null;
}


/**
 * Insert an abbreviation snippet into a buffer.
 *
 * @param snippet {Components.interfaces.koIPart_snippet} The snippet part
 *      to insert. You can use `ko.abbrev.findAbbrevSnippet()` to get one.
 * @param view {Components.interfaces.koIView} The buffer view in which to
 *      insert the snippet. Optional. If not specified then the current
 *      view is used.
 */
this.insertAbbrevSnippet = function(snippet, view /* =<curr view> */) {
    if (!snippet) {
        return;
    }
    if (typeof(view) == 'undefined' || view == null) {
        view = ko.views.manager.currentView;
    }

    var scimoz = view.scimoz;
    scimoz.beginUndoAction();
    try {
        ko.projects.snippetInsertImpl(snippet, view);
    } finally {
        scimoz.endUndoAction();
    }
}


var _abbrev_valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_";
function is_abbrev(s) {
    for (var i = 0; i < s.length; ++i) {
        if (_abbrev_valid_chars.indexOf(s[i]) == -1) {
            return false;
        }
    }
    return true;
}

}).apply(ko.abbrev);
