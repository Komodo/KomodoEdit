window.addEventListener('load', function() {
    window.document.documentElement.classList.add("hud");
    require("ko/windows").getMain().ko.skin._loadVirtualStyle("scheme-skinning-partial", window);
    
    var obs = Components.classes["@mozilla.org/observer-service;1"].getService(Components.interfaces.nsIObserverService);
    var consoleSdk = require("ko/console");
    
    obs.addObserver(
    {
        observe: function(aMessage, aTopic)
        {
            aMessage = aMessage.wrappedJSObject;
            
            var args = aMessage.arguments;
            var data = args.map(function(arg)
            {
                return consoleSdk._stringify(arg, true);
            }).join(" ");
            
            var details = null;
            var severity = Components.interfaces.koINotification.SEVERITY_INFO;

            if (aMessage.level == "timeEnd")
                details = "'" + aMessage.timer.name + "' " + aMessage.timer.duration + "ms";
            if (aMessage.level == "time")
                details = "'" + aMessage.timer.name + "' @ " + (new Date());
            if (aMessage.level == "trace")
                details = "trace" + "\n" + consoleSdk._formatTrace(aMessage.stacktrace);
                
            var type = aMessage.level;
            if (["info", "warn", "error", "exception"].indexOf(aMessage.level) == -1)
            {
                type = "debug";
                data = aMessage.level + ": " + data;
            }
                
            if (details) data = data + "\n" + details;
            window.app.print(type, data, true);
        }
    }, "console-api-log-event", false);
});