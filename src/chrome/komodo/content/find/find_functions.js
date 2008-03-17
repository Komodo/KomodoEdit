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

/* Komodo's Find and Replace general functions
 *
 * Presumably these are to used by the editor for findNext shortcuts and
 * by the Find and Replace dialog.
 *
 * Usage:
 *      Find_FindNext(...)
 *      Find_FindAll(...)
 *      Find_MarkAll(...)
 *      Find_Replace(...)
 *      Find_ReplaceAll(...)
 *      Find_FindAllInFiles(...)
 * where:
 *      "editor" is generally the editor object on which getFocusedView() et al
 *          can be called;
 *      "pattern" is the pattern string to search for;
 *      "replacement" is the replacement string to use; and
 *      "context" is a koIFindContext component.
 */


//---- globals

var findLog = ko.logging.getLogger("find_functions");
//findLog.setLevel(ko.logging.LOG_DEBUG);

var findSvc = null; // the find XPCOM service that does all the grunt work

// The find session is used to hold find results and to determine when to stop
// searching (i.e. when we have come full circle).
var gFindSession = Components.classes["@activestate.com/koFindSession;1"]
                   .getService(Components.interfaces.koIFindSession);


//--- internal support routines that Komodo's view system should have

function _IsViewSearchable(view) {
    var scimoz = null;
    try {
        scimoz = view && view.scintilla && view.scintilla.scimoz;
    } catch (ex) {
        return false;
    }
    return scimoz != null;
}

