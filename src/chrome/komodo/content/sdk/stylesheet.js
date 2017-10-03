/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Interface to work with stylesheets. Easily add new sharing tool to the Komodo command set and UI
 *
 * @module ko/stylesheet
 */
(function() {

    const {Cc, Ci}  = require("chrome");
    const windows = require("ko/windows");
    const w = windows.getMain();
    const styleUtils = require("sdk/stylesheet/utils");
    const observerSvc = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);

    var loadedSheets = [];
    var globalSheets = [];

    var init = () =>
    {
        var observer = {};
        observerSvc.addObserver(observer, "interface-scheme-changed", 0);

        observer.observe = () =>
        {
            for (let s of loadedSheets)
            {
                this.load(s.uri, s.window, s.type);
            }

            for (let s of globalSheets)
            {
                this.loadGlobal(s.uri, s.type);
            }
        };

        windows.onLoad(onLoadWindow);
    };

    var onLoadWindow = (window) =>
    {
        for (let sheet of globalSheets)
        {
            this.load(sheet.uri, window, sheet.type);
        }
    };

    /**
     * Load a stylesheet in the given window
     * 
     * @param {string}  uri     Stylesheet URI
     * @param {Window}  window  DOM Window
     * @param {string}  type=user|agent|author
     */
    this.load = (uri, window, type) =>
    {
        if ( ! window)
            window = w;

        this.unload(uri, window, type);

        styleUtils.loadSheet(window, uri, type);
        loadedSheets.push({uri: uri, window: window, type: type});
    };

    /**
     * Unload a stylesheet in the given window
     * 
     * @param {string}  uri     Stylesheet URI
     * @param {Window}  window  DOM Window
     * @param {string}  type=user|agent|author
     */
    this.unload = (uri, window, type) =>
    {
        if ( ! window)
            window = w;

        styleUtils.removeSheet(window, uri, type);

        for (let x=0;x<loadedSheets.length;x++)
        {
            let s = loadedSheets[x];
            if (s.uri == uri && s.window == window && s.type == type)
            {
                loadedSheets.splice(x, 1);
                break;
            }
        }
    };

    /**
     * Load the given stylesheet in all windows
     * 
     * @param {string}  uri     Stylesheet URI
     * @param {string}  type=user|agent|author
     */
    this.loadGlobal = (uri, type) =>
    {
        this.unloadGlobal(uri, type);

        for (let window of windows.getAll())
        {
            this.load(uri, window, type);
        }

        globalSheets.push({uri: uri, type: type});
    };

    /**
     * Unload the given stylesheet in all windows
     * 
     * @param {string}  uri     Stylesheet URI
     * @param {string}  type=user|agent|author
     */
    this.unloadGlobal = (uri, type) =>
    {
        for (let window of windows.getAll())
        {
            this.unload(uri, window, type);
        }

        for (let x=0;x<globalSheets.length;x++)
        {
            let s = loadedSheets[x];
            if (s.uri == uri && s.type == type)
            {
                globalSheets.splice(x, 1);
                break;
            }
        }
    };

    init();

}).apply(module.exports);
