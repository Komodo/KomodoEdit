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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.find)!='undefined') {
    if (ko.find.findNext) {
        ko.logging.getLogger('').warn("ko.find was already loaded, re-creating it.\n");
    }
} else {
    ko.find = {};
}

/* Komodo's Find and Replace general functions
 *
 * Presumably these are to used by the editor for findNext shortcuts and
 * by the Find and Replace dialog.
 *
 * Usage:
 *      ko.find.findNext(...)
 *      ko.find.findAll(...)
 *      ko.find.markAll(...)
 *      ko.find.replace(...)
 *      ko.find.replaceAll(...)
 *      ko.find.findAllInFiles(...)
 * where:
 *      "editor" is generally the editor object on which getFocusedView() et al
 *          can be called;
 *      "pattern" is the pattern string to search for;
 *      "replacement" is the replacement string to use; and
 *      "context" is a koIFindContext component.
 */

(function() {

//---- locals

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
const {XPCOMUtils} = Cu.import("resource://gre/modules/XPCOMUtils.jsm", {});

var lazy = {
};

XPCOMUtils.defineLazyGetter(lazy, "log", function() ko.logging.getLogger("find.functions"));
//lazy.log.setLevel(ko.logging.LOG_DEBUG);

// The find XPCOM service that does all the grunt work.
XPCOMUtils.defineLazyGetter(lazy, "findSvc", function()
    Cc["@activestate.com/koFindService;1"]
        .getService(Components.interfaces.koIFindService));

// The find session is used to hold find results and to determine when to stop
// searching (i.e. when we have come full circle).
XPCOMUtils.defineLazyGetter(lazy, "findSession", function()
    Cc["@activestate.com/koFindSession;1"]
        .getService(Components.interfaces.koIFindSession));

XPCOMUtils.defineLazyGetter(lazy, "ffBundle", function()
    Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/find/find_functions.properties"));



//--- internal support routines that Komodo's view system should have

this._isViewSearchable = function _IsViewSearchable(view) {
    var scimoz = null;
    try {
        scimoz = view && view.scintilla && view.scintilla.scimoz;
    } catch (ex) {
        return false;
    }
    return scimoz != null;
}

/**
 * Return the view after this one appropriate for searching. If there is no
 * such view (e.g. only one view), then return null.
 *
 * Dev Note: This in very inefficient for a lot of open files.
 *
 * XXX: Once all view types have viewIds we can do this more properly. I.e.
 *      don't default to 'editor' view 0 as the "next" view for any non-'editor'
 *      view.
 *
 * XXX: This internal method is required by the TODO addon.
 */
this._getNextView = function _GetNextView(editor, currView)
{
    // Filter out view types that cannot be searched.
    var views = editor.ko.views.manager.topView.getViews(true);
    var searchableViews = [];
    for (var i = 0; i < views.length; ++i) {
        //XXX Should the view grow a getType() method instead of having to do
        //    this? Does _this_ even work?
        if (views[i].getAttribute("type") == "editor") {
            searchableViews.push(views[i]);
        } else {
            lazy.log.debug("ko.find._getNextView: '"+views[i].getAttribute("type")+
                          "' view is not searchable");
        }
    }

    // Determine the index of the current one in this list.
    var currIndex = -1;
    if (currView.koDoc) {
        var currDisplayPath = currView.koDoc.displayPath;
        for (currIndex = 0; currIndex < searchableViews.length; ++currIndex) {
            if (searchableViews[currIndex].koDoc.displayPath == currDisplayPath)
                break;
        }
    }
    if (currIndex == searchableViews.length) {
        currIndex = -1;
    }

    // Find the next one.
    if (currIndex == -1) {
        if (searchableViews.length)
            return searchableViews[0];
        else
            return null;
    } else {
        if (searchableViews.length == 1) {
            return null;
        } else {
            var nextIndex = (currIndex + 1) % searchableViews.length;
            return searchableViews[nextIndex];
        }
    }
}

/**
 * Return the view before this one appropriate for searching. If there is no
 * such view (e.g. only one view), then return null.
 */
this._getPreviousView = function _GetPreviousView(editor, currView)
{
    // Filter out view types that cannot be searched.
    var views = editor.ko.views.manager.topView.getViews(true);
    var searchableViews = [];
    for (var i = 0; i < views.length; ++i) {
        var viewType = views[i].getAttribute("type")
        if (viewType == "editor") {
            searchableViews.push(views[i]);
        } else {
            lazy.log.debug("ko.find._getPreviousView: '" + viewType +
                          "' view is not searchable");
        }
    }

    // Determine the index of the current one in this list.
    var currIndex = -1;
    if (currView.koDoc) {
        var currDisplayPath = currView.koDoc.displayPath;
        for (currIndex = 0; currIndex < searchableViews.length; ++currIndex) {
            if (searchableViews[currIndex].koDoc.displayPath == currDisplayPath)
                break;
        }
    }
    if (currIndex == searchableViews.length) {
        currIndex = -1;
    }

    // Find the next one.
    if (currIndex == -1) {
        if (searchableViews.length)
            return searchableViews[searchableViews.length-1];
        else
            return null;
    } else {
        if (searchableViews.length == 1) {
            return null;
        } else {
            // XXX JavaScript get's modulus wrong for negative values, so add the
            //     .length to ensure the value is not negative.
            var prevIndex = (currIndex - 1 + searchableViews.length)
                            % searchableViews.length;
            return searchableViews[prevIndex];
        }
    }
}

this._getViewFromViewId = function _GetViewFromViewId(editor, displayPath)
{
    // Filter out view types that cannot be searched.
    var views = editor.ko.views.manager.topView.getViews(true);
    for (var i = 0; i < views.length; ++i) {
        if (views[i].uid == displayPath ||
            (views[i].koDoc && views[i].koDoc.displayPath == displayPath))
        {
            return views[i];
        }
    }
    return null;
}



//--- internal support routines


/**
 * Setup (i.e. do all the right things for find-session maintenance) and
 * find the next occurrence of "pattern".
 *
 * @param {DOMWindow|koIScintillaView} editor the main Komodo window in which
 *      to work, or the view to work with
 * @param {koIFindContext} context defines the scope in which to search,
 *      e.g., in a selection, just the current doc, all open docs.
 *      (if editor is a view, context.type cannot be FCT_ALL_OPEN_DOCS)
 * @param {string} pattern the pattern to search for.
 * @param {string} mode either 'find' or 'replace'. The maintenance of a
 *      find session needs to know if a find-next operation is in the
 *      context of finding or replacing.
 * @param {boolean} check_selection_only can be set true to have only
 *      consider the current selection in the document. This is used to
 *      handle the special case of priming a find-session for "Replace"
 *      when the current selection *is* the first hit. By default this
 *      is false.
 * @returns {koIFindResult|null} the found occurrence, or null if
 *      "pattern" wasn't found.
 */
this._setupAndFindNext = function _SetupAndFindNext(editor, context, pattern, mode,
                           check_selection_only /* =false */)
{
    if (typeof(check_selection_only) == 'undefined' || check_selection_only == null) check_selection_only = false;

    // abort if there is no current view
    var view = null;
    if (editor instanceof Components.interfaces.koIScintillaView) {
        lazy.log.debug("_setupAndFindNext: editor " + editor + " is a view");
        view = editor;
        if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
            lazy.log.exception("Trying to find in all open docs but only a view was given");
            throw new Components.Exception("Trying to find in all open docs but only a view was given",
                                           Components.results.NS_ERROR_INVALID_ARG);
        }
    } else {
        lazy.log.debug("_setupAndFindNext: editor " + editor + " is not a view");
        view = editor.ko.views.manager.currentView;
    }
    if (view == null) {
        return null;
    }

    if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS
        && ! ko.find._isViewSearchable(view))
    {
        if (lazy.findSvc.options.searchBackward) {
            view = ko.find._getPreviousView(editor, view);
        } else {
            view = ko.find._getNextView(editor, view);
        }
        if (view == null) {
            return null;
        }
    }

    // Get the necessary data (context may be other than the whole file).
    var scimoz = view.scimoz;
    // url: The unique view identifier.  We prefer koDoc.displayPath due to
    // backwards compatibility (and has the side effect of not searching
    // multiple views of the same file).
    var url = view.koDoc ? view.koDoc.displayPath : view.uid;
    var text; // the text to search (this is a subset of whole buffer if
              // searching within a selection)
    var contextOffset; // "text"s offset into the whole scimoz buffer
    var startOffset; // offset into "text" at which to begin searching
    var endOffset; // offset into "text" at which to stop searching
    if (check_selection_only)
    {
        var start, end;
        if (scimoz.anchor == scimoz.currentPos) {
            return null;
        } else if (scimoz.anchor < scimoz.currentPos) {
            start = scimoz.anchor;
            end = scimoz.currentPos;
        } else {
            start = scimoz.currentPos;
            end = scimoz.anchor;
        }
        text = scimoz.text;
        contextOffset = 0;
        startOffset = scimoz.charPosAtPosition(start);
        endOffset = scimoz.charPosAtPosition(end);
    }
    else if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS)
    {
        text = scimoz.text;
        contextOffset = 0;
        startOffset = scimoz.charPosAtPosition(-1);
        endOffset = text.length;
    }
    else if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION)
    {
        //TODO: fix this, send in all text and adjust offsets accordingly
        text = scimoz.getTextRange(
                    scimoz.positionAtChar(0, context.startIndex),
                    scimoz.positionAtChar(0, context.endIndex));
        contextOffset = context.startIndex;
        startOffset = scimoz.charPosAtPosition(-1) - contextOffset;
        endOffset = text.length;
    }
    else
    {
        throw new Error("unexpected context: name='" + context.name + "' type=" + context.type);
    }

    // Repeated searching forward works fine because a forward search sets up
    // for the next search when it selects the find result, which, as a
    // side-effect, sets the cursor position to the end of the find result.
    // This does not work in reverse because you keep getting the same result.
    // If there is a current find result (i.e. a selection) then set the
    // startOffset to the *start* of the selection.
    if (lazy.findSvc.options.searchBackward && scimoz.selText != "") {
        startOffset -= scimoz.selText.length;
    }

    // Special case: avoid duplicate matches for special patterns that match no
    // characters.
    // If there was a previous match in this URL that matched no characters
    // (e.g. "^", "$", "(...)*"), then advance the startOffset by one character
    // to ensure that this match does not happen again (because duplicate
    // matches end a find session).
    // XXX I *think* this is a valid fix, i.e. the result is what the user
    //     expects.
    var lastFindResult = lazy.findSession.GetLastFindResult();
    var unadjustedStartOffset = startOffset;
    if (lastFindResult && url == lastFindResult.url
        && lastFindResult.value.length == 0)
    {
        if (lazy.findSvc.options.searchBackward) {
            startOffset -= 1;
            if (startOffset < 0) {
                startOffset = ko.stringutils.bytelength(text.slice(0, text.length-1));
            }
        } else {
            startOffset += 1;
            if (startOffset > ko.stringutils.bytelength(text.slice(0, text.length-1))) {
                startOffset = 0;
            }
        }
    }

    // find it
    lazy.findSession.StartFind(pattern, url, lazy.findSvc.options,
                           // Lie to the find session manager about the
                           // possible startOffset adjustment, else the find
                           // session will reset itself.
                           // Note: these three are *char* offsets.
                           unadjustedStartOffset + contextOffset,
                           scimoz.charPosAtPosition(scimoz.selectionStart),
                           scimoz.charPosAtPosition(scimoz.selectionEnd),
                           mode);
    var findResult = null;
    while (1) {  // while not done searching all file(s)
        findResult = lazy.findSvc.find(url, text, pattern,
                                  startOffset, endOffset);
        // fix up the find result for context
        if (findResult != null) {
            findResult.start += contextOffset;
            findResult.end += contextOffset;
        }

        // if was not found then wrap (if have not already) and try again
        if (findResult == null && !lazy.findSession.wrapped) {
            lazy.findSession.wrapped = true;
            if (!lazy.findSvc.options.searchBackward) {
                startOffset = 0;
            } else {
                startOffset = ko.stringutils.bytelength(text);
            }
            continue;
        }

        // If finished searching the current document then:
        // - restore the cursor/selection state
        // - move to the next document (if we are searching more than one)
        if (findResult == null || lazy.findSession.WasAlreadyFound(findResult)
            || (mode == "replace" && lazy.findSession.IsRecursiveHit(findResult)))
        {
            // Switch to the next document to search, if there are any.
            if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
                var newView;
                if (lazy.findSvc.options.searchBackward) {
                    newView = ko.find._getPreviousView(editor, view);
                } else {
                    newView = ko.find._getNextView(editor, view);
                }
                if (newView == null)
                    break;  // Either there is no view or only the one.
                view = newView;
                url = view.koDoc ? view.koDoc.displayPath : view.uid;
                // restore the cursor/selection state in current document
                scimoz.setSel(lazy.findSession.fileSelectionStartPos, lazy.findSession.fileSelectionEndPos);
                //XXX Is this bad if the working view is not visible???
                scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(scimoz.currentPos));
                // we are done if this document has already been searched
                if (lazy.findSession.HaveSearchedThisUrlAlready(url)) {
                    break;
                }
                // make the switch
                scimoz = view.scimoz;
            } else {
                break;
            }

            // Save the start information in this doc.
            lazy.findSession.fileStartPos = scimoz.currentPos;
            lazy.findSession.fileSelectionStartPos = scimoz.selectionStart;
            lazy.findSession.fileSelectionEndPos = scimoz.selectionEnd;

            // Setup for a search in this document. (Currently only "all open
            // documents" should reach this code.)
            text = scimoz.text;
            if (lazy.findSvc.options.searchBackward) {
                startOffset = scimoz.length;
                endOffset = 0;
            } else {
                startOffset = 0;
                endOffset = scimoz.length;
            }
            contextOffset = 0;

            continue;
        }

        // fix up the find result for context and return it
        if (findResult != null) {
            lazy.findSession.NoteFind(findResult);
            return findResult;
        }
    }

    // Restore the editor state to that when this find session started.
    scimoz.hideSelection(true);
    if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
        // switch to the original url if it is still open
        var firstView = ko.find._getViewFromViewId(editor, lazy.findSession.firstUrl);
        if (editor.ko.views.manager.currentView.koDoc.displayPath
            != firstView.koDoc.displayPath) {
            firstView.makeCurrent(false);
        }
        scimoz.setSel(
            scimoz.positionAtChar(0, lazy.findSession.firstFileSelectionStartPos),
            scimoz.positionAtChar(0, lazy.findSession.firstFileSelectionEndPos));
    } else if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC) {
        scimoz.setSel(
            scimoz.positionAtChar(0, lazy.findSession.firstFileSelectionStartPos),
            scimoz.positionAtChar(0, lazy.findSession.firstFileSelectionEndPos));
    } else if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        // We have to investigate this but find session termination is broken and so we can't
        // elicit this code path.
        scimoz.setSel(
            scimoz.positionAtChar(0, context.startIndex),
            scimoz.positionAtChar(0, context.endIndex)); // XXXX
    } else {
        throw new Error("unexpected context: name='" + context.name + "' type=" + context.type);
    }
    scimoz.hideSelection(false);
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(scimoz.currentPos));
    return null;
}

