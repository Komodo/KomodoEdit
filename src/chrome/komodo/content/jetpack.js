/* Copyright (c) 2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/**
 * Jetpack loader
 *
 * This is used to load the commonjs-style modules.
 */

(function() {
    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    const {Services} = Cu.import("resource://gre/modules/Services.jsm");
    const { main, Loader, resolve, resolveURI } =
        Cu.import('resource://gre/modules/commonjs/toolkit/loader.js', {}).Loader;

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


    const globals = {
        ko: ko,
        window: window,
        document: document,
    };
    // Note that "paths" is required; _something_ needs to name the modules
    const paths = {
        // Resolving things to ko.* via the custom resolver...
        "x-komodo-internal://": "x-komodo-internal://",
        // Komodo API fallback...
        "ko/": "chrome://komodo/content/library/",
        // Default path
        '': 'resource://gre/modules/',
    }
    loader = Loader({resolve: my_resolve,
                     paths: paths,
                     globals: globals});

    const global = Cu.getGlobalForObject({});
    Object.defineProperty(global, "JetPack", {value: {
        defineLazyProperty: (object, property, id) => {
            function JetPack_LazyProperty() {
                delete object[property];
                return object[property] = require(id);
            }
            Object.defineProperty(object, property, {
                get: JetPack_LazyProperty,
                configurable: true,
                enumerable: true
            });
        },
        defineDeprecatedProperty: (object, property, id) => {
            function JetPack_DeprecatedProperty() {
                if ("logging" in ko) {
                    let objName = String(object);
                    if (object === ko) {
                        // Common case is ko.foo -> require("ko/foo")
                        objName = "ko";
                    }
                    ko.logging.getLogger("")
                      .deprecated(objName + "." + property +
                                  ' has been converted to a CommonJS module;' +
                                  ' use require("' + id + '") instead.');
                }
                delete object[property];
                return object[property] = require(id);
            }
            Object.defineProperty(object, property, {
                get: JetPack_DeprecatedProperty,
                configurable: true,
                enumerable: true
            });
        }
    }, enumerable: true});

    Object.defineProperty(global, "require", {value:
        function(id) {
            try {
                let uri = resolveURI(id, loader.mapping)
                if (uri in loader.modules) {
                    // Module already loaded; don't load it again
                    return loader.modules[uri].exports;
                }
                // Load the module for the first time
                return main(loader, id);
            } catch (ex) {
                Cu.reportError(ex);
                throw ex;
            }
            return null;
        },
        enumerable: true});

})();
