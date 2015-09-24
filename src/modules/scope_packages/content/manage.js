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
            scope("update", "Update Packages"),
            scope("uninstall", "Uninstall Packages"),
            scope("installed", "List Installed"),
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
    
    this.onSearchInstalled = function(query, uuid, onComplete)
    {
        packages._getInstalledPackages(function(pkgs) {
            if ( ! pkgs) return onComplete();
            
            if (query.length)
                pkgs = commando.filter(pkgs, query);
            
            var kinds = packages.getPackageKinds();
                
            for (let name in pkgs)
            {
                if ( ! pkgs.hasOwnProperty(name)) continue;
                let pkg = pkgs[name];
                
                try
                {
                    packages._renderPackage(pkg, uuid, {
                        descriptionPrefix: undefined,
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
                        descriptionPrefix: undefined,
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
    
    this.onSearchUninstall = function(query, uuid, onComplete)
    {
        packages._getInstalledPackages(function(pkgs) {
            if ( ! pkgs) return onComplete();
            
            if (query.length)
                pkgs = commando.filter(pkgs, query);
            
            var kinds = packages.getPackageKinds();
                
            for (let name in pkgs)
            {
                if ( ! pkgs.hasOwnProperty(name)) continue;
                let pkg = pkgs[name];
                
                try
                {
                    packages._renderPackage(pkg, uuid, {
                        descriptionPrefix: undefined,
                        command: this.uninstallPackage.bind(this, pkg),
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
                        descriptionPrefix: undefined,
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
        require("notify/notify").send(l.get("installing", pkg.name), "packages", {id: "packageInstall"});
        
        commando.block();
        
        var done = function(locale, priority = "notification")
        {
            window.clearTimeout(timeout);
            
            require("notify/notify").send(l.get(locale, pkg.name), "packages", {id: "packageInstall", priority: priority});
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
    
    this.uninstallPackage = function(pkg, callback)
    {
        require("notify/notify").send(l.get("uninstalling", pkg.name), "packages", {id: "packageUninstall"});
        
        commando.block();
        
        var done = function(locale, priority = "info")
        {
            window.clearTimeout(timeout);
            
            require("notify/notify").send(l.get(locale, pkg.name), "packages", {id: "packageUninstall"});
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
    
}).apply(module.exports);