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

(function() {
    /**
     * Open the href location.
     */
    function src_href_jump_handler() {
        var match = src_href_handler.regex_match;
        var filepath = match[2];
        if (filepath) {
            /**
             * @type {Components.interfaces.koIScintillaView}
             */
            var view = ko.views.manager.currentView;
            if (filepath[0] == "#") {
                // It's within this document (an anchor).
                // #1 - Look for an id=""
                var sm = view.scimoz;
                var text = sm.text;
                var pos = text.search(new RegExp("\\sid\\s?=\\s?['\"]" + filepath.substr(1) + "['\"][\\s>]", "i"));
                if (pos >= 0) {
                    var scimoz_pos = ko.stringutils.bytelength(text.substr(0, pos));
                    sm.gotoPos(scimoz_pos);
                    return;
                }
                // #2 - Look for a '<a name=...'
                var pos = text.search(new RegExp("<a\\s+(.*?\\s)?name\\s?=\\s?['\"]" + filepath.substr(1) + "['\"][\\s>]", "i"));
                if (pos >= 0) {
                    var scimoz_pos = ko.stringutils.bytelength(text.substr(0, pos));
                    sm.gotoPos(scimoz_pos);
                    return;
                }
            } else if (filepath[0] == "\\" || filepath[0] == "/") {
                // It's an absolute path.
                ko.open.URI(filepath);
            } else {
                // It's a relative path.
                // #1 - Check current directory.
                var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
                var view_filepath = view.document.file.path;
                var try_filepath = osPathSvc.join(ko.uriparse.dirName(view_filepath), filepath);
                if (osPathSvc.exists(try_filepath)) {
                    ko.open.URI(try_filepath);
                    return;
                }
                // #2 TODO: check against a list of known places (images, css,
                //          etc...)
            }
        }
    }
    var src_href_handler = new ko.hyperlinks.RegexHandler(
                            "Src and Href handler",
                            new RegExp("\\b(src|href)=[\\\"'](.*?)[\\\"']", "i"),
                            src_href_jump_handler,
                            null,  /* Use the found string instead of a replacement. */
                            null,  /* All language types */
                            Components.interfaces.ISciMoz.INDIC_PLAIN,
                            RGB(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(src_href_handler);


    /**
     * A generic file handler - to help in opening files. Examples:
     *    file:///foo/bar.txt
     *    /foo/bar.txt
     *    C:\foo\bar.txt
     *    \\foo\bar.txt
     */
    ko.hyperlinks.addHandler(
        new ko.hyperlinks.RegexHandler(
            "File handler",
            new RegExp("(file:|/|\\[A-Z]:\\\\|\\\\)[^'\"<>()[\\]\\s]+", "i"),
            ko.open.URI,
            null,  /* Use the found string instead of a replacement. */
            null,  /* All language types */
            Components.interfaces.ISciMoz.INDIC_PLAIN,
            RGB(0x60,0x90,0xff))
    );

})();
