(function() {
    const log       = require("ko/logging").getLogger("commando-scope-tools")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const prefs     = ko.prefs;

    const tbSvc     = Cc["@activestate.com/koToolbox2Service;1"]
                        .getService(Ci.koIToolbox2Service);

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    this.onSearch = function(query, uuid)
    {
        log.debug(uuid + " - Starting Scoped Search");

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

        var resultArr = [];
        var results = tbSvc.findTools(query, langs.length, langs, {});
        for (let k in results)
        {
            let result = results[k];

            resultArr.push({
                id: result.path_id,
                name: result.name,
                description: result.type + " - " + result.subDir,
                icon: result.iconUrl,

                data: {
                    tool: result
                }
            });
        }

        commando.renderResults(resultArr, uuid);
    }

    this.onSelectResult = function(selectedItems)
    {
        var uris = []
        for (let item in selectedItems)
        {
            let tool = selectedItems[item].resultData.data;
            try {
                if (tool instanceof CommandHit) {
                    ko.commands.doCommand(tool.commandId);
                } else {
                    ko.toolbox2.invokeTool(tool.koTool);
                }
            } catch(e) {
                log.exception(e, "Failed to invoke tool: ");
            }
        }

        commando.hideCommando();
    }

}).apply(module.exports);
