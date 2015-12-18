const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import('resource://gre/modules/Services.jsm');

var startupData;
var observer = {};

function loadIntoWindow(window) {
    try {
        window.require.setRequirePath("lintresults/", "chrome://lintresults/content/");
        
        var prefSvc = Cc["@activestate.com/koPrefService;1"].getService(Ci.koIPrefService);
        prefSvc.prefs.prefObserverService.addObserver(observer, 'editUseLinting', 0);
        
        var timer;
        var updater = function(now) {
            if (now !== true)
            {
                window.clearTimeout(timer);
                timer = window.setTimeout(updater.bind(null,true), 100);
                return;
            }
            window.require("lintresults/lintresults").update()
        };
        
        observer.observe = updater;
        
        window.addEventListener('current_view_changed', updater, false);
        window.addEventListener('current_view_check_status', updater, false);
        window.addEventListener('current_view_lint_results_done', updater, false);
        
    } catch (e) {
        Cu.reportError("lintresults: Exception while initializing");
        Cu.reportError(e);
    }
}

function unloadFromWindow(window) {
    if (!window) return;
    
    var prefSvc = Cc["@activestate.com/koPrefService;1"].
                  getService(Ci.koIPrefService);
    prefSvc.prefs.prefObserverService.removeObserver(observer, 'editUseLinting');
    
    window.removeEventListener('current_view_check_status', updater);
    window.removeEventListener('current_view_lint_results_done', updater);
}

/* Boilerplate below */

var windowListener = {
    onOpenWindow: function(aWindow) {
        // Wait for the window to finish loading
        let domWindow = aWindow.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIDOMWindowInternal || Ci.nsIDOMWindow);
        domWindow.addEventListener("komodo-post-startup", function onLoad() {
            domWindow.removeEventListener("komodo-post-startup", onLoad, false);
            loadIntoWindow(domWindow);
        }, false);
    },

    onCloseWindow: function(aWindow) {},
    onWindowTitleChange: function(aWindow, aTitle) {}
};

function startup(data, reason) {
    startupData = data;

    // Load into any existing windows
    let windows = Services.wm.getEnumerator("Komodo");
    while (windows.hasMoreElements()) {
        let domWindow = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
        loadIntoWindow(domWindow);
    }

    // Load into any new windows
    Services.wm.addListener(windowListener);
}

function shutdown(data, reason) {
    // When the application is shutting down we normally don't have to clean
    // up any UI changes made
    if (reason == APP_SHUTDOWN) return;

    // Stop listening for new windows
    Services.wm.removeListener(windowListener);

    // Unload from any existing windows
    let windows = Services.wm.getEnumerator("Komodo");
    while (windows.hasMoreElements()) {
        let domWindow = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
        unloadFromWindow(domWindow);
    }
}

function install(data, reason) {}

function uninstall(data, reason) {}
