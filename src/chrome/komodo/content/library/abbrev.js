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

var lazy = {};
XPCOMUtils.defineLazyGetter(lazy, "bundle", function()
    Services.strings.createBundle("chrome://komodo/locale/library.properties"));

var handle_toolbox_updates = false;
var toolbox_notification_names = [
    "toolbox-reload-view",
    "toolbox-loaded-global",
    "toolbox-loaded-local",
    "toolbox-unloaded-global",
    "toolbox-unloaded-local",
    "toolbox-tree-changed",
    "tool-deleted",
    "tool-appearance-changed"
];

this.initialize = function initialize() {
    this.log = ko.logging.getLogger('abbrev.js');
    ko.main.addWillCloseHandler(this.postCanClose, this);
    
    // Bug 96693: Watch for changes in the toolbox in order to track
    // all auto-abbreviation snippets, but after startup
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    for each (var name in toolbox_notification_names) {
        Services.obs.addObserver(this, name, false);
    }
    handle_toolbox_updates = true;
    this.updateAutoAbbreviations();
};

this.postCanClose = function postCanClose() {
    handle_toolbox_updates = false;
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    for each (var name in toolbox_notification_names) {
        Services.obs.removeObserver(this, name);
    }
};

this.observe = function(subject, topic, data) {
    this.updateAutoAbbreviations();
};

this.updateAutoAbbreviations = function updateAutoAbbreviations(event) {
    // Bug 96693: cache all auto_abbreviations to avoid looking up every
    // term.  On linux this query takes < 25% more of the time a lookup on
    // a single word takes, but is only done at startup and when the
    // toolbox or a snippet changes.
    if (!handle_toolbox_updates) {
        // We're shutting down, so don't bother processing.
        return;
    }
    try {
        var activeAutoAbbreviations;
        activeAutoAbbreviations = this.activeAutoAbbreviations = {};
        this.activeManualAbbreviations = {};
    
        var tbSvc = Components.classes["@activestate.com/koToolbox2Service;1"]
            .getService(Components.interfaces.koIToolbox2Service);
        var names = tbSvc.getAutoAbbreviationNames({});
        names.forEach(function(name) {
                // Map abbrev-name => { language => snippet|null }, lazily set
                activeAutoAbbreviations[name] = {};
            });
    } catch(ex) {
        this.log.exception(ex, "Failed to get abbreviations");
    }
}

// Note: If we want to support the full range of TextMate-style
// snippet tab-triggers, then 'wordLeftExtend' isn't
// sufficient. There is the (rare) TextMate tabTrigger that
// mixes word and non-word chars.
this._isWordChar_re = /[\w\d\-_=\+\.]/;
this.getWordStart = function(scimoz, lastCharPos, useWordBoundary) {
    var prevStyle = scimoz.getStyleAt(lastCharPos);
    var prevPos, firstPos = lastCharPos;
    var prevChar;
    while (firstPos >= 1) {
        prevPos = scimoz.positionBefore(firstPos);
        if (prevStyle !== scimoz.getStyleAt(prevPos)) {
            break;
        }
        if (useWordBoundary) {
            prevChar = scimoz.getWCharAt(prevPos);
            if (!this._isWordChar_re.test(prevChar)) {
                break;
            }
        }
        firstPos = prevPos;
    }
    return firstPos;
};

