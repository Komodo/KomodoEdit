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

var _log = ko.logging.getLogger("ko.main");
// a default logger that can be used anywhere (ko.main.log)
this.log = _log; 

function _komodoInitTemplateService(type) {
    var templateSvc = Components.classes["@activestate.com/koTemplateService?type="+type+";1"].getService();
    try {
        templateSvc.initializeUserTemplateTree();
    } catch(ex) {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                            getService(Components.interfaces.koILastErrorService);
        var errmsg = lastErrorSvc.getLastErrorMessage();
        alert("There was an error initializing your Komodo user "+
                     "settings directory with "+type+" template information: "+errmsg+
                     ". This may mean that you will not be able to create "+
                     "your own custom "+type+" templates. You will still be able "+
                     "to use Komodo's numerous standard "+type+" templates.");
    }
}

//
// This observer handles any notification pertinent
// to komodo the application (ie. startup/shutdown issues)
// that have no other place to be handled.
//
var _gKomodoObserver = null;
function _KomodoObserver() {
    ko.main.addUnloadHandler(this.shutdown, this);
    this.startup();
};
_KomodoObserver.prototype.constructor = _KomodoObserver;
_KomodoObserver.prototype.QueryInterface = function (iid) {
    if (!iid.equals(Components.interfaces.nsIObserver) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}
_KomodoObserver.prototype.startup = function()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    observerSvc.addObserver(this, "quit",false);
    observerSvc.addObserver(this, "open-url",false);
}
_KomodoObserver.prototype.shutdown = function()
{
    var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                    getService(Components.interfaces.nsIObserverService);
    try {
        observerSvc.removeObserver(this, "quit");
        observerSvc.removeObserver(this, "open-url");
    } catch(e) { /* moz already removed them */ _log.debug('quit '+e); }
    _gKomodoObserver = null;
}
_KomodoObserver.prototype.observe = function(subject, topic, data)
{
    _log.debug("_KomodoObserver: observed '"+topic+"' notification: data='"+data+"'\n");
    switch (topic) {
    case 'quit':
        window.setTimeout("goQuitApplication()", 0);
        break;
    case 'open-url': // see nsCommandLineServiceMac.cpp, bug 37787
        // This is also used by komodo macro API to open files from python
        var urllist = data.split('|'); //see asCommandLineHandler.js
        for (var i in urllist) {
            ko.open.URI(urllist[i]);
        }
        break;
    }
}

// #if BUILD_FLAVOUR == "dev"
var MozPref = new Components.Constructor("@mozilla.org/preferences;1","nsIPref");
function moz_user_pref(name, value) {
    var pref;
    if (typeof(value) == 'boolean') {
        pref = new MozPref();
        pref.SetBoolPref(name,value);
    } else
    if (typeof(value) == 'string') {
        pref = new MozPref();
        pref.SetCharPref(name,value);
    } else
    if (typeof(value) == 'number') {
        pref = new MozPref();
        pref.SetIntPref(name,value);
    }
}

