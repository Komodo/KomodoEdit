/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
    ko.main.addCanQuitHandler(this.canClose, this);
    ko.main.addWillQuitHandler(this.postCanClose, this);
    ko.main.addUnloadHandler(this.shutdown, this);
    this.docSvc = Components.classes['@activestate.com/koDocumentService;1']
                    .getService(Components.interfaces.koIDocumentService);
    this.observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    this.lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                            getService(Components.interfaces.koILastErrorService);
    this.observerSvc.addObserver(this, "open_file", false); // commandment
    this.observerSvc.addObserver(this, "SciMoz:FileDrop", false);
    this.observerSvc.addObserver(this, "view_opened", false);
    this.observerSvc.addObserver(this, "view_closed", false);
    this.observerSvc.addObserver(this, "current_view_changed", false);
    this.observerSvc.addObserver(this, "file_status", false);
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
        this.observerSvc.removeObserver(this, "open_file");  // commandment
        this.observerSvc.removeObserver(this, "SciMoz:FileDrop");
        this.observerSvc.removeObserver(this, "view_opened");
        this.observerSvc.removeObserver(this, "view_closed");
        this.observerSvc.removeObserver(this, "current_view_changed");
        this.observerSvc.removeObserver(this, "file_status");
    } catch(e) {
        /* moz probably already removed them */
        log.warn('possible error shutting down viewManager:'+e);
    }
    this.docSvc = null;
    this.observerSvc = null;
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
 * @param project {koIProject} optional, instance of a project
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
 * @param project {koIProject} optional, instance of a project
 * @return {koIView} the buffer view that is opened
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
 * create a new file based on a template, optionally add it to a
 * project
 *
 * @public
 * @param uri {string} optional, uri pointing to a template file
 * @param saveto {string} optional, where to save the new file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {koIViewList} optional, what pane to open the buffer in
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.doFileNewFromTemplate = function(uri,
                                                       saveto  /*=null*/,
                                                       viewType /*="editor"*/,
                                                       viewList /*=null*/)
{
    this.log.info("doing doFileNewFromTemplate: ");
    if (typeof(viewType) == "undefined" || viewType == null) viewType = "editor";
    if (typeof(viewList) == "undefined") viewList = null;
    if (typeof(saveto) == "undefined") saveto = null;

    var lastErrorSvc = Components.classes['@activestate.com/koLastErrorService;1'].getService();
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
    var doc = this.docSvc.createDocumentFromURI(uri);
    try {
        doc.load();
    } catch (ex) {
        errmsg = lastErrorSvc.getLastErrorMessage();
        log.exception(ex, errmsg);
        ko.dialogs.internalError("Error opening template.",
                             "Error loading template '"+
                             uri+"'.\n\n"+ko.logging.getStack());
        return null;
    }
    var content = doc.buffer;
    var encodingName = doc.encoding.python_encoding_name;

    // Warn about backward in-compatibility in template codes.
    var pattern = /\[\s*komodo-variable: \$(\w+)\s*\]/;
    if (content.match(pattern)) {
        ko.dialogs.alert("It looks like this template is using Komodo's old "+
            "system of special template codes.  This mechanism is "+
            "deprecated and will be removed in the next version of Komodo.  "+
            "You should upgrade your templates to use the new, more "+
            "capable, mechanism (see 'Interpolation Shortcuts' in Help).",
            null, "Deprecated Template Codes", "old_template_codes");
        content = this.docSvc.deprecatedInterpolateTemplate(content);
    }

    // Interpolate any codes.
    var icontent = null;
    try {
        var istrings = ko.interpolate.interpolate(
                          window,
                          [], // codes are not bracketed
                          [content], // codes are bracketed
                          "Template '"+name+"' Query");
        icontent = istrings[0];
    } catch (ex) {
        var errno = lastErrorSvc.getLastErrorCode();
        if (errno == Components.results.NS_ERROR_ABORT) {
            // Command was cancelled.
        } else if (errno == Components.results.NS_ERROR_INVALID_ARG) {
            errmsg = lastErrorSvc.getLastErrorMessage();
            ko.dialogs.alert("Could not interpolate:" + errmsg);
        } else {
            log.exception(ex, "Error interpolating template.");
            ko.dialogs.internalError("Could not process interpolation codes "+
                                 "in template '"+basename+"'.",
                                 "Error interpolating template '"+
                                 uri+"'.\n\n"+ko.logging.getStack());
        }
        return null;
    }

    // Load the template.
    ko.mru.addURL("mruTemplateList", uri);
    if (saveto) {
        doc = this.docSvc.createNewDocumentFromTemplate(icontent, encodingName,
                                                        saveto, true);
    } else {
        doc = this.docSvc.createDocumentFromTemplate(icontent, encodingName,
                                                     name, ext);
    }
    var view;
    if (viewList) {
        view = viewList.createViewFromDocument(doc, viewType);
    } else {
        view = this.topView.createViewFromDocument(doc, viewType);
    }

    if (gCodeIntelActive) {
        // We delay launching the code browser for a little while to provide
        // a smoother file-opening experience. It's not a big deal that the
        // code browser gets populated a tad late.
        var osPath = Components.classes["@activestate.com/koOsPath;1"]
                     .createInstance(Components.interfaces.koIOsPath);
        window.setTimeout(
            function(codeIntelSvc, msg, uri, doc) {
                codeIntelSvc.ideEvent(msg, uri, doc);
            },
            500, gCodeIntelSvc, "opened_document",
            osPath.join("<Unsaved>", doc.displayPath), doc
        );
    }
    return view;
}


