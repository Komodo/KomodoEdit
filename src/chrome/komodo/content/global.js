/**
 * This library contains methods to facilitate communication between all windows,
 * regardless of their top level. It will persist across the entire running
 * Komodo instance.
 *
 * Not to be confused with globals.js, which is horribly named and is really
 * just a bootstrapper for new Komodo windows
 */

const [Cc, Ci, Cu] = [Components.classes, Components.interfaces, Components.utils];
const {Services} = Cu.import("resource://gre/modules/Services.jsm");
const observerSvc = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);
                        
Services.scriptloader.loadSubScript("chrome://komodo/content/sdk/console.js");

const EXPORTED_SYMBOLS = ["global"];

var global = {};
(function() {
    
    var events = {};
    var loaded = [];

    var init = () =>
    {
        observerSvc.addObserver(observer, "toplevel-window-ready", false);
    };
    
    var observer = {
        observe: (subject, topic, data) =>
        {
            switch (topic)
            {
                case "toplevel-window-ready":
                    loadTopWindow(subject);
                    break;
            }
        }
    };

    var loadTopWindow = (w) =>
    {
        if (loaded.indexOf(w) != -1)
            return;

        loaded.push(w);

        var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
        var _w = wm.getMostRecentWindow("Komodo");

        w.addEventListener("unload", () => delete loaded[w]);
        
        // Prepare window.console so jetpack doesnt instantiate its own
        w.console = console;

        var mainWindow = w.arguments && w.arguments.length > 0 &&
                          w.arguments[0] && typeof w.arguments[0] == "object" &&
                          w.arguments[0].mainWindow;
        
        if ( ! mainWindow && _w && _w != w)
        {
            injectModules(_w, w);
        }
        else
        {
            // Jetpack must be loaded after window.ko has been created (so that it
            // knows how to get things into the right scope, for backwards compat)
            w.global = global;
            Services.scriptloader.loadSubScript("chrome://komodo/content/jetpack.js", w);
            if ( ! w.ko)
                w.ko = {};
            w.JetPack.defineLazyProperty(w.ko, "logging", "ko/logging", true);
        }
        
        // Any sub windows should get it modules from the top window
        w.addEventListener("DOMWindowCreated", (event) =>
        {
            var _w = event.originalTarget || event.target;
            if ("defaultView" in _w)
                _w = _w.defaultView;

            injectModules(w, _w);
            injectOpenHandler(_w);
        });

        injectOpenHandler(w);
    };

    var injectModules = (sourceWindow, targetWindow) =>
    {
        if (sourceWindow == targetWindow)
            return;
        
        for (let k of ["console", "require", "JetPack", "global"])
        {
            if (k in targetWindow)
                delete targetWindow[k];
            
            targetWindow[k] = sourceWindow[k];
        }

        if ( ! targetWindow.ko)
            targetWindow.ko = {};
        targetWindow.JetPack.defineLazyProperty(targetWindow.ko, "logging", "ko/logging", true);
    };
    
    var injectOpenHandler = (targetWindow) =>
    {
        var tw = targetWindow;
        var _openDialog = tw.openDialog;
        tw.openDialog = (url, name) =>
        {
            var _w;
            if (name)
                _w = tw.require("ko/windows").getWindowByName(name);

            if (_w)
                _w.focus();
            else
                _w = _openDialog.apply(tw, arguments);
            return _w;
        };
    };
    
    this.triggerEvent = (eventName, eventData) =>
    {
        if ( ! (eventName in events))
            return;
        
        for (let eventAction of events[eventName])
        {
            eventAction.call(null, eventData);
        }
    };
    
    this.addEventListener = (eventName, eventAction) =>
    {
        if ( ! (eventName in events))
        {
            events[eventName] = [];
        }
        
        events[eventName].push(eventAction);
    };
    
    this.removeEventListener = (eventName, eventAction) =>
    {
        if (eventName in events)
            events[eventName].filter((v) => v != eventAction);
    };
    
    init();
    
}).apply(global);