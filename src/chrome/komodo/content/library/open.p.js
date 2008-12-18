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
 * The open namespace contains functionality to open buffers in komodo
 */
ko.open = {};
(function() {
var fileLineNoRE = /^(.*)#(\d+)$/;
    
/**
 * Asynchronously open the URI in a new Komodo tab, if the file is already
 * open then this existing tab becomes the currently focused tab.
 *
 * If you need the view for the file that is opened from this call, pass in
 * a callback function argument and then this function will be called after
 * the view is opened (or re-focused if it was already open).
 *
 * @param uri {String} the path or URI to open
 * @param viewType {String} optional default "editor" type of view
 *        component to use. Values can be [ "editor", "browser", "diff" ].
 * @param skipRecentOpenFeature {boolean} optional default false, can
 *        be used when the URI to open is a project file to specify that
 *        the feature to open files in that project should not be offered.
 * @param callback {function} optional, to be called when the asynchronous load
 *        is complete. This will only be called if this opens or switches to
 *        an editor view, e.g. this won't be called for a kpf file. The view
 *        will be passed as an argument to the function.
 */
this.URI = function open_openURI(uri, viewType /* ="editor" */,
                                 skipRecentOpenFeature /* =false */,
                                 callback /* =null */) {
    try {
        // URI can be a local path or a URI
        uri = ko.uriparse.pathToURI(uri);
        // check for an attached line # in the form of:
        // file:///filename.txt#24
        var line = 0;
        var m = fileLineNoRE.exec(uri);
        if (m) {
            uri = m[1];
            line = m[2];
        }
        if (uri.match(/\.kpf$/i)) {
            ko.projects.open(uri, skipRecentOpenFeature);
        } else if (uri.match(/\.xpi$/i)) {
            if (InstallTrigger.enabled) {
                var xpi={'Komodo Extension': uri};
                InstallTrigger.install(xpi, null);
            } else {
                ko.dialogs.alert("Installing extensions is currently disabled.");
            }
        } else if (uri.match(/\.kpz$/i)) {
            ko.toolboxes.importPackage(ko.uriparse.URIToLocalPath(uri));
        } else {
            if (line) {
                ko.views.manager.doFileOpenAtLineAsync(uri, line, viewType, null, -1, callback);
            } else {
                ko.views.manager.doFileOpenAsync(uri, viewType, null, -1, callback);
            }
        }
    } catch(e) {
        log.exception(e);
    }
    return null;
}


/**
 * Open the given path in Komodo.
 *
 * If you need the view for the file that is opened from this call, pass in
 * a callback function argument and then this function will be called after
 * the view is opened (or re-focused if it was already open).
 *
 * @param displayPath {String} identifies the path to open. Display
 *        path may be the display path of an already open (and possibly
 *        untitled) document.
 * @param viewType {String} optional default "editor", the type of
 *        view to create for the openned path. It is ignored if the
 *        displayPath indicates an already open view.
 * @param callback {function} optional, to be called when the asynchronous load
 *        is complete. This will only be called if this opens or switches to
 *        an editor view, e.g. this won't be called for a kpf file. The view
 *        will be passed as an argument to the function.
 */
this.displayPath = function open_openDisplayPath(displayPath,
                                                 viewType /* ="editor" */,
                                                 callback /* =null */) {
    if (typeof(viewType) == "undefined" || !viewType) viewType = "editor";

    // Don't use `viewManager.getViewsByTypeAndURI()` because it doesn't handle
    // untitled views (bug 80232).
    var typedViews = ko.views.manager.topView.getViewsByType(true, viewType);
    var typedView;
    for (var i = 0; i < typedViews.length; ++i) {
        typedView = typedViews[i];
        if (! typedView.document) {
            continue;
        }
        if (_fequal(typedView.document.displayPath, displayPath)) {
            typedView.makeCurrent();
            if (callback) {
                callback(typedView);
                return;
            }
        }
    }

    // Fallback to open URI.
    ko.open.URI(displayPath, viewType, true, callback);
}


/**
 * Open Komodo's Start Page - the view will be opened synchronously.
 */
this.startPage = function open_openStartPage() {
    ko.views.manager._doFileOpen("chrome://komodo/content/startpage/startpage.xml#view-startpage",
                                 "startpage");
}

this.multipleURIs = function open_openMultipleURIs(urls, viewType)
{
    var i,j;
    if (urls.length) {
        var viewStateMRU = gPrefSvc.getPrefs("viewStateMRU");
        var projectFiles = [];
        var projectViewState,file_url;
        for (i=0; i < urls.length; i++) {
            if (viewStateMRU.hasPref(urls[i])) {
                projectViewState = viewStateMRU.getPref(urls[i]);
                if (projectViewState.hasPref('opened_files')) {
                    var opened_files = projectViewState.getPref('opened_files');
                    if (opened_files.length > 0) {
                        for (j=0; j < opened_files.length; j++) {
                            file_url = opened_files.getStringPref(j);
                            projectFiles.push(file_url);
                        }
                    }
                }
            }
        }

        var action;
        if (projectFiles.length > 0) {
            action = ko.dialogs.yesNoCancel(
                "One or more projects you are opening had files open "+
                "when you closed them.  Would you like to reopen "+
                "these files?",
                "Yes", null, null, // default response, text, title
                "open_recent_files_on_project_open");
            if (action == "Cancel") {
                return;
            }
            if (action == "Yes") {
                urls = urls.concat(projectFiles);
            }
        }

        if (urls.length > 1) {
            ko.views.manager.batchMode = true;
        }
        for (i=0; i < urls.length; i++) {
            if (i == urls.length-1) {
                ko.views.manager.batchMode = false;
            }
            ko.open.URI(urls[i], viewType, true);
        }
    }
}

/**
 * open a file picker, and open the files that the user selects
 */
this.filePicker = function view_openFilesWithPicker(viewType/*='editor'*/) {
    if (typeof(viewType)=='undefined' || !viewType) viewType = 'editor';

    // We want the default directory to be that of the current file if there is one
    var defaultDir = null;
    var v = ko.views.manager.currentView;
    if (v && v.getAttribute("type") == "editor" &&
        v.document && !v.document.isUntitled && v.document.file.isLocal)
    {
        defaultDir = ko.views.manager.currentView.document.file.dirName;
    }
    
    var paths = ko.filepicker.openFiles(defaultDir);
    if (paths == null) {
        return;
    }
    ko.open.multipleURIs(paths, viewType);
    if (ko.views.manager.currentView)
        window.setTimeout('ko.views.manager.currentView.setFocus();',1);
}

/**
 * open a file picker, and open the templates that the user selects.  This
 * allows editing the templates, it is not for creating new files from
 * templates.
 */
this.templatePicker = function view_openTemplatesWithPicker(viewType/*='editor'*/) {
    try {
        if (typeof(viewType)=='undefined' || !viewType) viewType = 'editor';

        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var templateSvc = Components.classes["@activestate.com/koTemplateService?type=file;1"].getService();
        var defaultDir = templateSvc.getUserTemplatesDir();
        var paths = ko.filepicker.openFiles(defaultDir);
        if (paths == null)
            return;
        ko.open.multipleURIs(paths, viewType);
    } catch (e) {
        log.exception(e);
    }
}


/* ---- internal support stuff ---- */

// Return true iff the two file paths are equal.
//TODO: Move this to a `ko.uriparse.arePathsEquivalent()` method.
function _fequal(a, b) {
// #if PLATFORM == "win" or PLATFORM == "darwin"
    return a.toLowerCase() == b.toLowerCase();
// #else
    return a == b;
// #endif
}

}).apply(ko.open);




// BC API
var open_openURI = ko.open.URI;
var open_openDisplayPath = ko.open.displayPath;
var open_openStartPage = ko.open.startPage;
var open_openMultipleURIs = ko.open.multipleURIs;

