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
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

var _log = ko.logging.getLogger('peSnippet');
var ANCHOR_MARKER = '!@#_anchor';
var CURRENTPOS_MARKER = '!@#_currentPos';

var _wrapsSelectionRE = /\[\[%[sS]\]\]/;

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/library.properties");



function peSnippet() {
    this.name = 'peSnippet';
}
peSnippet.prototype.constructor = peSnippet;
peSnippet.prototype.init = function() {
}

peSnippet.prototype.registerCommands = function() {
    ko.projects.extensionManager.registerCommand('cmd_makeSnippetFromSelection', this);
}

peSnippet.prototype.registerEventHandlers = function() {}

peSnippet.prototype.registerMenus = function() {}

peSnippet.prototype.supportsCommand = function(command, part) {
    return command == 'cmd_makeSnippetFromSelection';
}


peSnippet.prototype.isCommandEnabled = function(command, part) {
    switch (command) {
    case 'cmd_makeSnippetFromSelection':
        var sel = '';
        if (ko.views.manager.currentView &&
            ko.views.manager.currentView.getAttribute('type') == 'editor') {
            try {
                sel = ko.views.manager.currentView.selection;
            } catch(ex) {
                // This is one of the few isCommandEnabled methods that can
                // trigger a xbl "document.getAnonymousNodes(this) has no properties"
                // exception.
                return false;
            }
        }
        return (sel != '');
    }
    return false;
}

peSnippet.prototype.doCommand = function(command) {
    var item = null;
    switch (command) {
    case 'cmd_makeSnippetFromSelection':
        // Create new snippets in the current toolbox
        var parent = ko.toolbox2.getSelectedContainer();
        ko.projects.addSnippetFromText(ko.views.manager.currentView.selection, parent);
    default:
        break;
    }
}
// this is hidden away now, no namespce, the registration keeps the reference
// we need
ko.projects.registerExtension(new peSnippet());

this.snippetProperties = function snippet_editProperties (item)
{
    var obj = new Object();
    obj.item = item;
    obj.task = 'edit';
    window.openDialog(
        "chrome://komodo/content/project/snippetProperties.xul",
        "Komodo:SnippetProperties",
        "chrome,close=yes,dependent=no,resizable=yes,centerscreen",
        obj);
}

this.addSnippet = function peSnippet_addSnippet(/*koIPart|koITool*/ parent,
                                                /*koIPart|koITool*/ snippet )
{
    if (typeof(snippet) == "undefined") {
        snippet = ko.toolbox2.createPartFromType('snippet');
    }
    snippet.setStringAttribute('name', 'New Snippet');
    snippet.setStringAttribute('set_selection', 'false');
    snippet.setStringAttribute('indent_relative', 'false');
    snippet.setStringAttribute('auto_abbreviation', 'false');
    snippet.value = '';
    var obj = new Object();
    obj.item = snippet;
    if (typeof(parent)=='undefined' || !parent)
        parent = ko.projects.active.getSelectedItem();
    obj.parentitem = parent;
    obj.active = ko.projects.active;
    obj.task = 'new';
    ko.windowManager.openOrFocusDialog(
        "chrome://komodo/content/project/snippetProperties.xul",
        "komodo_snippetProperties",
        "chrome,close=yes,dependent=no,resizable=yes,centerscreen",
        obj);
}

this.addSnippetFromText = function AddSnippetFromText(snippettext, /*koIPart*/ parent) {
    // Bug 84625 - don't escape '%' in snippet shortcuts
    var parts = snippettext.split(/(\[\[%\w.*?\]\])/);
    for (var i = 0; i < parts.length; i += 2) {
        parts[i] = parts[i].replace('%', '%%', 'g');
    }
    var escapedtext = parts.join('');
    var snippet = ko.toolbox2.createPartFromType('snippet');
    snippet.type = 'snippet';
    snippet.setStringAttribute('name', snippetMakeDisplayName(snippettext));
    snippet.setStringAttribute('set_selection', 'true');
    snippet.setStringAttribute('indent_relative', 'false');
    snippet.setStringAttribute('auto_abbreviation', 'false');
    escapedtext = ANCHOR_MARKER + escapedtext + CURRENTPOS_MARKER;
    snippet.value = escapedtext;

    ko.toolbox2.addItem(snippet, parent, /*selectItem=*/true);
    return snippet;
}

