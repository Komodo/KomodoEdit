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
var log = require("ko/logging").getLogger("open");

var fileLineNoRE = /^(.*)[#:](\d+)$/;

var _viewsBundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/views.properties");

function removeAmpersands(labels) {
    var ret = [];
    labels.forEach(function(s) { ret.push(s.replace(/&/g, '')); });
    return ret;
}

// TODO: These would be better added to the Komodo file associations, allowing
//       the user to then customize which file types they wish to preview as
//       images/browser types.
this._imageUrlREs = [
    /.*\.png$/i,
    /.*\.gif$/i,
    /.*\.jpg$/i,
    /.*\.jpeg$/i,
    /.*\.bmp$/i,
    /.*\.ico$/i,
];

this.isImageUrl = function open_isImageUrl(url) {
    var imageREs = ko.open._imageUrlREs;
    for (var i=0; i < imageREs.length; i++) {
        if (imageREs[i].test(url)) {
            return true;
        }
    }
    return false;
}

this._audioUrlREs = [
    /.*\.mp3$/i,
];
this.isAudioUrl = function open_isAudioUrl(url) {
    var audioREs = ko.open._audioUrlREs;
    for (var i=0; i < audioREs.length; i++) {
        if (audioREs[i].test(url)) {
            return true;
        }
    }
    return false;
}

/**
 * Asynchronously open the URI in a new Komodo tab, if the file is already
 * open then this existing tab becomes the currently focused tab.
 *
 * If you need the view for the file that is opened from this call, pass in
 * a callback function argument and then this function will be called after
 * the view is opened (or re-focused if it was already open).
 *
 * @param {String} uri the path or URI to open
 * @param {String} viewType optional default "editor" type of view
 *        component to use. Values can be [ "editor", "browser", "diff" ].
 * @param {boolean} skipRecentOpenFeature optional default false, can
 *        be used when the URI to open is a project file to specify that
 *        the feature to open files in that project should not be offered.
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. This will only be called if this opens or switches to
 *        an editor view, e.g. this won't be called for a kpf file. The view
 *        will be passed as an argument to the function.
 */
this.URI = function open_openURI(uri, viewType /* ="editor" */,
                                 skipRecentOpenFeature /* =false */,
                                 callback /* =null */) {
    return ko.open.URIAtLine(uri, null, viewType, skipRecentOpenFeature, callback);
}

// Similar to this.URI, used to detect when a recent URI no longer
// exists, and can be removed  from the 'file' MRU list.
this.recentURI = function open_recentURI(uri,
                                         viewType /* ="editor" */,
                                         skipRecentOpenFeature /* =false */
                                         ) {
    if (typeof(viewType) == "undefined" || !viewType) viewType = "editor";
    if (typeof(skipRecentOpenFeature) == "undefined") {
        skipRecentOpenFeature = false;
    }
    if (uri.match(/\.(?:kpf|komodoproject)$/i)) {
        // Verify the file exists, and remove from the project MRU list in
        // advance if it doesn't, because there's no callback when
        // opening projects.
        var koFileEx = Components.classes["@activestate.com/koFileEx;1"].
                       createInstance(Components.interfaces.koIFileEx);
        koFileEx.URI = uri;
        if (!koFileEx.exists) {
            // Remove it in advance
            ko.mru.removeURL('mruProjectList', uri);
            if (ko.places && ko.projects.manager.single_project_view) {
                ko.places.projects_SPV.rebuildView();
            }
        }
    }
    var callback = function(view) {
        if (view === null) {
            ko.mru.removeURL('mruFileList', uri);
        }
    };
    this.URI(uri, viewType, skipRecentOpenFeature, callback);
};

/**
 * Asynchronously open the URI in a new Komodo tab, if the file is already
 * open then this existing tab becomes the currently focused tab.
 *
 * If you need the view for the file that is opened from this call, pass in
 * a callback function argument and then this function will be called after
 * the view is opened (or re-focused if it was already open).
 *
 * @param {String} uri the path or URI to open
 * @param {Number} lineno the line number to open the file at
 * @param {String} viewType optional default "editor" type of view
 *        component to use. Values can be [ "editor", "browser", "diff" ].
 * @param {boolean} skipRecentOpenFeature optional default false, can
 *        be used when the URI to open is a project file to specify that
 *        the feature to open files in that project should not be offered.
 * @param {function} callback optional, to be called when the asynchronous load
 *        is complete. This will only be called if this opens or switches to
 *        an editor view, e.g. this won't be called for a kpf file. The view
 *        will be passed as an argument to the function.
 */
this.URIAtLine = function open_openURIAtLine(uri, lineno, viewType /* ="editor" */,
                                             skipRecentOpenFeature /* =false */,
                                             callback /* =null */) {
    try {
        // URI can be a local path or a URI
        uri = ko.uriparse.pathToURI(uri);
        // check for an attached line # in the form of:
        // file:///filename.txt#24   or
        // file:///filename.txt:24
        if (lineno == null) {
            var m = fileLineNoRE.exec(uri);
            if (m) {
                uri = m[1];
                lineno = m[2];
            }
        }
        if (uri.match(/\.(?:kpf|komodoproject)$/i)) {
            ko.projects.open(uri, skipRecentOpenFeature);
        } else if (uri.match(/\.xpi$/i)) {
            try {
                this._installAddon(uri);
            } catch(ex) {
                ko.dialogs.alert(_viewsBundle.GetStringFromName("installingExtensionIsCurrentlyDisabled") + " " + ex);
            }
        } else if (uri.match(/\.kpz$/i)) {
            ko.toolboxes.importPackage(uri);
        } else {
            if (uri.match(/\.ksf$/i)) {
                var prompt = _viewsBundle.formatStringFromName("importFileAsScheme.prompt", [ko.uriparse.baseName(uri)], 1);
                var buttons = [_viewsBundle.GetStringFromName("OK.customButtonLabel"),
                               _viewsBundle.GetStringFromName("openAsText.customButtonLabel"),
                               _viewsBundle.GetStringFromName("Cancel.customButtonLabel")];
                var responses = removeAmpersands(buttons);
                var text = null;
                var title = _viewsBundle.GetStringFromName("openingSchemeFile.label");
                var answer = ko.dialogs.customButtons(prompt,
                                                      buttons,
                                                      null,  //response=buttons[0]
                                                      null, // text
                                                      title);
                if (!answer || answer == responses[2]) {
                    return null;
                } else if (answer == responses[0]) {
                    var schemeService = Components.classes['@activestate.com/koScintillaSchemeService;1'].getService();
                    var schemeBaseName = _checkKSFBaseName(schemeService, uri);
                    if (!schemeBaseName) {
                        // The user cancelled, so don't open anything
                        return null;
                    }
                    try {
                        var newSchemeName = schemeService.loadSchemeFromURI(uri, schemeBaseName);
                        var oldScheme = schemeService.activateScheme(newSchemeName);
                        this._notifyHowtoRestoreOldScheme(schemeService, oldScheme, newSchemeName);
                        return null;
                    } catch(ex) {
                        alert(ex);
                        log.exception(ex);
                        // At this point we want to load the original file,
                        // as there's something wrong with its contents.
                    }
                }
            } else if (!viewType && (ko.open.isImageUrl(uri)
                                     || ko.open.isAudioUrl(uri))) {
                // Open the image for previewing, bug 85103.
                viewType = "browser";
            }
            ko.history.note_curr_loc();
            if (lineno) {
                ko.views.manager.doFileOpenAtLineAsync(uri, lineno, viewType, null, -1, callback);
            } else {
                ko.views.manager.doFileOpenAsync(uri, viewType, null, -1, callback);
            }
        }
    } catch(e) {
        log.exception(e);
    }
    return null;
}

this._installAddon = function(uri) {
    Components.utils.import("resource://gre/modules/AddonManager.jsm", this);
    // if we're opening a new window, it won't get the install failed message
    // (because it fires before the window is ready?).  This means we'll have to
    // dispatch that manually...
    function gotInstallCallback(aInstall) {
        var addonMgr = ko.launch.openAddonsMgr();
        aInstall.addListener({
            doCommand: function(command, installs) {
                /* poll until the overlay loads */
                var tries = 0; // don't try forever, give up at some point
                var callback = function() {
                    if (!addonMgr.gkoAMActionObserver) {
                        if (++tries < 20) {
                            setTimeout(callback, 10);
                        }
                        return;
                    }
                    addonMgr.gkoAMActionObserver.observe({installs: installs},
                                                         "addon-install-" + command);
                };
                callback();
            },
            onDownloadCancelled: function(install) {
                // nothing here
            },
            onDownloadFailed: function(install) {
                Components.utils.reportError("Failed to download " +
                                             install.name +
                                             " from " +
                                             (install.sourceURI || {}).spec);
                this.doCommand("failed", [install]);
            },
            onInstallEnded: function(install) {
                if (install && install.addon && !install.addon.isCompatible) {
                    // lies! the install actually failed
                    Components.utils.reportError("Addon " +
                                                 install.name +
                                                 " is not compatible");
                    this.doCommand("failed", [install]);
                } else {
                    this.doCommand("complete", [install]);
                }
            },
            onInstallCancelled: function(install) {
                // nothing here; this can happen if we install the same thing
                // twice in a row, for example
            },
            onInstallFailed: function(install) {
                Components.utils.reportError("Installation of " +
                                             install.name +
                                             " failed for unknown reasons");
                this.doCommand("failed", [install]);
            }
        });
        aInstall.install();
        //log.debug("Installed " + uri);
    }
    this.AddonManager.getInstallForURL(uri,
                                       gotInstallCallback,
                                       "application/x-xpinstall");
}

/**
 * @param {nsIScintillaSchemeService} schemeService
 * @param {String} uri -- uri of the source of the KSF file
 * @returns {String} newBaseName or null
 */
function _checkKSFBaseName(schemeService, uri) {
    var currentSchemeNames_tmp = {};
    schemeService.getSchemeNames(currentSchemeNames_tmp, {});
    var currentSchemeNames = {};
    currentSchemeNames_tmp.value.forEach(function(name) {
// #if PLATFORM == 'darwin' or PLATFORM == 'win'
        name = name.toLowerCase();
// #endif
        currentSchemeNames[name] = null;
    });
    var schemeBaseName = ko.uriparse.baseName(uri);
    var ext = ko.uriparse.ext(uri);
    var newSchemeName = schemeBaseName.substring(0, schemeBaseName.lastIndexOf(ext));
    var prompt, testName;
    while (true) {
        if (newSchemeName.length == 0 || !schemeService.schemeNameIsValid(newSchemeName)) {
            prompt = _viewsBundle.formatStringFromName("schemeNameHasInvalidCharacters.template",
                                                       [newSchemeName], 1);
        } else {
// #if PLATFORM == 'darwin' or PLATFORM == 'win'
            testName = newSchemeName.toLowerCase();
// #else
            testName = newSchemeName;
// #endif
            if (typeof(currentSchemeNames[testName]) != "undefined") {
                prompt = _viewsBundle.formatStringFromName("schemeExists.template",
                                                           [newSchemeName], 1);
            } else {
                return newSchemeName + ext;
            }
        }
        newSchemeName = ko.dialogs.prompt(
            prompt,
            _viewsBundle.GetStringFromName("newSchemeName.label"),
            newSchemeName);
        if (!newSchemeName) {
            return null;
        }
    }
    //NOTREACHED
    return null;
}


/**
 * Display a notification box that lets the user revert the current
 * color scheme from the one that was just imported to the previous one.
 * @param {nsIScintillaSchemeService} schemeService
 * @param {String} oldSchemeName
 * @param {String} newSchemeName
 * @returns {undefined} not used
 */
this._notifyHowtoRestoreOldScheme = function(schemeService, oldSchemeName, newSchemeName) {
    var prefs = Components.classes["@activestate.com/koPrefService;1"].
                        getService(Components.interfaces.koIPrefService).prefs;
    var notificationBox = document.getElementById("komodo-notificationbox");
    var label = _viewsBundle.formatStringFromName("schemeChangeNotification.template",
                                                  [newSchemeName], 1);
    var value = 'offer-to-restore-scheme';
    var image = "chrome://famfamfamsilk/skin/icons/information.png";
    var priority = notificationBox.PRIORITY_WARNING_LOW;
    var existingNotification = notificationBox.getNotificationWithValue(value);
    if (existingNotification) {
        if ('preNotificationSessionSchemeName' in this) {
            oldSchemeName = this.preNotificationSessionSchemeName || oldSchemeName;
        }
        try {
            notificationBox.removeAllNotifications(/*immediate=*/true);
        } catch(ex) {
            log.exception(ex);
        }
    }
    var buttons = [
        {label: _viewsBundle.GetStringFromName("yes.label"),
         accessKey: _viewsBundle.GetStringFromName("yes.accessKey"),
         callback: function() {}
        },
        {label:_viewsBundle.formatStringFromName("noRevertTo.template",
                                                 [oldSchemeName], 1),
         accessKey: _viewsBundle.GetStringFromName("noRevertTo.accessKey"),
         callback: function() {
            try {
                schemeService.activateScheme(oldSchemeName);
            } catch(ex) { log.exception(ex); }
         }
        }
    ];
    notificationBox.appendNotification(label, value, image, priority, buttons);
    this.preNotificationSessionSchemeName = oldSchemeName;
}

/**
 * Open the given path in Komodo.
 *
 * If you need the view for the file that is opened from this call, pass in
 * a callback function argument and then this function will be called after
 * the view is opened (or re-focused if it was already open).
 *
 * @param {String} displayPath identifies the path to open. Display
 *        path may be the display path of an already open (and possibly
 *        untitled) document.
 * @param {String} viewType optional default "editor", the type of
 *        view to create for the openned path. It is ignored if the
 *        displayPath indicates an already open view.
 * @param {function} callback optional, to be called when the asynchronous load
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
        if (! typedView.koDoc) {
            continue;
        }
        if (_fequal(typedView.koDoc.displayPath, displayPath)) {
            ko.history.note_curr_loc();
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
 * Open quick start - the view will be opened synchronously.		
 */		
this.quickStart = function open_openStartPage() {		
    ko.history.note_curr_loc();		
    ko.views.manager._doFileOpen("chrome://komodo/content/quickstart.xml#view-quickstart",
                                 "quickstart");
}

this.multipleURIs = function open_openMultipleURIs(urls, viewType, isRecent)
{
    var i,j;
    if (typeof(isRecent) == "undefined") isRecent = false;
    if (urls.length) {
        var prefSvc = Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService);
        var viewStateMRU = prefSvc.getPrefs("viewStateMRU");
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
            action = ko.dialogs.yesNoCancel(_viewsBundle.GetStringFromName("reopenProjectFilesPrompt"),
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
        var openMethod = isRecent ? ko.open.recentURI : ko.open.URI;
        for (i=0; i < urls.length; i++) {
            if (i == urls.length-1) {
                ko.views.manager.batchMode = false;
            }
            openMethod.call(ko.open, urls[i], viewType, true);
        }
    }
}

/**
 * open a file picker, and open the files that the user selects
 */
this.filePicker = function view_openFilesWithPicker(viewType/*='editor'*/) {
    // We want the default directory to be that of the current file if there is one
    var defaultDir = null;
    var v = ko.views.manager.currentView;
    if (v && v.getAttribute("type") == "editor" &&
        v.koDoc && !v.koDoc.isUntitled && v.koDoc.file.isLocal)
    {
        defaultDir = ko.views.manager.currentView.koDoc.file.dirName;
    }
    
    var paths = ko.filepicker.browseForFiles(defaultDir);
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
        var os = Components.classes["@activestate.com/koOs;1"].getService();
        var templateSvc = Components.classes["@activestate.com/koTemplateService?type=file;1"].getService();
        var defaultDir = templateSvc.getUserTemplatesDir();
        var paths = ko.filepicker.browseForFiles(defaultDir);
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
