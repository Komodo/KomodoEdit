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

/* Komodo startup/shutdown handling.
 *
 * This file should ONLY contain functionality directly relevant to startup and
 * shutdown. Enforcer: ShaneC.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
ko.main = {};

(function() { /* ko.main */

const {classes: Cc, interfaces: Ci, utils: Cu} = Components;

var _log = ko.logging.getLogger("ko.main");
// a default logger that can be used anywhere (ko.main.log)
//_log.setLevel(ko.logging.LOG_DEBUG);

var _savedWorkspace = false;

function saveWorkspaceIfNeeded(reason) {
    if (!_savedWorkspace) {
        ko.workspace.saveWorkspace(true);
        ko.prefs.setBooleanPref("komodo_normal_shutdown", true);
        _savedWorkspace = true;
        // In the case of a regular quit-application, Komodo's prefs will
        // perform the necessary saveState() work.
        if (reason != "quit-application") {
            // Save prefs
            Components.classes["@activestate.com/koPrefService;1"]
                      .getService(Components.interfaces.koIPrefService)
                      .saveState();
        }
    }
}

/**
 * Is this window being closed?
 */
this.windowIsClosing = false;

this.quitApplication = function() {
    try {
        ko.main.windowIsClosing = true;
        ko.workspace.markClosedWindows();
        saveWorkspaceIfNeeded("quit-application");
    } catch(ex) {
        _log.exception(ex);
    }
    try {
        goQuitApplication();
    } catch(ex) {
        _log.exception(ex);
    }
};

/**
 * Window "close" event handler to close the Komodo window and, if it is the
 * last one, quit.
 *
 * This is called when the application's "x" close button is pressed. It is
 * NOT called when quitting Komodo via "File -> Exit", "Cmd+Q", or equivalent.
 */
this._onClose = function(event) {
    _log.debug(">> ko.main._onClose");

    // If this is the last main Komodo window, then call toolkit's
    // `goQuitApplication` to handle quitting.
    if (ko.windowManager.lastWindow()) {
        event.stopPropagation();
        event.preventDefault();
        event.cancelBubble = true;
        ko.main.quitApplication();
        return;
    }
    
    ko.workspace.saveWorkspaceForIdx(ko.main.__koNum);
    // Otherwise, this isn't the last Komodo window, just handle closing
    // this window.
    if (!ko.main.runCanCloseHandlers()) {
        event.stopPropagation();
        event.preventDefault();
        event.cancelBubble = true;
        return;
    }
    ko.main.windowIsClosing = true;
    ko.projects.prepareForShutdown();
    ko.main.runWillCloseHandlers();

    window.removeEventListener("close", ko.main._onClose, true);
    _log.debug("<< ko.main._onClose");
    return;
}
window.addEventListener("close", ko.main._onClose, true);


/**
 * Window "DOMWindowClose" event sent when the window is about to be closed by
 * `window.close()`.
 *
 * For Komodo shutdown this is called when a window is closed via toolkit's
 * `goQuitApplication()`, but NOT when closed via the application
 * window's "x" close button.
 *
 * However, this method will be called in procedures that cause
 * Komodo to shut down, such as during updates.  It's too late to check
 * if we can quit, but we should still save the workspace and run the
 * willCloseHandlers.  See bug 67126 for more details.
 *
 * http://developer.mozilla.org/en/docs/Gecko-Specific_DOM_Events#DOMWindowClose
 * http://mxr.mozilla.org/mozilla1.8/source/dom/src/base/nsGlobalWindow.cpp#4737
 *  ...
 *  DispatchCustomEvent("DOMWindowClose")
 *  ...
 */
this._onDOMWindowClose = function(event) {
    _log.debug(">> ko.main._onDOMWindowClose");
    if (ko.windowManager.lastWindow()) {
        saveWorkspaceIfNeeded("window-close");
    }
    ko.main.runWillCloseHandlers();
    window.removeEventListener("DOMWindowClose", ko.main._onDOMWindowClose, true);
    _log.debug("<< ko.main._onDOMWindowClose");
}
window.addEventListener("DOMWindowClose", ko.main._onDOMWindowClose, true);


