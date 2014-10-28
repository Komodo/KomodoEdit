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
     * A href|src file handler - to help in opening files. Examples:
     *    href="#main"
     *    src="foobar.css"
     *    href="script.js"
     */

    var _is_windows = (navigator.platform == 'Win32');
    const color = require("ko/color");

    /**
     * Jump to the given id in the supplied view.
     * 
     * @param view {Components.interfaces.koIScintillaView} - View to look in.
     * @param {string} id - The string id to locate.
     *
     * @returns {boolean} True when found, false otherwise.
     */
    function jump_to_html_id(view, id) {
        var sm = view.scimoz;
        var text = sm.text;
        var pos = text.search(new RegExp("\\sid\\s?=\\s?['\"]" + id + "['\"][\\s>]", "i"));
        if (pos >= 0) {
            var scimoz_pos = ko.stringutils.bytelength(text.substr(0, pos));
            sm.gotoPos(scimoz_pos);
            return true;
        }
        // TODO: It would really neat if we could check for the id in all of the
        //      loaded files - or a list of all known ids.
        return false;
    }

    /**
     * Expand and return the URI of the given relative path.
     *
     * @param {koIView} view - The editor view.
     * @param {String} filepath - The path to expand.
     * @param {array} alternativePaths - Other possible filepaths (when filepath doesn't exist).
     *
     * @returns {String}
     */
    function getUriForPath(view, filepath, alternativePaths /* [] */) {
        var absFilepath = null;
        if (filepath[0] == "\\" || filepath[0] == "/") {
            // It's an absolute path already.
            absFilepath = filepath;
        } else if (filepath.search(/^\w+:\/\//) == 0) {
            // It's in a URI format - convert to local path.
            // XXX: Need a way to deal with remote paths.
            absFilepath = ko.uriparse.URIToLocalPath(filepath);
        } else {
            // It's a relative path.

            // #1 - TODO: Check mapped URIs for this path.

            // #2 - TODO: check against a list of known places (images, css,
            //            etc...).

            // #3 - default to the current directory.
            var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
            var view_filepath = view.koDoc.file.path;
            var view_dirpath = ko.uriparse.dirName(view_filepath);
            absFilepath = osPathSvc.join(view_dirpath, filepath);
            if (alternativePaths && !osPathSvc.exists(absFilepath)) {
                // Check other possible locations
                var altPath = "";
                for (var i=0; i < alternativePaths.length; i++) {
                    altPath = osPathSvc.join(view_dirpath, alternativePaths[i]);
                    altPath = osPathSvc.normpath(altPath);
                    if (osPathSvc.exists(altPath)) {
                        absFilepath = altPath;
                        break;
                    }
                }
            }
        }
        if (view.koDoc.file.scheme != "file" && absFilepath) {
            // Turn absFilepath into a URI.
            var filler = "";
            absFilepath = absFilepath.replace("\\", "/", "g");
            if (_is_windows && absFilepath[1] == ":" && absFilepath[0] != "/") {
                filler = "/";
            }
            return view.koDoc.file.prePath + filler + absFilepath;
        }
        return absFilepath;
    }

    /**
     * Open the filepath/href location.
     *
     * @param {String} filepath - The (relative, href, absolute) path to open.
     * @param {array} alternativePaths - Other possible filepaths (when filepath doesn't exist).
     */
    function filename_jump_handler(filepath, alternativePaths) {
        if (typeof(filepath) == 'undefined') {
            var match = src_href_handler.regex_match;
            filepath = match[2];
        }
        if (filepath) {
            /**
             * @type {Components.interfaces.koIScintillaView}
             */
            var view = ko.views.manager.currentView;
            if (filepath[0] == "#") {
                // It's within this document (an anchor).
                // #1 - Look for an id=""
                if (jump_to_html_id(view, filepath.substr(1))) {
                    return;
                }
                // #2 - Look for a '<a name=...'
                var pos = text.search(new RegExp("<a\\s+(.*?\\s)?name\\s?=\\s?['\"]" + filepath.substr(1) + "['\"][\\s>]", "i"));
                if (pos >= 0) {
                    var scimoz_pos = ko.stringutils.bytelength(text.substr(0, pos));
                    sm.gotoPos(scimoz_pos);
                    return;
                } else {
                    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                        .getService(Components.interfaces.nsIStringBundleService)
                        .createBundle("chrome://komodo/locale/hyperlinks/hyperlinks.properties");
                    var msg = _bundle.formatStringFromName("noAnchorFound.message", [filepath], 1);
                    require("notify/notify").send(msg, "editor", {priority: "warning"});
                }
            } else {
                ko.open.URI(getUriForPath(view, filepath, alternativePaths));
            }
        }
    }
    function src_href_jump_fn(match) {
        var filepath = match[2];
        filename_jump_handler(filepath);
    }
    ko.hyperlinks.handlers.srcHrefHandler =
        new ko.hyperlinks.RegexHandler(
                            "Src and Href handler",
                            new RegExp("\\b(src|href)=[\\\"'](.*?)[\\\"']", "i"),
                            src_href_jump_fn,
                            null,  /* Use the found string instead of a replacement. */
                            null,  /* All language types */
                            Components.interfaces.ISciMoz.INDIC_PLAIN,
                            color.RGBToBGR(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(ko.hyperlinks.handlers.srcHrefHandler);


    /**
     * A JavaScript document.getElementById() helper:
     *    document.getElementById('myid')  =>  jumps to element with id 'myid'
     *    $('#foo')                        =>  jumps to element with id 'foo'
     *
     * Note: This hyperlink handler will only show when hovering over the
     *       string section of the match, i.e. over 'myid'.
     */
    function getelementbyid_jump_handler(match) {
        var id = match[2];
        if (id[0] == '#') {
            id = id.substr(1);
        }
        if (id) {
            jump_to_html_id(ko.views.manager.currentView, id);
        }
    }
    ko.hyperlinks.handlers.jsGetElementByIdHandler =
        new ko.hyperlinks.RegexHandler(
            "getElementById handler",
            new RegExp("(getElementById|\\$)\\s*\\(\\s*[\"'](.*?)[\"']", "i"),
            getelementbyid_jump_handler,
            null,  /* Use the found string instead of a replacement. */
            ["JavaScript"],  /* Just javascript. */
            Components.interfaces.ISciMoz.INDIC_PLAIN,
            color.RGBToBGR(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(ko.hyperlinks.handlers.jsGetElementByIdHandler);
    // Limit to JavaScript string styles.
    ko.hyperlinks.handlers.jsGetElementByIdHandler.limitToTheseStyles([Components.interfaces.ISciMoz.SCE_UDL_CSL_STRING]);


    /**
     * A PHP include file handler - to help in opening files. Examples:
     *    include('functions/myfile.php');
     *    require_once "foo/bar/myfile.php";
     *    include (dirname(__FILE__) . "myfile.php");
     */
    function php_jump_handler(match) {
        var filepath = match[3];
        filename_jump_handler(filepath);
    }
    ko.hyperlinks.handlers.phpIncludeHandler =
        new ko.hyperlinks.RegexHandler(
            "PHP include handler",
            new RegExp("(include|require|include_once|require_once)(\\s+|\\().*?[\"'](.*?)[\"']\\s*\\)?", "i"),
            php_jump_handler,
            null,  /* Use the found string instead of a replacement. */
            null,  /* All language types */
            Components.interfaces.ISciMoz.INDIC_PLAIN,
            color.RGBToBGR(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(ko.hyperlinks.handlers.phpIncludeHandler);


    /**
     * A Django view/template handler - to help in opening files. Examples:
     *    render_to_response('komodo/index.html', ...)
     */
    function django_view_jump_handler(match) {
        var filepath = match[3];
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
        // Try current directory templates.
        // XXX: The "templates" name should come from the settings.py file.
        var templatepath = osPathSvc.join("templates", filepath);
        var alternativePaths = [osPathSvc.join("..", templatepath)];
        // Also try parent directory templates, seeing if there is a match there.
        for (var i=1; i < 5; i++) {
            alternativePaths.push(osPathSvc.join("..", alternativePaths[i-1]));
        }
        filename_jump_handler(templatepath, alternativePaths);
    }
    ko.hyperlinks.handlers.djangoRenderViewHandler =
        new ko.hyperlinks.RegexHandler(
            "Django render_to_response handler",
            new RegExp("(render_to_response|render_to_string|template)\\s*(\\(\\s*)?[\"'](.*?)[\"']", "i"),
            django_view_jump_handler,
            null,  /* Use the found string instead of a replacement. */
            ["Python", "Python3"],  /* Python files only */
            Components.interfaces.ISciMoz.INDIC_PLAIN,
            color.RGBToBGR(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(ko.hyperlinks.handlers.djangoRenderViewHandler);


    /**
     * A Django view/template handler - to help in opening files. Examples:
     *    render_to_response('komodo/index.html', ...)
     */
    function django_extends_jump_handler(match) {
        var filepath = match[1];
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
        // Try current directory templates.
        // XXX: The "templates" name should come from the settings.py file.
        var templatepath = osPathSvc.join("templates", filepath);
        var alternativePaths = [osPathSvc.join("..", templatepath)];
        // Also try parent directory templates, seeing if there is a match there.
        for (var i=1; i < 5; i++) {
            alternativePaths.push(osPathSvc.join("..", alternativePaths[i-1]));
        }
        filename_jump_handler(templatepath, alternativePaths);
    }
    ko.hyperlinks.handlers.djangoExtendsHandler =
        new ko.hyperlinks.RegexHandler(
            "Django render_to_response handler",
            new RegExp("\\{\\%\\s*extends\\s+[\"'](.*?)[\"']", "i"),
            django_extends_jump_handler,
            null,  /* Use the found string instead of a replacement. */
            ["Django"],  /* Django files only */
            Components.interfaces.ISciMoz.INDIC_PLAIN,
            color.RGBToBGR(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(ko.hyperlinks.handlers.djangoExtendsHandler);


    /**
     * A generic file handler - to help in opening files. Examples:
     *    file:///foo/bar.txt
     *    /foo/bar.txt
     *    C:\foo\bar.txt
     *    \\foo\bar.txt
     *
     * Note: This must be the last added file hyperlink handler, so it has a
     * lower priority than the other more specific file handlers - bug 101505.
     */
    ko.hyperlinks.handlers.fileHandler =
        new ko.hyperlinks.RegexHandler(
            "File handler",
            new RegExp(_is_windows ? "(file:|[\\.]{1,2}/|/|[A-Z]:\\\\|\\\\\\\\)[^'\"<>(){}[\\]\\$\\s]+"
                                   : "(file:|[\\.]{1,2}/|/)[^'\"<>(){}[\\]\\$\\s]+",
                       "i"),
            function(match, arg) { filename_jump_handler(arg); },
            null,  /* Use the found string instead of a replacement. */
            null,  /* All language types */
            Components.interfaces.ISciMoz.INDIC_PLAIN,
            color.RGBToBGR(0x60,0x90,0xff));
    ko.hyperlinks.addHandler(ko.hyperlinks.handlers.fileHandler);


})();