/**
 * create a new empty, unsaved buffer
 *
 * @public
 * @param language {string} optional, language of the buffer (eg. python)
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.doNewView = function(language /*= prefs.fileDefaultNew*/,
                                           viewType /*='editor'*/) {
    this.log.info("doing doNewView: ");
    ko.trace.get().enter('viewManager.doNewView');

    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(language)=='undefined' || !language) {
        language = gPrefs.getStringPref('fileDefaultNew');
    }

    // the following line is delayed to avoid notifications during load()
    var doc = this.docSvc.createUntitledDocument(language);
    var view = this.topView.createViewFromDocument(doc,viewType);

    if (gCodeIntelActive) {
        // We delay launching the code browser for a little while to provide
        // a smoother file-opening experience. It's not a big deal that the
        // code browser gets populated a tad late.
        var osPath = Components.classes["@activestate.com/koOsPath;1"]
                     .createInstance(Components.interfaces.koIOsPath);
        window.setTimeout(
            function(codeIntelSvc, msg, uri, doc) {
                codeIntelSvc.ideEvent(msg, uri, doc);
            },
            500, gCodeIntelSvc, "opened_document",
            osPath.join("<Unsaved>", doc.displayPath), doc
        );
    }

    ko.trace.get().leave('viewManager.doNewView');
    this.log.info("leaving doNewView");
    return view;
}

