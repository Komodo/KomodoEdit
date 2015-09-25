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

/* Komodo view handling.
 * This is a singleton which provides simple interface to
 *   - currentView: The current view
 *
 * It also holds the controller for toplevel view-related commands
 * and "command-like" code to open files for example.

 * It manages internally which is the toplevel viewlist
 * (to which new views are added by default)

INTERFACE:

    ko.views.manager.currentView: The currently focused view

    ko.views.manager.topView: The toplevel viewlist -- this is what new views
                      get added to by default.


The viewMgr is also a controller for "top-level" commands such as
"cmd_bufferClose".

The viewMgr is an observer on "view_opened" and "view_closed" and
"current_view_changed" notifications.

OPTIMIZATION NOTE:

The viewMgr could also listen for "select" events, to filter out 'select' events that
don't correspond to real selection changes.  At this point that is not done.

*/

xtk.include('domutils');
xtk.include('controller');

if (typeof(ko.views)=='undefined') {
    ko.views = {};
}

(function() {

var locals = {};

XPCOMUtils.defineLazyGetter(locals, "bundle", function()
    Services.strings.createBundle("chrome://komodo/locale/views.properties"));

function viewManager() {
    this.log = ko.logging.getLogger('views');
    //this.log.setLevel(ko.logging.LOG_DEBUG);
    this.log.info("viewManager constructor");
    this._shuttingDown = false;
    /**
     * The current view that is shown in Komodo's main tab.
     * @type Components.interfaces.koIScintillaView
     */
    this.currentView = null;
    this.topView = document.getElementById('topview');
    this.topView.init();
    ko.main.addCanCloseHandler(this.canClose, this);
    ko.main.addWillCloseHandler(this.postCanClose, this);
    Services.obs.addObserver(this, "open_file", false); // commandment
    Services.obs.addObserver(this, "open-url",false);
    Services.obs.addObserver(this, "file_status", false);
    Services.obs.addObserver(this, "select", false);
    Services.obs.addObserver(this, "new_window",false);
    var self = this;
    this.handle_current_view_changed_setup = function(event) {
        self.handle_current_view_changed(event);
    };
    this.handle_view_list_closed = function(event) {
        self.currentView = null;
    };
    this.handle_view_closed_setup = function(event) {
        self.handle_view_closed();
    };
    this.handle_view_opened_setup = function(event) {
        self.handle_view_opened();
    };
    window.addEventListener('current_view_changed',
                            this.handle_current_view_changed_setup, false);
    window.addEventListener('view_list_closed',
                            this.handle_view_list_closed, false);
    window.addEventListener('view_closed',
                            this.handle_view_closed_setup, false);
    window.addEventListener('view_opened',
                            this.handle_view_opened_setup, false);
    this._viewCount = 0;
    this.batchMode = false;
    this.lastviewcache = this.cacheCommandData(null);
    window.controllers.appendController(this);
};

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
viewManager.prototype = new xtk.Controller();
viewManager.prototype.constructor = viewManager;

viewManager.prototype.shutdown = function()
{
    this._shuttingDown = true;
    try {
        window.controllers.removeController(this);
        Services.obs.removeObserver(this, "open_file");  // commandment
        Services.obs.removeObserver(this, "open-url");
        Services.obs.removeObserver(this, "file_status");
        Services.obs.removeObserver(this, "select");
        Services.obs.removeObserver(this, "new_window");
        window.removeEventListener('current_view_changed',
                                this.handle_current_view_changed_setup, false);
        window.removeEventListener('view_list_closed',
                                   this.handle_view_list_closed, false);
        window.removeEventListener('view_closed',
                                this.handle_view_closed_setup, false);
        window.removeEventListener('view_opened',
                                this.handle_view_opened_setup, false);
    } catch(e) {
        /* moz probably already removed them */
        this.log.warn('possible error shutting down viewManager:'+e);
    }
}

viewManager.prototype.canClose = function()
{
    try {
        this._dirtyItems = [];
        var dirtyItems = this.offerToSave();
        if (typeof(dirtyItems) == 'boolean')
            return dirtyItems;

        // we CAN shutdown.  Save the dirty items for handling
        // in the shutdown function above.  If the entire canClose
        // succeeds, these will be handled in the postCanClose below.
        this._dirtyItems = dirtyItems;
    } catch(e) {
        /* moz probably already removed them */
        this.log.exception(e,'exception in viewManager.canClose');
    }
    return true;
}

//Bad name -- should be "willClose"
viewManager.prototype.postCanClose = function()
{
    try {
        if (this._dirtyItems) {
            var i;
            var item;
            // first, unload the document service so that it no longer
            // auto saves files, then remove any autosave files that
            // might exist
            for (i = 0; i < this._dirtyItems.length; i++) {
                item = this._dirtyItems[i];
                if (item.view && item.view.koDoc)
                    item.view.koDoc.removeAutoSaveFile();
            }
        }
        this.shutdown();
        // We didn't call _doCloseViews originally when the view mgr
        // was designed around v2, for perf reasons,
        // which prob don't hold anymore.
        var ignoreFailures=true, doNotOfferToSave=true;
        this._doCloseViews(null /* all */, ignoreFailures, doNotOfferToSave);
    } catch(e) {
        /* moz probably already removed them */
        this.log.warn('exception in viewManager.postCanClose:'+e);
    }
    return false;
}

/**
 * Get the default directory based on a project or the current buffer.
 *
 * @private
 * @return {string} the current "default" directory to work from.
 */
viewManager.prototype._getDefaultDirectory = function() {
    // get the default dir from the current buffer directory, or the
    // current project directory
    var defaultDir = null;
    var project = ko.projects.manager.currentProject;
    if (project) {
        defaultDir = project.importDirectoryLocalPath;
    }
    if (!defaultDir) {
        var v = this.currentView;
        if (v
            && v.getAttribute("type") == "editor"
            && v.koDoc
            && !v.koDoc.isUntitled
            && v.koDoc.file
            && v.koDoc.file.isLocal)
        {
            defaultDir = this.currentView.koDoc.file.dirName;
        } else if (ko.places) {
            var koFileEx = Components.classes["@activestate.com/koFileEx;1"]
                             .createInstance(Components.interfaces.koIFileEx);
            koFileEx.URI = ko.places.manager.currentPlace;
            if (koFileEx.isLocal) {
                defaultDir = koFileEx.path;
            } else {
                defaultDir = ko.window.getHomeDirectory();
            }
        } else {
            defaultDir = ko.window.getHomeDirectory();
        }
    }
    return defaultDir;
}

/**
 * Create a new file based on a selected template. This will prompt the
 * user to select a template.
 *
 * @private
 * @param {string} defaultDir optional, current directory
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._newTemplate = function(defaultDir) {
    var view = null;
    if (!defaultDir) {
       defaultDir = this._getDefaultDirectory();
    }
    try {
        this.log.info("doing newTemplate: ");
        var uri;
        var saveto = null;

        // Get template selection from the user.
        var obj = new Object();
        obj.type = "file";
        obj.defaultDir = defaultDir;
        obj.filename = null;
        ko.launch.newTemplate(obj);
        if (obj.template == null) return null;

        uri = ko.uriparse.localPathToURI(obj.template);
        if (obj.filename)
            saveto = ko.uriparse.pathToURI(obj.filename);
        view = this._doFileNewFromTemplate(uri, saveto);
        if (!view) return null;
        window.setTimeout(function(view) {
            view.setFocus();
            if (view.koDoc && obj.template) {
                var currentLanguage = view.koDoc.language;
                // If the detected language is HTML, we may find a better
                // language name by checking the template filename, bug 88735.
                if (currentLanguage == "HTML" || currentLanguage == "Text") {
                    var requestedLanguage = Services.koLangRegistry.suggestLanguageForFile(obj.template);
                    if (currentLanguage != requestedLanguage) {
                        view.koDoc.language = requestedLanguage;
                        window.updateCommands('language_changed');
                    }
                }
            }
        }, 1, ko.views.manager.currentView);
    } catch(ex) {
        this.log.exception(ex, "Error in newTemplate.");
    }
    return view;
}


/**
 * Asynchronously create a new file based on a selected template. This
 * will prompt the user to select a template.
 *
 * @public
 * @param {string} defaultDir optional, current directory
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 */
viewManager.prototype.newTemplateAsync = function(defaultDir /*=null*/,
                                                  callback /*=null*/)
{
    if (typeof(defaultDir) == "undefined") defaultDir = null;
    if (typeof(callback) == "undefined") callback = null;
    window.setTimeout(function(mgr, defaultDir_, callback_) {
        var view = mgr._newTemplate(defaultDir_);
        if (callback_) {
            callback_(view);
        }
    }, 1, this, defaultDir, callback);
}


/**
 * Create a new file from the given template URI.
 *
 * @private
 * @param {string} uri optional, uri pointing to a template file
 * @param {string} saveto optional, where to save the new file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._doFileNewFromTemplate = function(uri,
                                                        saveto  /*=null*/,
                                                        viewType /*="editor"*/,
                                                        viewList /*=null*/)
{
    this.log.info("_doFileNewFromTemplate: ");
    if (typeof(viewType) == "undefined" || viewType == null) viewType = "editor";
    if (typeof(viewList) == "undefined") viewList = null;
    if (typeof(saveto) == "undefined") saveto = null;

    var localPath = ko.uriparse.URIToLocalPath(uri);
    var basename = ko.uriparse.baseName(uri);
    var ext, name;
    if (basename.indexOf('.')) {
        var p = basename.split('.');
        ext = '.'+p.slice(1).join('.');
        name = p[0];
    } else {
        ext = "";
        name = basename;
    }
    var errmsg;

    // Read the template.
    var doc = null;
    try {
        if (saveto) {
            doc = Services.koDocSvc.createFileFromTemplateURI(uri, saveto, false);
        } else {
            doc = Services.koDocSvc.createDocumentFromTemplateURI(uri, name, ext);
        }
    } catch (ex) {
        errmsg = Services.koLastError.getLastErrorMessage();
        this.log.exception(ex, errmsg);
        ko.dialogs.internalError(locals.bundle.GetStringFromName("errorOpeningTemplate.message"),
                                 locals.bundle.formatStringFromName("errorLoadingTemplate.message", [uri], 1),
                                 ex);
        // even though there is an error, continue opening the
        // file so the user gets *something*
        if (saveto) {
            doc = Services.koDocSvc.createDocumentFromURI(saveto);
        } else {
            var language = Services.koLangRegistry.suggestLanguageForFile(basename) || "Text";
            doc = Services.koDocSvc.createUntitledDocument(language);
        }
    }
    
    var docText = doc.buffer;
    var hasTabStops = ko.tabstops.textHasTabstops(docText);
    if (basename == "HTML.html"
        && ko.prefs.getStringPref('defaultHTMLDecl') == "-//W3C//DTD HTML 5//EN")
    {
        // Bug 99873: Replace the bogus HTML5 Doctype declaration
        // with a valid one, and set the language to HTML5
        var m = /<!DOCTYPE\s+HTML\s+PUBLIC\s+[\"']\[\[%\(pref:defaultHTMLDecl\)\]\][\"']\s*\[\[%\(pref:defaultHTMLDeclSystemIdentifier\)\]\]\s*>/i.exec(docText);
        if (m) {
            var m1 = /(\n|\r\n?)/.exec(docText) || ['', '\n'];
            docText = "<!doctype html>" + m1[1] + docText.substring(m[0].length);
            hasTabStops = ko.tabstops.textHasTabstops(docText);
            doc.language = "HTML5";
        }
    }
    try {
        // Interpolate any codes.
        var origViewData = { fileName :
                             saveto ? ko.uriparse.displayPath(saveto) : "" };
        var viewData = ko.interpolate.getViewData(window, origViewData);
        var istrings = ko.interpolate.interpolate(
                            window,
                            [], // codes are not bracketed
                            [docText], // codes are bracketed
                            locals.bundle.formatStringFromName("templateQuery.message", [name], 1),
                            viewData);
        var liveTextInfo = null;
        if (!hasTabStops) {
            doc.buffer = istrings[0];
        } else {
            try {
                liveTextInfo = ko.tabstops.parseLiveText(istrings[0]);
            } catch(ex) {
                ko.dialogs.alert(ex.message, ex.snippet);
                doc.buffer = docText;
                liveTextInfo = null;
            }
        }
    } catch (ex) {
        var errno = Services.koLastError.getLastErrorCode();
        if (errno == Components.results.NS_ERROR_ABORT) {
            // Command was cancelled.
        } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
            errmsg = Services.koLastError.getLastErrorMessage();
            ko.dialogs.alert(locals.bundle.formatStringFromName("couldNotInterpolate.message", [errmsg], 1));
        } else {
            this.log.exception(ex, locals.bundle.GetStringFromName("errorInterpolatingTemplate.message"));
            ko.dialogs.internalError(locals.bundle.formatStringFromName("couldNotProcessInterpolatingCodes.message", [basename], 1),
                                     locals.bundle.formatStringFromName("errorInterpolatingTemplateUri.message", [uri], 1),
                                     ex);
        }
    }

    // Load the template.
    if (/^(?:\/|\w:\\)/.test(uri)) {
        // Bug 81096: store templates as URIs
        try {
            uri = ko.uriparse.localPathToURI(uri);
        } catch(ex) {}
    }
    ko.mru.addURL("mruTemplateList", uri);
    if (saveto && !liveTextInfo) {
        doc.save(1);
    }
    doc.isDirty = false;
    var view;
    if (viewList) {
        view = viewList.createViewFromDocument(doc, viewType, -1);
    } else {
        view = this.topView.createViewFromDocument(doc, viewType, -1);
    }
    
    if (liveTextInfo) {
        doc.buffer = '';
        ko.tabstops.insertLiveText(view.scimoz, 0, liveTextInfo);
        view.scimoz.emptyUndoBuffer();
        if (saveto) {
            doc.save(1);
        }
        view.koDoc.setTabstopInsertionTable(liveTextInfo.tabstopInsertionTable.length,
                                               liveTextInfo.tabstopInsertionTable);
        view.moveToNextTabstop();
    }

    return view;
}

/**
 * Asynchronously create a new file based on the given template URI.
 *
 * @param {string} uri optional, uri pointing to a template file
 * @param {string} saveto optional, where to save the new file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 */
viewManager.prototype.doFileNewFromTemplateAsync = function(uri,
                                                       saveto  /*=null*/,
                                                       viewType /*="editor"*/,
                                                       viewList /*=null*/,
                                                       callback /*=null*/)
{
    window.setTimeout(function(mgr, uri_, saveto_, viewType_, viewList_, callback_) {
        var view = mgr._doFileNewFromTemplate(uri_, saveto_, viewType_, viewList_, callback_);
        if (callback_) {
            callback_(view);
        }
    }, 1, this, uri, saveto, viewType, viewList, callback);
}

/**
 * Create a new empty, unsaved buffer.
 *
 * @private
 *
 * @param {string} language optional, language of the buffer (eg. python)
 * @param {string} viewType optional, type of buffer to open, default "editor"
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._doNewView = function(language /*= prefs.fileDefaultNew*/,
                                            viewType /*='editor'*/)
{
    this.log.info("_doNewView: ");

    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(language)=='undefined' || !language) {
        language = ko.prefs.getStringPref('fileDefaultNew');
    }

    // the following line is delayed to avoid notifications during load()
    var doc = Services.koDocSvc.createUntitledDocument(language);
    var view = this.topView.createViewFromDocument(doc, viewType, -1);

    this.log.info("leaving _doNewView");
    return view;
}

