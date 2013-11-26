/* Copyright (c) 2000-2012 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

xtk.include('domutils');
Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.workspace) == "undefined") {
    ko.workspace = {};
}
(function() {

var log = ko.logging.getLogger('workspace');
//log.setLevel(ko.logging.LOG_DEBUG);
var _saveInProgress = false;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
    .getService(Components.interfaces.nsIStringBundleService)
    .createBundle("chrome://komodo/locale/views.properties");

this.saveInProgress = function() {
    return _saveInProgress;
}

const multiWindowWorkspacePrefName = "windowWorkspace";
const _mozPersistPositionDoesNotWork =
// #if PLATFORM == 'win' or PLATFORM == 'darwin'
false;
// #else
true;
// #endif

/**
 * Restore all workspaces, panes and widgets from the last session.
 */
this.restore = function ko_workspace_restore()
{
    // the offer to restore the workspace needs to be after the
    // commandments system is initialized because the commandments mechanism
    // is how the determination of 'running in non-interactive mode' happens,
    // which the restoration step needs to know about.

    // Eventually restoreWorkspace will be rewritten to restore
    // a set of windows, and restore will be done at app-startup
    // time, not when each window starts up.
    var restoreWorkspace = true;
    try {
        if (!ko.windowManager.lastWindow()) {
            restoreWorkspace = false;
        }
    } catch(ex) {
        // Restore the workspace on error
        _log.exception(ex);
    }

    if (restoreWorkspace) {
        ko.workspace.restoreWorkspace();
        // if the prefs are set to not restore workspaces, we still should
        // restore the widget/side pane layouts.  This relies on ko.widgets
        // being smart enough to restore things twice.
        let prefs = ko.prefs;
        let path = []
        if (prefs.hasPref(multiWindowWorkspacePrefName)) {
            let workspacePrefs = prefs.getPref(multiWindowWorkspacePrefName);
            if (workspacePrefs.hasPref("1")) {
                prefs = workspacePrefs.getPref("1");
                path = [multiWindowWorkspacePrefName, "1"];
            }
        }
        ko.widgets.restoreLayout(prefs, path);
    } else {
        // Restore the default layout (i.e. last closed window)
        ko.widgets.restoreLayout(ko.prefs, []);
    }

    // handle window.arguments spec list
    if ('arguments' in window && window.arguments && window.arguments[0]) {
        var arg = window.arguments[0];
        if ('workspaceIndex' in arg) {
            var thisIndexOnly = ('thisIndexOnly' in arg && arg.thisIndexOnly);
            ko.workspace.restoreWorkspaceByIndex(window, arg.workspaceIndex,
                                                 thisIndexOnly);
        } else {
            // There is no workspace to restore, but init window essentials
            ko.workspace.initializeEssentials(window);
            var urllist;
            if ('uris' in arg) {
                urllist = arg.uris; // Called from ko.launch.newWindow(uri)
            } else if (arg instanceof Components.interfaces.nsIDialogParamBlock) {
                var paramBlock = arg.QueryInterface(Components.interfaces.nsIDialogParamBlock);
                urllist = paramBlock ? paramBlock.GetString(0).split('|') : [];
            } else if (typeof(arg) == 'string') {
                urllist = arg.split('|'); //see asCommandLineHandler.js
            } else {
                // arg is most likely an empty object
                urllist = [];
            }
            for (var i in urllist) {
                ko.open.URI(urllist[i]);
            }
        }
    }

    // Some paths through the above block might not have called this,
    // so call it now to be sure.  See bug 87856.
    ko.workspace.initializeEssentials(window);
}

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

    var was_normal_shutdown = ko.prefs.getBooleanPref('komodo_normal_shutdown');
    if (was_normal_shutdown) {
        ko.prefs.setBooleanPref('komodo_normal_shutdown', false);
        // Force flushing of prefs to file.
        var prefSvc = Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService);
        prefSvc.saveState();
    }

    // If there is a workspace to restore - prompt the user to see if they wish
    // to restore it.
    if (!ko.prefs.hasPref(multiWindowWorkspacePrefName)) {
        return;
    } else if (!was_normal_shutdown) {   // Komodo crashed
        if (ko.prefs.getBooleanPref("donotask_restore_workspace") &&
            ko.prefs.getStringPref("donotask_action_restore_workspace") == "No") {
            // The user has explictly asked never to restore the workspace.
            return;
        }
        var prompt = _bundle.GetStringFromName("restoreWorkspaceAfterCrash.prompt");
        var title = _bundle.GetStringFromName("restoreWorkspaceAfterCrash.title");
        if (ko.dialogs.yesNo(prompt, null, null, title) == "No") {
            return;
        }
    } else if (ko.dialogs.yesNo(_bundle.GetStringFromName("doYouWantToOpenRecentFilesAndProjects.prompt"),
                                null, null, null, "restore_workspace") == "No") {
        return;
    }

    // Fix up the stored window numbers
    var windowWorkspacePref = ko.prefs.getPref(multiWindowWorkspacePrefName);
    let prefIds = {};
    windowWorkspacePref.getPrefIds(prefIds, {});
    prefIds = prefIds.value.map(function(n) parseInt(n, 10)).sort(function(a, b) a - b);
    if (prefIds[0] < 1) {
        // Invalid ids; shift everything over :|
        let prefs = prefIds.map(function(n) windowWorkspacePref.getPref(n));
        prefIds.map(function(n) windowWorkspacePref.deletePref(n));
        for (let i = 1; prefs.length; ++i) {
            windowWorkspacePref.setPref(i, prefs.shift());
        }
        windowWorkspacePref.getPrefIds(prefIds, {});
        prefIds = prefIds.value;
    }
    for each (let prefId in prefIds) {
        let pref = windowWorkspacePref.getPref(prefId);
        if (pref.hasLongPref("windowNum")) {
            pref.setLongPref("windowNum", prefId);
        }
    }

    // Restore the first workspace directly, and restore other
    // workspaces indirectly each new window's init routine in ko.main

    var checkWindowBounds = _mozPersistPositionDoesNotWork || windowWorkspacePref.hasPref(1);
    var nextIdx = this._getNextWorkspaceIndexToRestore(Number.NEGATIVE_INFINITY);
    if (nextIdx !== undefined) {
        let workspace = windowWorkspacePref.getPref(nextIdx);
        this._restoreWindowWorkspace(workspace,
                                     currentWindow,
                                     checkWindowBounds,
                                     [multiWindowWorkspacePrefName, nextIdx]);
        nextIdx = this._getNextWorkspaceIndexToRestore(nextIdx);
        if (nextIdx !== undefined) {
            ko.launch.newWindowFromWorkspace(nextIdx);
        }
    }
};