/**
 * Create a new buffer and open a file into it.
 * Note: The "uri" will *not* be translated by the mapped URI functionality.
 *
 * @public
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {koIViewList} optional, what pane to open the buffer in
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.newViewFromURI = function(uri, viewType/*='editor'*/, viewList/*=null*/)
{
    this.log.info("doing newViewFromURI: " + uri);
    ko.trace.get().enter('viewManager.newViewFromURI');
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(viewList)=='undefined')
        viewList = null;
    var doc = this.docSvc.createDocumentFromURI(uri);
    var view = null;
    if (! doc.file.exists) {
        if (ko.dialogs.yesNo("The file " + doc.file.displayPath +
                         " does not exist.  Do you want to create it?") == "No") {
            return null;
        } else {
            var sysUtils = Components.classes["@activestate.com/koSysUtils;1"]
                            .createInstance(Components.interfaces.koISysUtils);
            try {
                sysUtils.Touch(doc.file.displayPath);
            } catch(touch_ex) {
                ko.dialogs.alert('Komodo was unable to create the file: ' + doc.file.displayPath);
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
        ko.dialogs.alert('Komodo cannot open directories: ['+doc.file.path+']\n');
        return null;
    }
    try {
        if (doc.haveAutoSave() &&
            ko.dialogs.yesNo("It appears the file '"+doc.file.displayPath+
                        "' was not properly saved, would you "+
                        "like to restore the backup?", "Yes") == "Yes") {
            doc.restoreAutoSave();
        } else if (viewType != "browser") {
            doc.load();
        }
        // the following line is delayed to avoid notifications during load()
        if (viewList) {
            view = viewList.createViewFromDocument(doc,viewType);
        } else {
            view = this.topView.createViewFromDocument(doc,viewType);
        }
    } catch (e)  {
        var err = this.lastErrorSvc.getLastErrorMessage();
        ko.dialogs.alert('Komodo was unable to open the file: '+doc.file.baseName, err, 'File Open Error');
        this.log.exception(e);
        view = null;
    }
    try {
        if (gCodeIntelActive && view) {
            // We delay launching the code browser for a little while
            // to provide a smoother file-opening experience.  It's
            // not a big deal that the code browser gets populated a tad late.
            window.setTimeout(
                function(codeIntelSvc, msg, uri, doc) {
                    codeIntelSvc.ideEvent(msg, uri, doc);
                },
                500, gCodeIntelSvc, "opened_document", uri, doc
            );
        }
    } catch (e)  {
        this.log.exception(e);
    }

    ko.trace.get().leave('viewManager.newViewFromURI');
    this.log.info("leaving newViewFromURI");
    return view;
}

/**
 * open a file, if it is already open, then select that buffer, otherwise,
 * create a new buffer for the file.
 * Note: The "uri" will be translated using the mapped URI functionality.
 *
 * @public
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {koIViewList} optional, what pane to open the buffer in
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.doFileOpen = function(uri, viewType/*='editor'*/, viewList/*=null*/)
{
    if (typeof(viewList)=='undefined')
        viewList = null;
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (viewType == 'editor') {
        uri = ko.uriparse.getMappedURI(uri);
    }
    var views = this.topView.findViewsForURI(uri);
    if (views.length > 0) {
        if (views.indexOf(this.currentView) >= 0) {
            // this uses the correct view in a splitview
            this.currentView.makeCurrent();
            return this.currentView;
        }
        views[0].makeCurrent();
        return views[0];
    }
    return this.newViewFromURI(uri, viewType, viewList);
}

/**
 * open a file, if it is already open, then select that buffer, otherwise,
 * create a new buffer for the file.  Make the given line number visible.
 *
 * @public
 * @param uri {string} uri to file
 * @param lineno {integer} line number
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @param viewList {koIViewList} optional, what pane to open the buffer in
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.doFileOpenAtLine = function(uri, lineno, viewType/*='editor'*/, viewList/*=null*/) {
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    if (typeof(viewList)=='undefined')
        viewList = null;
    var v = this.doFileOpen(uri, viewType, viewList);
    if (v) {
        v.currentLine = lineno;
    }
    return v;
}

/**
 * get a reference to the buffer view for a uri
 *
 * @public
 * @param uri {string} uri to file
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.getViewForFile = function(uri) {
    var v = this.topView.findViewsForURI(uri);
    if (v.length > 0) return v[0];
    return null;
}

/**
 * get a reference to a new and unsaved buffer view
 *
 * @public
 * @param name {string} name of the buffer
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.getUntitledView = function(name) {
    try {
        var doc = this.docSvc.findDocumentByURI(name);
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
 * @param doc {koIDocument} the document object
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.getViewForDocument = function(doc) {
    return this.topView.findViewForDocument(doc);
}


/**
 * open a uri in a new view, bypassing any sanity checking on the uri
 * 
 * @public
 * @param uri {string} uri to file
 * @param viewType {string} optional, type of buffer to open, default "editor"
 * @return {koIView} the buffer view that is opened
 */