/**
 * Asynchronously create a new empty, unsaved editor buffer.
 *
 * @param {string} language optional, language of the buffer (eg. python)
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 */
viewManager.prototype.doNewViewAsync = function(language /*= prefs.fileDefaultNew*/,
                                                viewType /*='editor'*/,
                                                callback /*=null*/)
{
    window.setTimeout(function(mgr, language_, viewType_, callback_) {
        var view = mgr._doNewView(language_, viewType_);
        if (callback_) {
            callback_(view);
        }
    }, 1, this, language, viewType, callback);
}


/**
 * Create a new buffer and open a file into it.
 * Note: The "uri" will *not* be translated by the mapped URI functionality.
 *
 * @private
 *
 * @param {string} uri uri to file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._newViewFromURI = function(uri,
                                                 viewType/*='editor'*/,
                                                 viewList/*=null*/,
                                                 index /* =-1 */)
{
    this.log.info("_newViewFromURI: " + uri);
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(viewList)=='undefined')
        viewList = null;
    if (typeof(index) == 'undefined' || index == null)
        index = -1;

    var doc = Services.koDocSvc.createDocumentFromURI(uri);
    var view = null;
    if (! doc.file.exists) {
        if (ko.dialogs.yesNo(locals.bundle.formatStringFromName("theFileDoesNotExist.message", [doc.file.displayPath], 1)) == "No") {
            return null;
        } else {
            var sysUtils = Components.classes["@activestate.com/koSysUtils;1"]
                            .createInstance(Components.interfaces.koISysUtils);
            try {
                sysUtils.Touch(doc.file.displayPath);
            } catch(touch_ex) {
                ko.dialogs.alert(locals.bundle.formatStringFromName("komodoWasUnableToCreateTheFile.alert", [doc.file.displayPath], 1));
                return null;
            }
            try {
                // Ensure the file status is updated now that the file exists.
                // http://bugs.activestate.com/show_bug.cgi?id=67949
                Services.obs.notifyObservers(this, 'file_changed', doc.file.URI);
            } catch (ex) {
                /* no listeners for this event */
            }
        }
    }
    if (doc.file.isDirectory) {
        this.notify_visited_directory(doc.file.path);
        return null;
    }
    try {
        if (doc.haveAutoSave() &&
            ko.dialogs.yesNo(locals.bundle.formatStringFromName("itAppearsTheFileWasNotSaved.alert", [doc.file.displayPath], 1)) == "Yes") {
            doc.restoreAutoSave();
        } else if (viewType != "browser") {
            doc.load();
        }
        // the following line is delayed to avoid notifications during load()
        if (viewList) {
            view = viewList.createViewFromDocument(doc, viewType, index);
        } else {
            view = this.topView.createViewFromDocument(doc, viewType, index);
        }
        var originalLanguage;
        if (doc.isLargeDocument
            && doc.prefs.hasPrefHere("originalLanguage")
            && ((originalLanguage = doc.prefs.getStringPref("originalLanguage"))
                != "Text")) {
            this.showLargeFileProblem(doc.file.displayPath, originalLanguage);
        }
    } catch (e)  {
        var err = Services.koLastError.getLastErrorMessage();
        ko.dialogs.alert(locals.bundle.formatStringFromName("komodoWasUnableToOpenTheFile.alert", [doc.file.baseName], 1),
                         err,
                         locals.bundle.GetStringFromName("fileOpenError.alert"));
        this.log.exception(e);
        view = null;
    }

    // Ensure file is scanned (bug 77866).
    if (ko.workspace.restoreInProgress()) {
        window.addEventListener("komodo-ui-started", function() {
            ko.codeintel.scan_document(doc, 0, true);
            doc = null;
        }, false);
    } else {
        ko.codeintel.scan_document(doc, 0, true);
    }

    this.log.info("_newViewFromURI");
    return view;
}

/**
 * Create a new buffer and open a file into it.
 * Note: The "uri" will *not* be translated by the mapped URI functionality.
 *
 * @param {string} uri uri to file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 */
viewManager.prototype.newViewFromURIAsync = function(uri,
                                                     viewType/*='editor'*/,
                                                     viewList/*=null*/,
                                                     index /* =-1 */,
                                                     callback /* =null */)
{
    window.setTimeout(function(mgr, uri_, viewType_, viewList_, index_, callback_) {
        var view = mgr._newViewFromURI(uri_, viewType_, viewList_, index_);
        if (callback_) {
            callback_(view);
        }
    }, 1, this, uri, viewType, viewList, index, callback);
}

viewManager.prototype._openPreferredView = function(views, viewList) {
    if (viewList == null) {
        // If no tab group (viewList) is specified, maintain
        // pre-5.1 behavior of opening whichever view is found
        if (views.indexOf(this.currentView) >= 0) {
            // this uses the correct view in a splitview
            this.currentView.makeCurrent();
            return this.currentView;
        } else {
            views[0].makeCurrent();
            return views[0];
        }
    } else {
        // If a tab group is specified, but the URI isn't
        // found on that tab group, open a new view.
        for (var i = 0; i < views.length; i++) {
            var possibleView = views[i];
            if (viewList.id == "view-" + possibleView.tabbedViewId) {
                possibleView.makeCurrent();
                return possibleView;
            }
        }
        return null;
    }
}

/**
 * Open a file. If it is already open, then select that buffer,
 * else create a new buffer for the file.
 * Note: The "uri" will be translated using the mapped URI functionality.
 *
 * @private
 *
 * @param {string} uri uri to file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *      optional, what pane to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *      the new view. If not given, or -1, then the new view is appended.
 *      If there is already a view open for this `uri`, then index is ignored.
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._doFileOpen = function(uri,
                                             viewType/*='editor'*/,
                                             viewList/*=null*/,
                                             index /* =-1 */)
{
    if (typeof(viewList)=='undefined')
        viewList = null;
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(index) == 'undefined' || index == null)
        index = -1;

    if (viewType == 'editor') {
        uri = ko.uriparse.getMappedURI(uri);
    }
    var views = this.topView.getViewsByTypeAndURI(true, viewType, uri);
    if (views.length > 0) {
        var existingView = this._openPreferredView(views, viewList);
        if (existingView) {
            return existingView;
        }
    }
    return this._newViewFromURI(uri, viewType, viewList, index);
}

/**
 * Asyncronously open a file. If it is already open, then select that buffer,
 * else create a new buffer for the file.
 * Note: The "uri" will be translated using the mapped URI functionality.
 *
 * @param {string} uri uri to file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *      optional, what pane to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *      the new view. If not given, or -1, then the new view is appended.
 *      If there is already a view open for this `uri`, then index is ignored.
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 */
viewManager.prototype.doFileOpenAsync = function(uri,
                                                 viewType/*='editor'*/,
                                                 viewList/*=null*/,
                                                 index /* =-1 */,
                                                 callback /* =null */)
{
    window.setTimeout(function(mgr, uri_, viewType_, viewList_, index_, callback_) {
        var view = mgr._doFileOpen(uri_, viewType_, viewList_, index_);
        if (callback_) {
            callback_(view);
        }
    }, 1, this, uri, viewType, viewList, index, callback);
}

/**
 * Open a file at the given line number. If it is already open, then select
 * that buffer, else create a new buffer for the file.
 *
 * @private
 *
 * @param {string} uri uri to file
 * @param {integer} lineno line number
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._doFileOpenAtLine = function(uri,
                                                  lineno,
                                                  viewType/*='editor'*/,
                                                  viewList/*=null*/,
                                                  index /* =-1 */)
{
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(viewList)=='undefined')
        viewList = null;
    if (typeof(index) == 'undefined' || index == null)
        index = -1;
    var v = this._doFileOpen(uri, viewType, viewList, index);
    if (v) {
        var actualLineNo = Math.max(lineno - 1, 0);  // scimoz is 0-indexed
        this.ensureAtLine(v, actualLineNo);
    }
    return v;
}

viewManager.prototype.ensureAtLine = function(view, lineno, anchor, currentPos) {
    var scimoz = view.scimoz;
    view.registerUpdateUICallback(function() {
        this._ensureAtLine(view, scimoz, lineno, 20, 10);
        // Bug 98866: Don't try scrolling to the caret
        // until Scintilla has fired an onUpdateUI event
        // On OSX, we'll probably need to wait until
        // scimoz.linesOnScreen is no longer 0.
    }.bind(this));
    // do gotoline first because it messes w/ current position and anchor.
    scimoz.gotoLine(lineno);
    if (typeof(anchor) != "undefined") {
       scimoz.anchor = anchor;
    }
    if (typeof(currentPos) != "undefined") {
       scimoz.currentPos = currentPos;
    }
    view.verticallyAlignCaret("onethird");
}

