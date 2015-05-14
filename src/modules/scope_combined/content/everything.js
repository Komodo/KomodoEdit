(function() {
    const log       = require("ko/logging").getLogger("commando-scope-combined-everything")
    const commando  = require("commando/commando");

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var getScopes = function()
    {
        return commando.getRegisteredScopes();
    }

    this.onSearch = function(query, uuid, onComplete)
    {
        var subscope = commando.getSubscope();
        
        if ( ! subscope && query == "")
            return this.showScopes(uuid, onComplete);
        
        var scopes = getScopes();
        var _scopes = {};
        var length = 0;
        for (let id in scopes)
        {
            if (id.indexOf("scope-combined") != -1 || id == "scope-shell") continue;
            if (subscope && subscope.scope != id) continue;
            _scopes[id] = scopes[id];
            length++;
        }

        for (let id in _scopes)
        {
            let scope = _scopes[id];
            require(scope.handler).onSearch(query, uuid, function()
            {
                if (--length === 0) onComplete();
            }.bind(this));
        }
    }
    
    this.showScopes = function(uuid, onComplete)
    {
        var scopes = getScopes();
        var _scopes = [];
        var results = [];
        for (let id in scopes)
        {
            if (id.indexOf("scope-combined") != -1) continue;
            _scopes.push(scopes[id]);
        }
        
        _scopes.sort(function(a,b) { return a.name.localeCompare(b.name) > 0 ? 1 : -1; });
        for (let x=0;x<_scopes.length;x++)
        {
            let scope = _scopes[x];
            results.push({
                id: scope.id,
                name: scope.name,
                description: scope.description || "",
                icon: scope.icon,
                scope: "scope-everything",
                data: {
                    isScope: true
                }
            });
        }
        
        commando.renderResults(results, uuid);
        onComplete();
    }

    this.onSelectResult = function(selectedItems)
    {
        var scopeItems = {};
        var scopes = getScopes();
        
        var selected = commando.getSelectedResult();
        if (selected.data.isScope)
        {
            commando.selectScope(selected.id);
            return;
        }

        for (let item in selectedItems)
        {
            let scopeId = selectedItems[item].resultData.scope;
            
            if ( ! (scopeId in scopes))
                continue;

            if ( ! (scopeId in scopeItems))
                scopeItems[scopeId] = [];
            scopeItems[scopeId].push(selectedItems[item]);
        }

        for (let scopeId in scopeItems)
        {
            let handler = require(scopes[scopeId].handler);

            if ("onSelectResult" in handler)
                handler.onSelectResult(scopeItems[scopeId]);
        }
    }

}).apply(module.exports);
