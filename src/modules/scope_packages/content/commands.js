(function() {
    const log       = require("ko/logging").getLogger("commando-scope-packages-expand");
    const commando  = require("commando/commando");
    const packages  = require("./packages");
    const manage    = require("./manage");

    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    this.onSearch = function(query, uuid, onComplete)
    {
        var item = commando.getSubscope();
        var pkg = item.data.package;
        
        var results = [];
        
        var isSystemAddon = packages.isSystemAddon(pkg.id);

        if (item.data.installed)
        {
            if (! isSystemAddon)
            {
                results.push({
                    id: "pkg-uninstall",
                    name: "Uninstall",
                    scope: "scope-packages",
                    command: manage.uninstallPackage.bind(manage, pkg, commando.navBack.bind(commando))
                });
                results.push({
                    id: "pkg-update",
                    name: item.data.upgradeable ? "Update" : "Reinstall",
                    scope: "scope-packages",
                    command: manage.installPackage.bind(manage, pkg)
                });
            }
            if (pkg.kind == packages.ADDONS)
            {
                results.push({
                    id: "pkg-toggle",
                    name: item.data.disabled ? "Enable" : "Disable",
                    scope: "scope-packages",
                    command: manage.toggleAddon.bind(manage, pkg)
                });
            }
            this._appendOptions(pkg, uuid);
        }
        else
        {
            results.push({
                id: "pkg-install",
                name: "Install",
                scope: "scope-packages",
                command: manage.installPackage.bind(manage, pkg, commando.navBack.bind(commando))
            });
        }
        
        commando.renderResults(results, uuid);
        onComplete();
    }
    
    this._appendOptions = function (pkg, uuid)
    {
        if ( ! pkg.mock)
        {
            packages._getInstalledPackagesByKind(pkg.kind, function(installed)
            {
                if ( ! (pkg.id in installed)) return;
                this._appendOptions(installed[pkg.id], uuid);
            }.bind(this));
            return;
        }
        
        if ( ! pkg.data.optionsURL) return;
        
        commando.renderResult({
            id: "pkg-options",
            name: "Options",
            scope: "scope-packages",
            command: function()
            {
                commando.hide();
                require("ko/windows").getMain().openDialog(pkg.data.optionsURL, "chrome,titlebar,toolbar,centerscreen,modal");
            }
        }, uuid);
    }
    
    
}).apply(module.exports);
