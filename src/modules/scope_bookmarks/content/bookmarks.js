(function() {
    const log       = require("ko/logging").getLogger("commando-scope-bookmarks")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");

    var local = {};

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var editor = function()
    {
        if ( ! ("editor" in local))
            local.editor = require('ko/editor');
        return local.editor;
    }

    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");

        var view = ko.views.manager.currentView;
        var bookmarks = editor().getAllMarks();
        var results = [];

        for (let line in bookmarks)
        {
            if (query != "" && query != line && bookmarks[line].indexOf(query) == -1)
                continue;

            results.push({
                classList: "compact",
                id: view.uid + line,
                name: "line " + line,
                description: bookmarks[line],
                icon: "koicon://ko-svg/chrome/icomoon/skin/arrow-right14.svg",
                scope: "scope-bookmarks",
                allowMultiSelect: false,
                data: {
                    line: line
                }
            });
        }

        log.debug(uuid + " " + results.length + " results");

        if (results.length)
            commando.renderResults(results, uuid);

        onComplete(uuid);
    }

    this.onSelectResult = function(selectedItems)
    {
        var item = selectedItems.slice(0)[0];
        var line = item.resultData.data.line;
        var e = editor();

        e.setCursor(e.getLineEndPos(line));

        commando.hideCommando();
        ko.commands.doCommandAsync('cmd_focusEditor');
    }

}).apply(module.exports);