this._getNextWorkspaceIndexToRestore = function _getNextWorkspaceIndexToRestore(currIdx) {
    var windowWorkspacePref = ko.prefs.getPref(multiWindowWorkspacePrefName);
    var prefIds = {};
    windowWorkspacePref.getPrefIds(prefIds, {});
    prefIds = prefIds.value.filter(function(i) i > currIdx);
    prefIds.sort(function(a, b) { return a - b });
    //dump("_getNextWorkspaceIndexToRestore(" + currIdx +"): prefIds:" + prefIds + "\n");
    var lim = prefIds.length;
    for (var i = 0; i < lim; i++) {
        var newIdx = prefIds[i];
        if (!windowWorkspacePref.hasPref(newIdx)) {
            continue;
        }
        var workspace = windowWorkspacePref.getPref(newIdx);
        if (!workspace.hasPref('restoreOnRestart')
            || workspace.getBooleanPref('restoreOnRestart')) {
            return newIdx;
        }
    }
    return undefined;
};

this.restoreWorkspaceByIndex = function(currentWindow, idx, thisIndexOnly)
{
    if (!ko.prefs.hasPref(multiWindowWorkspacePrefName)) {
        ko.dialogs.alert("Internal error: \n"
                         + "ko.workspace.restoreWorkspaceByIndex invoked (index="
                         + idx
                         + "),\n"
                         + "but there's no " + multiWindowWorkspacePrefName + " pref\n");
        return;
    }
    idx = parseInt(idx);
    //dump("restoreWorkspaceByIndex: set this workspace _koNum to " + idx + "\n");
    currentWindow._koNum = idx;
    var windowWorkspacePref = ko.prefs.getPref(multiWindowWorkspacePrefName);
    try {
        this._restoreWindowWorkspace(windowWorkspacePref.getPref(idx),
                                     currentWindow,
                                     idx > 0 || _mozPersistPositionDoesNotWork,
                                     [multiWindowWorkspacePrefName, idx]);
    } catch(ex) {
        log.exception("Can't restore workspace for window " + idx + ", exception: " + ex);
    }
    if (thisIndexOnly) {
        // _restoreFocusToMainWindow();
        //dump("**************** restoreWorkspaceByIndex: Don't restore any other windows\n");
    } else {
        var nextIdx = this._getNextWorkspaceIndexToRestore(idx);
        if (nextIdx !== undefined) {
            ko.launch.newWindowFromWorkspace(nextIdx);
        } else {
            _restoreFocusToMainWindow();
        }
    }
};

