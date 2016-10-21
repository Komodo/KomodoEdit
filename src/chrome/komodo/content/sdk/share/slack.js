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
            filetype: fileType,
            title: filename
        };
        
        dialog.create(params, function(isSuccesful/*, code, responseText*/)
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