/**
 * Expands the abbreviation, if any, at the current cursor position.
 *
 * @param {String} abbrev Optional. The abbreviation to expand. If not
 *      given, then the current selection or word before the cursor is
 *      used.
 * @param {String} lang The language name to scope the search. Optional.
 * @param {String} sublang The sub-language name to scope the search.
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
    
    // Determine the abbrev to look for.
    var scimoz = currView.scimoz;
    var koDoc = currView.koDoc;
    var languageObj = koDoc.languageObj;
    if (!abbrev) {
        var pos = scimoz.anchor;
        if (pos < scimoz.currentPos) {
            pos = scimoz.currentPos;
        }
        if (pos == 0) {
            // No abbrevs in an empty buffer
            return false;
        }
        var prevPos = pos == 0 ? 0 : scimoz.positionBefore(pos);
        // Don't expand if the cursor is not at the right of a possible
        // abbreviation.
        if (this._isWordChar_re.test(scimoz.getWCharAt(pos))) {
            return false;
        }
        var currStyle = scimoz.getStyleAt(pos);
        // Allow abbreviations in comments, strings, HTML default,
        // and HTML PIs and cdata sections.
        var useWordBoundary = false;
        let defaultStyles = languageObj.getNamedStyles("default");
        let isDefaultStyle = defaultStyles.indexOf(currStyle) >= 0;
        let prevStyle = scimoz.getStyleAt(prevPos);
        if (isDefaultStyle || currStyle == prevStyle) {
            // Reopened bug 98154: always look at the previous style,
            // in case the current one is a default style.
            currStyle = prevStyle;
            // Normally we expect an abbrev to be in a different style
            // from the current character, but this isn't the case in
            // comments, strings, and a few specific HTML styles.
            if (languageObj.getCommentStyles().indexOf(currStyle) >= 0
                || languageObj.getStringStyles().indexOf(currStyle) >= 0
                || defaultStyles.indexOf(currStyle) >= 0
                || (languageObj.isHTMLLanguage && ([scimoz.SCE_UDL_M_PI,
                                                    scimoz.SCE_UDL_M_CDATA].
                                                   indexOf(currStyle) >= 0))) {
                useWordBoundary = true;
            } else if (!isDefaultStyle) {
                // Bug 98154:  If we aren't on one of the above styles,
                // and we weren't on a default point, return.
                return false;
            }
        }
        if (scimoz.anchor == scimoz.currentPos) {
            // Only do abbreviation expansion if next to a word char,
            // i.e. valid abbrev chars.
            if (pos == 0 || !is_abbrev(scimoz.getTextRange(prevPos, pos))) {
                var msg =  lazy.bundle.GetStringFromName("noAbbreviationAtTheCurrentPosition");
                require("notify/notify").send(msg, "tools", {priority: "warning"});
                return false;
            }
        }
        var wordStartPos = this.getWordStart(scimoz, prevPos, useWordBoundary);
        abbrev = scimoz.getTextRange(wordStartPos, pos);
    }
    if (!lang || !sublang) {
        [lang, sublang, languageObj] = this._getLangAndSublangNames(koDoc, languageObj, prevPos);
    }
    if (!this._checkOpenTag(languageObj, scimoz, wordStartPos)) {
        return false;
    }
    var snippet = this._getCachedSnippet(abbrev, lang, sublang,
                                         /*isAutoAbbrev=*/false);
    var msg;
    var origPos = null;
    var origAnchor = null;
    if (snippet) {
        origPos = pos;
        origAnchor = scimoz.anchor;
        scimoz.currentPos = wordStartPos;
        scimoz.anchor = pos;
        var exObj = {};
        if (ko.abbrev.insertAbbrevSnippet(snippet, currView, exObj)) {
            return true;
        } else {
            if (exObj.value && exObj.value.message) {
                msg = lazy.bundle.formatStringFromName("snippet X insertion deliberately suppressed with reason",
                                   [snippet.name, exObj.value.message], 2);
            } else {
                msg = lazy.bundle.formatStringFromName("snippet X insertion deliberately suppressed",
                                   [snippet.name], 1);
            }
        }
    } else {
        msg = lazy.bundle.formatStringFromName("noAbbreviationWasFound", [abbrev], 1);
    }
    if (origPos !== null) { // Restore state.
        scimoz.currentPos = origPos;
        scimoz.anchor = origAnchor;
    }
    require("notify/notify").send(msg, "tools", {priority: "warning"});
    return false;
};

this._allowedStylesNameSets = ['keywords', 'classes', 'functions', 'identifiers',
                               'tags', 'classes', 'functions', 'keywords2',
                               'variables', 'modules', 'default'];
