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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.views)=='undefined') {
    ko.views = {};
}

(function() {
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/views.properties");
var _docSvc = Components.classes['@activestate.com/koDocumentService;1']
                .getService(Components.interfaces.koIDocumentService);
var _observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                getService(Components.interfaces.nsIObserverService);
var _lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                        getService(Components.interfaces.koILastErrorService);

function viewManager() {
    this.log = ko.logging.getLogger('views');
    this.log.info("viewManager constructor");
    /**
     * The current view that is shown in Komodo's main tab.
     * @type Components.interfaces.koIScintillaView
     */
    this.currentView = null;
    this.topView = document.getElementById('topview');
    this.topView.init();
    ko.main.addCanCloseHandler(this.canClose, this);
    ko.main.addWillCloseHandler(this.postCanClose, this);
    _observerSvc.addObserver(this, "open_file", false); // commandment
    _observerSvc.addObserver(this, "open-url",false);
    _observerSvc.addObserver(this, "SciMoz:FileDrop", false);
    _observerSvc.addObserver(this, "file_status", false);
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
    window.controllers.appendController(this); // XXX need to uninstall on quit
};

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
viewManager.prototype = new xtk.Controller();
viewManager.prototype.constructor = viewManager;

viewManager.prototype.shutdown = function()
{
    try {
        _observerSvc.removeObserver(this, "open_file");  // commandment
        _observerSvc.removeObserver(this, "open-url");
        _observerSvc.removeObserver(this, "SciMoz:FileDrop");
        _observerSvc.removeObserver(this, "file_status");
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
        log.warn('possible error shutting down viewManager:'+e);
    }
}

viewManager.prototype.canClose = function()
{
    try {
        this._dirtyItems = null;
        var dirtyItems = this.offerToSave();
        if (typeof(dirtyItems) == 'boolean')
            return dirtyItems;

        // we CAN shutdown.  Save the dirty items for handling
        // in the shutdown function above.  If the entire canClose
        // succeeds, these will be handled in the postCanClose below.
        this._dirtyItems = dirtyItems;
    } catch(e) {
        /* moz probably already removed them */
        log.exception(e,'exception in viewManager.canClose');
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
                if (item.view && item.view.document)
                    item.view.document.removeAutoSaveFile();
            }
        }
        this.shutdown();
        // We didn't call _doCloseAll originally when the view mgr
        // was designed around v2, for perf reasons,
        // which prob don't hold anymore.
        var ignoreFailures=true, closeStartPage=true, doNotOfferToSave=true;
        this._doCloseAll(ignoreFailures, closeStartPage, doNotOfferToSave);
    } catch(e) {
        /* moz probably already removed them */
        log.warn('exception in viewManager.postCanClose:'+e);
    }
    return false;
}

/**
 * get the default directory based on a project or the current buffer.  This
 * is used by file open dialogs to set the initial directory of the dialog.
 *
 * @public
 * @param project {Components.interfaces.koIProject}
 *        optional, instance of a project
 * @return {string} the current "default" directory to work from.
 */
viewManager.prototype.getDefaultDirectory = function(project) {
    // get the default dir from the current buffer directory, or the
    // current project directory
    var defaultDir = null;
    if (!project) {
        project = ko.projects.manager.currentProject;
    }
    var v = this.currentView;
    if (v && v.getAttribute("type") == "editor" &&
        v.document && !v.document.isUntitled && v.document.file.isLocal)
    {
        defaultDir = this.currentView.document.file.dirName;
    } else if (project) {
        defaultDir = ko.projects.getDefaultDirectory(project);
    }
    if (!defaultDir) {
        // XXX TODO
        // lets use the users home dir on non-windows platforms
    }
    return defaultDir;
}

/**
 * create a new file based on a selected template, optionally add it to a
 * project.  this will prompt the user to select a template.
 *
 * @public
 * @param defaultDir {string} optional, current directory
 * @param project {Components.interfaces.koIProject}
 *        optional, instance of a project
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.newTemplate = function(defaultDir, project) {
    var view = null;
    if (!defaultDir) {
       defaultDir = this.getDefaultDirectory(project);
    }
    if (!project) {
        project = ko.projects.manager.currentProject;
    }
    try {
        this.log.info("doing newTemplate: ");
        var uri;
        var saveto = null;

        // Get template selection from the user.
        var obj = new Object();
        obj.type = "file";
        obj.defaultDir = defaultDir;
        obj.project = project;
        obj.filename = null;
        window.openDialog("chrome://komodo/content/templates/new.xul",
                          "_blank",
                          "chrome,modal,titlebar",
                          obj);
        if (obj.template == null) return null;

        uri = ko.uriparse.localPathToURI(obj.template);
        if (obj.filename)
            saveto = ko.uriparse.pathToURI(obj.filename);
        view = this.doFileNewFromTemplate(uri, saveto);
        if (!view) return null;
        if (saveto && obj.addToProject && project) {
            // does the project have a live folder that is the base
            // for the new filename?  If so, we do nothing.  Otherwise,
            // we add the file to the currently selected (if any) folder
            // for the current project
            if (!project.containsLiveURL(saveto)) {
                // don't pass a koipart here, it will get the selected folder
                // to add the file to.
                ko.projects.addFileWithURL(saveto, project);
            }
        }
        window.setTimeout(function(view) {view.setFocus();}, 1, ko.views.manager.currentView);
    } catch(ex) {
        this.log.exception(ex, "Error in newTemplate.");
    }
    return view;
}


/**
 * Create a new file based on a template, optionally add it to a project.
 *
 * @private
 *
 * @param uri {string} optional, uri pointing to a template file
 * @param saveto {string} optional, where to save the new file
 * @param viewType {string} optional, type of buffer to open, default "editor"
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
    this.log.info("doing doFileNewFromTemplate: ");
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
            doc = _docSvc.createFileFromTemplateURI(uri, saveto, false);
        } else {
            doc = _docSvc.createDocumentFromTemplateURI(uri, name, ext);
        }
    } catch (ex) {
        errmsg = _lastErrorSvc.getLastErrorMessage();
        log.exception(ex, errmsg);
        ko.dialogs.internalError(_bundle.GetStringFromName("errorOpeningTemplate.message"),
                                 _bundle.formatStringFromName("errorLoadingTemplate.message", [uri], 1),
                                 ex);
        // even though there is an error, continue opening the
        // file so the user gets *something*
    }
    
    var docText = doc.buffer;
    var hasTabStops = ko.tabstops.textHasTabstops(docText);
    try {
        // Interpolate any codes.
        var istrings = ko.interpolate.interpolate(
                            window,
                            [], // codes are not bracketed
                            [docText], // codes are bracketed
                            _bundle.formatStringFromName("templateQuery.message", [name], 1),
                            ko.interpolate.getViewData(window));
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
        var errno = _lastErrorSvc.getLastErrorCode();
        if (errno == Components.results.NS_ERROR_ABORT) {
            // Command was cancelled.
        } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
            errmsg = _lastErrorSvc.getLastErrorMessage();
            ko.dialogs.alert(_bundle.formatStringFromName("couldNotInterpolate.message", [errmsg], 1));
        } else {
            log.exception(ex, _bundle.GetStringFromName("errorInterpolatingTemplate.message"));
            ko.dialogs.internalError(_bundle.formatStringFromName("couldNotProcessInterpolatingCodes.message", [basename], 1),
                                     _bundle.formatStringFromName("errorInterpolatingTemplateUri.message", [uri], 1),
                                     ex);
        }
    }

    // Load the template.
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
        view.document.setTabstopInsertionTable(liveTextInfo.tabstopInsertionTable.length,
                                               liveTextInfo.tabstopInsertionTable);
        view.moveToNextTabstop();
    }

    return view;
}

/**
 * Create a new file based on a template, optionally add it to a project.
 * Deprecated, use the doFileNewFromTemplateAsync function instead.
 * 
 * @deprecated since 5.0.3 (this will be moved to an internal function)
 *
 * @param uri {string} optional, uri pointing to a template file
 * @param saveto {string} optional, where to save the new file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.doFileNewFromTemplate = function(uri,
                                                       saveto  /*=null*/,
                                                       viewType /*="editor"*/,
                                                       viewList /*=null*/)
{
    this.log.deprecated("doFileNewFromTemplate is deprecated, use " +
                        "ko.views.manager.doFileNewFromTemplateAsync");
    return this._doFileNewFromTemplate(uri, saveto, viewType, viewList);
}

