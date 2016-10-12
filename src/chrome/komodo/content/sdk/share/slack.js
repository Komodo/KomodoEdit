(function()
{
    const ajax = require("ko/ajax");
    const log = require("ko/logging").getLogger("slack");
    const prefs = require("ko/prefs");
    const _window = require("ko/windows").getMain();
    const slackAPI = require("ko/share/slack/api");
    // Slack variables
    var title = null;
    var channels = null;
    var comment = "";
    
    this.load = function()
    {
        require("ko/commands").register("share_on_slack",
                                        this.share.bind(this, undefined),
                                        {
                                            label: "Slack: Share Code on your slack"
                                        });
        
        require("ko/share").register("slack", "ko/share/slack", "Share Code via Slack");
        
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
    this.share = function(content, filename, fileType) 
    {
        var params =
        {
            content: content,
            filetype: filename,
            filename: fileType
        };
        
        // function to pass to API request to process response
        function processResponse(code, respText)
        {
            /** Notify instead of console.log
             * Write a proper callback that handles results from the API using
             * notify.  See errors section for API function:
             *   https://api.slack.com/methods/files.upload
             */
            
            var respJSON = JSON.parse(respText);
            console.log(respJSON);
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
        getPostData(params, processResponse);
    };

    // Title text field
    function createTitleField()
    {
        var options = { attributes:
        {
            id:"slackTitle",
            type:"autocomplete",
            value: title,
            label:"Title:",
            width: 70,
        }};
        return require("ko/ui/textbox").create(options);
    }
    
    // Title reset button
    function createTitleResetBtn() {
        function resetTitle()
        {
            // This won't do `filename-snippet.js`. Lame but when I'm in the
            // panel I no longer have access to getFilename. I can't make it
            // public just for that.
            require("ko/dom")("#slackTitle").value(require("ko/views").current().filename);
        }
        var resetBtn =  require("ko/ui/button").create( {attributes: { label:"Reset Title"} });
        resetBtn.onCommand(resetTitle);
        return resetBtn;
    }

    // Channel selection list        
    function createChannelField() {
        options = { attributes:
            {
                label:"Channels",
                value:"Loading...",
                disabled:"true",
                seltype:"multiple"
            }
        }
        var availableChannels = require("ko/ui/listbox").create(options);
        availableChannels.disable
        return availableChannels;
    }

    // Message Text field
    function createMsgField() {
        options = {
            attributes:
            {
                type:"autocomplete",
                label:"Message:",
                multiline:true,
                rows: 3,
                width: 60
            }
        };
        return require("ko/ui/textbox").create(options);
    }

    // Post button
    function createPostBtn() {
       return require("ko/ui/button").create({attributes:{label:"Post",disabled:true}});
    }
    
    // Close Button
    function createCloseBtn() {
        return require("ko/ui/button").create({attributes:{label:"Close"}});
    }
    
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
        try
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
            // XXX this should check for a panel and not recreate it if it already
            // exists.
            var panel = require("ko/ui/panel").create(null,{
                attributes: {
                    backdrag: true,
                    noautohide: true,
                    width: 200,
                    height: 100
                }
            });
            var x = (window.innerWidth/2)-(200/2);
            var y = (window.innerHeight/2)-(50/2);
            panel.open({ x:x, y:y });
            
            var titleField = createTitleField();
            panel.addRow(titleField);

            var titleRstBtn = createTitleResetBtn();
            panel.addRow(titleRstBtn);
            
            var availableChannels = createChannelField();
            panel.addRow(availableChannels);
            
            var selectedChannels = [];
            if( prefs.hasPref("slack.selected.channels") )
            {
                selectedChannels = JSON.parse(prefs.getStringPref("slack.selected.channels"));
            }

            var msgField = createMsgField();
            panel.addRow(msgField);
            
            var postButton = createPostBtn();
            var post = function()
            {
                title = titleField.$element.value();
                availableChannels.getSelectedItems().forEach(function(elem){selectedChannels.push(elem.value)});
                // save the selected channels
                prefs.setStringPref("slack.selected.channels",JSON.stringify(selectedChannels));
                var message = msgField.$element.value();
                if( "" == title )
                {
                    prefs.deletePref("slack.title");
                    title = null;
                }
                else
                {
                    prefs.setStringPref("slack.title", title);
                }
                params.title = title;
                params.channels = selectedChannels.join(",");
                if( 0 >= params.channels.length )
                {
                    require("notify/notify").interact("Choose a channel.", "slack", {priority: "warn"});
                }
                else
                {
                    params.initial_comment = message;
                    slackAPI.post(params, callback);
                    panel.close();
                }
            }
            postButton.onCommand(post);
            panel.addRow(postButton)
            
            var closeButton = createCloseBtn();
            var close = function()
            {
                panel.close();
            }
            closeButton.onCommand(close);
            panel.addRow(closeButton)
            
             // Must retrieve the channels async as they might need to be retrieved
            // through an API call.
            function populateChannels(channels)
            {
                channels = channels.split(",");
                // XXX This preselects but it doesn't actually select some
                // it seems to break the items that don't end up getting
                // selected
                var itemsToSelect = [];
                //Populate the list and create a list of items to select
                for ( var channel of channels ) {
                    var opts = {attributes:{label:channel,value:channel}}
                    var listitem = require("ko/ui/listitem").create(opts)
                    availableChannels.addListItem(listitem);
                    if( selectedChannels.indexOf(channel) > -1 )
                    {
                        itemsToSelect.push(listitem);
                    }
                }
                // now go through and select those items
                for ( var item of itemsToSelect ) {
                    availableChannels.selectItem(item.element, false);
                }
                // reset the list until it's repopulated during post process
                selectedChannels = []; 
                availableChannels.enable();
                postButton.enable();
            }
            slackAPI.getChannels(populateChannels);            
        }
        catch(e)
        {
            console.log(e);
            panel.close();
        }
    }
}).apply(module.exports);