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

// hide this controller from our global namespace, we simply dont need to
// touch anything in it from the outside world
(function() {
    
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/editor.properties");
    
function editor_editorController() {
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
editor_editorController.prototype = new xtk.Controller();
editor_editorController.prototype.constructor = editor_editorController;

editor_editorController.prototype.destructor = function() {
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
    if (v) {
        var exist = v.scintilla.scimoz[sci_prop_name];
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
    ko.views.manager.currentView.prefs.setBooleanPref(pref_name, !existing_val);
    // DONT update SciMoz here - let the preference notify mechanism
    // trigger the normal preference handling code.
}


//---- find stuff

editor_editorController.prototype.is_cmd_findNextSelected_enabled = function() {
    return ko.views.manager.currentView ? true : false;
}

editor_editorController.prototype.do_cmd_findNextSelected = function(backwards /* false */) {
    if (typeof(backwards) == 'undefined' || backwards == null) {
        backwards = false;
    }
    var v = ko.views.manager.currentView;
    var scimoz = v.scintilla.scimoz
    if (!scimoz) return;
    var pattern = scimoz.selText;
    if (pattern == '') {
        scimoz.wordLeft();
        var curChar = scimoz.getWCharAt(scimoz.currentPos);
        while (curChar.search(/\W/) == -1) {
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
    Find_FindNext(window, context, pattern);
}

editor_editorController.prototype.is_cmd_findPreviousSelected_enabled = function() {
    return ko.views.manager.currentView ? true : false;
}

editor_editorController.prototype.do_cmd_findPreviousSelected = function() {
    this.do_cmd_findNextSelected(/* backwards */ true);
}

editor_editorController.prototype.is_cmd_bookmarkToggle_enabled = function() {
    return ko.views.manager.currentView != null;
}
editor_editorController.prototype.do_cmd_bookmarkToggle = function() {
    var v = ko.views.manager.currentView;
    var line_no = v.scintilla.scimoz.lineFromPosition(v.scintilla.scimoz.selectionStart);
    var markerState = v.scintilla.scimoz.markerGet(line_no);
    if (markerState & (1 << ko.markers.MARKNUM_BOOKMARK)) {
        v.scintilla.scimoz.markerDelete(line_no, ko.markers.MARKNUM_BOOKMARK);
    } else {
        ko.history.note_curr_loc(v);
        v.scintilla.scimoz.markerAdd(line_no, ko.markers.MARKNUM_BOOKMARK);
    }
}

editor_editorController.prototype.is_cmd_bookmarkRemoveAll_enabled = function() {
    return ko.views.manager.currentView != null;
}
editor_editorController.prototype.do_cmd_bookmarkRemoveAll = function() {
    var v = ko.views.manager.currentView;
    if (v) v.scintilla.scimoz.markerDeleteAll(ko.markers.MARKNUM_BOOKMARK);
}

editor_editorController.prototype.is_cmd_bookmarkGotoNext_enabled = function() {
    return ko.views.manager.currentView != null;
}
editor_editorController.prototype.do_cmd_bookmarkGotoNext = function() {
    var v = ko.views.manager.currentView;
    var thisLine = v.scintilla.scimoz.lineFromPosition(v.scintilla.scimoz.selectionStart);
    var marker_mask = 1 << ko.markers.MARKNUM_BOOKMARK;
    var nextLine = v.scintilla.scimoz.markerNext(thisLine+1, marker_mask);
    if (nextLine < 0) {
        // try for search from top of file.
        nextLine = v.scintilla.scimoz.markerNext(0, marker_mask);
    }
    if (nextLine < 0 || nextLine == thisLine) {
        ko.statusBar.AddMessage(_bundle.GetStringFromName("noNextBookmark.message"),
                            "bookmark",
                             3000, true);
    } else {
        ko.history.note_curr_loc(v);
        v.scintilla.scimoz.ensureVisibleEnforcePolicy(nextLine);
        v.scintilla.scimoz.gotoLine(nextLine);
    }
}


editor_editorController.prototype.is_cmd_bookmarkGotoPrevious_enabled = function() {
    return ko.views.manager.currentView != null;
}
editor_editorController.prototype.do_cmd_bookmarkGotoPrevious = function() {
    var v = ko.views.manager.currentView;
    var thisLine = v.scintilla.scimoz.lineFromPosition(v.scintilla.scimoz.selectionStart);
    var marker_mask = 1 << ko.markers.MARKNUM_BOOKMARK;
    var prevLine = v.scintilla.scimoz.markerPrevious(thisLine-1, marker_mask);
    if (prevLine < 0) {
        // try for search from bottom of file.
        prevLine = v.scintilla.scimoz.markerPrevious(v.scintilla.scimoz.lineCount-1, marker_mask);
    }
    if (prevLine < 0 || prevLine == thisLine) {
        ko.statusBar.AddMessage(_bundle.GetStringFromName("noPreviousBookmark.message"),
                            "bookmark.message",
                             3000, true);
    } else {
        ko.history.note_curr_loc(v);
        v.scintilla.scimoz.ensureVisibleEnforcePolicy(prevLine);
        v.scintilla.scimoz.gotoLine(prevLine);
    }
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
    try {
        ko.views.manager.currentView.document.language = '';
        ko.views.manager.currentView.document.language = ko.views.manager.currentView.document.language;
        ko.views.manager.currentView.scimoz.colourise(0, -1);
    } catch (e) {
        log.exception(e);
    }
}

editor_editorController.prototype.is_cmd_browserPreview_enabled = function() {
    var view = ko.views.manager.currentView;
    return (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.document && view.document.file && view.document.file.isLocal);
}

editor_editorController.prototype.do_cmd_browserPreview = function() {
    var view = ko.views.manager.currentView;
    var canPreview = (view != null &&
            view.getAttribute('type') == 'editor' &&
            view.document && view.document.file && view.document.file.isLocal);
    if (canPreview)
        ko.views.manager.currentView.viewPreview();
}


window.controllers.appendController(new editor_editorController());

}).apply(); // apply into the global namespace