this._doMarkerClearingReplacement = function _doMarkerClearingReplacement(editor, scimoz, startByte, endByte, replacementText) {
    scimoz.targetStart = startByte;
    scimoz.targetEnd = endByte;
    scimoz.replaceTarget(replacementText);
}

this._doMarkerPreservingReplacement = function _doMarkerPreservingReplacement(editor, scimoz, startByte, endByte, replacementText) {
    var lineStart = scimoz.lineFromPosition(startByte);
    var lineEnd = scimoz.lineFromPosition(endByte);
    var ISciMoz = Components.interfaces.ISciMoz;
    var eol = (scimoz.eOLMode == ISciMoz.SC_EOL_CRLF ? "\r\n" :
               scimoz.eOLMode == ISciMoz.SC_EOL_LF ? "\n" : "\r");
    var eol_re = new RegExp(eol, 'g');
    scimoz.beginUndoAction();
    try {
        // HACK: Make a no-op replacement to the char preceding the current
        // cursor position so that if this "Replace" operation is undone
        // the cursor will be restored to its starting place (with the
        // exception of starting at pos=0 -- in which case it'll end up
        // at pos=1). Bug 75059.
        var restoreLine = null;
        var restoreCol = null;
        if (scimoz.length != 0) {
            var restorePos = scimoz.currentPos;
            if (scimoz.currentPos == 0) {
                restorePos = scimoz.positionAfter(0);
            }
            restoreLine = scimoz.lineFromPosition(restorePos);
            restoreCol = scimoz.getColumn(restorePos);
            var prevPos = scimoz.positionBefore(restorePos);
            var prevChar = scimoz.getTextRange(prevPos, restorePos);
            
            scimoz.targetStart = prevPos;
            scimoz.targetEnd = restorePos;
            scimoz.replaceTarget(prevChar);
        }
        
        var numLinesInReplacement = (replacementText.match(eol_re) || "").length;
        if (numLinesInReplacement != (lineEnd - lineStart)) {
            // Lines differ, do quick repl
            return ko.find._doMarkerClearingReplacement(editor, scimoz, startByte, endByte, replacementText);
        }
        var nextMarkerLine = scimoz.markerNext(lineStart, 0xffff); // -1 if no more markers
        if (nextMarkerLine == -1 || nextMarkerLine > lineEnd) {
            return ko.find._doMarkerClearingReplacement(editor, scimoz, startByte, endByte, replacementText);
        }
        var replacementLines = replacementText.split(eol_re);
        var i, j, currText, replText;

        // possible optimization by moving backwards:
        // no need to update scintilla coordinates until we're done.
        for (i = lineEnd, j = replacementLines.length - 1; i >= lineStart; i--, j--) {
            var currLineStartPos = scimoz.positionFromLine(i);
            var currLineEndPos = scimoz.getLineEndPosition(i);
            // If we're in a selection, the start and ends of the selections
            // might not span entire lines.
            if (i == lineEnd) {
                currLineEndPos = endByte;
            }
            if (i == lineStart) {
                currLineStartPos = startByte;
            }
            var currText = scimoz.getTextRange(currLineStartPos, currLineEndPos);
            replText = replacementLines[j];
            if (currText != replText) {
                scimoz.targetStart = currLineStartPos;
                scimoz.targetEnd = currLineEndPos;
                scimoz.replaceTarget(replText);
            }
        }
        
    } finally {
        // Continue the HACK above to restore position after a possible
        // *redo*.
        if (restoreLine != null) {
            var restorePos = scimoz.positionAtColumn(restoreLine, restoreCol);
            var prevPos = scimoz.positionBefore(restorePos);
            var prevChar = scimoz.getTextRange(prevPos, restorePos);
            scimoz.targetStart = prevPos;
            scimoz.targetEnd = restorePos;
            scimoz.replaceTarget(prevChar);
        }

        scimoz.endUndoAction();
    }
    return null;  // stifle js
}

