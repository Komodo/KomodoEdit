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

function peSnippet() {
    this.name = 'peSnippet';
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
peSnippet.prototype.constructor = peSnippet;

peSnippet.prototype.init = function() {
}

peSnippet.prototype.registerCommands = function() {
    ko.projects.extensionManager.registerCommand('cmd_insertSnippet', this);
    ko.projects.extensionManager.registerCommand('cmd_makeSnippetFromSelection', this);
}

peSnippet.prototype.registerEventHandlers = function() {
    ko.projects.extensionManager.addEventHandler(Components.interfaces.koIPart_snippet,'ondblclick',this);
}

peSnippet.prototype.registerMenus = function() {
    ko.projects.extensionManager.createMenuItem(Components.interfaces.koIPart_snippet,
                                    'Insert Snippet',
                                    'cmd_insertSnippet',
                                    null,
                                    null,
                                    true);
}

peSnippet.prototype.ondblclick = function(item,event) {
    if (item.type != 'snippet') return;
    ko.projects.snippetInsert(item);
}

peSnippet.prototype.supportsCommand = function(command, part) {
    if (command == 'cmd_makeSnippetFromSelection') return true;
    var items = ko.projects.active.getSelectedItems();
    if (items.length > 1) return false;

    if (!ko.projects.active) return false;
    switch (command) {
    case 'cmd_insertSnippet':
        return true;
    default:
        break;
    }
    return false;
}


peSnippet.prototype.isCommandEnabled = function(command, part) {
    var items = null
    if (ko.projects.active) {
        items = ko.projects.active.getSelectedItems();
    }
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
    case 'cmd_insertSnippet':
        if (!ko.projects.active ||
            items.length > 1 ||
            !ko.views.manager.currentView ||
            ko.views.manager.currentView.getAttribute('type') != 'editor')
                return false;

        // XXX should just return true here, but the Extension manager isn't calling
        // isCommandEnabled, so we'll just hide the menu item for now.
        if (!part)
            part = ko.projects.active.getSelectedItem();
        return ko.views.manager.currentView != null;
    default:
        break;
    }
    return false;
}

peSnippet.prototype.doCommand = function(command) {
    var item = null
    if (ko.projects.active) {
        item = ko.projects.active.getSelectedItem();
    }
    switch (command) {
    case 'cmd_insertSnippet':
        if (item) {
            ko.projects.snippetInsert(item);
        }
        break;
    case 'cmd_makeSnippetFromSelection':
        var snippet = ko.projects.addSnippetFromText(ko.views.manager.currentView.selection);
        ko.toolboxes.user.addItem(snippet,null);
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
        "chrome,close=yes,dependent=no,resizable=yes", obj);
}

this.addSnippet = function peSnippet_addSnippet(/*koIPart*/ parent)
{
    var snippet = parent.project.createPartFromType('snippet');
    snippet.setStringAttribute('name', 'New Snippet');
    snippet.setStringAttribute('set_selection', 'false');
    snippet.setStringAttribute('indent_relative', 'false');
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
        "chrome,close=yes,dependent=no,resizable=yes", obj);
}