viewManager.prototype._ensureAtLine = function _ensureAtLine(view, scimoz, lineno, delay, chancesLeft) {
    if (view != this.currentView) {
        //dump("We moved to another view, so abort\n");
        return;
    }
    scimoz.scrollCaret();
    // Allow for folded and wrapped lines.
    var firstDocLine = scimoz.docLineFromVisible(scimoz.firstVisibleLine);
    var lastDocLine = scimoz.docLineFromVisible(scimoz.firstVisibleLine + scimoz.linesOnScreen);
    if (firstDocLine <= lineno && lineno <= lastDocLine) {
        // We're ok
        return;
    }
    if (chancesLeft < 0) {
        // We're not ok, but give up
        return;
    }
    // "Wait " + delay + "msec.  Try to change the view again...\n")
    setTimeout(this._ensureAtLine.bind(this), delay, view, scimoz, lineno, delay, chancesLeft - 1);
}
/**
 * Asyncronously open a file at the given line number. If it is already open,
 * then select that buffer, else create a new buffer for the file.
 *
 * @param {string} uri uri to file
 * @param {integer} lineno line number
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 */
viewManager.prototype.doFileOpenAtLineAsync = function(uri,
                                                       lineno,
                                                       viewType/*='editor'*/,
                                                       viewList/*=null*/,
                                                       index /* =-1 */,
                                                       callback /* =null */)
{
    window.setTimeout(function(mgr, uri_, lineno_, viewType_, viewList_, index_, callback_) {
        var view = mgr._doFileOpenAtLine(uri_, lineno_, viewType_, viewList_, index_);
        if (callback_) {
            callback_(view);
        }
    }, 1, this, uri, lineno, viewType, viewList, index, callback);
}

/**
 * 
 * Asynchronously open a view, optionally in the specified tabbed list
 * and at the specified tab position.
 *
 * @param {string} uri uri to file
 * @param {string} viewType optional, type of buffer to open, default "editor"
 * @param {string} tabGroup optional, which tab group to open the buffer in
 * @param {integer} index optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 *
 * @return null
 */
viewManager.prototype.openViewAsync = function(viewType, uri, tabGroup, tabIndex, callback) {
    if (typeof(viewType) == "undefined" || viewType == null) viewType = "editor";
    if (typeof(tabGroup) == "undefined") tabGroup = null;

    var tabList = tabGroup ? document.getElementById(tabGroup) : null;
    switch (viewType) {
    case "quickstart":
        uri = "chrome://komodo/content/quickstart.xml#view-quickstart";
        break;
    case "editor":
        ko.views.manager.doFileOpenAsync(uri, viewType, tabList, tabIndex, callback);
        break;
    case "browser":
        var views = this.topView.getViewsByTypeAndURI(true, viewType, uri);
        if (views.length > 0) {
            var existingView = this._openPreferredView(views, tabList);
            if (existingView) {
                if (callback) {
                    callback(existingView);
                }
                break;
            }
        }
        ko.views.manager.newViewFromURIAsync(uri, 'browser', tabList, tabIndex, callback);
        break;
    default:
        this.log.error("Don't know how to open " + viewType + " views\n");
    }
}

/**
 * Return all opened views in Komodo of type 'viewType'. If no viewType is
 * specified then all views are returned. Use a viewType of 'editor' for the
 * Komodo editor views.
 *
 * @public
 * @since Komodo 5.2.0
 * 
 * @param {string} viewType optional, type of views to return, default is all
 * @param {object} xpcomCount optional, only used when called via XPCOM.
 * @return {array}  The array of views.
 */
viewManager.prototype.getAllViews = function(viewType /* all */, xpcomCount) {
    var views = ko.views.manager.topView.getDocumentViewList(true);
    if (viewType && viewType != "all") {
        views = views.filter(function(elem, index, array) { return elem.getAttribute("type") == viewType; });
    }
    if (xpcomCount /* only provided in XPCOM calls */) {
        xpcomCount.value = views.length;
    }
    return views;
}

/**
 * Get a reference to the buffer view for the given URI and view type.
 *
 * @public
 * @since Komodo 4.3.0
 * 
 * @param {string} uri URI to file
 * @param {string} viewType optional, type of view to find, default is any
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.getViewForURI = function(uri, viewType) {
    var v;
    if (viewType) {
        v = this.topView.getViewsByTypeAndURI(true, viewType, uri);
    } else {
        v = this.topView.findViewsForURI(uri);
    }
    if (v.length > 0)
        return v[0];
    return null;
}

/**
 * Get all references to the buffer view for the given URI
 *
 * @public
 * @since Komodo 5.2.0
 * 
 * @param {string} uri URI to file
 * @return list of {Components.interfaces.koIView} (open buffer views)
 */
viewManager.prototype.getAllViewsForURI = function(uri) {
    return this.topView.findViewsForURI(uri);
}

/**
 * get a reference to a new and unsaved buffer view
 *
 * @public
 * @param {string} name name of the buffer
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.getUntitledView = function(name) {
    try {
        var doc = Services.koDocSvc.findDocumentByURI(name);
        return this.topView.findViewForDocument(doc);
    } catch (e) {
        this.log.exception(e);
    }
    return null;
}

/**
 * get a reference to the buffer for a document
 * 
 * @public
 * @param doc {Components.interfaces.koIDocument} the document object
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.getViewForDocument = function(doc) {
    return this.topView.findViewForDocument(doc);
}

/**
 * Show that we're opening/saving-as a large document:
 */

viewManager.prototype.showLargeFileProblem = function(path, languageName) {
    ko.dialogs.alert(locals.bundle.GetStringFromName("newFileHasLongLines.prompt"),
                     locals.bundle.formatStringFromName("newFileAddedAsText.template",
                                                  [path, languageName], 2),
                     null, // title
                     "treat_large_documents_as_text");
};

/**
 * Used to reset the cached information for the current view
 */
viewManager.prototype.resetLastViewCache = function()
{
    if (this.currentView) {
        this.lastviewcache = this.cacheCommandData(this.currentView);
    }
}

/**
 * Used to cache a default set of information for a view
 */
viewManager.prototype.cacheCommandData = function(view)
{
    var cache = new Object();
    cache.type = null;
    cache.hasSelection = false;
    cache.isDirty = false;
    cache.canUndo = false;
    cache.canRedo = false;
    cache.canFold = false;
    cache.language = null;
    cache.isLocal = false;
    if (view) {
        cache.type = view.getAttribute('type');
        if (view.koDoc) {
            cache.hasSelection = view.selection !== undefined && view.selection != '';
            cache.isDirty = view.koDoc.isDirty
            if (cache.type == 'editor') {
                cache.canUndo = view.scintilla.canUndo();
                cache.canRedo = view.scintilla.canRedo();
                cache.isLocal = view.koDoc.file && view.koDoc.file.isLocal;
            }
            if (view.koDoc.languageObj) {
                cache.canFold = view.koDoc.languageObj.foldable;
                cache.language = view.koDoc.language;
            }
        }
    }
    return cache
}

viewManager.prototype.handle_open_file = function(topic, data)
{
    try {
        this.log.info("got open_file notification: " + data);
        var urllist = data.split('|'); //see asCommandLineHandler.js
        for (var i = 0; i < urllist.length; i++) {
            var thisPart = urllist[i];
            var uri;
            var fname = '';
            var anchorDesc = '';
            var currentPosDesc = '';
            var currentPos, anchor = 0;
            if (thisPart.indexOf('\t') != -1) { // We have a selection specification
                var parts = thisPart.split('\t');
                fname = parts[0];
                var subparts = parts[1].split('-');
                switch (subparts.length) {
                  case 1:
                   // Only one position is specified -- use it
                   // for both anchor and currentPos
                   anchorDesc = subparts[0];
                   currentPosDesc = anchorDesc;
                   break;
                  case 2:
                   // it's <anchor>-<currentPos>
                   anchorDesc = subparts[0];
                   currentPosDesc = subparts[1];
                   break;
                  default:
                   this.log.error("Error processing data segment of " +
                                  topic + " notification: " + thisPart);
                }
            } else {
                fname = thisPart;
            }
            try {
                uri = ko.uriparse.localPathToURI(fname);
            } catch(ex) {
                // Maybe it is a URI already?
                uri = fname;
            }
            ko.open.URI(uri, null, false,
                function(view) {
                    if (!view || !anchorDesc || !currentPosDesc) {
                        return;
                    }
                    var scimoz = view.scimoz;
                    var anchor, currentPos;
                    // Are we using character index or line,column?
                    if (anchorDesc.indexOf(',') == -1) {
                        anchor = Number(anchorDesc);
                    } else {
                        subparts = anchorDesc.split(',');
                        var anchorCol, anchorLine = Math.max(Number(subparts[0]) - 1, 0);
                        var lineStartPos, numBytes;
                        if (subparts[1][0] == 'p') {
                            anchorCol = Math.max(Number(subparts[1].substr(1)) - 1, 0);
                            // Don't expand tabs.  But do handle Unicode => utf8 expansion,
                            // to avoid selecting a partial character.
                            lineStartPos = scimoz.positionFromLine(anchorLine);
                            anchor = scimoz.positionAtChar(lineStartPos, anchorCol);
                        } else {
                            var anchorCol = Math.max(Number(subparts[1]) - 1, 0);
                            anchor = scimoz.positionAtColumn(anchorLine, anchorCol);
                        }
                    }
                    if (currentPosDesc.indexOf(',') == -1) {
                        currentPos = Number(currentPosDesc);
                    } else {
                        var currentPosCol;
                        subparts = currentPosDesc.split(',')
                        var currentPosLine = Math.max(Number(subparts[0]) - 1, 0);
                        if (subparts[1][0] == 'p') {
                            currentPosCol = Math.max(Number(subparts[1].substr(1)) - 1, 0);
                            lineStartPos = scimoz.positionFromLine(currentPosLine);
                            currentPos = scimoz.positionAtChar(lineStartPos, currentPosCol);
                        } else {
                            currentPosCol = Math.max(Number(subparts[1]) - 1, 0);
                            currentPos = view.positionAtColumn(currentPosLine, currentPosCol);
                        }
                    }
                    var lineNo = scimoz.lineFromPosition(currentPos);
                    var actualLineNo = Math.max(lineNo - 1, 0);
                    this.ensureAtLine(view, actualLineNo, anchor, currentPos);
                }.bind(this)
            );
            // Force the main window to the forefront
            //precondition: window == ko.windowManager.getMainWindow()
            window.focus();
        }
    } catch (e) {
        this.log.exception(e);
    }
}

viewManager.prototype.observe = function(subject, topic, data)
{
    this.log.debug("_ViewObserver: observed '"+topic+"' notification: data='"+data+"'\n");
    switch (topic) {
        case 'open_file':
        case 'open-url': // see nsCommandLineServiceMac.cpp, bug 37787
            // This is also used by komodo macro API to open files from python
            if (ko.windowManager.getMainWindow() == window) {
                // Check if there is a new Komodo window being opened. If there
                // is one - then any new opened files should go to that window.
                var lastWindow = ko.windowManager.getLastAnyWindow();
                if (lastWindow && lastWindow.isStillLoading && 'arguments' in lastWindow) {
                    if (lastWindow.arguments && lastWindow.arguments[0]) {
                        // Add to the Window's uris argument.
                        var arg = lastWindow.arguments[0];
                        if ('uris' in arg) {
                            urllist = arg.uris; // Called from ko.launch.newWindow(uri)
                        } else {
                            urllist = [];
                        }
                        urllist.push(data);
                        arg['uris'] = urllist;
                        break;
                    }
                }
                ko.workspace.waitForProjectManager(function() {
                        this.handle_open_file(topic, data);
                    }.bind(this));
            }
            break;
        case 'file_status':
            var urllist = data.split('\n');
            var views;
            for (var u=0; u < urllist.length; ++u) {
                views = this.topView.findViewsForURI(urllist[u]);
                for (var i=0; i < views.length; ++i) {
                    // XXX optimize all this stuff
                    views[i].updateFileStatus();
                    views[i].updateDirtyStatus();
                    if (views[i] == this.currentView) {
                        // Ensure the cached information gets updated.
                        this.lastviewcache = this.cacheCommandData(this.currentView);
                    }
                }
            }
            break;
        case 'select':
            window.updateCommands('select');
            break;
        case 'new_window':
            if (ko.windowManager.getMainWindow() == window) {
                var new_window = ko.launch.newWindow();
                new_window.isStillLoading = true;
                new_window.addEventListener("load", function() { new_window.isStillLoading = false; }, true);
            }
            break;
    }
}

