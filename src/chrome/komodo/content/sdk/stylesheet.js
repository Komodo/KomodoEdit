(function() {
    
    const {Cc, Ci}  = require("chrome");
    const windows = require("ko/windows");
    const w = windows.getMain();
    const styleUtils = require("sdk/stylesheet/utils");
    const observerSvc = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);
    
    var loadedSheets = [];
    var globalSheets = [];
    
    var observer = {};
    observerSvc.addObserver(observer, "interface-scheme-changed", 0);
    
    observer.observe = () =>
    {
        for (let s of loadedSheets)
        {
            s.load(s.uri, s.window, s.type);
        }
    };

    windows.onLoad(onLoadWindow);

    var onLoadWindow = (window) =>
    {
        for (let sheet of globalSheets)
        {
            this.load(sheet.uri, window, sheet.type);
        }
    };

    this.load = (uri, window, type) =>
    {
        if ( ! window)
            window = w;
            
        this.unload(uri, window, type);

        styleUtils.loadSheet(window, uri, type);
        loadedSheets.push({uri: uri, window: window, type: type});
    };

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
                delete loadedSheets[x];
                break;
            }
        }
    };

    this.loadGlobal = (uri, type) =>
    {
        for (let window of windows.getAll())
        {
            this.load(uri, window, type);
        }
        
        globalSheets.push({uri: uri, type: type});
    };

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
                delete globalSheets[x];
                break;
            }
        }
    };
    
}).apply(module.exports);
