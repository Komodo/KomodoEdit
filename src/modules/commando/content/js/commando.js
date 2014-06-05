(function() {
    
    const {Cc, Ci}  = require("chrome");
    const $         = require("ko/dom");
    const doT       = require("contrib/dot");
    const log       = require("ko/logging").getLogger("commando");
    const uuidGen   = require("sdk/util/uuid");

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var local = {
        scopes: {},
        elemCache: {},
        templateCache: {},
        resultCache: [],
        resultsReceived: 0,
        resultsRendered: 0,
        searchingUuid: null
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
        elem('search').on("keydown", onKeyNav);
        elem('results').on("keydown", onKeyNav);
        elem('results').on("select", onSelectResult);
        elem('search').on("keyup", onSearch);
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
            local.templateCache[name] = doT.template(elems.template[name]().html());

        return local.templateCache[name](params);
    }

    var onKeyNav = function(e)
    {
        log.debug("Event: onKeyNav");

        var results = elem('results');
        if ( ! results.visible()) return;
        var resultCount = results.element().getRowCount();
        var selIndex = results.element().selectedIndex;

        switch (e.keyCode)
        {
            case 40: // down arrow
            case 9:  // tab
                log.debug("Navigate Down in Results");
                e.preventDefault();

                if (selIndex+1 == resultCount)
                    results.element().selectedIndex = 0;
                else
                    results.element().selectedIndex++;
                    
                break;
            case 38: // up arrow
                log.debug("Navigate Up in Results");
                e.preventDefault();

                if (selIndex == 0)
                    results.element().selectedIndex = resultCount-1;
                else
                    results.element().selectedIndex--;

                break;
        }
    }

    var onSearch = function(e, noDelay = false)
    {
        log.debug("Event: onSearch");
        if (local.prevSearchValue == e.target.value) return;

        // Prevent multiple searches in a short amount of time
        if ( ! noDelay)
        {
            log.debug("Delaying Search");
            window.setTimeout(
                onSearch.bind(this, e, true),
                ko.prefs.getLong("commando_search_delay", 50)
            );
            return;
        }

        local.searchingUuid = uuidGen.uuid();
        local.resultCache = [];
        local.resultsReceived = 0;
        local.resultsRendered = 0;
        local.prevSearchValue = e.target.value;

        // perform onSearch
        log.debug(local.searchingUuid + " - Starting Search for: " + e.target.value);
        getScopeHandler().onSearch(e.target.value, local.searchingUuid);
    }

    var onSelectResult = function(e)
    {
        var selected = elem('results').element().selectedIem;
        getScopeHandler().onSelectResult(selected);
    }

    var getScope = function()
    {
        return elem('scope').element().selectedItem._scope;
    }

    var getScopeHandler = function()
    {
        var scope = getScope();
        return require(scope.handler);
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

        var scopeElem = $(template('scopeMenuItem', opts));
        scopeElem.element()._scope = local.scopes[id];

        elem('scopesSeparator').before(
            scopeElem
        );

        if ( ! elem('scope').element().selectedItem.nodeName != 'menuitem')
        {
            elem('scope').element().selectedItem = scopeElem.element()
        }
    }

    this.unregisterScope = function(id)
    {
        if ( ! (id in local.scopes)) return;

        log.debug("Unregistering Scope: " + id);

        $("#scope-" + id).delete();
        delete local.scopes[id];
    }

    this.renderResult = function(result, searchUuid)
    {
        if (local.searchingUuid != searchUuid)
        {
            log.debug(searchUuid + " - Skipping result for old search uuid");
            return;
        }

        local.resultsReceived++;
        local.resultCache.push(result);

        window.clearTimeout(local.renderResultsTimer);
        local.renderResultsTimer = window.setTimeout(function()
        {
            this.renderResults(local.resultCache, searchUuid, true);
            local.resultCache = [];
        }.bind(this), ko.prefs.getLong("commando_result_render_delay", 10));
    }

    this.renderResults = function(results, searchUuid, cacheOrigin)
    {
        if (local.searchingUuid != searchUuid)
        {
            log.debug(searchUuid + " - Skipping "+results.length+" results for old search uuid: " + searchUuid);
            return;
        }

        if ( ! cacheOrigin)
            local.resultsReceived += results.length;

        if (local.resultsRendered === 0)
            this.empty(); // Force empty results

        log.debug(searchUuid + " - Rendering Results");

        var resultElem = elem('results');
        var maxResults = ko.prefs.getLong("commando_search_max_results", 50);
        maxResults -= local.resultsRendered;
        results = results.slice(0, maxResults);
        local.resultsRendered += results.length;

        var resultElem = elem('results');
        for (let result of results)
        {
            result.subscope = local.subscope;
            resultEntry = $.createElement(template('resultItem', result));
            resultEntry.resultData = result;
            resultElem.element().appendChild(resultEntry);
        }

        resultElem.addClass("has-results");
        resultElem.css("maxHeight", (window.screen.availHeight / 2) + "px");

        this.sortResults();
    }

    this.sortResults = function()
    {
        log.debug("Sorting Results");
        var resultElem = elem('results');

        // Sort by handler.sort
        var handler = getScopeHandler();
        if ("sort" in handler)
        {
            resultElem.find("richlistitem").reverse().each(function()
            {
                var cont = true;
                while (this.previousSibling && cont)
                {
                    if (handler.sort(this.resultData, this.previousSibling.resultData) === 1)
                        this.parentNode.insertBefore(this, this.previousSibling);
                    else
                        cont = false;
                }
            });
        }

        // Sort by weight, if available
        resultElem.find("richlistitem").reverse().each(function()
        {
            var cont = true;
            while (this.previousSibling && cont)
            {
                let current = this.resultData;
                let previous = this.previousSibling.resultData;

                if ((current.weight && ! previous.weight) ||
                    (current.weight && previous.weight && current.weight > previous.weight)
                )
                    this.parentNode.insertBefore(this, this.previousSibling);
                else
                    cont = false;
            }
        });
    }

    this.onSearchComplete = function(scope, searchUuid)
    {
        if (local.searchingUuid != searchUuid) return;

        if (local.resultsReceived == 0)
        {
            this.renderResult({
                id: "",
                name: "No Results",
                classList: "no-result-msg non-interact"
            }, searchUuid);
        }
    }

    this.getSubscope = function()
    {
        return local.subscope;
    }

    this.setSubscope = function(subscope)
    {
        local.subscope = subscope;
    }

    this.empty = function()
    {
        log.debug("Emptying Results");

        var resultElem = elem('results');
        resultElem.empty();
        resultElem.removeClass("has-results");
        local.resultsRendered = 0;
    }

    init();

}).apply(module.exports);
