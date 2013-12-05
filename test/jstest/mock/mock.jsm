const EXPORTED_SYMBOLS = ["import"];

var {classes: Cc, interfaces: Ci, utils: Cu} = Components;

/**
 * Import mock modules
 * @param ko The global "ko" object to import to
 * @param ... The modules to import
 *
 * Example:
 *  import(ko, "views", "macros");
 */
Cu.getGlobalForObject({}).import = function _import(ko) {
    // special modules that we can import from the real thing
    const kSpecialCaseURLs = {
        "logging":
            "jetpack:ko/logging",
        "stringutils":
            "chrome://komodo/content/library/stringutils.js",
        "treeview":
            "chrome://xtk/content/treeview.js",
    };

    if (!("xtk" in ko)) {
        ko.xtk = {};
    }
    if (!Object.hasOwnProperty.call(ko, "__mock_loaded_modules")) {
        ko.__mock_loaded_modules = {};
    }

    let global = Cu.getGlobalForObject(ko);
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    let scope = Object.create(global, {ko: {value: ko}, xtk: {value: ko.xtk}});
    let log = null;

    for each (let module in Array.slice(arguments, 1)) {
        if (Object.hasOwnProperty.call(ko.__mock_loaded_modules, module)) {
            // already loaded
            continue;
        }
        let url = module;
        if (url.indexOf("://") == -1) {
            url = "resource://komodo-jstest/mock/" + module + ".jsm";
        }
        if (Object.hasOwnProperty.call(kSpecialCaseURLs, module)) {
            url = kSpecialCaseURLs[module];
        }
        try {
            if (url.startsWith("jetpack:")) {
                // Loading a JetPack-based module; this is for transition to
                // having the unit tests use require() directly.
                let id = url.replace(/^jetpack:/, "");
                if (typeof(global.JetPack) === "undefined") {
                    // Need to set up jetpack loader first...
                    // Use a sandbox, otherwise the loader gets confused about
                    // which global to use, and ends up with "ko is not an
                    // Object" errors.
                    let principal = Cc["@mozilla.org/systemprincipal;1"]
                                      .createInstance(Ci.nsIPrincipal);
                    let sandbox = Cu.Sandbox(principal,
                                             { sandboxName: "unit test mock global",
                                               sandboxPrototype: {
                                                 window: {},
                                                 document: {},
                                                 ko: ko,
                                               }});
                    Cc["@mozilla.org/moz/jssubscript-loader;1"]
                      .getService(Ci.mozIJSSubScriptLoader)
                      .loadSubScript("chrome://komodo/content/jetpack.js", sandbox);
                    // Copy things off the sandbox (xrays)
                    global.JetPack = sandbox.JetPack;
                    global.require = sandbox.require;
                }
                ko[module] = global.require(id);
            } else {
                loader.loadSubScript(url, scope, "UTF-8");
            }
        } catch (ex) {
            if (!log && module != "logging") {
                try {
                    log = _import({}, "logging").getLogger("jstest.mock");
                } catch (ex2) {
                    dump("Error importing logging module: " + ex2 + "\n" +
                         ex2.stack + "\n");
                    log = null;
                }
            }
            if (log) {
                log.error("While loading " + url + ": " + ex.toString());
            }
            throw ex;
        }
        ko.__mock_loaded_modules[module] = true;
    }
    return ko;
};
