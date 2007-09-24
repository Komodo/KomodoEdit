/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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
 * function for opening buffers in Komodo tabs
 *
 * @param uri {String} the path or URI to open
 * @param viewType {String} optional default "editor" type of view
 *  component to use. Values can be [ "editor", "browser", "diff" ].
 * @param skipRecentOpenFeature {boolean} optional default false, can
 *  be used when the URI to open is a project file to specify that
 *  the feature to open files in that project should not be offered.
 * @return view {DOMElement xul:view}
 *
 * If the URI is not successfully opened or if the URL opened is a Komodo
 * project file null is returned.
 */
this.URI = function open_openURI(uri, viewType /* ="editor" */,
                               skipRecentOpenFeature /* =false */) {
    try{
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
    if (typeof(viewType)=='undefined' || !viewType)
        viewType = 'editor';
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
        return ko.views.manager.doFileOpenAtLine(uri,line, viewType);
        } else {
        return ko.views.manager.doFileOpen(uri,viewType);
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
 * @param displayPath {String} identifies the path to open. Display
 *  path may be the display path of an already open (and possibly
 *  untitled) document.
 * @param viewType {String} optional default "editor", the type of
 *  view to create for the openned path. It is ignored if the
 *  displayPath indicates an already open view.
 */
this.displayPath = function open_openDisplayPath(displayPath, viewType /* ="editor" */) {
    if (typeof(viewType) == "undefined" || !viewType) viewType = "editor";

    var views = ko.views.manager.topView.getViews(true);
    for (var i = 0; i < views.length; ++i) {
        if (views[i].document && views[i].document.displayPath == displayPath) {
            views[i].makeCurrent();
            return;
        }
    }

    // Fallback to open URI.
    ko.open.URI(displayPath);
}

/**
 * Open Komodo's Start Page
 */
this.startPage = function open_openStartPage() {
    ko.views.manager.doFileOpen("chrome://komodo/content/startpage/startpage.xml#view-startpage",
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

}).apply(ko.open);




// BC API
var open_openURI = ko.open.URI;
var open_openDisplayPath = ko.open.displayPath;
var open_openStartPage = ko.open.startPage;
var open_openMultipleURIs = ko.open.multipleURIs;