this.getRecentClosedWindowList = function() {
    if (!ko.prefs.hasPref(multiWindowWorkspacePrefName)) {
        return [];
    }
    var windowWorkspacePref = ko.prefs.getPref(multiWindowWorkspacePrefName);
    var prefIds = {};
    windowWorkspacePref.getPrefIds(prefIds, {});
    prefIds = prefIds.value.map(function(x) parseInt(x));
    var loadedWindows = ko.windowManager.getWindows();
    var loadedIDs = loadedWindows.map(function(w) parseInt(w._koNum));
    var mruList = [];
    for (var i = 0; i < prefIds.length; i++) {
        try {
            var idx  = prefIds[i];
            if (loadedIDs.indexOf(idx) != -1) {
                //dump("Skip window " + idx + " -- it's already loaded\n");
                continue;
            }
            var workspace = windowWorkspacePref.getPref(idx);
            if (! workspace.hasPref('restoreOnRestart')
                || workspace.getBooleanPref('restoreOnRestart')) {
                // If restoreOnRestart is on or missing,
                // it means that the window wasn't opened at startup,
                // so we should offer to open it now
                continue;
            }
            if (!workspace.hasPref("topview")) {
                //Observation: this can happen for windows that have no loaded views.
                // Encountered while working on bug 91751 and bug 91744
                log.debug("getRecentClosedWindowList: !workspace.hasPref(topview)\n");
                continue;
            }
            var topview = workspace.getPref("topview");
            var childState = topview.getPref("childState");
            var current_view_index = childState.getPref(0).getLongPref("current_view_index");
            var view_prefs = childState.getPref(0).getPref('view_prefs');
            if (view_prefs.length <= current_view_index) {
                // Oops, this view doesn't actually exist?
                current_view_index = view_prefs.length - 1;
            }
            var currentFile = view_prefs.getPref(current_view_index).getStringPref("URI");
            var mru = {
              windowNum: idx,
              currentFile: currentFile
            };
            if (workspace.hasPref("current_project")) {
                var current_project = workspace.getStringPref("current_project");
                if (current_project) {
                    mru.current_project = current_project;
                }
            }
            mruList.push(mru);
        } catch(ex) {
            log.error("getRecentClosedWindowList error in workspace " + multiWindowWorkspacePrefName + ": " + ex);
        }
    }
    return mruList;
}

