(function()
{
    
    const api = require("ko/share/slack/api");
    const ss = require("ko/simple-storage").get("slack");
    const log = require("ko/logging").getLogger("slack/dialog");
    
    var panel;
    var elem = {};
    
    /**
     * Trigger a dialog for a user to fill in fields for posting to slack
     * Asks for (* means madatory):
     *   Title (Defaults to `   ` of `filename-snippet`, if changed gets saved to prefs)
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
    this.create = function(params, callback)
    {
        // Have to open the panel before appending anything
        // XXX this should check for a panel and not recreate it if it already
        // exists.
        panel = require("ko/ui/panel").create({
            attributes: {
                backdrag: true,
                noautohide: true,
                width: "400px",
                class: "dialog"
            }
        });
        panel.open();
        panel.on("popuphidden", this.close); // ensure the panel doesnt stick around
        
        var title = params.title || ss.storage.title || "";
        elem.titleField = createTitleField(title);
        panel.addRow(elem.titleField);

        elem.titleRstBtn = createTitleResetBtn();
        panel.addRow(elem.titleRstBtn);
        
        elem.availableChannels = createChannelField();
        panel.addRow(elem.availableChannels);
        
        var selectedChannels = [];
        if (ss.storage.selectedChannels) 
        {
            selectedChannels = ss.storage.selectedChannels;
        }

        elem.msgField = createMsgField();
        panel.addRow(elem.msgField);
        
        elem.useClipboard = createUseClipboard();
        panel.addRow(elem.useClipboard);
        
        elem.showInBrowser = createShowInBrowser();
        panel.addRow(elem.showInBrowser);
        
        elem.postButton = createPostBtn();
        elem.postButton.onCommand(onPost.bind(this, callback));
        panel.addRow(elem.postButton);
        
        elem.closeButton = createCloseBtn();
        elem.closeButton.onCommand(this.close);
        panel.addRow(elem.closeButton);
        
        // Must retrieve the channels async as they might need to be retrieved
        // through an API call.
        var populateChannels = function (channels)
        {
            // XXX This preselects but it doesn't actually select some
            // it seems to break the items that don't end up getting
            // selected
            //Populate the list and create a list of items to select
            for ( let channel of channels ) {
                let opts = {attributes:{label:channel,value:channel}};
                let listitem = require("ko/ui/listitem").create(opts);
                elem.availableChannels.addListItem(listitem);
                if( selectedChannels.indexOf(channel) > -1 )
                {
                    elem.availableChannels.selectItem(listitem.element, false);
                }
            }
            elem.availableChannels.enable();
            elem.postButton.enable();
        };
        api.getChannels(populateChannels);
    }
    
    this.close = function() 
    {
        panel.close();
    };
    
    function onPost(callback)
    {
        params.title = elem.titleField.value();
        params.initial_comment = msgField.value();
        
        var selectedChannels = []; 
        availableChannels.getSelectedItems().forEach(function(elem){selectedChannels.push(elem.value);});
        ss.storage.selectedChannels = selectedChannels;
        params.channels = selectedChannels.join(",");
        
        ss.storage.useClipboard = useClipboard.checked();
        ss.storage.showInBrowser = showInBrowser.checked();
        
        if ( ! params.channels.length)
        {
            require("notify/notify").interact("Choose must choose at least one channel", "slack", {priority: "warn"});
        }
        else
        {
            var disabled = [];
            for (let k in elems)
            {
                if ("disable" in elems[k])
                {
                    elems[k].disable();
                    disabled.push(elems[k]);
                }
            }
            
            api.post(params, function(code, respText)
            {
                for (let elem of disabled)
                    elem.enable();
                    
                onPostComplete(code, respText, callback);
            }.bind(this));
        }
    }
    
    function onPostComplete(code, respText, callback)
    {
        /** Write a proper callback that handles results from the API using
         * notify.  See errors section for API function:
         *   https://api.slack.com/methods/files.upload
         */
        var respJSON;
        try
        {
            respJSON = JSON.parse(respText);
        } catch(e)
        {
            log.error("Could not parse response from server: " + e);
            callback(false);
            return;
        }
        
        if( respJSON.ok )
        {
            var file = respJSON.file;
            var url = file.permalink;
            
            if (ss.storage.useClipboard)
            {
                require("sdk/clipboard").set(url);
            }
            
            if (ss.storage.showInBrowser)
            {
                ko.browse.openUrlInDefaultBrowser(url);
            }
            
            log.debug("code: "+code+"\nResponse: "+respText);
            callback(true);
            this.close();
        }
        else
        {
            log.warn(locale + "\n" + respText);
            callback(false, code, respText);
        }
    }
    
    // Title text field
    function createTitleField(title)
    {
        var options = { attributes:
        {
            id:"slackTitle",
            type:"autocomplete",
            value: title,
            defaultValue: title,
            label:"Title:",
            col: 120,
        }};
        return require("ko/ui/textbox").create(options);
    }
    
    // Title reset button
    function createTitleResetBtn()
    {
        function resetTitle()
        {
            // This won't do `filename-snippet.js`. Lame but when I'm in the
            // panel I no longer have access to getFilename. I can't make it
            // public just for that.
            require("ko/dom")("#slackTitle").element().reset();
        }
        var resetBtn =  require("ko/ui/button").create( {attributes: { label:"Reset Title"} });
        resetBtn.onCommand(resetTitle);
        return resetBtn;
    }

    // Channel selection list        
    function createChannelField()
    {
        var options = { attributes:
            {
                label:"Channels",
                value:"Loading...",
                disabled:"true",
                seltype:"multiple"
            }
        };
        var availableChannels = require("ko/ui/listbox").create(options);
        availableChannels.disable();
        return availableChannels;
    }

    function createUseClipboard()
    {
        var elem = require("ko/ui/checkbox").create("Add Slack URL to Clipboard");
        elem.checked( ss.storage.useClipboard ? true : false );
        return elem;
    }
    
    function createShowInBrowser()
    {
        var elem = require("ko/ui/checkbox").create("Open slack after posting content. Does not work for desktop App.");
        elem.checked( ss.storage.showInBrowser ? true : false );
        return elem;
    }
    
    // Message Text field
    function createMsgField() {
        var options = {
            attributes:
            {
                type:"autocomplete",
                label:"Message:",
                multiline:true,
                rows: 3,
                col: 120
            }
        };
        return require("ko/ui/textbox").create(options);
    }

    // Post button
    function createPostBtn()
    {
       return require("ko/ui/button").create({attributes:{label:"Post",disabled:true}});
    }
    
    // Close Button
    function createCloseBtn()
    {
        return require("ko/ui/button").create({attributes:{label:"Close"}});
    }
    
}).apply(module.exports);