/**
 * Replace the last find result in the current find session, if there is
 * one and if it is genuine and current. No return value.
 */
this._replaceLastFindResult = function _ReplaceLastFindResult(editor, context, pattern, replacement)
{
    var view = editor.ko.views.manager.currentView;
    if (! ko.find._isViewSearchable(view)) {
        return;
    }
    /** @type {Components.interfaces.ISciMoz} */
    var scimoz = view.scintilla.scimoz;
    var url = view.koDoc.displayPath;
    var replaceResult = null;
    var findResult = lazy.findSession.GetLastFindResult();
    
    // Special case: If there is *no* last find result (i.e. the session
    // just started), but the current selection is a legitimate hit, then
    // we need to prime the session with that find result.
    // http://bugs.activestate.com/show_bug.cgi?id=27208
    if (findResult == null) {
        findResult = ko.find._setupAndFindNext(editor, context, pattern, "replace", true);
        ko.find.highlightClearAll(scimoz);
    }

    if (findResult != null) {
        var startByte = scimoz.positionAtChar(0, findResult.start);
        var endByte = scimoz.positionAtChar(startByte,
                                            findResult.end-findResult.start);
        var findText = scimoz.getTextRange(startByte, endByte);
        var startOffset;
        if (lazy.findSvc.options.searchBackward) {
            startOffset = findResult.end;
        } else {
            startOffset = findResult.start;
        }
        replaceResult = lazy.findSvc.replace(url, scimoz.text, pattern,
                                        replacement, startOffset, scimoz);
        if (replaceResult) {
            lazy.log.info("replace result (from FindSvc): s/"+replaceResult.value+
                         "/"+replaceResult.replacement+"/ at "+
                         replaceResult.start+"-"+replaceResult.end);
        }

        // - make the replacement (if the findResult is genuine)
        if (replaceResult &&
            findResult.start == replaceResult.start &&
            findResult.end == replaceResult.end &&
            findText == replaceResult.value)
        {
            startByte = scimoz.positionAtChar(0, replaceResult.start);
            endByte = scimoz.positionAtChar(startByte,
                replaceResult.end-replaceResult.start);
            ko.find._doMarkerPreservingReplacement(editor, scimoz, startByte, endByte,
                                           replaceResult.replacement);
            var replaceByteLength = ko.stringutils.bytelength(replaceResult.replacement);
            if (ko.find.highlightingEnabled()) {
                var DECORATOR_FIND_HIGHLIGHT = Components.interfaces.koILintResult.DECORATOR_FIND_HIGHLIGHT;
                scimoz.indicatorCurrent = DECORATOR_FIND_HIGHLIGHT;
                scimoz.indicatorFillRange(startByte, replaceByteLength);
            }
            scimoz.anchor = startByte;
            scimoz.currentPos = startByte + replaceByteLength;
            

            // fix up the search context as appropriate
            if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
                || context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS)
            {
                // nothing for now
            } else if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
                // adjust the context range for the change in length
                //XXX I think perhaps context.endIndex should be measured in
                //    chars and not in bytes (as this ko.stringutils.bytelength
                //    is converting it to).
                context.endIndex += replaceByteLength -
                                    ko.stringutils.bytelength(replaceResult.value);
            } else {
                throw new Error("unexpected context: name='" + context.name + "' type=" + context.type);
            }

            // Fill in some data for possible display in the "Replace Results"
            // tab and note the replacement.
            // XXX I don't believe these Note'd replacements are ever used
            //     since ReplaceAll was re-factored.
            var startLineNum = scimoz.lineFromPosition(startByte);
            var endLineNum = scimoz.lineFromPosition(endByte);
            var contextStartPos = scimoz.positionFromLine(startLineNum);
            var contextEndPos = scimoz.getLineEndPosition(endLineNum);
            replaceResult.context_ = scimoz.getTextRange(contextStartPos, contextEndPos);
            replaceResult.line = startLineNum + 1;
            replaceResult.column = replaceResult.start -
                                   scimoz.positionFromLine(startLineNum);
            lazy.findSession.NoteReplace(replaceResult);
        } else {
            lazy.log.info("find result is not genuine: skipping replace");
        }
    } else {
        lazy.log.info("no last find result to replace");
    }
}


/**
 * Find all instances of "pattern" with "replacement" in the current
 * view context.
 *
 * Note: koIFindSession.StartFind() is skipped because we don't need to
 * use this state mechanism to know when to terminate the session. Session
 * termination is handled via .NoteUrl() and .HaveSearchedThisUrlAlready().
 *
 * No return value.
 *
 * XXX: This internal method is required by the TODO addon.
 */
this._findAllInView = function _FindAllInView(editor, view, context, pattern, resultsView,
                        highlightMatches)
{
    var viewId = view.koDoc.displayPath;
    var scimoz = view.scintilla.scimoz;
    var text; // the text to search (this is a subset of whole buffer if
              // searching within a selection)
    var contextOffset; // "text"s offset into the whole scimoz buffer
    if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        text = scimoz.getTextRange(
                    scimoz.positionAtChar(0, context.startIndex),
                    scimoz.positionAtChar(0, context.endIndex));
        contextOffset = context.startIndex;
    } else {
        text = scimoz.text;
        contextOffset = 0;
    }

    lazy.findSvc.findallex(viewId, text, pattern, resultsView, contextOffset,
                      scimoz);

    if (highlightMatches) {
        lazy.findSvc.highlightlastresults(scimoz);
    }

    lazy.findSession.NoteUrl(viewId);
}


/**
 * Mark all instances of "pattern" with "replacement" in the current
 * view context.
 *
 * Note: koIFindSession.StartFind() is skipped because we don't need to
 * use this state mechanism to know when to terminate the session. Session
 * termination is handled via .NoteUrl() and .HaveSearchedThisUrlAlready().
 *
 * Returns true if hits were found in the view, false otherwise.
 */
this._markAllInView = function _MarkAllInView(editor, view, context, pattern)
{
    var viewId = view.koDoc.displayPath;
    var scimoz = view.scintilla.scimoz;
    var text; // the text to search (this is a subset of whole buffer if
              // searching within a selection)
    var contextOffset; // "text"s offset into the whole scimoz buffer
    if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        text = scimoz.getTextRange(context.startIndex, context.endIndex);
        contextOffset = context.startIndex;
    } else {
        text = scimoz.text;
        contextOffset = 0;
    }

    var countObj = new Object();
    var lines = new Array();
    lines = lazy.findSvc.findalllines(viewId, text, pattern, contextOffset,
                                 scimoz, countObj);
    var foundSome = lines.length > 0;
    ko.find._markLinesForViewId(editor, viewId, lines);

    lazy.findSession.NoteUrl(viewId);
    return foundSome;
}

/**
 * Replace all instances of "pattern" with "replacement" in the current
 * view context.
 *
 * Note: koIFindSession.StartReplace() is skipped because we don't need to
 * use this state mechanism to know when to terminate the session. Session
 * termination is handled via .NoteUrl() and .HaveSearchedThisUrlAlready().
 *
 * Returns the number of replacements made.
 */
