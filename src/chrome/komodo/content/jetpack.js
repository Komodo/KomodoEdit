/* Copyright (c) 2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * Jetpack loader
 *
 * This is used to load the commonjs-style modules.
 */

const [JetPack, require, requirePaths] = (function() {
    let ko = this.ko || {};
    let loader;
    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    const { Services } = Cu.import("resource://gre/modules/Services.jsm", {});
    const { main, Loader, resolve, resolveURI, Module } =
        Cu.import('resource://gre/modules/commonjs/toolkit/loader.js', {}).Loader;

    const catMan = Cc["@mozilla.org/categorymanager;1"]
                        .getService(Ci.nsICategoryManager);

    /* Populate requirePaths with category entries */
    let requirePaths = {};
    let setRequirePaths = function()
    {
        let entries = catMan.enumerateCategory('require-path');
        while (entries.hasMoreElements())
        {
            let entry = entries.getNext().QueryInterface(Ci.nsISupportsCString);
            let uri = catMan.getCategoryEntry('require-path', entry);
            requirePaths[entry] = uri;
        }
    }
    setRequirePaths();

    /* Reload require paths on addon install */
    Components.utils.import("resource://gre/modules/AddonManager.jsm");
    AddonManager.addInstallListener({onInstallEnded: setRequirePaths});

    /* Resolve id from within a module context */
    let localResolve = function (id, requirer) {
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

    /* Resolve id from a global context */
    let globalResolve = function(id, mapping) {
        let ids = id.split("/");
        for (let i=ids.length-1;i>0;i--) {
            let _id = ids.slice(0,i).join('/');
            if (_id in requirePaths)
                return requirePaths[_id] + ids.slice(i).join('/') + ".js";
        }

        return false;
    }

    let globals = { ko: ko };
    if (String(this).contains("Window")) {
        // Have a window scope available
        globals.window = window;
        globals.document = document;
    } else if (String(this).contains("BackstagePass")) {
        // Being loaded via Components.utils.import
        this.EXPORTED_SYMBOLS = ["require", "JetPack"];
    }
    // Note that "paths" is required; _something_ needs to name the modules
    const paths = {
        // Resolving things to ko.* via the custom resolver...
        "x-komodo-internal://": "x-komodo-internal://",
        // Komodo API fallback...
        "ko/": "chrome://komodo/content/library/",
        // Default path
        '': 'resource://gre/modules/commonjs/',
    }
    loader = Loader({resolve: localResolve,
                     paths: paths,
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
            let resolved = globalResolve(id);
            let uri = resolved || resolveURI(id, loader.mapping)
            if (uri in loader.modules) {
                // Module already loaded; don't load it again
                return loader.modules[uri].exports;
            }

            /* Attempt to resolve using requirePaths */
            if (resolved) {
                let module;
                module = loader.modules[uri] = Module(id, uri);
                loader.load(loader, module);
                return freeze(module.exports);
            }
        } catch (ex) {
            Cu.reportError('Exception while trying to resolve ' + id + ', \
                            falling back on Mozilla\'s commonjs');
            Cu.reportError(ex);
        }

        try {
            // Load the module for the first time
            return main(loader, id);
        } catch (ex) {
            Cu.reportError('Exception while trying to require("' + id + '"):');
            Cu.reportError(ex);
            throw ex;
        }
        return null;
    };

    /* Helpers */

    // Copied from commonjs/lib/toolkit/loader.js as we can't access it directly
    function freeze(object) {
        let prototypeOf = Object.getPrototypeOf;
        if (prototypeOf(object) === null) {
            Object.freeze(object);
        }
        else {
            prototypeOf(prototypeOf(object.isPrototypeOf)).
                constructor. // `Object` from the owner compartment.
                freeze(object);
        }
        return object;
    }

    return [JetPack, require, requirePaths];
})();
