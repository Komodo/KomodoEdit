/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Monitor for file status changes
 *
 * Note this is an imperfect implementation, it only monitors files that
 * Komodo is already aware of, it does not monitor files that aren't already
 * monitored.
 *
 * @module ko/filestatus
 */
(function() {

    const {Cc, Ci}  = require("chrome");

    var listeners = {};

    this.init = function()
    {
        var observer = {
            observe: (subject, topic, data) =>
            {
                var urllist = data.split('\n');
                for (let u of urllist) {
                    if (u in listeners)
                    {
                        for (let cb of listeners[u])
                            cb(u);
                    }
                }

                if ("all" in listeners)
                {
                    for (let cb of listeners.all)
                        cb(urllist);
                }
            }
        };

        var observerSvc = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);
        observerSvc.addObserver(observer, "file_status", false);
    };

    /**
     * Monitor the given file urls
     *
     * @param   {Array|Function} fileurls - file urls or callback to monitor all file changes
     * @param   {Function} callback - What to do on change
     *
     * @returns {Void}
     */
    this.monitor = function(fileurls, callback)
    {
        if (typeof fileurls == "function")
        {
            callback = fileurls;
            fileurls = ["all"];
        }

        if ( ! Array.isArray(fileurls))
            fileurls = [fileurls];

        for (let url of fileurls)
        {
            if ( ! (url in listeners))
                listeners[url] = [];

            listeners[url].push(callback);
        }
    };

    /**
     * Stop monitoring file urls
     *
     * @param   {Array|Function}        fileurls, or callback to unmonitor all file changes
     * @param   {Function} callback     The callback that was used to monitor
     *
     * @returns {Void}
     */
    this.unmonitor = function(fileurls, callback)
    {
        if (typeof fileurls == "function")
        {
            callback = fileurls;
            fileurls = ["all"];
        }

        if ( ! Array.isArray(fileurls))
            fileurls = [fileurls];

        for (let url of fileurls)
        {
            if ( ! (url in listeners))
                continue;

            listeners[url] = listeners[url].filter((cb) => cb != callback);
        }
    };

    this.init();

}).apply(module.exports);