this._cachedAllowedStylesForLanguage = {};
this._allowedStylesForLanguage = function(languageObj) {
    var languageName = languageObj.name;
    if (!(languageName in this._cachedAllowedStylesForLanguage)) {
        var allowedStyles = [];
        this._allowedStylesNameSets.forEach(function(name) {
                allowedStyles = allowedStyles.concat(languageObj.getNamedStyles(name));
            });
        this._cachedAllowedStylesForLanguage[languageName] = allowedStyles;
    }
    return this._cachedAllowedStylesForLanguage[languageName];
};

this._textLikeLanguages = ["Markdown", "reStructuredText", "YAML",
                           "XML", "LaTeX", "troff", "POD",
                           "ASN.1", "PostScript", "SGML", "TeX", "ConTeX",
                           "PO", "TracWiki", "RTF"];
this.expandAutoAbbreviation = function(currView) {
    var scimoz = currView.scimoz;
    var currentPos = scimoz.anchor;
    if (currentPos < scimoz.currentPos) {
        currentPos = scimoz.currentPos;
    }
    var koDoc = currView.koDoc;
    // Note that the current character hasn't been styled yet, we're just
    // processing its keystroke event.
    // Also, don't expand auto-abbreviations if we aren't at the end of the line
    var lineEndPos = scimoz.getLineEndPosition(scimoz.lineFromPosition(currentPos));
    if (lineEndPos > currentPos) {
        return false;
    }
    var prevPos = currentPos == 0 ? 0 : scimoz.positionBefore(currentPos);
    var prevStyle = scimoz.getStyleAt(prevPos);
    var languageObj = koDoc.languageObj;
    var allowedStyles = this._allowedStylesForLanguage(languageObj);
    if (allowedStyles.indexOf(prevStyle) == -1) {
        return false;
    }
    var useWordBoundary;
    if (languageObj.name == "Text") {
        useWordBoundary = true;
    } else if (this._textLikeLanguages.indexOf(languageObj.name) >= 0
               || languageObj.isHTMLLanguage) {
        let defaultStyles = languageObj.getNamedStyles("default");
        useWordBoundary = defaultStyles.indexOf(prevStyle) >= 0;
    } else {
        useWordBoundary = false;
    }
    var wordStartPos = this.getWordStart(scimoz, prevPos, useWordBoundary);
    var abbrev = scimoz.getTextRange(wordStartPos, currentPos);
    if (!this._checkPossibleAbbreviation(abbrev)) {
        return false;
    }
    // At this point we might need to shift from the global doc language
    // to the sub-language at the current point.
    var languageName, subLanguageName;
    [languageName, subLanguageName, languageObj] = this._getLangAndSublangNames(koDoc, languageObj, prevPos)
    if (!this._checkOpenTag(languageObj, scimoz, wordStartPos)) {
        return false;
    }
    if (!this._checkPossibleAbbreviation(abbrev)) {
        return false;
    }
    var snippet = this._getCachedSnippet(abbrev, languageName, subLanguageName,
                                         /*isAutoAbbrev=*/true);
    if (snippet) {
        var origPos = currentPos;
        var origAnchor = scimoz.anchor;
        scimoz.currentPos = wordStartPos;
        scimoz.anchor = currentPos;
        if (ko.abbrev.insertAbbrevSnippet(snippet, currView)) {
            var msg = lazy.bundle.formatStringFromName("inserted autoabbreviation X",
                                                   [snippet.name], 1);
            var notify = require("notify/notify");
            notify.send(msg, "autoComplete",
                {
                    icon: snippet.iconurl,
                    undo: function(e) {
                        ko.commands.doCommand('cmd_focusEditor');
                        ko.commands.doCommandAsync('cmd_undo', e);
                    },
                    actions: [
                        {
                            label: lazy.bundle.GetStringFromName("Edit Snippet"),
                            command: function() {
                                ko.commands.doCommand("cmd_viewToolbox");
                                ko.toolbox2.ensureToolVisible(snippet, {select: true});
                                ko.toolbox2.editProperties_snippet(snippet);
                            }
                        },
                        {
                            label: lazy.bundle.GetStringFromName("disableAbbreviation"),
                            command: function() {
                                snippet.setStringAttribute("auto_abbreviation", "false");
                            }
                        }
                    ]
                }
            );
            return true;
        }
        scimoz.currentPos = origPos;
        scimoz.anchor = origAnchor;
    }
    return false;
};

