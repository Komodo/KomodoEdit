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
        resultsByScope: {},
        searchingUuid: null,
        prevSearchValue: null,
        transitKeyBinds: false,
        renderResultsTimer: undefined,
        searchTimer: false,
        favourites: null,
        history: [],
        uilayoutTimer: -1,
        quickSearch: false,
        altPressed: false,
        altNumber: null,
        useQuickScope: false,
        quickScope: null,
        blocked: null,
        panelClone: null,
        scopeOpener: null,
        firstShow: true,
        state: {},
        resultHeightTimer: null,
        lastSearch: 0,
        showing: false,
        accesskeys: {}
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
        spinner: function () { return $("#commando-spinner"); },
        scopeFilter: function () { return $("#commando-scope-filter-wrapper"); },
        template: {
            scopeMenuItem: function() { return $("#tpl-co-scope-menuitem"); },
            scopeNavMenuItem: function() { return $("#tpl-co-scope-nav-menuitem"); },
            resultItem: function() { return $("#tpl-co-result"); },
            subscope: function() { return $("#tpl-co-subscope"); },
            scopeFilter: function() { return $("#tpl-co-scopefilter"); }
        }
    };

    /* Private Methods */

    var init = function()
    {
        log.debug('Starting Commando');

        templateBuildCache();

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
        elem('results').on("command", onSelectResult.bind(this));
        elem('subscopeWrap').on("command", onCommandSubscope.bind(this));
        elem('scopeFilter').on("command", onCommandFilter.bind(this));
        
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
            
            c.focus();
        });

        panel.on("popuphidden", function(e)
        {
            if (e.originalTarget != panel.element()) return;
            
            elem('notifyWidget').css("min-width", 0);
            local.useQuickScope = false;
        });

        window.addEventListener("click", onWindowClick);
        window.addEventListener("deactivate", function (e)
        {
            if (!local.showing)
                c.hide();
        });
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
    
    var templateBuildCache = function()
    {
        for (let name in elems.template)
        {
            local.templateCache[name] = doT.template(elems.template[name]().html());
        }
    }

    var templateEncode = function(b)
    {
        var a = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': '\\"',
            "'": "'",
            "/": "/"
        }, d = b ? /[&<>"'\/]/g : /&(?!#?\w+;)|<|>|"|'|\//g;
        return b ? b.toString().replace(d, function(b) {
            return a[b] || b;
        }) : "";
    };

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
            }
        }

        if (local.altPressed)
        {
            prevDefault = true;
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
        if ( ! local.altPressed)
            return;
        
        var prevDefault = false;
        log.debug("Event: onKeyUp");
        
        if (e.keyCode == KeyEvent.DOM_VK_ALT)
        {
            onNumberSelect();
            local.altPressed = false;
        }

        var keyPressed = String.fromCharCode(e.keyCode);
        if (keyPressed && keyPressed.match(/[^\u0000-\u007F]|\w/)) // ensure matched key is unicode
            onAccessKeySelect(keyPressed);

        e.preventDefault();
        e.stopPropagation();
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
        
        local.altNumber = null;
    }

    var onAccessKeySelect = function(key)
    {
        var elems = elem('panel').find('[accesskey="'+key+'"]');
        elems.each(function ()
        {
            let el = $(this);
            if (el.visible())
            {
                el.trigger("command");
                return;
            }
        });
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

    var onSearch = function()
    {
        if ( ! c.isOpen())
            return;
        
        c.search(null, function() {});
    }

    var onSearchComplete = function(uuid)
    {
        if (local.searchingUuid != uuid) return;

        if (local.resultUuid != uuid || local.resultsReceived == 0)
        {
            c.renderResult({
                id: "",
                name: "No Results",
                classList: "no-result-msg non-interact",
                allowExpand: false
            }, uuid);
        }

        elem("panel").removeClass("loading");
    }

    var onSelectResult = function(e)
    {
        log.debug("Selected Result(s)");

        if (e)
        {
            var target = e.target;
            while (target && target.nodeName != "richlistitem")
            {
                target = target.parentNode;
            }

            if (target && target.nodeName == "richlistitem")
            {
                var resultElem = elem('results').element();
                resultElem.selectedItem = target;
            }
        }

        var selected = c.getSelected();
        c.selectResults(selected);
    }

    var onExpandResult = function(e)
    {
        if (e)
        {
            var target = e.target;
            while (target && target.nodeName != "richlistitem")
            {
                target = target.parentNode;
            }

            if (target && target.nodeName == "richlistitem")
            {
                var resultElem = elem('results').element();
                resultElem.selectedItem = target;
            }

            e.preventDefault();
            e.stopPropagation();
        }
        else
        {
            var textbox = elem("search").element();

            if (textbox.selectionEnd != textbox.selectionStart ||
                textbox.selectionStart < textbox.value.length)
            {
                return;
            }
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
        if ( ! c.isOpen()) return;
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
        if (c.isOpen()) return;
        
        setTimeout(function() {
            c.show(undefined, true);
            c.search();
        }, 100);
    }
    
    var onCommandSubscope = function(e)
    {
        var target = e.target;
        if (target.nodeName != "button")
        {
            while (target && target.nodeName != "button")
                target = target.parentNode;

            if ( ! target || target.nodeName != 'button')
                return;
        }

        var button = $(target);
        var index = button.attr("index");

        var scope = c.getScope();
        var subscope = local.subscope;
        var offset = 1;

        var scopes = local.history.slice(0); // clone
        if ( ! scope.quickscope)
        {
            scopes.unshift({ subscope: scope, isHistory: false });
            offset++;
        }
        scopes.unshift({ subscope: null, isHistory: false });

        if (index >= scopes.length) // clicking the tail does nothing
            return;

        var newScope = scopes[index];
        if (newScope.isHistory === false)
        {
            if (newScope.subscope)
            {
                c.selectScope(newScope.subscope.id);
            }
            else if (local.quickScope)
            {
                c.selectScope(local.quickScope);
            }
        }
        else
        {
            index = index - offset;
            local.history = local.history.slice(0, index);

            c.setSubscope(newScope.subscope, false);
            c.search();
        }

        c.focus();
    }

    var onCommandFilter = function(e)
    {
        var target = e.target;
        if (target.nodeName != "button")
        {
            while (target && target.nodeName != "button")
                target = target.parentNode;

            if ( ! target || target.nodeName != 'button')
                return;
        }

        var button = $(target);
        var searchValue = c.getSearchValue();

        elem('scopeFilter').hide();
        c.selectScope(button.attr("scope"), () =>
        {
            c.search(searchValue, function() {}, true);
            c.focus();
        });
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
        
        var panel = elem('panel');
        if (panel.element().state != "open")
        {
            local.showing = true;
            panel.on("popupshown", function() {
                setTimeout(function() {
                    local.showing = false;
                }, 200); // Allow for event handlers to finish
            });
        }
        
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
        
        var search = elem('search');
        var widget = elem('notifyWidget');
        
        var left, top;
        if (local.quickSearch)
        {
            panel.addClass("quick-search");
             
            var body = _window.document.documentElement;
            $(body).css("max-width", _window.innerWidth + "px");
            
            panel.on("popupshown", function() {
                $(body).css("max-width", ""); 
            });
        }
    
        [left, top] = this.center(true);
        panel.removeClass("quick-search");
        panel.element().openPopup();
        panel.element().moveTo(left, top);
        
        if (c.execScopeHandler("onShow") === false)
        {
            search.element().select();
            c.tip();
        }
        
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
                
                if (typeof subscopeId == "function")
                {
                    subscopeId(); // callback
                    return;
                }
                
                var subscope = resultElem.find(`richlistitem[result-id="${subscopeId}"]`);
                if (subscope.length)
                {
                    var data = subscope.element().resultData;
                    if ( ! data.isScope) return;
                    
                    c.setSubscope(data, true, selectSubscope);
                }
            }, prefs.getLong("commando_result_render_delay") + 10);
        }
        
        c.selectScope(scopeId, c.search.bind(c, "", selectSubscope, true));
    }
    
    this.center = function(returnValues)
    {
        if ( ! returnValues)
        {
            // Hack to get around XUL magically adding width/height to elements, THANKS XUL!
            elem('panel').removeAttr("height");
            elem('panel').removeAttr("width");
        }
        
        var panel = elem('panel');
        
        if (local.quickSearch)
        {
            var classicMode = prefs.getBoolean('ui.classic.toolbar');
            var widget = elem('notifyWidget');
            
            var bo = widget.element().boxObject;
            var top = bo.screenY;
            
            if ( ! classicMode)
            {
                var left = bo.screenX + (bo.width / 2); // calculate center
                left -= (panel.element().boxObject.width || panelWidth) / 2;
            }
            else
            {
                var left = bo.screenX + bo.width; // calculate right edge
                left -= panel.element().boxObject.width || panelWidth;
            }
        }
        else
        {
            var top = 100;
            var anchor = elem('editor').element();
            if ( ! anchor || ! anchor.boxObject)
            {
                anchor = document.documentElement;
            }
            var bo = anchor.boxObject;
            
            var x = bo.screenX,
                y = bo.screenY;
                
            top += y;
            
            var left = x + (bo.width / 2);
            left -= (panel.element().boxObject.width || 500) / 2;
        }
        
        if (returnValues)
            return [left, top];
        else
        {
            panel.element().moveTo(left, top);
            // repeat on slight timeout, to deal with XUL oddities
            setTimeout(function() {
                c.center(true);
                c.focus(); // Work around XUL focus bugs
            }, 25);
        }
    }
    
    this._centerQuickSearch = function (returnValues)
    {
        var panel = elem('panel');
        
        var classicMode = prefs.getBoolean('ui.classic.toolbar');
        var widget = elem('notifyWidget');
        var bo = widget.element().boxObject;
        var top = bo.screenY;
        
        var x = bo.screenX;
        
        if ( ! classicMode)
        {
            var left = x + (bo.width / 2); // calculate center
            left -= (panel.element().boxObject.width || panelWidth) / 2;
        }
        else
        {
            var left = x + bo.width; // calculate right edge
            left -= panel.element().boxObject.width || panelWidth;
        }
        
        if (returnValues)
            return [left, top];
        else
        {
            panel.element().moveTo(left, top);
            // repeat on slight timeout, to deal with XUL oddities
            setTimeout(function() {
                c.center(true);
                c.focus(); // Work around XUL focus bugs
            }, 25);
        }
    }
    
    this.isOpen = function()
    {
        var state = elem('panel').element().state;
        return state == "open" || state == "showing";
    }

    this.hide = function()
    {
        c.stop();
        log.debug("Hiding Commando");
        elem('panel').element().hidePopup();
        
        if (window == _window && window.isActive)
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
        
        c.stop();

        elem("panel").addClass("loading");
        var searchDelay = prefs.getLong('commando_search_delay');
        
        log.debug("Event: onSearch");
        window.clearTimeout(local.searchTimer);
            
        var uuid = uuidGen.uuid();
        
        searchDelay = Math.max(0, searchDelay - (Date.now() - local.lastSearch));
        local.lastSearch = Date.now();
        local.searchTimer = window.setTimeout(function()
        {
            local.searchTimer = false;

            log.debug("Event: onSearch - Timer Triggered");
            
            var searchValue = elem('search').value();
    
            local.searchingUuid = uuid;
            local.prevSearchValue = searchValue;
            elem('results').attr("dirty", "true");
            elem('spinner').addClass("enabled");
            
            var _callback = function()
            {
                callback();
                onSearchComplete(uuid);
                elem('results').removeAttr("dirty");
                elem('spinner').removeClass("enabled");
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
        return elem('search').value() + ""; // force string - not object ref
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

        if (selected.length == 1 && resultData.expand)
        {
            c.expandResult(resultData);
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
            
        var getAccessKey = function(str)
        {
            for (let x=0;x<str.length;x++)
            {
                let key = str.substr(x, 1).toUpperCase();
                if ( ! (key in local.accesskeys))
                {
                    local.accesskeys[key] = id;
                    return key;
                }
            }

            return null;
        };

        if ( ! opts.accesskey)
            opts.accesskey = getAccessKey(opts.name);
            
        var _opts = Object.assign({}, opts);
        var concatonator = _opts.icon.indexOf('?') == -1 ? '?' : '&';
        _opts.icon += concatonator + "scheme-color=textbox-foreground";

        var scopeElem = $(template('scopeMenuItem', _opts)).element();
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

    this.selectScope = function(scopeId, callback)
    {
        this._selectScope(scopeId);
        
        local.history = [];
        
        c.stop();
        c.empty();
        c.setSubscope(null, true, callback); 
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

        local.selectedScope = selectItem.id.substr(6);
    }

    this.renderResult = function(result, searchUuid)
    {
        this.renderResults([result], searchUuid);
    }

    this.renderResults = function(results, searchUuid, cacheOrigin, noDelay = false)
    {
        if ( ! results.length) return;
        
        // Prepare wordRx for highlighting matched words
        var searchValue = elem('search').value().trim();
        var wordRx;

        if (searchValue)
        {
            var words = searchValue.split(/\s+/);
            words = words.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
            wordRx = new RegExp(`(${words.join('|')})`, 'gi');

            // We need an intermediate replacement strategy because templateEncode
            // would otherwise encode our html tags
            var wordReplacement = ':html:strong:$1:/html:strong:';
            var wordReplacedRx = /:html:strong:(.*?):\/html:strong:/g;
            var wordReplacedReplacement = '<html:strong>$1</html:strong>';
        }

        var wordHighlight = (str) =>
        {
            str = str.replace(wordRx, wordReplacement);
            str = templateEncode(str);
            str = str.replace(wordReplacedRx, wordReplacedReplacement);
            return str;
        };

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
            local.resultsByScope = {};
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

        log.debug(searchUuid + " - Rendering "+results.length+" Results");

        // Replace result elem with temporary cloned node so as not to paint the DOM repeatedly
        var resultElem = elem('results', true);
        
        // Delay height updates so it doesn't flicker too much while searching
        var height = resultElem.css("height");
        if ((height == "inherit" || ! height) && resultElem.element().boxObject.height > 150)
        {
            resultElem.css("height", resultElem.element().boxObject.height);
            clearTimeout(local.resultHeightTimer);
            local.resultHeightTimer = setTimeout(() =>
            {
                elem('results', true).css("height", "inherit");
            }, prefs.getLong("commando_result_render_delay") + prefs.getLong("commando_search_delay") + 50);
        }
        
        var fragment = $(document.createDocumentFragment());
        var isNew = local.resultsRendered === 0;

        if (isNew)
        {
            local.resultsByScope = {};
        }

        if ( ! isNew)
        {
            fragment.append(resultElem.children());
        }
        
        for (let result of results)
        {
            if (local.favourites.findString(result.id) != -1)
            {
                result.favourite = true;
            }
            
            if (result.description && result.description.length > 300)
                result.description = result.description.substr(0, 300) + " [..]";

            if (result.icon && result.icon.substr(0,6) == 'koicon' &&
                               result.icon.substr(-3) == 'svg')
            {
                result.icon += "?scheme-color=textbox-foreground";
            }

            result.subscope = local.subscope;

            // Highlight matched words
            result.nameHighlighted = templateEncode(result.name);
            if (wordRx)
                result.nameHighlighted = wordHighlight(result.nameHighlighted);

            result.descriptionHighlighted = templateEncode(result.description || "");
            if (wordRx && result.description)
                result.descriptionHighlighted = wordHighlight(result.descriptionHighlighted);

            result.descriptionPrefixHighlighted = templateEncode(result.descriptionPrefix || "");
            if (wordRx && result.descriptionPrefix)
                result.descriptionPrefixHighlighted = wordHighlight(result.descriptionPrefixHighlighted);
            
            let resultEntry, appended = false;
            try
            {
                result.multiline = true;
                result.searchQuery = searchValue ? searchValue : false;
                result.accesskey = result.accesskey || "";
                resultEntry = $.createElement(template('resultItem', result));
                resultEntry.resultData = result;
                fragment.append(resultEntry);
                appended = true;
            }
            catch (e)
            {
                log.exception(e, "Failed rendering result: " + result.name);
            }
            
            if (appended) this.sortResult(resultEntry);

            if (result.scope)
            {
                if ( ! (result.scope in local.resultsByScope))
                    local.resultsByScope[result.scope] = 0;
                local.resultsByScope[result.scope]++;
            }
        }

        var counter = 1;
        fragment.find("label.number").each(function()
        {
            this.textContent = counter++;
        });

        fragment.find('button[anonid="expand"]').on("command", onExpandResult);

        // remove results exceeding max
        var maxResults = prefs.getLong("commando_search_max_results");
        fragment.find(`richlistitem:nth-child(n+${maxResults+1})`).remove();
        
        var resultsByScope = local.resultsByScope;
        if (isNew)
            this.empty();
        local.resultsByScope = resultsByScope;

        resultElem.empty().append(fragment);

        resultElem.addClass("has-results");
        resultElem.removeAttr("dirty");
        elem('spinner').removeClass("enabled");
        resultElem.css("maxHeight", (window.screen.availHeight / 2) + "px");

        local.resultsRendered = resultElem.childCount();

        resultElem.element().selectedIndex = 0;
        resultElem.element().scrollTop = 0;
        resultElem.element().ensureIndexIsVisible(0);
        
        elem('panel').css("min-height", "auto");
        elem('panel').removeAttr("height");
        elem('panel').removeAttr("width");
        setTimeout(function() {
            elem('panel').removeAttr("height");
            elem('panel').removeAttr("width");
            resultElem.element().scrollTop = 0;
            resultElem.element().ensureIndexIsVisible(0);
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
        
        c.renderScopeFilters();

        c.tip();
        onPreview();
        c.center();
    }
    
    this.renderScopeFilters = function()
    {
        var scopeFilter = elem('scopeFilter');
        scopeFilter.empty();
        var scopes = [];

        var maxResults = prefs.getLong("commando_search_max_results");

        for (let scope in local.resultsByScope)
        {
            if ( ! (scope in local.scopes))
                continue;
            if (local.scopes[scope].quickscope)
                break;

            scopes.push({
                scope: local.scopes[scope],
                count: local.resultsByScope[scope] == maxResults ? `${maxResults}+` : local.resultsByScope[scope]
            });
        }

        if ( ! scopes.length || ! c.getScope().quickscope)
        {
            scopeFilter.hide();
            return;
        }

        var val = template('scopeFilter', { scopes: scopes });
        scopeFilter.show().append($(val));
        
        var checkOverflow = () =>
        {
            scopeFilter.removeClass("overflown");
            if (scopeFilter.element().scrollWidth > scopeFilter.element().clientWidth)
                scopeFilter.addClass("overflown");
        };

        clearTimeout(c.renderScopeFilters._overflowTimer);
        c.renderScopeFilters._overflowTimer = setTimeout(checkOverflow, prefs.getLong("commando_result_render_delay") + 10);
    }
    this.renderScopeFilters._overflowTimer = null;
    
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
        var cont = true;
        while (elem.previousSibling && cont)
        {
            let current = elem.resultData;
            let previous = elem.previousSibling.resultData;
            let currentWeight = current.weight || 0;
            let prevWeight = previous.weight || 0;

            if ( ! current)
                continue;

            if ( ! previous || (currentWeight > prevWeight))
                elem.parentNode.insertBefore(elem, elem.previousSibling);
            else
                cont = false;
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
        if ( ! c.getSubscope() && local.quickScope && local.useQuickScope && local.quickScope != c.getScope().id)
        {
            c.selectScope(local.quickScope);
            return;
        }
        
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
            
            elem('search').attr("placeholder", subscope.placeholder || "");
        }

        local.subscope = subscope;

        this.clear(callback);
        this.renderSubscopes();

        return true;
    }

    this.renderSubscopes = function()
    {
        var scope = c.getScope();
        var subscope = local.subscope;
        var subscopeWrap = elem('subscopeWrap');

        if (scope.quickscope && ! subscope)
        {
            subscopeWrap.empty().hide();
            elem('panel').removeClass("subscoped");
            return;
        }

        var scopes = local.history.slice(0); // clone
        if ( ! scope.quickscope)
            scopes.unshift({ subscope: scope });
        scopes.unshift({ subscope: {
            name: "Go",
            accesskey: "",
            icon: "koicon://ko-svg/chrome/fontawesome/skin/search.svg?size=16"
        }});
        if (subscope && scope.id != subscope.id)
            scopes.push({ subscope: subscope });

        var el = $(template('subscope', {scopes: scopes}));
        subscopeWrap.empty();
        subscopeWrap.append(el).show();
        elem('panel').addClass("subscoped");

        var checkOverflow = () =>
        {
            var buttons = subscopeWrap.find("button");
            var index = 0;
            var count = buttons.length;
            while (index < count && subscopeWrap.element().scrollWidth > subscopeWrap.element().clientWidth)
            {
                let button = buttons.element(index++);
                button.classList.add("short");
            }
        };

        clearTimeout(c.renderSubscopes._overflowTimer);
        c.renderSubscopes._overflowTimer = setTimeout(checkOverflow, prefs.getLong("commando_result_render_delay") + 10);
    }
    this.renderSubscopes._overflowTimer = null;

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
        if ( ! state || ! state.resultElemChildren.children()) return false;
        
        log.debug("Restoring state for " + scope);
        
        try
        {
            for (let k in state.local)
                local[k] = state.local[k];
            
            c._selectScope(local.selectedScope);
                
            elem('results').append(state.resultElemChildren.children());
            elem('subscopeWrap').replaceWith(state.subscopeElem);
            
            local.elemCache = {};
            
            elem('results').element().selectedIndex = state.resultIndex;
            elem('results').element().ensureIndexIsVisible(state.resultIndex);
            elem('search').value(local.prevSearchValue);
        }
        catch (e)
        {
            log.exception(e);
            return false;
        }
        
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
        local.resultsByScope = {};
        
        resultElem.removeAttr("dirty");
        elem('spinner').removeClass("enabled");
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
        let selected = this.getSelectedResult();

        if ( ! tipMessage && local.quickSearch)
        {
            var bindLabel = keybinds.getKeybindFromCommand("cmd_showCommando");
            
            if (bindLabel != "")
                tipMessage = "TIP: Press " + bindLabel + " to quickly Go To Anything.";
        }

        if (!tipMessage && selected.allowExpand !== false) {
            tipMessage = 'TIP: Hit the right arrow key to "expand" your selection';
        }

        // todo: Use localized database of tips
        elem("tip").attr("tip-type", type);
        elem("tip").text(tipMessage || "");
        
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
    this.focus = function(times=0)
    {
        if (elem('search').visible())
        {
            if (times === 0)
                window.focus();
                
            elem('search').focus();

            if (document.activeElement.nodeName != "html:input" && times < 10)
            {
                log.debug("Can't grab focus, retrying");
                window.setTimeout(c.focus.bind(this, ++times), 10);
            }
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
