/**
 * @module windows
 */
(function() {
    
    const {Cc, Ci, Cu}  = require("chrome");
    const log           = require("ko/logging").getLogger("sdk/windows");
    
    var _window;
    
    /**
     * Retrieve the main komodo window
     * 
     * @returns {Window}
     */
    this.getMain = function()
    {
        if (_window) return _window;
        
        var _window = window;
        var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
        let windows = wm.getEnumerator("Komodo");
        while (windows.hasMoreElements()) {
            _window = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
        }
        
        return _window;
    }
    
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
        
        windows = windows.concat(this.getWidgetWindows());
        
        return windows;
    }
    
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
    
    this.getBrowserWindows = function(_window, recursive = false)
    {
        _window = _window || window;
        
        var windows = [];
        var browsers = _window.document.querySelectorAll("browser");
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