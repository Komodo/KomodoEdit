(function() {
    
    const {Cc, Ci}  = require("chrome");
    const $         = require("ko/dom");
    const doT       = require("contrib/dot");
    const log       = require("ko/logging").getLogger("commando");
    const uuidGen   = require("sdk/util/uuid");
    const keybinds  = require("ko/keybindings");
    const commands  = require("ko/commands");
    const _         = require("contrib/underscore");
    const controller= require("./controller");

    const ioService = Cc["@mozilla.org/network/io-service;1"]
                        .getService(Ci.nsIIOService);

    const KeyEvent = window.KeyEvent; // Todo: Don't depend on window

    // Short alias for the commando scope.
    const c = this;

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var local = {
        scopes: {},
        subscope: null,
        handlers: {},
        elemCache: {},
        templateCache: {},
        resultCache: [],
        resultsReceived: 0,
        resultsRendered: 0,
        searchingUuid: null,
        prevSearchValue: null,
        transitKeyBinds: false,
        renderResultsTimer: undefined,
        searchTimer: false,
        favourites: null,
        history: [],
        uilayoutTimer: -1,
        open: false,
        quickSearch: false,
        altPressed: true,
        altNumber: null,
        useQuickScope: false,
        quickScope: null
    };

    var elems = {
        panel: function() { return $("#commando-panel"); },
        scope: function() { return $("#commando-scope"); },
        subscopeWrap: function() { return $("#commando-subscope-wrap"); },
        results: function() { return $("#commando-results"); },
        search: function() { return $("#commando-search"); },
        quickSearch: function() { return $("#commando-search-quick"); },
        quickSearchToolbar: function() { return $("#quickCommando"); },
        scopePopup: function() { return $("commando-scope-menupopup"); },
        scopesSeparator: function() { return $("#scope-separator"); },
        menuItem: function() { return $("#menu_show_commando"); },
        tip: function() { return $("#commando-tip"); },
        tipDesc: function() { return $("#commando-tip description"); },
        template: {
            scopeMenuItem: function() { return $("#tpl-co-scope-menuitem"); },
            scopeNavMenuItem: function() { return $("#tpl-co-scope-nav-menuitem"); },
            resultItem: function() { return $("#tpl-co-result"); },
            subscope: function() { return $("#tpl-co-subscope"); }
        }
    };

    /* Private Methods */

    var init = function()
    {
        log.debug('Starting Commando');
        elem('search').on("input", onSearch.bind(this));
        elem('search').on("keydown", onKeyNav.bind(this));
        elem('search').on("keyup", onKeyUp.bind(this));
        elem('quickSearch').on("input", onSearch.bind(this));
        elem('quickSearch').on("keydown", onKeyNav.bind(this));
        elem('quickSearch').on("keyup", onKeyUp.bind(this));
        elem('quickSearch').on("focus", onQuickSearchFocus);
        elem('quickSearch').on("click", onQuickSearchFocus);
        elem('scope').on("command", onChangeScope.bind(this));
        elem('results').on("keydown", onKeyNav.bind(this));
        elem('results').on("dblclick", onSelectResult.bind(this));
        
        local.transitKeyBinds = ko.prefs.getBoolean("transit_commando_keybinds", false);
        if (local.transitKeyBinds)
        {
            log.debug("Transitioning keybinds");
            ko.prefs.deletePref("transit_commando_keybinds");
        }

        local.favourites = ko.prefs.getPref('commando_favourites');

        var panel = elem('panel');
        panel.on("popupshown", function(e)
        {
            if (e.originalTarget != panel.element()) return;

            // Sometimes Commando gets a height attribute set on it (externally)
            // Work around this by removing it on show, least until we find the
            // cause of the issue - https://bugs.activestate.com/show_bug.cgi?id=106266
            panel.removeAttr("height");
            
            local.open = true;
            c.focus();
        });

        panel.on("popuphidden", function(e)
        {
            if (e.originalTarget != panel.element()) return;
            
            local.open = false;
            elem("quickSearch").removeAttr("open");
            local.useQuickScope = false;
        });

        window.addEventListener("click", onWindowClick);
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

    /** Controllers **/

    var onKeyNav = function(e)
    {
        log.debug("Event: onKeyNav");

        var results = elem('results');
        if ( ! results.visible()) return;
        var prevDefault = false;

        // Todo: support selecting multiple items
        switch (e.keyCode)
        {
            case KeyEvent.DOM_VK_ESCAPE:
                if (c.getSearchValue() != "" || c.getSubscope())
                {
                    c.navBack();
                    c.empty();
                }
                else if (local.quickScope && local.useQuickScope && local.quickScope != c.getScope().id)
                {
                    c.selectScope(local.quickScope);
                }
                else
                {
                    c.hide();
                }
                break;
            case KeyEvent.DOM_VK_BACK_SPACE:
            case KeyEvent.DOM_VK_LEFT: 
                onNavBack();
                break;
            case KeyEvent.DOM_VK_RETURN: 
                onSelectResult();
                prevDefault = true;
                break;
            case KeyEvent.DOM_VK_TAB:  
                onTab(e);
                prevDefault = true;
                break;
            case KeyEvent.DOM_VK_DOWN: 
                onNavDown(e);
                prevDefault = true;
                break;
            case KeyEvent.DOM_VK_UP: 
                onNavUp(e);
                prevDefault = true;
                break;
            case KeyEvent.DOM_VK_RIGHT: 
                onExpandResult(e);
                break;
            case KeyEvent.DOM_VK_ALT:
                local.altPressed = true;
                break;
        }
        
        if (local.altPressed && e.keyCode != KeyEvent.DOM_VK_ALT)
        {
            var numberPressed = false;
            var numbers = [0,1,2,3,4,5,6,7,8,9];
            for (let number of numbers)
            {
                if (e.keyCode != KeyEvent["DOM_VK_" + number])
                    continue;
                
                numberPressed = true;
                prevDefault = true;
                
                if (local.altNumber)
                    local.altNumber += number;
                else
                    local.altNumber = number.toString();
            }
            
            if ( ! numberPressed)
            {
                local.altNumber = null;
                local.altPressed = false;
            }
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
    
    var onKeyUp = function(e)
    {
        if ( e.keyCode != KeyEvent.DOM_VK_ALT)
            return;
        
        log.debug("Event: onKeyUp");
        
        var results = elem('results');
        if (results.visible() && local.altNumber)
        {
            var index = parseInt(local.altNumber) - 1;
            results.element().selectedIndex = index;
            results.element().ensureIndexIsVisible(index);
            onSelectResult();
        }
        
        local.altPressed = false;
        local.altNumber = null;
    }

    var onNavBack = function()
    {
        var textbox = elem("search").element();
        if (textbox.selectionEnd != textbox.selectionStart ||
            textbox.selectionStart != 0)
        {
            return;
        }

        c.navBack();
    }

    var onTab = function(e)
    {
        var selected = c.getSelectedResult();
        if (selected.isScope) {
            // Set to the selected scope.
            c.setSubscope(selected);
        } else {
            // Set to the id of the selected item.
            var textbox = elem("search").element();
            textbox.value = selected.id;
        }
    }

    var onNavDown = function(e)
    {
        c.navDown(e && e.shiftKey);
    }

    var onNavUp = function(e)
    {
        if (e.ctrlKey) {
            c.onNavBack();
        } else {
            c.navUp(e && e.shiftKey);
        }
    }

    var onSearch = function(e)
    {
        var uuid = c.search(null, function()
        {
            onSearchComplete(uuid);
        });
    }

    var onSearchComplete = function(uuid)
    {
        if (local.searchingUuid != uuid) return;

        if (local.resultsReceived == 0)
        {
            c.renderResult({
                id: "",
                name: "No Results",
                classList: "no-result-msg non-interact"
            }, uuid);
        }

        window.setTimeout(function()
        {
            elem("panel").removeClass("loading");
        }, kitt.kitt ? 1000 : 0);
    }

    var onSelectResult = function()
    {
        log.debug("Selected Result(s)");

        var selected = c.getSelected();
        c.selectResults(selected);
    }

    var onExpandResult = function()
    {
        var textbox = elem("search").element();

        if (textbox.selectionEnd != textbox.selectionStart ||
            textbox.selectionStart < textbox.value.length)
        {
            return;
        }

        log.debug("Expanding Result");

        var selected = c.getSelectedResult();
        if ( ! selected)
            return;

        c.expandResult(selected);
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

        c.selectScope(scopeElem.element().selectedItem);
        c.execScopeHandler("onShow");
        window.setTimeout(function() { elem('search').focus(); }, 0);
    }

    var onWindowClick = function(e)
    {
        if ( ! local.open) return;
        var target = e.originalTarget || e.target;
        while((target=target.parentNode) && target !== elem('panel').element() && target.nodeName != "dialog");
        if ( ! target)
        {
            c.hide();
        }
    }
    
    var onQuickSearchFocus = function(e)
    {
        if (local.open) return;
        
        elem("quickSearch").attr("open", true);
        
        setTimeout(function() {
            c.show(undefined, true);
            c.search();
        }, 100);
    }

    /* Public Methods */
    this.show = function(scope, quickSearch = false)
    {
        log.debug("Showing Commando");
        
        local.quickSearch = quickSearch;
        
        if ( ! scope && local.quickScope)
            scope = local.quickScope;

        var preserve = ko.prefs.getBooleanPref('commando_preserve_query');
        if (scope && (scope != c.getScope().id || ! preserve))
            c.selectScope(scope);
        
        scope = c.getScope();
            
        if ("quickscope" in scope)
            local.useQuickScope = true;

        var panel = elem('panel');
        var search = elem('search');
        
        var left, top;
        if (local.quickSearch)
        {
            var qs = elem('quickSearch').element().boxObject;
            top = qs.y - 5;
            left = qs.x + qs.width - panel.element().width + 2;
            
            panel.addClass("quick-search");
        }
        else
        {
            top = 100;
            var bo = document.getElementById('komodo-editor-vbox');
            bo = bo ? bo.boxObject : document.documentElement.boxObject;
            
            left = bo.x + (bo.width / 2);
            left -= panel.element().width / 2;
            
            panel.removeClass("quick-search");
        }
        
        panel.element().openPopup(undefined, undefined, left, top);
        
        if (c.execScopeHandler("onShow") === false)
        {
            search.element().select();
            c.tip();
        }
    }

    this.isOpen = function()
    {
        return local.open;
    }

    this.hide = function()
    {
        elem('panel').element().hidePopup();
        
        var view = ko.views.manager.currentView;
        if (view && view.getAttribute("type") != "editor")
            view.scintilla.focus();
    }

    this.search = function(value, callback, noDelay = false)
    {
        if (value)
        {
            elem('search').value(value);
        }

        if ( ! callback) // this is a manual search
            return onSearch();

        kitt();

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

        var uuid = uuidGen.uuid();
        local.searchTimer = window.setTimeout(function()
        {
            local.searchTimer = false;

            log.debug("Event: onSearch");
            var searchValue = elem('search').value();
            
            // Update quick search value
            var preserve = ko.prefs.getBooleanPref('commando_preserve_query');
            if (preserve && searchValue.length)
            {
                log.debug("Store value to quickSearch");
                elem("quickSearch").attr({
                    placeholder: "false",
                    value: searchValue
                });
            }
            else
            {
                var quickSearch = elem("quickSearch");
                quickSearch.attr({
                    placeholder: "true",
                    value: quickSearch.attr("placeholdervalue")
                });
            }

            local.searchingUuid = uuid;
            local.resultCache = [];
            local.resultsReceived = 0;
            local.resultsRendered = 0;
            local.prevSearchValue = searchValue;
            
            elem('results').attr("dirty", "true");

            var subscope = c.getSubscope();
            if (subscope && subscope.isExpanded)
            {
                c.expandSearch(searchValue, local.searchingUuid, callback);
            }
            else
            {
                // perform onSearch
                log.debug(local.searchingUuid + " - Starting Search for: " + searchValue);
                c.execScopeHandler("onSearch", [searchValue, local.searchingUuid, callback])
            }
            
        }.bind(this), noDelay ? 0 : searchDelay);

        return uuid;
    }
    
    this.reSearch = function()
    {
        var query = local.prevSearchValue;

        c.stop();
        c.search(query);
    }

    this.expandSearch = function(query, uuid, callback)
    {
        var subscope = c.getSubscope();

        var results = [
            {
                id: "open",
                name: "Open",
                weight: 50,
                command: function()
                {
                    subscope.isExpanded = false;
                    c.selectResults([{resultData: subscope}]);
                }
            }
        ];

        if (local.favourites.findString(subscope.id) == -1)
        {
            results.push({
                id: "favourite",
                name: "Favourite",
                weight: 40,
                command: function()
                {
                    subscope.favourite = true;
                    local.favourites.appendString(subscope.id);
                    c.reSearch();
                },
                allowExpand: false
            });
        }
        else
        {
            results.push({
                id: "unfavourite",
                name: "Un-Favourite",
                weight: 40,
                command: function()
                {
                    subscope.favourite = false;
                    local.favourites.findAndDeleteString(subscope.id);
                    c.reSearch();
                },
                allowExpand: false
            });
        }

        log.debug(local.searchingUuid + " - Starting Expanded Search for: " + query);
        results = c.filter(results, query);
        c.renderResults(results, uuid);

        // perform onSearch
        if ( ! c.execScopeHandler("onExpandSearch", [query, uuid, callback]))
        {
            callback();
        }
    }
    
    this.getSearchValue = function()
    {
        return elem('search').value();
    }
    
    this.getActiveSearchUuid = function()
    {
        return local.searchingUuid;
    }

    this.selectResults = function(selected)
    {
        if (selected.length == 1 && selected.slice(0)[0].resultData.isScope)
        {
            c.setSubscope(selected.slice(0)[0].resultData);
            return;
        }

        selected = selected.filter(function(el)
        {
            if (selected.length > 1 && ! el.resultData.allowMultiSelect)
                return false;

            return true;
        });

        selected = selected.filter(function(el)
        {
            if ("command" in el.resultData)
            {
                log.debug("doCommand");
                el.resultData.command();
                return false;
            }

            return true;
        });

        if (selected.length)
            c.execScopeHandler("onSelectResult", [selected]);
    }

    this.expandResult = function(selected)
    {
        if (selected.allowExpand === false)
            return;

        var resultData = _.extend({}, selected);
        resultData.isExpanded = true;

        c.setSubscope(resultData);
        c.execScopeHandler("onExpand");

        c.clear();
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
        
        if (opts.quickscope)
            local.quickScope = id;

        var scopeElem = $(template('scopeMenuItem', opts)).element();
        scopeElem._scope = local.scopes[id];

        // Register command
        commands.register(id, this.show.bind(this, id), {
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

        if ("cloneUnifiedMenuItems" in ko.uilayout)
        {
            window.clearTimeout(local.uilayoutTimer);
            local.uilayoutTimer = window.setTimeout(function()
            {
                ko.uilayout.cloneUnifiedMenuItems();
            }, 50);
        }
    }

    this.unregisterScope = function(id)
    {
        if ( ! (id in local.scopes)) return;

        log.debug("Unregistering Scope: " + id);

        $("#scope-" + id).delete();
        delete local.scopes[id];

        commands.unregister(id);
    }

    this.registerHandler = function(id, scope, method, handler)
    {
        if ( ! (scope in local.handlers))
        {
            local.handlers[scope] = {};
        }

        if ( ! (method in local.handlers[scope]))
        {
            local.handlers[scope][method] = {};
        }
        
        local.handlers[scope][method][id] = handler;
    }

    this.unregisterHandler = function(id, scope, method)
    {
        if ((scope in local.handlers) && (method in local.handlers[scope]))
        {
            if (id in local.handlers[scope][method])
            {
                delete local.handlers[scope][method][id];
            }
        }
    }

    this.selectScope = function(scopeId)
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

        scopeElem.element().selectedItem = selectItem;
        scopeElem.attr("image", scopeElem.attr("image") + "?preset=hud");

        local.selectedScope = selectItem.id;

        c.stop();
        c.empty();
        c.setSubscope(null);
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
        }.bind(this), ko.prefs.getLong("commando_result_render_delay", 100));
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
        var resultElem = elem('results', true);
        var tmpResultElem = resultElem.element().cloneNode();
        resultElem.element().clearSelection();
        resultElem = $(resultElem.replaceWith(tmpResultElem));
        
        var maxResults = ko.prefs.getLong("commando_search_max_results", 50);
        maxResults -= local.resultsRendered;
        results = results.slice(0, maxResults);
        local.resultsRendered += results.length;

        if (local.resultsReceived == maxResults)
            log.debug("Reached max results");

        for (let result of results)
        {
            if (local.favourites.findString(result.id) != -1)
            {
                result.favourite = true;
            }

            result.subscope = local.subscope;
            var resultEntry = $.createElement(template('resultItem', result));
            resultEntry.resultData = result;
            resultElem.element().appendChild(resultEntry);
            this.sortResult(resultEntry);
        }

        resultElem.addClass("has-results");
        resultElem.css("maxHeight", (window.screen.availHeight / 2) + "px");
        
        var counter = 1;
        resultElem.find("label.number").each(function()
        {
            this.textContent = counter++;
        });

        tmpResultElem.parentNode.replaceChild(resultElem.element(), tmpResultElem);

        c.navDown();
        
        elem('panel').removeAttr("height");
    }

    this.filter = function(results, query, field)
    {
        field = "name";
        var words = query.toLowerCase().split(/\s+/);

        return results.filter(function(result)
        {
            if ( ! (field in result))
                return false;

            for (let w in words)
            {
                if (result[field].toLowerCase().indexOf(words[w]) == -1)
                    return false;
            }

            return true;
        });
    }

    // Todo: prevent multiple paints
    this.sortResult = function(elem)
    {
        // Sort by handler.sort
        var handler = c.getScopeHandler();
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

        if (elem.resultData.favourite)
        {
            while (elem.previousSibling)
            {
                let previous = elem.previousSibling.resultData;
                if ( ! previous || ! previous.favourite)
                    elem.parentNode.insertBefore(elem, elem.previousSibling);
                else
                    break;
            }
        }
    }

    this.navBack = function()
    {
        if ( ! c.getSubscope())
        {
            return false;
        }

        var history = local.history.pop();

        if ( ! history)
        {
            c.setSubscope();
            c.clear();
        }
        else
        {
            c.setSubscope(history.subscope, false);
            c.search();
        }
        
        return true;
    }

    this.navDown = function(append = false)
    {
        var results = elem('results');
        var resultElem = results.element();
        var resultCount = resultElem.getRowCount();

        var selIndex = resultElem.selectedIndex || 0;
        for (let item of resultElem.selectedItems)
        {
            let itemIndex = resultElem.getIndexOfItem(item);
            if (itemIndex > selIndex) selIndex = itemIndex;
        }

        if (append && resultElem.selectedItems.length)
        {
            log.debug("Add Next to Selection in Results");

            var selItem = resultElem.getItemAtIndex(selIndex);
            var sibling = selItem.nextSibling;
            if (sibling && selItem.resultData.allowMultiSelect && sibling.resultData.allowMultiSelect)
            {
                resultElem.addItemToSelection(sibling);
                resultElem.ensureElementIsVisible(sibling);
            }

            c.tip("Selected " + resultElem.selectedCount + " items");
        }
        else
        {
            log.debug("Navigate Down in Results");

            if (selIndex+1 == resultCount)
                resultElem.selectedIndex = selIndex = 0;
            else
                resultElem.selectedIndex = selIndex = selIndex+1;

            resultElem.ensureIndexIsVisible(selIndex);

            var data = resultElem.selectedItem.resultData;
            var description = data.name;
            if ("tip" in data) description = data.tip
            if (("description" in data) && data.description && data.description.length)
                description = data.name + " - " + data.description;
            c.tip(description);
        }
    }

    this.navUp = function(append = false)
    {
        var results = elem('results');
        var resultElem = results.element();
        var resultCount = resultElem.getRowCount();

        var selIndex = resultElem.selectedIndex;
        for (let item of resultElem.selectedItems)
        {
            let itemIndex = resultElem.getIndexOfItem(item);
            if (itemIndex < selIndex) selIndex = itemIndex;
        }

        if (append && resultElem.selectedItems.length)
        {
            log.debug("Add Previous to Selection in Results");

            var selItem = resultElem.getItemAtIndex(selIndex);
            var sibling = selItem.previousSibling;
            if (sibling && selItem.resultData.allowMultiSelect && sibling.resultData.allowMultiSelect)
            {
                resultElem.addItemToSelection(sibling);
                resultElem.ensureElementIsVisible(sibling);
            }

            c.tip("Selected " + resultElem.selectedCount + " items");
        }
        else
        {
            log.debug("Navigate Up in Results");

            if (selIndex == 0)
                resultElem.selectedIndex = selIndex = resultCount-1;
            else
                resultElem.selectedIndex = selIndex = selIndex-1;

            resultElem.ensureIndexIsVisible(selIndex);

            var data = resultElem.selectedItem.resultData;
            var description = data.name;
            if ("tip" in data) description = data.tip
            if (("description" in data) && data.description && data.description.length)
                description = data.name + " - " + data.description;
            c.tip(description);
        }
    }

    this.getSelected = function()
    {
        return elem('results').element().selectedItems.slice();
    }

    this.getSelectedResult = function()
    {
        var selected = c.getSelected();
        if ( ! selected.length) return false;
        return selected[0].resultData;
    }

    this.getSubscope = function()
    {
        return local.subscope;
    }

    this.setSubscope = function(subscope, record = true)
    {
        if (subscope && ! (subscope.scope in local.scopes))
            return log.error("Subscope does not exist: " + subscope.scope);

        if (subscope)
        {
            log.debug("Setting Subscope");

            if (local.subscope && record)
            {
                local.history.push({
                    subscope: local.subscope,
                    query: local.prevSearchValue
                });
            }

            var el = $(template('subscope', {scope: subscope, scopes: local.history}));
            elem('subscopeWrap').html(el).show();
            elem('panel').addClass("subscoped");
        }
        else
        {
            log.debug("Removing Subscope");

            elem('subscopeWrap').empty().hide();
            elem('panel').removeClass("subscoped");
        }

        local.subscope = subscope;

        this.clear();

        return true;
    }

    this.getScope = function()
    {
        try
        {
            if (local.selectedScope)
            {
                var scopeElem = elem('scope');
                return scopeElem.find("#"+local.selectedScope).element()._scope;
            }
        }
        catch (e)
        {
            log.exception(e);
        }

        return elem('scope').element().selectedItem._scope;
    }

    this.getScopeHandler = function()
    {
        var scope = c.getScope();
        return require(scope.handler);
    }
    
    this.getHistory = function()
    {
        return _.clone(local.history);
    }

    this.execScopeHandler = function(method, args)
    {
        var scope = c.getScope().handler;
        log.debug("Executing scope handler: " + method + " on " + scope);

        var result = false;
        var scopeHandler = c.getScopeHandler();
        if (method in scopeHandler)
        {
            log.debug("Executing " + method + " on scope");
            result = scopeHandler[method].apply(scopeHandler, args);
            if (result == undefined) result = true;
        }
        else
        {
            log.debug(method + " not found in scope, skipping");
        }

        if ((scope in local.handlers) && (method in local.handlers[scope]))
        {
            for (let id in local.handlers[scope][method])
            {
                log.debug("Executing Custom Handler: " + id);
                local.handlers[scope][method][id].apply(null, args);
            }
        }

        return result;
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
        
        resultElem.removeAttr("dirty");
    }

    this.clear = function()
    {
        elem('search').value("");

        c.stop();
        c.empty();
        c.search();
    }

    this.reset = function()
    {
        local.history = [];
        c.clear();
    }

    this.tip = function(tipMessage, type = "normal")
    {
        if ( ! tipMessage && local.quickSearch)
        {
            var bindLabel = keybinds.getKeybindFromCommand("cmd_showCommando");
            
            if (bindLabel != "")
                tipMessage = "TIP: Press " + bindLabel + " to quickly Go To Anything.";
        }
        
        // todo: Use localized database of tips
        elem("tip").attr("tip-type", type);
        elem("tipDesc").html(tipMessage ||
                             "TIP: Hit the right arrow key to \"expand\" your selection");
    }

    this.clearCache = function()
    {
        c.execScopeHandler("clearCache");
        c.tip("Cache Cleared");

        c.reSearch();
        c.focus();
    }

    /* Helpers */

    // XUL panel focus is buggy as hell, so we have to get crafty
    this.focus = function(times=0, timer = 10)
    {
        window.focus();
        elem('panel').focus();
        elem('search').focus();

        if (document.activeElement.nodeName != "html:input")
        {
            log.debug("Can't grab focus, retrying");
            timer = 100;
        }

        if (times < 10)
        {
            window.setTimeout(c.focus.bind(this, ++times), timer);
        }
    }

    this.prompt = function(message, label, defaultValue)
    {
        var panel = elem('panel');
        var bo = panel.element().boxObject;
        var system = require("sdk/system");

        panel.css("opacity", 0.8);

        var result =  require("ko/dialogs").prompt(message,
        {
            label: label,
            value: defaultValue,
            classNames: 'hud',
            hidechrome: system.platform != "darwin",
            features: "modal,width=600,left=" + (bo.x - 50) + ",top=" + (bo.y + 50)
        });

        panel.css("opacity", 1.0);

        return result;
    }

    this.alert = function(message)
    {
        var panel = elem('panel');
        var bo = panel.element().boxObject;

        panel.css("opacity", 0.8);

        var result = require("ko/dialogs").alert(message,
        {
            classNames: 'hud',
            hidechrome: true,
            features: "modal,width=600,left=" + (bo.x - 50) + ",top=" + (bo.y + 50)
        });

        panel.css("opacity", 1.0);
        return result;
    }

    var kitt = function()
    {
        // You didn't see this, you were never here
        if (kitt.kitt)
        {
            elem("panel").removeClass("kitt");
            delete kitt.kitt
        }
        if (["kitt", "michael"].indexOf(elem('search').value()) !== -1)
        {
            var sound = Cc["@mozilla.org/sound;1"].createInstance(Ci.nsISound);
            sound.play(ioService.newURI('chrome://commando/content/loading.wav', null, null));
            elem("panel").addClass("kitt");
            kitt.kitt = true;
        }
    }

    init();

}).apply(module.exports);