function _restoreFocusToMainWindow() {
    var windows = ko.windowManager.getWindows();
    for (var i = 0; i < windows.length; i++) {
        var w = windows[i];
        if (w.ko._hasFocus) {
            w.focus();
        }
        delete w.ko._hasFocus;
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

function _restoreWindowPosition(currentWindow, coordinates) {
    const _nsIDOMChromeWindow = Components.interfaces.nsIDOMChromeWindow;
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
    if (Math.abs(screenX) > 3 * screenWidth || Math.abs(screenY) > 3 * screenHeight) {
        screenX = screenY = 0;
    }
    if (currentWindow.screenX != screenX || currentWindow.screenY != screenY) {
        currentWindow.moveTo(screenX, screenY);
    }
    if (currentWindow.outerHeight != outerHeight || currentWindow.outerWidth != outerWidth) {
        var newHeight = _checkWindowCoordinateBounds(outerHeight, 0,
                                                     .2 * screenHeight,
                                                     screenHeight,
                                                     .9 * screenHeight);
        var newWidth = _checkWindowCoordinateBounds(outerWidth, 0,
                                                    .2 * screenWidth,
                                                    screenWidth,
                                                    .9 * screenWidth);
        currentWindow.resizeTo(newWidth, newHeight);
    }
    if (windowState == _nsIDOMChromeWindow.STATE_MINIMIZED) {
        currentWindow.minimize();
    } else if (windowState == _nsIDOMChromeWindow.STATE_MAXIMIZED) {
        currentWindow.maximize();
    }
}

this._restoreWindowWorkspace =
    function(workspace, currentWindow, checkWindowBounds, prefPath)
{
    try {
        var wko = currentWindow.ko;
        var cnt = new Object();
        var ids = new Object();
        var id, elt, pref;
        if (checkWindowBounds && workspace.hasPref('coordinates')) {
            var coordinates = workspace.getPref('coordinates');
            // Must be in a setTimeout, after the window has been loaded,
            // otherwise the window manager may resize or reposition it.
            setTimeout(_restoreWindowPosition, 1, currentWindow, coordinates);
        }
        // Opening the Start Page should be before commandment system init and
        // workspace restoration because it should be the first view opened.
        if (ko.prefs.getBooleanPref("show_start_page")) {
            ko.open.startPage();
        }

        if (workspace.hasPref('windowNum')) {
            let windowNum = workspace.getLongPref('windowNum');
            let infoService = Components.classes["@activestate.com/koInfoService;1"].
                                         getService(Components.interfaces.koIInfoService);
            currentWindow._koNum = windowNum;
            try {
                infoService.setUsedWindowNum(windowNum);
            } catch(ex) {
                // It turns out that the window # saved in the old workspace
                // has already been assigned.
                currentWindow._koNum = infoService.nextWindowNum();
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
        ko.widgets.restoreLayout(workspace, prefPath);
        if (wko.history) {
            wko.history.restore_prefs(workspace);
        }
        // Don't open startPage here (bug 87854)
        this.initializeEssentials(currentWindow, false);

        // Now projects depends on places, so open it after
        // In Version 7 Komodo saves opened projects in a different prefset,
        // so allow both here.
        if (workspace.hasPref('opened_projects')
            || workspace.hasPref('opened_projects_v7')) {
            var use_v7_mode;
            if (workspace.hasPref('opened_projects_v7')) {
                use_v7_mode = true;
                pref = workspace.getPref('opened_projects_v7');
            } else {
                use_v7_mode = false;
                pref = workspace.getPref('opened_projects');
            }
            var currentProjectURI;
            if (workspace.hasPref('current_project')) {
                currentProjectURI = workspace.getStringPref('current_project');
            } else {
                currentProjectURI = null;
            }
            // Don't load projects until places has initialized the projects view
            this.waitForProjectManager(function() {
                if (use_v7_mode) {
                    wko.projects.manager.setState(pref);
                } else {
                    wko.projects.manager.setState_v6(pref);
                }
                if (currentProjectURI) {
                    // If a project with that url is loaded, make it current
                    var proj = wko.projects.manager.getProjectByURL(currentProjectURI);
                    if (proj) {
                        wko.projects.manager.currentProject = proj;
                    }
                }
                });
        }
        wko._hasFocus = workspace.getBoolean('hasFocus', false);
    } catch(ex) {
        log.exception(ex, "Error restoring workspace:");
    }
};

this.waitForProjectManager = function(callback) {
    // First make sure the places widget exists ,and then verify
    // the project manager has been hooked up, so the tree is loaded.
    ko.widgets.getWidgetAsync('placesViewbox', function() {
            var delayFunc;
            var limit = 100; // iterations
            var delay = 50;  // time in msec
            delayFunc = function(tryNum) {
                try {
                    if (ko.projects.manager.viewMgr.owner.projectsTreeView) {
                        callback();
                        return;
                    }
                } catch(ex) {
                    log.info("waitForProjectManager: Failure: " + tryNum + ": "  + ex);
                };
                if (tryNum < limit) {
                    setTimeout(delayFunc, delay, tryNum + 1);
                } else {
                    log.error("waitForProjectManager: Gave up trying to restore the projects workspace");
                }
            }
            setTimeout(delayFunc, delay, 0);
        });
};

this._calledInitializeEssentials = false;
this.initializeEssentials = function(currentWindow, showStartPage /*true*/) {
    if (this._calledInitializeEssentials) {
        return;
    }
    if (typeof(showStartPage) == "undefined") showStartPage=true;
    var infoService = Components.classes["@activestate.com/koInfoService;1"].
                                 getService(Components.interfaces.koIInfoService);
    if (!("__koNum" in currentWindow.ko.main)) {
        currentWindow._koNum = infoService.nextWindowNum();
    }
    if (showStartPage && ko.prefs.getBooleanPref("show_start_page")) {
        ko.open.startPage();
    }
    xtk.domutils.fireEvent(window, 'workspace_restored');
    this._calledInitializeEssentials = true;
}

/*XXX: At some point remove these prefs from the global prefset:
 * uilayout_bottomTabBoxSelectedTabId
 * uilayout_leftTabBoxSelectedTabId
 * uilayout_rightTabBoxSelectedTabId
 */

this._saveWorkspaceForIdx_aux =
    function _saveWorkspaceForIdx_aux(idx, restoreOnRestart,
                                      thisWindow, mainWindow,
                                      windowWorkspace, saveCoordinates) {
    var workspace = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
    windowWorkspace.setPref(thisWindow._koNum, workspace);
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
    if (restoreOnRestart && thisWindow == mainWindow) {
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
    workspace.setLongPref('windowNum', thisWindow._koNum);
    workspace.setBooleanPref('restoreOnRestart', restoreOnRestart);
    // Divide the # of millisec by 1000, or we'll overflow on the setLongPref
    // conversion to an int.
    workspace.setLongPref('timestamp', (new Date()).valueOf() / 1000);
    if (wko.history) {
        wko.history.save_prefs(workspace);
    }
};

this._getWindowWorkspace = function() {
    if (ko.prefs.hasPref(multiWindowWorkspacePrefName)) {
        return ko.prefs.getPref(multiWindowWorkspacePrefName);
    }
    var windowWorkspace = Components.classes['@activestate.com/koPreferenceSet;1'].createInstance();
    ko.prefs.setPref(multiWindowWorkspacePrefName, windowWorkspace);
    return windowWorkspace;
}

this.saveWorkspaceForIdx = function saveWorkspaceForIdx(idx) {
    var mainWindow = ko.windowManager.getMainWindow();
    var windows = ko.windowManager.getWindows();
    var windowWorkspace = this._getWindowWorkspace();
    var saveCoordinates = _mozPersistPositionDoesNotWork || windows.length > 1;
    try {
        _saveInProgress = true;
        var restoreOnRestart = false;
        var thisWindow = window; // the current window
        this._saveWorkspaceForIdx_aux(idx, restoreOnRestart,
                                      thisWindow, mainWindow,
                                      windowWorkspace, saveCoordinates);
        var prefSvc = Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService);
        prefSvc.saveState();
    } catch (e) {
        log.exception(e,"Error saving workspace: ");
    } finally {
        _saveInProgress = false;
    }
};

/**
 * save all workspace preferences and state
 */
this.saveWorkspace = function view_saveWorkspace()
{
    _saveInProgress = true;
    // Ask each major component to serialize itself to a pref.
    try {
        var mainWindow = ko.windowManager.getMainWindow();
        var windows = ko.windowManager.getWindows();
        var windowWorkspace = ko.workspace._getWindowWorkspace();
        var saveCoordinates = _mozPersistPositionDoesNotWork || windows.length > 1;
        var restoreOnRestart = true;
        for (var thisWindow, idx = 0; thisWindow = windows[idx]; idx++) {
            ko.workspace._saveWorkspaceForIdx_aux(idx, restoreOnRestart,
                                          thisWindow, mainWindow,
                                          windowWorkspace, saveCoordinates);
        }
        // Use the current window's layout as the default for new windows
        mainWindow.ko.widgets.unload([]);
        // Save prefs
        var prefSvc = Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService);
        prefSvc.saveState();
    } catch (e) {
        log.exception(e,"Error saving workspace: ");
    } finally {
        _saveInProgress = false;
    }
}

this.markClosedWindows = function() {
    /**
     * markClosedWindows - get all the windows, and all the
     * members of preference-set:windowWorkspace.  Find
     * any that are set to restoreOnRestart to true, but are
     * no longer open, and turn the pref off.
     */
    if (!ko.prefs.hasPref(multiWindowWorkspacePrefName)) {
        return;
    }
    var windowWorkspacePref = ko.prefs.getPref(multiWindowWorkspacePrefName);
    var prefIds = {};
    windowWorkspacePref.getPrefIds(prefIds, {});
    prefIds = prefIds.value;
    var lim = prefIds.length;
    var workspacePrefs = [];
    var pref;
    var prefsByWindowNum = {};
    var loadedWindowNums = {};
    ko.windowManager.getWindows().forEach(function(win) {
            loadedWindowNums[win._koNum] = 1;
        });
    for (var i = 0; i < lim; i++) {
        if (windowWorkspacePref.getPrefType(prefIds[i]) != "object") {
            log.warning("markClosedWindows: ignoring invalid pref " + prefIds[i]);
            continue;
        }
        pref = windowWorkspacePref.getPref(prefIds[i]);
        if (pref.hasLongPref("windowNum")) {
            var windowNum = pref.getLongPref("windowNum");
            if (!(windowNum in loadedWindowNums)) {
                pref.setBooleanPref("restoreOnRestart", false);
            }
        }
    }
};

}).apply(ko.workspace);