this._replaceAllInView = function _ReplaceAllInView(editor, view, context, pattern, replacement,
                           firstOnLine, resultsView, highlightReplacements)
{
    var viewId = view.koDoc.displayPath;
    var scimoz = view.scintilla.scimoz;
    var text; // the text to search (this is a subset of whole buffer if
              // searching within a selection)
    var contextOffset; // "text"s offset into the whole scimoz buffer
    if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        text = scimoz.getTextRange(
                    scimoz.positionAtChar(0, context.startIndex),
                    scimoz.positionAtChar(0, context.endIndex));
        contextOffset = context.startIndex;
    } else {
        text = scimoz.text;
        contextOffset = 0;
    }

    // Find all possible replacements in this view.
    var numReplacementsObj = new Object();
    var replacementText = lazy.findSvc.replaceallex(viewId, text, pattern,
                                               replacement, firstOnLine,
                                               lazy.findSession,
                                               resultsView, contextOffset,
                                               scimoz, numReplacementsObj);
    var numReplacements = numReplacementsObj.value;

    if (numReplacements > 0) {
        if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
            ko.find._doMarkerPreservingReplacement(editor,
                                           scimoz,
                                           scimoz.positionAtChar(0, context.startIndex),
                                           scimoz.positionAtChar(0, context.endIndex),
                                           replacementText);
            // Restore the selection.
            scimoz.currentPos = scimoz.positionAtChar(0, context.startIndex);
            scimoz.anchor = scimoz.positionAtChar(0, context.startIndex)
                + ko.stringutils.bytelength(replacementText);
        } else {
            var line = scimoz.lineFromPosition(scimoz.currentPos);
            ko.find._doMarkerPreservingReplacement(editor,
                                           scimoz,
                                           0,
                                           scimoz.length,
                                           replacementText);
            // Put the cursor on the same line as before replacement.
            scimoz.anchor = scimoz.currentPos = scimoz.positionFromLine(line);
        }
    }

    //XXX Correct folds. See bug 25263.
    //    Are we losing other info like bookmarks?

    //XXX Is this bad if the working view is not visible???
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(scimoz.currentPos));

    lazy.findSession.NoteUrl(viewId);

    if (highlightReplacements) {
        lazy.findSvc.highlightlastresults(scimoz);
    }

    return numReplacements;
}

/**
 * Make the view for this find result current if necessary.
 * XXX Note that we are presuming that Komodo does not yet allow multiple
 *     views per document, which it eventually will. When this is possibly
 *     we must switch to storing unique view IDs in the find session.
 * XXX We are currently using view.koDoc.displayPath as the view's
 *     "unique id". The view system does not currently provide a way to
 *     getViewFromDisplayPath() so we roll our own.
 */
this._displayFindResult = function _DisplayFindResult(editor, findResult)
{
    //dump("display find result: "+findResult.url+": " + findResult.start +
    //     "-" + findResult.end + ": '" + findResult.value + "'\n");

    var win = editor, view = editor;
    if (editor instanceof Components.interfaces.koIScintillaView) {
        win = view.QueryInterface(Components.interfaces.nsIDOMNode)
                  .ownerDocument.defaultView;
    } else {
        view = editor.ko.views.manager.currentView;
    }

    var url = view.koDoc ? view.koDoc.displayPath : view.uid;
    if (url != findResult.url) {
        var view = ko.find._getViewFromViewId(win, findResult.url);
        if (view == null) {
            var err = "The view for a find result was closed before it could "+
                      "be displayed!";
            lazy.log.error(err);
            // Don't raise an error. Just attempt to limp along. This method
            // has no mechanism for signalling failure.
            return;
        }
        // we don't want to focus when find dialog is up.
        var noFocus = (win != window);
        win.ko.history.note_curr_loc(view);
        view.makeCurrent(noFocus);
    } else {
        win.ko.history.note_curr_loc(view);
    }

    // Jump to the find result and select it.
    // Jump to the _end_ (i.e. the start if going backwards) of the
    // result so that repeated finds are non-overlapping.
    var scimoz = view.scimoz;
    // Unfortunately this is going to be very slow -- I can't come up with a
    // way around this that will actually work without rewriting the find subsystem.
    var startByteIndex = ko.stringutils.bytelength(scimoz.text.slice(0, findResult.start));
    var endByteIndex = startByteIndex + ko.stringutils.bytelength(findResult.value);
    // Ensure folded lines are expanded. We *could* conceivably have search
    // results that span lines so should ensure that the whole selection is
    // visible. XXX should include every line in btwn here
    scimoz.gotoPos(startByteIndex);
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(startByteIndex));
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(endByteIndex));

    scimoz.setSel(startByteIndex, endByteIndex);

    scimoz.chooseCaretX();
}


/**
 * Mark all the given find results.
 */
this._markLinesForViewId = function _MarkLinesForViewId(editor, viewId, lines)
{
    var view = ko.find._getViewFromViewId(editor, viewId);
    if (!view) return;

    var isBookmarkable = false;
    try {
        view.QueryInterface(Components.interfaces.koIBookmarkableView);
        isBookmarkable = true;
    } catch (ex) {}
    if (!isBookmarkable) {
        lazy.log.warn("Could not bookmark find results for '"+viewId+
                     "', because that view does not support koIBookmarkableView.");
        return;
    }

    for (var i = 0; i < lines.length; ++i) {
        view.addBookmark(lines[i]);
    }
}


/**
 * Report the completion of a find session to the user.
 *
 * @param {DOMWindow} context is the koIFindContext for the find session.
 * @param {callback} msgHandler is a callback for displaying a
 *      message to the user. See ko.find.findNext documentation for details.
 */
this._uiForCompletedFindSession = function _UiForCompletedFindSession(context, msgHandler)
{
    var numFinds = lazy.findSession.GetNumFinds();
    var numReplacements = lazy.findSession.GetNumReplacements();

    // Put together an appropriate message.
    var msg = "";
    if (numFinds == 0) {
        let summary = Cc["@activestate.com/koTextUtils;1"]
                        .getService(Ci.koITextUtils)
                        .one_line_summary_from_text(lazy.findSession.GetPattern(), 30);
        msg = lazy.ffBundle.formatStringFromName("The pattern X was not found.",
                                             [summary], 1);
    } else if (numReplacements > 0) {
        msg = lazy.ffBundle.formatStringFromName("X of Y occurrence(s) were replaced.",
                                           [numReplacements, numFinds], 2);
    } else {
        msg = lazy.ffBundle.formatStringFromName("X occurrence(s) were found.",
                                           [numFinds], 1);
    }

    msgHandler("info", "find", msg);
}


/**
 * Report an error in the find service to the user.
 *
 * @param {string} context A short string giving context for the error,
 *      e.g. "find", "find all", "replace", ...
 * @param {exception} exc is an optional exception, if the error
 *      was trapped via try/catch. May be null.
 * @param {callback} msgHandler is a callback for displaying a
 *      message to the user. See ko.find.findNext documentation for details.
 *
 * The actual error message is pulled from the koILastErrorService.
 */
this._uiForFindServiceError = function _UiForFindServiceError(context, exc, msgHandler)
{
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                        .getService(Components.interfaces.koILastErrorService);
    var msg = "";
    msg = lastErrorSvc.getLastErrorMessage();
    if (!msg) {
        if (exc) {
            msg = "unexpected error: " + exc;
        } else {
            msg = "unexpected error in find service";
        }
    } else if (exc && exc.toString() != msg) {
        msg += " ("+exc+")";
    }

    msgHandler("error", context, msg);
}

