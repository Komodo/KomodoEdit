/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

/**
 * Sharing sub-module for ko/share that adds kopy.io sharing
 *
 * @module ko/share/kopy
 */
(function() {
    const log       = require("ko/logging").getLogger("kopy");
    const prefs     = require("ko/prefs");
    const menu      = require("ko/menu");
    const button      = require("ko/button");
    const legacy    = require("ko/windows").getMain().ko;

    this.load = function()
    {
        require("ko/share").register("kopy", "ko/share/kopy", "Share Code via kopy.io");

        require("notify/notify").categories.register("kopy",
        {
            label: "kopy.io Integration"
        });
    }

    /**
     * Share the given data on kopy.io
     *
     * @param   {String} data     Data to share
     *
     * @returns {Void}
     */
    this.share = function(data, meta)
    {
        var locale;
        var useClipboard = prefs.getBoolean("kopy_copy_to_clipboard", true);
        var showInBrowser = prefs.getBoolean("kopy_show_in_browser", true);

        if ( ! useClipboard && ! showInBrowser)
        {
            locale = "Could not share code via kopy.io; both clipboard and browser settings are disabled";
            require("notify/notify").send(locale, "kopy", {priority: "warning"});
            return;
        }

        locale = "You are about to share your current code selection with others, \
                     this means anyone with access to the URL can view your code.\
                     Are you sure you want to do this?";
        if ( ! require("ko/dialogs").confirm(locale, {doNotAskPref: "kopy_donotask"}))
        {
            log.debug("kopy cancelled by confirmation");
            return;
        }

        if ( ! meta.language)
        {
            meta.language = 'null';
        }

        var params = require("sdk/querystring").stringify(
        {
            data: data,
            language: meta.language,
            scheme: prefs.getStringPref("editor-scheme").replace(/\-(dark|light)$/, '.$1')
        });

        var baseUrl = prefs.getString("kopy_baseurl", "https://kopy.io");
        var httpReq = new window.XMLHttpRequest({mozSystem: true});
        httpReq.open("post", baseUrl + '/documents', true);
        httpReq.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        httpReq.setRequestHeader("Content-length", params.length);
        httpReq.setRequestHeader("Connection", "close");
        httpReq.send(params);

        httpReq.onload = function ()
        {
            try
            {
                var key = JSON.parse(this.responseText).key;
            }
            catch (e)
            {
                var errorMsg = "kopy.io: Code sharing failed, malformed response";
                log.warn(errorMsg + ": " + this.responseText);
                require("notify/notify").send(errorMsg, "kopy", {priority: "error"});
            }

            var url = baseUrl + '/' + key;
            if (useClipboard)
            {
                require("sdk/clipboard").set(url);
                var msg = "URL copied to clipboard: " + url;
                require("notify/notify").send(msg, "kopy",
                {
                    command: () => { legacy.browse.openUrlInDefaultBrowser(url) }
                });
            }

            if (showInBrowser)
            {
                legacy.browse.openUrlInDefaultBrowser(url);
            }
        };

        httpReq.onerror = function(e)
        {
            var errorMsg = "kopy.io: HTTP Request Failed: " + e.target.status;
            log.warn(errorMsg);
            require("notify/notify").send(errorMsg, "kopy", {priority: "error"});
        }
    }
}).apply(module.exports);
