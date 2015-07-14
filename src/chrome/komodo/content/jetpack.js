/* Copyright (c) 2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * Jetpack loader
 *
 * This is used to load the commonjs-style modules.
 */

const [JetPack, require] = (function() {
    var ko = this.ko || {};
    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    const { Services } = Cu.import("resource://gre/modules/Services.jsm", {});
    const { main, Loader, resolve, resolveURI } =
        Cu.import('resource://gre/modules/commonjs/toolkit/loader.js', {}).Loader;

    /* Populate requirePaths with category entries */
    const catMan = Cc["@mozilla.org/categorymanager;1"]
                        .getService(Ci.nsICategoryManager);
    var requirePaths = {};
    var setRequirePaths = function() {
        
        // Attempt to get the main komodo window to inherit require paths from it
        var _window = window;
        var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
        let windows = wm.getEnumerator("Komodo");
        while (windows.hasMoreElements()) {
            let __window = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
            if ("require" in __window && __window.require) {
                _window = __window;
            }
        }
        
        if ("require" in _window && _window.require) {
            // Inherit requirePaths
            requirePaths = _window.require.getRequirePaths();
        } else {
            // Set requirePaths manually
            
            // Komodo API fallback...
            requirePaths["ko/"] = "chrome://komodo/content/sdk/";
            // Komodo API fallback...
            requirePaths["contrib/"] = "chrome://komodo/content/contrib/commonjs/";
            // Default path
            requirePaths[''] = 'resource://gre/modules/commonjs/';
            
            Components.utils.import("resource://gre/modules/osfile.jsm")
            var tmpPath = Cc["@mozilla.org/file/directory_service;1"]
             .getService(Ci.nsIProperties).get("TmpD", Ci.nsIFile).path;
            requirePaths['tmp'] = OS.Path.toFileURI(tmpPath);
            
            var entries = catMan.enumerateCategory('require-path');
            while (entries.hasMoreElements()) {
                let entry = entries.getNext().QueryInterface(Ci.nsISupportsCString);
                let uri = catMan.getCategoryEntry('require-path', entry);
                // Stringafy entry - in order to get the nice JS string functions.
                entry = entry.toString();
                if (entry && !entry.endsWith("/")) {
                    // Needs a trailing slash in order to map correctly.
                    entry += "/";
                }
                requirePaths[entry] = uri;
            }
        }
    }
    setRequirePaths();
    /* Reload require paths on addon install */
    Components.utils.import("resource://gre/modules/AddonManager.jsm");
    AddonManager.addInstallListener({onInstallEnded: setRequirePaths});
    // TODO: May need to reset "loader.modules" when the add-on is loaded?

    var globals = { ko: ko };
    if (String(this).contains("Window")) {
        // Have a window scope available
        globals.window = window;
        globals.document = document;
        globals.setTimeout = window.setTimeout;
        globals.clearTimeout = window.clearTimeout;
        if ("console" in window) {
            // Add the console when available too - some of the SDK depends on
            // this being defined.
            globals.console = console;
        }
    } else if (String(this).contains("BackstagePass")) {
        // Being loaded via Components.utils.import
        this.EXPORTED_SYMBOLS = ["require", "JetPack"];
    }

    // Note that "paths" is required; _something_ needs to name the modules
    var loader = Loader({paths: requirePaths,
                         globals: globals});

    const JetPack = {
        // Keep handle to the JetPack ko namespace... as some tests require
        // access to tweak this namespace.
        ko: ko,

        defineLazyProperty: (object, property, id) => {
            const JetPack_LazyProperty = () => {
                delete object[property];
                return object[property] = require.call(this, id);
            }
            Object.defineProperty(object, property, {
                get: JetPack_LazyProperty,
                configurable: true,
                enumerable: true
            });
        },
        defineDeprecatedProperty: (object, property, id, options={}) => {
            let objName = (object === ko) ? "ko" : String(object);
            let deprecatedMessage = objName + "." + property +
                ' has been converted to a CommonJS module;' +
                ' use require("' + id + '") instead.';
            if ("since" in options) {
                deprecatedMessage = deprecatedMessage.replace(/\.$/, "") +
                                    " (since Komodo " + options.since + ").";
            }
            const JetPack_DeprecatedProperty = () => {
                if (id !== "ko/logging") {
                    let logging = require("ko/logging");
                    if (logging) {
                        logging.getLogger("")
                               .deprecated(deprecatedMessage, false, 2);
                    }
                }
                delete object[property];
                let result = object[property] = require.call(this, id);
                if (id === "ko/logging" && result) {
                    result.getLogger("").deprecated(deprecatedMessage, false, 2);
                }
                return result;
            }
            Object.defineProperty(object, property, {
                get: JetPack_DeprecatedProperty,
                configurable: true,
                enumerable: true
            });
        }
    };

    const require = function(id) {
        if (id.indexOf("/") == -1) {
            // Automatically resolve module namespaces
            id = id + "/" + id;
        }
            
        try {
            let uri = resolveURI(id, loader.mapping)
            if (uri in loader.modules) {
                // Module already loaded; don't load it again
                return loader.modules[uri].exports;
            }
            // Load the module for the first time
            return main(loader, id);
        } catch (ex) {
            Cu.reportError('While trying to require("' + id + '"):');
            Cu.reportError(ex);

            if (typeof(ex) == 'object' && 'stack' in ex && ex.stack)
                Cu.reportError(ex.stack);
                
            throw ex;
        }
        return null;
    };

    /**
     * Adds the namespace and path to the loader's list of require paths.
     * 
     * @param {String} namespace  The prefix for the required path.
     * @param {String} path       The directory to which this prefix is mapped.
     */
    require.setRequirePath = function(namespace, path) {
        if (namespace in requirePaths) return;
        requirePaths[namespace] = path;
        
        // Modify the loader mapping (a mapping of the paths) in place.
        //
        // We know the last item in the mapping is '' - so we cannot
        // leave this loop with finding a place to insert.
        var mapping_length = loader.mapping.length
        for (var i=0; i < mapping_length; i++) {
            if (loader.mapping[i][0].length <= namespace.length) {
                loader.mapping.splice(i, 0, [namespace, path]);
                break
            }
        }
        if (loader.mapping.length <= mapping_length) {
            throw new Error("setRequirePath didn't succeed in adding a mapping");
        }
    }
    
    require.getRequirePaths = function() {
        return requirePaths;
    }

    /**
     * Removes the namespace from the loader's list of require paths.
     * 
     * @param {String} namespace  The prefix for the required path.
     */
    require.removeRequirePath = function(namespace) {
        // The load.mapping will store the entries with a trailing slash.
        if (!namespace.endsWith("/")) {
            namespace += "/";
        }
        for (var i=0; i < loader.mapping.length; i++) {
            if (loader.mapping[i][0] == namespace) {
                loader.mapping.splice(i, 1);
                break
            }
        }
    }

    return [JetPack, require];
})();