// nsIConsoleListener
var consoleListener = {
    observe: function(/* nsIConsoleMessage */ aMessage) {
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

function configureDefaultEncoding() {
    // Setup Komodo default file encoding.
    // Komodo can only handle _some_ encodings out there. Typically
    // Komodo will use the current system encoding (as returned by
    // koInitService.getStartupEncoding()) as the default file encoding.
    // However if the system encoding is one that Komodo cannot handle
    // then we fallback to an encoding that we can handle.
    var initSvc = Components.classes["@activestate.com/koInitService;1"].
                  getService(Components.interfaces.koIInitService);
    var encodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                      getService(Components.interfaces.koIEncodingServices);
    // Determine the currently configured default file encoding.
    var useSystemEncoding = gPrefs.getBooleanPref("encodingEnvironment");
    var defaultEncoding = (useSystemEncoding ?
                           initSvc.getStartupEncoding() :
                           gPrefs.getStringPref("encodingDefault"));
    _log.debug("encoding: currently configured default is '"+
              defaultEncoding+"'");
    // Ensure the default encoding can be handled by Komodo.
    if (encodingSvc.get_encoding_index(defaultEncoding) == -1) {
        // The current default encoding is NOT supported.
        _log.debug("encoding: '"+defaultEncoding+"' is not supported");
        defaultEncoding = null;
        if (useSystemEncoding) {
            defaultEncoding = gPrefs.getStringPref("encodingDefault");
            _log.debug("encoding: try to fallback to 'encodingDefault' "+
                      "pref setting: '"+defaultEncoding+"'");
            if (encodingSvc.get_encoding_index(defaultEncoding) == -1) {
                // the default encoding in prefs is no good either
                _log.debug("encoding: '"+defaultEncoding+
                          "' is not supported either");
                defaultEncoding = null;
            }
        }
        if (! defaultEncoding) {
            // Western European is our last resort fallback.
            defaultEncoding = "iso8859-1";
            _log.debug("encoding: fallback to '"+defaultEncoding
                      +"' (Western European)");
        }
        gPrefs.setBooleanPref("encodingEnvironment", false);
    }
    //XXX Komodo code requires the encodingDefault string to be lowercase
    //    and while Komodo code has been updated to guarantee this there
    //    may still be uppercase user prefs out there.
    defaultEncoding = defaultEncoding.toLowerCase();
    //XXX Unfortunately we have to write the default encoding to user
    //    prefs even if the system encoding is being used because
    //    most Komodo code using "encodingDefault" does not honour
    //    "encodingEnvironment".
    gPrefs.setStringPref("encodingDefault", defaultEncoding);
}

/* generaly this holds anything that requires user interaction
   on startup.  We want that stuff to happen after komodo's main
   windows is up and running.  There may be a thing or two otherwise
   that also needs to start late. */
function onloadDelay() {
    try {
        // Used by perf_timeline.perf_startup. Mark before
        // commandmentSvc.initialize() because that will immediately start
        // executing queued up commandments.
        ko.trace.get().mark("startup complete");

        ko.uilayout.onloadDelayed(); // if closed fullscreen, maximize
        ko.run.output.initialize();

        // Openning the Start Page should be before commandment system init and
        // workspace restoration because it should be the first view opened.
        if (gPrefs.getBooleanPref("show_start_page")) {
            ko.open.startPage();
        }

        /* commandmentSvc needs the window to be alive */
        var commandmentSvc = Components.classes["@activestate.com/koCommandmentService;1"]
                           .getService(Components.interfaces.koICommandmentService);
        commandmentSvc.initialize();

        // the offer to restore the workspace needs to be after the
        // commandments system is initialized because the commandments mechanism
        // is how the determination of 'running in non-interactive mode' happens,
        // which the restoration step needs to know about.
        ko.workspace.restoreWorkspace();

        // handle window.arguments spec list
        if (window.arguments && window.arguments[0]) {
            var urllist = [];
            if (window.arguments[0] instanceof Components.interfaces.nsIDialogParamBlock) {
                var paramBlock = window.arguments[0].QueryInterface(Components.interfaces.nsIDialogParamBlock);
                if (paramBlock) {
                    urllist = paramBlock.GetString(0).split('|');
                }
            } else {
                urllist = window.arguments[0].split('|'); //see asCommandLineHandler.js
            }
            for (var i in urllist) {
                ko.open.URI(urllist[i]);
            }
        }
        
        ko.mozhacks.pluginContextMenu();

        // Initialize the Code Intel system *after* startup files are opened
        // via workspace restoration and 'open' commandments. See
        // _CodeIntelObserver.observe() for why.
        CodeIntel_Initialize();
        ko.uilayout.restoreTabSelections();

        // xul crash hack, see http://bugs.activestate.com/show_bug.cgi?id=30774
        // also see toolbar.xml bindings
        window.setTimeout("document.getElementById('toolbox_main').init();",10);
        ko.macros.eventHandler.hookOnStartup();
    } catch(ex) {
        _log.exception(ex);
    }
    try {
        observerSvc.notifyObservers(null, "komodo-ui-started", "");
    } catch(ex) {
        /* ignore this exception, there were no listeners for the event */
    }
}


window.onload = function(event) {
    // XXX PLUGINS cannot be touched here, do it in the delayed onload handler below!!!
    try {
// #if BUILD_FLAVOUR == "dev"
        enableDevOptions();
// #endif

        // XXX get rid of globals
        gPrefSvc = Components.classes["@activestate.com/koPrefService;1"].
                        getService(Components.interfaces.koIPrefService);
        gPrefs = gPrefSvc.prefs;

        configureDefaultEncoding();
        
        /* services needed for even the most basic operation of komodo */
        ko.keybindings.onload();

        /* setup observers */
        _gKomodoObserver = new _KomodoObserver();

        _komodoInitTemplateService("file");
        _komodoInitTemplateService("project");
        ko.mru.initialize();

        ko.views.onload();
        findtoolbar_onload();
        ko.projects.onload();

        FindResultsTab_OnLoad();
        ko.toolboxes.onload();
        ko.uilayout.onload();
        ko.lint.initialize();
        // anything that we want to do user interaction with at
        // startup should go into this timeout to let the window
        // onload handler finish.
        window.setTimeout(onloadDelay, 500);
    } catch (e) {
        _log.exception(e,"Error doing KomodoOnLoad:");
        throw e;
    }
}


/**
 * if you want to do something onUnload or onClose, then
 *  you have to register a handler function that takes no
 *  arguments.  This is called automaticaly.
 *  onOnload will call the handlers LIFO to reverse the
 *  order of initialization.
 */

var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                getService(Components.interfaces.nsIObserverService);

var _canQuitObservers = [];
var canQuitListener = {
    ignoreRequest : false,
    observe: function(subject, topic, data) {
        var cancelQuit = subject.QueryInterface(Components.interfaces.nsISupportsPRBool);
        cancelQuit.data = canQuitListener.cancelQuit();
        //_log.warn("observe cancelQuit? "+cancelQuit.data);
    },
    cancelQuit: function() {
        if (this.ignoreRequest) {
            return false;
        }
        for (var i=_canQuitObservers.length-1; i >= 0 ; i--) {
            try {
                var callback = _canQuitObservers[i];
                if (!callback.handler.apply(callback.object)) return true;
            } catch(e) {
                _log.exception(e,"error when running '"+callback.handler+
                          "' shutdown handler (object='"+callback.object+"':");
            }
        }
        this.ignoreRequest = true;
        return false;
    }
}
observerSvc.addObserver(canQuitListener, "quit-application-requested",false);

/**
 * addCanQuitHandler
 *
 * observer for watching the quit-application-requested notification, and
 * easily handling a response to it.
 *
 * @param <Function> fnCallback  callback returns a boolean
 * @param <Object> object for apply param
 */
this.addCanQuitHandler = function(handler, object /*=null*/) {
    if (typeof(object) == "undefined") object = null;
    var callback = new Object();
    callback.handler = handler;
    callback.object = object;
    _canQuitObservers.push(callback);
}


var _willQuitObservers = [];
var willQuitListener = {
    ignoreRequest : false,
    observe: function(subject, topic, data) {
        //_log.warn("willQuitListener called");
        willQuitListener.doQuit();
    },
    doQuit: function() {
        if (this.ignoreRequest) {
            return;
        }
        for (var i=0; i < _willQuitObservers.length; i++) {
            try {
                var callback = _willQuitObservers[i];
                callback.handler.apply(callback.object);
            } catch(e) {
                _log.exception(e,"error when running '"+callback.handler+
                          "' shutdown handler (object='"+callback.object+"':");
            }
        }
        this.ignoreRequest = true;
    }
}
observerSvc.addObserver(willQuitListener, "quit-application-granted",false);
/**
 * addWillQuitHandler
 *
 * simple observer for watching the quit-application-granted notification
 */
this.addWillQuitHandler = function(handler, object /*=null*/) {
    if (typeof(object) == "undefined") object = null;
    var callback = new Object();
    callback.handler = handler;
    callback.object = object;
    _willQuitObservers.push(callback);
}

/**
 * clearBrowserCache
 * clear the browser cache on shutdown (bug 67586)
 */
function clearBrowserCache() {
    var cacheService = Components.classes["@mozilla.org/network/cache-service;1"]
             .getService(Components.interfaces.nsICacheService);
    try {
        cacheService.evictEntries(Components.interfaces.nsICache.STORE_ANYWHERE);
    } catch(ex) {}
}
this.addWillQuitHandler(clearBrowserCache);

/*
    if you want to do something onUnload or onClose, then
    you have to register a handler function that takes no
    arguments.  This is called automaticaly.
    onOnload will call the handlers LIFO to reverse the
    order of initialization.
*/
var _unloadObservers = [];
window.onunload = function() {
    /* no further changes here, use registration functions below!

      we call onunload handlers LIFO
    */
    //_log.warn("window.onunload has been called\n");
    while (_unloadObservers.length > 0) {
        var callback = _unloadObservers.pop();
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
    //_log.debug("made it to the end of komodoOnUnload\n");
}


/**
 * addUnloadHandler
 * Register a routine to be called on Komodo shutdown.
 * To register a simple routine do this:
 *      ko.main.addUnloadHandler(<routine>)
 * To register an object method do this:
 *      ko.main.addUnloadHandler(this.<method>, this);
 *XXX Do we want to add an optional argument list to pass in?
 */
this.addUnloadHandler = function(handler, object /*=null*/) {
    if (typeof(object) == "undefined") object = null;
    var callback = new Object();
    callback.handler = handler;
    callback.object = object;
    _unloadObservers.push(callback);
}

window.tryToClose = function() {
    try {
        if (canQuitListener.cancelQuit()) {
            return false;
        }
        willQuitListener.doQuit();
    } catch(e) {
        log.exception(e);
    }
    return true;
}


}).apply(ko.main);

ko.mozhacks = {};
(function() { /* ko.mozhacks */
var _log = ko.logging.getLogger("ko.main");

/**
 * pluginContextMenu
 *
 * Verified still necessary with moz 1.8 branch - SMC
 * For some reason popups over the plugin are messed up until
 * the first context menu over mozilla is activated. It is apparently
 * due to popupNode not being initialized, so we do that here. See:
 *   http://www.xulplanet.com/references/elemref/ref_popup.html
 */
this.pluginContextMenu = function() {
    try {
        var toolbar = document.getElementById('toolbox_main');
        if (!toolbar) return;
        document.popupNode = toolbar;
    } catch(e) {
        _log.exception(e);
    }
}


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



// backwards compatibility APIs
var gPrefSvc = null;
var gPrefs = null;

__defineGetter__("gInfoSvc",
function()
{
    ko.logging.getLogger("ko.main").warn("gInfoSvc is deprecated, use getService");
    return Components.classes["@activestate.com/koInfoService;1"].
              getService(Components.interfaces.koIInfoService);
});

// XXX don't use this for new code, it's here to support
// older code
__defineGetter__("gObserverSvc",
function()
{
    ko.logging.getLogger("ko.main").warn("gObserverSvc is deprecated, use getService");
    return Components.classes["@mozilla.org/observer-service;1"].
            getService(Components.interfaces.nsIObserverService);
});

var KomodoRegisterOnUnloadHandler = ko.main.addUnloadHandler;
var KomodoRegisterCanCloseHandler = ko.main.addCanQuitHandler;
var KomodoRegisterPostCanCloseHandler = ko.main.addWillQuitHandler;