// Return the view after this one appropriate for searching. If there is no
// such view (e.g. only one view), then return null.
//
// Dev Note: This in very inefficient for a lot of open files.
//
//XXX Once all view types have viewIds we can do this more properly. I.e.
//    don't default to 'editor' view 0 as the "next" view for any non-'editor'
//    view.
function _GetNextView(editor, currView)
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
            findLog.debug("_GetNextView: '"+views[i].getAttribute("type")+
                          "' view is not searchable");
        }
    }

    // Determine the index of the current one in this list.
    var currIndex = -1;
    if (currView.document) {
        var currDisplayPath = currView.document.displayPath;
        for (currIndex = 0; currIndex < searchableViews.length; ++currIndex) {
            if (searchableViews[currIndex].document.displayPath == currDisplayPath)
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

// Return the view before this one appropriate for searching. If there is no
// such view (e.g. only one view), then return null.
function _GetPreviousView(editor, currView)
{
    // Filter out view types that cannot be searched.
    var views = editor.ko.views.manager.topView.getViews(true);
    var searchableViews = [];
    for (var i = 0; i < views.length; ++i) {
        var viewType = views[i].getAttribute("type")
        if (viewType == "editor") {
            searchableViews.push(views[i]);
        } else {
            findLog.debug("_GetPreviousView: '" + viewType +
                          "' view is not searchable");
        }
    }

    // Determine the index of the current one in this list.
    var currIndex = -1;
    if (currView.document) {
        var currDisplayPath = currView.document.displayPath;
        for (currIndex = 0; currIndex < searchableViews.length; ++currIndex) {
            if (searchableViews[currIndex].document.displayPath == currDisplayPath)
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

function _GetViewFromViewId(editor, displayPath)
{
    // Filter out view types that cannot be searched.
    var views = editor.ko.views.manager.topView.getViews(true);
    for (var i = 0; i < views.length; ++i) {
        if (views[i].document && views[i].document.displayPath == displayPath) {
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
 * @param editor {DOMWindow} the main Komodo window in which to work
 * @param context {koIFindContext} defines the scope in which to search,
 *      e.g., in a selection, just the current doc, all open docs.
 * @param pattern {string} the pattern to search for.
 * @param mode {string} either 'find' or 'replace'. The maintenance of a
 *      find session needs to know if a find-next operation is in the
 *      context of finding or replacing.
 * @param check_selection_only {boolean} can be set true to have only
 *      consider the current selection in the document. This is used to
 *      handle the special case of priming a find-session for "Replace"
 *      when the current selection *is* the first hit. By default this
 *      is false.
 * @returns {koIFindResult|null} the found occurrence, or null if
 *      "pattern" wasn't found.
 */
function _SetupAndFindNext(editor, context, pattern, mode,
                           check_selection_only /* =false */)
{
    if (typeof(check_selection_only) == 'undefined' || check_selection_only == null) check_selection_only = false;

    // abort if there is no current view
    var view = editor.ko.views.manager.currentView;
    if (view == null) {
        return null;
    }

    if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS
        && ! _IsViewSearchable(view))
    {
        if (findSvc.options.searchBackward) {
            view = _GetPreviousView(editor, view);
        } else {
            view = _GetNextView(editor, view);
        }
        if (view == null) {
            return null;
        }
    }

    // Get the necessary data (context may be other than the whole file).
    var scimoz = view.scintilla.scimoz;
    // url: The unique view identifier. This is not ideal. Eventually the view
    //      system should grow unique view ids that can be used here.
    var url = view.document.displayPath;
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
        throw("unexpected context: name='" + context.name + "' type=" + context.type);
    }

    // Repeated searching forward works fine because a forward search sets up
    // for the next search when it selects the find result, which, as a
    // side-effect, sets the cursor position to the end of the find result.
    // This does not work in reverse because you keep getting the same result.
    // If there is a current find result (i.e. a selection) then set the
    // startOffset to the *start* of the selection.
    if (findSvc.options.searchBackward && scimoz.selText != "") {
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
    var lastFindResult = gFindSession.GetLastFindResult();
    var unadjustedStartOffset = startOffset;
    if (lastFindResult && url == lastFindResult.url
        && lastFindResult.value.length == 0)
    {
        if (findSvc.options.searchBackward) {
            startOffset -= 1;
            if (startOffset < 0) {
                startOffset = stringutils_bytelength(text.slice(0, text.length-1));
            }
        } else {
            startOffset += 1;
            if (startOffset > stringutils_bytelength(text.slice(0, text.length-1))) {
                startOffset = 0;
            }
        }
    }

    // find it
    gFindSession.StartFind(pattern, url, findSvc.options,
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
        findResult = findSvc.find(url, text, pattern,
                                  startOffset, endOffset);
        // fix up the find result for context
        if (findResult != null) {
            findResult.start += contextOffset;
            findResult.end += contextOffset;
        }

        // if was not found then wrap (if have not already) and try again
        if (findResult == null && !gFindSession.wrapped) {
            gFindSession.wrapped = true;
            if (!findSvc.options.searchBackward) {
                startOffset = 0;
            } else {
                startOffset = stringutils_bytelength(text.slice(0, text.length-1));
            }
            continue;
        }

        // If finished searching the current document then:
        // - restore the cursor/selection state
        // - move to the next document (if we are searching more than one)
        if (findResult == null || gFindSession.WasAlreadyFound(findResult)
            || (mode == "replace" && gFindSession.IsRecursiveHit(findResult)))
        {
            // Switch to the next document to search, if there are any.
            if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
                var newView;
                if (findSvc.options.searchBackward) {
                    newView = _GetPreviousView(editor, view);
                } else {
                    newView = _GetNextView(editor, view);
                }
                if (newView == null)
                    break;  // Either there is no view or only the one.
                view = newView;
                url = view.document.displayPath;
                // restore the cursor/selection state in current document
                scimoz.setSel(gFindSession.fileSelectionStartPos, gFindSession.fileSelectionEndPos);
                //XXX Is this bad if the working view is not visible???
                scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(scimoz.currentPos));
                // we are done if this document has already been searched
                if (gFindSession.HaveSearchedThisUrlAlready(url)) {
                    break;
                }
                // make the switch
                scimoz = view.scintilla.scimoz;
            } else {
                break;
            }

            // Save the start information in this doc.
            gFindSession.fileStartPos = scimoz.currentPos;
            gFindSession.fileSelectionStartPos = scimoz.selectionStart;
            gFindSession.fileSelectionEndPos = scimoz.selectionEnd;

            // Setup for a search in this document. (Currently only "all open
            // documents" should reach this code.)
            text = scimoz.text;
            if (findSvc.options.searchBackward) {
                startOffset = stringutils_bytelength(text.slice(0, text.length - 1));
            } else {
                startOffset = 0;
            }
            contextOffset = 0;

            continue;
        }

        // fix up the find result for context and return it
        if (findResult != null) {
            gFindSession.NoteFind(findResult);
            return findResult;
        }
    }

    // Restore the editor state to that when this find session started.
    scimoz.hideSelection(true);
    if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
        // switch to the original url if it is still open
        var firstView = _GetViewFromViewId(editor, gFindSession.firstUrl);
        if (editor.ko.views.manager.currentView.document.displayPath
            != firstView.document.displayPath) {
            firstView.makeCurrent(false);
        }
        scimoz.setSel(
            scimoz.positionAtChar(0, gFindSession.firstFileSelectionStartPos),
            scimoz.positionAtChar(0, gFindSession.firstFileSelectionEndPos));
    } else if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC) {
        scimoz.setSel(
            scimoz.positionAtChar(0, gFindSession.firstFileSelectionStartPos),
            scimoz.positionAtChar(0, gFindSession.firstFileSelectionEndPos));
    } else if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        // We have to investigate this but find session termination is broken and so we can't
        // elicit this code path.
        scimoz.setSel(
            scimoz.positionAtChar(0, context.startIndex),
            scimoz.positionAtChar(0, context.endIndex)); // XXXX
    } else {
        throw("unexpected context: name='" + context.name + "' type=" + context.type);
    }
    scimoz.hideSelection(false);
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(scimoz.currentPos));
    return null;
}


function _ReplaceLastFindResult(editor, context, pattern, replacement)
{
    // Replace the last find result in the current find session, if there is
    // one and if it is genuine and current. No return value.
    var view = editor.ko.views.manager.currentView;
    if (! _IsViewSearchable(view)) {
        return;
    }
    var scimoz = view.scintilla.scimoz;
    var url = view.document.displayPath;
    var replaceResult = null;
    var findResult = gFindSession.GetLastFindResult();
    
    // Special case: If there is *no* last find result (i.e. the session
    // just started), but the current selection is a legitimate hit, then
    // we need to prime the session with that find result.
    // http://bugs.activestate.com/show_bug.cgi?id=27208
    if (findResult == null) {
        findResult = _SetupAndFindNext(editor, context, pattern, "replace", true);
    }

    if (findResult != null) {
        var startByte = scimoz.positionAtChar(0, findResult.start);
        var endByte = scimoz.positionAtChar(startByte,
                                            findResult.end-findResult.start);
        var findText = scimoz.getTextRange(startByte, endByte);
        var startOffset;
        if (findSvc.options.searchBackward) {
            startOffset = endByte;
        } else {
            startOffset = startByte;
        }
        replaceResult = findSvc.replace(url, scimoz.text, pattern,
                                        replacement, startOffset, scimoz);
        if (replaceResult) {
            findLog.info("replace result (from FindSvc): s/"+replaceResult.value+
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
            var byteLength = stringutils_bytelength(replaceResult.replacement);

            scimoz.targetStart = startByte;
            scimoz.targetEnd = endByte;
            scimoz.replaceTarget(byteLength, replaceResult.replacement);
            scimoz.anchor = startByte;
            scimoz.currentPos = startByte + byteLength;

            // fix up the search context as appropriate
            if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
                || context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS)
            {
                // nothing for now
            } else if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
                // adjust the context range for the change in length
                //XXX I think perhaps context.endIndex should be measured in
                //    chars and not in bytes (as this stringutils_bytelength
                //    is converting it to).
                context.endIndex += stringutils_bytelength(replaceResult.replacement) -
                                    stringutils_bytelength(replaceResult.value);
            } else {
                throw("unexpected context: name='" + context.name + "' type=" + context.type);
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
            gFindSession.NoteReplace(replaceResult);
        } else {
            findLog.info("find result is not genuine: skipping replace");
        }
    } else {
        findLog.info("no last find result to replace");
    }
}


function _FindAllInView(editor, view, context, pattern, resultsView)
{
    // Find all instances of "pattern" with "replacement" in the current
    // view context.
    //
    // Note: koIFindSession.StartFind() is skipped because we don't need to
    // use this state mechanism to know when to terminate the session. Session
    // termination is handled via .NoteUrl() and .HaveSearchedThisUrlAlready().
    //
    // No return value.

    var viewId = view.document.displayPath;
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

    findSvc.findallex(viewId, text, pattern, resultsView, contextOffset,
                      scimoz);
    gFindSession.NoteUrl(viewId);
}


function _MarkAllInView(editor, view, context, pattern)
{
    // Mark all instances of "pattern" with "replacement" in the current
    // view context.
    //
    // Note: koIFindSession.StartFind() is skipped because we don't need to
    // use this state mechanism to know when to terminate the session. Session
    // termination is handled via .NoteUrl() and .HaveSearchedThisUrlAlready().
    //
    // Returns true if hits were found in the view, false otherwise.

    var viewId = view.document.displayPath;
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
    lines = findSvc.findalllines(viewId, text, pattern, contextOffset,
                                 scimoz, countObj);
    var foundSome = lines.length > 0;
    _MarkLinesForViewId(editor, viewId, lines);

    gFindSession.NoteUrl(viewId);
    return foundSome;
}


function _ReplaceAllInView(editor, view, context, pattern, replacement,
                           resultsView)
{
    // Replace all instances of "pattern" with "replacement" in the current
    // view context.
    //
    // Note: koIFindSession.StartReplace() is skipped because we don't need to
    // use this state mechanism to know when to terminate the session. Session
    // termination is handled via .NoteUrl() and .HaveSearchedThisUrlAlready().
    //
    // Returns the number of replacements made.

    var viewId = view.document.displayPath;
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
    var replacementText = findSvc.replaceallex(viewId, text, pattern,
                                               replacement, gFindSession,
                                               resultsView, contextOffset,
                                               scimoz, numReplacementsObj);
    var numReplacements = numReplacementsObj.value;

    if (replacementText != null) {
        if (context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
            scimoz.targetStart = scimoz.positionAtChar(0, context.startIndex);
            scimoz.targetEnd = scimoz.positionAtChar(0, context.endIndex);
            scimoz.replaceTarget(-1, replacementText);
            // Restore the selection.
            scimoz.currentPos = scimoz.positionAtChar(0, context.startIndex);
            scimoz.anchor = scimoz.positionAtChar(0, context.startIndex)
                + stringutils_bytelength(replacementText);
        } else {
            var line = scimoz.lineFromPosition(scimoz.currentPos);
            scimoz.targetStart = 0;
            scimoz.targetEnd = stringutils_bytelength(text);
            scimoz.replaceTarget(-1, replacementText);
            // Put the cursor on the same line as before replacement.
            scimoz.anchor = scimoz.currentPos = scimoz.positionFromLine(line);
        }
    }

    //XXX Correct folds. See bug 25263.
    //    Are we losing other info like bookmarks?

    //XXX Is this bad if the working view is not visible???
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(scimoz.currentPos));

    gFindSession.NoteUrl(viewId);
    return numReplacements;
}