var _canCloseHandlers = [];
this.addCanCloseHandler = function(handler, object /*=null*/) {
    if (typeof(object) == "undefined") object = null;
    var callback = new Object();
    callback.handler = handler;
    callback.object = object;
    _canCloseHandlers.push(callback);
};

this.runCanCloseHandlers = function() {
    _log.debug(">> ko.main.runCanCloseHandlers");
    for (var i=_canCloseHandlers.length-1; i >= 0 ; i--) {
        try {
            var callback = _canCloseHandlers[i];
            var res;
            if (callback.object) {
                res = callback.handler.apply(callback.object);
            } else {
                res = callback.handler();
            }
            if (!res) {
                _log.debug("<< window.tryToClose: ret false, canClose says no");
                return false;
            }
        } catch(e) {
            _log.exception(e,"error when running '"+callback.handler+
                      "' shutdown handler (object='"+callback.object+"':");
        }
    }
    _log.debug("<< ko.main.runCanCloseHandlers ret true");
    return true;
};

var _willCloseHandlers = []; // synonym: willCloseHandlers

/**
 * Register a routine to be called when a Komodo window is closed.
 * To register a simple routine do this:
 *      ko.main.addWillCloseHandler(<routine>)
 * To register an object method do this:
 *      ko.main.addWillCloseHandler(this.<method>, this);
 *XXX Do we want to add an optional argument list to pass in?
 */
this.addWillCloseHandler = function(handler, object /*=null*/) {
    if (typeof(object) == "undefined") object = null;
    var callback = new Object();
    callback.handler = handler;
    callback.object = object;
    _willCloseHandlers.push(callback);
};

/**
 * Remove the given handler from the list of do-close handlers.
 */
this.removeWillCloseHandler = function(handler) {
    for (var i=0; i < _willCloseHandlers.length; i++) {
        if (_willCloseHandlers[i].handler == handler) {
            _willCloseHandlers.splice(i, 1);
            break;
        }
    }
};

this.runWillCloseHandlers = function() {
    _log.debug(">> ko.main.runWillCloseHandlers");
    while (_willCloseHandlers.length > 0) {
        var callback = _willCloseHandlers.pop();
        try {
            if (callback.object) {
                callback.handler.apply(callback.object);
            } else {
                callback.handler();
            }
        } catch(e) {
            _log.exception(e,"error when running '"+callback.handler+
                      "' shutdown handler (object='"+callback.object+"':");
        }
    }
    _log.debug("<< ko.main.runWillCloseHandlers");
}


// Callbacks on window used by goQuitApplication in moz toolkit.
// See KD 229 for details.

window.tryToClose = function() {
    _log.debug(">> window.tryToClose");
    var res = ko.main.runCanCloseHandlers();
    if (res) {
        // Fix bug 70859: Operations like Restart from Add-ons manager
        // send this message before starting the quit process.
        saveWorkspaceIfNeeded("try-to-close");
    }
    _log.debug("<< window.tryToClose: ret " + res.toString() + "\n");
    return res;
};

    
//************ End Shutdown Code



// #if BUILD_FLAVOUR == "dev"
function moz_user_pref(name, value) {
    const methName = {
        "boolean": "setBoolPref",
        "string": "setCharPref",
        "number": "setIntPref"
    };
    if (!(typeof(value) in methName)) {
        return;
    }
    var pref = Components.classes["@mozilla.org/preferences-service;1"]
                         .getService(Components.interfaces.nsIPrefBranch);
    pref[methName[typeof(value)]](name, value);
}

// nsIConsoleListener
var consoleListener = {
    observe: function(/* nsIConsoleMessage */ aMessage) {
        
        // Filter out unwanted strict warnings
        var regex = new RegExp('JavaScript Warning.*?(?:does not always return a value|redeclares argument|functions may be declared|test for equality|Update manifest had an unrecognised|reference to undefined property.*jquery.js\"|Trying to re-register CID .* already registered|Ignoring obsolete chrome registration modifier \'xpcnativewrappers\=no\'|Unknown property.*iframe\.css)');
        if (aMessage.message.match(regex) != null) return;
        
        dump(aMessage.message+"\n");
    }
}

