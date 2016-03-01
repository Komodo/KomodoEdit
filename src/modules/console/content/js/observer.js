window.addEventListener('load', function() {
    window.document.documentElement.classList.add("hud");
    
    var obs = Components.classes["@mozilla.org/observer-service;1"].getService(Components.interfaces.nsIObserverService);
    var consoleSdk = require("ko/console");
    
    obs.addObserver(
    {
        observe: function(aMessage, aTopic)
        {
            aMessage = aMessage.wrappedJSObject;
            
            var len = 0;
            var args = aMessage.arguments;
            var data = args.map(function(arg)
            {
                len++;
                return consoleSdk._stringify(arg, true);
            }).join(" ");
            if (len === 1) data = aMessage.arguments[0];
            
            var details = null;
            var severity = Components.interfaces.koINotification.SEVERITY_INFO;

            if (aMessage.level == "timeEnd")
                details = "'" + aMessage.timer.name + "' " + aMessage.timer.duration + "ms";
            if (aMessage.level == "time")
                details = "'" + aMessage.timer.name + "' @ " + (new Date());
            if (aMessage.level == "trace")
                details = "trace" + "\n" + consoleSdk._formatTrace(aMessage.stacktrace);
                
            var type = aMessage.level;
            if (["log", "info", "warn", "error", "exception"].indexOf(aMessage.level) == -1)
            {
                type = "log";
                if ((typeof data) == "string")
                    data = aMessage.level + ": " + data;
            }
                
            if ((typeof data) != "object" && details) data = data + "\n" + details;
            window.app.print(type, data);
        }
    }, "console-api-log-event", false);
});