var _Find_charsToEscape_re = /([\\\'\"])/g;
this.regexEscapeString = function _Find_RegexEscapeString(original) {
    return original.replace(_Find_charsToEscape_re, '\\$1').
           replace(/\r/g, '\\r').
           replace(/\n/g, '\\n');
}


/**
 * Return a callback appropriate for the 'msgHandler' callbacks that
 * will put a message on the status bar.
 */
this.getStatusbarMsgHandler = function _Find_GetStatusbarMsgHandler(editor)
{
    return function (level, context, msg) {
        require("notify/notify").send(context+": "+msg, "find", "searchReplace");
    }
}



//---- public functions

/**
 * Called by macros -- only difference with ko.find.findNext is that
 * contexttype is a constant, and the context needs to be created.
 *
 * XXX the APIs should be factored out so that these "inmacro" versions aren't
 *     necessary.
 */
this.findNextInMacro = function Find_FindNextInMacro(editor, contexttype, pattern, patternType,
                              caseSensitivity, searchBackward, matchWord,
                              mode, quiet, useMRU)
{
    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    // Stash old options
    old_patternType = lazy.findSvc.options.patternType;
    old_caseSensitivity = lazy.findSvc.options.caseSensitivity;
    old_searchBackward = lazy.findSvc.options.searchBackward;
    old_matchWord = lazy.findSvc.options.matchWord;

    lazy.findSvc.options.patternType = patternType;
    lazy.findSvc.options.caseSensitivity = caseSensitivity;
    lazy.findSvc.options.searchBackward = searchBackward;
    lazy.findSvc.options.matchWord = matchWord;

    ko.find.findNext(editor, context, pattern, mode, quiet, useMRU);

    // restore options
    lazy.findSvc.options.patternType = old_patternType;
    lazy.findSvc.options.caseSensitivity = old_caseSensitivity;
    lazy.findSvc.options.searchBackward = old_searchBackward;
    lazy.findSvc.options.matchWord = old_matchWord;
}

/**
 * Called by macros -- only difference with ko.find.findAll is that
 * contexttype is a constant, the context needs to be created, and options
 * need to be set (and unset).
 *
 * XXX the APIs should be factored out so that these "inmacro" versions
 *     aren't necessary.
 */
this.findAllInMacro = function Find_FindAllInMacro(editor, contexttype, pattern, patternType,
                             caseSensitivity, searchBackward, matchWord)
{
    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    // Stash old options
    old_patternType = lazy.findSvc.options.patternType;
    old_caseSensitivity = lazy.findSvc.options.caseSensitivity;
    old_searchBackward = lazy.findSvc.options.searchBackward;
    old_matchWord = lazy.findSvc.options.matchWord;

    lazy.findSvc.options.patternType = patternType;
    lazy.findSvc.options.caseSensitivity = caseSensitivity;
    lazy.findSvc.options.searchBackward = searchBackward;
    lazy.findSvc.options.matchWord = matchWord;

    ko.find.findAll(editor, context, pattern);

    // restore options
    lazy.findSvc.options.patternType = old_patternType;
    lazy.findSvc.options.caseSensitivity = old_caseSensitivity;
    lazy.findSvc.options.searchBackward = old_searchBackward;
    lazy.findSvc.options.matchWord = old_matchWord;
}

/**
 * Called by macros -- only difference with ko.find.markAll is that
 * contexttype is a constant, and the context needs to be created.
 *
 * XXX the APIs should be factored out so that these "inmacro" versions
 *     aren't necessary.
 */
this.markAllInMacro = function Find_MarkAllInMacro(editor, contexttype, pattern, patternType,
                             caseSensitivity, searchBackward, matchWord)
{
    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    // Stash old options
    old_patternType = lazy.findSvc.options.patternType;
    old_caseSensitivity = lazy.findSvc.options.caseSensitivity;
    old_searchBackward = lazy.findSvc.options.searchBackward;
    old_matchWord = lazy.findSvc.options.matchWord;

    lazy.findSvc.options.patternType = patternType;
    lazy.findSvc.options.caseSensitivity = caseSensitivity;
    lazy.findSvc.options.searchBackward = searchBackward;
    lazy.findSvc.options.matchWord = matchWord;

    ko.find.markAll(editor, context, pattern);

    // restore options
    lazy.findSvc.options.patternType = old_patternType;
    lazy.findSvc.options.caseSensitivity = old_caseSensitivity;
    lazy.findSvc.options.searchBackward = old_searchBackward;
    lazy.findSvc.options.matchWord = old_matchWord;
}

/**
 * Called by macros -- only difference with ko.find.replace is that
 * contexttype is a constant, and the context needs to be created.
 *
 * XXX the APIs should be factored out so that these "inmacro" versions
 *     aren't necessary.
 */
this.replaceInMacro = function Find_ReplaceInMacro(editor, contexttype, pattern, replacement,
                             patternType, caseSensitivity, searchBackward, matchWord)
{
    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    // Stash old options
    old_patternType = lazy.findSvc.options.patternType;
    old_caseSensitivity = lazy.findSvc.options.caseSensitivity;
    old_searchBackward = lazy.findSvc.options.searchBackward;
    old_matchWord = lazy.findSvc.options.matchWord;

    lazy.findSvc.options.patternType = patternType;
    lazy.findSvc.options.caseSensitivity = caseSensitivity;
    lazy.findSvc.options.searchBackward = searchBackward;
    lazy.findSvc.options.matchWord = matchWord;

    ko.find.replace(editor, context, pattern, replacement);

    // restore options
    lazy.findSvc.options.patternType = old_patternType;
    lazy.findSvc.options.caseSensitivity = old_caseSensitivity;
    lazy.findSvc.options.searchBackward = old_searchBackward;
    lazy.findSvc.options.matchWord = old_matchWord;
}


/**
 * Called by macros -- only difference with ko.find.replace is that
 * contexttype is a constant, and the context needs to be created.
 * XXX the APIs should be factored out so that these "inmacro" versions
 *     aren't necessary.
 *
 * @param {object} editor -- global window object
 * @param {int} contexttype -- one of the following koIFindContext values:
    FCT_CURRENT_DOC = 0, FCT_SELECTION, FCT_ALL_OPEN_DOCS,
    FCT_IN_FILES, FCT_IN_COLLECTION
 * @param {string} pattern
 * @param {string} replacement
 * @param {boolean} quiet
 * @param {int} patternType - one of the following koIFindOptions values:
    FOT_SIMPLE = 0, FOT_WILDCARD, FOT_REGEX_PYTHON
 * @param {int} caseSensitivity - one of the following koIFindOptions values:
    FOC_INSENSITIVE = 0, FOC_SENSITIVE, FOC_SMART
 * @param {boolean} searchBackward
 * @param {boolean} matchWord
 * 
 * @returns void    
 */   

this.replaceAllInMacro = function Find_ReplaceAllInMacro(editor, contexttype, pattern, replacement, quiet,
                                patternType, caseSensitivity, searchBackward, matchWord)
{
    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koRangeFindContext;1"]
            .createInstance(Components.interfaces.koIRangeFindContext);
    context.type = contexttype;
    if (contexttype == Components.interfaces.koIFindContext.FCT_SELECTION) {
        var msg = '';
        var view = editor.ko.views.manager.currentView;
        if (view) {
            var scimoz = view.scimoz;
            if (scimoz) {
                context.startIndex = scimoz.charPosAtPosition(scimoz.selectionStart);
                context.endIndex = scimoz.charPosAtPosition(scimoz.selectionEnd);
            } else {
                msg = lazy.ffBundle.GetStringFromName("No scintilla object on current view");
            }
        } else {
            msg = lazy.ffBundle.GetStringFromName("No current view");
        }
        if (msg) {
            require("notify/notify").send("macro-replace: " + msg, "searchReplace");
            return;
        }
    }

    // Stash old options
    old_patternType = lazy.findSvc.options.patternType;
    old_caseSensitivity = lazy.findSvc.options.caseSensitivity;
    old_searchBackward = lazy.findSvc.options.searchBackward;
    old_matchWord = lazy.findSvc.options.matchWord;

    lazy.findSvc.options.patternType = patternType;
    lazy.findSvc.options.caseSensitivity = caseSensitivity;
    lazy.findSvc.options.searchBackward = searchBackward;
    lazy.findSvc.options.matchWord = matchWord;

    ko.find.replaceAll(editor, context, pattern, replacement, quiet);

    // restore options
    lazy.findSvc.options.patternType = old_patternType;
    lazy.findSvc.options.caseSensitivity = old_caseSensitivity;
    lazy.findSvc.options.searchBackward = old_searchBackward;
    lazy.findSvc.options.matchWord = old_matchWord;
}

/**
 * Clear all of the current find and replace highlights.
 * 
 * @param scimoz {Components.interfaces.ISciMoz} - The scimoz instance.
 */
this.highlightClearAll = function Find_HighlightClearAll(scimoz) {
    var DECORATOR_FIND_HIGHLIGHT = Components.interfaces.koILintResult.DECORATOR_FIND_HIGHLIGHT;
    scimoz.indicatorCurrent = DECORATOR_FIND_HIGHLIGHT;
    scimoz.indicatorClearRange(0, scimoz.length);
}

/**
 * Clear any find highlights in the edited region.
 *
 * @param scimoz {Components.interfaces.ISciMoz} - Scintilla instance.
 * @param {int} position - The scimoz position (byte position)
 * @param {int} length - The number of affected bytes at this position.
 */
this.highlightClearPosition = function Find_HighlightClearPosition(scimoz, position, length) {
    lazy.log.deprecated("ko.find.highlightClearPosition is deprecated, " +
                       "use <view>._clearIndicatorsNearRange instead");
    var indic = Components.interfaces.koILintResult.DECORATOR_FIND_HIGHLIGHT;
    var range_start = scimoz.indicatorValueAt(indic, position) ?
                      scimoz.indicatorStart(indic, position) : position;
    var range_end = scimoz.indicatorValueAt(indic, position + length - 1) ?
                    scimoz.indicatorEnd(indic, position + length - 1) : position + length;
    scimoz.indicatorCurrent = indic;
    scimoz.indicatorClearRange(range_start, range_end - range_start);
}

/**
 * Highlight all additional find matches.
 *
 * @param {window} editor  - a reference to the komodo.xul main window
 * @param {Components.interfaces.koIFindContext} context - a koIFindContext instance
 * @param {string} pattern - the pattern being sought
 * @param {Number} timeout - [optional] number of milliseconds before timing out
 * @returns {boolean} Whether any matches have been found
 */
this.highlightAllMatches = function Find_HighlightAllMatches(scimoz, context, pattern, timeout) {
    var prefsSvc = Components.classes["@activestate.com/koPrefService;1"].
                            getService(Components.interfaces.koIPrefService);
    if (typeof(timeout) == "undefined") {
        timeout = prefsSvc.prefs.getLongPref("find-highlightTimeout");
    }
    if (timeout <= 0) {
        timeout = 500;  /* When set to zero, use minimum of 1/2 a second. */
    }
    if (!(context instanceof Components.interfaces.koIRangeFindContext)) {
        // We don't have a range context; search the whole document
        context = {startIndex: 0, endIndex: 0};
    }
    return lazy.findSvc.highlightall(scimoz,
                                 pattern,
                                 context.startIndex,
                                 context.endIndex,
                                 timeout /* timeout in ms */);
}

/**
 * Check to see if find highlighting is enabled.
 *
 * @returns {boolean} - true when enabled.
 */
this.highlightingEnabled = function Find_HighlightingEnabled() {
    var prefsSvc = Components.classes["@activestate.com/koPrefService;1"].
                            getService(Components.interfaces.koIPrefService);
    return prefsSvc.prefs.getBooleanPref("find-highlightEnabled");
}

/**
 * Find (and move to) the next occurrence of the given pattern.
 *
 * @param {window|koIScintillaView} editor - a reference to the komodo.xul main
 *        window, or a scintilla view in which to search
 * @param {Components.interfaces.koIFindContext} context - a koIFindContext
 * @param {string} pattern - the pattern being sought
 * @param {string} mode (optional) is either "find" (the default) or "replace",
 *        indicating if this is in the context of a replace UI.
 * @param {bool} quiet (optional) is a boolean indicating if UI (e.g. dialogs)
 *        may be used for presenting info, e.g. wrapped the document.
 *        Interactive search typically sets this to true. Default is false.
 * @param {bool} useMRU (optional) is a boolean indicating if the pattern should
 *        be loaded into the find MRU. Default is true.
 * @param msgHandler (optional) is a callback that is called for displaying
 *        a message during the find. It will be called like this:
 *            callback(level, context, message)
 *        where `level` is one of "info", "warn" or "error" and `message`
 *        is the message to display. The msgHandler is ignore if `quiet`
 *        is true. By default messages are sent to the statusbar.
 * @param {bool} highlightMatches (optional) when set, will highlight *all*
 *        matches in the context using a scintilla indicator.
 * @param {Number} highlightTimeout (optional) the maximum number of
 *        milliseconds to spend highlighting before giving up; defaults to using
 *        the user-specified preference value.
 *
 * @returns {boolean} True if the pattern was successfully found.
 */
this.findNext = function Find_FindNext(editor, context, pattern, mode /* ="find" */,
                       quiet /* =false */, useMRU /* =true */,
                       msgHandler /* =<statusbar notifier> */,
                       highlightMatches /* =true */,
                       highlightTimeout /* =from pref */,
                       displayResultCallback /* = null */)
{
    var win = editor, view;
    if (editor instanceof Components.interfaces.koIScintillaView) {
        win = editor.QueryInterface(Components.interfaces.nsIDOMNode)
                    .ownerDocument.defaultView;
        view = editor;
    } else {
        view = editor.ko.views.manager.currentView;
    }

    if (typeof(mode) == 'undefined' || mode == null) mode = "find";
    if (typeof(quiet) == 'undefined' || quiet == null) quiet = false;
    if (typeof(useMRU) == 'undefined' || useMRU == null) useMRU = true;
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(win);
    }
    if (typeof(highlightMatches) == 'undefined' || highlightMatches == null) highlightMatches = true;
    if (typeof(displayResultCallback) == 'undefined' || !displayResultCallback) {
        displayResultCallback = ko.find._displayFindResult;
    }
    if (!ko.find.highlightingEnabled()) {
        highlightMatches = false;
    }

    lazy.log.info("ko.find.findNext(editor="+editor+", context, pattern='"+pattern+
                 "', mode="+mode+", quiet="+quiet+", useMRU="+useMRU+")");

    if (win.ko.macros.recorder.mode == 'recording') {
        win.ko.macros.recorder.appendCode("ko.find.findNextInMacro(window, " +
                                    context.type + ", '" +
                                    ko.find.regexEscapeString(pattern) + "', " +
                                    lazy.findSvc.options.patternType + ", " +
                                    lazy.findSvc.options.caseSensitivity + ", " +
                                    lazy.findSvc.options.searchBackward + ", " +
                                    lazy.findSvc.options.matchWord + ", " +
                                    mode + ", " +
                                    quiet + ", " +
                                    useMRU +
                                    ");\n");
    }

    // Find the next match given the current state of the editor buffer and
    // do all the UI work to display the found result.
    // "mode" is either 'find' or 'replace'. The maintenance of a find session
    //      needs to know if a find-next operation is in the context of a
    //      finding or replacing.
    // Returns true iff a result was found and displayed.

    // Find the next "hit". If no result is returned then the find session is
    // complete.
    var findResult = null;
    var scimoz;
    if (highlightMatches) {
        scimoz = view.scimoz;
    }

    try {
        findResult = ko.find._setupAndFindNext(editor, context, pattern, mode);
    } catch (ex) {
        lazy.log.debug("_setupAndFindNext failed with " + ex);
        if (highlightMatches) {
            ko.find.highlightClearAll(scimoz);
        }
        if (!quiet)
            ko.find._uiForFindServiceError("find", ex, msgHandler);
        return null;
    }
    if (useMRU)
        ko.mru.add("find-patternMru", pattern, true);

    if (findResult) {
        lazy.log.debug("found a result " + findResult);
        displayResultCallback(editor, findResult);
        if (highlightMatches && (mode == "find")) {
            ko.find.highlightAllMatches(scimoz, context, pattern, highlightTimeout);
        }
    } else {
        if (highlightMatches) {
            ko.find.highlightClearAll(scimoz);
        }
        if (!quiet)
            ko.find._uiForCompletedFindSession(context, msgHandler);
        lazy.log.debug("Reset find session, because 'FindNext' did not find " +
                      "anything.");
        lazy.findSession.Reset();
    }
    return findResult != null;
}


/**
 * Find all occurrences of the given pattern.
 *
 * @param {window} editor  - a reference to the komodo.xul main window
 * @param {Components.interfaces.koIFindContext} context - a koIFindContext
 * @param {string} pattern - the pattern being sought
 * @param {string} patternAlias - shortened version of the pattern in use
 * @param msgHandler (optional) is a callback that is called for displaying
 *        a message during the find. It will be called like this:
 *            callback(level, context, message)
 *        where `level` is one of "info", "warn" or "error" and `message`
 *        is the message to display. The msgHandler is ignore if `quiet`
 *        is true. By default messages are sent to the statusbar.
 * @param {bool} highlightMatches (optional) when set, will highlight *all*
 *        matches in the context using a scintilla indicator.
 *
 * @returns {boolean} True if the pattern was successfully found.
 */
this.findAll = function Find_FindAll(editor, context, pattern, patternAlias,
                      msgHandler /* =<statusbar notifier> */,
                      highlightMatches /* =true */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(editor);
    }
    if (typeof(highlightMatches) == 'undefined' || highlightMatches == null) {
        highlightMatches = true;
    }
    if (!ko.find.highlightingEnabled()) {
        highlightMatches = false;
    }

    lazy.log.info("ko.find.findAll(editor, context, pattern='"+pattern+
                 "', patternAlias='"+patternAlias+"')");
    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("ko.find.findAllInMacro(window, " +
                                    context.type + ", '" +
                                    ko.find.regexEscapeString(pattern) + "', " +
                                    lazy.findSvc.options.patternType + ", " +
                                    lazy.findSvc.options.caseSensitivity + ", " +
                                    lazy.findSvc.options.searchBackward + ", " +
                                    lazy.findSvc.options.matchWord +
                                    ");\n");
    }

    var preferredResultsTab = lazy.findSvc.options.displayInFindResults2 ? 2 : 1;
    var resultsMgr = editor.ko.findresults.getTab(preferredResultsTab);
    if (resultsMgr == null)
        return null;
    resultsMgr.configure(pattern, patternAlias, null, context,
                         lazy.findSvc.options);
    resultsMgr.show();

    resultsMgr.searchStarted();
    var numFilesSearched = null;
    try {
        if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
            || context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
            lazy.log.debug("ko.find.findAll: find all in '"+
                          editor.ko.views.manager.currentView.koDoc.displayPath+"'\n");
            ko.find._findAllInView(editor, editor.ko.views.manager.currentView, context,
                           pattern, resultsMgr.view, highlightMatches);
        } else if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
            var view = editor.ko.views.manager.currentView;
            var viewId;
            numFilesSearched = 0;
            while (view) {
                if (ko.find._isViewSearchable(view)) {
                    viewId = view.koDoc.displayPath;
                    if (lazy.findSession.HaveSearchedThisUrlAlready(viewId)) {
                        lazy.log.debug("ko.find.findAll: have already searched '"+
                                      viewId+"'\n");
                        break;
                    }
    
                    lazy.log.debug("ko.find.findAll: find all in '"+viewId+"'\n");
                    ko.find._findAllInView(editor, view, context, pattern,
                                   resultsMgr.view, highlightMatches);
                    numFilesSearched += 1;
                }

                if (lazy.findSvc.options.searchBackward) {
                    view = ko.find._getPreviousView(editor, view);
                } else {
                    view = ko.find._getNextView(editor, view);
                }
            }
        } else {
            throw new Error("unexpected context: name='" + context.name + "' type=" +
                  context.type);
        }
        // Would be good to pass in the number of files in which hits were
        // found, but don't easily have that value and it's not a biggie.
        resultsMgr.searchFinished(true, resultsMgr.view.rowCount, null,
                                  numFilesSearched);
    } catch (ex) {
        ko.find._uiForFindServiceError("find all", ex, msgHandler);
        return null;
    }


    ko.mru.add("find-patternMru", pattern, true);
    var foundSome = resultsMgr.view.rowCount > 0;
    if (! foundSome) {
        var msg;
        if (typeof(patternAlias) != 'undefined' && patternAlias) {
            msg = lazy.ffBundle.formatStringFromName("No X were found in Y",
                                               [patternAlias, context.name], 2);
        } else {
            var text_utils = Components.classes["@activestate.com/koTextUtils;1"]
                               .getService(Components.interfaces.koITextUtils);
            var summary = text_utils.one_line_summary_from_text(pattern, 30);
            msg = lazy.ffBundle.formatStringFromName("X was not found in Y",
                                               [summary, context.name], 2);
        }
        msgHandler("warn", "find", msg);
    }
    lazy.findSession.Reset();

    return foundSome;
}