function enableDevOptions() {
    // Enable dumps
    try  {
        moz_user_pref("browser.dom.window.dump.enabled", true);
        moz_user_pref("nglayout.debug.disable_xul_cache", true);
        moz_user_pref("javascript.options.strict", true);
        moz_user_pref("javascript.options.showInConsole", true);
        moz_user_pref("layout.css.report_errors", true);

        // Ensure caches and fast load are invalidated on the next restart.
        var nsXulAppInfo = Components.classes["@mozilla.org/xre/app-info;1"].getService(Components.interfaces.nsIXULAppInfo);
        var nsXulRuntime = nsXulAppInfo.QueryInterface(Components.interfaces.nsIXULRuntime);
        nsXulRuntime.invalidateCachesOnRestart();

        // get all console messages and dump them, then hook up the
        // console listener so we can dump console messages
        var cs = Components.classes['@mozilla.org/consoleservice;1'].getService(Components.interfaces.nsIConsoleService);
        var messages = new Object();
        cs.getMessageArray(messages, new Object());
        for (var i = 0; i < messages.value.length; i++) {
            consoleListener.observe(messages.value[i]);
        }
        cs.registerListener(consoleListener);
    }
    catch(e) { _log.exception(e,"Error setting Mozilla prefs"); }
}
// #endif

/* generaly this holds anything that requires user interaction
   on startup.  We want that stuff to happen after komodo's main
   windows is up and running.  There may be a thing or two otherwise
   that also needs to start late. */
function onloadDelay() {
    try {
        var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                        getService(Components.interfaces.nsIObserverService);
        observerSvc.addObserver(ko.main, "quit-application-requested", false);
        // Used by perf_timeline.perf_startup. Mark before
        // commandmentSvc.initialize() because that will immediately start
        // executing queued up commandments.
        ko.uilayout.onloadDelayed(); // if closed fullscreen, maximize

        // Fix for getting keybindings working in new windows - bug 87979.
        // TODO: Better fix needed?
        if (ko.windowManager.getWindows().length > 1) {
            // Bug 97191: Sometimes new windows don't start because
            // the toolbox hasn't been initialized
            ko.widgets.getWidgetAsync("toolbox2viewbox",
                                      function() { ko.toolbox2.applyKeybindings(); });
        }

        ko.workspace.restore();

        ko.history.init();

        ko.macros.eventHandler.hookOnStartup();
    } catch(ex) {
        _log.exception(ex);
    }

    // Let everyone know Komodo is fully started.
    setTimeout(function() {
        // This is a global event, no need to use the WindowObserverSvc
        var obSvc = Components.classes["@mozilla.org/observer-service;1"].
                getService(Components.interfaces.nsIObserverService);
        obSvc.notifyObservers(null, "komodo-ui-started", "");
        xtk.domutils.fireEvent(window, "komodo-ui-started");
    }, 0);
}

/**
 * Hack to detect if the native file icons "moz-icon://.js" are available -
 * bug 92863.
 */
function _check_native_mozicon_availability() {
    // We load a moz-icon image and then examine the width/height of it to see
    // if the images are available. Note that the icon must be in a portion of
    // the UI that is visible.
    let image = document.createElement("image");
    image.setAttribute("id", "_check_mozicon_availability");
    image.setAttribute("src", "moz-icon://.js");
    let komodo_vbox = document.getElementById('komodo-vbox');
    komodo_vbox.appendChild(image);
    window.setTimeout(function() {
        let image = document.getElementById("_check_mozicon_availability");
        ko.prefs.setBooleanPref("native_mozicons_available", image.boxObject.height > 0);
        image.parentNode.removeChild(image);
    }, 0);
}

/**
 * Set constant attributes for CSS
 */
function _set_docelement_css_classes() {
    var sysInfo = Cc["@mozilla.org/system-info;1"].getService(Ci.nsIPropertyBag2);
    var elem = document.documentElement;
    const props = {
        "os-name": "name",
        "os-version": "version",
        "cpu-arch": "arch",
    };
    for (let [attr, prop] in Iterator(props)) {
        let value = sysInfo.get(prop);
        if (value !== null) {
            elem.setAttribute(attr, value);
        }
    }
}

