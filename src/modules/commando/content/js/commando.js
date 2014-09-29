(function() {
    
    const {Cc, Ci}  = require("chrome");
    const $         = require("ko/dom");
    const doT       = require("contrib/dot");
    const log       = require("ko/logging").getLogger("commando");
    const uuidGen   = require("sdk/util/uuid");
    const keybinds  = require("ko/keybindings");
    const commands  = require("ko/commands");

    const ioService = Cc["@mozilla.org/network/io-service;1"]
                        .getService(Ci.nsIIOService);

    const commando  = this;

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var local = {
        scopes: {},
        subscope: null,
        elemCache: {},
        templateCache: {},
        resultCache: [],
        resultsReceived: 0,
        resultsRendered: 0,
        searchingUuid: null,
        prevSearchValue: null,
        transitKeyBinds: false,
        renderResultsTimer: undefined,
        searchTimer: false
    };

    var elems = {
        panel: function() { return $("#commando-panel"); },
        scope: function() { return $("#commando-scope"); },
        subscope: function() { return $("#commando-subscope"); },
        results: function() { return $("#commando-results"); },
        search: function() { return $("#commando-search"); },
        scopePopup: function() { return $("commando-scope-menupopup"); },
        scopesSeparator: function() { return $("#scope-separator"); },
        menuItem: function() { return $("#menu_show_commando"); },
        template: {
            scopeMenuItem: function() { return $("#tpl-co-scope-menuitem"); },
            scopeNavMenuItem: function() { return $("#tpl-co-scope-nav-menuitem"); },
            resultItem: function() { return $("#tpl-co-result"); }
        }
    };

    /* Private Methods */

    var init = function()
    {
        log.debug('Starting Commando');
        elem('search').on("input", onSearch.bind(this));
        elem('search').on("keydown", onKeyNav.bind(this));
        elem('scope').on("command", onChangeScope.bind(this));
        elem('results').on("keydown", onKeyNav.bind(this));

        local.transitKeyBinds = ko.prefs.getBoolean("transit_commando_keybinds", false);
        if (local.transitKeyBinds)
        {
            log.debug("Transitioning keybinds");
            ko.prefs.deletePref("transit_commando_keybinds");
        }
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
        var resultElem = results.element();
        var resultCount = resultElem.getRowCount();
        var prevDefault = false;

        // Todo: support selecting multiple items
        switch (e.keyCode)
        {
            case 8: // backspace
                if (elem('search').value() == "" && commando.getSubscope() && local.prevKeyCode == 8)
                    commando.setSubscope(null);
                break;
            case 13: // enter
                onSelectResult(e);
                break;
            case 40: // down arrow
            case 9:  // tab
                prevDefault = true;

                var selIndex = resultElem.selectedIndex;
                for (let item of resultElem.selectedItems)
                {
                    let itemIndex = resultElem.getIndexOfItem(item);
                    if (itemIndex > selIndex) selIndex = itemIndex;
                }

                if (e.shiftKey && resultElem.selectedItems.length)
                {
                    log.debug("Add Next to Selection in Results");

                    var selItem = resultElem.getItemAtIndex(selIndex);
                    var sibling = selItem.nextSibling;
                    if (sibling && selItem.resultData.allowMultiSelect && sibling.resultData.allowMultiSelect)
                    {
                        resultElem.addItemToSelection(sibling);
                        resultElem.ensureElementIsVisible(sibling);
                    }
                }
                else
                {
                    log.debug("Navigate Down in Results");

                    if (selIndex+1 == resultCount)
                        resultElem.selectedIndex = selIndex = 0;
                    else
                        resultElem.selectedIndex = selIndex = selIndex+1;

                    resultElem.ensureIndexIsVisible(selIndex);
                }
                    
                break;
            case 38: // up arrow
                prevDefault = true;

                var selIndex = resultElem.selectedIndex;
                for (let item of resultElem.selectedItems)
                {
                    let itemIndex = resultElem.getIndexOfItem(item);
                    if (itemIndex < selIndex) selIndex = itemIndex;
                }

                if (e.shiftKey && resultElem.selectedItems.length)
                {
                    log.debug("Add Previous to Selection in Results");

                    var selItem = resultElem.getItemAtIndex(selIndex);
                    var sibling = selItem.previousSibling;
                    if (sibling && selItem.resultData.allowMultiSelect && sibling.resultData.allowMultiSelect)
                    {
                        resultElem.addItemToSelection(sibling);
                        resultElem.ensureElementIsVisible(sibling);
                    }
                }
                else
                {
                    log.debug("Navigate Up in Results");
                    
                    if (selIndex == 0)
                        resultElem.selectedIndex = selIndex = resultCount-1;
                    else
                        resultElem.selectedIndex = selIndex = selIndex-1;

                    resultElem.ensureIndexIsVisible(selIndex);
                }

                break;
        }

        local.prevKeyCode = e.keyCode;

        // Always keep focus on search
        elem('search').focus();

        if (prevDefault)
        {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }

    var onSearch = function(e, noDelay)
    {
        _onKitt();

        if (local.searchTimer && ! noDelay) return; // Search is already queued

        elem("panel").addClass("loading");
        var searchDelay = ko.prefs.getLong('commando_search_delay', 200);

        if (noDelay)
        {
            window.clearTimeout(local.searchTimer);
            local.searchTimer = false;
        }
        else if ( ! local.lastSearch || (new Date().getTime()) - local.lastSearch > searchDelay)
            noDelay = true; // why delay the inevitable

        local.lastSearch = new Date().getTime();

        local.searchTimer = window.setTimeout(function()
        {
            local.searchTimer = false;
            
            log.debug("Event: onSearch");
            var searchValue = elem('search').value();
            if (local.prevSearchValue == searchValue) return;

            local.searchingUuid = uuidGen.uuid();
            local.resultCache = [];
            local.resultsReceived = 0;
            local.resultsRendered = 0;
            local.prevSearchValue = searchValue;

            // perform onSearch
            log.debug(local.searchingUuid + " - Starting Search for: " + searchValue);
            getScopeHandler().onSearch(searchValue, local.searchingUuid);
        }, noDelay ? 0 : searchDelay);
    }

    _onKitt = function()
    {
        // You didn't see this, you were never here
        if (_onKitt.kitt)
        {
            elem("panel").removeClass("kitt");
            delete _onKitt.kitt
        }
        if (["kitt", "michael"].indexOf(elem('search').value()) !== -1)
        {
            var sound = Cc["@mozilla.org/sound;1"].createInstance(Ci.nsISound);
            sound.play(ioService.newURI('chrome://commando/content/loading.wav', null, null));
            elem("panel").addClass("kitt");
            _onKitt.kitt = true;
        }
    }

    var onSelectResult = function(e)
    {
        log.debug("Selected Result(s)");

        e.cancelBubble = true;
        e.preventDefault();

        var selected = elem('results').element().selectedItems.slice();

        if (selected.length == 1 && selected.slice(0)[0].resultData.isScope)
        {
            commando.setSubscope(selected.slice(0)[0].resultData);
            return;
        }

        if (selected.length > 1)
        {
            for (let i in selected)
            {
                if ( ! selected[i].resultData.allowMultiSelect)
                    delete selected[i];
            }
        }

        if (selected.length)
            getScopeHandler().onSelectResult(selected);
    }

    var onChangeScope = function(e)
    {
        log.debug("Changing Active Scope");
        var scopeElem = elem('scope');

        if ( ! ("_scope" in scopeElem.element().selectedItem))
        {
            log.debug("Scope selection is not an actual scope, reverting active scope menuitem");
            log.debug(local.selectedScope);

            if (local.selectedScope)
                scopeElem.element().selectedItem = scopeElem.find("#"+local.selectedScope).element();
            else
                scopeElem.element().selectedIndex = 0;
            return;
        }

        commando.selectScope(scopeElem.element().selectedItem, true);
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

    this.showCommando = function(scope)
    {
        log.debug("Showing Commando");

        if (scope)
            commando.selectScope(scope);

        var panel = elem('panel');
        var search = elem('search');

        let left = window.innerWidth / 2;
        left -= panel.element().width / 2;
        panel.element().openPopup(undefined, undefined, left, 100);

        search.focus();

        if (ko.prefs.getBoolean('commando_preserve_query', true))
            search.element().select();
        else
            search.value("");
        
        elem('results').element().clearSelection();

        var scopeHandler = getScopeHandler();
        if ("onShow" in scopeHandler)
            scopeHandler.onShow();
    }

    this.search = function(value)
    {
        elem('search').value(value);
        onSearch();
    }

    this.hideCommando = function()
    {
        this.stop();
        log.debug("Hiding Commando");
        elem('panel').element().hidePopup();
    }

    this.getRegisteredScopes = function()
    {
        return local.scopes;
    }

    this.registerScope = function(id, opts)
    {
        log.debug("Registering Scope: " + id);

        opts.id = id;
        local.scopes[id] = opts;

        var scopeElem = $(template('scopeMenuItem', opts)).element();
        scopeElem._scope = local.scopes[id];

        // Register command
        commands.register(id, this.showCommando.bind(this, id), {
            defaultBind: opts.keybind,
            label: "Commando: Open Commando with the " + opts.name + " scope"
        });

        if (local.transitKeyBinds && opts.keybindTransit)
        {
            log.debug("Checking keybind for " + opts.keybindTransit);
            var keybind = keybinds.getKeybindFromCommand(opts.keybindTransit);
            if (keybind)
            {
                log.debug("Binding " + keybind + " to " + id);
                keybinds.register(id, keybind, true);
            }
        }

        opts.accelText = keybinds.getKeybindFromCommand("cmd_" + id) || "";

        // Insert Scope Selection
        var sepElem = elem('scopesSeparator').element();
        sepElem.parentNode.insertBefore(scopeElem, sepElem);

        // Sort Scope Selection
        while (scopeElem.previousSibling)
        {
            var prevElem = scopeElem.previousSibling;
            var weighsMore = ("weight" in opts) &&
                             ( ! ("weight" in prevElem._scope) || opts.weight > prevElem._scope.weight);
            var comesFirst = prevElem._scope.name.localeCompare(opts.name) > 0;

            if (weighsMore || (comesFirst && ! prevElem._scope.weight))
                scopeElem.parentNode.insertBefore(scopeElem, prevElem);
            else
                break;
        }

        // Set Default Scope Selection
        if ( ! scopeElem.previousSibling)
            elem('scope').element().selectedIndex = 0;

        // Inset Menuitem
        opts.menuLabel = "Go to " + opts.name;
        var menuitem = $(template('scopeNavMenuItem', opts)).element();
        var sibling = elem('menuItem').element();
        while (sibling.nextSibling)
        {
            sibling = sibling.nextSibling;
            if (sibling.nodeName == "menuseparator" || sibling.getAttribute("label").localeCompare(opts.menuLabel)>0)
            {
                $(sibling).before(menuitem);
                break;
            }
        }

        window.clearTimeout(local.uilaoutTimer);
        local.uilaoutTimer = window.setTimeout(function()
        {
            ko.uilayout.cloneUnifiedMenuItems();
        }, 50);
    }

    this.unregisterScope = function(id)
    {
        if ( ! (id in local.scopes)) return;

        log.debug("Unregistering Scope: " + id);

        $("#scope-" + id).delete();
        delete local.scopes[id];

        commands.unregister(id);
    }

    this.selectScope = function(scopeId, doOnShow)
    {
        var scopeElem = elem('scope');
        var selectedItem = scopeElem.element().selectedItem;

        if (typeof scopeId != "string")
            var selectItem = scopeId;
        else
            var selectItem = scopeElem.find("#scope-" + scopeId).element();

        if ( ! selectItem)
        {
            log.error("selectScope: Scope could not be found: " + scopeId);
            return;
        }

        if (selectedItem != selectItem)
            scopeElem.element().selectedItem = selectItem;

        local.selectedScope = selectItem.id;

        commando.stop();
        commando.empty();
        commando.setSubscope(null);

        if (doOnShow)
        {
            var scopeHandler = getScopeHandler();
            if ("onShow" in scopeHandler)
                scopeHandler.onShow();

            window.setTimeout(function() { elem('search').focus(); }, 0);
        }
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
        }.bind(this), ko.prefs.getLong("commando_result_render_delay", 50));
    }

    this.renderResults = function(results, searchUuid, cacheOrigin)
    {
        if ( ! results.length) return;

        if (local.searchingUuid != searchUuid)
        {
            log.debug(searchUuid + " - Skipping "+results.length+" results for old search uuid: " + searchUuid);
            return;
        }

        if ( ! cacheOrigin)
            local.resultsReceived += results.length;

        if (local.resultsRendered === 0)
            this.empty(); // Force empty results

        log.debug(searchUuid + " - Rendering "+results.length+" Results");

        // Replace result elem with temporary cloned node so as not to paint the DOM repeatedly
        var resultElem = elem('results');
        var tmpResultElem = resultElem.element().cloneNode();
        resultElem.element().clearSelection();
        resultElem = $(resultElem.replaceWith(tmpResultElem));
        
        var maxResults = ko.prefs.getLong("commando_search_max_results", 50);
        maxResults -= local.resultsRendered;
        results = results.slice(0, maxResults);
        local.resultsRendered += results.length;

        if (local.resultsReceived == maxResults)
            log.debug("Reached max results");

        var process = [];
        for (let result of results)
        {
            result.subscope = local.subscope;
            var resultEntry = $.createElement(template('resultItem', result));
            resultEntry.resultData = result;
            resultElem.element().appendChild(resultEntry);
            this.sortResult(resultEntry);

            if (result.descriptionComplex)
                process.push(resultEntry);
        }

        resultElem.addClass("has-results");
        resultElem.css("maxHeight", (window.screen.availHeight / 2) + "px");

        tmpResultElem.parentNode.replaceChild(resultElem.element(), tmpResultElem);

        resultElem.element().selectedIndex = 0;

        if (process) processResults(process);
    }

    var processResults = function(resultEntries)
    {
        var getByAttr = window.xtk.domutils.getChildByAttribute;
        for (let entry in resultEntries)
        {
            entry = resultEntries[entry];
            var wrapper = getByAttr(entry.childNodes[0], "class", "entry-wrapper");
            var prefix = getByAttr(wrapper, "class", "prefix")
            var descComplex = getByAttr(wrapper, "class", "descriptionComplex")

            var prefixWidth = prefix.boxObject.width;

            // Todo: account for other nodes, clean up
            // Detect width automatically
            // MAKE XUL RESPECT THE FREAKING PARENT NODE WIDTH! SERIOUSL XUL GRRRRRRR
            // And if at all possible find a pure XUL/CSS way, this sucks
            descComplex.style.maxWidth = (430 - prefixWidth) + "px";

            // Yes this code sucks, XUL made me do it
            if (descComplex.firstChild && descComplex.firstChild.classList && descComplex.firstChild.classList.contains("crop"))
                descComplex.firstChild.style.maxWidth = descComplex.style.maxWidth;
        }
    }

    // Todo: prevent multiple paints
    this.sortResult = function(elem)
    {
        // Sort by handler.sort
        var handler = getScopeHandler();
        if ("sort" in handler)
        {
            while (elem.previousSibling)
            {
                let current = elem.resultData;
                let previous = elem.previousSibling.resultData;

                if ( ! current)
                    continue;

                if (handler.sort(current, previous) === 1)
                {
                    if ((elem.previousSibling.resultData.weight || 0) > (elem.resultData.weight || 0))
                        break;

                    elem.parentNode.insertBefore(elem, elem.previousSibling);
                }
                else
                    break;
            }
        }

        // Sort by weight, if available
        if (elem.resultData.weight)
        {
            var cont = true;
            while (elem.previousSibling && cont)
            {
                let current = elem.resultData;
                let previous = elem.previousSibling.resultData;

                if ( ! current)
                    continue;

                if ( ! previous || (current.weight && ! previous.weight) ||
                    (current.weight && previous.weight && current.weight > previous.weight)
                )
                    elem.parentNode.insertBefore(elem, elem.previousSibling);
                else
                    cont = false;
            }
        }
    }

    this.onSearchComplete = function(searchUuid)
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

        window.setTimeout(function()
        {
            elem("panel").removeClass("loading");
        }, _onKitt.kitt ? 1000 : 0);

    }

    this.getSubscope = function()
    {
        return local.subscope;
    }

    this.setSubscope = function(subscope)
    {
        if (subscope && (! subscope.scope in local.scopes))
            return log.error("Scope does not exist: " + subscope.scope);

        local.subscope = subscope;

        if (subscope)
            elem('subscope').value(subscope.name).show();
        else
            elem('subscope').value("").hide();

        local.prevSearchValue = null;

        if (subscope)
        {
            var scopeHandler = require(local.scopes[subscope.scope].handler);
            if ("onShow" in scopeHandler)
                return scopeHandler.onShow();
        }

        this.empty();
    }

    this.stop = function()
    {
        local.prevSearchValue = null;
        local.searchingUuid = null;
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