this.snippetInsert = function Snippet_insert (snippet) { // a part

    // Snippet insertion is surprisingly tricky to do.
    // Snippets also store the selection within the snippet using line/column markers.
    // These are converted to index positions, inserted into the text using special
    // markers, the text is run through the interpolation service, indented
    // according to the local context if appropriate; the markers are removed and
    // the selection is set (if required) after the insertion.
    var view = ko.views.manager.currentView;
    if (!view || view.getAttribute('type') != 'editor') return;
    var scimoz = view.scimoz;

    ko.tabstops.clearTabstopInfo(view); // could call endUndoAction() if there are active links
    scimoz.beginUndoAction();
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                        getService(Components.interfaces.koILastErrorService);
    var enteredUndoableTabstop = false;
    try {
        try {
            enteredUndoableTabstop = ko.projects.snippetInsertImpl(snippet, view);
        } catch (ex if ex instanceof ko.snippets.RejectedSnippet) {
            let msg;
            if (ex.message) {
                msg = _bundle.formatStringFromName("snippet X insertion deliberately suppressed with reason", [snippet.name, ex.message], 2);
            } else {
                msg = _bundle.formatStringFromName("snippet X insertion deliberately suppressed", [snippet.name], 1);
            }
            require("notify/notify").send(msg, "tools", {priority: "warning"});
        } catch (ex) {
            var errno = lastErrorSvc.getLastErrorCode();
            if (errno == Components.results.NS_ERROR_ABORT) {
                // Command was cancelled.
            } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
                var errmsg = lastErrorSvc.getLastErrorMessage();
                ko.dialogs.alert("Error inserting snippet: " + errmsg);
            } else {
                log.exception(ex, "Error with snippet");
                ko.dialogs.internalError(ex, "Error inserting snippet");
            }
        }
    } finally {
        ko.macros.recordPartInvocation(snippet);
        if (!enteredUndoableTabstop) {
            scimoz.endUndoAction();
        }
    }
}

function _repeatChar(c, count) {
    var s = '';
    for(; count > 0; --count) {
        s += c;
    }
    return s;
}

/* Convert white-space to tabs
 * @param {String} s
 * @param {Integer} tabWidth
 * @returns {String} detabified string
 */
this._detabify = function(s, tabWidth) {
    if (tabWidth <= 0) return s; // sanity check user input
    var s_new = '';
    var out_pos = 0;
    var in_len = s.length;
    for (var in_pos = 0; in_pos < in_len; ++in_pos) {
        var c = s.substr(in_pos, 1);
        if (c == ' ') {
            s_new += c;
            out_pos += 1;
        } else if (c == '\t') {
            var num_needed = tabWidth - out_pos % tabWidth;
            out_pos += num_needed;
            s_new += _repeatChar(' ', num_needed);
        } else {
            s_new += s.substr(in_pos);
            break;
        }
    }
    return s_new;
}

/* Convert leading white-space in each line to spaces, and remove
 * the base indentation from each lines.
 *
 * @param {String} text
 * @param {Integer} tabWidth
 * @param {String} baseIndentation
 * @returns {String} converted string
 */
