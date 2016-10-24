/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Sharing sub-module for ko/share that adds slack sharing
 *
 * @module ko/share/slack
 */
(function()
{
    const api = require("ko/share/slack/api");
    const dialog = require("ko/share/slack/dialog");

    this.load = function()
    {
        require("ko/share").register("slack", "ko/share/slack", "Share Code via Slack");
    };
    
    /**
     * Share content on Slack
     * 
     * @param   {String} data     Data to share
     * @param   {Object} meta     Object containing meta information
     * 
     * @returns {Void} 
     */
    this.share = function(content, meta) 
    {
        var params =
        {
            content: content,
            title: meta.title || null
        };
        
        dialog.create(params, function(isSuccesful, url/*, code, responseText*/)
        {
            if (isSuccesful)
            {
                var msg = "Content posted successfully to Slack: " + url;
                require("notify/notify").send(msg, "kopy",
                {
                    command: () => { ko.browse.openUrlInDefaultBrowser(url); }
                });
            }
            else
            {
                var locale = "Share to slack failed, try again later.";
                require("notify/notify").send(locale, "slack", {priority: "warn"});
            }
        });
    };
    
    /**
     * Deletes your api key and deletes saved cookies that make you log into a
     * particular team, ie. activestate.slack.com
     */
    this.signout = function()
    {
        api.deleteKey();
        // delete other stuff here XXX NOT DONE
    };

}).apply(module.exports);