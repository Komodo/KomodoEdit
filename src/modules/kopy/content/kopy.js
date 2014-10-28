(function() {
    const log       = require("ko/logging").getLogger("kopy");
    const {Cc, Ci}  = require("chrome");
    const prefs     = ko.prefs;
    const menu      = require("ko/menu");
    const commands  = require("ko/commands");
    const editor    = require("ko/editor");

    var context = [
        {
            select: menu.context.editorContext,
            after: "#editor-context-makeSnippet"
        }
    ];

    this.load = function()
    {
        commands.register("kopy", this.share.bind(this, undefined), {
            label: "kopy: Share Code via kopy.io"
        });

        menu.register({
            id: "kopy",
            label: "Share Code via kopy.io",
            image: "chrome://kopy/skin/icon.png",
            command: ko.commands.doCommandAsync.bind(ko.commands, "cmd_kopy"),
            context: context
        });

        require("notify/notify").categories.register("kopy",
        {
            label: "kopy.io Integration"
        });
    }

    this.unload = function()
    {
        menu.unregister("kopy", context);
    }

    this.share = function(data, language)
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

        if ( ! data)
        {
            if ( ! editor.available())
            {
                locale = "Please enter the code that you would like to share"; // todo: localize
                data = require("ko/dialogs").prompt(locale, {});

                if ( ! data) return;
            }
            else
            {
                data = editor.getSelection();
                if (data == "")
                {
                    data = editor.getValue();
                }
                language = editor.getLanguage();
            }
        }

        if ( ! language)
        {
            language = 'null';
        }

        var params = require("sdk/querystring").stringify(
        {
            data: data,
            language: language,
            scheme: prefs.getStringPref("editor-scheme").replace(/\-(dark|light)$/, '.$1')
        });

        var baseUrl = ko.prefs.getString("kopy_baseurl", "http://kopy.io");
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
                var msg = "URL copied to keyboard: " + url;
                require("notify/notify").send(msg, "kopy",
                {
                    command: () => { ko.browse.openUrlInDefaultBrowser(url) }
                });
            }

            if (showInBrowser)
            {
                ko.browse.openUrlInDefaultBrowser(url);
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
