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
            PREF_USE_CUSTOM_SCROLLBARS = 'koSkin_use_custom_scrollbars';
    
    // Old preference value reference
    var prefOld = {};
    prefOld[PREF_CUSTOM_ICONS]      = prefs.getString(PREF_CUSTOM_ICONS, '');
    prefOld[PREF_CUSTOM_SKIN]       = prefs.getString(PREF_CUSTOM_SKIN, '');
    prefOld[PREF_USE_GTK_DETECT]    = prefs.getBoolean(PREF_USE_GTK_DETECT, true);
    
    ko.skin.prototype  =
    {
        PREF_CUSTOM_ICONS:      PREF_CUSTOM_ICONS,
        PREF_CUSTOM_SKIN:       PREF_CUSTOM_SKIN,
        PREF_USE_GTK_DETECT:    PREF_USE_GTK_DETECT,
        
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
            for (let pref in prefOld)
            {
                prefs.prefObserverService.addObserver(this, pref, false);
            }

            // Check whether we need to load a custom skin manually
            if (this.gtk.init(this) && prefs.getBoolean(PREF_USE_GTK_DETECT, true))
            {
                this.gtk.loadDetectedTheme();
            }

            this._setupCustomScrollbars();
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
            if ([PREF_CUSTOM_ICONS,PREF_CUSTOM_SKIN].indexOf(topic)!=-1)
            {
                // Skip if the value hasn't changed
                let value = prefs.getString(topic, '');
                if (value == prefOld[topic])
                {
                    return;
                }

                log.debug("Pref changed: " + topic + ", old value: " + prefOld[topic] + ", new value: " + value);

                // Unload the previous skin
                try {
                    if (prefOld[topic] != '')
                    {
                        this.unloadCustomSkin(prefOld[topic]);
                    }
                } catch (e) {}

                // Store new value for future updates
                prefOld[topic] = value;

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
                    this.loadPreferredIcons();
                }
            }
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
                    Services.scriptloader.loadSubScript(initUri.spec, {koSkin: this});
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

            this._setupCustomScrollbars();

            koLess.reload();

            var nb = document.getElementById("komodo-notificationbox");
            var nf = nb.appendNotification("Some of the changes made may require a Komodo restart to apply properly",
                                  "skin-restart", null, nb.PRIORITY_INFO_HIGH,
            [
                {
                    accessKey: "r",
                    callback: ko.utils.restart,
                    label: "Restart Komodo"
                },
                {
                    accessKey: "l",
                    callback: nb.removeNotification.bind(nb, nf),
                    label: "Restart Later"
                },
            ]);
        },

        /**
         * Apply the custom scrollbar preferences
         */
        _setupCustomScrollbars: function()
        {
            var skinName = prefs.getString(PREF_CUSTOM_SKIN, "");
            try
            {
                Cc["@mozilla.org/categorymanager;1"]
                  .getService(Ci.nsICategoryManager)
                  .getCategoryEntry("komodo-skins-use-custom-scrollbars",
                                    skinName);
                prefs.setBooleanPref(PREF_USE_CUSTOM_SCROLLBARS, true);
                log.debug("Using custom scrollbars for " + skinName);
            }
            catch (ex)
            {
                // no category entry
                prefs.setBooleanPref(PREF_USE_CUSTOM_SCROLLBARS, false);
                log.debug("Not using custom scrollbars for " + skinName);
            }
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

                while (entries.hasMoreElements())
                {
                    var entry = entries.getNext().QueryInterface(Ci.nsISupportsCString);
                    if (entry == themeInfo.name.toLowerCase())
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
            
        }
        
    };
    
    ko.skin = new ko.skin();
    
}).apply();