function _DisplayFindResult(editor, findResult)
{
    //dump("display find result: "+findResult.url+": " + findResult.start +
    //     "-" + findResult.end + ": '" + findResult.value + "'\n");

    // Make the view for this find result current if necessary.
    // XXX Note that we are presuming that Komodo does not yet allow multiple
    //     views per document, which it eventually will. When this is possibly
    //     we must switch to storing unique view IDs in the find session.
    // XXX We are currently using view.document.displayPath as the view's
    //     "unique id". The view system does not currently provide a way to
    //     getViewFromDisplayPath() so we roll our own.
    if (editor.ko.views.manager.currentView.document.displayPath != findResult.url) {
        var view = _GetViewFromViewId(editor, findResult.url);
        if (view == null) {
            var err = "The view for a find result was closed before it could "+
                      "be displayed!";
            findLog.error(err);
            // Don't raise an error. Just attempt to limp along. This method
            // has no mechanism for signalling failure.
            return;
        }
        // we don't want to focus when find dialog is up.
        var noFocus = editor != window;
        view.makeCurrent(noFocus);
    }

    // Jump to the find result and select it.
    // Jump to the _end_ (i.e. the start if going backwards) of the
    // result so that repeated finds are non-overlapping.
    var scimoz = editor.ko.views.manager.currentView.scintilla.scimoz;
    // Unfortunately this is going to be very slow -- I can't come up with a
    // way around this that will actually work without rewriting the find subsystem.
    var startByteIndex = stringutils_bytelength(scimoz.text.slice(0, findResult.start));
    var endByteIndex = startByteIndex + stringutils_bytelength(findResult.value);
    scimoz.setSel(startByteIndex, endByteIndex);

    // Ensure folded lines are expanded. We *could* conceivably have search
    // results that span lines so should ensure that the whole selection is
    // visible. XXX should include every line in btwn here
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(startByteIndex));
    scimoz.ensureVisibleEnforcePolicy(scimoz.lineFromPosition(endByteIndex));

    scimoz.chooseCaretX();
}


