/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

if (typeof(ko) == 'undefined')
{
    var ko = {};
}

ko.analytics = new function()
{

    const CAT_FILE_METRIC    = 'File Metrics';
    const CAT_INSTALL_METRIC = 'Install Metrics';
    const CAT_SYSTEM_METRIC  = 'System Metrics';
    const CAT_PREF_METRIC    = 'Pref Metrics';

    const DIM_PRODUCT     = 'dimension1';
    const DIM_VERSION     = 'dimension2';
    const DIM_BUILD       = 'dimension3';
    const DIM_BUILDTYPE   = 'dimension4';
    const DIM_LICENSETYPE = 'dimension5';
    const DIM_EXPIRATION  = 'dimension6';

    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;

    const { logging }       = Cu.import("chrome://komodo/content/library/logging.js", {});
    const { DownloadUtils } = Cu.import("resource://gre/modules/DownloadUtils.jsm", {});
    
    var prefs   = Cc['@activestate.com/koPrefService;1'].getService(Ci.koIPrefService).prefs;

    var log = logging.getLogger('analytics');

    var sectionRegex = /^[a-z]*\:\//i;

    /**
     * Constructor
     */
    this.init = () =>
    {
        //this.debug();

        // Retrieve unique user id
        var firstRun = false;
        var uid = prefs.getString('analytics_ga_uid', '');
        if (uid == '')
        {
            var uuidGenerator = Cc["@mozilla.org/uuid-generator;1"]
                                .getService(Ci.nsIUUIDGenerator);
            uid = new String(uuidGenerator.generateUUID());
            uid = uid.substr(1).substr(0,uid.length-2);
            prefs.setStringPref('analytics_ga_uid', uid);
            firstRun = true;
        }

        if ( ! prefs.getBoolean('analytics_enabled', false))
        {
            if (firstRun)
            {
                var bundle = Cc["@mozilla.org/intl/stringbundle;1"]
                            .getService(Ci.nsIStringBundleService)
                            .createBundle("chrome://analytics/locale/analytics.properties");
                            
                var nb = document.getElementById("komodo-notificationbox");
                var nf = nb.appendNotification(bundle.GetStringFromName("analytics.optin.ask.message"),
                                      "optin-analytics", null, nb.PRIORITY_INFO_HIGH,
                [
                    {
                        accessKey: bundle.GetStringFromName("analytics.optin.confirm.accessKey"),
                        callback: () =>
                        {
                            prefs.setBooleanPref('analytics_enabled', true);
                            nb.removeNotification(nf);
                            this.init();

                            var nf = nb.appendNotification(bundle.GetStringFromName("analytics.optin.thanks.message"),
                                                  "optin-analytics", null, nb.PRIORITY_INFO_LOW);
                            setTimeout(nb.removeNotification.bind(nb,nf), 5000);
                        },
                        label: bundle.GetStringFromName("analytics.optin.confirm.label")
                    },
                    {
                        accessKey: bundle.GetStringFromName("analytics.optin.deny.accessKey"),
                        callback: nb.removeNotification.bind(nb, nf),
                        label: bundle.GetStringFromName("analytics.optin.deny.label")
                    },
                ]);
            }
            
            return;
        }

        // Init Ganalytics
        var proxy_window = document.getElementById('analyticsProxy').contentWindow;
        proxy_window.ga_initialize();

        this._proxyGa('create', prefs.getStringPref('analytics_ga_id'), {
          'cookieDomain': 'activestate.com', // gotta use something
          'clientId': uid
        });
        this._proxyGa('set', 'checkProtocolTask', function(){});
        this._proxyGa('set', 'checkStorageTask', function(){});
        
        // Set custom dimensions
        var infoSvc = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
        this.setProperty(DIM_PRODUCT,       infoSvc.productType);
        this.setProperty(DIM_VERSION,       infoSvc.version);
        this.setProperty(DIM_BUILD,         infoSvc.buildNumber);
        this.setProperty(DIM_BUILDTYPE,     infoSvc.buildType);
        this.setProperty(DIM_LICENSETYPE,   infoSvc.licenseType);
        this.setProperty(DIM_EXPIRATION,    infoSvc.daysUntilExpiration);

        // Track installs / upgrades
        var lastVersion = prefs.getString('analyticsLastVersion', '');
        if (lastVersion != infoSvc.version)
        {
            prefs.setStringPref('analyticsLastVersion', infoSvc.version);
            if (lastVersion == '')
            {
                this.trackEvent(CAT_INSTALL_METRIC, "Fresh Install", infoSvc.version);
            }
            else
            {
                this.trackEvent(CAT_INSTALL_METRIC, "Update", infoSvc.version);
            }

            this.trackEvent(CAT_INSTALL_METRIC, "Install", "from " + lastVersion + " to " + infoSvc.version);
        }

        // Track system info, don't want to waste dimensions on this
        if (firstRun)
        {
            var sysInfo = Cc["@mozilla.org/system-info;1"].getService(Ci.nsIPropertyBag2);
            var memSize = Math.round(sysInfo.getPropertyAsInt64("memsize") / 1073741824, 2);
            var cpucount = sysInfo.getPropertyAsInt32("cpucount");
            this.trackEvent(CAT_SYSTEM_METRIC, "memory", memSize, memSize);
            this.trackEvent(CAT_SYSTEM_METRIC, "arch", sysInfo.getPropertyAsAString("arch"));
            this.trackEvent(CAT_SYSTEM_METRIC, "cpucount", cpucount, cpucount);
        }

        this.bindListeners();
    };

    /**
     * Debug helper, when called this starts listening for debug messages from ganalytics
     * Helps tracking ganalytics debug info, but also allows users to track
     * what data is being send
     */
    this.debug = () =>
    {
        log.setLevel(10);
        var proxy = document.getElementById('analyticsProxy').contentWindow;
        var debug = proxy.document.getElementById('debug');
        if (debug.textContent.length) log.debug(debug.textContent);
        debug.textContent = '';

        setTimeout(this.debug, 500);
    };

    /**
     * Event listeners 
     */
    this.bindListeners = () =>
    {
        window.addEventListener('view_opened', this._eventProxy.bind(this, this.onViewOpened));
        window.addEventListener('focus', this._eventProxy.bind(this, this.onWindowFocus));
        //window.addEventListener('loadDialog', e => e.detail["dialog"]
        //                                            .addEventListener('focus',_proxy.bind(this, this.onWindowFocus)) );

        var ww = Cc["@mozilla.org/embedcomp/window-watcher;1"].getService(Ci.nsIWindowWatcher);
        ww.registerNotification(this.onWindowOpened);

        var _prefs = prefs.getPref('analytics_track_prefs');
        for (let x=0;x<_prefs.length;x++)
        {
            prefs.prefObserverService.addObserver(this.onPrefChanged, _prefs.getString(x), false);
        }
    };

    ///**
    // * Listen to changes on deck elems for pageviews
    // *
    // * @param {Window} _window
    // */
    //this.bindDeckListeners = (_window) =>
    //{
    //    if (_window._hasDeckListeners) return;
    //    _window._hasDeckListeners = true;
    //
    //    // Get deck id's that we want to track
    //    if ( ! ("_trackDecks" in this))
    //    {
    //        this._trackDecks = [];
    //        var _decks = prefs.getPref('analytics_track_decks');
    //        for (let x=0;x<_decks.length;x++)
    //        {
    //            this._trackDecks.push(_prefs.getString(x));
    //        }
    //    }
    //
    //    // Iterate over all decks in the window and track "select" event on those
    //    // that we opted in to track
    //    var elem = _window.document.getElementsByTagName("deck");
    //    for (let [,elem] in Iterator(elems))
    //    {
    //        if (this._trackDecks.indexOf(elem.getAttribute("id")) == -1) continue;
    //        ((_elem) => {
    //            _elem.addEventListener("select", (e) => {
    //                if (e.target!=e.originalTarget) return;
    //                this.trackPageView(section + "#deck-" + _elem.getAttribute("id") + "-" + _elem.selectedIndex)
    //            });
    //        })(elem);
    //    }
    //};

    /**
     * Triggered when a pref has been changed, holds the observe key used by
     * the prefobserver
     */
    this.onPrefChanged = { observe: (subject, topic, data) => {
        switch (topic) {

            // Iconset / Skin prefs
            case 'koSkin_custom_skin':
            case 'koSkin_custom_icons':
                var val = ko.prefs.getStringPref(topic);
                if (val.indexOf("chrome:") !== 0) return;
                this.trackEvent(CAT_PREF_METRIC, data + "_" + topic, val);
                break;

            // Scheme prefs
            case 'keybinding-scheme':
            case 'editor-scheme':
                if (topic == 'editor-scheme')
                {
                    var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
                    var schemes = [], defaults = [];
                    schemeService.getSchemeNames(schemes, new Object());
                    for (var i = 0; i < schemes.value.length; i++) {
                        let name = schemes.value[i];
                        let scheme = schemeService.getScheme(name);
                        if (scheme && ! scheme.writeable) {
                            defaults.push(name);
                        }
                    }
                }
                else
                {
                    // These are unlikely to change (often), so just hardcode it
                    var defaults = ["Default", "Emacs", "Vi", "Windows"];
                }

                var val = ko.prefs.getStringPref(topic);
                if (defaults.indexOf(val) == -1)
                {
                    // Don't track values of custom schemes
                    this.trackEvent(CAT_PREF_METRIC, data + "_" + topic, "Custom");
                }
                else
                {
                    this.trackEvent(CAT_PREF_METRIC, data + "_" + topic, val);
                }
                break;

            // Track the string value for these prefs
            case 'ui.tabs.sidepanes.left.layout':
            case 'ui.tabs.sidepanes.right.layout':
            case 'ui.tabs.sidepanes.bottom.layout':
                var val = ko.prefs.getStringPref(topic);
                this.trackEvent(CAT_PREF_METRIC, data + "_" + topic, val);
                break;

            // Track boolean state, int value or otherwise just track that the pref was set
            default:
                if (prefs.getPrefType(topic) == 'boolean')
                {
                    var val = ko.prefs.getBooleanPref(topic);
                    this.trackEvent(CAT_PREF_METRIC, data + "_" + topic, val, val ? 1 : 0);
                }
                else if (prefs.getPrefType(topic) == 'long')
                {
                    var val = ko.prefs.getLongPref(topic);
                    this.trackEvent(CAT_PREF_METRIC, data + "_" + topic, val, val);
                }
                else
                {
                    this.trackEvent(CAT_PREF_METRIC, data + "_" + topic);
                }
                break;
        }
    }};

    /**
     * Triggered when a view (editor) has been opened
     */
    this.onViewOpened = (e) =>
    {
        var view = ko.views.manager.currentView;
        this.trackPageView("/editor/" + view.koDoc.language);
        if ("koDoc" in view && "file" in view.koDoc && view.koDoc.file && "scimoz" in view)
        {
            this.trackEvent(CAT_FILE_METRIC, "Opened");
            this.trackEvent(CAT_FILE_METRIC, "Language", view.koDoc.language);

            // Track filesize, but standarize it a bit so we can group similar
            // filesizes together
            var size = DownloadUtils.convertByteUnits(view.scimoz.textLength);
            var bins = [10,50,100,200,300,400,500,600,700,800,900];
            var binIndex = this._getNumberBin(size[0], bins);

            this.trackEvent(CAT_FILE_METRIC, "Size",
                            (binIndex > 0 ? bins[binIndex-1] : 0) + "-" + bins[binIndex] + " " + size[1]);

            if (view.koDoc.file.isLocal)
            {
                this.trackEvent(CAT_FILE_METRIC, "Location", "Local");
            }
            else
            {
                this.trackEvent(CAT_FILE_METRIC, "Location", "Remote");
            }
        }
    };

    this.onWindowOpened = { observe: (_window, topic) => //aSubject, aTopic, aData
    {
        var docElem = _window.document.documentElement;
        var windowId = docElem.getAttribute("id");
        var section = _window.location.href.replace(sectionRegex, '');

        if (windowId == "commonDialog")
            return;

        if (windowId == "prefWindow")
        {
            this.trackPageView(section);
        }

        if (docElem.nodeType == 'wizard')
        {
            var onWizardPageStep = () => this.trackPageView(section + "#wizard-step-" + docElem.pagestep);
            var onWizardFinish = () => this.trackPageView(section + "#wizard-finish");
            var onWizardCancel = () => this.trackPageView(section + "#wizard-cancel");
            
            docElem.addEventListener("wizardnext", onWizardPageStep);
            docElem.addEventListener("wizardback", onWizardPageStep)
            docElem.addEventListener("wizardfinish", onWizardPageStep)
            docElem.addEventListener("wizardcancel", onWizardPageStep)
        }

        _window.addEventListener('focus', this._eventProxy.bind(this, this.onWindowFocus));
    }};

    /**
     * Track "page" views on window focus
     */
    this.onWindowFocus = (e) =>
    {
        var _window = e.view;
        var windowId = _window.document.documentElement.getAttribute("id");
        var section = _window.location.href.replace(sectionRegex, '');
        // Document title may disclose personal information (file / project name)
        // Disabled this entirely for now as the document title isn't that relevant
        //var title = ("document" in _window) ? window.document.title : null;

        if (_window.document.documentElement.nodeType == 'wizard')
        {
            section += "#wizard-step-" + _window.document.documentElement.pagestep;
        }

        if (windowId == "prefWindow")
        {
            var panelFrame = _window.document.getElementById('panelFrame');
            var frame = panelFrame.children[panelFrame.selectedIndex];
            var section = frame.getAttribute("src").replace(sectionRegex, '');
        }

        this.trackPageView(section);
    };

    var _lastPageView = null;
    /**
     * Track page view by location and title
     *
     * @param {String} section
     * @param {String} title
     */
    this.trackPageView = (section, title) =>
    {
        if (_lastPageView == section) return;
        _lastPageView = section;
        
        log.debug("Tracking pageview. Section: " + section);

        var args = {
            hitType: 'pageview',
            page: section,
            location: section
        };

        if (title) args.title = title;

        this._proxySend(args);
    };

    /**
     * Track a custom event
     *
     * @param {String} category     Typically the object that was interacted with (e.g. file)
     * @param {String} action       The type of interaction (e.g. opened)
     * @param {String} label        Useful for categorizing events (e.g. python)
     * @param {Integer} value       Values must be non-negative. Useful to pass counts (e.g. filename length)
     */
    this.trackEvent = (category, action, label, value) =>
    {
        log.debug("Tracking event.\n\nCategory: " + category +
                  ",\nAction: " + action + "\nLabel: " + label +
                  ",\nValue: " + value + "\n");

        var args = {
            hitType: 'event',
            eventCategory: category,
            eventAction: action
        };

        if (label) args.eventLabel = new String(label);
        if (value) args.eventValue = parseInt(value);

        this._proxySend(args);
    };

    /**
     * Set a user/session property
     *
     * @param {String|Object} properties
     * @param {String} value
     */
    this.setProperty = (properties, value) =>
    {
        if (value)
        {
            var _properties = {};
            _properties[properties] = new String(value);
            properties = _properties;
        }

        this._proxySet(properties);
    };

    /**
     * Send a "send" event over the GA proxy
     */
    this._proxySend = (...args) =>
    {
        args = Array.prototype.slice.call(args); // convert to array
        args.unshift("send");
        this._proxyGa.apply(this, args);
    }

    /**
     * Send a "set" event over the GA proxy
     */
    this._proxySet = (...args) =>
    {
        args = Array.prototype.slice.call(args); // convert to array
        args.unshift("set");
        this._proxyGa.apply(this, args);
    }

    /**
     * Send data over the GA proxy
     */
    this._proxyGa = (...args) =>
    {
        var proxy = document.getElementById('analyticsProxy').contentWindow;
        proxy.ga.apply(proxy, args);
        //proxy.contentWindow.postMessage(JSON.stringify(args), "*");
    }

    /**
     * Group "amount" under relevant "bin"
     *
     * @param {Integer} amount
     * @param {Array} bins      Must be sorted ASC, eg. [1024, 10240, 102400]
     *
     * @returns index of matching bin
     */
    this._getNumberBin = (amount, bins) =>
    {
        for (let [x,bin] in Iterator(bins))
        {
            if (amount < bin) return x;
        }
        return bins.length-1;
    }

    this._eventProxy = (cb, ...args) =>
    {
        try {
            cb.apply(this, args);
        } catch (e) {
            log.exception(e);
        }
    };

};

// Start after the workspace_restored even is fired, as we don't want to track any
// events triggered by the restore
window.addEventListener("workspace_restored", ko.analytics.init.bind(ko.analytics));