/**
 * Find a snippet for the given abbreviation name.
 *
 * Abbreviations used for snippets are looked for in
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
 * @param {String} abbrev The abbreviation name.
 * @param {String} lang The language name to scope the search. Optional.
 *      If not given, then the language of the current view is used.
 *      Specify "General" to *not* search for a lang-specific
 *      abbreviation.
 * @param {String} sublang The sub-language name top scope the search.
 *      This can be relevant for multi-language files (e.g. HTML can have
 *      HTML and JavaScript and CSS). Optional. If not given, then
 *      the sub-lang of the current cursor position in the current view is
 *      used. Specify "General" to *not* search for a sub-lang-specific
 *      abbreviation.
 * @param {Boolean} isAutoAbbrev: True if we're trying to expand an
 *      auto-abbreviation snippet.
 * @returns {Components.interfaces.koITool} the relevant snippet,
 *      or null if no snippet is found.
 */
this.findAbbrevSnippet = function(abbrev, lang /* =<curr buf lang> */,
                                  sublang /* =<curr pos sublang> */,
                                  isAutoAbbrev) {
    if (typeof(lang) == 'undefined') lang = null;
    if (typeof(sublang) == 'undefined') sublang = null;
    
    // Determine 'lang' and 'sublang', if not provided.
    var currView = ko.views.manager.currentView;
    if (lang == null && currView && currView.koDoc) {
        lang = currView.koDoc.language;
    }
    if (sublang == null && currView && currView.koDoc) {
        sublang = currView.koDoc.subLanguage;
    }
    
    // The list of sub-folder names under an "Abbreviations" folder in
    // which to look for the snippet.
    // Never look for both sublang's and langs.  For example, if we're
    // in a script block we want JS abbrev'ns, but never want HTML abbrev'ns.
    var subnames = (sublang ? [sublang]
                    : (lang ? [lang] : []));
    if (subnames.indexOf("General") == -1) subnames.push("General");
    
    return ko.toolbox2.getAbbreviationSnippet(abbrev, subnames, isAutoAbbrev);
}


/**
 * Insert an abbreviation snippet into a buffer.
 *
 * @param snippet {Components.interfaces.koITool} The snippet part
 *      to insert. You can use `ko.abbrev.findAbbrevSnippet()` to get one.
 * @param view {Components.interfaces.koIView} The buffer view in which to
 *      insert the snippet. Optional. If not specified then the current
 *      view is used.
 * @param exObj {object} -- if it exists and trying to insert a snippet
 *      throws an exception, set exObj.value to the exception.
 * @returns {boolean} true if a snippet was inserted, false if not.
 */
this.insertAbbrevSnippet = function(snippet, view /* =<curr view> */,
                                     exObj /* ={} */) {
    if (!snippet) {
        return false;
    }
    if (typeof(view) == 'undefined' || view == null) {
        view = ko.views.manager.currentView;
    }

    var scimoz = view.scimoz;
    var enteredUndoableTabstop = false;
    ko.tabstops.clearTabstopInfo(view); // could call endUndoAction() if there are active links
    scimoz.beginUndoAction();
    try {
        ko.snippets.invokedExplicitly = false;
        enteredUndoableTabstop = ko.projects.snippetInsertImpl(snippet, view);
    } catch(ex) {
        //dump("snippetInsertImpl failed: " + ex + "\n");
        if (typeof(exObj) == "object") {
            exObj.value = ex;
        }
        return false;
    } finally {
        ko.snippets.invokedExplicitly = true;
        if (!enteredUndoableTabstop) {
            scimoz.endUndoAction();
        }
    }
    return true;
}