this._stripLeadingWS  = function(text, tabWidth, baseIndentation) {
    if (!baseIndentation) {
        return text;
    }
    var lines = text.split(/(\r?\n|\r)/);
    var fixedLines = [];
    var lim = lines.length;
    if (lim % 2) {
        lines.push("");
        lim += 1;
    }
    for (var i = 0; i < lim; i += 2) {
        var noTabLine = this._detabify(lines[i], tabWidth);
        if (noTabLine.indexOf(baseIndentation) != 0) {
            if (i > 0) {
                dump("Whoa, reduced indentation at line " + i
                     + "\n");
                // Bail out
                return text;
            } else {
                fixedLines.push(noTabLine);
            }
        } else {
            fixedLines.push(noTabLine.substr(baseIndentation.length));
        }
        fixedLines.push(lines[i + 1]);
    }
    return fixedLines.join("");
}

this.snippetInsertImpl = function snippetInsertImpl(snippet, view /* =<curr view> */) {
    
    if(typeof(view) == 'undefined') {
        view = ko.views.manager.currentView;
    }
    
    var scimoz = view.scimoz;
    
    view.scintilla.focus(); // we want focus right now, not later
    var setSelection = snippet.hasAttribute('set_selection')
            && snippet.getStringAttribute('set_selection') == 'true';
    var relativeIndent = snippet.hasAttribute('indent_relative')
            && snippet.getStringAttribute('indent_relative') == 'true';
    var viewData = ko.interpolate.getViewData(window);
    var treat_as_ejs = (snippet.hasAttribute('treat_as_ejs')
                       && snippet.getStringAttribute('treat_as_ejs') == 'true');
    var text = snippet.value;
    
    // Normalize the text to use the target view's preferred EOL.
    // (See bug 69535).
    var eol = view.koDoc.new_line_endings;
    var eol_str;
    switch (eol) {
    case Components.interfaces.koIDocument.EOL_LF:
        eol_str = "\n";
        break;
    case Components.interfaces.koIDocument.EOL_CRLF:
        eol_str = "\r\n";
        break;
    case Components.interfaces.koIDocument.EOL_CR:
        eol_str = "\r";
        break;
    };
    if (treat_as_ejs && text.indexOf("<%") >= 0) {
        text = this._textFromEJSTemplate(text, eol, eol_str, snippet);
    } else {
        text = text.replace(/\r\n|\n|\r/g, eol_str);
    }
    
    // detect if there are tabstops before we interpolate the snippet text
    var hasTabStops = ko.tabstops.textHasTabstops(text);
    if (hasTabStops) {
        ko.tabstops.clearTabstopInfo(view);
    }

    if (scimoz.selText.length == 0 && text.match(/%\(?[wW]/) != null) {
        // There is no selection but there is a '%w', '%W', '%(w', or
        // '%(W' in the snippet. Special case: select the word.
        //TODO: Can we not use ko.interpolate.getWordUnderCursor()?
        if (ko.interpolate.isWordCharacter(
                scimoz.getWCharAt(scimoz.currentPos-1))) {
            // There is part of a word to our left
            scimoz.wordLeft();
        }
        // Using several wordPartRights instead of one wordRight
        // because the latter is whitespace swallowing.
        while (ko.interpolate.isWordCharacter(
                    scimoz.getWCharAt(scimoz.currentPos))) {
            // There is part of a word to our right
            scimoz.wordPartRightExtend();
        }
    }

    // Do the interpolation of special codes.
    // var snippetWrapsSelection = text.indexOf('[[%s') >= 0;
    var snippetWrapsSelection = _wrapsSelectionRE.test(text);
    text = text.replace('%%', '%', 'g');

    // Common variables...
    var leading_ws_re = /^(\s+)(.*)/;
    var startingLine = scimoz.lineFromPosition(scimoz.currentPos);
    var startingLineStartPos = scimoz.positionFromLine(startingLine);
    var currLineText = scimoz.getTextRange(startingLineStartPos,
                                           scimoz.currentPos);
    var match = currLineText.match(leading_ws_re);

    var useTabs = view.prefs.getBooleanPref("useTabs");
    var tabWidth = view.prefs.getLongPref("tabWidth");
    var indentWidth = view.prefs.getLongPref("indentWidth");
    var baseIndentation = match ? this._detabify(match[1], tabWidth) : "";

    // Trim the baseIndentation from each line but the first of the selection.
    // It will get re-inserted after interpolation.
    if (snippetWrapsSelection) {
        if (viewData.selection) {
            viewData.selection = this._stripLeadingWS(viewData.selection,
                                                      tabWidth,
                                                      baseIndentation);
        } else {
            ko.dialogs.alert("Error inserting snippet: "
                             + "The snippet expects a selection, but there is none.");
            return false;
        }
    }        

    var istrings = ko.interpolate.interpolate(
                        window,
                        [], // codes are not bracketed
                        [text], // codes are bracketed
                        snippet.getStringAttribute("name"),
                        viewData);
    text = istrings[0];

    var oldInsertionPoint;
    // Do the indentation, if necessary.
    var remainingText = null;
    if (relativeIndent) {
        var initialCurrentPos = scimoz.currentPos;
        var initialAnchor = scimoz.anchor;

        // Sometimes the snippet will absorb the current selection,
        // so we don't want to keep it.
        var zapSelection = initialCurrentPos != initialAnchor;
        if (zapSelection) {
            scimoz.replaceSel("");
            initialCurrentPos = initialAnchor = scimoz.currentPos;
        }
        oldInsertionPoint = initialCurrentPos;
        var selectionEndLine = scimoz.lineFromPosition(initialCurrentPos);
        var selectionEndPoint = scimoz.getLineEndPosition(selectionEndLine);
        remainingText = scimoz.getTextRange(initialAnchor, selectionEndPoint);
        scimoz.targetStart = initialCurrentPos;
        scimoz.targetEnd = selectionEndPoint;
        scimoz.replaceTarget(0, "");

        // Figure out what the base indentation for the snippet should be
        // Assume that the line that starts the snippet insertion point
        // defines the indentation the snippet will use.
        
        var lines = text.split(eol_str);
        scimoz.lineEnd();
        for (var i = 1; i < lines.length; i++) {
            // Turn the snippet tabs into a space-equivalent value,
            // we only need to do this for starting whitespace though.
            var match = lines[i].match(leading_ws_re);
            if (match) {
                var whitespace = baseIndentation + match[1];
                var rest = match[2];
                var tab_pos;
                // If we have tabs in the preceeding whitespace of the
                // snippet, we need to convert them into spaces.
                while ((tab_pos = whitespace.search("\t")) >= 0) {
                    // Simulate pressing a tab by moving to the next multiple of indentWidth
                    whitespace = (whitespace.substr(0, tab_pos)
                                  + _repeatChar(' ', indentWidth - (tab_pos % indentWidth))
                                  + whitespace.substr(tab_pos + 1));
                }
                lines[i] = whitespace + match[2];
            } else {
                lines[i] = baseIndentation + lines[i];
            }
            if (useTabs) {
                var newindent = '';
                var rest = lines[i].replace(/^\s*/, '');
                newindent = lines[i].slice(0, lines[i].length-rest.length);
                newindent = newindent.replace(_repeatChar(' ', tabWidth), '\t', 'g');
                lines[i] = newindent + rest;
            }
        }
        text = lines.join(eol_str);
    } else {
        scimoz.replaceSel("");
        oldInsertionPoint = scimoz.currentPos;
    }


    // Determine and set the selection and cursor position.
    var anchor = text.indexOf(ANCHOR_MARKER);
    var currentPos = text.indexOf(CURRENTPOS_MARKER);
    if (anchor != -1 && currentPos != -1) {
        if (anchor < currentPos) {
            anchor = text.indexOf(ANCHOR_MARKER);
            text = text.replace(ANCHOR_MARKER, '');
            currentPos = text.indexOf(CURRENTPOS_MARKER);
            text = text.replace(CURRENTPOS_MARKER, '');
        } else {
            currentPos = text.indexOf(CURRENTPOS_MARKER);
            text = text.replace(CURRENTPOS_MARKER, '');
            anchor = text.indexOf(ANCHOR_MARKER);
            text = text.replace(ANCHOR_MARKER, '');
        }
    } else {
        anchor = 0;
        currentPos = 0;
    }
    
    try {
        var snippetInfo = ko.tabstops.parseLiveText(text);
    } catch(ex) {
        ko.dialogs.alert(ex.message, ex.snippet);
        log.exception(ex);
        return false;
    }
    if (remainingText) {
        // Don't process the text we snipped out as part of the snippet,
        // because we won't pull it out of cached parse trees.
        scimoz.insertText(oldInsertionPoint, remainingText);
    }
    ko.tabstops.insertLiveText(scimoz, oldInsertionPoint, snippetInfo);
    
    var enteredUndoableTabstop = false;
    if (hasTabStops) {
        // If there are tabstops, run cmd_indent which ends up running the tabstop handler
        // XXX calling cmd_indent is a hack, see bug #74565
        scimoz.currentPos = oldInsertionPoint;
        // concat(): js idiom for List#clone() -- the view consumes this table
        // as it steps through it.
        view.koDoc.setTabstopInsertionTable(snippetInfo.tabstopInsertionTable.length,
                                               snippetInfo.tabstopInsertionTable);
        scimoz.endUndoAction();
        view.moveToNextTabstop();
        enteredUndoableTabstop = true;
    } else if (setSelection) {
        scimoz.anchor = scimoz.positionAtChar(oldInsertionPoint,
                                              anchor);
        scimoz.currentPos = scimoz.positionAtChar(oldInsertionPoint,
                                                  currentPos);
    } else {
        // selection will be after snippet
        scimoz.anchor = scimoz.positionAtChar(scimoz.anchor,
                                              text.length);
        scimoz.currentPos = scimoz.anchor;
    }
    return enteredUndoableTabstop;
}

this._textFromEJSTemplate = function _textFromEJSTemplate(text, eol, eol_str, snippet) {
    // ejs will convert all \r and \r\n's to \n, so we'll need to
    // convert them back to eol_str on return
    // But make sure the snippet metadata isn't caught inside an EJS part
    var ptn = new RegExp('(<%)((?:(?!%>)[\\s\\S])*?)'
                         + '(' + ANCHOR_MARKER + "|" + CURRENTPOS_MARKER + ')'
                         + '([\\s\\S]*?)(%>)');
    while (ptn.test(text)) {
        text = text.replace(ptn, "$1$2$4$5$3");
    }
    var ejs = null;
    try {
        ejs = new ko.snippets.EJS(text);
    } catch(ex) {
        ex.fileName = ko.snippets.snippetPathShortName(snippet);
        var msg2 = _bundle.formatStringFromName("snippet exception details 2",
                                                [ex.fileName], 1);
        var msg3 = _bundle.formatStringFromName("snippet exception details 3",
                                                [ex.lineNumber + 1], 1);
        var msg = ex + "\n" + msg2 + "\n" + msg3;
        ko.dialogs.alert(null, msg,
                         _bundle.GetStringFromName("Error in snippet"));
        throw new ko.snippets.RejectedSnippet(_bundle.GetStringFromName("Error in snippet"), ex);
    }
    var ejsOut = ejs.render();
    text = (eol != Components.interfaces.koIDocument.EOL_LF
            ? ejsOut.replace(/\n/g, eol_str)
            : ejsOut);
    return text;
};

/* Utility functions */

function snippetMakeDisplayName(text) {
    // Strip leading whitespace.
    text = text.replace( /^\s+/, "" );
    // Strip trailing whitespace.
    text = text.replace( /\s+$/, "" );
    if (text.length > 30) {
        text = text.substr(0, 20) + ' ... ' + text.substr(text.length - 10, text.length)
    }
    // Compress remaining whitespace.
    text = text.replace( /\s+/g, " " );
    return text
}

}).apply(ko.projects);
