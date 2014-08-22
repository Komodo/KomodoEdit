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
            "chrome://komodo/content/library/logging.js",
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
            loader.loadSubScript(url, scope, "UTF-8");
        } catch (ex) {
            if (!log && module != "logging") {
                log = _import({}, "logging").getLogger("jstest.mock");
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
