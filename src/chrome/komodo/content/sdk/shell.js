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
    
    this.getEnv = function()
    {   
        var env = {};
        var koEnviron = Cc["@activestate.com/koUserEnviron;1"].getService();
        var keys = koEnviron.keys();
        for (let key of keys)
            env[key] = koEnviron.get(key);
        
        return env;
    }
    
    this.lookup = function(command, env)
    {
        var ioFile = require("sdk/io/file");
        
        var isExecutable = function(str)
        {
            try
            {
                let file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
                file.initWithPath(str);
                
                if (file.isFile() && file.isExecutable())
                    return true;
            }
            catch (e) {}
            
            return false;
        }
        
        if (isExecutable(command))
            return command;
        
        env = env || this.getEnv();
        let commands = [command];
        if (require("sdk/system").platform == "WINNT" && "PATHEXT" in env)
        {
            var pathExt = env.PATHEXT.split(/;|:/);
            for (let ext of pathExt)
                commands.push(command + ext);
        }
        
        var paths = (env.PATH || "").split(/;|:/);
        for (let path of paths)
        {
            for (let cmd of commands)
            {
                let _path = ioFile.join(path, cmd);
                if (isExecutable(_path))
                    return _path;
            }
        }
        
        return false;
    }
    
    this.run = function(binary, args, opts)
    {
        var _opts = {
            cwd: this.getCwd(),
            env: this.getEnv()
        };
        
        var _ = require("contrib/underscore");
        _opts = _.extend(_opts, opts);
        
        binary = this.lookup(binary) || binary;
        
        // Start child process - `npm ls --depth=0`
        var proc = require("sdk/system/child_process");
        return proc.spawn(binary, args, _opts);
    }

}).apply(module.exports)