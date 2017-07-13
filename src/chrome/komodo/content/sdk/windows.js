/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Mediates with all the windows existing within Komodo
 *
 * A window can refer both to an internal window (eg. an iframe) as well as
 * a standalone application window
 *
 * @module ko/windows
 */
(function() {
    
    const {Cc, Ci, Cu}  = require("chrome");
    const log           = require("ko/logging").getLogger("sdk/windows");

    var onLoadCallbacks = { all: [] };
    var initialized = false;

    this.init = () =>
    {
        if (initialized)
            return;

        initialized = true;

        var w = this.getMain();
        w.addEventListener("window_opened", onWindowOpened);
    };

    var onWindowOpened = function(e)
    {
        var w = e.detail;
        if (w.location.href in onLoadCallbacks)
        {
            for (let callback of onLoadCallbacks[w.location.href])
            {
                callback(w);
            }
        }

        for (let callback of onLoadCallbacks.all)
        {
            callback(w);
        }
    };

    this.onLoad = function(href, callback)
    {
        if (typeof href == "function")
        {
            callback = href;
            href = "all";
        }

        if ( ! (href in onLoadCallbacks))
        {
            onLoadCallbacks[href] = [];
        }

        onLoadCallbacks[href].push(callback);
    };
    
    this.removeOnLoad = function(href, callback)
    {
        if (typeof href == "function")
        {
            callback = href;
            href = "all";
        }

        if ( ! (href in onLoadCallbacks))
        {
            return;
        }

        onLoadCallbacks[href] = onLoadCallbacks[href].filter((cb) => cb != callback);
    };

    /**
     * Retrieve the main komodo window
     * 
     * @returns {Window}
     */   
    this.getMain = function(w)
    {
        if ( ! w)
            w = window;

        var topHref = "chrome://komodo/content/komodo.xul";
        var topWindow = null;
        topWindow = w;
        
        var assignWindow = function(w, k)
        {
            while (( ! w.location || w.location.href != topHref) && w[k] && w[k] != w)
                w = w[k];
            return w;
        };
        
        var prevWindow = null;
        while (prevWindow != topWindow)
        {
            prevWindow = topWindow;
            topWindow = assignWindow(topWindow, "opener");
            topWindow = assignWindow(topWindow, "parent");
            topWindow = assignWindow(topWindow, "top");
        }
        
        if (topWindow.location.href != topHref)
            topWindow = null;
            
        if ( ! topWindow)
            topWindow = this.getMostRecent("Komodo");
            
        if ( ! topWindow)
            topWindow = this.getMostRecent();
        
        return topWindow;
    }
    
    /**
     * Retrieve all windows (excluding internal)
     * 
     * @returns {Array} 
     */
    this.getWindows = function(type = "")
    {
        var windows = [];
        
        var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
        let enumerated = wm.getEnumerator(type);
        while (enumerated.hasMoreElements()) {
            let w = enumerated.getNext().QueryInterface(Ci.nsIDOMWindow);
            windows.push(w);
        }
        
        return windows;
    }
    
    this.getWindowByUrl = function(url)
    {
        for (let w of this.getAll())
        {
            if (w.location.href == url)
                return w;
        }
        
        return false;
    }
    
    /**
     * Retrieve all windows (including internal)
     * 
     * @returns {Array} 
     */
    this.getAll = function()
    {
        var windows = [];
        
        var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
        let enumerated = wm.getEnumerator("");
        while (enumerated.hasMoreElements()) {
            let w = enumerated.getNext().QueryInterface(Ci.nsIDOMWindow);
            windows.push(w);
            windows = windows.concat(this.getBrowserWindows(w, true));
        }
        
        for (let w of this.getWidgetWindows())
        {
            windows.push(w);
            windows = windows.concat(this.getBrowserWindows(w, true));
        }
        
        return windows;
    }
    
    /**
     * Get windows belonging to widgets (side panes)
     * 
     * @returns {Array} 
     */
    this.getWidgetWindows = function()
    {
        var windows = [];
        var w = this.getMain();
        for (let id of w.ko.widgets.widgets)
        {
            try
            {
                windows.push(w.ko.widgets.getWidget(id).contentWindow);
            }
            catch (e)
            {
                log.debug("Cannot access widget " + id);
            }
        }
        
        return windows;
    }
    
    /**
     * Get browser windows residing within the given window
     * 
     * @param   {Window}    _window     Window to search in
     * @param   {Boolean}   recursive   Recursively search within each window
     * 
     * @returns {Array} 
     */
    this.getBrowserWindows = function(_window, recursive = false)
    {
        _window = _window || this.getMain();
        
        var windows = [];
        var browsers = _window.document.querySelectorAll("browser, iframe");
        for (let browser of browsers)
        {
            try
            {
                let w = browser.contentWindow;
                windows.push(w);
                
                if (recursive) windows = windows.concat(this.getBrowserWindows(w, true));
            }
            catch (e)
            {
                log.debug("Cannot access browser " + browser.id || null);
            } 
        }
        
        return windows;
    };
    
    /**
     * Pin window ontop of other windows including non Komodo windows.
     *
     * @param   {Window}    _window     The window to pin.
     */
    this.pin = (_window) =>
    {
        function getXULWindowForDOMWindow(win)
            win.QueryInterface(Ci.nsIInterfaceRequestor)
               .getInterface(Ci.nsIWebNavigation)
               .QueryInterface(Ci.nsIDocShellTreeItem)
               .treeOwner
               .QueryInterface(Ci.nsIInterfaceRequestor)
               .getInterface(Ci.nsIXULWindow)

        let rootWin = getXULWindowForDOMWindow(_window);
        let opener = _window.opener;
        let parentWin = ((opener && !opener.closed) ?
                         getXULWindowForDOMWindow(opener)
                         : null);
        Cc["@activestate.com/koIWindowManagerUtils;1"]
          .getService(Ci.koIWindowManagerUtils)
          .setOnTop(rootWin, parentWin, true);
    };
    
}).apply(module.exports);
