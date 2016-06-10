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
    
    /**
     * Retrieve the main komodo window
     * 
     * @returns {Window}
     */
    this.getMain = function()
    {
        // Return the topWindow global if it's set, this is the topmost window
        // as detected by jetpack.js
        if (topWindow)
        {
            return topWindow;
        }
        
        var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
        return wm.getMostRecentWindow("Komodo");
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
    }
    
}).apply(module.exports);