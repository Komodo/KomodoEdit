/* Copyright (c) 2000-2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
