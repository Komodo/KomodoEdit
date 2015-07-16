(function() {
    
    const {Cc, Ci, Cu}  = require("chrome");
    const log           = require("ko/logging").getLogger("sdk/windows");
    
    var _window;
    
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
    
}).apply(module.exports);