function _MarkLinesForViewId(editor, viewId, lines)
{
    // Mark all the given find results.
    var view = _GetViewFromViewId(editor, viewId);
    if (!view) return;

    var isBookmarkable = false;
    try {
        view.QueryInterface(Components.interfaces.koIBookmarkableView);
        isBookmarkable = true;
    } catch (ex) {}
    if (!isBookmarkable) {
        findLog.warn("Could not bookmark find results for '"+viewId+
                     "', because that view does not support koIBookmarkableView.");
        return;
    }

    for (var i = 0; i < lines.length; ++i) {
        view.addBookmark(lines[i]);
    }
}


/** Report the completion of a find session to the user.
 *
 * @param context {DOMWindow} is the koIFindContext for the find session.
 * @param msgHandler {callback} is a callback for displaying a
 *      message to the user. See Find_FindNext documentation for details.
 */
function _UiForCompletedFindSession(context, msgHandler)
{
    var numFinds = gFindSession.GetNumFinds();
    var numReplacements = gFindSession.GetNumReplacements();

    // Put together an appropriate message.
    var msg = "";
    if (numFinds == 0) {
        msg += " The pattern was not found.";
    } else if (numReplacements > 0) {
        msg += " " + numReplacements + " of " + numFinds +
               " occurrence(s) were replaced.";
    } else {
        msg += " " + numFinds + " occurrence(s) were found.";
    }

    msgHandler("info", "find", msg);
}


/** Report an error in the find service to the user.
 *
 * @param context {string} A short string giving context for the error,
 *      e.g. "find", "find all", "replace", ...
 * @param exc {exception} is an optional exception, if the error
 *      was trapped via try/catch. May be null.
 * @param msgHandler {callback} is a callback for displaying a
 *      message to the user. See Find_FindNext documentation for details.
 *
 * The actual error message is pulled from the koILastErrorService.
 */
function _UiForFindServiceError(context, exc, msgHandler)
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

var _Find_charsToEscape_re = /([\\\'])/g;
function _Find_RegexEscapeString(original) {
    return original.replace(_Find_charsToEscape_re, '\\$1');
}


/**
 * Return a callback appropriate for the 'msgHandler' callbacks that
 * will put a message on the status bar.
 */
function _Find_GetStatusbarMsgHandler(editor)
{
    return function (level, context, msg) {
        editor.ko.statusBar.AddMessage(context+": "+msg, "find",
                                       3000, true);
    }
}



//---- public functions

function Find_FindNextInMacro(editor, contexttype, pattern, patternType,
                              caseSensitivity, searchBackward, matchWord,
                              mode, quiet, useMRU)
{
    // Called by macros -- only difference with Find_FindNext is that
    // contexttype is
    // a constant, and the context needs to be created.
    // XXX the APIs should be factored out so that these "inmacro" versions aren't necessary.
    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"]
                  .getService(Components.interfaces.koIFindService);
    }

    // Stash old options
    old_patternType = findSvc.options.patternType;
    old_caseSensitivity = findSvc.options.caseSensitivity;
    old_searchBackward = findSvc.options.searchBackward;
    old_matchWord = findSvc.options.matchWord;

    findSvc.options.patternType = patternType;
    findSvc.options.caseSensitivity = caseSensitivity;
    findSvc.options.searchBackward = searchBackward;
    findSvc.options.matchWord = matchWord;

    Find_FindNext(editor, context, pattern, mode, quiet, useMRU);

    // restore options
    findSvc.options.patternType = old_patternType;
    findSvc.options.caseSensitivity = old_caseSensitivity;
    findSvc.options.searchBackward = old_searchBackward;
    findSvc.options.matchWord = old_matchWord;
}

function Find_FindAllInMacro(editor, contexttype, pattern, patternType,
                             caseSensitivity, searchBackward, matchWord)
{
    // Called by macros -- only difference with Find_FindAll is that
    // contexttype is a constant, the context needs to be created, and options
    // need to be set (and unset).
    // XXX the APIs should be factored out so that these "inmacro" versions
    //     aren't necessary.

    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"]
                  .getService(Components.interfaces.koIFindService);
    }

    // Stash old options
    old_patternType = findSvc.options.patternType;
    old_caseSensitivity = findSvc.options.caseSensitivity;
    old_searchBackward = findSvc.options.searchBackward;
    old_matchWord = findSvc.options.matchWord;

    findSvc.options.patternType = patternType;
    findSvc.options.caseSensitivity = caseSensitivity;
    findSvc.options.searchBackward = searchBackward;
    findSvc.options.matchWord = matchWord;

    Find_FindAll(editor, context, pattern);

    // restore options
    findSvc.options.patternType = old_patternType;
    findSvc.options.caseSensitivity = old_caseSensitivity;
    findSvc.options.searchBackward = old_searchBackward;
    findSvc.options.matchWord = old_matchWord;
}


