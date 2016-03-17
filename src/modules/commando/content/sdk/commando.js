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
    const prefs     = require("ko/prefs");
    const _window   = require("ko/windows").getMain();

    const ioService = Cc["@mozilla.org/network/io-service;1"]
                        .getService(Ci.nsIIOService);

    const KeyEvent = _window.KeyEvent;

    // Short alias for the commando scope.
    const c = this;

    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    var widgetWidth = 350;
    var panelWidth = 500;

    var local = {
        scopes: {},
        subscope: null,
        handlers: {},
        elemCache: {},
        templateCache: {},
        resultUuid: [],
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
        altPressed: false,
        altNumber: null,
        useQuickScope: false,
        quickScope: null,
        blocked: null,
        panelClone: null,
        scopeOpener: null,
        firstShow: true,
        state: {}
    };

    var elems = {
        panelWindow: function() { return $("#commando-panel", _window); },
        editor: function() { return $("#komodo-editor-vbox"); },
        panel: function() { return $("#commando-panel"); },
        scope: function() { return $("#commando-scope"); },
        subscopeWrap: function() { return $("#commando-subscope-wrap"); },
        results: function() { return $("#commando-results"); },
        search: function() { return $("#commando-search"); },
        scopePopup: function() { return $("commando-scope-menupopup"); },
        scopesSeparator: function() { return $("#scope-separator"); },
        menuItem: function() { return $("#menu_show_commando"); },
        tip: function() { return $("#commando-tip"); },
        preview: function() { return $("#commando-preview"); },
        notifyWidget: function() { return $("#notification-widget-textbox"); },
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
        
        // If this is a secondary commando instance, load up the UI
        // from the main window and register its scopes
        if ( ! elem('panel').length)
        {
            var _c = _window.require("commando");
            $(document.documentElement).append(
                _c.getPanelClone()
            );
            var scopes = _c.getRegisteredScopes();
            for (let id in scopes)
            {
                if (scopes.hasOwnProperty(id))
                    c.registerScope(id, scopes[id]);
            }
            
            var styleUtil = require("sdk/stylesheet/utils");
            styleUtil.loadSheet(window, "less://commando/skin/commando.less", "author");
            
            local.elemCache = {}
        }
        else
        {
            local.panelClone = elem('panel').clone();
        }
        
        elem('search').on("input", onSearch.bind(this));
        elem('search').on("keydown", onKeyNav.bind(this));
        elem('search').on("keyup", onKeyUp.bind(this));
        elem('scope').on("command", onChangeScope.bind(this));
        elem('results').on("keydown", onKeyNav.bind(this));
        elem('results').on("dblclick", onSelectResult.bind(this));
        
        /* Notification widget & quick search */
        $("#notification-widget-default-text").value("Go to Anything");
        elem("notifyWidget").on("click", function(e) {
            if (e.target.nodeName == "label" && e.target.getAttribute("anonid") == "notification-widget-text")
                onQuickSearchFocus();
        });
        
        if (window == _window)
        {
            local.transitKeyBinds = prefs.getBoolean("transit_commando_keybinds", false);
            if (local.transitKeyBinds)
            {
                log.debug("Transitioning keybinds");
                prefs.deletePref("transit_commando_keybinds");
            }
        }
        
        local.favourites = prefs.getPref('commando_favourites');

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
            
            elem('notifyWidget').css("min-width", 0);
            local.open = false;
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
        
        if (local.blocked)
        {
            e.preventDefault();
            return false;
        }

        // Todo: support selecting multiple items
        switch (e.keyCode)
        {
            case KeyEvent.DOM_VK_ESCAPE:
                if (c.getSearchValue() != "")
                {
                    c.clear();
                }
                else if (c.getSubscope())
                {
                    c.navBack();
                }
                else if (local.quickScope && local.useQuickScope && local.quickScope != c.getScope().id)
                {
                    c.selectScope(local.quickScope);
                }
                else
                {
                    c.hide();
                }
                prevDefault = true;
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
        
        var numberNav = prefs.getBoolean('commando_navigate_by_number', true);
        numberNav = numberNav && ! local.prevSearchValue;
        if (numberNav || (local.altPressed && e.keyCode != KeyEvent.DOM_VK_ALT))
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
                
                if (numberNav && ! local.altPressed)
                {
                    if (local.numberSelectTimer)
                    {
                        window.clearTimeout(local.numberSelectTimer);
                    }
                    
                    var delay = prefs.getLongPref('commando_number_select_delay');
                    local.numberSelectTimer = window.setTimeout(onNumberSelect.bind(this), delay);
                }
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
        
        onNumberSelect();
    }
    
    var onNumberSelect = function()
    {
        log.debug("Event: onNumberSelect");
        
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
        c.navDown(e && e.shiftKey)
        onPreview(e);
    }

    var onNavUp = function(e)
    {
        if (e.ctrlKey) {
            c.onNavBack();
        } else {
            c.navUp(e && e.shiftKey);
        }
        onPreview(e);
    }
    
    var onPreview = function(e)
    {
        if (elem('panel').hasClass("maximized"))
        {
            elem('panel').removeClass("maximized");
        }
        
        if ( ! c.execScopeHandler("onPreview"))
        {
            if (elem('preview').visible())
            {
                elem('preview').hide();
                elem('preview').empty();
                elem('panel').removeClass("previewing");
                c.center();
            }
            return;
        }
        
        c.preview();
    }
    
    this.onPreview = onPreview;

    var onSearch = function(e)
    {
        var uuid = c.search(null, function() {});
    }

    var onSearchComplete = function(uuid)
    {
        if (local.searchingUuid != uuid) return;

        if (local.resultUuid != uuid || local.resultsReceived == 0)
        {
            c.renderResult({
                id: "",
                name: "No Results",
                classList: "no-result-msg non-interact"
            }, uuid);
        }

        elem("panel").removeClass("loading");
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
                scopeElem.element().selectedItem = scopeElem.find("#scope-"+local.selectedScope).element();
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
        var bo = elem('panel').element().boxObject;
        if ((e.screenX > bo.screenX && e.screenX < (bo.screenX + bo.width)) &&
            (e.screenY > bo.screenY && e.screenY < (bo.screenY + bo.height)))
        {
            return;
        }
        c.hide();
    }
    
    var onQuickSearchFocus = function(e)
    {
        if (local.open) return;
        
        setTimeout(function() {
            c.show(undefined, true);
            c.search();
        }, 100);
    }
    
    /* Public Methods */
    this.toggle = function(scope)
    {
        log.debug("Toggling");
        
        // If calling show again, with the same scope, treat this as a toggle
        if (c.isOpen() && (! scope || scope == local.scopeOpener))
        {
            c.hide();
            return;
        }
        
        c.show(scope);
    }
    
    this.show = function(scope, quickSearch)
    {
        log.debug("Showing Commando");
        
        if (quickSearch === undefined)
        {
            var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
            var recentWindow = wm.getMostRecentWindow(null);
            
            if (_window == recentWindow && elem("notifyWidget").visible())
                quickSearch = true;
        }
        
        local.quickSearch = quickSearch;
        
        if ( ! scope || scope == local.quickScope)
            local.useQuickScope = true;
            
        var preserve = prefs.getBooleanPref('commando_preserve_query');
        var scopeChanged = false;
        if (scope && (scope != local.scopeOpener || ! preserve))
        {
            c.storeState();
            
            if ( ! c.restoreState(scope))
            {
                scopeChanged = true;
                c.selectScope(scope);
            }
        }
        
        local.scopeOpener = scope;
        
        var panel = elem('panel');
        var search = elem('search');
        var widget = elem('notifyWidget');
        
        var left, top;
        if (local.quickSearch)
        {
            panel.addClass("quick-search");
            
            var body = _window.document.documentElement;
            $(body).css("max-width", body.width + "px");
            
            panel.on("popupshown", function() {
                $(body).css("max-width", "");
            });
            
            widget.css("min-width", (panelWidth-10) + "px");
            panel.element().openPopup(widget.element(), "topcenter");
        }
        else
        {
            [left, top] = this.center(true);
            panel.removeClass("quick-search");
            panel.element().openPopup(undefined, undefined, left, top);
        }
        
        
        if (c.execScopeHandler("onShow") === false)
        {
            search.element().select();
            c.tip();
        }
        
        // Force local.open now for sync calls that depend on it
        local.open = true;
        
        if (scopeChanged || local.firstShow)
        {
            local.firstShow = false;
            c.search();
        }
        
        elem('search').element().select();
        c.center();
    }
    
    this.showSubscope = function()
    {
        var scopeIds = Array.slice(arguments);
        var scopeId = scopeIds.shift();
        
        c.show(scopeId);
        var resultElem = elem('results');
        
        var selectSubscope = () =>
        {
            window.setTimeout(() => {
                var subscopeId = scopeIds.shift();
                if (! subscopeId) return;
                
                var subscope = resultElem.find(`richlistitem[result-id="${subscopeId}"]`);
                if (subscope.length)
                {
                    var data = subscope.element().resultData;
                    if ( ! data.isScope) return;
                    
                    c.setSubscope(data, false, selectSubscope);
                }
            }, prefs.getLong("commando_result_render_delay") + 10);
        }
        
        c.search("", selectSubscope, true);
    }
    
    this.center = function(returnValues)
    {
        if (local.quickSearch) return;
        
        if ( ! returnValues)
        {
            // Hack to get around XUL magically adding width/height to elements, THANKS XUL!
            elem('panel').removeAttr("height");
            elem('panel').removeAttr("width");
        }
        
        var panel = elem('panel');
        
        var top = 100;
        var anchor = elem('editor').element();
        if ( ! anchor || ! anchor.boxObject)
        {
            anchor = document.documentElement;
        }
        var bo = anchor.boxObject;
        
        var x = bo.x, y= bo.y;
        if ( ! returnValues) x = bo.screenX, y = bo.screenY;
        
        var left = x + (bo.width / 2);
        left -= (panel.element().boxObject.width || 500) / 2;
        
        if (returnValues)
            return [left, top];
        else
        {
            panel.element().moveTo(left, y + top);
            // repeat on slight timeout, to deal with XUL oddities
            setTimeout(function() {
                c.center(true);
                c.focus(); // Work around XUL focus bugs
            }, 25);
        }
    }
    this.isOpen = function()
    {
        return local.open;
    }

    this.hide = function()
    {
        elem('panel').element().hidePopup();
        
        if (window == _window)
        {
            var view = _window.ko.views.manager.currentView;
            if (view && view.getAttribute("type") == "editor")
                view.scintilla.focus();
        }
    }

    this.search = function(value, callback, noDelay = false)
    {
        if (value)
        {
            elem('search').value(value);
        }

        if ( ! callback) // this is a manual search
            return onSearch();
        
        if (local.searchTimer && ! noDelay) return; // Search is already queued
        
        c.stop();

        elem("panel").addClass("loading");
        var searchDelay = prefs.getLong('commando_search_delay');

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

            local.searchingUuid = uuid;
            local.prevSearchValue = searchValue;
            
            elem('results').attr("dirty", "true");
            
            var _callback = function()
            {
                callback();
                onSearchComplete(uuid);
                elem('results').removeAttr("dirty");
            };

            var subscope = c.getSubscope();
            if (subscope && subscope.isExpanded)
            {
                c.expandSearch(searchValue, local.searchingUuid, _callback);
            }
            else
            {
                // perform onSearch
                log.debug(local.searchingUuid + " - Starting Search for: " + searchValue);
                c.execScopeHandler("onSearch", [searchValue, local.searchingUuid, _callback])
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
    
    this.refresh = this.reSearch;

    this.expandSearch = function(query, uuid, callback)
    {
        var subscope = c.getSubscope();

        var results = [
            {
                id: "open",
                name: "Open",
                weight: 50,
                allowExpand: false,
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
        var resultData = selected.slice(0)[0].resultData;
        if (selected.length == 1 && resultData.isScope)
        {
            if ( ! c.setSubscope(resultData))
            {
                // Scope is already set
                this.clear();
            }
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

    this.expandResult = function(selected = null)
    {
        if ( ! selected)
            selected = this.getSelectedResult();
        
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

        // Don't register command or keybindings if this is not the main
        // commando instance
        if (window == _window)
        {
            // Register command
            commands.register(id, this.toggle.bind(this, id), {
                defaultBind: opts.keybind,
                label: "Commando: Toggle Commando with the " + opts.name + " scope"
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

    this.selectScope = function(scopeId, hotSwap = false)
    {
        this._selectScope(scopeId);
        
        local.history = [];
        
        c.stop();
        c.empty();
        c.setSubscope(null); 
    }
    
    this._selectScope = function(scopeId)
    {
        log.debug("_selectScope(): " + scopeId);
        
        var scopeElem = elem('scope');
        var selectedItem = scopeElem.element().selectedItem;

        if (typeof scopeId != "string")
            var selectItem = scopeId;
        else
            var selectItem = scopeElem.find("#scope-" + scopeId).element();

        if ( ! selectItem)
        {
            log.error("_selectScope: Scope could not be found: " + scopeId);
            return;
        }

        scopeElem.element().selectedItem = selectItem;
        scopeElem.attr("image", scopeElem.attr("image") + "?preset=hud");

        local.selectedScope = selectItem.id.substr(6);
    }

    this.renderResult = function(result, searchUuid)
    {
        this.renderResults([result], searchUuid);
    }

    this.renderResults = function(results, searchUuid, cacheOrigin, noDelay = false)
    {
        if ( ! results.length) return;
        
        if (local.searchingUuid != searchUuid && local.resultUuid == searchUuid)
        {
            log.debug(searchUuid + " - Skipping "+results.length+" results for old search uuid: " + searchUuid);
            return;
        }
        
        if (local.searchingUuid == searchUuid && local.resultUuid != searchUuid)
        {
            local.resultCache = [];
            local.resultsReceived = 0;
            local.resultsRendered = 0;
            local.resultUuid = searchUuid;
        }
        
        if ( ! cacheOrigin)
            local.resultsReceived += results.length;
        
        if ( ! noDelay)
        {
            local.resultCache = local.resultCache.concat(results);
    
            if ( ! local.renderResultsTimer)
            {
                log.debug("Setting result timer");
                window.clearTimeout(local.renderResultsTimer);
                local.renderResultsTimer = window.setTimeout(function()
                {
                    log.debug("Triggering result timer");
                    this.renderResults(local.resultCache, searchUuid, true, true);
                    local.resultCache = [];
                    local.renderResultsTimer = false;
                }.bind(this), prefs.getLong("commando_result_render_delay"));
            }
            return;
        }
        
        if (local.resultsRendered === 0)
            this.empty(); // Force empty results

        log.debug(searchUuid + " - Rendering "+results.length+" Results");

        // Replace result elem with temporary cloned node so as not to paint the DOM repeatedly
        var resultElem = elem('results', true);
        var tmpResultElem = resultElem.element().cloneNode();
        resultElem.element().clearSelection();
        resultElem = $(resultElem.replaceWith(tmpResultElem));
        
        var maxResults = prefs.getLong("commando_search_max_results", 50);
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
            
            if (result.icon && result.icon.substr(0,6) == 'koicon' &&
                               result.icon.substr(-3) == 'svg')
            {
                result.icon += "?preset=hud"
            }

            result.subscope = local.subscope;
            
            let resultEntry, appended = false;
            try
            {
                resultEntry = $.createElement(template('resultItem', result));
                resultEntry.resultData = result;
                resultElem.element().appendChild(resultEntry);
                appended = true;
            }
            catch (e)
            {
                log.exception(e, "Failed rendering result: " + result.name);
            }
            
            if (appended) this.sortResult(resultEntry);
        }

        resultElem.addClass("has-results");
        resultElem.removeAttr("dirty");
        resultElem.css("maxHeight", (window.screen.availHeight / 2) + "px");
        
        var counter = 1;
        resultElem.find("label.number").each(function()
        {
            this.textContent = counter++;
        });

        tmpResultElem.parentNode.replaceChild(resultElem.element(), tmpResultElem);

        c.navDown();
        
        elem('panel').css("min-height", "auto");
        elem('panel').removeAttr("height");
        elem('panel').removeAttr("width");
        setTimeout(function() {
            elem('panel').removeAttr("height");
            elem('panel').removeAttr("width");
        }, 100);
        
        // Work around weird XUL flex issue where the richlistbox shows a scrollbar
        // when none is needed
        var resultElem = elem('results');
        var height = resultElem.element().boxObject.height;
        var maxHeight = resultElem.css("max-height");
        maxHeight = parseInt(maxHeight.substr(0,maxHeight.length-2));
        
        if (height+5 > maxHeight)
        {
            resultElem.addClass("scrollable");
        }
        else
        {
            resultElem.removeClass("scrollable");
        }
        
        c.reloadTip();
        onPreview();
        c.center();
    }

    this.filter = function(results, query, field = "name")
    {
        var words = query.toLowerCase().split(/\s+/);

        var passes = function(result)
        {
            if ( ! (field in result))
                return false;

            for (let w in words)
            {
                if (result[field].toLowerCase().indexOf(words[w]) == -1)
                    return false;
            }

            return true;
        };

        if (Array.isArray(results))
        {
            return results.filter(passes);
        }
        {
            var _results = {};
            for (let k in results)
            {
                if (passes(results[k]))
                {
                    _results[k] = results[k];
                }
            }
            return _results;
        }
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
    
    this.selectFirstResult = function()
    {
        var results = elem('results');
        var resultElem = results.element();
        resultElem.selectedIndex = 0;
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
    
    this.preview = function()
    {
        elem('panel').css("min-height", "600px");
        elem('panel').addClass("previewing");
        elem('preview').show();
        
        c.center();
    }
    
    this.maximizePreview = function()
    {
        if ( ! elem('panel').hasClass("previewing"))
        {
            log.warning("Cannot maximize nonexistant preview")
            return;
        }
        
        elem('panel').addClass("maximized");
        elem('panel').css("min-height", "400px");
        
        c.center();
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

    this.setSubscope = function(subscope, record = true, callback = () => {})
    {
        if (subscope && ! (subscope.scope in local.scopes))
            return log.error("Subscope does not exist: " + subscope.scope);
        
        elem('search').removeAttr("placeholder");
    
        if (subscope)
        {
            log.debug("Setting Subscope");

            if (local.subscope && subscope.id == local.subscope.id)
                return false;

            if (local.subscope && record)
            {
                local.history.push({
                    subscope: local.subscope,
                    query: local.prevSearchValue
                });
            }

            var el = $(template('subscope', {scope: subscope, scopes: local.history}));
            elem('subscopeWrap').empty();
            elem('subscopeWrap').append(el).show();
            elem('panel').addClass("subscoped");
            
            elem('search').attr("placeholder", subscope.placeholder || "");
        }
        else
        {
            log.debug("Removing Subscope");

            elem('subscopeWrap').empty().hide();
            elem('panel').removeClass("subscoped");
        }

        local.subscope = subscope;

        this.clear(callback);

        return true;
    }

    this.getScope = function()
    {
        try
        {
            if (local.selectedScope)
            {
                var scopeElem = elem('scope');
                return scopeElem.find("#scope-"+local.selectedScope).element()._scope;
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
    
    this.getPanelClone = function()
    {
        return local.panelClone.clone();
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
    
    this.restoreState = function(scope)
    {
        if ( ! prefs.getBooleanPref('commando_preserve_query')) return;
        
        var state = local.state[scope] || false;
        if ( ! state) return false;
        
        log.debug("Restoring state for " + scope);
        
        for (let k in state.local)
            local[k] = state.local[k];
        
        c._selectScope(local.selectedScope);
            
        elem('results').append(state.resultElemChildren.children());
        elem('subscopeWrap').replaceWith(state.subscopeElem);
        
        local.elemCache = {};
        
        elem('results').element().selectedIndex = state.resultIndex;
        elem('results').element().ensureIndexIsVisible(state.resultIndex);
        elem('search').value(local.prevSearchValue);
        
        c.center();
        onPreview();
        
        return true;
    }
    
    this.storeState = function()
    {
        if ( ! prefs.getBooleanPref('commando_preserve_query')) return;
        
        var scope = local.scopeOpener;
        if ( ! scope) return;
        
        log.debug("Storing state for " + scope);
        
        var resultElem = elem('results');
        var selectedIndex = elem('results').element().selectedIndex;
        resultElem.element().clearSelection();
        
        var children = $("<box/>");
        children.append(resultElem.children());
        
        local.state[scope] = {
            local: {
                prevSearchValue: local.prevSearchValue,
                resultsReceived: local.resultsReceived,
                resultsRendered: local.resultsRendered,
                selectedScope: local.selectedScope,
                history: _.clone(local.history),
                subscope: _.clone(local.subscope)
            },
            resultElemChildren: children,
            resultIndex: selectedIndex,
            subscopeElem: elem('subscopeWrap').clone(true)
        }
    }

    this.stop = function()
    {
        local.prevSearchValue = null;
        local.searchingUuid = null;
        
        if (local.renderResultsTimer)
        {
            window.clearTimeout(local.renderResultsTimer);
            local.renderResultsTimer = false;
        }
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

    this.clear = function(callback = () => {})
    {
        elem('search').value("");

        c.stop();
        c.empty();
        c.search("", callback);
    }

    this.block = function()
    {
        elem("panel").addClass("blocked");
        elem("search").attr("disabled", true);
        local.blocked = true;
    }
    
    this.unblock = function()
    {
        elem("panel").removeClass("blocked");
        elem("search").removeAttr("disabled");
        local.blocked = false;
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
        elem("tip").text(tipMessage ||
                             'TIP: Hit the right arrow key to "expand" your selection');
        
        c.reloadTip();
    }
    
    this.reloadTip = function()
    {
        var tip = elem("tip");
        var results = elem('results');
        
        tip.removeAttr("height");
        var height = tip.element().boxObject.height;
        tip.attr("height", height);
        
        tip.css("margin-top", "1px");
        results.css("margin-bottom", "-1px");
        setTimeout(function()
        {
             tip.element().style.removeProperty("margin-top");
             results.element().style.removeProperty("margin-bottom");
        }, 50);
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
        if (elem('search').visible())
        {
            window.focus();
            elem('panel').focus();
            elem('search').focus();
    
            if (document.activeElement.nodeName != "html:input")
            {
                log.debug("Can't grab focus, retrying");
                timer = 100;
            }
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

    init();

}).apply(module.exports);