/**
 * Asynchronously create a new file based on a template, optionally add it
 * to a project.
 *
 * @param uri {string} optional, uri pointing to a template file
 * @param saveto {string} optional, where to save the new file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param callback {function} optional, to be called when the asynchronous load
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
 * @param language {string} optional, language of the buffer (eg. python)
 * @param viewType {string} optional, type of buffer to open, default "editor"
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype._doNewView = function(language /*= prefs.fileDefaultNew*/,
                                            viewType /*='editor'*/)
{
    this.log.info("doing doNewView: ");
    ko.trace.get().enter('viewManager.doNewView');

    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(language)=='undefined' || !language) {
        language = gPrefs.getStringPref('fileDefaultNew');
    }

    // the following line is delayed to avoid notifications during load()
    var doc = _docSvc.createUntitledDocument(language);
    var view = this.topView.createViewFromDocument(doc, viewType, -1);

    ko.trace.get().leave('viewManager.doNewView');
    this.log.info("leaving doNewView");
    return view;
}

/**
 * Create a new empty, unsaved editor buffer.
 *
 * @deprecated since 5.0.3 (this will be moved to an internal function)
 *
 * @param language {string} optional, language of the buffer (eg. python)
 * @param viewType {string} optional, type of buffer to open, default "editor"
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.doNewView = function(language /*= prefs.fileDefaultNew*/,
                                           viewType /*='editor'*/)
{
    this.log.deprecated("doNewView is deprecated, use " +
                        "ko.views.manager.doNewViewAsync");
    return this._doNewView(language, viewType);
}

/**
 * Asynchronously create a new empty, unsaved editor buffer.
 *
 * @param language {string} optional, language of the buffer (eg. python)
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param callback {function} optional, to be called when the asynchronous load
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
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
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
    this.log.info("doing newViewFromURI: " + uri);
    ko.trace.get().enter('viewManager.newViewFromURI');
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(viewList)=='undefined')
        viewList = null;
    if (typeof(index) == 'undefined' || index == null)
        index = -1;

    var doc = _docSvc.createDocumentFromURI(uri);
    var view = null;
    if (! doc.file.exists) {
        if (ko.dialogs.yesNo(_bundle.formatStringFromName("theFileDoesNotExist.message", [doc.file.displayPath], 1)) == "No") {
            return null;
        } else {
            var sysUtils = Components.classes["@activestate.com/koSysUtils;1"]
                            .createInstance(Components.interfaces.koISysUtils);
            try {
                sysUtils.Touch(doc.file.displayPath);
            } catch(touch_ex) {
                ko.dialogs.alert(_bundle.formatStringFromName("komodoWasUnableToCreateTheFile.alert", [doc.file.displayPath], 1));
                return null;
            }
            try {
                // Ensure the file status is updated now that the file exists.
                // http://bugs.activestate.com/show_bug.cgi?id=67949
                var obSvc = Components.classes["@mozilla.org/observer-service;1"].
                        getService(Components.interfaces.nsIObserverService);
                obSvc.notifyObservers(this, 'file_changed', doc.file.URI);
            } catch (ex) {
                /* no listeners for this event */
            }
        }
    }
    if (doc.file.isDirectory) {
        ko.dialogs.alert(_bundle.formatStringFromName("komodoCannotOpenDirectories.alert", [doc.file.path], 1));
        return null;
    }
    try {
        if (doc.haveAutoSave() &&
            ko.dialogs.yesNo(_bundle.formatStringFromName("itAppearsTheFileWasNotSaved.alert", [doc.file.displayPath], 1)) == "Yes") {
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
    } catch (e)  {
        var err = _lastErrorSvc.getLastErrorMessage();
        ko.dialogs.alert(_bundle.formatStringFromName("komodoWasUnableToOpenTheFile.alert", [doc.file.baseName], 1),
                         err,
                         _bundle.GetStringFromName("fileOpenError.alert"));
        this.log.exception(e);
        view = null;
    }

    // Ensure file is scanned (bug 77866).
    var codeIntelSvc = Components.classes["@activestate.com/koCodeIntelService;1"]
        .getService(Components.interfaces.koICodeIntelService);
    codeIntelSvc.scan_document(doc, 0, true);

    ko.trace.get().leave('viewManager.newViewFromURI');
    this.log.info("leaving newViewFromURI");
    return view;
}

/**
 * Create a new buffer and open a file into it.
 * Note: The "uri" will *not* be translated by the mapped URI functionality.
 *
 * @deprecated since 5.0.3 (this will be moved to an internal function)
 *
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.newViewFromURI = function(uri,
                                                viewType/*='editor'*/,
                                                viewList/*=null*/,
                                                index /* =-1 */)
{
    this.log.deprecated("newViewFromURI is deprecated, use " +
                        "ko.views.manager.newViewFromURIAsync");
    return this._newViewFromURI(uri, viewType, viewList, index);
}

/**
 * Create a new buffer and open a file into it.
 * Note: The "uri" will *not* be translated by the mapped URI functionality.
 *
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 * @param callback {function} optional, to be called when the asynchronous load
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

/**
 * Open a file. If it is already open, then select that buffer,
 * else create a new buffer for the file.
 * Note: The "uri" will be translated using the mapped URI functionality.
 *
 * @private
 *
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *      optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
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
        }
    }
    return this._newViewFromURI(uri, viewType, viewList, index);
}

/**
 * Open a file. If it is already open, then select that buffer,
 * else create a new buffer for the file.
 * Note: The "uri" will be translated using the mapped URI functionality.
 *
 * @deprecated since 5.0.3 (this will be moved to an internal function)
 *
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *      optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
 *      the new view. If not given, or -1, then the new view is appended.
 *      If there is already a view open for this `uri`, then index is ignored.
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.doFileOpen = function(uri,
                                            viewType/*='editor'*/,
                                            viewList/*=null*/,
                                            index /* =-1 */)
{
    this.log.deprecated("doFileOpen is deprecated, use " +
                        "ko.views.manager.doFileOpenAsync");
    return this._doFileOpen(uri, viewType, viewList, index);
}

/**
 * Asyncronously open a file. If it is already open, then select that buffer,
 * else create a new buffer for the file.
 * Note: The "uri" will be translated using the mapped URI functionality.
 *
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *      optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
 *      the new view. If not given, or -1, then the new view is appended.
 *      If there is already a view open for this `uri`, then index is ignored.
 * @param callback {function} optional, to be called when the asynchronous load
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
 * @param uri {string} uri to file
 * @param lineno {integer} line number
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
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
        v.currentLine = lineno;
    }
    return v;
}

/**
 * Open a file at the given line number. If it is already open, then select
 * that buffer, else create a new buffer for the file.
 *
 * @deprecated since 5.0.3 (this will be moved to an internal function)
 *
 * @param uri {string} uri to file
 * @param lineno {integer} line number
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 *
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.doFileOpenAtLine = function(uri,
                                                  lineno,
                                                  viewType/*='editor'*/,
                                                  viewList/*=null*/,
                                                  index /* =-1 */)
{
    this.log.deprecated("doFileOpenAtLine is deprecated, use " +
                        "ko.views.manager.doFileOpenAtLineAsync");
    return this._doFileOpenAtLine(uri, lineno, viewType, viewList, index);
}

