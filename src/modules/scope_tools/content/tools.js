(function() {
    const log       = require("ko/logging").getLogger("commando-scope-tools")
    const commando  = require("commando/commando");
    const timers    = require("sdk/timers");
    const {Cc, Ci}  = require("chrome");
    const prefs     = ko.prefs;

    const tbSvc     = Cc["@activestate.com/koToolbox2Service;1"]
                        .getService(Ci.koIToolbox2Service);

    var local = {};

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");

        var subscope = commando.getSubscope();
        if ( ! subscope && query == '')
        {
            this.showToolCategories(uuid, onComplete);
            return;
        }

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

        var type = "";
        if (subscope)
            type = subscope.data.type;

        var tools = [];
        tbSvc.findToolsAsync(query, langs.length, langs, type, function(code, results)
        {
            for (let k in results)
            {
                let result = results[k];
                let description = result.type;

                if (result.subDir)
                    description += " - " + result.subDir;

                tools.push({
                    classList: "compact",
                    id: result.path_id,
                    name: result.name,
                    description: description,
                    icon: result.iconUrl,

                    scope: "scope-tools",
                    data: {
                        tool: result
                    },

                    allowMultiSelect: false
                });
            }

            if (results.length)
                commando.renderResults(tools, uuid);

            onComplete();
        });
    }

    this.showToolCategories = function(uuid, onComplete)
    {
        var categories = [
            {
                id: "command",
                name: "Commands",
            },
            {
                id: "snippet",
                name: "Snippets",
            },
            {
                id: "template",
                name: "Templates",
            },
            {
                id: "folder_template",
                name: "Folder Templates",
            },
            {
                id: "tutorial",
                name: "Tutorials",
            },
            {
                id: "macro",
                name: "Userscripts",
            },
            {
                id: "url",
                name: "URL",
            },
        ];

        var results = [];
        for (let category of categories)
        {
            results.push({
                id: "tool-category-" + category.id,
                name: category.name,
                icon: "chrome://komodo/skin/images/toolbox/"+category.id+".svg?size=14",
                scope: "scope-tools",
                isScope: true,
                data: { type: category.id },
                allowMultiSelect: false
            });
        }

        commando.renderResults(results, uuid);
        onComplete();
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
                timers.setTimeout(function()
                           {
                    log.debug("Invoking tool: " + resultData.id);
                    ko.toolbox2.invokeTool(resultData.data.tool.koTool);
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
