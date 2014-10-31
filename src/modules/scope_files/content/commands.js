(function() {
    const log       = require("ko/logging").getLogger("commando-scope-files-expand");
    const commando  = require("commando/commando");
    log.setLevel(require("ko/logging").LOG_DEBUG);

    var entries = [
        {
            id: "cut",
            name: "Cut",
            scope: "scope-files",
            command: function() {}
        },
        {
            id: "copy",
            name: "Copy",
            scope: "scope-files",
            command: function() {}
        },
        {
            id: "rename",
            name: "Rename",
            scope: "scope-files",
            command: doRename
        }
    ];

    this.onSearch = function(query, uuid, onComplete)
    {
        //commando.renderResults(commando.filter(entries, query), uuid);
        onComplete()
    }

    function doRename()
    {
        var item = commando.getSubscope();
        require("ko/file").rename(item.data.path);
    }

}).apply(module.exports);
