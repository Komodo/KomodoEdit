(function() {
    
    const {Cc, Ci, Cu}  = require("chrome");
    const prefs         = ko.prefs;

    const log           = require("ko/logging").getLogger("ko-shell");
    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    this.getCwd = function()
    {
        // Detect current working directory
        var partSvc = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
        var cwd = ko.uriparse.URIToPath(ko.places.getDirectory());
        if (partSvc.currentProject)
            cwd = partSvc.currentProject.liveDirectory;
            
        return cwd;
    }
    
    this.run = function(binary, args, opts)
    {
        // Create environment variables
        var env = {};
        var koEnviron = Cc["@activestate.com/koUserEnviron;1"].getService();
        var keys = koEnviron.keys({}, {});
        for (let key of keys)
            env[key] = koEnviron.get(key);
            
        var _opts = {
            cwd: this.getCwd(),
            env: env
        };
        
        var _ = require("contrib/underscore");
        _opts = _.extend(_opts, opts)
        
        // Start child process - `npm ls --depth=0`
        var proc = require("sdk/system/child_process");
        return proc.spawn(binary, args, _opts);
    }

}).apply(module.exports)