viewManager.prototype.handle_current_view_changed = function(event) {
    // Update the currentView
    // This has to happen always since one can do ctrl+tab,ctrl+i, and that
    // needs to find the right view.
    this.currentView = event.originalTarget;

    if ("koDoc" in this.currentView) {
        var koDoc = this.currentView.koDoc;
        if (koDoc) {
            koDoc.setFileAccessed();
        }
    }

    if (this.batchMode) {
        // break out early -- we don't want to update controllers at this point.
        return;
    }
    if (this.topView.viewhistory.inBufferSwitchingSession) {
        // break out early -- we don't want to update controllers at this point.
        return;
    }

    this.updateCommands();
}

viewManager.prototype.updateCommands = function() {
    var oldcache = this.lastviewcache;
    var newcache = this.cacheCommandData(this.currentView);
    //for (var x in oldcache) {
    //    dump('oldcache['+ x +'] = ' + oldcache[x] + '\n');
    //}
    //for (var x in newcache) {
    //    dump('newcache['+ x +'] = ' + newcache[x] + '\n');
    //}
    this.currentView.updateCurrentLineColor();
    
    // Bug 83741 - ensure the scintilla focus is still correctly set,
    // sometimes the focus may have reset to another element by the time the
    // below timeout(s) are called, so we must reset it in that case,
    // otherwise the updateCommands will fail to find a Scintilla
    // controller, which means these Scintilla commands will not fail to get
    // updated/enabled.
    window.setTimeout(function() {
            var view = this.currentView;
            if (view && view.scintilla && !view.scintilla.isFocused) {
                window.document.commandDispatcher.focusedElement = view.scintilla;
            }
        }.bind(this), 1);
    
    window.setTimeout(window.updateCommands, 1, 'current_view_changed');
    var update_editor_change = (oldcache.type != newcache.type) &&
        (oldcache.type == 'editor' || newcache.type== 'editor');
    if (update_editor_change) {
        window.setTimeout(window.updateCommands, 1, 'currentview_is_editor');
    }
    window.setTimeout(window.updateCommands, 1, 'dirty');
    if (update_editor_change || oldcache.canUndo != newcache.canUndo ||
        oldcache.canRedo != newcache.canRedo) {
        window.setTimeout(window.updateCommands, 1, 'undo');
    }
    if (update_editor_change || oldcache.language != newcache.language) {
        window.setTimeout(window.updateCommands, 1, 'language_changed');
    }
    if (update_editor_change || oldcache.canFold != newcache.canFold) {
        window.setTimeout(window.updateCommands, 1, 'foldability_changed');
    }
    if (update_editor_change || oldcache.isLocal != newcache.isLocal) {
        window.setTimeout(window.updateCommands, 1, 'previewability_changed');
    }
    if (update_editor_change || oldcache.hasSelection != newcache.hasSelection) {
        window.setTimeout(window.updateCommands, 1, 'select');
    }
    this.lastviewcache = newcache;
}

viewManager.prototype.handle_view_closed = function() {
    // Don't trust _viewCount, it's probably bogus :(
    let viewCount = Array.slice(this.topView.getViews(true))
                         .filter(function(e) e.koDoc).length;
    this.log.info("_viewcount is " + viewCount);
    if (this._viewCount == viewCount) {
        // Duplicate notification
        this.log.warn("Inconsistent view count in view_closed event");
        return;
    }
    this._viewCount = viewCount;
    if (this._viewCount === 0) {
        this.log.info("sending event: 'some_files_open'");
        window.setTimeout(window.updateCommands, 1, 'some_files_open');
    } else if (this._viewCount == 1) {
        // We've closed our second view
        window.setTimeout(window.updateCommands, 1, 'second_view_open_close');
    }
    if (!ko.workspace.saveInProgress() && !ko.views.manager.batchMode &&
        !ko.main.windowIsClosing) {
        // Requires a timeout because the new document is not fully unloaded.
        window.setTimeout(ko.workspace.saveWorkspace, 1);
    }
};

viewManager.prototype.handle_view_opened = function() {
    this.log.info("got 'view opened' notification");
    // Don't trust _viewCount, it's probably bogus :(
    let viewCount = Array.slice(this.topView.getViews(true))
                         .filter(function(e) e.koDoc).length;
    this.log.info("_viewcount is " + viewCount);
    if (this._viewCount === viewCount) {
        // Duplicate notification
        this.log.warn("Inconsistent view count in view_opened event");
        return;
    }
    this._viewCount = viewCount;
    if (this._viewCount == 1) {
        this.log.info("sending event: 'some_files_open'");
        window.setTimeout(window.updateCommands, 1, 'some_files_open');
    } else if (this._viewCount == 2) {
        // We've opened our second view
        window.setTimeout(window.updateCommands, 1, 'second_view_open_close');
    }
    if (!ko.workspace.saveInProgress() && !ko.views.manager.batchMode &&
        !ko.main.windowIsClosing) {
        // Requires a timeout because the new document is not yet fully loaded.
        window.setTimeout(ko.workspace.saveWorkspace, 1);
    }
};

viewManager.prototype.is_cmd_bufferClose_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_bufferClose_enabled = function() {
    return this.currentView;
}

viewManager.prototype.do_cmd_bufferClose = function() {
    if (this.currentView) {
        this.currentView.close();
    }
}

viewManager.prototype.is_cmd_closeAll_supported = function() {
    this.log.info('is_cmd_closeAll_supported');
    return 1;
}

viewManager.prototype.is_cmd_closeAll_enabled = function() {
    this.log.info('is_cmd_closeAll_enabled' + String(this._viewCount != 0));
    return this._viewCount != 0;
}

viewManager.prototype.do_cmd_closeAll = function() {
    // Offer to close/save all dirty files first.
    var retval = this.canClose();
    if (retval) {
        // Now close all files, without offering to save each individual file,
        // bug 85489.
        this._doCloseViews(null /* all */, false, /* doNotOfferToSave */ true);
    }
    // Ensure the title bar is correctly set - bug 91958.
    ko.uilayout.updateTitlebar(this.currentView);
}

/**
 * Close the list of views provided.
 * @param {koIView} views - Views to close - when no views are provided, then
 *                          the list of all views will be used.
 * @param {boolean} ignoreFailures - ignore any failures when closing files
 * @param {boolean} doNotOfferToSave - whether to offer to save dirty files
 */
viewManager.prototype._doCloseViews = function(views, ignoreFailures, doNotOfferToSave) {
    if (!views) views = this.topView.getDocumentViews(true);
    if (typeof(ignoreFailures) == "undefined") ignoreFailures = false;
    if (typeof(doNotOfferToSave) == "undefined") doNotOfferToSave = false;
    // returns true if all views were closed.
    var i;
    // Uses batch mode to avoid perf hit from resetting the current view, see
    // bug 85290.
    ko.views.manager.batchMode = true;
    try {
        for (i = views.length-1; i >= 0; i--) {
            if (i == 0 && !this._shuttingDown) {
                // Ensure the last file closure causes currentView changed
                // notifications, to update the Komodo window title.
                ko.views.manager.batchMode = false;
            }
            if (! views[i].close(doNotOfferToSave) && !ignoreFailures) {
                return false;
            }
        }
    } finally {
        ko.views.manager.batchMode = false;
    }
    return true;
}

viewManager.prototype.is_cmd_bufferCloseOthers_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_bufferCloseOthers_enabled = function() {
    return this._viewCount > 1;
}

viewManager.prototype.do_cmd_bufferCloseOthers = function() {
    // Offer to close/save any "other" dirty files first.
    var currView = ko.views.manager.currentView;
    var views = this.topView.getViews(true);
    // Get the other editor views.
    var view, filtered_views = [], urls = [];
    for (var i = 0; i < views.length; i++) {
        view = views[i];
        var viewType = view.getAttribute("type");
        if (view == currView) {
            continue;
        } else if (viewType == "browser") {
            filtered_views.push(view);
        } else if (view.getAttribute("type") != "editor" || !view.koDoc) {
            continue;
        } else if (view.koDoc.isUntitled) {
            if (view.isDirty) {
                var res = ko.dialogs.yesNoCancel("Save changes to " + view.koDoc.baseName +
                                                "?");
                if (res == "Cancel") {
                    return;
                } else if (res == "Yes" && ! this.saveAs()) {
                    return;
                }
                view.close(true);
            } else {
                view.close();
            }
        } else {
            filtered_views.push(view);
            urls.push(view.koDoc.file.URI);
        }
    }
    var retval = this.offerToSave(urls);
    if (retval === false) {
        // User cancelled the operation.
        return;
    }
    // Now close the "other" files, the offering to save is already done.
    this._doCloseViews(filtered_views, false /* ignoreFailures */,
                       true /* doNotOfferToSave */);
}

viewManager.prototype.is_cmd_cleanLineEndings_supported = function() {
    this.log.info('is_cmd_cleanLineEndings_supported');
    return 1;
}

viewManager.prototype.is_cmd_cleanLineEndings_enabled = function() {
    var currView = ko.views.manager.currentView;
    return (currView && currView.getAttribute("type") == "editor" &&
            currView.koDoc);
}

viewManager.prototype.do_cmd_cleanLineEndings = function() {
    var currView = ko.views.manager.currentView;
    if (currView && currView.getAttribute("type") == "editor" && currView.koDoc) {
        currView.koDoc.cleanLineEndings();
    }
}

function _elementInArray(element, array)
{
    for (var i = 0; i < array.length; i++) {
        if (array[i] == element) {
            return true;
        }
    }
    return false;
}

