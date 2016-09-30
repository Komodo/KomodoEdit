(function()
{
    const ajax = require("ko/ajax");
    const log = require("ko/logging").getLogger("Slack");

    // Slack variables
    const realm = "Slack Integration User Key"; // Used while saving key
    var key = null;
    var channels = null;
    
    this.load = function()
    {
        require("ko/commands").register("share_on_slack",
                                        this.share.bind(this, undefined),
                                        {
                                            label: "Slack: Share Code on your slack"
                                        });
        
        require("ko/share").register("ko/share/slack", "Share Code via Slack");
        
        // Create a pref page for this that is appended into the existing prefs
        // dialog.
        // Should be able to show:
        //  - available channels to pick a/few default/s (This has to perform an API call using this module)
        //  - default initial message (in the "" below the post in Slakc)
        //  - default title
        
        require("ko/share").register("slack", "Share Code on Slack");
        
        require("notify/notify").categories.register("slack",
        {
            label: "Slack Integration"
        });
    };
    
    /**
     * Share content on Slack
     * Must have a file open
     * Must have content in file
     * If there is no module Key set then it uses useKey which will execute
     * share() AND save the key in the module for later use
     */ 
    this.share = function()
    {
        var ajax = require("ko/ajax");
        var content = getContent();
        // If `content` is empty then stop.  Slack won't accept it any way.
        // Response: {"ok":false,"error":"no_file_data"}
        if( content == "" )
        {
            return;
        }
        if( ! key )
        {
            this.useKey(this.share);
            return;
        }
        // set the language to be coloured as
        var language = getFileLangName();
        if( ! channels )
        {
            channels = getChannels(true);
            if ( ! channels ) {
                var locale = "You have to pick a channel.  Next time pick a channel.  No Channel?  No Slack!";
                require("notify/notify").interact(locale, "slack", {priority: "warn"});
                return;
            }
        }
        var params = require("sdk/querystring").stringify(
        {
            token: key,
            content: content,
            //file: filepath,
            filetype: language,
            filename: filename,
            //title: filename,
            channels: channels, // komodo
            //channels: "komodo", // komodo
            //channels: "general", // ckf
            initial_comment: "It's almost REEEEEEEEEEADYYYYYYYY!", // Ask user for comment
            title: "Post from Komodo IDE via Slack APIs" // Allow default in prefs
            // this should have 
        });
        var baseUrl = "https://slack.com/api/files.upload?";
        var reqStr = baseUrl+params;
        ajax.post(reqStr,(code, respText) =>
        {
            // Notify instead of console.log
            // Write a proper callback that handles results from the API using
            // notify.  See errors section for API function:
            //   https://api.slack.com/methods/files.upload
            var respJSON = JSON.parse(respText);
            if( respJSON.ok )
            {
                // XXX Include channels posted to and link in notification
                // XXX If option is enable, add link to clipboard
                // XXX If option enabled, open the link? Might be annoying to
                //     have a new slack window opened everytime you share code.
                var locale = "Content posted successfully to Slack";
                require("notify/notify").interact(locale, "slack", {priority: "info"});
                /** We get a link and a bunch of other stuff that we can use here
                 * 
                "file": {
                    "id": "F2HA5CFB4",
                    "created": 1475104033,
                    "timestamp": 1475104033,
                    "name": "Text-1.txt",
                    "title": "Sent from Komodo IDE 10.1 using ko\/share\/slack",
                    "mimetype": "text\/plain",
                    "filetype": "text",
                    "pretty_type": "Plain Text",
                    "user": "U03AEA29V",
                    "editable": true,
                    "size": 4,
                    "mode": "snippet",
                    "is_external": false,
                    "external_type": "",
                    "is_public": true,
                    "public_url_shared": false,
                    "display_as_bot": false,
                    "username": "",
                    "url_private": "https:\/\/files.slack.com\/files-pri\/T0336E9KP-F2HA5CFB4\/text-1.txt",
                    "url_private_download": "https:\/\/files.slack.com\/files-pri\/T0336E9KP-F2HA5CFB4\/download\/text-1.txt",
                    "permalink": "https:\/\/activestate.slack.com\/files\/careyh\/F2HA5CFB4\/text-1.txt",
                    "permalink_public": "https:\/\/slack-files.com\/T0336E9KP-F2HA5CFB4-fe078814ce",
                    "edit_link": "https:\/\/activestate.slack.com\/files\/careyh\/F2HA5CFB4\/text-1.txt\/edit",
                    "preview": "boop",
                    "preview_highlight": "<div class=\"CodeMirror cm-s-default CodeMirrorServer\" oncopy=\"if(event.clipboardData){event.clipboardData.setData('text\/plain',window.getSelection().toString().replace(\/\\u200b\/g,''));event.preventDefault();event.stopPropagation();}\">\n<div class=\"CodeMirror-code\">\n<div><pre>boop<\/pre><\/div>\n<\/div>\n<\/div>\n",
                    "lines": 1,
                    "lines_more": 0,
                    "preview_is_truncated": false,
                    "channels": ["C03NU4MN5", "C03NU99VB", "C22B2S1KK"],
                    "groups": [],
                    "ims": [],
                    "comments_count": 1,
                    "initial_comment": {
                        "id": "Fc2H9U7T1T",
                        "created": 1475104033,
                        "timestamp": 1475104033,
                        "user": "U03AEA29V",
                        "is_intro": true,
                        "comment": "@carey This is working!!!",
                        "channel": ""
                    }
                }*/
                // XXX Include name
                log.debug("code: "+code+"\nResponse: "+respText);
            }
            else
            {
                // XXX I don't know what a bad response looks like at the moment
                // need to look this up.
                var locale = "Couldn't post to Slack.";
                require("notify/notify").interact(locale, "slack", {priority: "warn"});
                log.warn(locale + "\n" + respText);
                return;    
            }
            // XXX shouldn't be doing this but don't have a proper solution for
            // channel selection yet.  Needs a pref saved somehow.
            channels = null;
        });
    };
 
    /**
     * Authenticate the user trying to post to Slack
     * 
     * This need to be async as well so it can call whatever function was trying
     * to run when it was asked to authenticate.
     *
     * @argument    {function}  callback  function to be run with the key  
     */
    this.authenticate = function(callback)
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
                
                if( credentials.length > 0 )
                {
                    if( callback ) this.useKey(callback);
                }
                else
                {
                    var locale = "Authentication cancelled or failed.";
                    require("notify/notify").interact(locale, "slack", {priority: "info"});
                    return;    
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
                // Set module key variable
                require("sdk/passwords").search({
                    username: "slack",
                    url: "https://slack.com/api",
                    onComplete: function (credentials) {
                        credentials.forEach
                        (
                            function(element)
                            {
                                key = element.password;
                            }
                        );
                    }   
                });
            }   
        });
    };
    
    /**
     * Get the saved Slack API key
     *
     * @argument {function} callback    The function to run once key is set.
     *
     * The function that retrieves keys from storage is async so we can't just
     * return it if it's not set yet.
     * If not authenticated then the callback is passed to
     * authenticate(callback) to, you know, authenticate, then passed to
     * useKey(callback) again.
     *
     */
    this.useKey = function(callback)
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
                    if( credentials.length < 1 )
                    {
                        log.warn("You have not been authenticated with a slack channel.  Let's do that now...");
                        this.authenticate(callback); 
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
    };
    
       
    /**
     * Get the currently open files languages name
     * Defaults to "text"
     */
    function getFileLangName()
    {
        var view = require("ko/views").current().get();
        return view.koDoc.language || "text";
    }
    /**
     * Retrieve the list of available channels for the authenticated user
     *
     * @argument {bool} prompt  prompt the user to enter a channel manually
     * 
     * @returns {String} comma delimited string of one or more channels
     * 
     */
    function getChannels(prompt)
    {
        // Check for module var being set
        // Check for pref being set, if yes, set the module var then return it
        // XXX Change to prompt to see if user wants to make this their default
        // If yes, save it to prefs.  If it does, we have to provide 
        if( prompt )
        {
            return require("ko/dialogs").prompt("What channel? You can pick more than one using ',' as a delimiter.");
        }
        else
        {
            // get it from the prefs.  If it's not in the prefs then select from
            // API call list.
            require("notify/notify").interact("getChannels(false) not Implmemented", "slack", {priority: "error"});
        }
    };
    
    /**
     * Get content to post to Slack
     * 
     */
    function getContent()
    {
        var view = require("ko/views").current().get();
        if ( ! view.scimoz )
        {
            var locale = "You don't have a file open to post any content to Slack.";
            require("notify/notify").interact(locale, "slack", {priority: "info"});
            return "";
        }
        // get content
        //   whole file
        //   Or
        //   selection
        if ( view.scimoz.selectionEmpty ) {
            content = view.scimoz.text;
            filename = view.title;
        } else {
            content = view.scimoz.selText;
            let viewTitlesplit = view.title.split(".");
            let name = viewTitlesplit.shift() + "-snippet";
            let extension = viewTitlesplit.toString();
            filename = [name,extension].join(".");
        }
        if( content == "" )
        {
            var locale = "You're file is empty.  You don't want to share that.  Don't be weird.";
            require("notify/notify").interact(locale, "slack", {priority: "info"});
            return content;
        }
        return content;
    };
    
}).apply(module.exports);