function Find_MarkAllInMacro(editor, contexttype, pattern, patternType,
                             caseSensitivity, searchBackward, matchWord)
{

    // Called by macros -- only difference with Find_MarkAll is that
    // contexttype is a constant, and the context needs to be created.
    // XXX the APIs should be factored out so that these "inmacro" versions
    //     aren't necessary.

    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"]
                  .getService(Components.interfaces.koIFindService);
    }

    // Stash old options
    old_patternType = findSvc.options.patternType;
    old_caseSensitivity = findSvc.options.caseSensitivity;
    old_searchBackward = findSvc.options.searchBackward;
    old_matchWord = findSvc.options.matchWord;

    findSvc.options.patternType = patternType;
    findSvc.options.caseSensitivity = caseSensitivity;
    findSvc.options.searchBackward = searchBackward;
    findSvc.options.matchWord = matchWord;

    Find_MarkAll(editor, context, pattern);

    // restore options
    findSvc.options.patternType = old_patternType;
    findSvc.options.caseSensitivity = old_caseSensitivity;
    findSvc.options.searchBackward = old_searchBackward;
    findSvc.options.matchWord = old_matchWord;
}

function Find_ReplaceInMacro(editor, contexttype, pattern, replacement,
                             patternType, caseSensitivity, searchBackward, matchWord)
{
    // Called by macros -- only difference with Find_Replace is that
    // contexttype is a constant, and the context needs to be created.
    // XXX the APIs should be factored out so that these "inmacro" versions
    //     aren't necessary.

    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"]
                  .getService(Components.interfaces.koIFindService);
    }

    // Stash old options
    old_patternType = findSvc.options.patternType;
    old_caseSensitivity = findSvc.options.caseSensitivity;
    old_searchBackward = findSvc.options.searchBackward;
    old_matchWord = findSvc.options.matchWord;

    findSvc.options.patternType = patternType;
    findSvc.options.caseSensitivity = caseSensitivity;
    findSvc.options.searchBackward = searchBackward;
    findSvc.options.matchWord = matchWord;

    Find_Replace(editor, context, pattern, replacement);

    // restore options
    findSvc.options.patternType = old_patternType;
    findSvc.options.caseSensitivity = old_caseSensitivity;
    findSvc.options.searchBackward = old_searchBackward;
    findSvc.options.matchWord = old_matchWord;
}


function Find_ReplaceAllInMacro(editor, contexttype, pattern, replacement, quiet,
                                patternType, caseSensitivity, searchBackward, matchWord)
{
    // Called by macros -- only difference with Find_Replace is that
    // contexttype is a constant, and the context needs to be created.
    // XXX the APIs should be factored out so that these "inmacro" versions
    //     aren't necessary.

    var old_patternType, old_caseSensitivity, old_searchBackward, old_matchWord;
    var context = Components.classes["@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
    context.type = contexttype;

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"]
                  .getService(Components.interfaces.koIFindService);
    }

    // Stash old options
    old_patternType = findSvc.options.patternType;
    old_caseSensitivity = findSvc.options.caseSensitivity;
    old_searchBackward = findSvc.options.searchBackward;
    old_matchWord = findSvc.options.matchWord;

    findSvc.options.patternType = patternType;
    findSvc.options.caseSensitivity = caseSensitivity;
    findSvc.options.searchBackward = searchBackward;
    findSvc.options.matchWord = matchWord;

    Find_ReplaceAll(editor, context, pattern, replacement, quiet);

    // restore options
    findSvc.options.patternType = old_patternType;
    findSvc.options.caseSensitivity = old_caseSensitivity;
    findSvc.options.searchBackward = old_searchBackward;
    findSvc.options.matchWord = old_matchWord;
}


