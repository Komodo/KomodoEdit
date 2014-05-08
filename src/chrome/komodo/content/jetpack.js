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
    let requirePaths = {};
    let setRequirePaths = function() {
        // Resolving things to ko.* via the custom resolver...
        requirePaths["x-komodo-internal://"] = "x-komodo-internal://";
        // Komodo API fallback...
        requirePaths["ko/"] = "chrome://komodo/content/library/";
        // Default path
        requirePaths[''] = 'resource://gre/modules/commonjs/';

        let entries = catMan.enumerateCategory('require-path');
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
    setRequirePaths();
    /* Reload require paths on addon install */
    Components.utils.import("resource://gre/modules/AddonManager.jsm");
    AddonManager.addInstallListener({onInstallEnded: setRequirePaths});
    // TODO: May need to reset "loader.modules" when the add-on is loaded?

    var loader;
    let my_resolve = function (id, requirer) {
        if (id.startsWith("ko/") && !(id in loader.modules)) {
            // Try to grab it off the global |ko| object...
            let parts = id.split("/").slice(1);
            let obj = ko;
            while (obj && parts.length > 0) {
                obj = obj[parts.shift()];
            }
            if (obj) {
                // Got it off a global; map it to a fake URI
                let url = "x-komodo-internal://" + id;
                let resolvedURI = resolveURI(url, loader.mapping);
                if (!(resolvedURI in loader.modules)) {
                    // Module hasn't been loaded yet, give a reference to it
                    loader.modules[resolvedURI] =
                        {exports: Cu.getGlobalForObject(obj).Object.freeze(obj)};
                }
                return url;
            }
        }
        // Can't resolve it to a global, try the normal path
        return resolve(id, requirer);
    };

    var globals = { ko: ko };
    if (String(this).contains("Window")) {
        // Have a window scope available
        globals.window = window;
        globals.document = document;
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
    loader = Loader({resolve: my_resolve,
                     paths: requirePaths,
                     globals: globals});

    const JetPack = {
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
            throw ex;
        }
        return null;
    };

    return [JetPack, require];
})();