/**
 * Bookmark all occurrences of the given pattern.
 *
 * @param {window} editor  - a reference to the komodo.xul main window
 * @param {Components.interfaces.koIFindContext} context - a koIFindContext
 * @param {string} pattern - the pattern being sought
 * @param {string} patternAlias a name for the pattern (for display to user)
 * @param msgHandler (optional) is a callback that is called for displaying
 *        a message during the find. It will be called like this:
 *            callback(level, context, message)
 *        where `level` is one of "info", "warn" or "error" and `message`
 *        is the message to display. The msgHandler is ignore if `quiet`
 *        is true. By default messages are sent to the statusbar.
 *
 * @returns {boolean} True if there were bookmarks made.
 */
this.markAll = function Find_MarkAll(editor, context, pattern, patternAlias,
                      msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(editor);
    }
    
    // Returns true iff any matches were found and displayed.
    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("ko.find.markAllInMacro(window, " +
                                    context.type + ", '" +
                                    ko.find.regexEscapeString(pattern) + "', " +
                                    lazy.findSvc.options.patternType + ", " +
                                    lazy.findSvc.options.caseSensitivity + ", " +
                                    lazy.findSvc.options.searchBackward + ", " +
                                    lazy.findSvc.options.matchWord + ", " +
                                    ");\n");
    }

    var foundSome = false;
    var rv
    if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        rv = ko.find._markAllInView(editor, editor.ko.views.manager.currentView, context,
                            pattern);
        if (rv) foundSome = true;
    } else if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
        var view = editor.ko.views.manager.currentView;
        var viewId;
        while (view) {
            viewId = view.koDoc.displayPath;
            if (lazy.findSession.HaveSearchedThisUrlAlready(viewId)) {
                lazy.log.debug("ko.find.markAll: have alread searched '"+
                              viewId+"'\n");
                break;
            }

            rv = ko.find._markAllInView(editor, view, context, pattern);
            if (rv) foundSome = true;

            if (lazy.findSvc.options.searchBackward) {
                view = ko.find._getPreviousView(editor, view);
            } else {
                view = ko.find._getNextView(editor, view);
            }
        }
    } else {
        throw new Error("unexpected context: name='" + context.name + "' type=" +
              context.type);
    }

    ko.mru.add("find-patternMru", pattern, true);
    if (! foundSome) {
        var msg;
        if (typeof(patternAlias) != 'undefined' && patternAlias) {
            msg = lazy.ffBundle.formatStringFromName("No X were found in Y",
                                               [summary, context.name], 2);
        } else {
            var text_utils = Components.classes["@activestate.com/koTextUtils;1"]
                               .getService(Components.interfaces.koITextUtils);
            var summary = text_utils.one_line_summary_from_text(pattern, 30);
            msg = lazy.ffBundle.formatStringFromName("X was not found in Y",
                                               [summary, context.name], 2);
        }
        msgHandler("warn", "find", msg);
    }
    lazy.findSession.Reset();

    return foundSome;
}