window.onload = function(event) {
    _log.debug(">> window.onload");

    JetPack.defineDeprecatedProperty(ko, "printing", "ko/printing");
    //dump(">>> window.onload\n");
    // XXX PLUGINS cannot be touched here, do it in the delayed onload handler below!!!
    try {
// #if BUILD_FLAVOUR == "dev"
        enableDevOptions();
// #endif

// #if PLATFORM == "linux"
        _check_native_mozicon_availability();
// #endif

        /* services needed for even the most basic operation of komodo */
        ko.keybindings.onload();

        /* set up things needed for CSS */
        try {
            _set_docelement_css_classes();
        } catch(ex) {
            _log.exception(ex);
        }

        // These routines use the handlers defined in this module.
        ko.mru.initialize();

        ko.views.onload();
        ko.widgets.getWidgetAsync("toolbox2viewbox",
                                  function() ko.toolbox2.onload());
        ko.projects.onload();

        ko.uilayout.onload();

        onloadDelay();
    } catch (e) {
        _log.exception(e,"Error doing KomodoOnLoad:");
        throw e;
    }
    _log.debug("<< window.onload");
}

ko.main.__koNum = null;

window.__defineGetter__("_koNum",
function()
{
    if (ko.main.__koNum == null) {
        // We need to give each window its unique ID before we start
        // hitting the history system.
        ko.main.__koNum = (Components.classes["@activestate.com/koInfoService;1"].
                          getService(Components.interfaces.koIInfoService).
                          nextWindowNum());
    }
    return ko.main.__koNum;
});
window.__defineSetter__("_koNum",
function(val)
{
    ko.main.__koNum = val;
});
        

var _deprecated_getters_noted = {};
var _log = ko.logging.getLogger("ko.main");
this.__deprecatedNameTest = function(deprecatedName, supportedName) {
    if (!(deprecatedName in _deprecated_getters_noted)) {
        _deprecated_getters_noted[deprecatedName] = true;
        _log.error("DEPRECATED: "
                   + deprecatedName
                   + ", please use "
                   + supportedName
                   + "\n");
    }
};

this.observe = function(subject, topic, data) {
    if (topic == "quit-application-requested") {
        var cancelQuit = subject;
        if ((cancelQuit instanceof Components.interfaces.nsISupportsPRBool) && cancelQuit.data) {
            return;
        }
        if (!this.runCanCloseHandlers()) {
            // Set the cancelData thing to true
            cancelQuit.QueryInterface(Components.interfaces.nsISupportsPRBool);
            cancelQuit.data = true;
        }
    }
};

}).apply(ko.main);

ko.mozhacks = {};
(function() { /* ko.mozhacks */
var _log = ko.logging.getLogger("ko.main");

// #if PLATFORM == "darwin"
var _openDialog = window.openDialog;
/**
 * openDialog
 *
 * http://bugs.activestate.com/show_bug.cgi?id=51068
 * dialogs on osx appear as sheets, but in our port we did
 * not want that to happen till we can refactor the ui.
 * unfortunate side affect of preventing the sheets caused
 * bug 51068.  This is an alternate fix for OSX only, that
 * will be refactored sometime during 4.X.
 *
 * Note: this is duplicated in ko.windowManager functions.
 */
window.openDialog = function openDialogNotSheet() {
    // fix features
    if (arguments.length < 2 || !arguments[2]) {
        arguments[2] = "chrome,dialog=no";
    } else if (arguments[2].indexOf("dialog") < 0) {
        arguments[2] = "dialog=no,"+arguments[2];
    }
    var args = [];
    for ( var i=0; i < arguments.length; i++ )
        args[i]=arguments[i];
    return _openDialog.apply(this, args);
}

// #endif

}).apply(ko.mozhacks);


/**
 * @deprecated since 7.0
 */
ko.logging.globalDeprecatedByAlternative('gPrefSvc', 'Components.classes["@activestate.com/koPrefService;1"].getService(Components.interfaces.koIPrefService)');
ko.logging.globalDeprecatedByAlternative("gPrefs", "ko.prefs");
ko.logging.globalDeprecatedByAlternative("log", "ko.logging.getLogger('')");