// Find (and move to) the next occurrence of the given pattern.
//
//  "editor" is a reference to the komodo.xul main window
//  "context" is a koIFindContext instance
//  "pattern" is the pattern being sought
//  "mode" (optional) is either "find" (the default) or "replace",
//      indicating if this is in the context of a replace UI.
//  "quiet" (optional) is a boolean indicating if UI (e.g. dialogs) may
//      be used for presenting info, e.g. wrapped the document. Interactive
//      search typically sets this to true. Default is false.
//  "useMRU" (optional) is a boolean indicating if the pattern should be
//      loaded into the find MRU. Default is true.
//  "msgHandler" (optional) is a callback that is called for displaying
//      a message during the find. It will be called like this:
//          callback(level, context, message)
//      where `level` is one of "info", "warn" or "error" and `message`
//      is the message to display. The msgHandler is ignore if `quiet`
//      is true. By default messages are sent to the statusbar.
function Find_FindNext(editor, context, pattern, mode /* ="find" */,
                       quiet /* =false */, useMRU /* =true */,
                       msgHandler /* =<statusbar notifier> */)
{
    if (typeof(mode) == 'undefined' || mode == null) mode = "find";
    if (typeof(quiet) == 'undefined' || quiet == null) quiet = false;
    if (typeof(useMRU) == 'undefined' || useMRU == null) useMRU = true;
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }

    findLog.info("Find_FindNext(editor, context, pattern='"+pattern+
                 "', mode="+mode+", quiet="+quiet+", useMRU"+useMRU+")");

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }
    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("Find_FindNextInMacro(window, " +
                                    context.type + ", '" +
                                    _Find_RegexEscapeString(pattern) + "', " +
                                    findSvc.options.patternType + ", " +
                                    findSvc.options.caseSensitivity + ", " +
                                    findSvc.options.searchBackward + ", " +
                                    findSvc.options.matchWord + ", " +
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
    try {
        findResult = _SetupAndFindNext(editor, context, pattern, mode);
    } catch (ex) {
        if (!quiet)
            _UiForFindServiceError("find", ex, msgHandler);
        return null;
    }
    if (useMRU)
        ko.mru.add("find-patternMru", pattern, true);

    if (findResult) {
        _DisplayFindResult(editor, findResult);
    } else {
        if (!quiet)
            _UiForCompletedFindSession(context, msgHandler);
        //log.debug("Reset find session, because 'FindNext' did not find "
        //         + "anything.");
        gFindSession.Reset();
    }
    return findResult != null;
}


function Find_FindAll(editor, context, pattern, patternAlias,
                      msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }

    findLog.info("Find_FindAll(editor, context, pattern='"+pattern+
                 "', patternAlias='"+patternAlias+"')");
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }
    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("Find_FindAllInMacro(window, " +
                                    context.type + ", '" +
                                    _Find_RegexEscapeString(pattern) + "', " +
                                    findSvc.options.patternType + ", " +
                                    findSvc.options.caseSensitivity + ", " +
                                    findSvc.options.searchBackward + ", " +
                                    findSvc.options.matchWord +
                                    ");\n");
    }

    var preferredResultsTab = findSvc.options.displayInFindResults2 ? 2 : 1;
    var resultsMgr = editor.FindResultsTab_GetTab(preferredResultsTab);
    if (resultsMgr == null)
        return null;
    resultsMgr.configure(pattern, patternAlias, null, context,
                         findSvc.options);
    resultsMgr.show();

    resultsMgr.searchStarted();
    var numFilesSearched = null;
    try {
        if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
            || context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
            findLog.debug("Find_FindAll: find all in '"+
                          editor.ko.views.manager.currentView.document.displayPath+"'\n");
            _FindAllInView(editor, editor.ko.views.manager.currentView, context,
                           pattern, resultsMgr.view);
        } else if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
            var view = editor.ko.views.manager.currentView;
            var viewId;
            numFilesSearched = 0;
            while (view) {
                if (_IsViewSearchable(view)) {
                    viewId = view.document.displayPath;
                    if (gFindSession.HaveSearchedThisUrlAlready(viewId)) {
                        findLog.debug("Find_FindAll: have already searched '"+
                                      viewId+"'\n");
                        break;
                    }
    
                    findLog.debug("Find_FindAll: find all in '"+viewId+"'\n");
                    _FindAllInView(editor, view, context, pattern, resultsMgr.view);
                    numFilesSearched += 1;
                }

                if (findSvc.options.searchBackward) {
                    view = _GetPreviousView(editor, view);
                } else {
                    view = _GetNextView(editor, view);
                }
            }
        } else {
            throw("unexpected context: name='" + context.name + "' type=" +
                  context.type);
        }
        // Would be good to pass in the number of files in which hits were
        // found, but don't easily have that value and it's not a biggie.
        resultsMgr.searchFinished(true, resultsMgr.view.rowCount, null,
                                  numFilesSearched);
    } catch (ex) {
        _UiForFindServiceError("find all", ex, msgHandler);
        return null;
    }


    ko.mru.add("find-patternMru", pattern, true);
    var foundSome = resultsMgr.view.rowCount > 0;
    if (! foundSome) {
        var msg;
        if (typeof(patternAlias) != 'undefined' && patternAlias) {
            msg = "No "+patternAlias+" were found in "+context.name+".";
        } else {
            var text_utils = Components.classes["@activestate.com/koTextUtils;1"]
                               .getService(Components.interfaces.koITextUtils);
            var summary = text_utils.one_line_summary_from_text(pattern, 30);
            msg = "'"+summary+"' was not found in "+context.name+".";
        }
        msgHandler("warn", "find", msg);
    }
    gFindSession.Reset();

    return foundSome;
}


