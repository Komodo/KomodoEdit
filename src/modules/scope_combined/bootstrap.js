const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import('resource://gre/modules/Services.jsm');

var startupData;

function loadIntoWindow(window) {
    var require = window.require;
    require.setRequirePath("scope-combined/", "chrome://scope-combined/content/");
    var commando = require("commando/commando");
    var system   = require("sdk/system");
    
    try {
        commando.registerScope("scope-combined", {
            name: "Everything",
            description: "Access all scopes at once",
            weight: 100,
            icon: "koicon://ko-svg/chrome/icomoon/skin/search3.svg",
            handler: "scope-combined/everything",
            quickscope: true
        });
    } catch (e) {
        Cu.reportError("Commando: Exception while registering scope 'Combined - Everything'");
        Cu.reportError(e);
    }

    try {
        commando.registerScope("scope-combined-toolscmds", {
            name: "Tools and Commands",
            icon: "koicon://ko-svg/chrome/icomoon/skin/cogs.svg",
            handler: "scope-combined/toolscommands",
            keybindTransit: "cmd_invokeTool"
        });
    } catch (e) {
        Cu.reportError("Commando: Exception while registering scope 'Combined - Tools & Commands'");
        Cu.reportError(e);
    }
}

function unloadFromWindow(window) {
    if (!window) return;
    var commando = window.require("commando/commando");
    commando.unregisterScope("scope-combined");
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
