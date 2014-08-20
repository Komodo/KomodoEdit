(function() {
    const log       = require("ko/logging").getLogger("commando-scope-tools")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const prefs     = ko.prefs;

    const tbSvc     = Cc["@activestate.com/koToolbox2Service;1"]
                        .getService(Ci.koIToolbox2Service);

    var local = {};

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    this.onShow = function()
    {
        commando.search("");
    }

    this.onSearch = function(query, uuid, onComplete = null)
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

        var tools = [];
        var results = tbSvc.findToolsAsync(query, langs.length, langs, function(code, results)
        {
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
                        tool: result
                    },

                    allowMultiSelect: false
                });
            }

            commando.renderResults(tools, uuid);

            if (onComplete)
                onComplete(uuid);
            else
                commando.onSearchComplete(uuid);
        });
    }

    this.onSelectResult = function(selectedItems)
    {
        log.debug("Invoking Tools");

        var uris = [];
        for (let item in selectedItems)
        {
            let resultData = selectedItems[item].resultData;
            try
            {
                // Brute force async
                setTimeout(function()
                           {
                    log.debug("Invoking tool: " + resultData.id);
                    ko.toolbox2.invokeTool(resultData.data.koTool);
                }, 0)
            }
            catch(e)
            {
                log.exception(e, "Failed to invoke tool: ");
            }
        }

        commando.hideCommando();
    }

}).apply(module.exports);
