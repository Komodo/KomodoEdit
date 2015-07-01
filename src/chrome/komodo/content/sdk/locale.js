(function() {
    
    const {Cc, Ci} = require("chrome");
    const bundleSvc = Cc["@mozilla.org/intl/stringbundle;1"].getService(Ci.nsIStringBundleService);
    const log = require("ko/logging").getLogger("ko_locale");
    //log.setLevel(10);
    
    const locale = this;
    
    var used = {};
    
    this.use = function(properties)
    {
        log.debug("Using " + properties);
        
        if (properties in used)
        {
            return used[properties];
        }
        
        var bundle = bundleSvc.createBundle(properties);
        return {
            get: function(name)
            {
                var args = Array.prototype.slice.call(arguments);
                args.shift();
                
                if ( ! args.length)
                {
                    if (args.length == 1 && Array.isArray(args[0]))
                    {
                        args = args[0];
                    }
                    
                    return bundle.GetStringFromName(name)
                }
                else
                {
                    return bundle.formatStringFromName(name, args, args.length);
                }
            }
        }
    }
    
    this.getBundleURI = function()
    {
        var stack = require("ko/console")._parseStack((new Error()).stack);
        var invoker = stack.slice(2,3)[0].fileName;
        
        var sdkUrl = require("sdk/url");
        
        try
        {
            var url = sdkUrl.URL(invoker);
        }
        catch (e)
        {
            log.error("Invoker does not have a valid URL: " + invoker, false);
            return false;
        }
        
        var bundleUri = url.protocol + "//" + url.host + "/locale/" + url.host + ".properties";
        return bundleUri;
    }
    
    this.get = function(name)
    {
        var bundleUri = this.getBundleURI();
        if ( ! bundleUri)
        {
            return name;
        }
        
        return this.use(bundleUri).get.apply(this, arguments);
    }
    
}).apply(module.exports);