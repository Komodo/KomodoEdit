(function() {
    const log       = require("ko/logging").getLogger("commando-scope-combined-toolscommands")
    const commando  = require("commando/commando");

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var getScopes = function()
    {
        return commando.getRegisteredScopes();
    }

    this.onSearch = function(query, uuid, onComplete)
    {
        var scopes = getScopes();
        var subscope = commando.getSubscope();
        var _scopes = {};
        var length = 0;
        for (let id in scopes)
        {
            if (["scope-tools","scope-commands"].indexOf(id) == -1) continue;
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

    this.onSelectResult = function(selectedItems)
    {
        var scopeItems = {};
        var scopes = getScopes();

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
