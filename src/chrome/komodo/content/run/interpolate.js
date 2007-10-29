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

/**
 * Utility methods to easily use the KoIInterpolationService from JavaScript.
 * Basically you can use the ko.interpolate.interpolate() method to iterpolation
 * special '%'-escape codes in a given list of strings. See
 * koInterpolationService.py (or play around with "run commands") for an
 * authoritative description of available escape codes.
 *
 * How to interpolate a couple of strings (mystringa, mystringb). You can do as
 * many strings as you want.
 *
 *    var imystringa = null;
 *    var imystringb = null;
 *    try {
 *        var istrings = ko.interpolate.interpolate(
 *                          <ref-to-komodo.xul>,
 *                          [mystringa, mystringb],  // codes are not bracketed
 *                          [mystringc, mystringd],  // codes are bracketed
 *                          <optional-query-title>);
 *        imystringaForUse     = istrings[0];
 *        imystringaForDisplay = istrings[1];
 *        imystringbForUse     = istrings[2];
 *        imystringbForDisplay = istrings[3];
 *        imystringcForUse     = istrings[4];
 *        imystringcForDisplay = istrings[5];
 *        imystringdForUse     = istrings[6];
 *        imystringcForDisplay = istrings[7];
 *    } catch (ex) {
 *        var errno = lastErrorSvc.getLastErrorCode();
 *        if (errno == Components.results.NS_ERROR_ABORT) {
 *             // Command was cancelled.
 *        } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
 *            var errmsg = lastErrorSvc.getLastErrorMessage();
 *            alert("Could not interpolate:" + errmsg);
 *        } else {
 *            log.error(ex);
 *            alert("There was an unexpected error: " + ex);
 *        }
 *    }
 *
 */
