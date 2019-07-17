(function() {

    if (typeof(window) !== "undefined") {
        // This is being loaded in a window; make sure we have the jetpack loader,
        // and define ko.logging as a lazy property
        var { classes: Cc, interfaces: Ci, utils: Cu } = Components;
        if (window && window.__is_unit_test__) {
            window.__method__ = "window"; // For unit testing
        }
    } else  {
        // This is being loaded in a JS component or a JS module; export a "logging"
        // object with the desired API.
        var { logging } = Components.utils.import("chrome://komodo/content/sdk/logging.js", {});

        // Note that Cu.getGlobalForObject({}) gives us the wrong global...
        this.EXPORTED_SYMBOLS = ["logging"];
        this.logging = this.exports = logging;
        this.exports.__method__ = "import"; // For unit testing
    }

})();
