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
        "stringutils":
            "chrome://komodo/content/library/stringutils.js",
    };

    let global = Cu.getGlobalForObject(ko);
    let loader = Cc['@mozilla.org/moz/jssubscript-loader;1']
                   .getService(Ci.mozIJSSubScriptLoader);
    let scope = Object.create(global, {ko: {value: ko}});
    let log = null;

    for each (let module in Array.slice(arguments, 1)) {
        let url = "resource://komodo-jstest/mock/" + module + ".jsm";
        if (Object.hasOwnProperty(kSpecialCaseURLs, module)) {
            url = kSpecialCaseURLs[module];
        }
        try {
            loader.loadSubScript(url, scope, "UTF-8");
        } catch (ex) {
            if (!log) {
                let logging = Cu.import("chrome://komodo/content/library/logging.js", {}).logging;
                log = logging.getLogger("jstest.mock");
            }
            log.error(ex.toString());
            throw ex;
        }
    }
};
