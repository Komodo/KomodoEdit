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

var _lessClearCache = undefined;

(function() {

    const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
    const {NetUtil}     = Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const {Services}    = Cu.import("resource://gre/modules/Services.jsm", {});
    const {ctypes}      = Cu.import("resource://gre/modules/ctypes.jsm", {});

    // Make prefs accessible across "class"
    var prefs = Components.classes['@activestate.com/koPrefService;1']
                    .getService(Components.interfaces.koIPrefService).prefs;
                    
    var log = ko.logging.getLogger('koSkin');
    
    // Preference constants
    const   PREF_CUSTOM_ICONS     = 'koSkin_custom_icons',
            PREF_CUSTOM_SKIN      = 'koSkin_custom_skin',
            PREF_USE_GTK_DETECT   = 'koSkin_use_gtk_detection';
    
    // Old preference value reference
    var prefOld = {};
    prefOld[PREF_CUSTOM_ICONS]      = prefs.getString(PREF_CUSTOM_ICONS, '');
    prefOld[PREF_CUSTOM_SKIN]       = prefs.getString(PREF_CUSTOM_SKIN, '');
    prefOld[PREF_USE_GTK_DETECT]    = prefs.getBoolean(PREF_USE_GTK_DETECT, true);
    
    // Self pointer for use in observer, as .bind() doesn't work with xpcom
    var self;
    
    // Helper vars
    var _clearCacheTimer = null;
    
    ko.skin.prototype  =
    {
        PREF_CUSTOM_ICONS:      PREF_CUSTOM_ICONS,
        PREF_CUSTOM_SKIN:       PREF_CUSTOM_SKIN,
        PREF_USE_GTK_DETECT:    PREF_USE_GTK_DETECT,
        
        skinHasChanged: false,
        iconsetHasChanged: false,
        
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
            self = this;
            
            for (let pref in prefOld)
            {
                prefs.prefObserverService.addObserver(this, pref, false);
            }

            // Check whether we need to load a custom skin manually
            if (this.gtk.init(this) && prefs.getBoolean(PREF_USE_GTK_DETECT, true))
            {
                this.gtk.loadDetectedTheme();
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
            if ([PREF_CUSTOM_ICONS,PREF_CUSTOM_SKIN].indexOf(topic)!=-1)
            {
                // Skip if the value hasn't changed
                let value = prefs.getString(topic, '');
                if (value == prefOld[topic])
                {
                    return;
                }

                // Unload the previous skin
                try {
                    if (prefOld[topic] != '')
                    {
                        self.unloadCustomSkin(prefOld[topic]);
                    }
                } catch (e) {}

                // Store new value for future updates
                prefOld[topic] = value;

                setTimeout(function() {
                // Reload relevant skin
                if (topic == PREF_CUSTOM_SKIN)
                {
                    self.skinHasChanged = true;
                    self.loadPreferredSkin();
                }
                else if (topic == PREF_CUSTOM_ICONS)
                {
                    self.iconsetHasChanged = true;
                    self.loadPreferredIcons();
                }
                }, 50);
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
            if (preferredSkin == '')
            {
                return;
            }

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

            if (uri == '')
            {
                if (window.navigator.platform.toLowerCase().indexOf("mac") === 0)
                {
                    var uri = "resource://app/chrome/iconsets/cupertino/chrome.manifest";
                }
                else
                {
                    var uri = "resource://app/chrome/iconsets/dark/chrome.manifest";
                }
                
                prefs.setStringPref(PREF_CUSTOM_ICONS, uri);
            }

            this.loadCustomSkin(uri);
        },
        
        /**
         * Load a custom skin
         * 
         * @param   {String} uri
         * 
         * @returns {Void}
         */
        loadCustomSkin: function(uri)
        {
            log.debug("Loading custom skin: " + uri);

            var manifestLoader = Cc["@activestate.com/koManifestLoader;1"]
                                    .getService(Ci.koIManifestLoader);
            if ( ! manifestLoader.loadManifest(uri, true))
            {
                log.error("Failed loading manifest: '" + uri);
                return;
            }
            
            if (this.skinHasChanged)
            {
                this.clearCache();
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
            
            this.clearCache();
        },
        
        /**
         * Clear skin caches
         *
         * We'll need to reload any css files that have been affected
         *
         * @param   {Boolean} noDelay   Whether to execute immediately or after
         *                              a short delay, used to prevent multiple
         *                              reloads in a short time
         * 
         * @returns {Void} 
         */
        clearCache: function(noDelay = false)
        {
            // Prevent multiple calls in a short time
            if ( ! noDelay)
            {
                clearTimeout(_clearCacheTimer);
                _clearCacheTimer = setTimeout(this.clearCache.bind(this, true), 50);
                return;
            }
            
            try
            {
                // Flush image caches first to ensure that if we end up
                // switching skins, we get the new images
                let observers = Services.obs.enumerateObservers("chrome-flush-caches");
                while (observers.hasMoreElements())
                {
                    let observer = observers.getNext();
                    if (observer instanceof Ci.imgICache)
                    {
                        observer.clearCache(true /*chrome*/);
                    }
                }

                Services.obs.notifyObservers(null, "chrome-flush-caches", null);
                
                // Clear less cache
                if ("less" in ko && "initialized" in ko.less)
                {
                    var clearLessCache = function()
                    {
                        if ( ! ko.less.initialized)
                        {
                            // Need to account for the use-case where the
                            // initialization may still be in progress
                            setTimeout(clearLessCache, 50);
                            return;
                        }
                        
                        ko.less.reload(true);
                    }
                    clearLessCache();
                    
                    return;
                }
            }
            catch (e) {
                log.error(e.message);
            }
            
            _lessClearCache = true;
        },

        _getFile: function(uri)
        {
            try
            {

                var match = uri.match(/([a-z]{2,})\:/);

                switch (match ? match[1] : '')
                {
                    case 'resource':
                        var file = Services.io.newURI(uri, null,null)
                                    .QueryInterface(Ci.nsIFileURL).file;
                        break;

                    case 'file':
                        var file = NetUtil.newURI(uri)
                                    .QueryInterface(Ci.nsIFileURL)
                                    .file;
                        break;

                    default:
                        var file = Cc["@mozilla.org/file/local;1"]
                                    .createInstance(Components.interfaces.nsILocalFile);
                        file.initWithPath(uri);
                        break;
                }

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
                    return false;
                }
                
                this.getThemeInfo(this._loadTheme.bind(this), function() 
                {
                    // Retrieving theme failed
                    prefs.setStringPref(PREF_CUSTOM_SKIN,'');
                    prefs.setStringPref(PREF_CUSTOM_ICONS,'');
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
                    prefs.setStringPref(PREF_CUSTOM_SKIN,'');
                    prefs.setStringPref(PREF_CUSTOM_ICONS,'');
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
                Components.utils.import("resource://gre/modules/Services.jsm");

                var uri = "resource://app/chrome/skins/gtk-"+themeInfo.name+"/chrome.manifest";
                var file = Services.io.newURI(uri, null,null)
                            .QueryInterface(Components.interfaces.nsIFileURL).file;

                if ( ! file.exists())
                {
                    return false;
                }

                return uri;
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
                        gtk = ctypes.open("libgtk-x11-2.0.so");
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
                            log.debug("Got theme: " + this._themeInfo.name);
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
                var callbackPos = 0;
                
                // Callback handler for commands
                var self = this;
                var callbackHandler =
                {
                    "callback": function(command, returncode, stdout, stderr)
                    {
                        callbackPos++;
                        
                        // Check if we have a valid result 
                        if (stdout && !stderr) 
                        {
                            var themeInfo = {
                                name: stdout.replace(/^(?:'|"|\s)*|(?:'|"|\s)*$/gm,'')
                            }
                            
                            // Split from callback thread so as not to log redundant
                            // exceptions, should they occur
                            setTimeout(function() {
                                callbackSuccess.call(this, themeInfo);
                            }, 0);
                        }
                        // If invalid result and we reached the end of our command list
                        else if (callbackPos == commands.length)
                        {
                            callbackFailed.call(this);
                        }
                        else
                        {
                            koRunSvc.RunAsync(commands[callbackPos], callbackHandler);
                        }
                    }.bind(self)
                };
                
                koRunSvc.RunAsync(commands[0], callbackHandler);
                
            }
            
        }
        
    };
    
    ko.skin = new ko.skin();
    
}).apply();
