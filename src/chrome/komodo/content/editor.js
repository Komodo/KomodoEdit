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

// Controller for "view" related edit menu items.
// XXX - should be moved to view.js.
// XXX - note - we could probably get _significant_ performance
// gains by ensuring that this controller is _only_ in place when
// a view is current.  When we can guarntee this, all "isCommandEnabled()"
// calls, which currently call viewManager.getCurrentView(), can be replaced with
// "return true;".  This may already be true, but not going to
// attempt this optimization for release.
xtk.include("controller");
xtk.include("clipboard");

// hide this controller from our global namespace, we simply dont need to
// touch anything in it from the outside world
(function() {
var log = ko.logging.getLogger("ko.editor");
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/editor.properties");
var editor_controller_instance = null;

const ISCIMOZ = Components.interfaces.ISciMoz;
// Scintilla styling
const DEFAULT_STYLE = ISCIMOZ.SCE_UDL_M_DEFAULT;
const START_TAG_OPEN = ISCIMOZ.SCE_UDL_M_STAGO;
const END_TAG_OPEN = ISCIMOZ.SCE_UDL_M_ETAGO;
const START_TAG_CLOSE = ISCIMOZ.SCE_UDL_M_STAGC;
const END_TAG_CLOSE = ISCIMOZ.SCE_UDL_M_ETAGC;
const VALID_TAG_STYLES = [START_TAG_OPEN,
                          END_TAG_OPEN,
                          START_TAG_CLOSE,
                          END_TAG_CLOSE,
                          ISCIMOZ.SCE_UDL_M_COMMENT];
const OPEN_TAG_STYLES = [START_TAG_OPEN,
                         END_TAG_OPEN,
                         ISCIMOZ.SCE_UDL_M_COMMENT];
    
function editor_editorController() {
    ko.main.addWillCloseHandler(this.destructor, this);
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
editor_editorController.prototype = new xtk.Controller();
editor_editorController.prototype.constructor = editor_editorController;

editor_editorController.prototype.destructor = function() {
    window.controllers.removeController(this);
}

// boolean prefs are marked "not supported" if there is no view
// This is to handle that "isCommandEnabled" is actually doing
// the state of the checkbox.
editor_editorController.prototype._is_bool_pref_command_supported = function(pref_name) {
    return ko.views.manager.currentView != null;
}

// This is probably bogus.  Instead of asking scintilla its current state
// we should just ask the preference service for the state.
// See _is_bool_real_pref_command_enabled
editor_editorController.prototype._is_bool_pref_command_enabled = function(sci_prop_name) {
    var v = ko.views.manager.currentView;
    if (v && v.scimoz) {
        var exist = v.scimoz[sci_prop_name];
        return exist;
    }
    return false;
}

editor_editorController.prototype._is_bool_real_pref_command_enabled = function(pref_name) {
    var cv = ko.views.manager.currentView;
    if (cv) {
        return cv.prefs.getBooleanPref(pref_name)
    }
    return false;
}

editor_editorController.prototype._do_bool_pref_command = function(pref_name, existing_val) {
    var v = ko.views.manager.currentView;
    if (!v) {
        return;
    }
    v.prefs.setBooleanPref(pref_name, !existing_val);
    // DONT update SciMoz here - let the preference notify mechanism
    // trigger the normal preference handling code.
}

function _getCurrentScimozView() {
    var v = ko.views.manager.currentView;
    return v && v.scimoz ? v : null;
}
//---- find stuff

editor_editorController.prototype.is_cmd_findNextSelected_enabled = function() {
    return ko.views.manager.currentView ? true : false;
}

editor_editorController.prototype.do_cmd_findNextSelected = function(backwards /* false */) {
    if (typeof(backwards) == 'undefined' || backwards == null) {
        backwards = false;
    }
    var v = _getCurrentScimozView();
    if (!v) {
        return;
    }
    var scimoz = v.scimoz
    var pattern = scimoz.selText;
    if (pattern == '') {
        scimoz.wordLeft();
        var curChar = scimoz.getWCharAt(scimoz.currentPos);
        while (scimoz.wordChars.indexOf(curChar) != -1) {
            pattern += curChar;
            scimoz.charRight();
            curChar = scimoz.getWCharAt(scimoz.currentPos);
        }
    }

    var context = Components.classes["@activestate.com/koFindContext;1"]
        .createInstance(Components.interfaces.koIFindContext);
    var findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    context.type = findSvc.options.FCT_CURRENT_DOC;
    findSvc.options.preferredContextType = findSvc.options.FCT_CURRENT_DOC;
    findSvc.options.searchBackward = backwards;
    ko.find.findNext(window, context, pattern);
}

editor_editorController.prototype.is_cmd_findPreviousSelected_enabled = function() {
    var v = ko.views.manager.currentView;
    return v && !!v.scimoz;
}


editor_editorController.prototype.do_cmd_findPreviousSelected = function() {
    editor_controller_instance.do_cmd_findNextSelected(/* backwards */ true);
}

/**
 * Extract quick bookmark location from docstate by index and jump to thatline
 *
 * @param {numbers}  index, key number was saved under.
 */
function goToQuickBookmark(index) {
    var docState = require("ko/views").current().prefs;
    var quickBookmarkPref = {};
    var quickBookmarkName = "quick_bookmarks_" + index;
    if (!docState.hasPref(quickBookmarkName))
    {
        require("notify/notify").send("No quick bookmark for index " + index,
                                      "editor")
        return;
    }
    quickBookmarkPref = docState.getPref(quickBookmarkName);
    if (!quickBookmarkPref.hasPref("markerId")) {
        log.warn("Stale/broken quick bookmark ID. Removing quick bookmark index.");
        docState.deletePref(quickBookmarkName);
        return;
    }
    let markerid = quickBookmarkPref.getLong("markerId");
    let editor = require("ko/editor");
    let line = editor.getBookmarkLineFromHandle(markerid);
    // Above line sets -1 if not found
    // Gotta check or else we'll go to line 0 
    if (line >= 0) {
        editor.gotoLine(line);
    }
    else{
        docState.deletePref(quickBookmarkName);
    }
}

//Easiest way to add the 10 goToQuickBookmark functions needs for this feature
[0,1,2,3,4,5,6,7,8,9].forEach(function(i)
    {
        //commands.register("setQuickBookmark_" + i, setQuickBookmark(i),{
        //    label: "Quick Bookmark: Set quick bookmark for " + i + "key"
        //});
        editor_editorController.prototype["do_cmd_goToQuickBookmark_"+i] = function() {
            goToQuickBookmark(i);
        }
        editor_editorController.prototype["is_cmd_goToQuickBookmark_"+i+"_enabled"] = function() {
            return !!_getCurrentScimozView();
        }
    })

/**
 * Set a quick book mark and save it to the docstate for retrieval purposes
 *
 * @param {numbers}  index, key number was saved under.
 */
function setQuickBookmark(index)
{
    var editor = require("ko/editor")
    var docState = require("ko/views").current().prefs;
    var quickBookmarkName = "quick_bookmarks_" + index;
    var quickBookmarkPref = {};

    if (docState.hasPref(quickBookmarkName))
    {
        quickBookmarkPref = docState.getPref(quickBookmarkName);
    }
    else 
    {
        quickBookmarkPref = Cc['@activestate.com/koPreferenceSet;1'].createInstance();
        docState.setPref(quickBookmarkName, quickBookmarkPref)
    }
    
    //Delete old quick bookmark if it's already set
    if (quickBookmarkPref.hasPref("markerId")) {
        editor.unsetBookmarkByHandle(quickBookmarkPref.getLong("markerId"));
    }
    
    ko.history.note_curr_loc(require("ko/views").current().get());
    var markerId = editor.setBookmark(editor.getLineNumber(),
                                      ko.markers['MARKNUM_BOOKMARK' + index]);
    var markerId = editor.setBookmark(editor.getLineNumber());
    quickBookmarkPref.setLong("markerId", markerId);
}

//Easiest way to add the 10 setQuickBookmark functions needs for this feature
[0,1,2,3,4,5,6,7,8,9].forEach(function(i)
    {
        //commands.register("setQuickBookmark_" + i, setQuickBookmark(i),{
        //    label: "Quick Bookmark: Set quick bookmark for " + i + "key"
        //});
        editor_editorController.prototype["do_cmd_setQuickBookmark_"+i] = function() {
            setQuickBookmark(i);
        }
        editor_editorController.prototype["is_cmd_setQuickBookmark_"+i+"_enabled"] = function() {
            return !!_getCurrentScimozView();
        }
    })
    
editor_editorController.prototype.is_cmd_bookmarkToggle_enabled = function() {
    return !!_getCurrentScimozView();
}
editor_editorController.prototype.do_cmd_bookmarkToggle = function() {
    var v = _getCurrentScimozView();
    require("ko/editor").toggleBookmark();
}

editor_editorController.prototype.is_cmd_bookmarkRemoveAll_enabled = function() {
    return !!_getCurrentScimozView();
}
editor_editorController.prototype.do_cmd_bookmarkRemoveAll = function() {
    var v = _getCurrentScimozView();
    if (v) {
        v.scimoz.markerDeleteAll(ko.markers.MARKNUM_BOOKMARK);
        for (let i = 0; i < 10; i++) {
            v.scimoz.markerDeleteAll(ko.markers['MARKNUM_BOOKMARK' + i]);
        }
    }
    window.dispatchEvent(new CustomEvent("bookmark_deleted",
                                         { bubbles: true, detail: { 'all': true } }));
}

editor_editorController.prototype.is_cmd_bookmarkGotoNext_enabled = function() {
    return !!_getCurrentScimozView();
}
editor_editorController.prototype.do_cmd_bookmarkGotoNext = function() {
    var v = _getCurrentScimozView();
    if (!v) {
        return;
    }
    var thisLine = v.scimoz.lineFromPosition(v.scimoz.selectionStart);
    var marker_mask = 1 << ko.markers.MARKNUM_BOOKMARK;
    for (let i = 0; i < 10; i++) {
        marker_mask |= 1 << ko.markers['MARKNUM_BOOKMARK' + i];
    }
    var nextLine = v.scimoz.markerNext(thisLine+1, marker_mask);
    if (nextLine < 0) {
        // try for search from top of file.
        nextLine = v.scimoz.markerNext(0, marker_mask);
    }
    if (nextLine < 0 || nextLine == thisLine) {
        require("notify/notify").send(
            _bundle.GetStringFromName("noNextBookmark.message"),
            "bookmark");
        
    } else {
        ko.history.note_curr_loc(v);
        v.scimoz.ensureVisibleEnforcePolicy(nextLine);
        v.scimoz.gotoLine(nextLine);
    }
}


editor_editorController.prototype.is_cmd_bookmarkGotoPrevious_enabled = function() {
    return !!_getCurrentScimozView();
}
editor_editorController.prototype.do_cmd_bookmarkGotoPrevious = function() {
    var v = _getCurrentScimozView();
    if (!v) {
        return;
    }
    var thisLine = v.scimoz.lineFromPosition(v.scimoz.selectionStart);
    var marker_mask = 1 << ko.markers.MARKNUM_BOOKMARK;
    for (let i = 0; i < 10; i++) {
        marker_mask |= 1 << ko.markers['MARKNUM_BOOKMARK' + i];
    }
    var prevLine = v.scimoz.markerPrevious(thisLine-1, marker_mask);
    if (prevLine < 0) {
        // try for search from bottom of file.
        prevLine = v.scimoz.markerPrevious(v.scimoz.lineCount-1, marker_mask);
    }
    if (prevLine < 0 || prevLine == thisLine) {
        require("notify/notify").send(
            _bundle.GetStringFromName("noPreviousBookmark.message"),
            "bookmark.message");
    } else {
        ko.history.note_curr_loc(v);
        v.scimoz.ensureVisibleEnforcePolicy(prevLine);
        v.scimoz.gotoLine(prevLine);
    }
}

editor_editorController.prototype.do_cmd_macroNew= function() {
    // Ensure the toolbox is visible.
    ko.uilayout.ensureTabShown('toolbox2viewbox');
    // Show the new macro dialog.
    ko.toolbox2.addToolboxItem('macro');
}

editor_editorController.prototype.is_cmd_startMacroMode_enabled = function() {
    return ko.macros.recorder.mode != 'recording';
}

editor_editorController.prototype.do_cmd_startMacroMode= function() {
    ko.macros.recorder.startRecording();
}

editor_editorController.prototype.is_cmd_pauseMacroMode_enabled = function() {
    return ko.macros.recorder.mode == 'recording';
}

editor_editorController.prototype.do_cmd_pauseMacroMode= function() {
    ko.macros.recorder.pauseRecording();
}

editor_editorController.prototype.is_cmd_stopMacroMode_enabled = function() {
    return ko.macros.recorder.mode != 'stopped';
}

editor_editorController.prototype.do_cmd_stopMacroMode= function() {
    ko.macros.recorder.stopRecording();
}

editor_editorController.prototype.is_cmd_executeLastMacro_enabled = function() {
    return ko.macros.recorder.mode != 'recording' && ko.macros.recorder.currentMacro != null;
}

editor_editorController.prototype.do_cmd_executeLastMacro = function() {
    ko.macros.recorder.executeLastMacro()
}

editor_editorController.prototype.is_cmd_saveMacroToToolbox_enabled = function() {
    return ko.macros.recorder.mode != 'recording' && ko.macros.recorder.currentMacro != null;
}

editor_editorController.prototype.do_cmd_saveMacroToToolbox = function() {
    ko.macros.recorder.saveToToolbox();
}

editor_editorController.prototype.is_cmd_viewAsGuessedLanguage_enabled = function() {
    return (ko.views.manager.currentView != null &&
      ko.views.manager.currentView.getAttribute('type') == 'editor');
}

editor_editorController.prototype.do_cmd_viewAsGuessedLanguage = function() {
    var v = _getCurrentScimozView();
    if (!v) {
        return;
    }
    try {
        v.koDoc.language = '';
        v.koDoc.language = v.koDoc.language;
        v.scimoz.colourise(0, -1);
    } catch (e) {
        log.exception(e);
    }
}

editor_editorController.prototype.is_cmd_browserPreview_enabled = function() {
    var view = ko.views.manager.currentView;
    return (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.koDoc && view.koDoc.file);
}

editor_editorController.prototype.do_cmd_browserPreview = function() {
    var view = ko.views.manager.currentView;
    var canPreview = (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.koDoc && view.koDoc.file);
    if (canPreview)
        view.viewPreview();
}

editor_editorController.prototype.is_cmd_browserPreviewInternal_enabled = function() {
    var view = ko.views.manager.currentView;
    return (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.koDoc && view.koDoc.file && view.koDoc.file.isLocal);
}

editor_editorController.prototype.do_cmd_browserPreviewInternal = function() {
    var view = ko.views.manager.currentView;
    var canPreview = (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.koDoc && view.koDoc.file && view.koDoc.file.isLocal);
    if (canPreview)
        view.createInternalViewPreview(null, view.alternateViewList);
}

editor_editorController.prototype.is_cmd_browserPreviewInternalSameTabGroup_enabled = function() {
    var view = ko.views.manager.currentView;
    return (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.koDoc && view.koDoc.file && view.koDoc.file.isLocal);
}

editor_editorController.prototype.do_cmd_browserPreviewInternalSameTabGroup = function() {
    var view = ko.views.manager.currentView;
    var canPreview = (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.koDoc && view.koDoc.file && view.koDoc.file.isLocal);
    if (canPreview)
        view.createInternalViewPreview(null, view.parentView);
}

/**
 * handle raw key commands (i.e. insert literal key)
 */
editor_editorController.prototype.is_cmd_rawKey_enabled = function() {
    return !!_getCurrentScimozView();
}

editor_editorController.prototype.do_cmd_rawKey= function() {
    var v = _getCurrentScimozView();
    var scintilla;
    if (!v || !(scintilla = v.scintilla)) {
        return;
    }
    var scintilla = v.scintilla;
    scintilla.key_handler = editor_controller_instance.rawHandler;
    scintilla.addEventListener('blur', gCancelRawHandler, false);
    scintilla.scimoz.isFocused = true;
}

function gCancelRawHandler(event) {
    if (editor_controller_instance.key_handler) {
        editor_controller_instance.key_handler = null;
        var v = _getCurrentScimozView();
        if (!v) {
            return;
        }
        v.scintilla.removeEventListener('blur', gCancelRawHandler, false);
    }
}

editor_editorController.prototype.rawHandler= function(event) {
    try {
        if (event.type != 'keypress') return;
        var v = _getCurrentScimozView();
        var scintilla;
        if (!v || !(scintilla = v.scintilla)) {
            return;
        }
        scintilla.key_handler = null;
        var scimoz = scintilla.scimoz;
        event.cancelBubble = true;
        event.preventDefault();
        // XXX handle meta key here?
        if (event.ctrlKey) {
            // Need to convert from charCode to ASCII value
            scimoz.replaceSel(String.fromCharCode(event.charCode-96));
        } else {
            if (event.charCode != 0) {  // not sure why space doesn't work.
                scimoz.replaceSel(String.fromCharCode(event.charCode));
            } else {
                switch (event.keyCode) {
                    case event.DOM_VK_ESCAPE:
                    case event.DOM_VK_RETURN:
                    case event.DOM_VK_TAB:
                    case event.DOM_VK_BACK_SPACE:
                        scimoz.replaceSel(String.fromCharCode(event.keyCode));
                        break;
                    default:
                        // do nothing
                }
            }
        }
    } catch (e) {
        log.error(e);
    }
};

editor_editorController.prototype.is_cmd_pasteHtml_enabled = function() {
    return xtk.clipboard.containsHtml();
}

editor_editorController.prototype.do_cmd_pasteHtml= function() {
    var v = _getCurrentScimozView();
    if (!v) {
        return;
    }
    var scimoz = v.scimoz;
    var html = xtk.clipboard.getHtml();
    scimoz.replaceSel(html);
}

var is_cmd_addAdditionalCaret_enabled_aux = function() {
    var view = _getCurrentScimozView();
    if (!view) {
        return null;
    }
    var scimoz = view.scimoz;
    if (!scimoz) {
        return null;
    }
    return (scimoz.selectionMode != scimoz.SC_SEL_RECTANGLE
            || (scimoz.lineFromPosition(scimoz.selectionStart)
                == scimoz.lineFromPosition(scimoz.selectionEnd))) ? view : null;
};

editor_editorController.prototype.is_cmd_addNextWordToCaretSet_enabled = function() {
    return !!is_cmd_addAdditionalCaret_enabled_aux();
}
  
editor_editorController.prototype.do_cmd_addNextWordToCaretSet = function() {
    var view = is_cmd_addAdditionalCaret_enabled_aux();
    if (!view) {
        return;
    }
    var scimoz = view.scimoz;
    scimoz.targetWholeDocument();
    scimoz.searchFlags = scimoz.SCFIND_MATCHCASE;
    if (scimoz.selectionEmpty || scimoz.isRangeWord(scimoz.selectionStart, scimoz.selectionEnd)) {
        scimoz.searchFlags |= scimoz.SCFIND_WHOLEWORD;
    }
    scimoz.multipleSelectAddNext();
};

editor_editorController.prototype._aux_is_cmd_rename_tag_enabled = function() {
    var view = _getCurrentScimozView();
    if (!view || view.getAttribute("type") != "editor") {
        return [false];
    }
    var koDoc = view.koDoc;
    if (!koDoc) {
        return [false];
    }
    if (koDoc.languageObj.supportsSmartIndent != "XML") {
        return [false];
    }
    return [true, view, koDoc];
}

editor_editorController.prototype.is_cmd_rename_tag_enabled = function() {
    return editor_controller_instance._aux_is_cmd_rename_tag_enabled()[0];
    // Because there aren't any events that fire when the doc position
    // changes, we need to check if we're on a tag in the do-part
}

editor_editorController.prototype.do_cmd_rename_tag = function() {
    var parts, isEnabled, view, koDoc;
    parts = editor_controller_instance._aux_is_cmd_rename_tag_enabled();
    if (!parts[0]) {
        require("notify/notify").send(
            "Invalid context for renaming a tag",
            "editor", {priority: "warning"});
        return;
    }
    [isEnabled, view, koDoc] = parts;
    var scimoz = view.scimoz;
    var currentPos = scimoz.currentPos;
    var prevPos = currentPos > 0 ? scimoz.positionBefore(currentPos) : 0;
    var anchorOffset = currentPos - scimoz.anchor;
    var currentStyle = scimoz.getStyleAt(currentPos);
    var prevStyle = scimoz.getStyleAt(prevPos);
    var validStyles = [scimoz.SCE_UDL_M_STAGO,
                       scimoz.SCE_UDL_M_TAGNAME,
                       scimoz.SCE_UDL_M_TAGSPACE,
                       scimoz.SCE_UDL_M_ATTRNAME,
                       scimoz.SCE_UDL_M_OPERATOR,
                       scimoz.SCE_UDL_M_STAGC,
                       scimoz.SCE_UDL_M_STRING,
                       scimoz.SCE_UDL_M_ETAGO,
                       scimoz.SCE_UDL_M_ETAGC,
                       ];
    if (validStyles.indexOf(prevStyle) === -1
        && validStyles.indexOf(currentStyle) === -1) {
        return;
    }
    var tagNameStartPos;
    var isStartTag;
    // Move to the start of TAGNAME
    // First, if we're on the start of a start-tag, move right.
    if (prevStyle == scimoz.SCE_UDL_M_STAGO) {
        isStartTag = true;
        tagNameStartPos = currentPos;
    } else if (currentStyle == scimoz.SCE_UDL_M_STAGO) {
        isStartTag = true;
        tagNameStartPos = currentPos + 1;
    } else if (prevStyle == scimoz.SCE_UDL_M_ETAGO) {
        isStartTag = false;
        tagNameStartPos = currentPos;
    } else if (currentStyle == scimoz.SCE_UDL_M_ETAGO) {
        isStartTag = false;
        tagNameStartPos = currentPos + 1;
    } else {
        // Move to a "<" and then figure out where we're at
        let style, pos;
        for (pos = prevPos - 1; pos >= 0; --pos) {
            style = scimoz.getStyleAt(pos);
            if (style == scimoz.SCE_UDL_M_STAGO) {
                isStartTag = true;
                tagNameStartPos = pos + 1;
                break;
            } else if (style == scimoz.SCE_UDL_M_ETAGO) {
                isStartTag = false;
                tagNameStartPos = pos + 1;
                break;
            } else if (validStyles.indexOf(style) == -1) {
                require("notify/notify").send(
                    _bundle.GetStringFromName("RenameTag not in a start or end tag"),
                    "editor", {priority: "warning"});
                return;
            }
        }
    }
    var offset = currentPos - tagNameStartPos;
    let tagNameEndPos = tagNameStartPos + 1;
    let lim = scimoz.length;
    for (tagNameEndPos = tagNameStartPos + 1; tagNameEndPos < lim; tagNameEndPos++) {
        if (scimoz.getStyleAt(tagNameEndPos) !== scimoz.SCE_UDL_M_TAGNAME) {
            break;
        }
    }
    var tagName = scimoz.getTextRange(tagNameStartPos, tagNameEndPos);
    var result = {};
    koDoc.languageObj.getMatchingTagInfo(scimoz, tagNameStartPos - 1, false, result, {});
    if (!result.value || !result.value.length) {
        var msg = _bundle.formatStringFromName("RenameTag Failed to find a matching tag for X",
                                               [tagName], 1);
        require("notify/notify").send(msg, "editor", {priority: "warning"});
        return;
    }
    let atStartTag, s1, s2, e1, e2, sn1, en1;
    [atStartTag, s1, s2, e1, e2] = result.value;
    // Now find the tag boundaries.
    s1 += 1;
    e1 += 2;
    if (scimoz.getStyleAt(s1) != scimoz.SCE_UDL_M_TAGNAME
        || scimoz.getStyleAt(e1) != scimoz.SCE_UDL_M_TAGNAME) {
        var msg = _bundle.GetStringFromName("RenameTag Cant find the start of a tagname");
        require("notify/notify").send(msg, "editor", {priority: "warning"});
        return;
    }
    for (sn1 = s1 + 1; sn1 <= lim && scimoz.getStyleAt(sn1) == scimoz.SCE_UDL_M_TAGNAME; ++sn1) {
        // empty
    }
    for (en1 = e1 + 1; en1 <= lim && scimoz.getStyleAt(en1) == scimoz.SCE_UDL_M_TAGNAME; ++en1) {
        // empty
    }
    scimoz.setSelection(sn1, s1);
    scimoz.addSelection(en1, e1);
    scimoz.mainSelection = 0;
}

editor_editorController.prototype.is_cmd_launchColorPicker_enabled = function() {
    return !!_getCurrentScimozView();
};

editor_editorController.prototype.do_cmd_launchColorPicker = function() {
    const view = _getCurrentScimozView();
    if (!view) {
        return;
    }
    const scimoz = view.scimoz;
    const currentPos = scimoz.currentPos;
    const lineNo = scimoz.lineFromPosition(currentPos);
    const line = {};
    scimoz.getLine(lineNo, line);
    const lineStartPos = scimoz.positionFromLine(lineNo);
    const lineEndPos = scimoz.getLineEndPosition(lineNo);
    const reason = "command";
    const hyperlink =
        ko.hyperlinks.handlers.colorPreviewHandler.show(view,
                                                        scimoz,
                                                        currentPos,
                                                        line.value,
                                                        lineStartPos,
                                                        lineEndPos,
                                                        reason);
    if (hyperlink) {
        ko.hyperlinks.handlers.colorPreviewHandler.jump(view, hyperlink);
        view.removeHyperlinks(reason);
    } else {
        ko.hyperlinks.handlers.colorPreviewHandler.
            showColorPicker(view, { startPos: scimoz.selectionStart,
                                      endPos: scimoz.selectionEnd });
    }
};


/**
 * Select and move xml style tags easily 
 * @postcondition view._htmlRelocator exists.
 */
editor_editorController.prototype.do_cmd_htmlTagRelocator = function() {
    var view = _getCurrentScimozView();
    
    log.debug("Running html tag relocator: " +
              "_htmlTagRelocator is in view: " + ("_htmlTagRelocator" in view));
    
    var scimoz = view.scimoz;
    var currentPos = scimoz.currentPos;
    
    if (!("_htmlTagRelocator" in view)) {
        makeRelocatorSelection(view, scimoz);
    } else {
        var {savedSelectionStart,savedSelectionEnd} = view._htmlTagRelocator;
        // warning terrible function name coming
        if(!isContextCorrect(scimoz, view)){
            var statMsg = _bundle.GetStringFromName("htmlRelocatorLostContext");
            require("notify/notify").send(statMsg, "editor", {priority: "warning"});
            deleteHtmlRelocator();
            return;
        }
        // Empty selection
        if (currentPos == scimoz.anchor) {
            // Check that the script is not being run inside another tag 
            if (scimoz.getStyleAt(currentPos) == DEFAULT_STYLE ||
                scimoz.getWCharAt(currentPos) ==  '<')
            {
                var text = scimoz.getTextRange(savedSelectionStart,
                                               savedSelectionEnd);
                moveRelocatorText(savedSelectionStart,
                                  savedSelectionEnd - savedSelectionStart,
                                  currentPos,
                                  text);
            } else {
                var sttMsg = _bundle.GetStringFromName("htmlRelocatorRunExist");
                require("notify/notify").send(sttMsg, "editor", {priority: "warning"});
                makeRelocatorSelection(view, scimoz);
            }
        }
        // Check that the user hasn't highlighted something else since
        // makeRelocatorSelection() was last run.
        // Protection agains accidentally running the script and chopping up the 
        // user's code.  Restart the process.
        else if (scimoz.selectionEnd != savedSelectionEnd ||
                 scimoz.selectionStart != savedSelectionStart)
        {
            makeRelocatorSelection(view, scimoz);
        } else {
            skipWordsTagsRight(view, scimoz);
        }
    }
}

/**
 * highlights the initial tag and sets view variables;
 * @precondition view be defined
 * @postcondition current tag is selected based on scimoz.currentPos
 * @postcondition view._htmlTagRelocator is set/reset
 */
function makeRelocatorSelection(view, scimoz) {
    // If there is a selection, get rid of it and reset it to currentPos
    // assumption being that the user will not drag the selection to OUTSIDE
    // the tag they want to select.
    log.debug("Running makeRelocatorSelection() in ko.editor.");
    
    if ("_htmlrelocator" in view) { deleteHtmlRelocator(); };
    
    scimoz.anchor = scimoz.currentPos;
    var currentPos = scimoz.currentPos;
    var startOfCurrentLine =
        scimoz.positionFromLine(scimoz.lineFromPosition(currentPos));
    var endOfDocument = scimoz.length;
    var currentStyle = scimoz.getStyleAt(currentPos);
    var startOfCurrentTag;
    if(!relocatorInsideTag(scimoz)){
        var sttMsg = _bundle.GetStringFromName("htmlRelocateNotInTagNotCosed");
        require("notify/notify").send(sttMsg, "editor", {priority: "warning"});
        log.debug("htmlTagRelocator stopped. Not in tag or tag does not close");
        return;
    }
    
    /**
     * I know I'm within the boundaries of a tag so move forward one position
     * before search for start so I don't miss when I'm at |<p>
     */
    var posAfterCurPos = scimoz.positionAfter(currentPos);
    startOfCurrentTag = findNextValidCloseOpenSymbol(posAfterCurPos,
                                                     startOfCurrentLine,
                                                     "<");
    var posAfterStart = scimoz.positionAfter(startOfCurrentTag);
    var endOfCurrentTag = findNextValidCloseOpenSymbol(
                            posAfterStart, endOfDocument, ">");
    var nextStartTagOpen = findNextValidCloseOpenSymbol(
                            posAfterStart, endOfDocument, "<");
    
    if (nextStartTagOpen < endOfCurrentTag && nextStartTagOpen != -1) {
        var sttMsg = _bundle.GetStringFromName("htmlRelocatorNotClosed");
        require("notify/notify").send(sttMsg, "editor", {priority: "warning"});
        return;
    } 
    endOfCurrentTag  = scimoz.positionAfter(endOfCurrentTag);
    
    log.debug("tag_relocator: makeRelocatorSelection: \nStart of Current Tag: "+
              startOfCurrentTag +
              "\nEnd of current tag: " + endOfCurrentTag);
    
    if (startOfCurrentTag == endOfCurrentTag) {
        var stMg = _bundle.GetStringFromName("htmlRelocatorNothingSelected");
        require("notify/notify").send(stMsg, "editor", {priority: "warning"});
    } else {
        scimoz.setSel(startOfCurrentTag, endOfCurrentTag);
        saveRelocatorSelection(scimoz.selectionStart, scimoz.selectionEnd);
        log.debug("tag_relocator: makeRelocatorSelection: Saved selection " +
                  "start: " + view._htmlTagRelocator.savedSelectionStart +
                  "\nSaved selection end: " +
                  view._htmlTagRelocator.savedSelectionEnd);
    }
}
 /**
  * Skip tags/words manually to the right
  * @precondition scimoz.currentPos != anchor
  * @precondition view._htmlTagRelocator is set
  * @postcondition view._htmlTagRelocator is deleted
  */
function skipWordsTagsRight(view, scimoz) {
    log.debug("Running skipWordsTagsRight() in ko.editor.");
    var endOfDocument = scimoz.length;
    var {savedSelectionStart, savedSelectionEnd} = view._htmlTagRelocator;
    var text = scimoz.selText;
    
    var whitespaceObject = {};
    scimoz.getWhitespaceChars(whitespaceObject);
    var whiteSpace = whitespaceObject.value;
    var currentLine = scimoz.lineFromPosition(savedSelectionEnd)
    var shufflePos = savedSelectionEnd;

    // skip the white space to the start of the next character
    // Wrapping this in a while accounts for EOL characters.
    while(whiteSpace.contains(scimoz.getWCharAt(shufflePos)))
    {
        shufflePos = scimoz.wordEndPosition(shufflePos, false);
        
    }

    // Check if that next character is a tag and jump over the
    // whole tag if it is
    var styleOfNextChar = scimoz.getStyleAt(shufflePos);
    if (VALID_TAG_STYLES.indexOf(styleOfNextChar) >= 0)
    {
        // Move to the position after the next ">" that is a valid closing
        // character
        var nextValidChar = findNextValidCloseOpenSymbol(
                                shufflePos, endOfDocument, ">")
        // If there are no more then just jump past everything to the end
        // of the doc.  It's what the user would have wanted...
        if (nextValidChar == -1) {
            var statMsg =  _bundle.GetStringFromName("htmlRelocatorNoEnd");
            require("notify/notify").send(statMsg, "editor", {priority: "warning"});
            nextValidChar = endOfDocument;
        }
        shufflePos = scimoz.positionAfter(nextValidChar);
    } else {
        var curChar = scimoz.getWCharAt(shufflePos);
        var curCharStyle = scimoz.getStyleAt(shufflePos);
        if (scimoz.wordChars.contains(curChar)) {
            shufflePos = scimoz.wordEndPosition(shufflePos, false);
        } else {
            /*
             * Punctuation is not included in scimoz.wordChars.  Must manually
             * skip until another word or tag is hit.
             */
            var relWordChars = scimoz.wordChars;
            var docEnd = scimoz.length;
            for(; shufflePos < docEnd; ++shufflePos) {
                curCharStyle = scimoz.getStyleAt(shufflePos);
                if (VALID_TAG_STYLES.indexOf(curCharStyle) >= 0) {
                    break;
                }
                curChar = scimoz.getWCharAt(shufflePos);
                if (relWordChars.contains(curChar)) {
                    break;
                }
            }
        }
    }
    moveRelocatorText(savedSelectionStart,
             savedSelectionEnd - savedSelectionStart,
             shufflePos,
             text);
}

/*
 * move text from one position to a another
 * @postcondition view._htmlRelocator is set.
 */
function moveRelocatorText(startDelete, lenDelete, newPos, text) {
    log.debug("Running moveRelocatorText()");
    var view = _getCurrentScimozView()
    var scimoz = view.scimoz;
    // If the cursor has been moved to a position past the tag, then its new
    // paste position must be offset by the length of the removed text
    if (newPos >= view._htmlTagRelocator.savedSelectionEnd) {
         newPos -= lenDelete;
    }
    scimoz.beginUndoAction();
    try {
        scimoz.deleteRange(startDelete, lenDelete);
        scimoz.insertText(newPos, text);
        scimoz.anchor = newPos;
        scimoz.currentPos = newPos + lenDelete;
        saveRelocatorSelection(scimoz.selectionStart, scimoz.selectionEnd);
    } catch(e) {
        log.exception(e.message);
    } finally {
        scimoz.endUndoAction();
    }
    log.debug("moveRelocatorText: Text moved: " + text);
}

/**
 * This function searches for the next close or open symbol with a valid style
 *
 * @param searchStart {Number} the position to start searching
 * @param searchEnd {Number}
 * @return the position {Number} of the 1st character after searchStart that
 *  isn't whitespace; -1 if no results.
 */
function findNextValidCloseOpenSymbol (searchStart, searchEnd, searchChar) {
        log.debug("Running findNextValidCloseOpenSymbol()");
        var view = _getCurrentScimozView();
        var scimoz = view.scimoz;
        scimoz.targetStart = searchStart;
        scimoz.targetEnd = searchEnd;

        var pos = scimoz.searchInTarget(1, searchChar);
        scimoz.targetEnd = searchEnd;
        while (pos >= 0 &&
               VALID_TAG_STYLES.indexOf(scimoz.getStyleAt(pos)) < 0)
        {
            if (searchEnd > searchStart){
                scimoz.targetStart = scimoz.positionAfter(pos)
            } else {
                scimoz.targetStart = scimoz.positionBefore(pos);
            }
            scimoz.targetEnd    = searchEnd;
            pos = scimoz.searchInTarget(1, searchChar);
        }
    return pos;
}

/**
 * Is the scimoz.currentPos inside of any tag?
 * Look behind the currentPos, find closest < and >.  If < is closer then > then
 * you must be in a tag.
 * Note: I don't use the VALID_TAG_STYLES list as that broken in certain use
 * cases, eg. Django templating <p attr="{{foo}}"> Needed a more generic way of
 * checking if I was in a tag.
 */
function relocatorInsideTag(scimoz) {
    var currentPos = scimoz.currentPos;
    var startOfLine = scimoz.positionFromLine(scimoz.lineFromPosition(currentPos));
    // posAfterCurPos is needed in case we are at the start of a tag, |<p>.
    // Would always return false in that case otherwise as it would not find
    // the "<".
    var posAfterCurPos = scimoz.positionAfter(currentPos);
    var startTagChar = findNextValidCloseOpenSymbol(posAfterCurPos, startOfLine,"<");
    var endTagChar = findNextValidCloseOpenSymbol(currentPos, startOfLine, ">");
    return startTagChar > endTagChar;
}

/**
 * save the current tag selected for moving
 * @postcondition view._htmlTagRelocator.relTimeout is reset
 * relTimeout is set so view._htmlTagRelocator doesn't stick around forever
 */
function saveRelocatorSelection(selStart, selEnd){
    var view = _getCurrentScimozView();
    if (view._htmlTagRelocator) {
        clearTimeout(view._htmlTagRelocator.relTimeout);
    }
    log.debug("saveRelocatorSelection: \nSel Start: " + selStart +
              "\nsel End: " + selEnd +
              "\nselText: " + view.scimoz.getTextRange(selStart, selEnd));
    
    view._htmlTagRelocator = {savedSelectionStart : selStart,
                              savedSelectionEnd   : selEnd,
                              savedText : view.scimoz.getTextRange(selStart,
                                                                   selEnd),
                              // XXX move relTimeout to preference
                              relTimeout: setTimeout(relocateTimeoutDelete,9999)
                              };
}
/**
 * Wraps deleteHtmlRelocator to added appropriate logging referencing the use
 * of setTimeout() in saveRelocatorSelection()
 */
function relocateTimeoutDelete(){
    log.debug("Timeout delete relocator variables");
    var sttMsg = _bundle.GetStringFromName("htmlRelocateRmVars");
    require("notify/notify").send(sttMsg, "editor", {priority: "warning"});
    deleteHtmlRelocator();
}
/**
 * make sure saved location is the tag wanted 
 * @returns true saved tag matches location found between savedSelectionStart
 * and savedSelectionEnd
 * This will happen when the user runs undo, can't update view._htmlTagRelocator
 */
function isContextCorrect(scimoz, view)  {
    var {savedSelectionStart,savedSelectionEnd,savedText} =
                                                    view._htmlTagRelocator;
    // If the user uses undo, the saved position of the tag is old.
    // Running the script again will use the pre-undo location.
    // Check if the saved location matches the previous tag.
    var prevTagLocation = scimoz.getTextRange(savedSelectionStart,
                                              savedSelectionEnd);
    return (savedText == prevTagLocation) 
}

/**
 * Remove _htmlTagRelocator variables
 */
function deleteHtmlRelocator() {
    log.debug("removing view._htmlRelocator");
    delete _getCurrentScimozView()._htmlTagRelocator;
}

// Keep a handle on the controller, for local functions to use.
editor_controller_instance = new editor_editorController();

// No window while testing so skip (jsTest)
if (typeof(window) != "undefined") {
    window.controllers.appendController(editor_controller_instance);
} else {
    ko.editor = editor_controller_instance;
}


}).apply(); // apply into the global namespace
