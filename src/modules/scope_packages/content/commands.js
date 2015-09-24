(function() {
    const log       = require("ko/logging").getLogger("commando-scope-packages-expand");
    const commando  = require("commando/commando");
    const packages  = require("./packages");
    const manage    = require("./manage");

    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    this.onSearch = function(query, uuid, onComplete)
    {
        var item = commando.getSubscope();
        var pkg =item.data.package;
        
        var results = [];
        
        if (item.data.installed)
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
    
    
}).apply(module.exports);