/**
 * Asyncronously open a file at the given line number. If it is already open,
 * then select that buffer, else create a new buffer for the file.
 *
 * @param uri {string} uri to file
 * @param lineno {integer} line number
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {Components.interfaces.koIViewList}
 *        optional, what pane to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
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
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param tabGroup {string} optional, which tab group to open the buffer in
 * @param index {integer} optional index in the `viewList` at which to insert
 *        the new view. If not given, or -1, then the new view is appended.
 *        If there is already a view open for this `uri`, then index is ignored.
 * @param callback {function} optional, to be called when the asynchronous load
 *        is complete. The view will be passed as an argument to the function.
 *
 * @return null
 */
viewManager.prototype.openViewAsync = function(viewType, uri, tabGroup, tabIndex, callback) {
    if (typeof(tabGroup) == "undefined") tabGroup = null;
    var tabList = tabGroup ? document.getElementById(tabGroup) : null;
    switch (viewType) {
    case "startpage":
        // ko.open.startPage() uses the current view.
        // Using doFileOpen... uses the same view when it was closed,
        // but we have to hardwire the startpage URI
        uri = "chrome://komodo/content/startpage/startpage.xml#view-startpage";
        // FALLTHRU
    case "editor":
        ko.views.manager.doFileOpenAsync(uri, viewType, tabList, tabIndex, callback);
        break;
    case "browser":
        ko.views.manager.newViewFromURIAsync(uri, 'browser', tabList, tabIndex, callback);
        break;
    default:
        this.log.error("Don't know how to open " + viewType + " views\n");
    }
}

/**
 * Get a reference to the buffer view for the given URI and view type.
 *
 * @public
 * @since Komodo 4.3.0
 * 
 * @param uri {string} URI to file
 * @param viewType {string} optional, type of view to find, default is any
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
 * Get a reference to the buffer view for the given URI.
 *
 * @public
 * @deprecated since Komodo 4.3.0, use getViewForURI instead.
 * 
 * @param uri {string} uri to file
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.getViewForFile = function(uri) {
    log.warn("viewManager.getViewForFile is deprecated, use " +
             "viewManager.getViewForURI instead.");
    return this.getViewForURI(uri);
}

/**
 * get a reference to a new and unsaved buffer view
 *
 * @public
 * @param name {string} name of the buffer
 * @return {Components.interfaces.koIView} the buffer view that is opened
 */