viewManager.prototype.loadViewFromURI = function(uri, viewType/*='editor'*/)
{
    this.log.info("doing loadViewFromURI: " + uri);
    ko.trace.get().enter('viewManager.loadViewFromURI');
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
    var doc = this.docSvc.createDocumentFromURI(uri);

    // the following line is delayed to avoid notifications during load()
    var view = this.topView.createViewFromDocument(doc,viewType);
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
    cache.sccSummary = null;
    cache.hasSelection = false;
    cache.isDirty = false;
    cache.canUndo = false;
    cache.canRedo = false;
    cache.canFold = false;
    cache.canDebug = false;
    cache.language = null;
    cache.canPreview = false;
    if (view) {
        cache.type = view.getAttribute('type');
        if (view.document) {
            cache.sccSummary = view.document.isUntitled?'':view.document.file.sccSummary;
            cache.hasSelection = view.selection != '';
            cache.isDirty = view.document.isDirty
            if (cache.type == 'editor') {
                cache.canUndo = view.scintilla.canUndo();
                cache.canRedo = view.scintilla.canRedo();
                cache.canPreview = view.document.file && view.document.file.isLocal;
            }
            if (view.document.languageObj) {
                cache.canFold = view.document.languageObj.foldable;
                cache.canDebug = true; // XXX view.document.languageObj.debuggable;
                cache.language = view.document.language;
            }
        }
    }
    return cache
}

