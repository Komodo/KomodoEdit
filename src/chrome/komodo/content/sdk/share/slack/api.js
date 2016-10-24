/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * api methods for ko/share/slack
 *
 * @module ko/share/slack/api
 */
(function()
{
    const ajax = require("ko/ajax");
    const log = require("ko/logging").getLogger("slack/api");
    const _window = require("ko/windows").getMain();
    const prefs = require("ko/prefs");
    const slackAPI_SS = require("ko/simple-storage").get("slackAPI");
    // Slack variables
    const realm = "Slack Integration User Key"; // Used while saving key
    //var title = "Post from Komodo IDE via Slack APIs"
    var key = null;

    /**
     * Post your file to Slack
     *
     * @param    {Object}    params  params to push a file
     * @param    {function}  callback    function run when post is complete
     */
    this.post = function(params, callback)
    {
        if( ! key )
        {
            useKey(this.post.bind(this, params, callback));
            return;
        }
        params.token = key;
        makeAPIcall("files.upload", params, callback);
    }
    /**
     * Make an API call and process the result
     *
     * @param {String}   method  The API method to be called
     * @param {Object}   params  An object of API call parameters
     * @param {function} callback    To process response
     *    Callback takes req.status and req.responseTextText, req.
     *    This function uses ko/ajax.post
     */
    function makeAPIcall(method, params, callback) {
        
        var reqUrl =  "https://slack.com/api/"+method+"?"+
            require("sdk/querystring").stringify(params);
        ajax.post(reqUrl, callback);
    }
    
    /**
     * Authenticate the user trying to post to Slack
     * 
     * This need to be async as well so it can call whatever function was trying
     * to run when it was asked to authenticate.
     *
     * @param    {function}  callback  function to be run with the key  
     */
    var authenticate = function(callback)
    {
        // ### If I cancel in the dialog this gets stuck in a loop.
        // Also server fails to handle and sends back garbage.
        ko.windowManager.openDialog("chrome://komodo/content/dialogs/slackauth.xul",
                                    "Slack Auth",
                                    "chrome,modal,titlebar,centerscreen");
        // Confirm a key was saved then run the callback if it was passed in
        require("sdk/passwords").search(
        {
            username: "slack",
            url: "https://slack.com/api",
            onComplete: function (credentials)
            {
                
                if( credentials.length )
                {
                    if( callback ) useKey(callback.bind(this));
                }
                else
                {
                    var locale = "Authentication cancelled or failed.";
                    require("notify/notify").interact(locale, "share", {priority: "info"});
                }
                
            }.bind(this)
        });
    };
    
    /**
     * Delete the currently saved key.  Just incase.
     * May be used later if we need to handle invalid keys.
     */
    this.deleteKey = function()
    {
        require("sdk/passwords").search({
            username: "slack",
            url: "https://slack.com/api",
            onComplete: function (credentials) {
                credentials.forEach(require("sdk/passwords").remove);
            }   
        });
        key = null;
    };
    
    /**
     * Save the API key
     * Only saves one key.  Deletes the previously saved key if it exists.
     */
    this.saveKey = function(APIkey)
    {
        // delete any saved keys
        require("sdk/passwords").search({
            username: "slack",
            url: "https://slack.com/api",
            onComplete: function (credentials) {
                credentials.forEach(require("sdk/passwords").remove);
                // Safest place to save the key is inside the search callback
                // where the deletion might happen as it will run regardless of
                // anything being found and I wouldn't want to save the key only
                // to have this callback delete it later.
                //
                // Save the new key
                require("sdk/passwords").store({
                    url: "https://slack.com/api",
                    username: "slack",
                    password: APIkey,
                    realm: realm
                });
                key = APIkey;
            }   
        });
    };
    
    /**
     * Get the saved Slack API key
     *
     * @param {function} callback    The function to run once key is set.
     *
     * This function ensures that global key var is set when the user tries to
     * post something.  It goes through the following workflow:
     *  - The function that retrieves keys from storage is async so we can't just
     * return it if it's not set yet.
     *  - If not authenticated then the callback is passed to
     * authenticate(callback) to, you know, authenticate, then passed to
     * useKey(callback) again.
     *
     */
    function useKey(callback)
    {
        // Check if key has been set or this is the second time this has run.
        // If not, grab it, save key globally, then check again.
        if ( ! key ) {
            // Once you're in this `if` you won't get a return from the function
            // I feel like this is terrible UX.
            require("sdk/passwords").search(
            {
                username: "slack",
                url: "https://slack.com/api",
                onComplete: function (credentials)
                {
                    if( ! credentials.length )
                    {
                        log.warn("You have not been authenticated with a slack channel.  Let's do that now...");
                        authenticate(callback); 
                        return;
                    }
                    // Otherwise, save the key globally
                    credentials.forEach
                    (
                        function(element)
                        {
                            key = element.password;
                            if( callback )
                            {
                                callback();
                            }
                        }
                    );
                }.bind(this)
            });
        }
        else
        {
            callback();
        }
    };
     
    /**
     * Retrieve the list of available channels for the authenticated user and
     * save it to the prefs.  Just pull them from the prefs if they are already
     * there.
     * 
     * @param {function} callback  function to do something with the return
     *                                channels.  This callback gets passed a
     *                                comma separate string of channel names
     * 
     */
    this.getChannels = function(callback)
    {
        if (slackAPI_SS.storage.channels)
        {
            callback(slackAPI_SS.storage.channels);
            return;
        }
        if( ! key )
        {
            useKey(this.getChannels.bind(this, callback));
            return;
        }
        var params = require("sdk/querystring").stringify(
        {
            token: key,
            exclude_archived:1
        });
        function processResponse(code, respText)
        {
            var respJSON;
            var message = "Could not process response from Slack.  No channels available.  Please try again: ";
            try
            {
                respJSON = JSON.parse(respText);
            } catch(e) {
                log.error(message+e);
                require("notify/notify").interact(message+e, "share", {priority: "info"});
                return;
            }
            if ( true === respJSON.ok )
            {
                var channelsJSON = respJSON.channels;
                var channels = [];
                for ( let channel of channelsJSON ) {
                    channels.push(channel.name);
                }
                slackAPI_SS.storage.channels = channels;
                callback(channels);
            }
            else
            {
                require("notify/notify").interact(message+respJSON.error, "share", {priority: "info"});
            }
           
        }
        makeAPIcall("channels.list", params, processResponse);
    };
    
}).apply(module.exports);