viewManager.prototype.getUntitledView = function(name) {
    try {
        var doc = _docSvc.findDocumentByURI(name);
        return this.topView.findViewForDocument(doc);
    } catch (e) {
        log.exception(e);
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
 * Open a uri in a new view, bypassing any sanity checking on the uri.
 * This function is deprecated, use newViewFromURI instead.
 *
 * @deprecated since 5.0.3
 *
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 */
viewManager.prototype.loadViewFromURI = function(uri, viewType/*='editor'*/)
{
    this.log.info("doing loadViewFromURI: " + uri);
    ko.trace.get().enter('viewManager.loadViewFromURI');
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    var doc = _docSvc.createDocumentFromURI(uri);

    // the following line is delayed to avoid notifications during load()
    var view = this.topView.createViewFromDocument(doc, viewType, -1);
    ko.trace.get().leave('viewManager.loadViewFromURI');
    this.log.info("leaving loadViewFromURI");
}

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
    cache.canPreview = false;
    if (view) {
        cache.type = view.getAttribute('type');
        if (view.document) {
            cache.hasSelection = view.selection != '';
            cache.isDirty = view.document.isDirty
            if (cache.type == 'editor') {
                cache.canUndo = view.scintilla.canUndo();
                cache.canRedo = view.scintilla.canRedo();
                cache.canPreview = view.document.file && view.document.file.isLocal;
            }
            if (view.document.languageObj) {
                cache.canFold = view.document.languageObj.foldable;
                cache.language = view.document.language;
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
                    // Are we using character index or line,column?
                    if (anchorDesc.indexOf(',') == -1) {
                        anchor = Number(anchor);
                    } else {
                        subparts = anchorDesc.split(',');
                        var anchorLine = Math.max(Number(subparts[0]) - 1, 0);
                        var anchorCol = Math.max(Number(subparts[1]) - 1, 0);
                        anchor = ko.views.manager.currentView.positionAtColumn(anchorLine,
                                                                               anchorCol);
                    }
                    if (currentPosDesc.indexOf(',') == -1) {
                        currentPos = Number(currentPos);
                    } else {
                        subparts = currentPosDesc.split(',')
                        var currentPosLine = Math.max(Number(subparts[0]) - 1, 0);
                        var currentPosCol = Math.max(Number(subparts[1]) - 1, 0);
                        currentPos = ko.views.manager.currentView.positionAtColumn(currentPosLine,
                                                                                   currentPosCol);
                    }
                    // do gotoline first because it messes w/ current position and anchor.
                    var lineNo = view.scimoz.lineFromPosition(currentPos);
                    view.scimoz.gotoLine(Math.max(lineNo - 1, 0)); // scimoz is 0-indexed
                    view.anchor = anchor;
                    view.currentPos = currentPos;
                }
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
        case 'SciMoz:FileDrop':
        case 'open_file':
        case 'open-url': // see nsCommandLineServiceMac.cpp, bug 37787
            // This is also used by komodo macro API to open files from python
            if (ko.windowManager.getMainWindow() == window) {
                this.handle_open_file(topic, data);
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
    }
}

viewManager.prototype.handle_current_view_changed = function(event) {
    // Update the currentView
    // This has to happen always since one can do ctrl+tab,ctrl+i, and that
    // needs to find the right view.
    this.currentView = event.originalTarget;
    if (this.batchMode) {
        // break out early -- we don't want to update controllers at this point.
        return;
    }
    if (this.topView.viewhistory.inBufferSwitchingSession) {
        // break out early -- we don't want to update controllers at this point.
        return;
    }
    var oldcache = this.lastviewcache;
    var newcache = this.cacheCommandData(this.currentView);
    //for (var x in oldcache) {
    //    dump('oldcache['+ x +'] = ' + oldcache[x] + '\n');
    //}
    //for (var x in newcache) {
    //    dump('newcache['+ x +'] = ' + newcache[x] + '\n');
    //}
    window.setTimeout("window.updateCommands('current_view_changed');", 1);
    var update_editor_change = (oldcache.type != newcache.type) &&
        (oldcache.type == 'editor' || newcache.type== 'editor');
    if (update_editor_change) {
        window.setTimeout("window.updateCommands('currentview_is_editor');", 1)
    }
    window.setTimeout("window.updateCommands('dirty');", 1);
    if (update_editor_change || oldcache.canUndo != newcache.canUndo ||
        oldcache.canRedo != newcache.canRedo) {
        window.setTimeout("window.updateCommands('undo');", 1);
    }
    if (update_editor_change || oldcache.language != newcache.language) {
        window.setTimeout("window.updateCommands('language_changed');", 1)
    }
    if (update_editor_change || oldcache.canFold != newcache.canFold) {
        window.setTimeout("window.updateCommands('foldability_changed');", 1);
    }
    if (update_editor_change || oldcache.canPreview != newcache.canPreview) {
        window.setTimeout("window.updateCommands('previewability_changed');",1);
    }
    if (update_editor_change || oldcache.hasSelection != newcache.hasSelection) {
        window.setTimeout("window.updateCommands('select');", 1);
    }
    this.lastviewcache = newcache;
}

viewManager.prototype.handle_view_closed = function() {
    this._viewCount--;
    this.log.info("_viewcount is " + this._viewCount);
    if (this._viewCount == 0) {
        this.log.info("sending event: 'some_files_open'");
        window.setTimeout("window.updateCommands('some_files_open');", 1);
    } else if (this._viewCount == 1) {
        // We've closed our second view
        window.setTimeout("window.updateCommands('second_view_open_close');", 1);
    }
};

viewManager.prototype.handle_view_opened = function() {
    this.log.info("got 'view opened' notification");
    this._viewCount++;
    this.log.info("_viewcount is " + this._viewCount);
    if (this._viewCount == 1) {
        this.log.info("sending event: 'some_files_open'");
        window.setTimeout("window.updateCommands('some_files_open');", 1);
    } else if (this._viewCount == 2) {
        // We've opened our second view
        window.setTimeout("window.updateCommands('second_view_open_close');", 1);
    }
};
        
viewManager.prototype.supportsCommand = function(command) {
    if (command.indexOf("cmd_viewAs") == 0) {
        return true;
    }

    return Controller.prototype.supportsCommand.apply(this, [command]);
}

viewManager.prototype.isCommandEnabled = function(command) {
    if (command.indexOf("cmd_viewAs") == 0) {
        // XXX we want to use a broadcaster for this, there are too many.
        var rc = ko.views.manager.currentView && ko.views.manager.currentView.getAttribute('type') == 'editor'
        //this.log.warn('asked about' + command + ', returning ' + rc );
        return rc;
    }

    return Controller.prototype.isCommandEnabled.apply(this, [command]);
}

viewManager.prototype.doCommand = function(command) {
    Controller.prototype.doCommand.apply(this, [command]);
}

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
    this._doCloseAll();
}

viewManager.prototype._doCloseAll = function(ignoreFailures, closeStartPage, doNotOfferToSave) {
    if (typeof(ignoreFailures) == "undefined") ignoreFailures = false;
    if (typeof(closeStartPage) == "undefined") closeStartPage = false;
    if (typeof(doNotOfferToSave) == "undefined") doNotOfferToSave = false;
    // returns true if all views were closed.
    var views = this.topView.getDocumentViews(true);
    var i;
    for (i = views.length-1; i >= 0; i--) {
        // Exclude the Start Page from "Close All".
        //   http://bugs.activestate.com/show_bug.cgi?id=27321
        if (views[i].getAttribute("type") == "startpage" && !closeStartPage)
            continue;
        if (! views[i].close(doNotOfferToSave) && !ignoreFailures) {
            return false;
        }
    }
    return true;
}

viewManager.prototype.is_cmd_cleanLineEndings_supported = function() {
    this.log.info('is_cmd_cleanLineEndings_supported');
    return 1;
}

viewManager.prototype.is_cmd_cleanLineEndings_enabled = function() {
    var currView = ko.views.manager.currentView;
    return (currView && currView.getAttribute("type") == "editor" &&
            currView.document);
}

viewManager.prototype.do_cmd_cleanLineEndings = function() {
    var currView = ko.views.manager.currentView;
    if (currView && currView.getAttribute("type") == "editor" && currView.document) {
        currView.document.cleanLineEndings();
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
        title = _bundle.GetStringFromName("saveModifiedFiles.prompt");
    }
    if (typeof(prompt) == 'undefined' || prompt == null) {
        title = _bundle.GetStringFromName("pleaseSelectTheFilesYouWishToSave.prompt");
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
                    ko.statusBar.AddMessage(
                        _bundle.GetStringFromName("macroInterruptedFileClosingProcedure.message"),
                        "macro",
                        5000,
                        true);
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
                if (view.document.isUntitled) continue;
                // exclude if it's not in the list
                if (! _elementInArray(view.document.file.URI, urls)) {
                    continue;
                }
            }
            if (aboutToClose
                && !view.document.isUntitled
                && ko.windowManager.otherWindowHasViewForURI(view.document.file.URI)) {
                // Untitled documents can't be in other windows.
                continue;
            }
            // We need to deal with views that are split and that share a document
            // So we keep track of the displayPaths, and only add a view
            // if it's display path isn't already in our list.
            if (view.document.displayPath in sofar) continue;
            sofar[view.document.displayPath] = true;
            item = new Object();
            item.type = 'view';
            item.view = view;
            dirtyItems.push(item);
        }
    }
    if (!skipProjects) {
        var dirtyProjects = ko.projects.manager.getDirtyProjects();
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
            return item.view.document.displayPath;
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
                          [_bundle.GetStringFromName("save.prompt"),
                           _bundle.GetStringFromName("doNotSave.prompt"),
                           _bundle.GetStringFromName("cancel.prompt")]);
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
 * @param urls {array} list of files to revert
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
 * @param urls {array} list of files to close
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

// cmd_find
viewManager.prototype.is_cmd_find_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_find_enabled = function() {
    var currView = ko.views.manager.currentView;
    if (currView && currView.getAttribute("type") == "editor") {
        return true;
    } else {
        return false;
    }
}

viewManager.prototype.do_cmd_find = function() {
    ko.launch.find();
}

// cmd_replace
viewManager.prototype.is_cmd_replace_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_replace_enabled = function() {
    return this._viewCount != 0;
}

viewManager.prototype.do_cmd_replace = function() {
    ko.launch.replace();
}

// cmd_findNext
viewManager.prototype.is_cmd_findNext_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_findNext_enabled = function() {
    return ko.views.manager.currentView ? true : false;
}

viewManager.prototype.do_cmd_findNext = function() {
    var pattern = ko.mru.get("find-patternMru");
    if (pattern) {
        var context = Components.classes[
            "@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
        var findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
        context.type = findSvc.options.preferredContextType;
        findSvc.options.searchBackward = false;
        Find_FindNext(window, context, pattern);
    } else {
        ko.launch.find();
    }
}

// cmd_findPrevious
viewManager.prototype.is_cmd_findPrevious_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_findPrevious_enabled = function() {
    return ko.views.manager.currentView ? true : false;
}

viewManager.prototype.do_cmd_findPrevious = function() {
    var pattern = ko.mru.get("find-patternMru");
    if (pattern) {
        var context = Components.classes["@activestate.com/koFindContext;1"]
                      .createInstance(Components.interfaces.koIFindContext);
        var findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
        context.type = findSvc.options.preferredContextType;
        findSvc.options.searchBackward = true;
        Find_FindNext(window, context, pattern);
    } else {
        ko.launch.find();
    }
}

// cmd_findNextResult
viewManager.prototype.is_cmd_findNextResult_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_findNextResult_enabled = function() {
    return ko.views.manager.currentView ? true : false;
}

viewManager.prototype.do_cmd_findNextResult = function() {
    FindResultsTab_NextResult();
}

// cmd_findNextFunction, cmd_findPreviousFunction, cmd_findAllFunctions

// Auxiliary function used by the find*Function(s) methods.
//
//  "searchType" is one of "next", "previous" or "all"
//
viewManager.prototype._findFunction = function(searchType) {
    try {
        var language = ko.views.manager.currentView.document.languageObj;
        var re = language.namedBlockRE;
        var namedBlockDescription = language.namedBlockDescription;
        if (re == null || re == '')
            return;

        var findSvc = Components.classes["@activestate.com/koFindService;1"].
                      getService(Components.interfaces.koIFindService);
        var patternType, caseSensitivity, searchBackward, matchWord;
        patternType = findSvc.options.patternType;
        caseSensitivity = findSvc.options.caseSensitivity;
        searchBackward = findSvc.options.searchBackward;
        matchWord = findSvc.options.matchWord;

        findSvc.options.patternType = findSvc.options.FOT_REGEX_PYTHON;
        findSvc.options.caseSensitivity = findSvc.options.FOT_SENSITIVE;
        if (searchType == "previous") {
            findSvc.options.searchBackward = 1;
        } else {
            findSvc.options.searchBackward = 0;
        }
        findSvc.options.matchWord = 0;

        var context = Components.classes["@activestate.com/koFindContext;1"]
                      .createInstance(Components.interfaces.koIFindContext);
        context.type = Components.interfaces.koIFindContext.FCT_CURRENT_DOC;
        context.name = _bundle.GetStringFromName("theCurrentDocument.name");
        if (searchType == "all") {
            Find_FindAll(window, context, re, namedBlockDescription);
        } else {
            Find_FindNext(window, context, re);
        }
        findSvc.options.patternType = patternType;
        findSvc.options.caseSensitivity = caseSensitivity;
        findSvc.options.searchBackward = searchBackward;
        findSvc.options.matchWord = matchWord;
    }  catch (e) {
        this.log.error(e);
    }
}

viewManager.prototype.is_cmd_findNextFunction_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_findNextFunction_enabled = function() {
    var view = ko.views.manager.currentView;
    return view != null && view.document && view.document.languageObj.namedBlockRE != '';
}

viewManager.prototype.do_cmd_findNextFunction = function() {
    this._findFunction("next");
}

viewManager.prototype.is_cmd_findPreviousFunction_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_findPreviousFunction_enabled = function() {
    var view = ko.views.manager.currentView;
    return view != null && view.document && view.document.languageObj.namedBlockRE != '';
}

viewManager.prototype.do_cmd_findPreviousFunction = function() {
    this._findFunction("previous");
}

viewManager.prototype.is_cmd_findAllFunctions_supported = function() {
    return true;
}

viewManager.prototype.is_cmd_findAllFunctions_enabled = function() {
    var view = ko.views.manager.currentView;
    return view != null && view.document && view.document.languageObj.namedBlockRE != '';
}

viewManager.prototype.do_cmd_findAllFunctions = function() {
    this._findFunction("all");
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
    function parseLine(line) {
        // Return [sign, num] for the given line string.
        //   42     sign=null, num=42
        //   +1     sign=+, num=1
        //   a      sign=null, num=NaN
        var stripped = line.replace(/(^\s*|\s*$)/g, '');
        var sign = null, num;
        if (stripped[0] == "-" || stripped[0] == "+") {
            sign = stripped[0];
            num = parseInt(stripped.substring(1, stripped.length));
        } else {
            sign = null;
            num = parseInt(stripped);
        }
        //dump("parseLine(line="+line+"): sign="+sign+", num="+num+"\n");
        return [sign, num];
    }

    function validateLine(window, line) {
        // Good: 1, 42, +12, -5. Bad: a, +1a, -, 3.14
        var parsed = parseLine(line);
        var sign = parsed[0];
        var num = parsed[1];
        //dump("validateLine(line="+line+"): sign="+sign+", num="+num+"\n");
        if (isNaN(num) || num < 0) {
            window.alert(_bundle.formatStringFromName("isInvalidYoumustEnterANumber.alert", [line], 1));
            return false;
        }
        return true;
    }

    // Prompt for the line.
    var view = ko.views.manager.currentView;
    var line = ko.dialogs.prompt(
            // prompt
            _bundle.GetStringFromName("enterALineNumberToGoToPrefix.prompt"),
            _bundle.GetStringFromName("enterLineNumber.prompt"), // label
            null, // value
            _bundle.GetStringFromName("goToLine.prompt"), // title
            // mruName: Don't use one because this tends to gobble up one
            // <Enter> keypress, which is annoying more than the MRU is
            // potentially useful. Use the following to get per-file-mru:
            //      "goto_line_"+view.document.displayPath,
            null,
            validateLine) //validator

    if (line == null)
        return;  // dialog cancelled

    // Go to the given line.
    var parsed = parseLine(line);
    var sign = parsed[0];
    var num = parsed[1];
    var scimoz = view.scintilla.scimoz;
    var currLine;
    var targetLine;
    switch (sign) {
    case null:
        scimoz.gotoLine(num-1);  // scimoz handles out of bounds
        targetLine = num - 1;
        break;
    case "+":
        currLine = scimoz.lineFromPosition(scimoz.currentPos);
        targetLine = currLine + num;
        break;
    case "-":
        currLine = scimoz.lineFromPosition(scimoz.currentPos);
        targetLine = currLine - num;
        break;
    default:
        log.error("unexpected goto line 'sign' value: '"+sign+"'")
        targetLine = null;
        break;
    }
    if (targetLine != null) {
        scimoz.gotoLine(targetLine);
        scimoz.ensureVisible(targetLine);
        scimoz.scrollCaret();
    }
}

// cmd_goToDefinition
viewManager.prototype.is_cmd_goToDefinition_enabled = function() {
    if (!gCodeIntelActive) return false;
    var view = ko.views.manager.currentView;
    return (view && view.scimoz && view.document &&
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
    var trg = view.document.ciBuf.defn_trg_from_pos(view.scimoz.currentPos);
    if (!trg) {
        // Do nothing.
    } else {
        // We do it asynchronously
        var ctlr = Components.classes["@activestate.com/koCodeIntelEvalController;1"].
                    createInstance(Components.interfaces.koICodeIntelEvalController);
        ctlr.set_ui_handler(view.ciCompletionUIHandler);
        view.document.ciBuf.async_eval_at_trg(trg, ctlr);
    }
}

// cmd_save
viewManager.prototype.is_cmd_save_supported = function() {
    return this.currentView != null && typeof(this.currentView.save) != 'undefined';
}

viewManager.prototype.is_cmd_save_enabled = function() {
    return this.currentView && this.currentView.document && this.currentView.document.isDirty;
}


viewManager.prototype.do_cmd_save = function() {
    this.currentView.save();
}


// cmd_revert
viewManager.prototype.is_cmd_revert_supported = function() {
    return this.currentView != null && typeof(this.currentView.revert) != 'undefined';
}

viewManager.prototype.is_cmd_revert_enabled = function() {
    return this.currentView && this.currentView.document && this.currentView.document.isDirty;
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
        var views = this.topView.getViews(true);
        var i, view;
        this.log.info("length of views is: " + views.length);
        for (i = views.length-1; i >= 0; i--) {
            view = views[i];
            if (view.document && view.document.isDirty) {
                view.save(); // we'll ignore return values here.
            }
        }

        // Save the toolbox data
        try {
            ko.toolboxes.user.save();
        } catch(ex) {
            ko.dialogs.alert(_bundle.GetStringFromName("thereWasAnErrorSavingTheToolbox.alert"),
                         _lastErrorSvc.getLastErrorMessage(),
                         _bundle.GetStringFromName("toolboxSaveError.alert"));
        }

        // Save all dirty projects
        var projects = ko.projects.manager.getDirtyProjects();
        for (i = 0; i < projects.length; i++) {
            ko.projects.manager.saveProject(projects[i]);
        }

        // save workspace
        ko.workspace.saveWorkspace();
    } catch(ex) {
        this.log.exception(ex, "Error in do_cmd_saveAll");
    }
}


// cmd_saveAs
viewManager.prototype.is_cmd_saveAs_supported = function() {
    return this.currentView != null && typeof(this.currentView.saveAs) != 'undefined';
}

viewManager.prototype.is_cmd_saveAs_enabled = function() {
    return (this.currentView && this.currentView.document &&
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
    return (this.currentView && this.currentView.document &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_saveAs_remote = function() {
    this.currentView.saveAsRemote();
}

// cmd_open_remote
viewManager.prototype.do_cmd_open_remote = function() {
    if (this.currentView && this.currentView.document &&
        this.currentView.getAttribute('type') == 'editor') {
        // Open with specific location of current file if possible
        this.currentView.openRemote();
    } else {
        // Open with the default location
        ko.filepicker.openRemoteFiles();
    }
}

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
    return (this.currentView && this.currentView.document &&
        this.topView.canSplitView(this.currentView));
}

viewManager.prototype.do_cmd_splittab = function() {
    this.topView.splitView(this.currentView);
}

// cmd_movetab
viewManager.prototype.is_cmd_movetab_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_movetab_enabled = function() {
    return this._viewCount > 1 &&
        this.currentView && this.currentView.document &&
        this.topView.canMoveView(this.currentView);
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
    ko.launch.newWindow(this.currentView.document.file.URI);
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
    var uri = this.currentView.document.file.URI;
    if (!this.currentView.close()) {
        return;
    }
    ko.launch.newWindow(uri);
}

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
        log.exception(e);
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
        log.exception(e);
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
    var sm = this.currentView.scimoz
    if (sm.callTipActive()) {
        sm.callTipCancel()
    } else if (sm.autoCActive()) {
        sm.autoCCancel()
    } else {
        Find_HighlightClearAll(sm);
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
    ko.printing.print(this.currentView, 0, 0);
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
    ko.printing.print(this.currentView, false, false, true);
}

viewManager.prototype.is_cmd_printPreview_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_printPreview_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_printPreview = function() {
    ko.printing.printPreview(this.currentView, 1, 0);
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
    ko.printing.printPreview(this.currentView, 1, 0, 1);
}

viewManager.prototype.is_cmd_exportHTML_supported = function() {
    return 1;
}

viewManager.prototype.is_cmd_exportHTML_enabled = function() {
    return (this.currentView &&
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_exportHTML = function() {
    ko.printing.print(this.currentView, 0, 1);
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
    ko.printing.print(this.currentView, false, true, true);
}

viewManager.prototype.do_ViewAs = function(language) {
    this.currentView.document.language = language;
    // bug 34689  for some reason the above setter is not forcing a colourise.
    // we need to do this get get a relexing of the syntax colouring.  It is
    // better to do it here since this will only happen when the menu
    // "view->view as language" is used.
    this.currentView.scimoz.colourise(0,-1);
}

viewManager.prototype.is_cmd_editPrefsCurrent_enabled = function () {
    return this.currentView && this.currentView.getAttribute('type') == 'editor';
}
viewManager.prototype.do_cmd_editPrefsCurrent = function () {
    ko.projects.fileProperties(null, this.currentView, false);
}

viewManager.prototype.is_cmd_createMappedURI_enabled = function () { 
    return this.currentView && this.currentView.getAttribute('type') == 'editor' &&
        this.currentView.document && this.currentView.document.file;
}
viewManager.prototype.do_cmd_createMappedURI = function () {
    if (this.currentView.document.file.isLocal) {
        ko.uriparse.addMappedURI(null, this.currentView.document.file.path);
    } else {
        var uri = this.currentView.document.file.URI;
        ko.uriparse.addMappedURI(uri, null);
    }
}
viewManager.prototype.is_cmd_saveAsTemplate_enabled = function () {
    return this.currentView && this.currentView.getAttribute('type') == 'editor';
}
viewManager.prototype.do_cmd_saveAsTemplate = function () {
    try {
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var templateSvc = Components.classes["@activestate.com/koTemplateService?type=file;1"].getService();
        //TODO: The directory name "My Templates" should be localized
        var dname = os.path.join(templateSvc.getUserTemplatesDir(), "My Templates");
        var templatename = ko.filepicker.saveFile(dname,
                                this.currentView.document.baseName);
        if (!templatename) return;
        var docsvc = Components.classes['@activestate.com/koDocumentService;1']
                    .getService(Components.interfaces.koIDocumentService);
        var doc = docsvc.createDocumentFromURI(ko.uriparse.localPathToURI(templatename));
        doc.buffer = this.currentView.document.buffer;
        doc.encoding = this.currentView.document.encoding;
        doc.save(0);
    } catch(ex) {
        this.log.exception(ex, "Error saving the current view as a template.");
    }
}

this.viewManager = viewManager;

var _manager = null;
var _gCheckFilesObserver = null;

/**
 * Get the view manager.
 * @type ko.views.viewManager
 *
 */
this.__defineGetter__("manager",
function()
{
    return _manager;
});

this.onload = function views_onload() {
    _manager = new viewManager();
    var viewSvc = Components.classes['@activestate.com/koViewService;1'].getService(
                    Components.interfaces.koIViewService);
    viewSvc.setViewMgr(_manager);

// #if PLATFORM == "linux"
    if (window == ko.windowManager.getMainWindow())
        window.addEventListener("focus", ko.window.checkDiskFiles, false);
// #else
    function _checkFilesObserver() {
        var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                        getService(Components.interfaces.nsIObserverService);
        observerSvc.addObserver(this, "application-activated",false);

        var me = this;
        this.removeListener = function() { me.finalize(); }
        window.addEventListener("unload", this.removeListener, false);
    };
    _checkFilesObserver.prototype = {
        finalize: function() {
            if (!this.removeListener) return;
            window.removeEventListener("unload", this.removeListener, false);
            this.removeListener = null;
            var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                            getService(Components.interfaces.nsIObserverService);
            observerSvc.removeObserver(this, "application-activated");
        },
        observe: function(subject, topic, data)
        {
            if (topic == 'application-activated'){
                var activated = subject.QueryInterface(Components.interfaces.nsISupportsPRBool).data;
                if (activated) {
                    ko.window.checkDiskFiles();
                }
            }
        }
    }
    _gCheckFilesObserver = new _checkFilesObserver();
// #endif
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
    var onModifiedHandler = view.onModifiedHandler;
    view.onModifiedHandler = ko.views.nullOnModifiedHandler;
    try {
        func();
    } finally {
        view.onModifiedHandler = onModifiedHandler;
    }
};


/**
 * Shared code that returns a label and tooltip based on the supplied view,
 * suitable for a menuitem.  
 * @param {Object(koIScintillaView)} view
 * @param {Number} lineNo - one-based line number
 * @param {Boolean} showDirty - put a "*" in the label if the view's document is dirty
 * @returns {Array} returns two values: the label and a suggested tooltip.
 *             If no label can be calculated, both items are null.
 */
this.labelsFromView = function(view,
                               lineNo, /*=null*/
                               showDirty /* false */
                               ) {
    if (typeof(lineNo) == "undefined") {
        lineNo = null;
    }
    if (typeof(showDirty) == "undefined") {
        showDirty = false;
    }
    var label = null, tooltip = null;
    if (view.document) {
        // Example:
        //  "C:\trentm\tmp\foo.py" -> "foo.py (C:\trentm\tmp)"
        var doc = view.document;
        var path = tooltip = doc.displayPath;
        var idx = path.lastIndexOf("/");
        if (idx == -1) {
            idx = path.lastIndexOf("\\");
        }
        var dir = null;
        var label;
        if (idx != -1) {
            dir = path.substring(0, idx);
            label = path.substring(idx+1);  // basename
        } else {
            label = path;
        }
        if (lineNo != null) {
            label += ":" + lineNo;
        }
        if (showDirty && doc.isDirty) {
            label += " *";
        }
        if (dir) {
            label += " (" + dir + ")";
        }
    }
    return [label, tooltip];
};

}).apply(ko.views);

if (typeof(ko.workspace) == "undefined") {
    ko.workspace = {};
}
(function() {

var _restoreInProgress = false;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/views.properties");

this.restoreInProgress = function() {
    return _restoreInProgress;
}
const multiWindowWorkspacePrefName = "windowWorkspace";
const _mozPersistPositionDoesNotWork = 
// #if PLATFORM == 'win' or PLATFORM == 'darwin'
false;
// #else
true;
// #endif
/**
 * restore all workspace preferences and state, open files and projects
 */
this.restoreWorkspace = function view_restoreWorkspace(currentWindow)
{
    if (typeof(currentWindow) == "undefined") {
        // Get the window that's executing, and use that.
        currentWindow = ko.windowManager.getMainWindow();
    }
    var infoSvc = Components.classes["@activestate.com/koInfoService;1"].getService();
    if (infoSvc.nonInteractiveMode) return;

    if ((!gPrefs.hasPref(multiWindowWorkspacePrefName)
         && !gPrefs.hasPref('workspace'))
        || ko.dialogs.yesNo(_bundle.GetStringFromName("doYouWantToOpenRecentFilesAndProjects.prompt"),
                            null, null, null, "restore_workspace") == "No")
    {
        return;
    }
    if (!gPrefs.hasPref(multiWindowWorkspacePrefName)) {
        this._restoreWindowWorkspace(gPrefs.getPref('workspace'), currentWindow, _mozPersistPositionDoesNotWork);
        setTimeout(ko.uilayout.restoreTabSelections, 10, gPrefs);
        return;
    }
    // Restore the first workspace directly, and restore other
    // workspaces indirectly each new window's init routine in ko.main
    
    var windowWorkspacePref = gPrefs.getPref(multiWindowWorkspacePrefName);
    var checkWindowBounds = _mozPersistPositionDoesNotWork || windowWorkspacePref.hasPref(1);
    this._restoreWindowWorkspace(windowWorkspacePref.getPref(0), currentWindow, checkWindowBounds);
    if (windowWorkspacePref.hasPref(1)) {
        ko.launch.newWindowFromWorkspace(1);
    }
};

this.restoreWorkspaceByIndex = function(currentWindow, idx)
{
    if (!gPrefs.hasPref(multiWindowWorkspacePrefName)) {
        ko.dialogs.alert("Internal error: \n"
                         + "ko.workspace.restoreWorkspaceByIndex invoked (index="
                         + idx
                         + "),\n"
                         + "but there's no windowWorkspace pref\n");
        return;
    }
    idx = parseInt(idx);
    var windowWorkspacePref = gPrefs.getPref('windowWorkspace');
    try {
        this._restoreWindowWorkspace(windowWorkspacePref.getPref(idx), currentWindow, idx > 0 || _mozPersistPositionDoesNotWork);
    } catch(ex) {
        log.exception("Can't restore workspace for window " + idx);
    }
    var windowWorkspacePref = gPrefs.getPref(multiWindowWorkspacePrefName);
    if (windowWorkspacePref.hasPref(idx + 1)) {
        ko.launch.newWindowFromWorkspace(idx + 1);
    } else {
        _restoreFocusToMainWindow();
    }
};

function _restoreFocusToMainWindow() {
    var windows = ko.windowManager.getWindows();
    for (var i = 0; i < windows.length; i++) {
        var w = windows[i];
        if (w.ko._hasFocus) {
            w.focus();
            delete w.ko._hasFocus;
            return;
        }
    }
}

// Bug 80604 -- screenX and screenY values like -32000 can occur.
// Generalize it: if we fall behind or in front of some threshold,
// return the acceptable min/max value.
function _checkWindowCoordinateBounds(candidateValue,
                            minAcceptableThreshold, minAcceptable,
                            maxAcceptableThreshold, maxAcceptable) {
    if (candidateValue < minAcceptableThreshold) {
        return Math.round(minAcceptable);
    }
    if (candidateValue > maxAcceptableThreshold) {
        return Math.round(maxAcceptable);
    }
    return candidateValue;
}
const _nsIDOMChromeWindow = Components.interfaces.nsIDOMChromeWindow;
this._restoreWindowWorkspace = function(workspace, currentWindow, checkWindowBounds)
{
    _restoreInProgress = true;
    try {
        var wko = currentWindow.ko;
        var cnt = new Object();
        var ids = new Object();
        var id, elt, pref;
        if (checkWindowBounds && workspace.hasPref('coordinates')) {
            var coordinates = workspace.getPref('coordinates');
            var windowState = (coordinates.hasPrefHere('windowState')
                               ? coordinates.getLongPref('windowState')
                               : _nsIDOMChromeWindow.STATE_NORMAL);
            // If it's minimized or maximized we still need to set the
            // window's coords for when it's restored.
            var screenHeight = window.screen.availHeight;
            var screenWidth = window.screen.availWidth;
            var screenX = coordinates.getLongPref('screenX');
            var screenY = coordinates.getLongPref('screenY');
            var outerHeight = coordinates.getLongPref('outerHeight');
            var outerWidth = coordinates.getLongPref('outerWidth');
            if (Math.abs(screenX) > 3 * screenWidth
                || Math.abs(screenY) > 3 * screenHeight) {
                screenX = screenY = 0;
            }
            if (currentWindow.screenX != screenX
                || currentWindow.screenY != screenY) {
                currentWindow.moveTo(screenX, screenY);
            }
            if (currentWindow.outerHeight != outerHeight
                || currentWindow.outerWidth != outerWidth) {
                var newHeight = _checkWindowCoordinateBounds(
                    outerHeight,
                    0, .2 * screenHeight,
                    screenHeight, .9 * screenHeight);
                var newWidth = _checkWindowCoordinateBounds(
                    outerWidth,
                    0, .2 * screenWidth,
                    screenWidth, .9 * screenWidth);
                currentWindow.resizeTo(newWidth, newHeight);
            }
            if (windowState == _nsIDOMChromeWindow.STATE_MINIMIZED) {
                currentWindow.minimize();
            } else if (windowState == _nsIDOMChromeWindow.STATE_MAXIMIZED) {
                currentWindow.maximize();
            }
        }
        if (workspace.hasPref('opened_projects')) {
            pref = workspace.getPref('opened_projects');
            wko.projects.manager.setState(pref);
            if (workspace.hasPref('current_project')) {
                var url = workspace.getStringPref('current_project');
                // If a project with that url is loaded, make it current
                var proj = wko.projects.manager.getProjectByURL(url);
                if (proj) {
                    wko.projects.manager.currentProject = proj;
                }
            }
        }
        workspace.getPrefIds(ids, cnt);
        for (var i = 0; i < ids.value.length; i++) {
            id = ids.value[i];
            elt = currentWindow.document.getElementById(id);
            if (elt) {
                pref = workspace.getPref(id);
                elt.setState(pref);
            }
        }
        if (workspace.hasPref('uilayout_bottomTabBoxSelectedTabId')) {
            setTimeout(wko.uilayout.restoreTabSelections, 10, workspace);
        }
        wko._hasFocus = (workspace.hasBooleanPref('hasFocus')
                         && workspace.getBooleanPref('hasFocus'));
        var infoService = Components.classes["@activestate.com/koInfoService;1"].
                            getService(Components.interfaces.koIInfoService);
        if (workspace.hasPref('windowNum')) {
            var windowNum = workspace.getLongPref('windowNum');
            currentWindow._koNum = windowNum;
            try {
                infoService.setUsedWindowNum(windowNum);
            } catch(ex) {
                // It turns out that the window # saved in the old workspace
                // has already been assigned.
                currentWindow._koNum = infoService.nextWindowNum();
            }
        } else {
            currentWindow._koNum = infoService.nextWindowNum();
        } 
    } catch(ex) {
        log.exception(ex, "Error restoring workspace:");
    }
    _restoreInProgress = false;
};

/*XXX: At some point remove these prefs from the global prefset:
 * uilayout_bottomTabBoxSelectedTabId
 * uilayout_leftTabBoxSelectedTabId
 * uilayout_rightTabBoxSelectedTabId
 */

/**
 * save all workspace preferences and state
 */
this.saveWorkspace = function view_saveWorkspace()
{
    // Ask each major component to serialize itself to a pref.
    try {
        var mainWindow = ko.windowManager.getMainWindow();
        var windows = ko.windowManager.getWindows();
        var windowWorkspace = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
        gPrefs.setPref(multiWindowWorkspacePrefName, windowWorkspace);
        var saveCoordinates = _mozPersistPositionDoesNotWork || windows.length > 1;
        for (var thisWindow, idx = 0; thisWindow = windows[idx]; idx++) {
            var workspace = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
            windowWorkspace.setPref(idx, workspace);
            if (saveCoordinates) {
                var coordinates = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
                workspace.setPref('coordinates', coordinates);
                coordinates.setLongPref('windowState', thisWindow.windowState);
                var docElement = thisWindow.document.documentElement;
                coordinates.setLongPref('screenX', docElement.getAttribute('screenX'));
                coordinates.setLongPref('screenY', docElement.getAttribute('screenY'));
                coordinates.setLongPref('outerHeight', docElement.height);
                coordinates.setLongPref('outerWidth', docElement.width);
            }
            if (thisWindow == mainWindow) {
                workspace.setBooleanPref('hasFocus', true);
            }
            var wko = thisWindow.ko;
            var pref = wko.projects.manager.getState();
            if (pref) {
                workspace.setPref(pref.id, pref);
                var currentProject = wko.projects.manager.currentProject;
                if (currentProject) {
                    workspace.setStringPref('current_project', currentProject.url);
                }
            }
            var ids = ['topview'];
            var i, elt, id, pref;
            for (i = 0; i < ids.length; i++) {
                id = ids[i];
                elt = thisWindow.document.getElementById(id);
                if (!elt) {
                    alert(_bundle.formatStringFromName("couldNotFind.alert", [id], 1) );
                }
                pref = elt.getState();
                if (pref) {
                    pref.id = id;
                    workspace.setPref(id, pref);
                }
            }
            wko.uilayout.saveTabSelections(workspace);
            workspace.setLongPref('windowNum', thisWindow._koNum);
        }
        // Save prefs
        gPrefSvc.saveState();
    } catch (e) {
        log.exception(e,"Error saving workspace: ");
    }
}

}).apply(ko.workspace);


ko.window = {};
(function() {
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/views.properties");

/**
 * File Status Service used by the function(s) below.
 * @private
 */
var _fileStatusSvc = Components.classes["@activestate.com/koFileStatusService;1"].
                    getService(Components.interfaces.koIFileStatusService);
/**
 * Asyncronous operations service used by the function(s) below.
 * @private
 */
var _asyncSvc = Components.classes['@activestate.com/koAsyncService;1'].
                getService(Components.interfaces.koIAsyncService);

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
    try {
        var commandDispatcher = top.document.commandDispatcher
        var focusedElement = commandDispatcher.focusedElement;
        if (!focusedElement) return null;
        if (focusedElement.tagName == 'xul:scintilla') return focusedElement;
        if (focusedElement.tagName == 'html:embed' &&
            focusedElement.parentNode.tagName == 'xul:scintilla') return focusedElement.parentNode;
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

    var checkDisk = (gPrefs.hasBooleanPref("checkDiskFile") &&
                     gPrefs.getBooleanPref("checkDiskFile"));
    if (!checkDisk) return true;
    _gInCheckDiskFiles = true;
    log.info('Checking Disk Files');
    window.setTimeout(_view_checkDiskFiles,1);
    return true;
}

function _view_checkDiskFiles(event) {
    // checks open files and projects for dirtiness
    var obSvc = Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
    try {
        window.updateCommands('clipboard');
        var changedItems = [];
        var removedItems = [];
        var viewsToReload;
        var conflictedItems = [];
        var view, url, i, j, hasChanged;
        var views, file, prompt, title, item, items;

        // Deal with views first
        views = ko.views.manager.topView.getDocumentViewList(true);
        for (i = 0; i < views.length; i++) {
            view = views[i];
            // browser views do not load via document, so will
            // always be wrong when checking hasChanged
            if (view.getAttribute('type')!='editor') continue;
            if (typeof(view.document) == 'undefined' ||
                !view.document ||
                view.document.isUntitled) continue;
            file = view.document.file;
            // onFocus: Don't check file changed for remote files
            if (!file.isLocal) continue;
            item = new Object;
            item.type = 'view';
            item.view = view;
            item.file = file;
            if (!file.exists) {
                removedItems.push(item);
                view.document.isDirty = true;
            } else {
                if (view.document.differentOnDisk() &&
                    // If this is has a pending operation, the view will be
                    // updated automatically when the command finishes, we
                    // don't want to warn about it until it's finished. See bug:
                    // http://bugs.activestate.com/show_bug.cgi?id=74471
                    !_asyncSvc.uriHasPendingOperation(file.URI)) {

                    if (view.document.isDirty) {
                        conflictedItems.push(item);
                    } else {
                        changedItems.push(item);
                    }
                    view.document.isDirty = true;
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
                // Force a file stat update by calling hasChanged, this is so
                // the file.exists check made below will still work correctly.
                file.hasChanged;
                item = new Object;
                item.type = 'project';
                item.project = projects[i];
                item.file = file;
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
            title = _bundle.GetStringFromName("reloadChangedFilesAndProjects.prompt");
            prompt = _bundle.GetStringFromName("someOpenFilesAndOrProjectsHaveChanged.prompt");
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
                        if (gCodeIntelActive) {
                            gCodeIntelSvc.scan_document(
                                items[i].view.document,
                                // linesAdded: using non-zero value to
                                // encourage high-prio rescan
                                1,
                                true);
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
                    removedItems[i].view.document) {
                    removedItems[i].view.document.isDirty = true;
                }
            }
            title = _bundle.GetStringFromName("closeDeletedFilesAndProjects.prompt");
            prompt = _bundle.GetStringFromName("theFollowingFilesAndProjectsDeleted.prompt");
            items = ko.dialogs.selectFromList(title,
                                          prompt,
                                          removedItems,
                                          'zero-or-more',
                                          _itemStringifier,
                                          'close_deleted_files');
            if (items != null && items.length > 0) {
                for (i = 0; i < items.length; i++) {
                    if (item.type == 'view') {
                        items[i].view.close()
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
            prompt = _bundle.GetStringFromName("theFollowingFilesHaveChangedOnDisk.prompt");
            title = _bundle.GetStringFromName("modifiedFilesHaveChangedOnDisk.prompt");
            var text = '';
            for (i = 0; i < conflictedItems.length; i++) {
                text += _itemStringifier(conflictedItems[i]) + '\n'
            }
            ko.dialogs.alert(prompt, text, title, "buffer_conflicts_with_file_on_disk")
        }

        // XXX now follow up with the toolboxes
        if (ko.toolboxes.user) {
            ko.toolboxes.user.verifyUnchanged();
        }
    } catch(e) {
        log.exception(e);
    }
    _fileStatusSvc.updateStatusForAllFiles(REASON_ONFOCUS_CHECK);
    // when we leave this function, if any dialogs were shown, the
    // main window gets a focus event again.  So we want to wait long
    // enough so that the new focus event does not enter this function
    // again. (bug 29037)
    window.setTimeout(function() { _gInCheckDiskFiles = false; }, 100);
    return true;
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
        view.document.file &&
        view.document.file.isLocal) {
        return view.cwd;
    } else {
        var userEnvSvc = Components.classes['@activestate.com/koUserEnviron;1'].
                         getService(Components.interfaces.koIUserEnviron);
        if (userEnvSvc.has("HOME")) {
            return userEnvSvc.get("HOME");
        } else {
// #if PLATFORM == "win"
            return "C:\\";
// #else
            return "/";
// #endif
        }
    }
}

}).apply(ko.window);



// backwards compatibility api's
var gEditorTooltipHandler = xtk.domutils.tooltips.getHandler('editorTooltip');
var view_openFilesWithPicker = ko.open.filePicker;
var view_openTemplatesWithPicker = ko.open.templatePicker;
var view_elementHasFocus = xtk.domutils.elementInFocus;
var view_restoreWorkspace = ko.workspace.restoreWorkspace;
var view_saveWorkspace = ko.workspace.saveWorkspace;
var view_focusedScintilla = ko.window.focusedScintilla;
var view_focusedView = ko.window.focusedView;
var view_checkDiskFiles = ko.window.checkDiskFiles;
var View_GetCwd = ko.window.getCwd;
function view_getFocusedProjectView() { return ko.projects.getFocusedProjectView(); }

__defineGetter__("gViewMgr",
function()
{
    ko.views.manager.log.warn("gViewMgr is deprecated, use ko.views.manager");
    return ko.views.manager;
});