/**
 * Replace one occurrence of the given pattern.
 *
 * @param {window} editor  - a reference to the komodo.xul main window
 * @param {Components.interfaces.koIFindContext} context - a koIFindContext
 * @param {string} pattern - the pattern being sought
 * @param {string} replacement - the pattern to replace with
 * @param msgHandler (optional) is a callback that is called for displaying
 *        a message during the find. It will be called like this:
 *            callback(level, context, message)
 *        where `level` is one of "info", "warn" or "error" and `message`
 *        is the message to display. The msgHandler is ignore if `quiet`
 *        is true. By default messages are sent to the statusbar.
 *
 * @returns {boolean} True if there was a replacement made.
 */
this.replace = function Find_Replace(editor, context, pattern, replacement,
                      msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(editor);
    }

    // Replace the currently selected find result (if there is one) and find
    // the next occurrence of the current pattern. Returns true iff a next
    // occurence of the pattern was found and hilighted.
    lazy.log.info("ko.find.replace(editor, context, pattern='"+pattern+
                 "', replacement='"+replacement+"')");

    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("ko.find.replaceInMacro(window, " +
                                    context.type + ", '" +
                                    ko.find.regexEscapeString(pattern) + "', '" +
                                    ko.find.regexEscapeString(replacement) + "', " +
                                    lazy.findSvc.options.patternType + ", " +
                                    lazy.findSvc.options.caseSensitivity + ", " +
                                    lazy.findSvc.options.searchBackward + ", " +
                                    lazy.findSvc.options.matchWord +
                                    ");\n");
    }

    var view = editor.ko.views.manager.currentView;
    var findResult = null;
    if (view != null) {
        // Here is how a replace works:
        //  - the first "Replace" will just identify the replacement to make
        //  - the second "Replace" will make that replacement and find the next
        //  - and so on...

        // replace the current find result if there is one
        try {
            lazy.log.info("ko.find.replace: replace last find result");
            ko.find._replaceLastFindResult(editor, context, pattern, replacement);
        } catch (ex) {
            ko.find._uiForFindServiceError("replace", ex, msgHandler);
            return null;
        }

        // find the next one
        try {
            lazy.log.info("ko.find.replace: find next hit");
            findResult = ko.find._setupAndFindNext(editor, context, pattern,
                                           'replace');
            if (findResult) {
                lazy.log.info("ko.find.replace: found next hit: "+
                             findResult.start+"-"+findResult.end+": '"+
                             findResult.value+"'");
            }
        } catch (ex) {
            ko.find._uiForFindServiceError("replace", ex, msgHandler);
            return null;
        }
        ko.mru.add("find-patternMru", pattern, true);

        // Do the appropriate UI work for results.
        if (findResult == null) {
            ko.find._uiForCompletedFindSession(context, msgHandler);
            //lazy.log.debug("Reset find session, because 'Replace' action "
            //              + "returned no result.");
            lazy.findSession.Reset();
        } else {
            ko.find._displayFindResult(editor, findResult);
        }
    }
    return findResult != null;
}


/**
 * Replace all occurrences of the given pattern.
 *
 * @param {window} editor  - a reference to the komodo.xul main window
 * @param {Components.interfaces.koIFindContext} context - a koIFindContext
 * @param {string} pattern - the pattern being sought
 * @param {string} replacement - the pattern to replace with
 * @param {boolean} showReplaceResults - whether to show the results tab
 * @param {boolean} firstOnLine A boolean indicating, if true, that only
 *      the first hit on a line should be replaced. Default is false. (This
 *      is to support Vi's replace with the 'g' flag.)
 * @param msgHandler (optional) is a callback that is called for displaying
 *        a message during the find. It will be called like this:
 *            callback(level, context, message)
 *        where `level` is one of "info", "warn" or "error" and `message`
 *        is the message to display. The msgHandler is ignore if `quiet`
 *        is true. By default messages are sent to the statusbar.
 * @param {boolean} highlightReplacements To highlight the replacements made.
 *
 * @returns {boolean} True if there were replacements made.
 */