this.addSnippetFromText = function AddSnippetFromText(snippettext, /*koIPart*/ parent) {
    if (typeof(parent) == 'undefined' || !parent) {
        parent = ko.projects.active.manager.getCurrentProject();
    }

    var escapedtext = snippettext;
    escapedtext = escapedtext.replace('%', '%%', 'g');
    var snippet = parent.project.createPartFromType('snippet');
    snippet.type = 'snippet';
    snippet.setStringAttribute('name', snippetMakeDisplayName(snippettext));
    snippet.setStringAttribute('set_selection', 'true');
    snippet.setStringAttribute('indent_relative', 'false');
    escapedtext = ANCHOR_MARKER + escapedtext + CURRENTPOS_MARKER;
    snippet.value = escapedtext;

    ko.projects.addItem(snippet, parent);
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

    scimoz.beginUndoAction();
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                        getService(Components.interfaces.koILastErrorService);
    try {
        try {
            ko.projects.snippetInsertImpl(snippet, view);
        } catch (ex) {
            var errno = lastErrorSvc.getLastErrorCode();
            if (errno == Components.results.NS_ERROR_ABORT) {
                // Command was cancelled.
            } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
                var errmsg = lastErrorSvc.getLastErrorMessage();
                ko.dialogs.alert("Error inserting snippet: " + errmsg);
            } else {
                log.error(ex);
                ko.dialogs.internalError(ex, "Error inserting snippet");
            }
        }
    } finally {
        ko.macros.recordPartInvocation(snippet);
        scimoz.endUndoAction();
    }
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
    var text = snippet.value;
    
    // Normalize the text to use the target view's preferred EOL.
    // (See bug 69535).
    var eol = view.document.new_line_endings;
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
    var text = text.replace(/\r\n|\n|\r/g, eol_str);
    
    // detect if there are tabstops before we interpolate the snippet text
    var hasTabStops = (text.match(/\[%tabstop\:/) != null);

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
    text = text.replace('%%', '%', 'g');
    
    var istrings = ko.interpolate.interpolate(
                        window,
                        [], // codes are not bracketed
                        [text], // codes are bracketed
                        snippet.getStringAttribute("name"),
                        viewData);
    text = istrings[0];

    var oldInsertionPoint;
    // Do the indentation, if necessary.
    if (relativeIndent) {
        // Work out the equivalent number of spaces to use for each tab.
        var tabequivalent = '';
        var useTabs = view.prefs.getBooleanPref("useTabs");
        var tabWidth = view.prefs.getLongPref("tabWidth");
        for (i = 0; i < tabWidth; i++) {
            tabequivalent += ' ';
        }

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
        var remainingText = scimoz.getTextRange(initialAnchor, selectionEndPoint);
        scimoz.targetStart = initialCurrentPos;
        scimoz.targetEnd = selectionEndPoint;
        scimoz.replaceTarget(0, "");

        // Figure out what the base indentation for the snippet should be
        scimoz.lineEnd();
        ko.commands.doCommand('cmd_newline');
        var createdLine = selectionEndLine + 1;
        var newLineStart = scimoz.positionFromLine(createdLine);
        var newLineEnd = scimoz.getLineEndPosition(createdLine);
        var baseIndentation = scimoz.getTextRange(newLineStart, newLineEnd);

        // Now get rid of the inserted blank line
        scimoz.targetStart = initialCurrentPos;
        scimoz.targetEnd = newLineEnd;
        scimoz.replaceTarget(0, "");
        scimoz.gotoPos(initialCurrentPos);

        var lines = text.split(eol_str);
        scimoz.lineEnd();
        var leading_ws_re = /^(\s+)(.*)/;
        for (i = 1; i < lines.length; i++) {
            // Turn the snippet tabs into a space-equivalent value,
            // we only need to do this for starting whitespace though.
            var match = lines[i].match(leading_ws_re);
            if (match) {
                var whitespace = baseIndentation + match[1];
                var rest = match[2];
                var tab_pos = whitespace.search("\t");
                // If we have tabs in the preceeding whitespace of the
                // snippet, we need to convert them into spaces.
                //XXX: Take into account tabs in baseIndentation as well.
                while (tab_pos >= 0) {
                    if (tab_pos % tabWidth) {
                        // Ick, the tab does not align according to the
                        // user's tabWidth preference, so we have to fix it.
                        var s = '';
                        for (var j=0; j < tabWidth - (tab_pos % tabWidth); j++) {
                            s += ' ';
                        }
                        whitespace = whitespace.substr(0, tab_pos) + s +
                            whitespace.substr(tab_pos+1);
                    } else {
                        whitespace = whitespace.replace('\t', tabequivalent);
                    }
                    tab_pos = whitespace.search("\t");
                }
                lines[i] = whitespace + match[2];
            } else {
                lines[i] = baseIndentation + lines[i];
            }
            if (useTabs) {
                var newindent = '';
                var rest = lines[i].replace(/^\s*/, '');
                newindent = lines[i].slice(0, lines[i].length-rest.length);
                newindent = newindent.replace(tabequivalent, '\t', 'g');
                lines[i] = newindent + rest;
            }
        }
        text = lines.join(eol_str) + remainingText;
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
    scimoz.insertText(oldInsertionPoint, text);
    
    if (setSelection) {
        scimoz.anchor = scimoz.positionAtChar(oldInsertionPoint,
                                              anchor);
        scimoz.currentPos = scimoz.positionAtChar(oldInsertionPoint,
                                                  currentPos);
    } else if (hasTabStops) {
        // If there are tabstops, run cmd_indent which ends up running the tabstop handler
        // XXX calling cmd_indent is a hack, see bug #74565
        ko.commands.doCommand('cmd_tabstopClear');
        ko.commands.doCommand('cmd_indent');
    } else {
        // selection will be after snippet
        scimoz.anchor = scimoz.positionAtChar(scimoz.anchor,
                                              text.length);
        scimoz.currentPos = scimoz.anchor;
    }
}


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

// backwards compat api, now we know why we have namespace properly
var peSnippet_addSnippet = ko.projects.addSnippet;
var AddSnippetFromText = ko.projects.addSnippetFromText;
var Snippet_insert = ko.projects.snippetInsert;
var snippet_editProperties = ko.projects.snippetProperties;