this._checkPossibleAbbreviation = function _checkPossibleAbbreviation(abbrev) {
    try {
        if (!(abbrev in this.activeAutoAbbreviations)) {
            // Bug 96693: avoid database lookups when the term on the right
            // is known not to be an auto-abbreviation (for any language)
            return false;
        }
    } catch(ex) {
        if (ex instanceof TypeError) {
            this.log.warn("Never got a komodo-ui-started notification, do it now");
            this.initialize();
            // And retry.
            if (!(abbrev in this.activeAutoAbbreviations)) {
                return false;
            }
        } else {
            this.log.exception(ex, "Unexpected problem checking for abbrev in this.activeAutoAbbreviations");
            return false;
        }
    }
    return true;
};

this._getLangAndSublangNames = function _getLangAndSublangNames(koDoc, languageObj, prevPos) {
/**
 * Given the current view, language, and position, determine whether we're
 * at the top-level language, or are looking at a sublanguage.
 * @returns @array [ languageName {String}, subLanguageName {String},
 *                   languageObj { koILanguage }]
 * If the actual subLanguageName is the same as languageName,
 * the returned subLanguageName is nulil.
 */
    var languageName = koDoc.language;
    var subLanguageName = null;
    if (koDoc.subLanguage != languageName) {
        subLanguageName = koDoc.languageForPosition(prevPos);
        languageObj = Components.classes["@activestate.com/koLanguageRegistryService;1"]
            .getService(Components.interfaces.koILanguageRegistryService).getLanguage(subLanguageName);
    }
    return [languageName, subLanguageName, languageObj];
};

this._checkOpenTag = function _checkOpenTag(languageObj, scimoz, wordStartPos) {
    if (languageObj.supportsSmartIndent != "XML") {
        return true; // it's ok
    }
    var wordStartStyle = scimoz.getStyleAt(wordStartPos);
    if (wordStartStyle != scimoz.SCE_UDL_M_TAGNAME) {
        // Must be a plain style, so it's expandable.
        return true; // it's ok
    }
    // Verify that it starts with a start-tag-open ("<").
    var prevPrevPos = scimoz.positionBefore(wordStartPos);
    return scimoz.getStyleAt(prevPrevPos) == scimoz.SCE_UDL_M_STAGO;
};

this._getCachedSnippet = function _getCachedSnippet(abbrev, lang, sublang,
                                                    isAutoAbbrev) {
    var abbrevInfo, snippet;
    var collection = isAutoAbbrev ? this.activeAutoAbbreviations: this.activeManualAbbreviations;
    var langKey = (sublang || lang) + ":" + (isAutoAbbrev ? "1" : "0");
    if (abbrev in collection) {
        abbrevInfo = collection[abbrev];
        if (abbrevInfo && langKey in abbrevInfo) {
            return abbrevInfo[langKey];
        }
    } else {
        abbrevInfo = null;
    }
    // Find the snippet for this abbrev, if any, and insert it.
    // We know that the current abbrev is an auto-abbreviation for
    // *some* language, here we check to see if it's valid for
    // the current language.  If so, cache it.  If not, mark it as
    // null, so subsequent occurrences of this word don't cause
    // database lookups.
    snippet = ko.abbrev.findAbbrevSnippet(abbrev,
                                          lang,
                                          sublang,
                                          isAutoAbbrev);
    if (!abbrevInfo) {
        abbrevInfo = collection[abbrev] = {};
    }
    if (snippet) {
        // Cache the snippet until the next time anything in the
        // toolbox changes.
        abbrevInfo[langKey] = snippet;
    } else {
        abbrevInfo[langKey] = null;
    }
    return snippet;
};

// Currently don't allow triggering at a whitespace char.
function is_abbrev(s) {
    return !/\s/.test(s);
}

}).apply(ko.abbrev);

window.addEventListener("komodo-ui-started", ko.abbrev.initialize.bind(ko.abbrev));
