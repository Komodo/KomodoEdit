(function() {
    const log       = require("ko/logging").getLogger("commando-scope-commands")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const prefs     = ko.prefs;

    var local = {};

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");

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
                    scope: "scope-commands",
                    allowMultiSelect: false
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

        if (commands.length)
            commando.renderResults(commands, uuid);

        onComplete();
    }

    this.onSelectResult = function(selectedItems)
    {
        log.debug("Invoking Commands");

        var uris = []
        for (let item in selectedItems)
        {
            let resultData = selectedItems[item].resultData;
            try {
                log.debug("Invoking command: " + resultData.id);
                ko.commands.doCommandAsync(resultData.id);
            } catch(e) {
                log.exception(e, "Failed to invoke command: ");
            }
        }

        commando.hideCommando();
    }

}).apply(module.exports);
