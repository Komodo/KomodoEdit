(function ()
{
    const {Cc, Ci}  = require("chrome");
    
    var profiler = Cc["@mozilla.org/tools/profiler;1"].getService(Ci.nsIProfiler);
    var prefs = require("ko/prefs");
    var enabled = prefs.getBoolean("profilerEnabled", false);
    var activeProfiler = null;
    
    this.enable = () =>
    {
        enabled = true;
    }
    
    this.disable = () =>
    {
        enabled = false;
    }
    
    this.start = (name = "") =>
    {
        if (name == "" && ! enabled)
            return;
        
        if (name)
        {
            if (prefs.getString("profilerEnabledName", "") !== name)
                return;
        }
        
        this.stop(activeProfiler);
        activeProfiler = name;
            
        var features = prefs.getString("profilerFeatures", "stackwalk,js").split(",");
        profiler.StartProfiler(
            prefs.getLong("profilerMemory", 10000000),
            prefs.getLong("profilerSampleRate", 1),
            features,
            features.length
        );
    };
    
    this.isActive = () =>
    {
        return profiler.IsActive();
    };
    
    this.stop = (name = "") =>
    {
        if ( ! profiler.IsActive() || name !== activeProfiler)
            return;
        
        profiler.StopProfiler();
    };
    
    this.pause = (name = "") =>
    {
        if ( ! profiler.IsActive() || name !== activeProfiler)
            return;
        
        profiler.PauseSampling();
    };
    
    this.resume = (name = "") =>
    {
        if ( ! profiler.IsPaused() || name !== activeProfiler)
            return;
        
        profiler.ResumeSampling();
    };
    
    this.save = (name = "") =>
    {
        if ( ! profiler.IsActive() || name !== activeProfiler)
            return;
        
        if (name == "")
            name = "unnamed";
            
        var sys = require("sdk/system");
        var koFile = require("ko/file");
        var profileDir = sys.pathFor("ProfD");
        var dir = koFile.join(profileDir, '..', 'profiler');
        koFile.mkpath(dir);
        
        var profileObj = profiler.getProfileData();
        var file = koFile.open(koFile.join(dir, `${name}-${Date.now()}.cleo`), "w");
        file.write(JSON.stringify(profileObj));
        file.close();
    };
    
}).apply(module.exports);