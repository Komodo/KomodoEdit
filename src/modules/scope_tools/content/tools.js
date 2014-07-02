(function() {
    const log       = require("ko/logging").getLogger("commando-scope-tools")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const prefs     = ko.prefs;

    const tbSvc     = Cc["@activestate.com/koToolbox2Service;1"]
                        .getService(Ci.koIToolbox2Service);

    var local = {};

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var searchTools = function(query, uuid)
    {
        log.debug(uuid + " - Searching Tools");
        // Get ordered list of best language scope (a *list* for
        // multi-language files).
        var currView = ko.views.manager.currentView;
        var langs = [];
        if (currView && currView.koDoc)
        {
            var koDoc = currView.koDoc;
            langs.push(koDoc.subLanguage);  // lang at current cursor position

            if (langs.indexOf(koDoc.language) === -1)
                langs.push(koDoc.language);

            currView.koDoc.languageObj.getSubLanguages({}).forEach(function(lang)
            {
                if (langs.indexOf(lang) === -1)
                    langs.push(lang);
            });
        }

        var tools = [];
        var results = tbSvc.findTools(query, langs.length, langs, {});
        for (let k in results)
        {
            let result = results[k];

            tools.push({
                classList: "compact",
                id: result.path_id,
                name: result.name,
                description: result.type + " - " + result.subDir,
                icon: result.iconUrl,

                scope: "scope-tools",
                data: {
                    type: "tool",
                    tool: result
                }
            });
        }

        commando.renderResults(tools, uuid);
    }

    var searchCommands = function(query, uuid)
    {
        log.debug(uuid + " - Searching Commands");

        if (!local.commands)
        {
            local.commands = [];
            var desc;
            var commandname;

            if (!ko.keybindings.manager.commanditems)
            {
                // Load the keybinding description information.
                ko.keybindings.manager.parseGlobalData();
            }

            var commanditems = ko.keybindings.manager.commanditems;
            for (var i=0; i < commanditems.length; i++)
            {
                commandname = commanditems[i].name;
                desc = commanditems[i].desc;
                if (!commandname || !desc) continue;
                local.commands.push({
                    classList: "compact",
                    id: commandname,
                    name: desc,
                    description: commandname,
                    icon: "chrome://fugue/skin/icons/external.png",
                    scope: "scope-tools",
                    data: {
                        type: "command"
                    }
                });
            }
        }

        var commands = local.commands.slice(); // clone
        query = query.toLowerCase();
        var words = query.split(" ");
        
        // Filter out empty word entries.
        words = words.filter(function(w) !!w);
        if (words)
        {
            commands = commands.filter(function(command)
            {
                var text = (command.id + command.name).toLowerCase();
                if (words.every(function(w) text.indexOf(w) != -1))
                {
                    return true;
                }
                return false;
            });
        }

        commando.renderResults(commands, uuid);
    }

    this.onSearch = function(query, uuid)
    {
        log.debug(uuid + " - Starting Scoped Search");

        searchTools(query, uuid);
        searchCommands(query, uuid);
    }

    this.onSelectResult = function(selectedItems)
    {
        log.debug("Invoking Tools");

        var uris = []
        for (let item in selectedItems)
        {
            let resultData = selectedItems[item].resultData;
            try {
                if (resultData.data.type == "command")
                {
                    log.debug("Invoking command: " + resultData.id);
                    ko.commands.doCommandAsync(resultData.id);
                }
                else
                {
                    // Brute force async
                    setTimeout(function() {
                        log.debug("Invoking tool: " + resultData.id);
                        ko.toolbox2.invokeTool(resultData.data.koTool);
                    }, 0)
                }
            } catch(e) {
                log.exception(e, "Failed to invoke tool: ");
            }
        }

        commando.hideCommando();
    }

}).apply(module.exports);
