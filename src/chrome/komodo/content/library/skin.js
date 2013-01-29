// Copyright (c) 2000-2013 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.
 
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
    
    // Make prefs accessible across "class"
    var prefs = Components.classes['@activestate.com/koPrefService;1']
                    .getService(Components.interfaces.koIPrefService).prefs;
                    
    var log = ko.logging.getLogger('koSkin');
    
    // Preference constants
    const PREF_CUSTOM_SKIN      = 'koSkin_custom_skin',
          PREF_USE_GTK_DETECT   = 'koSkin_use_gtk_detection';
          
    ko.skin.prototype  =
    {
        
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
            this.loadPreferredSkin();
            
            // Check whether we need to load a custom skin manually
            if (this.gtk.init(this) && prefs.getBoolean(PREF_USE_GTK_DETECT, true))
            {
                this.gtk.loadDetectedTheme();
            }
        },
        
        /**
         * Load the skin the user has stored as his preference (if any)
         * 
         * @returns {Void} 
         */
        loadPreferredSkin: function()
        {
            var preferredSkin = prefs.getString(PREF_CUSTOM_SKIN, '');
            
            if (preferredSkin == '')
            {
                return;
            }
            
            try
            {
                var file = Components.classes["@mozilla.org/file/local;1"]
                            .createInstance(Components.interfaces.nsILocalFile);
                file.initWithPath(preferredSkin);
            }
            catch(e)
            {
               	ko.logging.getLogger('koSkin').error(e.name + ": " + e.message);
            }
            
            this.loadCustomSkin(file, true);
        },
        
        /**
         * Load a custom skin
         * 
         * @param   {nsIFile} file       File pointer of chrome.manifest
         * 
         * @returns {Void}
         */
        loadCustomSkin: function(file, internal = false)
        {
            if ( ! file instanceof Components.interfaces.nsIFile)
            {
                throw new Error("First attribute should be instance of nsILocalFile");
            }
            
            if ( ! file.exists())
            {
                throw new Error("Custom skin file does not exist: " + file.path);
            }
            
            if (file.leafName != 'chrome.manifest')
            {
                throw new Error("Filename should be 'chrome.manifest'");
            }
            
            try
            {
                Components.manager.addBootstrappedManifestLocation(file.parent);
            }
            catch (e)
            {
               log.error("Failed loading manifest: '" + file.path + "'. " + e.message);
            }
            
            
            // If this is not an internal call, save the new theme
            // as the preferred theme and disable automatic theme detection
            if ( ! internal)
            {
                prefs.setBooleanPref(PREF_USE_GTK_DETECT, false);
                prefs.setStringPref(PREF_CUSTOM_SKIN, file.path);
            }
        },
        
        /**
         * Clear less cache
         *
         * We'll need to reload any css files that have been affected
         * 
         * @returns {Void} 
         */
        clearCache: function()
        {
            if (typeof less != 'undefined')
            {
                less.clearFileCache();
                less.refresh();
                return;
            }
            
            if (typeof window.less == 'undefined')
            {
                window.less = {};
            }
            window.less._clearFileCache = true;
        },
        
        /**
         * GTK specific functionality
         */
        gtk: {
            
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
                this.koSkin = koSkin;
                
                var koInfoService = Components.classes["@activestate.com/koInfoService;1"].
                        getService(Components.interfaces.koIInfoService);
                if (window.navigator.platform.toLowerCase().indexOf("linux") == -1)
                {
                    return false;
                }
                
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
                    if (prefs.getString(PREF_CUSTOM_SKIN, '') != '')
                    {
                        this.koSkin.clearCache();
                        prefs.setStringPref(PREF_CUSTOM_SKIN,'');
                    }
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
                
                Components.utils.import("resource://gre/modules/Services.jsm");
                
                try
                {
                    var file = Services.io.newURI("resource://app/chrome/skin/gnome/"+themeInfo.name+"/chrome.manifest", null,null)
                                .QueryInterface(Components.interfaces.nsIFileURL).file;
                    
                    if ( ! file.exists())
                    {
                        throw new Error;
                    }
                }
                catch(e)
                {
                    if (typeof file == 'undefined' || prefs.getString(PREF_CUSTOM_SKIN, '') == file.path)
                    {
                        this.koSkin.clearCache();
                        prefs.setStringPref(PREF_CUSTOM_SKIN,'');
                        return;
                    }
                }
                
                if (prefs.getString(PREF_CUSTOM_SKIN, '') != file.path)
                {
                    this.koSkin.loadCustomSkin(file, true);
                    this.koSkin.clearCache();
                    prefs.setStringPref(PREF_CUSTOM_SKIN, file.path);
                }
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
                
                // Possible commands to retrieve gtk theme name
                var commands = [
                    'dconf read /org/gnome/desktop/interface/gtk-theme',
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
            
        },
        
    };
    
    ko.skin = new ko.skin();
    
}).apply();