viewManager.prototype.offerToSave = function(urls, /* default is null meaning all dirty files */
                                             title, /* default is "Save modified files?" */
                                             prompt, /* default is "Please select the files you wish to save:" */
                                             doNotAskPref, /* default is null */
                                             skipProjects, /* default is false */
                                             aboutToClose /* default is true */
                                             ) {
    // This function offers to save the subset of 'urls' which correspond to dirty
    // files, whether corresponding to views, project files, or GUI dialogs.
    //
    // If 'urls' is null or unspecified, then it offers to save all dirty documents.
    //
    // This function returns false if the user cancels the operation, false otherwise.
    //
    // the 'doNotAskPref' can be used to let the user skip the dialog.  use carefully!
    //
    // If 'skipProjects' is true, then projects aren't considered
    //
    // Note that offerToSave needs to save all views that need saving, but actually close
    // none of them, in case another canclose handler cancels the close operation
    //
    // Note that this function is used in many places throughout the chrome.
    // Sometimes this is called when files are about to be closed, but not
    // always -- the actions this function takes are different for the two.

    if (typeof(urls) == 'undefined') {
        urls = null;
    }
    if (typeof(title) == 'undefined' || title == null) {
        title = locals.bundle.GetStringFromName("saveModifiedFiles.prompt");
    }
    if (typeof(prompt) == 'undefined' || prompt == null) {
        title = locals.bundle.GetStringFromName("pleaseSelectTheFilesYouWishToSave.prompt");
    }
    if (typeof(doNotAskPref) == 'undefined') {
        doNotAskPref = null;
    }
    if (typeof(skipProjects) == 'undefined' || skipProjects == null) {
        skipProjects = false;
    }
    if (typeof(aboutToClose) == 'undefined' || aboutToClose == null) {
        aboutToClose = true;
    }

    if (!this.topView) {
        // Most likely we're shutting down and there are no dirty views
        return true;
    }
    var views = this.topView.getViews(true);
    var i, view, item, k;
    var dirtyItems = [];
    var sofar = {};
    for (i = 0; i < views.length; i++) {
        view = views[i];
        if (!view) continue;
        // Persist view state now, to not have to do it as part of onunload handling
        if (aboutToClose && view.getAttribute('type') == 'editor') {
            try {
                view.saveState();
                if (ko.macros.eventHandler.hookPreFileClose(view)) {
                    var msg = locals.bundle.GetStringFromName("macroInterruptedFileClosingProcedure.message");
                    require("notify/notify").send(msg, "editor", {priority: "warning"});
                    return false;
                }
            } catch (e) {
                this.log.error(e);
            }
        }
        if (typeof(view.isDirty) != 'undefined' && view.isDirty) {
            if (urls != null) {
                // Exclude the view if it's not in the urls list
                // There is no way that untitled documents could be in the list
                if (view.koDoc.isUntitled) continue;
                // exclude if it's not in the list
                if (! _elementInArray(view.koDoc.file.URI, urls)) {
                    continue;
                }
            }
            if (aboutToClose
                && !view.koDoc.isUntitled
                && ko.windowManager.otherWindowHasViewForURI(view.koDoc.file.URI)) {
                // Untitled documents can't be in other windows.
                continue;
            }
            // We need to deal with views that are split and that share a document
            // So we keep track of the displayPaths, and only add a view
            // if it's display path isn't already in our list.
            if (view.koDoc.displayPath in sofar) continue;
            sofar[view.koDoc.displayPath] = true;
            item = new Object();
            item.type = 'view';
            item.view = view;
            dirtyItems.push(item);
        }
    }
    if (!skipProjects) {
        var dirtyProjects = ko.projects.manager.getDirtyProjects();
        for (var i = dirtyProjects.length - 1; i >= 0; i--) {
            var proj = dirtyProjects[i];
            if (!proj.isDirty) {
                // quietly save isPrefDirty projects
                try {
                    ko.projects.manager.saveProject(proj);
                } catch(ex) {
                    this.log.error("Failed to save project " + proj.name + ":" + ex);
                }
                dirtyProjects.splice(i, 1);
            }
        }
        for (i = 0; i < dirtyProjects.length; i++) {
            if (urls != null && ! _elementInArray(dirtyProjects[i].url, urls)) continue;
            item = new Object();
            item.type = 'project';
            item.URL = dirtyProjects[i].url;
            item.project = dirtyProjects[i];
            dirtyItems.push(item);
        }
    }

    if (dirtyItems.length == 0) return true; // nothing to save
    function stringifier(item) {
        if (item.type == 'view') {
            return item.view.koDoc.displayPath;
        } else {
            return ko.uriparse.displayPath(item.URL);
        }
    }
    var itemsToSave = ko.dialogs.selectFromList(title,
                                            prompt,
                          dirtyItems,
                          "zero-or-more",
                          stringifier,
                          doNotAskPref,
                          true /* yesNoCancel */,
                          [locals.bundle.GetStringFromName("save.prompt"),
                           locals.bundle.GetStringFromName("doNotSave.prompt"),
                           locals.bundle.GetStringFromName("cancel.prompt")]);
    if (itemsToSave == null) {
        return false; // canceled
    }
    for (i = 0; i < itemsToSave.length; i++) {
        item = itemsToSave[i];
        if (item.type == 'view') {
            if (item.view.save() == false) {
                // the user hit cancel
                return false;
            }
        } else if (item.type == 'project') {
            if (ko.projects.manager.saveProject(item.project) == false) {
                // the user hit cancel
                return false;
            }
        } else {
            this.log.error("Unknown item type in canClose handler");
        }
    }

    if (dirtyItems.length == 0) return true; // nothing to save
    // we return the dirtyItems array here.  this will evaluate to true
    // for those area's we expect a truth value.  For canClose, this
    // allows us to remove the autosave files for the dirty items that
    // were chosen not to be saved, which we only want to do from
    // canClose.
    return dirtyItems;
}

/**
 * revert files to the version saved on disk
 * 
 * @public
 * @param {array} urls list of files to revert
 */
viewManager.prototype.revertViewsByURL = function(urls) {
    var i, j, view, views;
    for (i = 0; i < urls.length; i++) {
        views = this.topView.findViewsForURI(urls[i]);
        for (j = 0; j < views.length; j++) {
            view = views[j];
            view.revertUnconditionally();
        }
    }
}

/**
 * close a set of files
 * 
 * @public
 * @param {array} urls list of files to close
 */
viewManager.prototype.closeViewsByURL = function(urls) {
    var i, j, view, views;
    for (i = 0; i < urls.length; i++) {
        views = this.topView.findViewsForURI(urls[i]);
        for (j = 0; j < views.length; j++) {
            view = views[j];
            view.close();
        }
    }
}

// cmd_triggerPrecedingCompletion (AutoComplete/CallTip initiation)

viewManager.prototype.is_cmd_triggerPrecedingCompletion_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_triggerPrecedingCompletion_enabled = function() {
    var view = ko.views.manager.currentView;
    var retval = (view != null
                  && typeof(view.ciCompletionUIHandler) != "undefined"
                  && view.ciCompletionUIHandler != null);
    return retval;
}

viewManager.prototype.do_cmd_triggerPrecedingCompletion = function() {
    var view = ko.views.manager.currentView;
    if (view && view.ciCompletionUIHandler) {
        view.ciCompletionUIHandler.triggerPrecedingCompletion();
    }
}


// cmd_viewAsLanguage

viewManager.prototype.is_cmd_viewAsLanguage_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_viewAsLanguage_enabled = function() {
    var currView = ko.views.manager.currentView;
    if (currView && currView.getAttribute("type") == "editor") {
        return true;
    } else {
        return false;
    }
}

// cmd_viewAsGuessedLanguage

viewManager.prototype.is_cmd_viewAsGuessedLanguage_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_viewAsGuessedLanguage_enabled = function() {
    return (this.currentView && this.currentView.getAttribute("type") == "editor");
}

viewManager.prototype.do_cmd_viewAsGuessedLanguage = function() {
    if (this.currentView && this.currentView.getAttribute("type") == "editor") {
        ko.views.manager.do_ViewAs('');
    }
}

// cmd_gotoLine

viewManager.prototype.is_cmd_gotoLine_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_gotoLine_enabled = function() {
    var currView = ko.views.manager.currentView;
    if (currView && currView.getAttribute("type") == "editor") {
        return true;
    } else {
        return false;
    }
}

viewManager.prototype.do_cmd_gotoLine = function() {
    // Clear any existing line information.
    var gotoLineTextbox = document.getElementById('gotoLine_textbox');
    gotoLineTextbox.value = "";
    // Get the current scintilla position.
    var currentView = ko.views.manager.currentView;
    /** @type {Components.interfaces.ISciMoz} */
    var scimoz = currentView.scimoz;
    var middleLine = scimoz.firstVisibleLine + (scimoz.linesOnScreen / 2) - 5;
    var pos = scimoz.positionFromLine(middleLine);
    var x = scimoz.pointXFromPosition(pos);
    var y = scimoz.pointYFromPosition(pos);
    // Show the goto line panel/popup.
    var panel = document.getElementById("gotoLine_panel");
    panel.openPopup(ko.views.manager.currentView, "after_pointer", x, y);
}

// cmd_goToDefinition
viewManager.prototype.is_cmd_goToDefinition_enabled = function() {
    if (!ko.codeintel.isActive) return false;
    var view = ko.views.manager.currentView;
    return (view && view.scimoz && view.koDoc &&
            view.isCICitadelStuffEnabled);
}

// attributes
// doc
// file
// ilk  - function, scope, class...
// line
// name
// signature
viewManager.prototype.do_cmd_goToDefinition = function() {
    // Get citdl defn trigger from where the cursor is located
    var view = ko.views.manager.currentView;
    var pos = view.scimoz.currentPos;
    var ciBuf = view.koDoc.ciBuf;
    ko.codeintel.linkCurrentProjectWithBuffer(ciBuf);
    ciBuf.defn_trg_from_pos(pos, function (trg) {
        if (!trg) {
            return;
        }
        if (!view.isCICplnEnabled) {
            // completion is not available for this view; we can't do go to
            // definition. (As a side effect of checking this, we might create
            // the completion ui handler.)
            ko.statusBar
              .AddMessage("Go to definition not available for this file",
                          "codeintel", 4000, true, true, true);
            return;
        }
        // We mostly want to use the normal UI handler, except that we override
        // setDefinitionsInfo to do nothing if the user has moved on (i.e. when
        // go to definition was too slow).
        var handler = Object.create(view.ciCompletionUIHandler, {
            setDefinitionsInfo: {
                writable: true,
                configurable: true,
                value: function (count, defns, trg) {
                    if (ko.views.manager.currentView !== view) {
                        return; // view changed, the user has moved on
                    }
                    if (view.scimoz.currentPos !== pos) {
                        return; // The user has moved on
                    }
                    view.ciCompletionUIHandler
                        .setDefinitionsInfo(count, defns, trg);
                }
            },
        });
        ciBuf.async_eval_at_trg(trg, handler);
    }, ko.codeintel.handleError);
}

// cmd_save
viewManager.prototype.is_cmd_save_supported = function() {
    return this.currentView != null && typeof(this.currentView.save) != 'undefined';
}

viewManager.prototype.is_cmd_save_enabled = function() {
    return this.currentView && this.currentView.koDoc && this.currentView.koDoc.isDirty;
}


viewManager.prototype.do_cmd_save = function() {
    this.currentView.save();
}


// cmd_revert
viewManager.prototype.is_cmd_revert_supported = function() {
    return this.currentView != null && typeof(this.currentView.revert) != 'undefined';
}

viewManager.prototype.is_cmd_revert_enabled = function() {
    let view = this.currentView;
    return view && view.koDoc && (view.koDoc.isDirty ||
                                  // Always enable it for remote files.
                                  (view.koDoc.file && view.koDoc.file.isRemoteFile));
}


viewManager.prototype.do_cmd_revert = function() {
    this.currentView.revert();
}

// cmd_saveAll
viewManager.prototype.is_cmd_saveAll_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_saveAll_enabled = function() {
    return true;
}

viewManager.prototype.do_cmd_saveAll = function() {
    try {
        var views = this.topView.getDocumentViews(true);
        var i, view;
        this.log.info("length of views is: " + views.length);
        for (i = views.length-1; i >= 0; i--) {
            view = views[i];
            if (view.save && view.koDoc.isDirty) {
                view.save(); // we'll ignore return values here.
            }
        }

        // Save all dirty projects
        var projects = ko.projects.manager.getDirtyProjects();
        for (i = 0; i < projects.length; i++) {
            ko.projects.manager.saveProject(projects[i]);
        }

        // save workspace
        ko.workspace.saveWorkspace(true);
    } catch(ex) {
        this.log.exception(ex, "Error in do_cmd_saveAll");
    }
}


// cmd_saveAs
viewManager.prototype.is_cmd_saveAs_supported = function() {
    return this.currentView != null && typeof(this.currentView.saveAs) != 'undefined';
}

