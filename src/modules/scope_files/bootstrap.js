const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import('resource://gre/modules/Services.jsm');

var startupData;

function loadIntoWindow(window) {
    try {
        var require = window.require;
        require.setRequirePath("scope-files/", "chrome://scope-files/content/");
        var commando = require("commando/commando");
        var system   = require("sdk/system");
        commando.registerScope("scope-files", {
            name: "Files",
            description: "Search through your project files",
            icon: "koicon://ko-svg/chrome/icomoon/skin/file5.svg",
            handler: "scope-files/files",
            keybindTransit: "cmd_goToFile"
        });
    } catch (e) {
        Cu.reportError("Commando: Exception while registering scope 'Files'");
        Cu.reportError(e);
    }

    try {
        var component = startupData.installPath.clone();
        component.append("components");
        component.append("component.manifest");

        var registrar = Components.manager.QueryInterface(Ci.nsIComponentRegistrar);
        registrar.autoRegister(component);
    } catch (e) {
        Cu.reportError("Commando: Exception while registering component for 'Files' scope");
        Cu.reportError(e);
    }

    window.require("scope-files/files").prepare();
}

function unloadFromWindow(window) {
    if (!window) return;
    var commando = window.require("commando/commando");
    commando.unregisterScope("project-files");
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
        Cu.reportError("====== HAS WINDOW");
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
