(function()
{
    const ajax = require("ko/ajax");
    const log = require("ko/logging").getLogger("Slack");
    const prefs = require("ko/prefs");

    // Slack variables
    const realm = "Slack Integration User Key"; // Used while saving key
    //var title = "Post from Komodo IDE via Slack APIs";
    var title = channels = key = null;
    var comment = "";
    
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
        var params =
        {
            token: key,
            content: content,
            filetype: getFileLangName(),
            filename: getFilename(),
        };
        
        // function to pass to API request to process response
        function callback(code, respText)
        {
            /** Notify instead of console.log
             * Write a proper callback that handles results from the API using
             * notify.  See errors section for API function:
             *   https://api.slack.com/methods/files.upload
             */
            
            var respJSON = JSON.parse(respText);
            if( respJSON.ok )
            {
                /** XXX Include channels posted to and link in notification
                 * XXX If option is enable, add link to clipboard
                 * XXX If option enabled, open the link? Might be annoying to
                 *     have a new slack window opened everytime you share code.
                 */
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
        };
    };

    /**
     * Trigger a dialog for a user to fill in fields for posting to slack
     * Asks for (* means madatory):
     *   Title (Defaults to `filename` of `filename-snippet`, if changed gets saved to prefs)
     *   Channels* (Saves last select)
     *   Message (No default, not saved)
     *
     * @returns {Object}    postData    object holding the about values
     * {
     *      "title":"Posted from Komodo IDE",
     *      "channels":"a,b,c",
     *      "message":"Look what I made!"
     *  }
     */
    function getPostData(params, callback)
    {
        // Retrieve title from prefs
        if( prefs.hasPref("slack.title") )
        {
            var userSetTitle = true;
            title = prefs.getStringPref("slack.title");
        }
        else
        {
            var userSetTitle = false;
            title = getFilename();
        }
        // Have to open the panel before appending anything
        var panel = require("ko/ui/panel").create(null,{
            attributes: {
                backdrag: true,
                noautohide: true,
                width: 200,
                height: 100
            }
        });
        var komodo = require("ko/dom")("#komodo_main");
        komodo.append(panel.$element);
        var x = (window.innerWidth/2)-(200/2);
        var y = (window.innerHeight/2)-(50/2);
        panel.open({ x:x, y:y });
        
        // Title text field
        var options = { attributes:
        {
            id:"slackTitle",
            type:"autocomplete",
            value: title,
            label:"Title:",
            width: 70,
        }};
        var textTitle = require("ko/ui/textbox").create(options);
        panel.addRow(textTitle);
        
        // Title reset button
        var resetTitleBtn = require(ko/ui/button).create(
            {
                attributes:
                {
                    label:"Reset Title",
                    oncommand: function()
                    {
                        require("ko/dom")("#slackTitle").text(getFilename());
                    }
                }
            }
        )
        panel.addRow(resetTitleBtn);
        
        // Channel selection list        
        options = { attributes:
            {
                label:"Channels",
                value:"Loading...",
                disabled:"true",
                seltype:"multiple"
            }
        }
        var channelList = require("ko/ui/listbox").create(options);
        panel.addRow(channelList);
        channelList.disable();
        // Must retrieve the channels async as they might need to be retrieved
        // through an API call.
        function populateChannels(channels)
        {
            channelList.addListItems(channels.split(","));
            channelList.enable();
            postButton.enable();
        }
        getChannels(populateChannels);
        
        // Message Text field
        options = { attributes:
        {
            type:"autocomplete",
            label:"Message:",
            multiline:true,
            rows: 3,
            width: 60
        }};
        var textMessage = require("ko/ui/textbox").create(options);
        panel.addRow(textMessage.$element);
        
        // Post button
        var postButton = require("ko/ui/button").create(
            {
                attributes:
                {
                    label:"Post",
                    disabled:true
                }
            });
        var onClick = function()
        {
            title = textTitle.$element.text();
            var channelsList = [];
            channelList.getSelectedItem().forEach(function(elem){channelList.push(elem.value)});
            var message = textMessage.$element.text();
            if( "" == title )
            {
                prefs.deletePref("slack.title");
                title = null;
            }
            else if( getFilename() == title )
            {
                prefs.deletePref("slack.title");
            }
            else
            {
                prefs.setStringPref("slack.title", title);
            }
            params.title = title;
            params.channels = channelList.join(",");
            params.initial_comment = message;
            makeAPIcall("files.upload", params, callback);
            panel.element.hidePopup();
        }
        postButton.onCommand(onClick);
        panel.addRow(postButton)
        
        //   Done button
        // Add listener to button to retrieve fields
        //   save Title to prefs & add to postData
      
        //   add selected channels to postData & save to global var
        //   add message to 
        //   return postData obj.
    }
    
    /**
     * Make an API call and process the result
     *
     * @argument {String}   method  The API method to be called
     * @argument {Object}   params  An object of API call parameters
     * @argument {function} callback    To process response
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
        key = null
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
     * This function ensures that global key var is set when the user tries to
     * post something.  It goes through the following workflow:
     *  - The function that retrieves keys from storage is async so we can't just
     * return it if it's not set yet.
     *  - If not authenticated then the callback is passed to
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
                                callback(key);
                            }
                        }
                    );
                }.bind(this)
            });
        }
        else
        {
            callback(key);
        }
    };
     
    /**
     * Get or create a file name to be displayed.
     * Takes the file name if nothing selected
     * Inserts `-snippet` before extension if
     *
     * @returns {String}    filename    name of file with "-snippet" appended
     *                                  if only sending selection.
     */
    function getFilename()
    {
        var view = require("ko/views").current().get();
        var filename;
        if ( view.scimoz.selectionEmpty ) {
            filename = view.title;
        } else {
            let viewTitlesplit = view.title.split(".");
            let name = viewTitlesplit.shift() + "-snippet";
            // support multi ext. filenames common in templating
            let extension = viewTitlesplit.join(".");
            // Filter out empty string if this file had no extension
            filename = [name,extension].filter(function(e){return e}).join(".");
        }
        return filename;
    }
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
     * Retrieve the list of available channels for the authenticated user and
     * save it to the prefs.  Just pull them from the prefs if they are already
     * there.
     * 
     * @argument {function} callback  function to do something with the return
     *                                channels.  This callback gets passed a
     *                                comma separate string of channel names
     * 
     */
    function getChannels(callback)
    {
        var pref = "slack.channels";
        if (prefs.hasPref(pref))
        {
            callback(prefs.getStringPref(pref).split(","));
        }
        if( ! key )
        {
            this.useKey(getChannels());
            return;
        }
        var params = require("sdk/querystring").stringify(
        {
            token: key,
            exclude_archived:1
        });
        //var baseUrl = "https://slack.com/api/channels.list?";
        function processResponse(code, respText)
        {
            // Notify instead of console.log
            var respJSON = JSON.parse(respText);
            var channelsJSON = respJSON.channels;
            var channels = [];
            for (let channel of channelsJSON) {
                channels.push(channel.name);
            }
            var chanString = channels.join(",");
            prefs.setStringPref(pref,chanString)
            callback(chanString);
        }
        makeAPIcall("channels.list", params, callback);
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
        // Get whole file or get selection
        if ( view.scimoz.selectionEmpty ) {
            content = view.scimoz.text;
        } else {
            content = view.scimoz.selText;
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