viewManager.prototype.is_cmd_saveAs_enabled = function() {
    return (this.currentView && this.currentView.koDoc &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_saveAs = function() {
    this.currentView.saveAs();
}

// cmd_saveAs_remote
viewManager.prototype.is_cmd_saveAs_remote_supported = function() {
    return this.currentView != null && typeof(this.currentView.saveAsRemote) != 'undefined';
}

viewManager.prototype.is_cmd_saveAs_remote_enabled = function() {
    return (this.currentView && this.currentView.koDoc &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_saveAs_remote = function() {
    this.currentView.saveAsRemote();
}

// cmd_open_remote
viewManager.prototype.do_cmd_open_remote = function() {
    if (this.currentView && this.currentView.koDoc &&
        this.currentView.getAttribute('type') == 'editor') {
        // Open with specific location of current file if possible
        this.currentView.openRemote();
    } else {
        // Open with the default location
        ko.filepicker.openRemoteFiles();
    }
}


// cmd_buffer[1-9] -- switch to the given tab index
viewManager.prototype.is_cmd_buffer1_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer1_enabled = function() { return this._viewCount >= 1; }
viewManager.prototype.do_cmd_buffer1 = function() { return this.topView.setCurrentViewIndex(1-1); }
viewManager.prototype.is_cmd_buffer2_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer2_enabled = function() { return this._viewCount >= 2; }
viewManager.prototype.do_cmd_buffer2 = function() { return this.topView.setCurrentViewIndex(2-1); }
viewManager.prototype.is_cmd_buffer3_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer3_enabled = function() { return this._viewCount >= 3; }
viewManager.prototype.do_cmd_buffer3 = function() { return this.topView.setCurrentViewIndex(3-1); }
viewManager.prototype.is_cmd_buffer4_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer4_enabled = function() { return this._viewCount >= 4; }
viewManager.prototype.do_cmd_buffer4 = function() { return this.topView.setCurrentViewIndex(4-1); }
viewManager.prototype.is_cmd_buffer5_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer5_enabled = function() { return this._viewCount >= 5; }
viewManager.prototype.do_cmd_buffer5 = function() { return this.topView.setCurrentViewIndex(5-1); }
viewManager.prototype.is_cmd_buffer6_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer6_enabled = function() { return this._viewCount >= 6; }
viewManager.prototype.do_cmd_buffer6 = function() { return this.topView.setCurrentViewIndex(6-1); }
viewManager.prototype.is_cmd_buffer7_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer7_enabled = function() { return this._viewCount >= 7; }
viewManager.prototype.do_cmd_buffer7 = function() { return this.topView.setCurrentViewIndex(7-1); }
viewManager.prototype.is_cmd_buffer8_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer8_enabled = function() { return this._viewCount >= 8; }
viewManager.prototype.do_cmd_buffer8 = function() { return this.topView.setCurrentViewIndex(8-1); }
viewManager.prototype.is_cmd_buffer9_supported = function() { return true; }
viewManager.prototype.is_cmd_buffer9_enabled = function() { return this._viewCount >= 9; }
viewManager.prototype.do_cmd_buffer9 = function() { return this.topView.setCurrentViewIndex(9-1); }

// cmd_bufferNext
viewManager.prototype.is_cmd_bufferNext_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_bufferNext_enabled = function() {
    return this._viewCount > 1;
}

viewManager.prototype.do_cmd_bufferNext = function() {
    this.topView.makeNextViewCurrent();
}

// cmd_bufferPrevious
viewManager.prototype.is_cmd_bufferPrevious_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_bufferPrevious_enabled = function() {
    return this._viewCount > 1;
}

viewManager.prototype.do_cmd_bufferPrevious = function() {
    this.topView.makePreviousViewCurrent();
}

// cmd_bufferNextMostRecent
viewManager.prototype.is_cmd_bufferNextMostRecent_enabled = function() {
    return this._viewCount > 1;
}

viewManager.prototype.do_cmd_bufferNextMostRecent = function() {
    this.topView.viewhistory.doNextMostRecentView(this.currentView);
}

viewManager.prototype.is_cmd_bufferNextLeastRecent_enabled = function() {
    return this._viewCount > 1;
}

// cmd_bufferLeastMostRecent
viewManager.prototype.do_cmd_bufferNextLeastRecent = function() {
    this.topView.viewhistory.doNextLeastRecentView(this.currentView);
}

// cmd_splittab
viewManager.prototype.is_cmd_splittab_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_splittab_enabled = function() {
    return this._viewCount >= 1;
}

viewManager.prototype.do_cmd_splittab = function() {
    this.topView.splitView(this.currentView);
}

// cmd_movetab
viewManager.prototype.is_cmd_movetab_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_movetab_enabled = function() {
    return this._viewCount >= 1;
}

viewManager.prototype.do_cmd_movetab = function() {
    this.topView.moveView(this.currentView);
}

// cmd_openTabInNewWindow
viewManager.prototype.is_cmd_openTabInNewWindow_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_openTabInNewWindow_enabled = function() {
    return (this.currentView
            // When quitting, commands in command sets observing the "dirty"
            // command update get called. For some reason, the methods on
            // the view aren't there at this point (XBL binding destruction?).
            && "canBeOpenedInAnotherWindow" in this.currentView
            && this.currentView.canBeOpenedInAnotherWindow());
}

viewManager.prototype.do_cmd_openTabInNewWindow = function() {
    ko.launch.newWindow(this.currentView.koDoc.file.URI);
}

// cmd_moveTabToNewWindow
viewManager.prototype.is_cmd_moveTabToNewWindow_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_moveTabToNewWindow_enabled = function() {
    return (this.currentView
            // When quitting, commands in command sets observing the "dirty"
            // command update get called. For some reason, the methods on
            // the view aren't there at this point (XBL binding destruction?).
            && "canBeOpenedInAnotherWindow" in this.currentView
            && this.currentView.canBeOpenedInAnotherWindow());
}

viewManager.prototype.do_cmd_moveTabToNewWindow = function() {
    // Close the tab first, because if it's dirty and we try
    // copying it to the new window first, the changes will get lost.
    // Not sure why.
    var uri = this.currentView.koDoc.file.URI;
    if (!this.currentView.close()) {
        return;
    }
    ko.launch.newWindow(uri);
}

// cmd_togglePanels

viewManager.prototype.is_cmd_togglePanels_supported = function() {
    return true;
};
viewManager.prototype.is_cmd_togglePanels_enabled =
    viewManager.prototype.is_cmd_togglePanels_supported;
viewManager.prototype.do_cmd_togglePanels = function() {
    // If any are visible hide all
    // If all are hidden show all.
    var panels = ["workspace_left_area",
                  "workspace_bottom_area",
                  "workspace_right_area" ].map(
        function(pname) document.getElementById(pname)
    );
    var anyVisible = panels.some(function(p) !p.collapsed);
    panels.forEach(function(p) p.collapsed = anyVisible);
};

// cmd_rotateSplitter
viewManager.prototype.is_cmd_rotateSplitter_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_rotateSplitter_enabled = function() {
    var othertabbox = document.getElementById('view-2');
    return (!othertabbox.hasAttribute('collapsed') ||
            othertabbox.getAttribute('collapsed') == 'false');
}

viewManager.prototype.do_cmd_rotateSplitter = function() {
    try {
        this.topView.changeOrient();
    } catch (e) {
        this.log.exception(e);
    }
}


viewManager.prototype.is_cmd_switchpane_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_switchpane_enabled = function() {
    return ko.views.manager.topView.otherView;
}

viewManager.prototype.do_cmd_switchpane = function() {
    try {
        ko.views.manager.topView.otherView.currentView.makeCurrent();
    } catch (e) {
        this.log.exception(e);
    }
}

// cmd_cancel
viewManager.prototype.is_cmd_cancel_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_cancel_enabled = function() {
    return this.currentView && this.currentView.getAttribute('type') == 'editor';
}

viewManager.prototype.do_cmd_cancel = function() {
    if (!this.currentView || this.currentView.getAttribute('type') != 'editor') {
        return;
    }
    var view = this.currentView;
    var sm = view.scimoz
    if (sm.callTipActive()) {
        sm.callTipCancel()
    } else if (sm.autoCActive()) {
        sm.autoCCancel()
    } else {
        ko.find.highlightClearAll(sm);
        view.removeHyperlinks("cmd_cancel");
        let currentPos = sm.currentPos;
        const DECORATOR_SOFT_CHAR = Components.interfaces.koILintResult.DECORATOR_SOFT_CHAR;
        let softPositionEnd = sm.indicatorEnd(DECORATOR_SOFT_CHAR, currentPos);
        if (softPositionEnd > currentPos) {
            sm.indicatorCurrent = DECORATOR_SOFT_CHAR;
            sm.indicatorClearRange(currentPos, softPositionEnd - currentPos);
        }
        if (ko.tabstops) {
            ko.tabstops.clearTabstopInfo(view);
        }
        view.clearMatchingTag(view);
    }
}

viewManager.prototype.is_cmd_print_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_print_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_print = function() {
    require("ko/printing").print(this.currentView, 0, 0);
}

viewManager.prototype.is_cmd_printSelection_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_printSelection_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor' &&
            this.currentView.selection);
}

viewManager.prototype.do_cmd_printSelection = function() {
    require("ko/printing").print(this.currentView, false, false, true);
}

viewManager.prototype.is_cmd_printPreview_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_printPreview_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_printPreview = function() {
    require("ko/printing").printPreview(this.currentView, 1, 0);
}

viewManager.prototype.is_cmd_printPreviewSelection_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_printPreviewSelection_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor' &&
            this.currentView.selection);
}

viewManager.prototype.do_cmd_printPreviewSelection = function() {
    require("ko/printing").printPreview(this.currentView, 1, 0, 1);
}

viewManager.prototype.is_cmd_exportHTML_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_exportHTML_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_exportHTML = function() {
    require("ko/printing").print(this.currentView, 0, 1);
}


viewManager.prototype.is_cmd_exportHTMLSelection_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_exportHTMLSelection_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor' &&
            this.currentView.selection);
}

viewManager.prototype.do_cmd_exportHTMLSelection = function() {
    require("ko/printing").print(this.currentView, false, true, true);
}

viewManager.prototype.do_ViewAs = function(language) {
    var scimoz = this.currentView.scimoz;
    var firstVisibleLine = -1;
    if (scimoz) {
        firstVisibleLine = scimoz.firstVisibleLine;
    }
    var view = this.currentView;
    view.koDoc.docSettingsMgr.applyViewSettingsToDocument(view);
    view.koDoc.language = language;
    if (firstVisibleLine != -1 && !!(scimoz = view.scimoz)) {
        // For some reason the settings mgr doesn't fix the scroll
        var newFirstVisibleLine = scimoz.firstVisibleLine;
        if (newFirstVisibleLine != firstVisibleLine) {
            scimoz.lineScroll(0, firstVisibleLine - newFirstVisibleLine);
        }
    }
    // koDocumentBase.set_language sends a language_changed notification,
    // but it doesn't update the commands.
    window.setTimeout(window.updateCommands, 1, 'language_changed');
}

viewManager.prototype.is_cmd_editPrefsCurrent_enabled = function () {
    return this.currentView && this.currentView.getAttribute('type') == 'editor';
}
viewManager.prototype.do_cmd_editPrefsCurrent = function () {
    ko.projects.fileProperties(null, this.currentView, false);
}

viewManager.prototype.is_cmd_createMappedURI_enabled = function () { 
    return this.currentView && this.currentView.getAttribute('type') == 'editor' &&
        this.currentView.koDoc && this.currentView.koDoc.file;
}
viewManager.prototype.do_cmd_createMappedURI = function () {
    if (this.currentView.koDoc.file.isLocal) {
        ko.uriparse.addMappedURI(null, this.currentView.koDoc.file.path);
    } else {
        var uri = this.currentView.koDoc.file.URI;
        ko.uriparse.addMappedURI(uri, null);
    }
}
viewManager.prototype.is_cmd_saveAsTemplate_enabled = function () {
    return this.currentView && this.currentView.getAttribute('type') == 'editor';
}
viewManager.prototype.do_cmd_saveAsTemplate = function () {
    try {
        var templateSvc = Components.classes["@activestate.com/koTemplateService?type=file;1"].getService();
        //TODO: The directory name "My Templates" should be localized
        var dname = Services.koOs.path.join(templateSvc.getUserTemplatesDir(), "My Templates");
        var templatename = ko.filepicker.saveFile(dname,
                                this.currentView.koDoc.baseName);
        if (!templatename) return;
        var doc = Services.koDocSvc.createDocumentFromURI(ko.uriparse.localPathToURI(templatename));
        doc.buffer = this.currentView.koDoc.buffer;
        doc.encoding = this.currentView.koDoc.encoding;
        doc.save(0);
    } catch(ex) {
        this.log.exception(ex, "Error saving the current view as a template.");
    }
}

// cmd_fontZoomReset
viewManager.prototype.is_cmd_fontZoomReset_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_fontZoomReset_enabled = function() {
    return this.currentView && this.currentView.getAttribute('type') == 'editor';
}

viewManager.prototype.do_cmd_fontZoomReset = function() {
    if (this.currentView && this.currentView.getAttribute('type') == 'editor') {
        this.currentView.scimoz.zoom = 0;
    }
}

// cmd_reloadBrowserPreview - works on either a browser view, or a document
// which has a linked browser view.
viewManager.prototype.is_cmd_reloadBrowserPreview_enabled = function() {
    return this.currentView && (this.currentView.getAttribute('type') == 'browser' ||
                                (this.currentView.getAttribute('type') == 'editor' &&
                                 this.currentView.preview));
}

viewManager.prototype.do_cmd_reloadBrowserPreview = function() {
    if (!this.currentView)
        return;
    if (this.currentView.getAttribute('type') == 'browser') {
        this.currentView.reload();
    } else if (this.currentView.getAttribute('type') == 'editor') {
        if (this.currentView.preview) {
            this.currentView.preview.reload();
        }
    }
}

viewManager.prototype.is_cmd_showHideMinimap_enabled = function () {
    var menuitem = document.getElementById("menu_showHideMinimap");
    var inEditorView = (this.currentView
                        && this.currentView.getAttribute('type') == 'editor');
    if (!inEditorView) {
        menuitem.disabled = true;
        return false;
    } else {
        if (this.currentView.minimap) {
            menuitem.setAttribute("checked", "true");
        } else {
            menuitem.removeAttribute("checked");
        }
        menuitem.disabled = false;
        return true;
    }
};