function Find_MarkAll(editor, context, pattern, patternAlias,
                      msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }
    
    // Returns true iff any matches were found and displayed.
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"]
                  .getService(Components.interfaces.koIFindService);
    }
    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("Find_MarkAllInMacro(window, " +
                                    context.type + ", '" +
                                    _Find_RegexEscapeString(pattern) + "', " +
                                    findSvc.options.patternType + ", " +
                                    findSvc.options.caseSensitivity + ", " +
                                    findSvc.options.searchBackward + ", " +
                                    findSvc.options.matchWord + ", " +
                                    ");\n");
    }

    var foundSome = false;
    var rv
    if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        rv = _MarkAllInView(editor, editor.ko.views.manager.currentView, context,
                            pattern);
        if (rv) foundSome = true;
    } else if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
        var view = editor.ko.views.manager.currentView;
        var viewId;
        while (view) {
            viewId = view.document.displayPath;
            if (gFindSession.HaveSearchedThisUrlAlready(viewId)) {
                findLog.debug("Find_MarkAll: have alread searched '"+
                              viewId+"'\n");
                break;
            }

            rv = _MarkAllInView(editor, view, context, pattern);
            if (rv) foundSome = true;

            if (findSvc.options.searchBackward) {
                view = _GetPreviousView(editor, view);
            } else {
                view = _GetNextView(editor, view);
            }
        }
    } else {
        throw("unexpected context: name='" + context.name + "' type=" +
              context.type);
    }

    ko.mru.add("find-patternMru", pattern, true);
    if (! foundSome) {
        var msg;
        if (typeof(patternAlias) != 'undefined' && patternAlias) {
            msg = "No "+patternAlias+"' were found in "+context.name+".";
        } else {
            var text_utils = Components.classes["@activestate.com/koTextUtils;1"]
                               .getService(Components.interfaces.koITextUtils);
            var summary = text_utils.one_line_summary_from_text(pattern, 30);
            msg = "'"+summary+"' was not found in "+context.name+".";
        }
        msgHandler("warn", "find", msg);
    }
    gFindSession.Reset();

    return foundSome;
}


function Find_Replace(editor, context, pattern, replacement,
                      msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }

    // Replace the currently selected find result (if there is one) and find
    // the next occurrence of the current pattern. Returns true iff a next
    // occurence of the pattern was found and hilighted.
    findLog.info("Find_Replace(editor, context, pattern='"+pattern+
                 "', replacement='"+replacement+"')");
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }

    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("Find_ReplaceInMacro(window, " +
                                    context.type + ", '" +
                                    _Find_RegexEscapeString(pattern) + "', '" +
                                    _Find_RegexEscapeString(replacement) + "', " +
                                    findSvc.options.patternType + ", " +
                                    findSvc.options.caseSensitivity + ", " +
                                    findSvc.options.searchBackward + ", " +
                                    findSvc.options.matchWord +
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
            findLog.info("Find_Replace: replace last find result");
            _ReplaceLastFindResult(editor, context, pattern, replacement);
        } catch (ex) {
            _UiForFindServiceError("replace", ex, msgHandler);
            return null;
        }

        // find the next one
        try {
            findLog.info("Find_Replace: find next hit");
            findResult = _SetupAndFindNext(editor, context, pattern,
                                           'replace');
            if (findResult) {
                findLog.info("Find_Replace: found next hit: "+
                             findResult.start+"-"+findResult.end+": '"+
                             findResult.value+"'");
            }
        } catch (ex) {
            _UiForFindServiceError("replace", ex, msgHandler);
            return null;
        }
        ko.mru.add("find-patternMru", pattern, true);

        // Do the appropriate UI work for results.
        if (findResult == null) {
            _UiForCompletedFindSession(context, msgHandler);
            //findLog.debug("Reset find session, because 'Replace' action "
            //              + "returned no result.");
            gFindSession.Reset();
        } else {
            _DisplayFindResult(editor, findResult);
        }
    }
    return findResult != null;
}


function Find_ReplaceAll(editor, context, pattern, replacement,
                         showReplaceResults /* =false */,
                         msgHandler /* =<statusbar notifier> */)
{
    if (typeof(showReplaceResults) == "undefined") showReplaceResults = false;
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }

    findLog.info("Find_ReplaceAll(editor, context, pattern='"+pattern+
                 "', replacement='"+replacement+"', showReplaceResults="+
                 showReplaceResults+")\n");

    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }

    if (editor.ko.macros.recorder.mode == 'recording') {
        editor.ko.macros.recorder.appendCode("Find_ReplaceAllInMacro(window, " +
                                    context.type + ", '" +
                                    _Find_RegexEscapeString(pattern) + "', '" +
                                    _Find_RegexEscapeString(replacement) + "', " +
                                    showReplaceResults + ", " +
                                    findSvc.options.patternType + ", " +
                                    findSvc.options.caseSensitivity + ", " +
                                    findSvc.options.searchBackward + ", " +
                                    findSvc.options.matchWord +
                                    ");\n");
    }

    var resultsMgr = null;
    var resultsView = null;
    var numFiles = null;
    var numFilesSearched = null;
    if (showReplaceResults) {
        var preferredResultsTab = findSvc.options.displayInFindResults2 ? 2 : 1;
        resultsMgr = editor.FindResultsTab_GetTab(preferredResultsTab);
        if (resultsMgr == null)
            return false;
        resultsMgr.configure(pattern, null, replacement, context,
                             findSvc.options);
        resultsMgr.show();
        resultsView = resultsMgr.view;
        resultsMgr.searchStarted();

        // Should add results already in session.
        var countObj = new Object();
        var replaceResults = new Object();
        var rrs = gFindSession.GetReplacements(countObj);
        var i, rr;
        for (i = 0; i < rrs.length; ++ i) {
            rr = rrs[i];
            resultsMgr.addReplaceResult(
                "hit",
                rr.url, rr.start, rr.end, rr.value, rr.replacement, rr.url,
                rr.line, rr.column, rr.context_);
        }
    }

    var numReplacements = gFindSession.GetNumReplacements();
    var nr;
    if (context.type == Components.interfaces.koIFindContext.FCT_CURRENT_DOC
        || context.type == Components.interfaces.koIFindContext.FCT_SELECTION) {
        findLog.debug("Find_ReplaceAll: replace all in '"+
                      editor.ko.views.manager.currentView.document.displayPath+"'\n");
        nr = _ReplaceAllInView(editor, editor.ko.views.manager.currentView, context,
                               pattern, replacement, resultsView);
        numReplacements += nr;
    } else if (context.type == Components.interfaces.koIFindContext.FCT_ALL_OPEN_DOCS) {
        var view = editor.ko.views.manager.currentView;
        var viewId;
        numFiles = numFilesSearched = 0;
        while (view) {
            if (_IsViewSearchable(view)) {
                viewId = view.document.displayPath;
                if (gFindSession.HaveSearchedThisUrlAlready(viewId)) {
                    findLog.debug("Find_ReplaceAll: have already searched '"+
                                  viewId+"'\n");
                    break;
                }
    
                findLog.debug("Find_ReplaceAll: replace all in '"+viewId+"'\n");
                nr = _ReplaceAllInView(editor, view, context, pattern,
                                       replacement, resultsView);
                numReplacements += nr;
                if (nr) {
                    numFiles += 1;
                }
                numFilesSearched += 1;
            }

            if (findSvc.options.searchBackward) {
                view = _GetPreviousView(editor, view);
            } else {
                view = _GetNextView(editor, view);
            }
        }
    } else {
        throw("unexpected context: name='" + context.name + "' type=" +
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
        msg = "'" + summary + "' was not found in " + context.name
              + ". No changes were made.";
        msgHandler("info", "find", msg);
    } else {
        msg = "Made "+numReplacements+" replacements in "+
                  context.name+".";
        editor.ko.statusBar.AddMessage(msg, "find", 3000, true);
    }
    gFindSession.Reset();

    return numReplacements != 0;
}


