(function() {
    
    const {Cc, Ci, Cu} = require("chrome");
    const log          = require("ko/logging").getLogger("commando-scope-packages-manage");
    const commando     = require("commando/commando");
    const packages     = require("./packages");
    const l            = require("ko/locale");
    
    //log.setLevel(10);
    
    var scope = function(id, name, tip) {
        return {
            id: "packages-" + id,
            name: name,
            tip: tip,
            scope: "scope-packages",
            isScope: true
        }
    }
    
    var entry = function(id, name, command) {
        return {
            id: "entry-" + id,
            name: name,
            scope: "scope-packages",
            command: command
        }
    }
    
    var structure = {
        "manage": [
            scope("update", "List Update Available"),
            scope("installed", "List Installed"),
            scope("system", "List System Addons", "These addons come with Komodo and can be disabled but not uninstalled"),
            scope("disabled", "List Disabled"),
            scope("outdated", "List Outdated", "Packages that could potentially cause problems")
        ]
    }
    
    this.onSearch = function(query, uuid, onComplete)
    {
        var subscope = commando.getSubscope();
        var id = subscope.id.substr(9)
        
        if (id in structure)
        {
            commando.renderResults(structure[id], uuid);
        }
        
        var methodName = "onSearch" + id.charAt(0).toUpperCase() + id.slice(1);
        if (methodName in this)
        {
            this[methodName](query, uuid, onComplete);
            return;
        }
        
        onComplete();
    }

    this.onSearchSystem = function(query, uuid, onComplete)
    {
        return _onSearchInstalled(query, uuid, onComplete, true, false);
    }
    
    this.onSearchInstalled = function(query, uuid, onComplete)
    {
        return _onSearchInstalled(query, uuid, onComplete, false, false);
    }

    this.onSearchDisabled = function(query, uuid, onComplete)
    {
        return _onSearchInstalled(query, uuid, onComplete, -1, true);
    }

    var _onSearchInstalled = function(query, uuid, onComplete, system = false, disabledOnly = false)
    {
        packages._getInstalledPackages(function(pkgs) {
            if ( ! pkgs) return onComplete();

            if (query.length)
                pkgs = commando.filter(pkgs, query);

            var kinds = packages.getPackageKinds();

            for (let name in pkgs)
            {
                if ( ! pkgs.hasOwnProperty(name))
                    continue;

                let pkg = pkgs[name];
                
                if (system != -1 && packages.isSystemAddon(pkg.id) != system)
                    continue;
                
                if (disabledOnly && ! packages.isDisabled(pkg.id))
                    continue;

                try
                {
                    packages._renderPackage(pkg, uuid, {
                        command: commando.expandResult.bind(commando)
                    });
                }
                catch (e)
                {
                    log.exception(e, "Failed parsing package info");
                }
            }
        }.bind(this))
    }
    
    this.onSearchOutdated = function(query, uuid, onComplete)
    {
        packages._getInstalledPackages(function(pkgs) {
            if ( ! pkgs) return onComplete();
            
            if (query.length)
                pkgs = commando.filter(pkgs, query);
            
            for (let name in pkgs)
            {
                if ( ! pkgs.hasOwnProperty(name)) continue;
                
                let pkg = pkgs[name];
                if (pkg.data.isCompatible && pkg.data.isPlatformCompatible) continue;
                
                try
                {
                    packages._renderPackage(pkg, uuid, {
                        command: commando.expandResult.bind(commando)
                    });
                }
                catch (e)
                {
                    log.exception(e, "Failed parsing package info");
                }
            }
        }.bind(this))
    }
    
    this.onSearchUpdate = function(query, uuid, onComplete)
    {
        packages._getUpgradablePackages(function(pkgs) {
            if ( ! pkgs) return onComplete();
            
            if (query.length)
                pkgs = commando.filter(pkgs, query);
                
            for (let name in pkgs)
            {
                if ( ! pkgs.hasOwnProperty(name)) continue;
                let pkg = pkgs[name];
                
                try
                {
                    packages._renderPackage(pkg, uuid, {
                        description: pkg.currentVersion + " > " + pkg.availableVersion,
                        command: this.installPackage.bind(this, pkg),
                    });
                }
                catch (e)
                {
                    log.exception(e, "Failed parsing package info");
                }
            }
        }.bind(this))
    }
    
    this.installPackage = function(pkg, callback)
    {
        require("notify/notify").interact(l.get("installing", pkg.name), "packages", {id: "packageInstall"});
        
        commando.block();
        
        var done = function(locale, priority = "notification")
        {
            window.clearTimeout(timeout);
            
            require("notify/notify").interact(l.get(locale, pkg.name), "packages", {id: "packageInstall", priority: priority});
            commando.unblock();
            packages.clearCaches();
            
            if (callback)
                callback();
            else
                commando.refresh();
        };
        
        var timeout = window.setTimeout(done.bind(this, "installTimeout", "warning"), 10000);
        packages._installPackage(pkg, done.bind(this, "installed"), done.bind(this, "installFailed", "error"));
    }
    
    this.installPackageByUrl = function(url, callback)
    {
        require("notify/notify").interact(l.get("installing", "addon"), "packages", {id: "packageInstall"});
        
        if (commando.isOpen()) commando.block();
        
        var done = function(locale, priority = "notification")
        {
            window.clearTimeout(timeout);
            
            require("notify/notify").interact(l.get(locale, "addon"), "packages", {id: "packageInstall", priority: priority});
            if (commando.isOpen()) commando.unblock();
            packages.clearCaches();
            
            if (callback)
                callback();
            else
            {
                if (commando.isOpen()) commando.refresh();
            }
        };
        
        var timeout = window.setTimeout(done.bind(this, "installTimeout", "warning"), 10000);
        packages._installXpi(url, done.bind(this, "installed"), done.bind(this, "installFailed", "error"));
    }
    
    this.uninstallPackage = function(pkg, callback)
    {
        require("notify/notify").interact(l.get("uninstalling", pkg.name), "packages", {id: "packageUninstall"});
        
        commando.block();
        
        var done = function(locale, priority = "info")
        {
            window.clearTimeout(timeout);
            
            require("notify/notify").interact(l.get(locale, pkg.name), "packages", {id: "packageUninstall"});
            commando.unblock();
            packages.clearCaches();
            
            if (callback)
                callback();
            else
                commando.refresh();
        };
        
        var timeout = window.setTimeout(done.bind(this, "uninstallTimeout", "warning"), 10000);
        packages._uninstallPackage(pkg, done.bind(this, "uninstalled"), done.bind(this, "uninstallFailed", "error"));
    }
    
    this.updateAll = function()
    {
        packages._getUpgradablePackages(function(pkgs) {
            var _pkgs = [];
            for (let name in pkgs)
            {
                if ( ! pkgs.hasOwnProperty(name)) continue;
                _pkgs.push(pkgs[name]);
            }
            _updateAll(_pkgs);
        });
    }
    
    this.toggleAddon = function(pkg)
    {
        commando.block();
        packages._toggleAddon(pkg.data);
        commando.refresh();

        require("sdk/timers").setTimeout(() => commando.unblock(), 500);
    }

}).apply(module.exports);