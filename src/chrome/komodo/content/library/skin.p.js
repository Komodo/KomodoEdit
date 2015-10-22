/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */
 
/* Komodo Skinning
 *
 * Defines the "ko.skin" namespace.
 */
if (typeof(ko) == 'undefined')
{
    var ko = {};
}

if (ko.skin == undefined)
{
    ko.skin = function()
    {
        this.init();
    };
}

(function() {

    const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
    const {NetUtil}     = Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const {Services}    = Cu.import("resource://gre/modules/Services.jsm", {});
    const {ctypes}      = Cu.import("resource://gre/modules/ctypes.jsm", {});
    const {koLess}      = Cu.import("chrome://komodo/content/library/less.js", {});

    // Make prefs accessible across "class"
    var prefs = Components.classes['@activestate.com/koPrefService;1']
                    .getService(Components.interfaces.koIPrefService).prefs;
                    
    var log = ko.logging.getLogger('koSkin');
    //log.setLevel(ko.logging.LOG_DEBUG);
    
    // Preference constants
    const   PREF_CUSTOM_ICONS     = 'koSkin_custom_icons',
            PREF_CUSTOM_SKIN      = 'koSkin_custom_skin',
            PREF_USE_GTK_DETECT   = 'koSkin_use_gtk_detection',
            PREF_EDITOR_SCHEME    = 'editor-scheme',
            PREF_SCHEME_SKINNING  = 'koSkin_scheme_skinning',
            PREF_SCHEME_FORCE_DARK  = 'scheme-force-is-dark';
    
    // Old preference value reference
    var prefInfo = {};
    prefInfo[PREF_CUSTOM_ICONS]      = {type: "String", old: prefs.getString(PREF_CUSTOM_ICONS, '')};
    prefInfo[PREF_CUSTOM_SKIN]       = {type: "String", old: prefs.getString(PREF_CUSTOM_SKIN, '')};
    prefInfo[PREF_USE_GTK_DETECT]    = {type: "Boolean", old: prefs.getBoolean(PREF_USE_GTK_DETECT, true)};
    prefInfo[PREF_EDITOR_SCHEME]     = {type: "String", old: prefs.getString(PREF_EDITOR_SCHEME, '')};
    prefInfo[PREF_SCHEME_SKINNING]   = {type: "Boolean", old: prefs.getBoolean(PREF_SCHEME_SKINNING, '')};
    prefInfo[PREF_SCHEME_FORCE_DARK] = {type: "String", old: prefs.getString(PREF_SCHEME_FORCE_DARK, '-1')};
    
    ko.skin.prototype  =
    {
        PREF_CUSTOM_ICONS:      PREF_CUSTOM_ICONS,
        PREF_CUSTOM_SKIN:       PREF_CUSTOM_SKIN,
        PREF_USE_GTK_DETECT:    PREF_USE_GTK_DETECT,
        PREF_EDITOR_SCHEME:     PREF_EDITOR_SCHEME,
        PREF_SCHEME_SKINNING:   PREF_SCHEME_SKINNING,
        PREF_SCHEME_FORCE_DARK: PREF_SCHEME_FORCE_DARK,
        
        shouldFlushCaches: false,
        
        /**
         * Constructor
         *
         * Offloads the loading of a custom skin to gtk if available,
         * otherwise calls it manually using the skin preference
         * 
         * @returns {Void} 
         */
        init: function()
        {
            for (let pref in prefInfo)
            {
                prefs.prefObserverService.addObserver(this, pref, false);
            }

            // Check whether we need to load a custom skin manually
            if (this.gtk.init(this) && prefs.getBoolean(PREF_USE_GTK_DETECT, true))
            {
                this.gtk.loadDetectedTheme();
            }

            this.loadSchemeSkinning();
            this.setSchemeClasses();
            
            // Force skin reload if Komodo has been updated
            var skinVersion = prefs.getString('skinVersion', '');
            var infoSvc = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
            var platVersion = infoSvc.buildPlatform + infoSvc.buildNumber;
            var forceReload = prefs.getBoolean('forceSkinReload', false);
            if (skinVersion != platVersion || forceReload)
            {
                log.info("Komodo has been updated, forcing a skin reload");
                prefs.setStringPref('skinVersion', platVersion);
                this.shouldFlushCaches = true;
                [PREF_CUSTOM_SKIN, PREF_CUSTOM_ICONS].forEach(function(keyName)
                {
                    if (prefs.getString(keyName, '') == '') return;
                    var value = prefs.getStringPref(keyName);
                    
                    // Set pref to default without triggering a reload
                    prefInfo[keyName] = {type: "String", old: prefs.parent.getString(keyName, '')};
                    prefs.setString(keyName, prefs.parent.getString(keyName, ''));
                    
                    // Set pref and trigger reload
                    prefs.setString(keyName, value);
                });
                
                // And in case that didn't do it ..
                koLess.reload(true);
                setTimeout(function()
                {
                    koLess.reload();
                }, 100);
                prefs.deletePref('forceSkinReload');
            }
            
            // Check if this user used to be an Abyss user, and notify them accordingly
            if (prefs.getBoolean("removedAbyss", false))
            {
                var elem;
                var installAbyss = function()
                {
                    nb.removeNotification(elem);
                    
                    var p = require("scope-packages/packages");
                    p._getAvailablePackagesByKind(p.SKINS, function(pkgs)
                    {
                        var abyss;
                        for (let pkg in pkgs)
                        {
                            if (pkg == "Abyss") abyss = pkgs[pkg];
                        }
                        
                        if ( ! abyss)
                        {
                            var msg = "Unable to find the Abyss skin, " +
                                "possibly the Komodo website is under maintenance, " +
                                "please try again later."
                            require("ko/dialogs").alert(msg);
                            return;
                        }
                        
                        p._installPackage(abyss);
                    });
                    prefs.deletePref("removedAbyss");
                };
                
                var nb = document.getElementById("komodo-notificationbox");
                var msg = "The Abyss skin is no longer packaged with Komodo, " +
                          "would you like to have Komodo download and install it?";
                elem = nb.appendNotification(msg,
                                      "abyss-install", null, nb.PRIORITY_INFO_HIGH,
                [
                    {
                        accessKey: "y",
                        callback: installAbyss,
                        label: "Yes (Install Abyss Skin)"
                    },
                    {
                        accessKey: "n",
                        callback: function()
                        {
                            prefs.deletePref("removedAbyss");
                            nb.removeNotification(elem);
                        },
                        label: "No Thanks"
                    },
                ]);
            }
        },
        
        /**
         * Preference Observer
         * 
         * @param   {Object} subject 
         * @param   {String} topic
         * @param   {String} data    
         * 
         * @returns {Void} 
         */
        observe: function(subject, topic, data)
        {
            // Skip if the value hasn't changed
            let value = prefs["get"+prefInfo[topic].type](topic);
            if (value == prefInfo[topic].old)
            {
                return;
            }

            log.debug("Pref changed: " + topic + ", old value: " + prefInfo[topic].old + ", new value: " + value);

            switch (topic)
            {
                case PREF_CUSTOM_ICONS:
                case PREF_CUSTOM_SKIN:
                    // Unload the previous skin
                    try {
                        if (prefInfo[topic].old != '')
                        {
                            this.unloadCustomSkin(prefInfo[topic].old);
                        }
                    } catch (e) {}

                    // Queue a cache flush; both skins and iconsets might change the
                    // CSS generated (e.g. for icon URLs)
                    this.shouldFlushCaches = true;

                    // Reload relevant skin
                    if (topic == PREF_CUSTOM_SKIN)
                    {
                        this.loadPreferredSkin();
                    }
                    else if (topic == PREF_CUSTOM_ICONS)
                    {
                        var values = ["iconset-base-color", "iconset-toolbar-color",
                                     "iconset-widgets-color", "iconset-selected-color",
                                     "iconset-base-defs", "iconset-toolbar-defs",
                                     "iconset-widgets-defs", "iconset-selected-defs"];
                        values.forEach(function(pref)
                        {
                            // Set value as -1, as deletePref only resets it to the
                            // global default, it does not actually delete the pref
                            prefs.setString(pref, '-1');
                        });
                        this.loadPreferredIcons();
                    }
                    break;

                case PREF_EDITOR_SCHEME:
                case PREF_SCHEME_SKINNING:
                    this.loadSchemeSkinning();
                    this.setSchemeClasses();
                    break;
                case PREF_SCHEME_FORCE_DARK:
                    this.loadSchemeSkinning();
                    this.setSchemeClasses();
                    break;
            }

            // Store new value for future updates
            prefInfo[topic].old = value;
        },
        
        /**
         * Load the skin the user has stored as his preference (if any)
         * 
         * @returns {Void} 
         */
        loadPreferredSkin: function(pref)
        {
            var preferredSkin = prefs.getString(PREF_CUSTOM_SKIN, '');
            this.loadCustomSkin(preferredSkin);
        },
        
        /**
         * Load the skin the user has stored as his preference (if any)
         * 
         * @returns {Void} 
         */
        loadPreferredIcons: function()
        {
            var uri = prefs.getString(PREF_CUSTOM_ICONS,'');
            this.loadCustomSkin(uri);
        },
        
        _loadCustomSkinTimer: null,
        _loadCustomSkinQueue: [],
        
        /**
         * Load a custom skin
         * 
         * @param   {String} uri
         * 
         * @returns {Void}
         */
        loadCustomSkin: function(uri)
        {
            if (this.shouldFlushCaches)
            {
                log.debug("Queueing up load of custom skin: " + uri);
                
                clearTimeout(this._loadCustomSkinTimer)
                this._loadCustomSkinQueue.push(uri);
                this._loadCustomSkinTimer = setTimeout(this._loadCustomSkins.bind(this), 50);
            }
            else
            {
                this._loadCustomSkin(uri);
            }
        },
        
        _loadCustomSkin: function(uri)
        {
            if (uri == "") {
                return;
            }
            
            log.debug("Loading custom skin: " + uri);
            
            var manifestLoader = Cc["@activestate.com/koManifestLoader;1"]
                                    .getService(Ci.koIManifestLoader);
            if ( ! manifestLoader.loadManifest(uri, true))
            {
                log.error("Failed loading manifest: '" + uri);
                return;
            }
            
            var file = this._getFile(uri);
            var initFile = file.parent;
            initFile.appendRelativePath('init.js');
            if (initFile.exists())
            {
                try
                {
                    let initUri = Services.io.newFileURI(initFile);
                    Services.scriptloader.loadSubScript(initUri.spec, {koSkin: this, ko: ko});
                }
                catch (e)
                {
                    log.error("Failed loading skin init: '" + initFile.path + "'. " + e.message);
                }
            }
        },
        
        _loadCustomSkins: function()
        {
            log.debug("Loading " + this._loadCustomSkinQueue.length + " custom skins");
            
            koLess.cache.clear();

            var uri;
            while ((uri = this._loadCustomSkinQueue.pop()) !== undefined)
            {
                log.debug("Processing " + uri);
                this._loadCustomSkin(uri);
            }

            koLess.reload();
            setTimeout(function()
            {
                koLess.reload();
            }, 100);

            var nb = document.getElementById("komodo-notificationbox");
            if (("_koSkinElem" in nb) && nb._koSkinElem) nb.removeNotification(nb._koSkinElem);
            nb._koSkinElem = nb.appendNotification("Some of the changes made may require a Komodo restart to apply properly",
                                  "skin-restart", null, nb.PRIORITY_INFO_HIGH,
            [
                {
                    accessKey: "r",
                    callback: ko.utils.restart,
                    label: "Restart Komodo"
                },
                {
                    accessKey: "l",
                    callback: function() { nb.removeNotification(nb._koSkinElem); },
                    label: "Restart Later"
                },
            ]);
        },

        /**
         * Unload a custom skin
         * 
         * @param   {String} uri
         * 
         * @returns {Void} 
         */
        unloadCustomSkin: function(uri)
        {
            log.debug("Unloading custom skin: " + uri);

            var manifestLoader = Cc["@activestate.com/koManifestLoader;1"]
                                    .getService(Ci.koIManifestLoader);
            if ( ! manifestLoader.unloadManifest(uri, true))
            {
                log.error("Failed unloading manifest: '" + uri);
                return;
            }
        },
        
        setSchemeClasses:function()
        {
            var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
            var scheme = schemeService.getScheme(prefs.getString(PREF_EDITOR_SCHEME));
            document.documentElement.classList.remove("hud-isdark");
            document.documentElement.classList.remove("hud-islight");
            
            var darkScheme = prefs.getString('scheme-force-is-dark', '-1');
            if (darkScheme == '-1')
                darkScheme = scheme.isDarkBackground ? "1" : "0";
            
            document.documentElement.classList.add(darkScheme == "1" ? "hud-isdark" : "hud-islight");
        },

        loadSchemeSkinning: function()
        {
            this.unloadVirtualStyle("scheme-skinning-partial");
            
            document.documentElement.classList.add("hud-skinning");
            if ( ! prefs.getBoolean(PREF_SCHEME_SKINNING))
            {
                document.documentElement.classList.remove("hud-skinning");
                return;
            }
            
            var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
            var scheme = schemeService.getScheme(prefs.getString(PREF_EDITOR_SCHEME));
            var darkScheme = prefs.getString('scheme-force-is-dark', '-1');
            if (darkScheme == '-1')
            {
                darkScheme = scheme.isDarkBackground ? "1" : "0";
            }
            
            var back = scheme.backgroundColor,
                fore = scheme.foregroundColor;

            // Skip if the value hasn't changed
            var lessCode = "" +
                "@dark: " + darkScheme + ";\n" +
                "@special: " + scheme.getCommon("keywords", "fore") + ";\n" +
                "@background: " + back + ";\n" +
                "@foreground: " + fore + ";\n" +
                "@import url('chrome://komodo/skin/partials/scheme-skinning.less');";
            this.loadVirtualStyle(lessCode, "scheme-skinning-partial", "agent");
        },

        _getFile: function(uri)
        {
            try
            {

                var koResolve = Cc["@activestate.com/koResolve;1"]
                                        .getService(Ci.koIResolve);

                var filePath = koResolve.uriToPath(uri);
                if ( ! filePath)
                {
                    return false;
                }

                // Create nsIFile with path
                var file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
                file.initWithPath(filePath);

                return file;

            }
            catch(e)
            {
                log.error("Error retrieving file: " + uri + ": " + e.message);
                return false;
            }
        },
        
        /**
         * GTK specific functionality
         */
        gtk: {
            
            enabled: false,
            koSkin: null,
            _themeInfo: null,
            catMan: null,
            
            /**
             * Constructor
             * 
             * @param   {Object} koSkin     Pointer to parent instance
             * 
             * @returns {Boolean}           returns false if gtk is not used
             */
            init: function(koSkin)
            {
                var koInfoService = Components.classes["@activestate.com/koInfoService;1"].
                        getService(Components.interfaces.koIInfoService);
                if (window.navigator.platform.toLowerCase().indexOf("linux") == -1)
                {
                    return false;
                }
                
                this.enabled = true;
                this.koSkin = koSkin;

                this.catMan = Cc["@mozilla.org/categorymanager;1"]
                                .getService(Ci.nsICategoryManager);
                
                return true;
            },
            
            /**
             * Detect and load a theme relevant to the current gtk theme
             * 
             * @returns {Boolean}   False if no relevant theme exists
             */
            loadDetectedTheme: function()
            {
                // Don't load if detection is disabled in user preferences
                if ( ! prefs.getBoolean(PREF_USE_GTK_DETECT, true))
                {
                    return;
                }
                
                this.getThemeInfo(this._loadTheme.bind(this), function() 
                {
                    // Retrieving theme failed
                    prefs.deletePref(PREF_CUSTOM_SKIN);
                    prefs.deletePref(PREF_CUSTOM_ICONS);
                }.bind(this));
            },
            
            /**
             * Load theme using theme info provided
             * 
             * @param   {Object} themeInfo Theme information object (contains name key)
             * 
             * @returns {Void} 
             */
            _loadTheme: function(themeInfo)
            {
                if (themeInfo.name == prefs.getString(PREF_CUSTOM_SKIN, ''))
                {
                    return;
                }
                
                var uri = this.resolveSkin(themeInfo);
                if ( ! uri)
                {
                    prefs.deletePref(PREF_CUSTOM_SKIN,'');
                    prefs.deletePref(PREF_CUSTOM_ICONS,'');
                    return;
                }
                
                if (prefs.getString(PREF_CUSTOM_SKIN, '') != uri)
                {
                    prefs.setStringPref(PREF_CUSTOM_SKIN, uri);
                }
            },
            
            /**
             * Use the provided theme info to resolve to a relevant komodo skin
             *
             * @param   {Object} themeInfo Theme information object (contains name key)
             *
             * @returns {Boolean|String}
             */
            resolveSkin: function(themeInfo)
            {
                var entries = this.catMan.enumerateCategory('ko-gtk-compat');
                Components.utils.import("resource://gre/modules/Services.jsm");

                var themeName = themeInfo.name.toLowerCase().replace(/\s+/g, '-');
                while (entries.hasMoreElements())
                {
                    var entry = entries.getNext().QueryInterface(Ci.nsISupportsCString);
                    if (entry == themeName)
                    {
                        var uri = this.catMan.getCategoryEntry('ko-gtk-compat', entry);
                        return uri;
                    }
                }

                return false;
            },

            /**
             * Retrieve gtk theme information
             * 
             * @returns {Object}    Returns object containing theme info
             *                      currently only contains the theme name
             */
            getThemeInfo: function(callbackSuccess, callbackFailed)
            {
                if (this._themeInfo != null)
                {
                    callbackSuccess.call(this,this._themeInfo);
                    return;
                }

                // Try to get the theme name through gtk
                {
                    let gtk = null, g_free = null;
                    let name_pointer = ctypes.void_t.ptr();
                    try
                    {
                        gtk = ctypes.open("libgtk-x11-2.0.so.0");
                        let gtk_settings_get_default =
                            gtk.declare("gtk_settings_get_default",
                                        ctypes.default_abi,
                                        ctypes.void_t.ptr);
                        let g_object_get =
                            gtk.declare("g_object_get",
                                        ctypes.default_abi,
                                        ctypes.void_t,
                                        ctypes.void_t.ptr,
                                        ctypes.char.ptr,
                                        ctypes.void_t.ptr,
                                        ctypes.void_t.ptr);
                        g_free =
                            gtk.declare("g_free",
                                        ctypes.default_abi,
                                        ctypes.void_t,
                                        ctypes.void_t.ptr);

                        let settings = gtk_settings_get_default();
                        g_object_get(settings,
                                     "gtk-theme-name",
                                     name_pointer.address(),
                                     null);
                        if ( ! name_pointer.isNull())
                        {
                            this._themeInfo =
                            {
                                name: ctypes.cast(name_pointer, ctypes.char.ptr)
                                            .readString(),
                            }
                            log.warn("Detected GTK theme via libgtk: " + this._themeInfo.name);
                            callbackSuccess.call(this, this._themeInfo);
                            return;
                        }
                    }
                    catch (ex)
                    {
                        log.exception("Failed to get gtk theme name, " +
                                        "falling back to shell",
                                      ex);
                    }
                    finally
                    {
                        if (g_free && ! name_pointer.isNull())
                        {
                            g_free(name_pointer);
                        }
                        if (gtk)
                        {
                            gtk.close();
                        }
                    }
                }
                
                // Possible commands to retrieve gtk theme name
                var commands = [
                    'dconf read /org/gnome/desktop/interface/gtk-theme',
                    'gsettings get org.gnome.desktop.interface gtk-theme',
                    'gconftool-2 -g /desktop/gnome/interface/gtk_theme'
                ];
                
                // Prepare vars used by callbacks
                var koRunSvc = Components.classes["@activestate.com/koRunService;1"]
                                .getService(Components.interfaces.koIRunService);
                
                // Callback handler for commands
                var self = this;
                var themeInfo = null;

                var _callbackSuccess = function(themeInfo)
                {
                    // Split from callback so as not to log redundant
                    // exceptions, should they occur
                    setTimeout(function() {
                        callbackSuccess.call(self, themeInfo);
                    }, 0);
                };

                var callbackHandler =
                {
                    "callback": function(command, returncode, stdout, stderr)
                    {
                        // Check if we have a valid result 
                        if (stdout && !stderr)
                        {
                            themeInfo = {
                                name: stdout.replace(/^(?:'|"|\s)*|(?:'|"|\s)*$/gm,'')
                            }
                            
                            log.warn("Detected GTK theme via commands: " + themeInfo.name);

                            // Adwaita is the gnome default so we need to ensure
                            // that we're not just running with the default
                            if (themeInfo.name != 'Adwaita')
                            {
                                _callbackSuccess(themeInfo);
                                return;
                            }
                        }

                        // If invalid result and we reached the end of our command list
                        if ( ! commands.length)
                        {
                            if (themeInfo)
                            {
                                _callbackSuccess(themeInfo);
                            }
                            else
                            {
                                callbackFailed.call(this);
                            }
                        }
                        else
                        {
                            koRunSvc.RunAsync(commands.shift(), callbackHandler);
                        }
                    }.bind(self)
                };
                
                koRunSvc.RunAsync(commands.shift(), callbackHandler);
            }
            
        },

        unloadVirtualStyle: function(id)
        {
            if ( ! id) throw "You must provide a unique id for your style";
            if ( ! (id in this._virtualStyles)) return;

            var style = this._virtualStyles[id];
            var styleUtil = require("sdk/stylesheet/utils");

            var unloadFromWindow = function(_window)
            {
                try
                {
                    styleUtil.removeSheet(_window, style.href, style.type);
                } catch (e) {} // no need for an exception if its already removed
            }

            var windows = Services.wm.getEnumerator(null);
            while (windows.hasMoreElements())
            {
                let xulWindow = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
                unloadFromWindow(xulWindow);
            }

            var widgets = ko.widgets._widgets.listitems()
            for (let widget in widgets)
            {
                let [id, data] = widgets[widget];
                unloadFromWindow(data.browser.contentWindow);
            }

            delete this._virtualStyles[id];
        },

        _virtualStyles: {},
        loadVirtualStyle: function(lessCode, id, type = "author")
        {
            this.unloadVirtualStyle(id);

            log.debug("Loading virtual style: " + lessCode);

            koLess.parse(lessCode, function(cssCode)
            {
                var path = require('sdk/system').pathFor('ProfD');
                var ioFile = require('sdk/io/file');
                path = ioFile.join(path, "userstyleCache", id + ".css");

                if ( ! ioFile.exists(ioFile.dirname(path)))
                    ioFile.mkpath(ioFile.dirname(path));

                var file = ioFile.open(path, "w");
                file.write(cssCode);
                file.close();

                this._virtualStyles[id] = {href: ko.uriparse.pathToURI(path), type: type};

                this._loadVirtualStyle(id);
                this._virtualStyleListener();
            }.bind(this));
        },

        _virtualStyleListener: function()
        {
            if (this._virtualStyleListener.initialized) return;

            this._virtualStyleListener.initialized = true;

            Services.wm.addListener({
                onOpenWindow: function (aWindow)
                {
                    let domWindow = aWindow.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIDOMWindow);
                    domWindow.addEventListener("load", function ()
                    {
                        domWindow.removeEventListener("load", arguments.callee, false);
                        for (let id in this._virtualStyles)
                            this._loadVirtualStyle(id, domWindow);
                    }.bind(this), false);
                }.bind(this),
                onCloseWindow: function (aWindow) {},
                onWindowTitleChange: function (aWindow, aTitle) {}
            });

            window.addEventListener("widget-load", function(e)
            {
                for (let id in this._virtualStyles)
                    this._loadVirtualStyle(id, e.detail.browser.contentWindow);
            }.bind(this));
            
            window.addEventListener("pref-frame-load", function(e)
            {
                for (let id in this._virtualStyles)
                    this._loadVirtualStyle(id, e.detail);
            }.bind(this));
        },

        _loadVirtualStyle: function(id, _window = null)
        {
            if (_window)
                log.debug("Loading virtual style " + id + " into " + (_window.name || _window.id || "unknown window"));

            var style = this._virtualStyles[id];
            var styleUtil = require("sdk/stylesheet/utils");

            var loadIntoWindow = function(xulWindow)
            {
                styleUtil.loadSheet(xulWindow, style.href, style.type);
            }

            if (_window)
                return loadIntoWindow(_window);

            var windows = Services.wm.getEnumerator(null);
            while (windows.hasMoreElements())
            {
                let xulWindow = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
                loadIntoWindow(xulWindow);
            }

            var widgets = ko.widgets._widgets.listitems()
            for (let widget in widgets)
            {
                let [id, data] = widgets[widget];
                loadIntoWindow(data.browser.contentWindow);
            }
        }
        
    };
    
    window.addEventListener("komodo-ui-started", function()
    {
        ko.skin = new ko.skin();
    });
    
}).apply();