viewManager.prototype.observe = function(subject, topic, data)
{
    this.log.debug("_ViewObserver: observed '"+topic+"' notification: data='"+data+"'\n");
    switch (topic) {
        case 'SciMoz:FileDrop':
        case 'open_file':
            try {
                this.log.info("got open_file notification: " + data);
                var uri;
                var fname = '';
                var anchorDesc = '';
                var currentPosDesc = '';
                var currentPos, anchor = 0;
                if (data.indexOf('\t') != -1) { // We have a selection specification
                    var parts = data.split('\t');
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
                                           topic + " notification: " + data);
                    }
                } else {
                    fname = data;
                }
                try {
                    uri = ko.uriparse.localPathToURI(fname);
                } catch(ex) {
                    // Maybe it is a URI already?
                    uri = fname;
                }
                ko.open.URI(uri); // dispatch to view, project, UI builder as necessary
                if (anchorDesc && currentPosDesc) {
                    // Are we using character index or line,column?
                    if (anchorDesc.indexOf(',') == -1) {
                        anchor = Number(anchor);
                    } else {
                        subparts = anchorDesc.split(',');
                        var anchorLine = Math.max(Number(subparts[0]) - 1,
                                                  0);
                        var anchorCol = Math.max(Number(subparts[1]) - 1,
                                                 0);
                        anchor = ko.views.manager.currentView.positionAtColumn(anchorLine,
                                             anchorCol);
                    }
                    if (currentPosDesc.indexOf(',') == -1) {
                        currentPos = Number(currentPos);
                    } else {
                        subparts = currentPosDesc.split(',')
                        var currentPosLine = Math.max(Number(subparts[0]) - 1,
                                                      0);
                        var currentPosCol = Math.max(Number(subparts[1]) - 1,
                                                     0);
                        currentPos = ko.views.manager.currentView.positionAtColumn(currentPosLine,
                                             currentPosCol);
                    }
                    // do gotoline first because it messes w/ current position and anchor.
                    var lineNo = ko.views.manager.currentView.scimoz.lineFromPosition(currentPos);
                    ko.views.manager.currentView.scimoz.gotoLine(Math.max(lineNo - 1, 0)); // scimoz is 0-indexed
                    ko.views.manager.currentView.anchor = anchor;
                    ko.views.manager.currentView.currentPos = currentPos;
                    // Force the main window to the forefront
                    ko.windowManager.getMainWindow().focus();
                }
                break;
            } catch (e) {
                this.log.exception(e);
            }
            break;
        case 'current_view_changed':
            // Update the currentView
            // This has to happen always since one can do ctrl+tab,ctrl+i, and that
            // needs to find the right view.
            this.currentView = subject;
            if (this.batchMode) {
                // break out early -- we don't want to update controllers at this point.
                break;
            }
            if (this.topView.viewhistory.inBufferSwitchingSession) {
                // break out early -- we don't want to update controllers at this point.
                break;
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
            if (update_editor_change || oldcache.sccSummary!= newcache.sccSummary) {
                window.setTimeout("window.updateCommands('SCC');", 1);
            }
            window.setTimeout("window.updateCommands('dirty');", 1);
            if (update_editor_change || oldcache.canUndo != newcache.canUndo ||
                oldcache.canRedo != newcache.canRedo) {
                window.setTimeout("window.updateCommands('undo');", 1);
            }
            if (update_editor_change || oldcache.language != newcache.language) {
                window.setTimeout("window.updateCommands('language_changed');", 1)
            }
            if (update_editor_change || oldcache.canDebug != newcache.canDebug) {
                window.setTimeout("window.updateCommands('debuggability_changed');", 1);
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
            break;
        case 'view_opened':
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
            break;
        case 'view_closed':
            this._viewCount--;
            this.log.info("_viewcount is " + this._viewCount);
            if (this._viewCount == 0) {
                this.log.info("sending event: 'some_files_open'");
                window.setTimeout("window.updateCommands('some_files_open');", 1);
            } else if (this._viewCount == 1) {
                // We've closed our second view
                window.setTimeout("window.updateCommands('second_view_open_close');", 1);
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
                        window.setTimeout("window.updateCommands('SCC');", 1);
                        // Ensure the cached information gets updated, so the
                        // SCC toolbars and menu are properly set. Fixes bug:
                        // http://bugs.activestate.com/show_bug.cgi?id=48417
                        this.lastviewcache = this.cacheCommandData(this.currentView);
                    }
                }
            }
            break;
    }
}

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
    if (this.currentView)
        this.currentView.close();
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

