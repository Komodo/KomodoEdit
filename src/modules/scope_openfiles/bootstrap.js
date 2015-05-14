const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import('resource://gre/modules/Services.jsm');

var startupData;

function loadIntoWindow(window) {
    try {
        var require = window.require;
        require.setRequirePath("scope-openfiles/", "chrome://scope-openfiles/content/");
        var commando = require("commando/commando");
        var system   = require("sdk/system");
        commando.registerScope("scope-openfiles", {
            name: "Open Files",
            description: "Access your opened files",
            icon: "koicon://ko-svg/chrome/icomoon/skin/files.svg",
            handler: "scope-openfiles/openfiles"
        });
    } catch (e) {
        Cu.reportError("Commando: Exception while registering scope 'openfiles'");
        Cu.reportError(e);
    }
}

function unloadFromWindow(window) {
    if (!window) return;
    var commando = window.require("commando/commando");
    commando.unregisterScope("project-commands");
}

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