/**
 * Find all hits in files.
 *
 * @param editor {DOMWindow} the main Komodo window in which to work
 * @param context {Components.interfaces.koIFindContext}
 * @param pattern {string} the pattern to search for.
 * @param patternAlias {string} a name for the pattern (for display to
 *      the user)
 * @param msgHandler {callback} is an optional callback for displaying a
 *      message to the user. See Find_FindNext documentation for details.
 */
function Find_FindAllInFiles(editor, context, pattern, patternAlias,
                             msgHandler /* =<statusbar notifier> */)
{
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }

    findLog.info("Find_FindAllInFiles(editor, context, pattern='"+pattern+
                 "', patternAlias='"+patternAlias+"')");
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }

    //TODO macro recording stuff for this

    var resultsMgr = editor.FindResultsTab_GetTab();
    if (resultsMgr == null)
        return false;
    resultsMgr.configure(pattern, patternAlias, null, context,
                         findSvc.options);
    resultsMgr.show();

    try {
        findSvc.findallinfiles(resultsMgr.id, pattern, resultsMgr);
    } catch (ex) {
        _UiForFindServiceError("find all in files", ex, msgHandler);
        resultsMgr.clear();
        return false;
    }
    return true;
}


/**
 * Replace all hits in files.
 *
 * @param editor {DOMWindow} the main Komodo window in which to work
 * @param context {Components.interfaces.koIFindContext} defines the
 *      scope in which to search, e.g., in a selection, just the current
 *      doc, all open docs.
 * @param pattern {string} the pattern to search for.
 * @param repl {string} the replacement string.
 * @param confirm {boolean} Whether to confirm replacements. Optional,
 *      true by default.
 * @param msgHandler {callback} is an optional callback for displaying a
 *      message to the user. See Find_FindNext documentation for details.
 * @returns {boolean} True if the operation was successful. False if there
 *      was an error or replacement was aborted.
 */
function Find_ReplaceAllInFiles(editor, context, pattern, repl,
                                confirm /* =true */,
                                msgHandler /* =<statusbar notifier> */)
{
    if (typeof(confirm) == 'undefined' || confirm == null) confirm = true;
    if (typeof(msgHandler) == 'undefined' || msgHandler == null) {
        msgHandler = _Find_GetStatusbarMsgHandler(editor);
    }

    findLog.info("Find_ReplaceAllInFiles(editor, context, pattern='"+pattern+
                 "', repl='"+repl+"', confirm="+confirm+")");
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }

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
            msgHandler("info", "replace", "No replacements were found.");
            return false;
        }
        
        // The replacement completed, and there were hits.
        // I.e., we now have to make those replacements.
        var resultsMgr = editor.FindResultsTab_GetTab();
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
                             findSvc.options,
                             true);  // opSupportsUndo
        resultsMgr.show();
        replacer.commit(resultsMgr);
        editor.ko.window.checkDiskFiles(); // Ensure changes *open* files get reloaded.
        return true;

    } else {
        var resultsMgr = editor.FindResultsTab_GetTab();
        if (resultsMgr == null)
            return false;
        resultsMgr.configure(pattern, null, repl, context,
                             findSvc.options,
                             true); // opSupportsUndo
        resultsMgr.show();
    
        try {
            findSvc.replaceallinfiles(resultsMgr.id, pattern, repl,
                                      resultsMgr);
        } catch (ex) {
            _UiForFindServiceError("replace all in files", ex, msgHandler);
            resultsMgr.clear();
            return false;
        }
    }

    return true;
}