this.replaceAll = function Find_ReplaceAll(editor, context, pattern, replacement,
                         showReplaceResults /* =false */,
                         firstOnLine /* =false */,
                         msgHandler /* =<statusbar notifier> */,
                         highlightReplacements /* =true */)
{
    if (typeof(showReplaceResults) == "undefined") showReplaceResults = false;
    if (typeof(firstOnLine) == "undefined" || firstOnLine == null) {
        firstOnLine = false;
    }
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(editor);
    }
    if (typeof(highlightReplacements) == 'undefined' || highlightReplacements == null) {
        highlightReplacements = true;
    }
    if (!ko.find.highlightingEnabled()) {
        highlightReplacements = false;
    }

    lazy.log.info("ko.find.replaceAll(editor, context, pattern='"+pattern
                 +"', replacement='"+replacement
                 +"', showReplaceResults="+showReplaceResults
                 +"', firstOnLine="+firstOnLine+")\n");

    if (editor.ko.macros.recorder.mode == 'recording') {
        //TODO: Support 'firstOnLine' here.
        editor.ko.macros.recorder.appendCode("ko.find.replaceAllInMacro(window, " +
                                    context.type + ", '" +
                                    ko.find.regexEscapeString(pattern) + "', '" +
                                    ko.find.regexEscapeString(replacement) + "', " +
                                    showReplaceResults + ", " +
                                    lazy.findSvc.options.patternType + ", " +
                                    lazy.findSvc.options.caseSensitivity + ", " +
                                    lazy.findSvc.options.searchBackward + ", " +
                                    lazy.findSvc.options.matchWord +
                                    ");\n");
    }

    var resultsMgr = null;
    var resultsView = null;
    var numFiles = null;
    var numFilesSearched = null;
    if (showReplaceResults) {
        var preferredResultsTab = lazy.findSvc.options.displayInFindResults2 ? 2 : 1;
        resultsMgr = editor.ko.findresults.getTab(preferredResultsTab);
        if (resultsMgr == null)
            return false;
        resultsMgr.configure(pattern, null, replacement, context,
                             lazy.findSvc.options);
        resultsMgr.show();
        resultsView = resultsMgr.view;
        resultsMgr.searchStarted();

        // Should add results already in session.
        var countObj = new Object();
        var replaceResults = new Object();
        var rrs = lazy.findSession.GetReplacements(countObj);
        var i, rr;
        for (i = 0; i < rrs.length; ++ i) {
            rr = rrs[i];
            resultsMgr.addReplaceResult(
                "hit",
                rr.url, rr.start, rr.end, rr.value, rr.replacement, rr.url,
                rr.line, rr.column, rr.context_);
        }
    }
    
    // Really only want to note this location if the "replace all" actually
    // replaces something. Good enough just always do it for now.
    editor.ko.history.note_curr_loc();

    var numReplacements = lazy.findSession.GetNumReplacements();
    var nr;
    if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        lazy.log.debug("ko.find.replaceAll: replace all in '"+
                      editor.ko.views.manager.currentView.koDoc.displayPath+"'\n");
        nr = ko.find._replaceAllInView(editor, editor.ko.views.manager.currentView, context,
                               pattern, replacement, firstOnLine, resultsView,
                               highlightReplacements);
        numReplacements += nr;
    } else if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
        var view = editor.ko.views.manager.currentView;
        var viewId;
        numFiles = numFilesSearched = 0;
        while (view) {
            if (ko.find._isViewSearchable(view)) {
                viewId = view.koDoc.displayPath;
                if (lazy.findSession.HaveSearchedThisUrlAlready(viewId)) {
                    lazy.log.debug("ko.find.replaceAll: have already searched '"+
                                  viewId+"'\n");
                    break;
                }
    
                lazy.log.debug("ko.find.replaceAll: replace all in '"+viewId+"'\n");
                nr = ko.find._replaceAllInView(editor, view, context, pattern,
                                       replacement, firstOnLine, resultsView,
                                       highlightReplacements);
                numReplacements += nr;
                if (nr) {
                    numFiles += 1;
                }
                numFilesSearched += 1;
            }

            if (lazy.findSvc.options.searchBackward) {
                view = ko.find._getPreviousView(editor, view);
            } else {
                view = ko.find._getNextView(editor, view);
            }
        }
    } else {
        throw new Error("unexpected context: name='" + context.name + "' type=" +
              context.type);
    }
    if (showReplaceResults) {
        resultsMgr.searchFinished(true, numReplacements, numFiles,
                                  numFilesSearched);
    }

    ko.mru.add("find-patternMru", pattern, true);
    var msg;
    if (numReplacements == 0) {
        var text_utils = Components.classes["@activestate.com/koTextUtils;1"]
                           .getService(Components.interfaces.koITextUtils);
        var summary = text_utils.one_line_summary_from_text(pattern, 30);
        msg = (lazy.ffBundle.formatStringFromName("X was not found in Y",
                                           [summary, context.name], 2)
               + " "
               + lazy.ffBundle.GetStringFromName("No changes were made."));
        msgHandler("info", "find", msg);
    } else {
        msg = lazy.ffBundle.formatStringFromName("Made X replacement(s) in Y",
                                           [numReplacements, context.name], 2);
        require("notify/notify").send(msg, "searchReplace");
    }
    lazy.findSession.Reset();

    return numReplacements != 0;
}


/**
 * Find all hits in files.
 *
 * @param {DOMWindow} editor the main Komodo window in which to work
 * @param {Components.interfaces.koIFindContext} context
 * @param {string} pattern the pattern to search for.
 * @param {string} patternAlias a name for the pattern (for display to user)
 * @param {callback} msgHandler is an optional callback for displaying a
 *      message to the user. See ko.find.findNext documentation for details.
 *
 * @returns {boolean} True if the operation was successful. False if there
 *      was an error or find was aborted.
 */
this.findAllInFiles = function Find_FindAllInFiles(editor, context, pattern, patternAlias,
                             msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(editor);
    }

    lazy.log.info("ko.find.findAllInFiles(editor, context, pattern='"+pattern+
                 "', patternAlias='"+patternAlias+"')");

    //TODO macro recording stuff for this

    var resultsMgr = editor.ko.findresults.getTab();
    if (resultsMgr == null)
        return false;
    resultsMgr.configure(pattern, patternAlias, null, context,
                         lazy.findSvc.options);
    resultsMgr.show(true);

    try {
        lazy.findSvc.findallinfiles(resultsMgr.id, pattern, resultsMgr);
    } catch (ex) {
        ko.find._uiForFindServiceError("find all in files", ex, msgHandler);
        resultsMgr.clear();
        return false;
    }
    return true;
}


/**
 * Replace all hits in files.
 *
 * @param {DOMWindow} editor the main Komodo window in which to work
 * @param context {Components.interfaces.koIFindContext} defines the
 *      scope in which to search, e.g., in a selection, just the current
 *      doc, all open docs.
 * @param {string} pattern the pattern to search for.
 * @param {string} repl the replacement string.
 * @param {boolean} confirm Whether to confirm replacements. Optional,
 *      true by default.
 * @param {callback} msgHandler is an optional callback for displaying a
 *      message to the user. See ko.find.findNext documentation for details.
 *
 * @returns {boolean} True if the operation was successful. False if there
 *      was an error or replacement was aborted.
 */
this.replaceAllInFiles = function Find_ReplaceAllInFiles(editor, context, pattern, repl,
                                confirm /* =true */,
                                msgHandler /* =<statusbar notifier> */)
{
    if (typeof(confirm) == 'undefined' || confirm == null) confirm = true;
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = ko.find.getStatusbarMsgHandler(editor);
    }

    lazy.log.info("ko.find.replaceAllInFiles(editor, context, pattern='"+pattern+
                 "', repl='"+repl+"', confirm="+confirm+")");

    //TODO macro recording stuff for this

    if (confirm) {
        // Pass off to the "Confirm Replacements" dialog.
        // This dialog runs the replacer thread and either returns it
        // (a koIConfirmReplacerInFiles instance) -- with a set of
        // confirmed replacements to make -- or return null, if the
        // replacement was aborted.
        var args = {
            "editor": editor,
            "context": context,
            "pattern": pattern,
            "repl": repl
        };
        ko.windowManager.openDialog(
            "chrome://komodo/content/find/confirmrepl.xul",
            "komodo_confirm_repl",
            "chrome,modal,titlebar,resizable=yes",
            args);
        var replacer = args.replacer;
        if (!replacer) {
            // The replacement was aborted.
            return false;
        } else if (replacer.num_hits == 0) {
            // No replacements were found.
            msgHandler("info", "replace", lazy.ffBundle.GetStringFromName("No replacements were found."));
            return false;
        }
        
        // The replacement completed, and there were hits.
        // I.e., we now have to make those replacements.
        var resultsMgr = editor.ko.findresults.getTab();
        if (resultsMgr == null) {
            //TODO: It really isn't a good thing that we can abort the
            //      "Replace in Files" at this point just because we
            //      don't have a free "Find Results" tab in which to
            //      show the results. The *best* fix for this is
            //      to just have unlimited find results tabs (there is
            //      a separate bug for this).
            return false;
        }
        resultsMgr.configure(pattern, null, repl, context,
                             lazy.findSvc.options,
                             true);  // opSupportsUndo
        resultsMgr.show();
        replacer.commit(resultsMgr);
        editor.ko.window.checkDiskFiles(); // Ensure changes *open* files get reloaded.
        return true;

    } else {
        var resultsMgr = editor.ko.findresults.getTab();
        if (resultsMgr == null)
            return false;
        resultsMgr.configure(pattern, null, repl, context,
                             lazy.findSvc.options,
                             true); // opSupportsUndo
        resultsMgr.show();
    
        try {
            lazy.findSvc.replaceallinfiles(resultsMgr.id, pattern, repl,
                                       resultsMgr);
        } catch (ex) {
            var msg = lazy.ffBundle.GetStringFromName("replace all in files");
            ko.find._uiForFindServiceError(msg, ex, msgHandler);
            resultsMgr.clear();
            return false;
        }
    }

    return true;
}

}).apply(ko.find);
