/* Copyright (c) 2000-2013 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


if (typeof(ko)=='undefined') {
    var ko = {};
}

ko.utils = {};

(function() {

    const log = ko.logging.getLogger('ko.utils');

    /**
     * Require one or multiple files
     *
     * @param prefix {string}               Optional path prefix to use for all files
     * @param files {string|array|null}     file or files to be loaded. If this is null
     *                                      or not an array then prefix will become files.
     * @param targetObj {null}              See mozIJSSubScriptLoader documentation
     */
    this.include = function ko_utils_require(prefix, files = undefined, targetObj = undefined)
    {
        if ( ! files || ( ! Array.isArray(files) && typeof files != "string"))
        {
            targetObj = files;
            files = prefix;
            prefix = '';
        }

        if ( ! Array.isArray(files))
        {
            files = [files];
        }

        for (let [,file] in Iterator(files))
        {
            if (typeof file != "string") continue;
            
            log.debug("Including " + file);

            Services.scriptloader.loadSubScript(prefix + file, targetObj);
        }
    };

    /**
     * Restart Komodo
     *
     * @param confirmation {boolean}    Whether to show a confirmation (if necessary)
     */
    this.restart = function(confirmation = true)
    {
        log.warn('Restarting Komodo');

        if (confirmation)
        {
            var cancelQuit = Cc["@mozilla.org/supports-PRBool;1"].
                             createInstance(Ci.nsISupportsPRBool);
            Services.obs.notifyObservers(cancelQuit, "quit-application-requested",
                                         "restart");
            if (cancelQuit.data)
              return; // somebody canceled our quit request
        }

        var appStartup = Cc["@mozilla.org/toolkit/app-startup;1"].
                         getService(Ci.nsIAppStartup);
        appStartup.quit(Ci.nsIAppStartup.eAttemptQuit |  Ci.nsIAppStartup.eRestart);
    };

}).apply(ko.utils);
