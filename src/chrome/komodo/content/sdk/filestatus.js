(function() {
    
    const {Cc, Ci}  = require("chrome");
    
    var listeners = {};
    
    this.init = function()
    {
        var observer = {
            observe: (subject, topic, data) =>
            {
                var urllist = data.split('\n');
                for (let u of urllist) {
                    if (u in listeners)
                    {
                        for (let cb of listeners[u])
                            cb(u);
                    }
                }
                
                if ("all" in listeners)
                {
                    for (let cb of listeners.all)
                        cb(urllist);
                }
            }
        };
        
        var observerSvc = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);
        observerSvc.addObserver(observer, "file_status", false);
    };
    
    this.monitor = function(fileurls, callback)
    {
        if (typeof fileurls == "function")
        {
            callback = fileurls;
            fileurls = ["all"];
        }
        
        if ( ! Array.isArray(fileurls))
            fileurls = [fileurls];
            
        for (let url of fileurls)
        {
            if ( ! (url in listeners))
                listeners[url] = [];
                
            listeners[url].push(callback);
        }
    };
    
    this.unmonitor = function(fileurls, callback)
    {
        if (typeof fileurls == "function")
        {
            callback = fileurls;
            fileurls = ["all"];
        }
        
        if ( ! Array.isArray(fileurls))
            fileurls = [fileurls];
            
        for (let url of fileurls)
        {
            if ( ! (url in listeners))
                continue;
                
            listeners[url] = listeners[url].filter((cb) => cb != callback);
        }
    };
    
    this.init();
    
}).apply(module.exports);