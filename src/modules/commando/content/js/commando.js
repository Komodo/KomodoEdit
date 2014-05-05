(function() {
    
    const {Cc, Ci}  = require("chrome");
    const $         = require("ko/dom");
    const mustache  = require("contrib/mustache");
    const log       = require("ko/logging").getLogger("commando")

    log.setLevel(require("ko/logging").LOG_DEBUG);

    var local = {
        scopes: {},
        elemCache: {},
        templateCache: {}
    };

    var elems = {
        panel: function() { return $("#commando-panel"); },
        scope: function() { return $("#commando-scope"); },
        results: function() { return $("#commando-results"); },
        search: function() { return $("#commando-search"); },
        scopesSeparator: function() { return $("#scope-separator"); },
        customScopesSeparator: function() { return $("#custom-scope-separator"); },
        template: {
            scopeMenuItem: function() { return $("#tpl-co-scope-menuitem"); },
            resultItem: function() { return $("#tpl-co-result"); }
        }
    };

    /* Private Methods */

    var init = function()
    {
        log.debug('Starting Commando');
        elem('search').on("input", onSearch);
        elem('scope').on("change", function(e) { elem('search').focus(); });
    }

    var elem = function(name, noCache)
    {
        if ( ! (name in elems)) return undefined;
        if (noCache || ! (name in local.elemCache))
            local.elemCache[name] = elems[name]();
        return local.elemCache[name];
    }

    var template = function(name, params)
    {
        if ( ! (name in elems.template)) return undefined;
        if ( ! (name in local.templateCache))
            local.templateCache[name] = elems.template[name]().html();

        return $(mustache.render(local.templateCache[name], params));
    }

    var onSearch = function(e, noDelay = false)
    {
        if ( ! noDelay)
        {
            if ("searchTimer" in local)
                window.clearTimeout(local.searchTimer);

            log.debug("Delaying Search");
            local.searchTimer = window.setTimeout(
                onSearch.bind(this, e, true),
                ko.prefs.getLong("commando_search_delay", 100)
            );
        }

        log.debug("Starting Search");
        var scope = elem('scope').element().selectedItem._scope;
        var handler = require(scope.handler);

        handler.onSearch(e.target.value, undefined, onResults);
    }

    var onResults = function(results)
    {
        var resultElem = elem('results');
        resultElem.empty();
        
        for (let result of results)
        {
            resultElem.append(template('resultItem', result));

        }

        if (results.length > 0)
            resultElem.addClass("has-results");
        else
            resultElem.removeClass("has-results");
    }

    /* Public Methods */
    
    this.showCommando = function()
    {
        log.debug("Showing Commando");

        var panel = elem('panel');
        var search = elem('search');
        
        let left = window.innerWidth / 2;
        left -= panel.element().getBoundingClientRect().width / 2;
        panel.element().openPopup(undefined, undefined, left, 100);

        search.value("");
        search.focus();
    }

    this.registerScope = function(id, opts)
    {
        log.debug("Registering Scope: " + id);

        opts.id = id;
        local.scopes[id] = opts;

        var scopeElem = template('scopeMenuItem', opts);
        scopeElem.element()._scope = local.scopes[id];

        elem('scopesSeparator').before(
            scopeElem
        );
    }

    this.unregisterScope = function(id)
    {
        if ( ! (id in local.scopes)) return;
        
        log.debug("Unregistering Scope: " + id);

        $("#scope-" + id).delete();
        delete local.scopes[id];
    }

    init();

}).apply(module.exports);
