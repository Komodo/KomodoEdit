/* Copyright (c) 2012 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * ko.widgets implementation
 * This implements ko.widgets, one per window, meant mostly for JS use
 */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.widgets)=='undefined') {
    ko.widgets = {};
}

(function() {
    /**
     * Substitute default parameters
     * @param aParams {Object} the parameters
     * @param aDefaults {Object} default values
     * @returns {Object} the parsed parameters
     *
     * Example:
     * function foo(aParams) {
     *   var {param1, param2} = parseParams(aParams, {param1: true, param2: 1});
     * }
     */
    function parseParams(aParams, aDefaults) {
        let props = {}, params = aParams || {};
        for (let prop of Object.keys(params)) {
            props[prop] = Object.getOwnPropertyDescriptor(params, prop);
        }
        return Object.create(aDefaults, props);
    }

    let { classes: Cc, interfaces: Ci, results: Cr, utils: Cu } = Components;
    let _import = function _import(url) { let obj = {}; Cu.import(url, obj); return obj; }
    let {Services} = _import("resource://gre/modules/Services.jsm");
    let {XPCOMUtils} = _import("resource://gre/modules/XPCOMUtils.jsm");
    let {logging} = _import("chrome://komodo/content/library/logging.js");
    let {Dict} = _import("resource://gre/modules/Dict.jsm");
    let log = logging.getLogger("ko.widgets");
    //log.setLevel(logging.LOG_DEBUG);
    log.debug("initializing...");

    let layoutRestored = false;
    let appStartupCompleted = false;

    this._widgets = new Dict(); // key: id; value:
        ({   /* this._widgets value type: */
            URL: String,
            label: String,
            shortLabel: String,
            defaultPane: String, // pane id
            iconURL: String,
            inactiveIconURL: String || null,
            persist: Boolean, // whether to persist widget position data
            show: Boolean, // true, false, or undefined (to use prefs)
            forceLoad: Boolean, // if true, always load the widget somewhere
            browser: null, // or <browser type="ko-widget">
            loadCallbacks: [], // functions to call when the browser has finished loading
            autoload: Number, // or missing
            attrs: {} // String(name) -> String(value)
        });
    this._panes = new Dict(); // key: id; value: <ko-pane>

    this.registerWidget = function koWidgetManager_registerWidget(aID, aLabel, aURL, aParams) {
        if (typeof(aLabel) !== "string") {
            log.exception("registerWidget: No ID given");
            throw Components.Exception("No ID given", Cr.NS_ERROR_INVALID_ARG);
        }
        if (typeof(aLabel) !== "string") {
            log.exception("registerWidget: No label given");
            throw Components.Exception("No label given", Cr.NS_ERROR_INVALID_ARG);
        }
        if (typeof(aURL) !== "string") {
            log.exception("registerWidget: No URL given");
            throw Components.Exception("No URL given", Cr.NS_ERROR_INVALID_ARG);
        }
        let {defaultPane, iconURL, inactiveIconURL, persist, show, _widget} =
            parseParams(aParams, {defaultPane: null,
                                  iconURL: null,
                                  inactiveIconURL: null,
                                  persist: true,
                                  show: undefined,
                                 });
        log.debug("registerWidget(" + [aID, aLabel, aURL].join(", ") + ", " +
                  JSON.stringify(aParams) + ")");

        let id = String(aID), label = String(aLabel), url = String(aURL);
        // check that the URL given smells like one
        Services.io.newURI(url, null, null);
        if (this._widgets.has(id)) {
            // given id already exists
            return false;
        }
        this._widgets.set(id, { URL:             url,
                                label:           label,
                                defaultPane:     defaultPane,
                                iconURL:         iconURL,
                                inactiveIconURL: inactiveIconURL,
                                persist:         persist,
                                show:            show,
                                forceLoad:       false,
                                browser:         null,
                                loadCallbacks:   [],
                                attrs:           {},
                              });
        if (appStartupCompleted) {
            // Application startup / widget restore has completed; show the
            // widget now if it seems useful to do so.
            if (show === undefined) {
                show = (this._persist_state.widgets[id.substr(1)] || {}).show || false;
            }
            if (show) {
                // we want to show this widget
                this.getWidget(id, true);
            }
        }
        return true;
    };

    /**
     * Helper to get the widget data given a widget ID
     * @returns widget data, or null
     */
    this._get = function koWidgetManager__get(aID) {
        return this._widgets.get(aID, null);
    };

    /**
     * Register a widget from an existing element
     * Called from the <ko-pane> constructor; note that the pain will be removed
     * right after, so we don't hold references to anything but attributes
     */
    this._registerWidgetFromElement =
    function koWidgetManager__registerWidgetFromElement(aElement, aIndex, aPane) {
        let id = "__komodo_widget__" + Date.now() + "_" + Math.random();
        if (aElement.hasAttribute("id")) {
            id = aElement.getAttribute("id");
        }

        let params = { defaultPane: aPane.id };
        if (aElement.hasAttribute("icon")) {
            params.iconURL = aElement.getAttribute("icon");
        }
        if (aElement.hasAttribute("icon-inactive")) {
            params.iconURL = aElement.getAttribute("icon-inactive");
        }
        let success = this.registerWidget(id,
                                          aElement.getAttribute("label"),
                                          aElement.getAttribute("src"),
                                          params);
        if (!success) return success;
        // copy attributes over
        let data = this._get(id);
        if (!data) {
            let msg = "after successful registration, widget " + id +
                      " was not found in " + this._widgets.listkeys();
            log.exception(msg);
            throw Components.Exception(msg, Cr.NS_ERROR_UNEXPECTED);
        }
        data.forceLoad = true;
        data.attrs = {};
        data.orient = aPane.orient;
        for (let attr of Array.slice(aElement.attributes)) {
            data.attrs[attr.name] = attr.value;
        }
        data.autoload = aIndex;
        return true;
    };

    this.unregisterWidget = function koWidgetManager_unregisterWidget(aID, aCallback) {
        let id = this._getIDForWidget(aID) || String(aID);
        function callback(result) {
            try {
                if (aCallback) {
                    aCallback(result);
                }
            } catch (ex) {
                log.exception("Error invoking callback while unregistering " +
                              id);
            }
        }

        log.debug("unregisterWidget(" + id + ")");
        let data = this._get(id);
        if (!data) {
            log.debug("widget " + id + " was not registered");
            callback(true);
            return false;
        }
        let widget = data.browser;
        if (widget) {
            let success = true;
            let pane = widget.containerPane;
            if (pane) {
                success = pane.removeWidget(widget);
            }
            if (!success) {
                // the widget remove was refused
                callback(false);
                return true; // but we did find it, so return true
            }
        }

        this._widgets.del(id);
        // clear caches
        _widget_to_id_cache = new WeakMap();
        callback(true);
        return true;
    };

    /**
     * This is set up from the <ko-pane>, and is called when a <browser
     * type=ko-widget> has done loading (that is, a web progress state of
     * window|stop).
     * @params widget {<browser type=ko-widget>}
     * @note This will only fire once per widget (on the initial load)
     * @note This will not fire from widget moves, just initial creation
     */
    this._widgetLoadCallback = function koWidgetManager__widgetLoadCallback(widget, status) {
        log.debug("_widgetLoadCallback: " + this._getIDForWidget(widget) + " (" + widget + ")");
        let id = this._getIDForWidget(widget);
        if (!id) {
            return;
        }
        let data = this._get(id);
        // Make sure to remove the load callbacks as we call them; we can
        // end up with multiple load listeners if getWidget(..., true)
        // was called more than once
        while (data.loadCallbacks.length > 0) {
            try {
                data.loadCallbacks.shift()(widget);
            } catch (ex) {
                log.exception(ex);
            }
        }
    };

    this.getWidget = function koWidgetManager_getWidget(aID, aForceLoad) {
        log.debug("getWidget(" + aID + ", " + aForceLoad + "): " +
                  !!this._get(aID));
        let data = this._get(aID);
        if (!data) {
            return null;
        }
        if (data.browser) {
            log.debug("existing browser for " + aID + ": " +
                      data.browser.contentDocument.readyState + " @ " +
                      data.browser.currentURI.spec);
        }
        if (aForceLoad && (!data.browser || data.browser.currentURI.spec == "about:blank")) {
            let pane = this.getPaneAt(data.defaultPane || this.panes[0]);
            if (!pane) {
                log.debug("no pane: " + data.defaultPane + " / " + JSON.stringify(this.panes) +
                          " / " + uneval(this._panes));
            }
            if (!data.browser) {
                data.browser = pane.addWidget(aID, {focus: false});
            }
        }

        if (data.browser && ! data._loadListenerAdded) {
            data._loadListenerAdded = true;

            var loadEvent = function() {
                var event = new CustomEvent("widget-load",
                {
                    bubbles: false,
                    cancelable: false,
                    detail: data
                });
                window.dispatchEvent(event);
            }

            if (data.browser.contentDocument.readyState == "complete") {
                loadEvent();
            } else {
                data.browser.contentWindow.addEventListener("load", loadEvent);
            }
        }

        return data.browser;
    };

    this.getWidgetAsync = function koWidgetManager_getWidgetAsync(aID, aCallback) {
        Services.tm.currentThread.dispatch((function() {
            log.debug("getWidgetAsync: " + aID + (aCallback ? " (with callback)" : ""));
            let callbackArgs = null;
            try {
                let data = this._get(aID);
                if (!data) {
                    log.debug("getWidgetAsync: Widget " + aID + " is not registered");
                    return;
                }
                let browser = data.browser;
                if (browser && browser.contentDocument &&
                    (browser.contentDocument.readyState == "complete"))
                {
                    callbackArgs = browser;
                    return;
                }
                if (aCallback) {
                    log.debug("getWidgetAsync: delaying callback for " + aID);
                    data.loadCallbacks.push(aCallback);
                    aCallback = null; // don't call synchronously
                }
                if (!browser || !browser.currentURI ||
                    browser.currentURI.spec == "about:blank")
                {
                    log.debug("getWidgetAsync: forcing a load");
                    this.getWidget(aID, true); // cause a load
                }
            } catch (ex) {
                log.exception(ex);
                callbackArgs = null;
            } finally {
                if (aCallback) {
                    log.debug("getWidgetAsync: calling callback for " + aID + " now");
                    try {
                        aCallback(callbackArgs);
                    } catch (ex) {
                        log.exception(ex);
                    }
                }
            }
        }).bind(this), Ci.nsIEventTarget.DISPATCH_NORMAL);
    };

    this.modifyWidget = (function koWidgetManager_modifyWidget(aID, aParams) {
        let id = aID;
        if (id && id._is_ko_widget) {
            id = this._getIDForWidget(id);
        }
        let data = this._get(id);
        if (!data) {
            throw new Error("Widget " + aID + " is unknown");
        }
        if (!aParams) {
            throw Components.Exception("No parameters specified for modifyWidget",
                                       Cr.NS_ERROR_INVALID_ARG);
        }
        if ("defaultPane" in aParams) {
            if (this._panes.has(aParams.defaultPane)) {
                data.defaultPane = aParams.defaultPane;
            } else {
                throw Components.Exception("Pane " + aParams.defaultPane + " is unknown",
                                           Cr.NS_ERROR_INVALID_ARG);
            }
        }
        if ("URL" in aParams) {
            data.URL = aParams.URL;
        }
        let iconChanged = false;
        for (let key of ["iconURL", "inactiveIconURL"]) {
            if (key in aParams) {
                data[key] = aParams[key];
                iconChanged = true;
            }
        }
        if (iconChanged && data.browser && data.browser.containerPane) {
            data.browser.containerPane._updateTabIcon(data.browser.tab);
        }
        if ("persist" in aParams) {
            data.persist = !!aParams.persist;
        }
        if ("visible" in aParams) {
            if (aParams.visible) {
                this.getWidgetAsync(id, function(widget) {
                    widget.containerPane.addWidget(widget, {focus: true});
                });
            } else {
                // only hide it if it's loaded
                if (this.getWidget(id)) {
                    this.getWidgetAsync(id, function(widget) {
                        widget.containerPane.removeWidget(widget);
                    });
                }
            }
        }
        if ("label" in aParams) {
            data.label = aParams.label;
            if (data.browser && data.browser.tab) {
                data.browser.tab.label = aParams.label;
            }
        }
        if ("shortLabel" in aParams) {
            data.shortLabel = aParams.shortLabel;
            if (data.browser && data.browser.tab) {
                data.browser.tab.setAttribute("short-label", aParams.shortLabel);
            }
        }

        return {
            defaultPane: data.defaultPane,
            iconURL: data.iconURL,
            inactiveIconURL: data.inactiveIconURL,
            URL: data.URL,
            persist: data.persist,
            visible: !!this.getWidget(id),
            ID: id,
            label: data.label,
            shortLabel: data.shortLabel,
        }
    }).bind(this);

    this.getWidgetInfo = (function koWidgetMangager_getWidgetInfo(aID) {
        return this.modifyWidget(aID, {});
    }).bind(this);

    /**
     * Given a <browser type="ko-widget">, return its id.
     */
    this._getIDForWidget = (function koWidgetManager__getIDForWidget(aWidget) {
        if (!aWidget || !aWidget._is_ko_widget) {
            // invalid argument
            return null;
        }
        if (_widget_to_id_cache.has(aWidget)) {
            // cache hit
            let id = _widget_to_id_cache.get(aWidget);
            if (this._get(id).browser === aWidget) {
                return id;
            }
        }
        // cache miss; re-popuplate the cache
        for (let [id, data] in this._widgets.items) {
            if (data.browser) {
                _widget_to_id_cache.set(data.browser, id);
            }
        }
        // try again; note that we _should_ have references to all widgets, so
        // hopefully repeated misses won't always re-populate
        return _widget_to_id_cache.get(aWidget, null);
    }).bind(this);
    var _widget_to_id_cache = new WeakMap();

    Object.defineProperty(this, "widgets", {
        enumerable: true,
        get: function koWidgetManager_get_widgets()
            this._widgets.listkeys(),
    });

    this.getPaneAt = function koWidgetManager_getPaneAt(aPaneId)
        this._panes.get(aPaneId, null);

    // Spawn a new floating pane
    this.createPane = function koWidgetManager_createPane(aCallback, aTemplatePane) {
        // Open the container window
        let Element = null;
        let features = {
            resizable: 1,
            dependent: 1,
            chrome: 1,
            alwaysRaised: 1,
        };
        if (aTemplatePane) {
            Element = Cu.getGlobalForObject(aTemplatePane).Element;
            if (Element && (aTemplatePane instanceof Element)) {
                features.innerWidth = aTemplatePane.getBoundingClientRect().width;
                features.innerHeight = aTemplatePane.getBoundingClientRect().height;
                features.left = aTemplatePane.boxObject.screenX;
                features.top = aTemplatePane.boxObject.screenY;
            } else {
                // aTemplatePane is a generic object; this should only happen
                // as a result for restoring things on startup
                for (let prop of ["innerWidth", "innerHeight", "left", "top"]) {
                    if (prop in aTemplatePane) {
                        features[prop] = aTemplatePane[prop];
                    }
                }
            }
        }
        let initializer = (function(win) {
            ["require", "JetPack", "ko", "xtk", "gEditorTooltipHandler"].forEach(function(prop) {
                Object.defineProperty(win, prop, {
                    get: function() window[prop],
                    enumerable: true, configurable: true,
                });
            }, this);
        }).bind(this);
        let loadHandler = (function(pane) {
            if (aTemplatePane) {
                if (Element && (aTemplatePane instanceof Element)) {
                    for (let attr of Array.slice(aTemplatePane.attributes)) {
                        if (["persist", "id", "ready"].indexOf(attr.name) != -1) {
                            continue;
                        }
                        let override = ["type"].indexOf(attr.name) != -1;
                        if (override || !pane.hasAttribute(attr.name)) {
                            pane.setAttribute(attr.name, attr.value);
                        }
                    }
                } else {
                    // aTemplatePane is a generic object; this should only happen
                    // as a result for restoring things on startup
                    for (let attr of ["type", "orient"]) {
                        if (attr in aTemplatePane) {
                            pane.setAttribute(attr, aTemplatePane[attr]);
                        }
                    }
                }
            }

            // find a usable label.
            let panes = [pane for (pane in this._panes.values) if (pane.floating)];
            let labels = panes.map(function(p) p.getAttribute("label"));
            let label = this._strings.GetStringFromName("pane.floating.default.label");
            if (labels.indexOf(label) == -1) {
              pane.setAttribute("label", label);
              pane.ownerDocument.title = label;
            } else {
              for (let i = 1;; ++i) {
                label = this._strings.formatStringFromName("pane.floating.count.label",
                                                           [i], 1);
                if (labels.indexOf(label) == -1) {
                  pane.setAttribute("label", label);
                  pane.ownerDocument.title = label;
                  break;
                }
              }
            }
            pane.setAttribute("ready", "true");

            aCallback(pane);
        }).bind(this);

        openDialog("chrome://komodo/content/dialogs/widgetFloating.xul",
                   "",
                   [k + "=" + v for ([k, v] in Iterator(features))].join(","),
                   initializer,
                   loadHandler);

    };

    Object.defineProperty(this, "panes", {
        enumerable: true,
        get: function koWidgetManager_get_panes()
            this._panes.listkeys(),
    });

    /**
     * Register a pane
     * This should only be called by the <ko-pane> constructor
     */
    this._registerPane = function koWidgetManager__registerPane(aPane) {
        if (!aPane.id) {
            aPane.id = "__komodo_pane__" + Date.now() + "__" + Math.random() + "__";
        }
        log.debug("_registerPane: " + aPane.id);
        let oldPane = this._panes.get(aPane.id, null);
        if (oldPane && oldPane !== aPane) {
            throw Components.Exception("Pane " + aPane.id + " already registered",
                                       Cr.NS_ERROR_ALREADY_INITIALIZED);
        }
        this._panes.set(aPane.id, aPane);
    };

    /**
     * Unregister a pane
     */
    this._unregisterPane = function koWidgetManager__unregisterPane(aPane) {
        if (!aPane || !aPane.id) {
            return;
        }
        log.debug("_unregisterPane: " + aPane.id);
        this._panes.del(aPane.id);
    };

    /**
     * The _saved_ state of various panes; this is only used for restoring panes
     * (either on window open, or on adding a widget later), and isn't meant to
     * reflect the state of the window at runtime.
     */
    this._persist_state = {widgets: {},
                           panes: { /* id: [] */ }};
    /**
     * Called by ko.main's window.onload
     */
    this.restoreLayout = function koWidgetManager_restoreLayout(prefs, prefpath) {

        if (layoutRestored) {
            log.debug("layout already restored");
            return;
        }
        layoutRestored = true;

        prefpath = prefpath || [];
        log.debug("saving pref path: " + prefpath.join(", "));
        ko.main.addWillCloseHandler(this.unload.bind(this, prefpath));

        try {
            log.debug("onload: " + JSON.stringify(this._widgets));
        } catch (TypeError) {
            log.debug("onload: " + this._widgets.listkeys());
        }
        let panes = {}; // the state we want to end up in

        for (let paneId of this.panes) {
            panes[paneId] = {children: []};
        }

        // See what the registered widgets have to say... (These are the things
        // from XUL overlays)
        for (let [id, data] in this._widgets.items) {
            if (!("autoload" in data)) continue;
            if (!this._panes.has(data.defaultPane)) continue;
            if (!(data.defaultPane in panes)) panes[data.defaultPane] = {children: []};
            panes[data.defaultPane].children[data.autoload] = [{id: id}];
        }
        log.debug("after processing widgets: " + JSON.stringify(panes));
        // remove missing children
        for (let [id, pane] in Iterator(panes)) {
            panes[id].children = pane.children.filter(function(c) c && c.length > 0);
        }
        // Restore data from prefs
        try {
            this._persist_state = JSON.parse(prefs.getString("ui.tabs.sidepanes.state",
                                                             "(invalid json)"));
        } catch (SyntaxError) {
            // Invalid json; try to pick it up from old prefs
            for (let side of ["left", "right", "bottom"]) {
                let id = "workspace_" + side + "_area";
                let data = this._persist_state.panes[id] || {};
                let pane = this.getPaneAt(id);
                let collapsed = pane ? pane.getAttribute("collapsed") : false;
                data.collapsed = prefs.getBoolean("uilayout_" + side + "TabBox_collapsed",
                                                  (collapsed && collapsed != "false"));
                let selected = prefs.getString("uilayout_" + side + "TabBoxSelectedTabId", "");
                if (selected) {
                    data.selectedTab = selected;
                }
                if (!("children" in data)) {
                    data.children = [];
                }
                this._persist_state.panes[id] = data;
            }
            log.debug("onload: old panes = " + JSON.stringify(this._persist_state));
            for (let id of prefs.getPrefIds()) {
                log.debug("load prefs: id=" + id);
                if (!/^uilayout_widget_position_/.test(id)) {
                    continue;
                }
                let pos = prefs.getString(id);
                if (!(pos in this._persist_state.panes)) {
                    continue;
                }
                id = id.replace(/^uilayout_widget_position_/, "");
                let data = this._get(id);
                if (data) {
                    // remove this widget from all other areas
                    for (let [,d] in Iterator(this._persist_state.panes)) {
                        for (let [i, child] in Iterator(d.children)) {
                            d.children[i] = child.filter(function(u) u != id);
                        }
                    }
                    // Push it in the the pane, as a new tabpanel
                    let d = this._persist_state.panes[pos];
                    d.children.push([{id: id}]);
                }
            }
        }
        for (let [paneId,paneData] in Iterator(this._persist_state.panes)) {
            if (/^__komodo_floating_pane__\d+/.test(paneId)) {
                paneData.floating = true;
            }
            if (!("orient" in paneData)) {
                let elem = document.getElementById(paneId);
                if (elem) {
                    if ("orient" in elem) {
                        paneData.orient = elem.orient;
                    } else if (elem.hasAttribute("orient")) {
                        paneData.orient = elem.getAttribute("orient");
                    } else {
                        paneData.orient = getComputedStyle(elem).MozBoxOrient;
                    }
                }
            }
            if ("children" in paneData) {
                log.debug("before fixup: " + JSON.stringify(paneData.children));
                for (let tabData of paneData.children) {
                    for (let [idx, w_info] in Iterator(tabData)) {
                        if (typeof(w_info) == "string") {
                            tabData[idx] = {id: w_info};
                        }
                    }
                }
                log.debug("after fixup: " + JSON.stringify(paneData.children));
            }
        }
        log.debug("onload: persisted data = " + JSON.stringify(this._persist_state));
        log.debug("onload: panes = " + JSON.stringify(panes));

        let outstandingPanesToCreate = 0;
        for (let id of Object.keys(this._persist_state.panes)) {
            let data = this._persist_state.panes[id];
            let doOnePane = id => {
                if (("children" in data) && (data.children instanceof Array)) {
                    log.debug(id + ": " + JSON.stringify(panes[id].children) +
                              " -> " + JSON.stringify(data.children));
                    panes[id].children = data.children.concat();
                }
                for (let key of ["selectedTab", "collapsed"]) {
                    if (key in data) {
                        panes[id][key] = data[key];
                    }
                }
            };
            if (data.floating) {
                // FLoating pane... make it
                if (!("children" in data) || data.children.length < 1) {
                    continue; // don't restore empty floating panes
                }
                ++outstandingPanesToCreate;
                this.createPane(pane => {
                    panes[pane.id] = {children: []};
                    doOnePane(pane.id);
                    if (--outstandingPanesToCreate < 1) {
                        doRestorePanes();
                    }
                }, data);
            } else if (id in panes) {
                doOnePane(id);
            } else {
                log.debug("Ignoring unknown pane " + id + ", data " +
                          JSON.stringify(data));
            }
        }

        let doRestorePanes = (function doRestorePanes() {
            // Make sure widgets that didn't opt-in to being unloaded will still
            // load, just hidden
            log.debug("panes: " + JSON.stringify(panes));
            let extra_widgets = {};
            for (let id in this._widgets.keys) {
                extra_widgets[id] = true;
            }
            for (let [paneId,paneData] in Iterator(panes)) {
                for (let [,tab] in Iterator(paneData.children || [])) {
                    for (let [,widgetInfo] in Iterator(tab || [])) {
                        delete extra_widgets[widgetInfo.id];
                    }
                }
            }
            log.debug("extra widgets: " + Object.keys(extra_widgets));
            for (let widgetId of Object.keys(extra_widgets)) {
                let data = this._get(widgetId);
                if (!data || (!data.show && !data.forceLoad)) {
                    continue; // We don't need to force load this one
                }
                if (data.defaultPane && data.defaultPane in panes) {
                    panes[data.defaultPane].children.push([{id:widgetId}]);
                } else {
                    // Umm, can't find it anywhere.  Stuff it into any pane
                    [p for (p in Iterator(panes))].sort(function(a, b) {
                        if ("orient" in data) {
                            // sort by orient
                            if (a[1].orient != b[1].orient) {
                                return (a[1].orient === data.orient) ? -1 : 1;
                            }
                        }
                        if (a[1].floating !== b[1].floating) {
                            // prefer not-floating panes
                            return a[1].floating ? 1 : -1;
                        }
                        // Out of ideas.  By id, I guess?
                        return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0;
                    }).shift()[1].children.push([{id:widgetId}]);
                }
            }

            log.debug("onload: panes = " + JSON.stringify(panes));
            for (let id of Object.keys(panes)) {
                let pane = this._panes.get(id);
                for (let tabpanel of panes[id].children) {
                    let tab = null; // Used to put further widgets in the same tabpanel
                    for (let w_info of tabpanel) {
                        if (typeof(w_info) == "string" || (w_info instanceof String)) {
                            // name-only widget info (bug 96876)
                            w_info = {id: w_info};
                        }
                        if (!("id" in w_info)) {
                            log.warn("Found a widget with no id, ignoring");
                            continue;
                        }
                        let data = this._get(w_info.id);
                        if (!data) {
                            log.warn("Could not restore widget " + w_info.id);
                            continue;
                        } else if (data.browser) {
                            log.debug(w_info.id +
                                      " already loaded, moving it to be with " +
                                      (tab ? tab.label : "(null)"));
                            // Somebody called getWidget() synchronously too early! Try to move it
                            pane.addWidget(data.browser,
                                           {focus: false,
                                            tab: tab,
                                            width: w_info.width,
                                            height: w_info.height});
                            if (!tab) {
                                tab = data.browser.tab;
                            }
                        } else if (data.show === false) {
                            // Explicity flagged as don't restore
                            log.debug("Not restoring don't-show widget " + w_info.id);
                            continue;
                        } else {
                            let widget = pane.addWidget(w_info.id,
                                                        {focus: false,
                                                         tab: tab,
                                                         width: w_info.width,
                                                         height: w_info.height});
                            log.debug("added " + w_info.id + " -> " + this._getIDForWidget(widget));
                            tab = widget.tab;
                        }
                    }
                }
                if (panes[id].children.length > 0) {
                    /**
                     * Figure out if a widget can be selected.
                     * A widget can be selected if there is at least on widget
                     * visible in its tab.
                     * @param widget {Element} The widget to check
                     */
                    let canSelectWidget = function(widget) {
                        let widgets = Array.slice(widget.parentNode.childNodes)
                                           .filter(function(e) "_is_ko_widget" in e)
                                           .filter(function(e) !e.collapsed)
                                           .filter(function(e) !e.hidden);
                        return widgets.length > 0;
                    };
                    let children = panes[id].children
                                            .reduce(function(a,b) a.concat(b), [])
                                            .map(function (info) info.id);
                    let tabs = Array.slice(this.getPaneAt(id).tabs.children);
                    let selected = panes[id].selectedTab;
                    // make sure what we want to select actually works..
                    let alternate = null;
                    if (!selected || children.indexOf(selected) == -1 || !this._get(selected)) {
                        alternate = children[0];
                    } else if (selected) {
                        let widget = this._get(selected).browser;
                        if (widget && widget.parentNode && !canSelectWidget(widget)) {
                            let index = tabs.indexOf(widget.tab);
                            tabs = tabs.slice(index + 1)
                                       .concat(tabs.slice(0, index).reverse());
                            for (let tab of tabs) {
                                let w = tab.linkedpanel.firstChild;
                                if (canSelectWidget(w)) {
                                    alternate = this.getWidgetInfo(w).ID;
                                    break;
                                }
                            }
                        }
                    }
                    if (alternate) {
                        log.debug("Can't select " + selected + " in " + id +
                                  ", picking " + alternate + " instead");
                        selected = alternate;
                    }
                    log.debug("onload: selecting " + selected + " in " + id);
                    pane.addWidget(selected, {focus: true});
                    pane.collapsed = panes[id].collapsed;
                } else {
                    pane.collapsed = true;
                }
                // panes can now un-collapse as appropriate
                pane.setAttribute("ready", "true");
            }

            appStartupCompleted = true;
        }).bind(this);

        if (outstandingPanesToCreate < 1) {
            // no floating panes need to be created; restore everything now
            doRestorePanes();
        }
    };

    this.unload = function koWidgetManager_onunload(prefpath) {
        // Note that this doesn't use this._persist_state; that's for restoring
        // only, we want to record the state as it is now
        let panes = {};
        for (let [id, pane] in this._panes.items) {
            panes[id] = {
                collapsed: pane.collapsed,
                children: [],
            };
            if (pane.floating) {
                panes[id].left = pane.boxObject.screenX;
                panes[id].top = pane.boxObject.screenY;
                panes[id].innerWidth = pane.boxObject.width;
                panes[id].innerHeight = pane.boxObject.height;
                panes[id].type = pane.getAttribute("type");
                panes[id].orient = pane.orient;
            }
            for (let tabpanel of pane.tabpanels.childNodes) {
                let children = [];
                for (let widget of tabpanel.childNodes) {
                    if (!widget || !widget._is_ko_widget) {
                        continue;
                    }
                    let w_id = this._getIDForWidget(widget);
                    if (w_id && this._get(w_id).persist) {
                        let w_info = {id: w_id};
                        for (let prop of ["width", "height"]) {
                            if (widget.hasAttribute(prop)) {
                                let val = parseInt(widget.getAttribute(prop), 10);
                                if (!isNaN(val)) {
                                    w_info[prop] = val;
                                }
                            }
                        }
                        children.push(w_info);
                    }
                }
                if (children.length) {
                    // sanity check: tabpanels should have children...
                    panes[id].children.push(children);
                }
            }
            if (pane.widgets.length > 0 && pane.selectedPanel) {
                let selectedWidget = Array.slice(pane.selectedPanel.childNodes)
                                          .filter(function(e) "_is_ko_widget" in e)
                                          .shift();
                panes[id].selectedTab = this._getIDForWidget(selectedWidget);
            } else {
                panes[id].selectedTab = null;
            }
        }
        let data = {
            widgets: {},
            panes: panes,
        }
        let prefs = ko.prefs;
        log.debug("Getting prefs from " + prefpath.join(", "));
        for (let key of prefpath) {
            prefs = prefs.getPref(key);
        }
        log.debug("ko.widgets.unload: " + JSON.stringify(data));
        prefs.setStringPref("ui.tabs.sidepanes.state", JSON.stringify(data));
    };

    this.toString = function() {
        return "<ko.widgets implementation>";
    };

    this.updateMenu = function koWidgetManager_updateMenu(menupopup) {
        try {
            for (let child of Array.slice(menupopup.childNodes)) {
                menupopup.removeChild(child);
            }
            // The panes are ordered:
            // 1) built-ins (left, right, bottom)
            // 2) unknown (extension-provided)
            // 3) floating
            // 4) widgets not in any panes
            let builtins = [this._panes.get("workspace_left_area"),
                            this._panes.get("workspace_right_area"),
                            this._panes.get("workspace_bottom_area")];
            let unknowns = [];
            let floating = [];
            for (let pane in this._panes.values) {
                if (builtins.indexOf(pane) != -1) {
                    continue; // built-in pane
                }
                (pane.hasAttribute("floating") ? floating : unknowns).push(pane);
            }
            let compare = function(a, b)
                String.localeCompare(("label" in a) ? a.label : a.getAttribute("label"),
                                     ("label" in b) ? b.label : b.getAttribute("label"));
            let panes = Array.concat(builtins,
                                     unknowns.sort(compare),
                                     floating.sort(compare));

            let idCompare = (function(a, b)
                             String.localeCompare(this._get(a).label,
                                                  this._get(b).label)).bind(this);

            let seen = {}; // seen widgets, keyed by id
            for (let pane of panes) {
                let ids = pane.widgets
                              .map(this._getIDForWidget)
                              .filter(function(u)!!u);
                // Don't sort IDs here; we want it in DOM-order
                for (let id of ids) {
                    seen[id] = true;
                    let data = this._get(id);
                    if (data.browser && data.browser.collapsed) {
                        continue; // this widget isn't selectable
                    }
                    let menuitem = document.createElement("menuitem");
                    for (let [k,v] in Iterator({label: data.label,
                                                type: "checkbox",
                                                widget: id}))
                    {
                        menuitem.setAttribute(k, v);
                    }
                    menupopup.appendChild(menuitem);
                }
                if (menupopup.lastChild && menupopup.lastChild.localName != "menuseparator") {
                    menupopup.appendChild(document.createElement("menuseparator"));
                }
            }
            let extras = [];
            for each (let [id, data] in this._widgets.items) {
                if (id in seen) {
                    continue;
                }
                seen[id] = true;
                if (data.browser && data.browser.collapsed) {
                    continue; // don't show explicitly hidden widgets
                }
                extras.push(id);
            }
            extras = extras.sort(idCompare);
            for (let id of extras) {
                let menuitem = document.createElement("menuitem");
                for (let [k,v] in Iterator({label: this._get(id).label,
                                            type: "checkbox",
                                            widget: id}))
                {
                    menuitem.setAttribute(k, v);
                }
                menupopup.appendChild(menuitem);
            }
            if (menupopup.lastChild && menupopup.lastChild.localName == "menuseparator") {
                menupopup.removeChild(menupopup.lastChild);
            }

        } catch (e) {
            log.exception(e);
        }
    };
    this.onMenuCommand = function koWidgetManager_onMenuCommand(event) {
        let id = event.target.getAttribute("widget");
        this.modifyWidget(id, {visible: true});
    };

    XPCOMUtils.defineLazyGetter(this, "_strings", function()
        Services.strings.createBundle("chrome://komodo/locale/komodo.properties"));

}).apply(ko.widgets);