viewManager.prototype.do_cmd_showHideMinimap = function () {
    var view = this.currentView;
    if (!view) {
        return;
    }
    view.prefs.setBooleanPref("editShowMinimap",
                              !view.prefs.getBoolean("editShowMinimap", false));
};

viewManager.prototype.is_cmd_minimap_fontZoom_enabled = function () {
    // As long as we have an editor/view, mark all minimap menu items enabled.
    var view = this.currentView;
    return view && "minimap" in view && view.minimap;
};
viewManager.prototype.is_cmd_minimap_fontZoomIn_enabled = function () {
    return this.is_cmd_minimap_fontZoom_enabled();
};
viewManager.prototype.is_cmd_minimap_fontZoomOut_enabled = function () {
    return this.is_cmd_minimap_fontZoom_enabled();
};
viewManager.prototype.is_cmd_minimap_fontZoomReset_enabled = function () {
    return this.is_cmd_minimap_fontZoom_enabled();
};
viewManager.prototype.is_cmd_minimap_hide_enabled = function () {
    return this.is_cmd_minimap_fontZoom_enabled();
};

// Minimap setting:
// -8 is the lowest possible zoom. Lower values are accepted, but
// have no effect, and make it look like ctrl-scroll doesn't work.
// Ref bug 97447
viewManager.prototype.DEFAULT_MINIMAP_ZOOM = -8;

viewManager.prototype._do_cmd_minimap_fontZoom = function(arg) {
    var minimap, view = this.currentView;
    if (!view || !(minimap = view.minimap)) {
        return;
    }
    minimap.scimoz.zoom += arg;
};
viewManager.prototype.do_cmd_minimap_fontZoomIn = function () {
    this._do_cmd_minimap_fontZoom(1);
};
viewManager.prototype.do_cmd_minimap_fontZoomOut = function () {
    this._do_cmd_minimap_fontZoom(-1);
};
viewManager.prototype.do_cmd_minimap_fontZoomReset = function () {
    var minimap, view = this.currentView;
    if (!view || !(minimap = view.minimap)) {
        return;
    }
    minimap.scimoz.zoom = this.DEFAULT_MINIMAP_ZOOM;
};
viewManager.prototype.do_cmd_minimap_hide = function () {
    var view = this.currentView;
    if (view) {
        view.prefs.setBooleanPref("editShowMinimap", false);
        document.getElementById("menu_showHideMinimap").removeAttribute("checked");
    }
};

viewManager.prototype.notify_visited_directory = function(path) {
    var event = new CustomEvent("visit_directory_proposed",
                                {bubbles: true, "detail": { "visitedPath": path }});
    window.dispatchEvent(event);
}

this.viewManager = viewManager;

var _manager = null;
var _gCheckFilesObserver = null;

/**
 * Get the view manager.
 * @type ko.views.viewManager
 *
 */
XPCOMUtils.defineLazyGetter(this, "manager",
function()
{
    _manager = new viewManager();
    Services.koViewSvc.setViewMgr(_manager);

// #if PLATFORM == "linux"
    if (window == ko.windowManager.getMainWindow())
        window.addEventListener("focus", ko.window.checkDiskFiles, false);
// #else
    function _checkFilesObserver() {
        Services.obs.addObserver(this, "application-activated",false);

        var me = this;
        this.removeListener = function() { me.finalize(); }
        window.addEventListener("unload", this.removeListener, false);
    };
    _checkFilesObserver.prototype = {
        finalize: function() {
            if (!this.removeListener) return;
            window.removeEventListener("unload", this.removeListener, false);
            this.removeListener = null;
            Services.obs.removeObserver(this, "application-activated");
        },
        observe: function(subject, topic, data)
        {
            if (topic == 'application-activated'){
                var activated = subject.QueryInterface(Components.interfaces.nsISupportsPRBool).data;
                if (activated) {
                    ko.window.checkDiskFiles();
// #if PLATFORM == "win"
                    // Ensure the Komodo focus is set correctly - bug 86766.
                    var focusedElement = document.commandDispatcher.focusedElement;
                    if (focusedElement &&
                        focusedElement.localName == "embed" &&
                        focusedElement.parentNode.localName == "scintilla") {
                        // Should not be focused on the embed element, should
                        // always be focused on the Scintilla element.
                        ko.views.manager.log.warn("The focus is on the embed element - changing it to scintilla");
                        document.getBindingParent(focusedElement).focus();
                    }
// #endif
                }
            }
        }
    }
    _gCheckFilesObserver = new _checkFilesObserver();
// #endif
    return _manager;
});
this.onload = function views_onload() {
    // force trigger the lazy getter if it hasn't happened yet
    this.manager;
};

/* convert an offset in character coordinates to an offset in
 * scintilla coordinates.  The reason we need this function is due to
 * a leaky abstraction in scimoz wrt multi-byte characters.
 * This function will be redundant, but continue to function correctly, if we
 * move to a UCS2-based scintilla component.
 * @param {Object} scimoz - scimoz object
 * @param {Number} pos - a valid scintilla position
 * @param {Number} delta - the number of characters to move, may be negative
 * @returns {Number} the equivalent position in scintilla coordinates to use
 *     for scimoz calls that refer to the character position pos+delta
 */
this.ScimozOffsetFromUCS2Offset = function ScimozOffsetFromUCS2Offset(scimoz, pos, delta) {
    var count;
    if (delta < 0) {
        count = -1 * delta;
        while (count > 0 && pos > 0) {
            pos = scimoz.positionBefore(pos);
            count -= 1;
        }
    } else {
        count = delta;
        var lim = scimoz.textLength;
        while (count > 0 && pos < scimoz.textLength) {
            pos = scimoz.positionAfter(pos);
            count -= 1;
        }
    }
    return pos;
}

this.nullOnModifiedHandler = function() {
    // See views-buffer.xml:onModified
    return true;
}

// Functions that modify the buffer should be wrapped to avoid
// triggering re-entrant calls.

this.wrapScintillaChange = function(view, func) {
    view.addModifiedHandler(this.nullOnModifiedHandler, this, 0);
    try {
        func();
    } finally {
        view.removeModifiedHandler(this.nullOnModifiedHandler);
    }
};


/**
 * Shared code that returns a label and tooltip based on the supplied view,
 * suitable for a menuitem.  
 * @param {Object(koIScintillaView)} view
 * @param {Number} lineNo - one-based line number
 * @param {Boolean} showDirty - put a "*" in the label if the view's document is dirty
 * @param {String} sectionTitle - optional string that describes a location.
 * @returns {Array} returns two values: the label and a suggested tooltip.
 *             If no label can be calculated, both items are null.
 */
this.labelsFromView = function(view,
                               lineNo, /*=null*/
                               showDirty, /* false */
                               sectionTitle /*=null*/
                               ) {
    if (typeof(lineNo) == "undefined") {
        lineNo = null;
    }
    if (typeof(showDirty) == "undefined") {
        showDirty = false;
    }
    if (typeof(sectionTitle) == "undefined") {
        sectionTitle = null;
    }
    var label = null, tooltip = null;
    if (view.koDoc) {
        // Example:
        //  "C:\trentm\tmp\foo.py" -> "foo.py (C:\trentm\tmp)"
        var doc = view.koDoc;
        var path = tooltip = doc.displayPath;
        var idx = path.lastIndexOf("/");
        if (idx == -1) {
            idx = path.lastIndexOf("\\");
        }
        var baseName, dirName = null;
        var label;
        if (idx != -1) {
            dirName = path.substring(0, idx);
            baseName = path.substring(idx+1);  // basename
        } else {
            baseName = path;
        }
        label = this.labelFromPathInfo(baseName, dirName, lineNo,
                                       null, // tab id
                                       null, // view type
                                       sectionTitle,
                                       showDirty && doc.isDirty);
    }
    if (view.getAttribute("type") != "editor") {
        label = view.title;
    }
    return [label, tooltip];
};

/**
 * Shared code that returns a label and tooltip based on the path info,
 * and other pertinent info on the state of the document/view object.
 * @param {string} baseName
 * @param {string} dirName
 * @param {Number} lineNo - one-based line number
 * @param {string} tabId - Komodo tab id
 * @param {string} viewType - editor/browser/...
 * @param {string} sectionTitle
 * @param {Boolean} showDirty
 * @returns {string} returns a formatted string: 
 *                      baseName[:lineNo] [*] [(dirName)]
 */
this.labelFromPathInfo = function(baseName, dirName, lineNo, tabId,
                                  viewType, sectionTitle,
                                  showDirty) {
    if (typeof(lineNo) == "undefined") {
        lineNo = null;
    }
    if (typeof(tabId) == "undefined") {
        tabId = null;
    }
    if (typeof(viewType) == "undefined") {
        viewType = null;
    }
    if (typeof(sectionTitle) == "undefined") {
        sectionTitle = null;
    }
    if (typeof(showDirty) == "undefined") {
        showDirty = false;
    }

    var label = baseName;
    if (lineNo != null) {
        label += ":" + lineNo;
    }
    if (showDirty) {
        label += "*";
    }
    if (sectionTitle) {
        if (sectionTitle.length > 25) {
            // ellipsis
            sectionTitle = sectionTitle.substr(0, 25) + String.fromCharCode(0x2026);
        }
        label += " '" + sectionTitle + "'";
    }
    if (tabId != null || viewType != null) {
        label += " (";
        if (tabId != null) {
            label += tabId;
            if (viewType) {
                label += ",";
            }
        }
        if (viewType) {
            label += viewType;
        }
        label += ")";
    }
    if (dirName) {
        // mdash
        label += " " + String.fromCharCode(0x2014) + " " + dirName;
    }
    return label;
};

this._gotoLine_report_error = function _gotoLine_report_error(errorBox, line) {
    document.getElementById('gotoLine_error_label').value = locals.bundle.formatStringFromName("isInvalidYoumustEnterANumber.alert", [line], 1);
    errorBox.removeAttribute("collapsed");
};