ko.interpolate = {};
(function() {
var _log = ko.logging.getLogger("interpolate");

//---- public interface

this.isWordCharacter = function Interpolate_isWordCharacter(ch)
{
    return /^\w/.test(ch);
}

this.getWordUnderCursor = function Interpolate_getWordUnderCursor(scimoz) {
    var start = scimoz.wordStartPosition(scimoz.currentPos, true);
    var end = scimoz.wordEndPosition(scimoz.currentPos, true);
    return scimoz.getTextRange(start, end);
}

this.currentFilePath = function Interpolate_CurrentFilePath() {
    var editor = ko.windowManager.getMainWindow();
    var view = editor.ko.views.manager.currentView;
    if (view && view.document && view.document.file && view.document.file.isLocal) {
        return view.document.file.path;
    }
    return '';
}

this.currentFileProjectPath = function Interpolate_CurrentFileProjectPath() {
    // return the path of the project that the current file is in
    var editor = ko.windowManager.getMainWindow();
    var view = editor.ko.views.manager.currentView;
    var projectFile = '';
    if (view && view.document && view.document.file && view.document.file.isLocal) {
        var fileURL = view.document.file.URI;
        var filePart = editor.ko.projects.manager.findPartByTypeAttributeValue('file',
                                    'url', fileURL, true)
        if (filePart) {
            var projectPart = filePart.project;
            projectFile = ko.uriparse.displayPath(projectPart.url);
        }
    } else {
        // use current project if there are no files open
        var project = ko.projects.manager.getCurrentProject();
        if (project) {
            projectFile = ko.uriparse.displayPath(project.url);
        }
    }
    return projectFile;
}


this.activeProjectPath = function Interpolate_activeProjectPath() {
    // return the path of the active project
    var editor = ko.windowManager.getMainWindow();
    var project = editor.ko.projects.manager.getCurrentProject();
    var projectFile = '';
    if (project) {
        projectFile = ko.uriparse.displayPath(project.url);
    }
    return projectFile;
}

/**
 * A utility function to retrieving specific view data required by
 * Interpolate_interpolate().
 *  "editor" is a reference to the komodo.xul window.
 *  "viewData" (optional) is a object possibly containing overriding values for
 *      some of the view data.
 */
this.getViewData = function Interpolate_getViewData(editor,
                                 viewData /* =<determined from curr view> */)
{
    if (typeof viewData == 'undefined' || viewData == null)
        viewData = new Object();

    var view = editor.ko.window.focusedView();
    if (!view) view = editor.ko.views.manager.currentView;
    var scimoz = null;
    if (view && view.scintilla) {
        scimoz = view.scintilla.scimoz;
    }
    

    // fileName
    if ( !("fileName" in viewData) ) {
        if (view && view.document) {
            viewData.fileName = view.document.displayPath;
        } else {
            viewData.fileName = null;
        }
    }

    // projectFile
    if ( !("projectFile" in viewData) ) {
        viewData.projectFile = ko.interpolate.activeProjectPath();
    }

    // lineNum
    if ( !("lineNum" in viewData) ) {
        if (scimoz) {
            viewData.lineNum = scimoz.lineFromPosition(scimoz.currentPos) + 1;
        } else {
            viewData.lineNum = 0;
        }
    }

    // selection
    if ( !("selection" in viewData) ) {
        if (scimoz) {
            viewData.selection = scimoz.selText;
        } else {
            viewData.selection = null;
        }
    }

    // word
    if ( !("word" in viewData) ) {
        if (scimoz) {
            viewData.word = ko.interpolate.getWordUnderCursor(scimoz);
        } else {
            viewData.word = null;
        }
    }

    // prefSet
    if ( !("prefSet" in viewData) ) {
        if (view) {
            viewData.prefSet = view.prefs;
        } else {
            viewData.prefSet = null;  // means: fallback to the global prefset
        }
    }

    return viewData;
}

/**
 * Interpolate '%'-escape codes in the given list(s) of strings.
 *
 *  "editor" is a reference the komodo.xul window.
 *  "strings" is a list of raw strings to interpolate.
 *  "bracketedStrings" is a list of raw strings to interpolate, using the bracketed form
 *  "queryTitle" (optional) is a title for the possible query dialog raised
 *      during interpolation.
 *  "viewData" (optional) allows one to override specific view data used for
 *      interpolation. By default view data is retrieved from the current view.
 *      This may not always be appropriate. It may be an object with one or
 *      more of the following attributes:
 *          "fileName" is the filename of the current file (null, if N/A);
 *          "lineNum" is the current line number (0, if N/A);
 *          "word" is the current word under cursor (null if none);
 *          "selection" is the current selection (null if none).
 *
 * On success, this function returns a *double* list of interpolated strings:
 * For each string in "strings" and "bracketedStrings" two strings are
 * returned. The first is the interpolated string for use and the second for
 * *display*. In most cases these are the same but they may differ, for
 * example, if a password query response was interpolated into the string which
 * should not be displayed in the Komodo UI.
 *
 * Otherwise an exception is raised and an error set on the last error service:
 *      koILastError errno      reason
 *      ----------------------- -----------------------------------------
 *      NS_ERROR_ABORT          User cancelled the query dialog.
 *      NS_ERROR_INVALID_ARG    A normal interpolation failure because of
 *                              invalid interp code usage.
 */
this.interpolate = function Interpolate_interpolate(editor, strings, bracketedStrings,
                                 queryTitle /* =null */,
                                 viewData /* =<determined from current view> */)
{
    try {
    if (typeof queryTitle == 'undefined') queryTitle = null;
    _log.info("interpolate.interpolate(editor, strings=["+strings+
                          "], bracketedStrings=["+bracketedStrings+"], queryTitle='"+
                          queryTitle+"', viewData)");
    viewData = ko.interpolate.getViewData(editor, viewData);

    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                       .getService(Components.interfaces.koILastErrorService);

    // Interpolation step 1: get queries.
    var queriesCountObj = new Object();
    var queriesObj = new Array();
    var i1countObj = new Object();
    var i1stringsObj = new Array();

    //XXX The prefset used may need to be the project prefs at some point in
    //    the future, for now we'll stick with the current view's prefset.
    var iSvc = Components.classes["@activestate.com/koInterpolationService;1"]
               .getService(Components.interfaces.koIInterpolationService);
    iSvc.Interpolate1(strings.length, strings,
                      bracketedStrings.length, bracketedStrings,
                      viewData.fileName, viewData.lineNum,
                      viewData.word, viewData.selection,
                      viewData.projectFile,
                      viewData.prefSet,
                      queriesCountObj, queriesObj,
                      i1countObj, i1stringsObj);
    var queries = queriesObj.value;
    var istrings = i1stringsObj.value;

    // Ask the user for required data. (If there are no queries then we are
    // done interpolating.)
    if (queries.length != 0) {
        var obj = new Object();
        obj.queries = queries;
        obj.title = queryTitle;
        window.openDialog("chrome://komodo/content/run/interpolationquery.xul",
                          "Komodo:InterpolationQuery",
                          "chrome,modal,titlebar",
                          obj);
        if (obj.retval == "Cancel") {
            var errmsg = "Interpolation query cancelled.";
            lastErrorSvc.setLastError(Components.results.NS_ERROR_ABORT,
                                      errmsg);
            throw errmsg;
        }

        // Interpolation step 2: interpolated with answered queries.
        var i2countObj = new Object();
        var i2stringsObj = new Array();
        iSvc.Interpolate2(istrings.length, istrings,
                          queries.length, queries,
                          i2countObj, i2stringsObj);
        istrings = i2stringsObj.value;
    }

    _log.info("interpolate.interpolate: istrings=["+istrings+"]");
    return istrings;
    } catch(e) {
        _log.exception(e);
        throw e;
    }
}

this.interpolateStrings = function(s, bracketed /*=false*/, queryTitle)
{
    if (typeof(queryTitle) == "undefined") queryTitle = "Interpolation Query";
    if (typeof(bracketed) == "undefined") bracketed = false;
    _log.debug("interpolateStrings('"+s+"', bracketed="+bracketed+", queryTitle=["+queryTitle+"])");
    var istring = null;

    //XXX We are assuming that ko.interpolate.interpolate() gathers
    //    viewData for the same view for this same view for which this
    //    macro is being run. Currently in Komodo this is the current
    //    view for both so we are fine.
    var bracketedStrings, strings;
    if (bracketed) {
        strings = [];
        bracketedStrings = [s];
    } else {
        strings = [s];
        bracketedStrings = [];
    }
    try {
        var mainWindow = ko.windowManager.getMainWindow();
        var istrings = ko.interpolate.interpolate(mainWindow, strings,
                                               bracketedStrings,
                                               queryTitle);
        istring             = istrings[0];
        //istringForDisplay = istrings[1];
    } catch (ex) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                           .getService(Components.interfaces.koILastErrorService);
        var errno = lastErrorSvc.getLastErrorCode();
        if (errno == Components.results.NS_ERROR_ABORT) {
            // interpolation was cancelled.
        } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
            var errmsg = lastErrorSvc.getLastErrorMessage();
            throw("could not interpolate string: " + errmsg);
        } else {
            throw(ex);
        }
    }
    return istring;
}

/** 
 * Return a list of start and end offsets of interpolation code blocks into the
 * given strings "s".
 */
this.getBlockOffsets = function Interpolate_getBlockOffsets(s, bracketed)
{
    var offsetsCountObj = new Object();
    var offsetsObj = new Array();
    var iSvc = Components.classes["@activestate.com/koInterpolationService;1"]
               .getService(Components.interfaces.koIInterpolationService);
    iSvc.GetBlockOffsets(s, bracketed, offsetsCountObj, offsetsObj);
    var offsets = offsetsObj.value;

    return offsets;
}


}).apply(ko.interpolate);


// backwards compatibility apis
var Interpolate_isWordCharacter = ko.interpolate.isWordCharacter;
var Interpolate_getWordUnderCursor = ko.interpolate.getWordUnderCursor;
var Interpolate_CurrentFilePath = ko.interpolate.currentFilePath;
var Interpolate_CurrentFileProjectPath = ko.interpolate.currentFileProjectPath;
var Interpolate_activeProjectPath = ko.interpolate.activeProjectPath;
var Interpolate_getViewData = ko.interpolate.getViewData;
var Interpolate_interpolate = ko.interpolate.interpolate;
var Interpolate_getBlockOffsets = ko.interpolate.getBlockOffsets;