viewManager.prototype._doCloseAll = function() {
    // returns true if all views were closed.
    var views = this.topView.getDocumentViews(true);
    var i;
    for (i = views.length-1; i >= 0; i--) {
        // Exclude the Start Page from "Close All".
        //   http://bugs.activestate.com/Komodo/show_bug.cgi?id=27321
        if (views[i].getAttribute("type") == "startpage")
            continue;
        if (! views[i].close()) {
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
                                             skipProjects /* default is false */
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

    if (typeof(urls) == 'undefined') {
        urls = null;
    }
    if (typeof(title) == 'undefined') {
        title = "Save Modified Files?";
    }
    if (typeof(prompt) == 'undefined') {
        title = "Please select the files you wish to save";
    }
    if (typeof(doNotAskPref) == 'undefined') {
        doNotAskPref = null;
    }
    if (typeof(skipProjects) == 'undefined') {
        skipProjects = false;
    }

    var views = this.topView.getViews(true);
    var i, view, item, k;
    var dirtyItems = [];
    var sofar = {};
    for (i = 0; i < views.length; i++) {
        view = views[i];
        if (!view) continue;
        // Persist view state now, to not have to do it as part of onunload handling
        if (view.getAttribute('type') == 'editor') {
            try {
                view.saveState();
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
                if (! _elementInArray(view.document.file.URI, urls)) continue;
                // exclude if we've already got it!
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
                          ["Save", "Do Not Save", "Cancel"]);
    if (itemsToSave == null) return false; // canceled
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
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }
    var pattern = ko.mru.get("find-patternMru");
    if (pattern) {
        var context = Components.classes[
            "@activestate.com/koFindContext;1"]
            .createInstance(Components.interfaces.koIFindContext);
        context.type = findSvc.options.preferredContextType;
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
    if (findSvc == null) {
        findSvc = Components.classes["@activestate.com/koFindService;1"].
                  getService(Components.interfaces.koIFindService);
    }
    var pattern = ko.mru.get("find-patternMru");
    if (pattern) {
        var context = Components.classes["@activestate.com/koFindContext;1"]
                      .createInstance(Components.interfaces.koIFindContext);
        context.type = findSvc.options.preferredContextType;
        // go in the opposite direction from the current setting
        findSvc.options.searchBackward = !findSvc.options.searchBackward;
        Find_FindNext(window, context, pattern);
        // restore the direction setting
        findSvc.options.searchBackward = !findSvc.options.searchBackward;
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

        if (findSvc == null) {
            findSvc = Components.classes["@activestate.com/koFindService;1"].
                      getService(Components.interfaces.koIFindService);
        }
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
        context.name = "the current document";
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
            window.alert("'"+line+"' is invalid. You must enter a number, "+
                         "with an optional '+' or '-' prefix.");
            return false;
        }
        return true;
    }

    // Prompt for the line.
    var view = ko.views.manager.currentView;
    var line = ko.dialogs.prompt(
            // prompt
            "Enter a line number to go to. Prefix + or - to move relative "+
            "to the current line. For example: +4 will move forward 4 lines.",
            "Enter line number:", // label
            null, // value
            "Go To Line", // title
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
    switch (sign) {
    case null:
        scimoz.gotoLine(num-1);  // scimoz handles out of bounds
        break;
    case "+":
        currLine = scimoz.lineFromPosition(scimoz.currentPos);
        scimoz.gotoLine(currLine + num);
        break;
    case "-":
        currLine = scimoz.lineFromPosition(scimoz.currentPos);
        scimoz.gotoLine(currLine - num);
        break;
    default:
        log.error("unexpected goto line 'sign' value: '"+sign+"'")
        break;
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
            ko.dialogs.alert('There was an error saving the toolbox: ',
                         this.lastErrorSvc.getLastErrorMessage(),
                         'Toolbox Save Error');
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

// cmd_movetab
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
            this.currentView.getAttribute('type') == 'editor');
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
            this.currentView.getAttribute('type') == 'editor');
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
            this.currentView.getAttribute('type') == 'editor');
}

viewManager.prototype.do_cmd_exportHTMLSelection = function() {
    ko.printing.print(this.currentView, false, true, true);
}

viewManager.prototype.do_ViewAs = function(language) {
    this.currentView.document.language = language;
    // bug 34689  for some reason the above setter is not forcing a colourise.
    // we need to do this get get a relexing of the syntax colouring.  It is
    // better to do it here since this will only happen when the menu
    // "view->view as langauge" is used.
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
        var dname = os.path.join(templateSvc.getUserTemplatesDir(), 'My Templates');
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

}).apply(ko.views);

if (typeof(ko.workspace) == "undefined") {
    ko.workspace = {};
}
(function() {

var _restoreInProgress = false;
this.restoreInProgress = function() {
    return _restoreInProgress;
}

/**
 * restore all workspace preferences and state, open files and projects
 */
this.restoreWorkspace = function view_restoreWorkspace()
{
    try {
        var infoSvc = Components.classes["@activestate.com/koInfoService;1"].getService();
        if (infoSvc.nonInteractiveMode) return;

        if (gPrefs.hasPref('workspace') &&
            ko.dialogs.yesNo("Do you want to open recent files and projects?",
                         null, null, null, "restore_workspace") == "Yes")
        {
            _restoreInProgress = true;
            try {
                var workspace = gPrefs.getPref('workspace');
                var cnt = new Object();
                var ids = new Object();
                var id, elt;
                var pref;
                workspace.getPrefIds(ids, cnt);
                if (workspace.hasPref('opened_projects')) {
                    pref = workspace.getPref('opened_projects');
                    ko.projects.manager.setState(pref)
                }
                for (var i = 0; i < ids.value.length; i++) {
                    id = ids.value[i];
                    elt = document.getElementById(id);
                    if (elt) {
                        pref = workspace.getPref(id);
                        elt.setState(pref);
                    }
                }
            } catch(ex) {
                log.exception(ex, "Error restoring workspace:");
            }
            _restoreInProgress = false;
        }
        ko.main.addUnloadHandler(ko.workspace.saveWorkspace, this);
    } catch(ex) {
        log.exception(ex, "Error restoring workspace:");
    }
}

/**
 * save all workspace preferences and state
 */
this.saveWorkspace = function view_saveWorkspace()
{
    try {
        // Ask each major component to serialize itself to a pref.
        var workspace;
        if (gPrefs.hasPref('workspace')) {
            workspace = gPrefs.getPref('workspace');
        } else {
            workspace = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
            workspace.id = 'workspace';
        }
        var haveStateToPersist = false;
        var pref = ko.projects.manager.getState()
        if (pref) {
            workspace.setPref(pref.id, pref)
            haveStateToPersist = true;
        } else if (workspace.hasPref('opened_projects')) {
            workspace.deletePref('opened_projects');
        }
        var ids = ['topview'];
        var i, elt, id, pref;
        for (i = 0; i < ids.length; i++) {
            id = ids[i];
            elt = document.getElementById(id);
            if (!elt) {
                alert("couldn't find " + id );
            }
            pref = elt.getState();
            if (pref) {
                haveStateToPersist = true;
                pref.id = id;
                workspace.setPref(id, pref);
            } else if (workspace.hasPref(id)) {
                workspace.deletePref(id);
            }
        }
        if (haveStateToPersist) {
            gPrefs.setPref(workspace.id, workspace);
        } else if (gPrefs.hasPref(workspace.id)) {
            gPrefs.deletePref(workspace.id);
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
            hasChanged = file.hasChanged;
            if (file.exists && hasChanged) {
                obSvc.notifyObservers(this, 'file_changed', file.URI);
            }
            item = new Object;
            item.type = 'view';
            item.view = view;
            item.file = file;
            if (!file.exists) {
                removedItems.push(item);
                view.document.isDirty = true;
            } else {
                if (view.document.differentOnDisk()) {
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
            file = projects[i].getFile();
            if (file.hasChanged) {
                item = new Object;
                item.type = 'project';
                item.project = projects[i];
                item.file = file;
                if (!file.exists) {
                    removedItems.push(item);
                    item.project.isDirty = true;
                } else if (item.project.isDirty) {
                    conflictedItems.push(item);
                } else {
                    changedItems.push(item);
                    item.project.isDirty = true;
                }
            }
        }

        // handle files and projects that have changed on disk
        if (changedItems.length > 0) {
            title = 'Reload Changed Files and Projects';
            prompt = 'Some open files and/or projects have changed on '+
                     'disk, do you want to reload them?';
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
                            var doc = items[i].view.document;
                            gCodeIntelSvc.ideEvent("changed_document",
                                                   doc.file.URI, doc);
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
            title = 'Close Deleted Files and Projects';
            prompt = 'The following open files and/or projects have been '+
                     'deleted from disk.  Do you want to close them?';
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
            prompt = 'The following files and projects have changed on disk '+
                     'and have unsaved changes in Komodo.  You can use '+
                     '"Show Unsaved Changes" to view a diff of the files, '+
                     'revert or save your changes.';
            title = 'Modified files have changed on disk';
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
    obSvc.notifyObservers(null,'file_update_now',url)
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