this.gotoLine_onkeypress_handler = function ko_views_gotoLine_onkeypress_handler(event)
{
    if (event.keyCode != event.DOM_VK_RETURN) {
        return;
    }
    // Stop the event from being consumed by Komodo's keybinding manager.
    event.preventDefault();
    event.stopPropagation();

    var gotoLineTextbox = document.getElementById("gotoLine_textbox");
    var line = gotoLineTextbox.value;
    if (!line) {
        return;
    }

    // Columns are optional, follow either "," or "." (Bug 88710)
    //   42     go to line 42 (column 0)
    //   42,10  -- go to line 42, col 10 (1-based) (or EOL)

    //   +1     sign=+, num=1 -- move down 1 line, but to column 0 (legacy behavior)
    //   +1,+0  move down 1 line, keep same column
    //   +1,-0  same: down 1 line, same column

    //   ,+8 -- on current line, move 8 columns to the right, or EOL
    //   ,-8 -- move 6 columns to the left, or start of line
    //   -1,+10 move to previous line, than right 10 columns
    //   a      invalid

    // Parse the line, creates [lineSign, lineNum, columnSign, columnNum] variables for the given line string.
    var lineParser_re = /^\s*(?:([\-\+]?)(\d*))(?:[\,\.]([\-\+]?)(\d+))?\s*$/;
    var errorBox = document.getElementById('gotoLine_error_hbox');
    var m = lineParser_re.exec(line);
    if (!m) {
        this._gotoLine_report_error(errorBox, line);
        return;
    }
    errorBox.setAttribute("collapsed", "true");
    var lineSign = m[1], lineNum = m[2], columnSign = m[3], columnNum = m[4];
    // column parts could be undefined
    if (typeof(columnNum) === "undefined") {
        columnSign = columnNum = null;
    }
    if (lineNum === "") {
        if (lineSign) {
            this._gotoLine_report_error(errorBox, line);
            return;
        }
        lineSign = lineNum = null;
    } else {
        lineNum = parseInt(lineNum, 10);
        if (lineSign === "") {
            lineSign = null;
        }
    }
    if (columnNum === null) {
        if (columnSign) {
            this._gotoLine_report_error(errorBox, line);
            return;
        }
    } else {
        columnNum = parseInt(columnNum, 10);
        if (columnSign === "") {
            columnSign = null;
        }
    }
    if (lineNum === null && columnNum === null) {
        // No input to work with.
        this._gotoLine_report_error(errorBox, line);
        return;
    }
    //dump("parseLine(line="+line+"): lineSign="+lineSign+", lineNum="+lineNum+", columnSign: " + columnSign + ", columnNum: " + columnNum + "\n");

    var gotoLinePanel = document.getElementById("gotoLine_panel");
    gotoLinePanel.hidePopup();

    var view = ko.views.manager.currentView;
    ko.history.note_curr_loc(view);
    
    var scimoz = view.scintilla.scimoz;
    var currentPos = scimoz.currentPos;
    var currentColumn = scimoz.getColumn(currentPos);
    var currentLine = scimoz.lineFromPosition(currentPos);
    var targetLine;
    if (lineNum !== null) {
        // Go to the given line.
        switch (lineSign) {
            // No need to do sanity-checking on out-of-bounds targetLine :
            // Scintilla stops at either line 0 or line <lineCount - 1>
          case null:
           targetLine = lineNum - 1;
           break;
          case "+":
           targetLine = currentLine + lineNum;
           break;
          case "-":
           targetLine = currentLine - lineNum;
           break;
          default:
           // This shouldn't happen, but leave it in for better maintenance.
           ko.views.manager.log.error("unexpected goto line 'sign' value: '"+lineSign+"'");
           targetLine = lineNum - 1;
        }
        if (targetLine != currentLine) {
            scimoz.gotoLine(targetLine);
            scimoz.ensureVisible(targetLine);
        }
    } else {
        targetLine = currentLine;
    }
    if (columnNum !== null) {
        var targetColumn, targetPos;
        switch (columnSign) {
            // No need to do sanity-checking on out-of-bounds targetLine :
            // Scintilla stops at either line 0 or line <lineCount - 1>
          case null:
           targetColumn = columnNum;
           break;
          case "+":
           targetColumn = currentColumn + columnNum;
           break;
          case "-":
           targetColumn = currentColumn - columnNum;
           break;
          default:
           // This shouldn't happen
           ko.views.manager.log.error("unexpected goto line 'columnSign' value: '"+columnSign+"'");
           targetColumn = columnNum;
        }
        // Again, scintilla handles negative columns by stopping at line 0,
        // and positions past end-of-line by stopping at end-of-line
        targetPos = scimoz.positionAtColumn(targetLine, targetColumn);
        scimoz.gotoPos(targetPos);
    }
    view.verticallyAlignCaret("onethird");
    scimoz.chooseCaretX();
    // Ensure the view/editor is properly focused - bug 104827.
    view.setFocus();
}

}).apply(ko.views);


ko.window = {};
(function() {

var log = ko.logging.getLogger('window');
//log.setLevel(ko.logging.LOG_DEBUG);

var locals = {};

XPCOMUtils.defineLazyGetter(locals, "bundle", function()
    Services.strings.createBundle("chrome://komodo/locale/views.properties"));

var REASON_ONFOCUS_CHECK = Components.interfaces.koIFileStatusChecker.REASON_ONFOCUS_CHECK;

/**
 * does scintilla have focus?  Return the scintilla widget
 *
 * @returns {Element} xul:scintilla
 */
this.focusedScintilla = function view_focusedScintilla() {
    // Find out if a scintilla (or its child html:embed element) has focus,
    // and if so, return it (not the html:embed element in the latter case).
    // Otherwise, return null.
    function isScintillaTag(elem)
        elem.namespaceURI == "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul" &&
            elem.localName == "scintilla";
    try {
        var commandDispatcher = top.document.commandDispatcher;
        var focusedElement = commandDispatcher.focusedElement;
        if (!focusedElement) return null;
        if (isScintillaTag(focusedElement)) {
            return focusedElement;
        }
        let bindingParent = document.getBindingParent(focusedElement);
        if (bindingParent && isScintillaTag(bindingParent)) {
            return bindingParent;
        }
    } catch (e) {
        log.exception(e);
    }
    return null;
}

/**
 * does any view widget have focus?  return which one does or null
 *
 * @returns {Element} xul:view
 */
this.focusedView = function view_focusedView() {
    return xtk.domutils.getFocusedAncestorByName('view');
}

function _itemStringifier(item)
{
    return item.file.displayPath;
}

var _gInCheckDiskFiles = false;

/**
 * view_checkDiskFiles is only called from the window's focus handler,
 * located in komodo.xul.  it handles checking if any files have changed.
 */
this.checkDiskFiles = function view_checkDiskFiles(event)
{
    if (_gInCheckDiskFiles || !ko.views.manager || ko.views.manager.batchMode) {
        return true;
    }
    if (event && event.eventPhase != event.AT_TARGET) return true;

    var checkDisk = ko.prefs.getBoolean("checkDiskFile", false);
    if (!checkDisk) return true;
    _gInCheckDiskFiles = true;
    log.info('Checking Disk Files');
    window.setTimeout(_view_checkDiskFiles,1);
    return true;
}

function _view_checkDiskFiles(event) {
    // checks open files and projects for dirtiness
    try {
        window.updateCommands('clipboard');
        var changedItems = [];
        var removedItems = [];
        var viewsToReload;
        var conflictedItems = [];
        var view, url, i, j;
        var views, file, prompt, title, item, items;

        // Deal with views first
        views = ko.views.manager.topView.getDocumentViewList(true);
        for (i = 0; i < views.length; i++) {
            view = views[i];
            // browser views do not load via document, so will
            // always be wrong when trying to update status.
            if (view.getAttribute('type')!='editor') continue;
            if (typeof(view.koDoc) == 'undefined' ||
                !view.koDoc ||
                view.koDoc.isUntitled) continue;
            file = view.koDoc.file;
            file.updateStats();
            // onFocus: Don't check file changed for remote files
            if (!file.isLocal || file.isNetworkFile) continue;
            item = new Object;
            item.type = 'view';
            item.view = view;
            item.file = file;
            if (!file.exists) {
                // Force a file stat update by calling updateStats(), this is so
                // we get the latest information for this file, as sometimes
                // this information is stale - bug 94121.
                file.updateStats();
            }
            if (!file.exists) {
                removedItems.push(item);
                view.koDoc.isDirty = true;
            } else {
                if (view.koDoc.differentOnDisk() &&
                    // If this is has a pending operation, the view will be
                    // updated automatically when the command finishes, we
                    // don't want to warn about it until it's finished. See bug:
                    // http://bugs.activestate.com/show_bug.cgi?id=74471
                    !Services.koAsync.uriHasPendingOperation(file.URI)) {

                    if (view.koDoc.isDirty) {
                        conflictedItems.push(item);
                    } else {
                        changedItems.push(item);
                    }
                    view.koDoc.isDirty = true;
                }
            }
        }

        // Now look for changed projects
        var projects = ko.projects.manager._projects;
        for (i = 0; i < projects.length; i++) {
            if (projects[i].haveContentsChangedOnDisk()) {
                if (ko.projects.manager.notifiedIsAlreadySetForProject(projects[i])) {
                    continue;
                }
                file = projects[i].getFile();
                // Force a file stat update by calling updateStats(), this is so
                // the file.exists check made below will still work correctly.
                file.updateStats();
                item = new Object;
                item.type = 'project';
                item.project = projects[i];
                item.file = file;
                if (!file.exists) {
                    // Force file stat update by calling updateStats(), this is
                    // so we get the latest information for this file, as
                    // sometimes this information is stale - bug 94121.
                    file.updateStats();
                }
                if (!file.exists) {
                    removedItems.push(item);
                    // XXX: I don't agree with the setting to dirty here, this
                    //      should only be done if the user cancels the offer
                    //      to close the file, as when the user selects "close",
                    //      they will be prompted a second time asking if they
                    //      now wish to save the project before they close it,
                    //      even if it was not dirty to debug with. (ToddW)
                    item.project.isDirty = true;
                } else if (item.project.isDirty) {
                    conflictedItems.push(item);
                } else {
                    changedItems.push(item);
                    item.project.isDirty = true;
                }
                // Mark the project, so we don't keep re-prompting for the same
                // situation (the mark will be removed when the project is
                // saved or reverted by the user).
                ko.projects.manager.notifiedAddProject(projects[i]);
            }
        }

        // handle files and projects that have changed on disk
        if (changedItems.length > 0) {
            title = locals.bundle.GetStringFromName("reloadChangedFilesAndProjects.prompt");
            prompt = locals.bundle.GetStringFromName("someOpenFilesAndOrProjectsHaveChanged.prompt");
            items = ko.dialogs.selectFromList(title,
                                          prompt,
                                          changedItems,
                                          'zero-or-more',
                                          _itemStringifier,
                                          'reload_changed_files');
            if (items != null && items.length > 0) {
                for (i = 0; i < items.length; i++) {
                    if (item.type == 'view') {
                        items[i].view.revertUnconditionally()
                        if (ko.codeintel.isActive) {
                            ko.codeintel.scan_document(
                                items[i].view.koDoc,
                                // linesAdded: using non-zero value to
                                // encourage high-prio rescan
                                1,
                                false /* forcedScan */);
                        }
                    } else {
                        ko.projects.manager.revertProject(items[i].project);
                    }
                }
            }
        }
        // handle files and projects that have changed on disk
        if (removedItems.length > 0) {
            for (i = 0; i < removedItems.length; ++i) {
                if (removedItems[i].view &&
                    removedItems[i].view.koDoc) {
                    removedItems[i].view.koDoc.isDirty = true;
                }
            }
            title = locals.bundle.GetStringFromName("closeDeletedFilesAndProjects.prompt");
            prompt = locals.bundle.GetStringFromName("theFollowingFilesAndProjectsDeleted.prompt");
            items = ko.dialogs.selectFromList(title,
                                          prompt,
                                          removedItems,
                                          'zero-or-more',
                                          _itemStringifier,
                                          'close_deleted_files');
            if (items != null && items.length > 0) {
                for (i = 0; i < items.length; i++) {
                    if (item.type == 'view') {
                        items[i].view.close(true);
                    } else {
                        ko.projects.manager.closeProject(items[i].project);
                    }
                }
            }
        }

        //XXX You can get this dialog when closing Komodo with
        //    a file one choses to not save and after everything else has
        //    closed so there is nothing that can really be done.
        // handle files and projects that have changed and are dirty
        if (conflictedItems.length > 0) {
            prompt = locals.bundle.GetStringFromName("theFollowingFilesHaveChangedOnDisk.prompt");
            title = locals.bundle.GetStringFromName("modifiedFilesHaveChangedOnDisk.prompt");
            var text = '';
            for (i = 0; i < conflictedItems.length; i++) {
                text += _itemStringifier(conflictedItems[i]) + '\n'
            }
            ko.dialogs.alert(prompt, text, title, "buffer_conflicts_with_file_on_disk")
        }
    } catch(e) {
        log.exception(e);
    }
    Services.koFileStatus.updateStatusForAllFiles(REASON_ONFOCUS_CHECK);
    // when we leave this function, if any dialogs were shown, the
    // main window gets a focus event again.  So we want to wait long
    // enough so that the new focus event does not enter this function
    // again. (bug 29037)
    window.setTimeout(function() { _gInCheckDiskFiles = false; }, 100);
    return true;
}

this.getHomeDirectory = function() {
    if (Services.koUserEnv.has("HOME")) {
        return Services.koUserEnv.get("HOME");
    } else {
// #if PLATFORM == "win"
        return "C:\\";
// #else
        return "/";
// #endif
    }
}

/**
 * get the current working directory for the window, which is the directory
 * of the current buffer, or the home directory of the user
 */

this.getCwd = function view_GetCwd() {
    var win = ko.windowManager.getMainWindow();
    var view = win.ko.views.manager.currentView;
    if (view != null &&
        view.getAttribute("type") == "editor" &&
        view.koDoc.file &&
        view.koDoc.file.isLocal) {
        return view.cwd;
    } else {
        return this.getHomeDirectory();
    }
}

}).apply(ko.window);

// Convenient accessors, not to be deprecated (yet).
var gEditorTooltipHandler = xtk.domutils.tooltips.getHandler('editorTooltip');
