(function() {
    const log       = require("ko/logging").getLogger("commando-scope-openfiles")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");

    const partSvc   = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
    const ioService = Cc["@mozilla.org/network/io-service;1"].getService(Ci.nsIIOService);

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    this.onShow = function()
    {
        commando.search("");
    }

    this.onSearch = function(query, uuid)
    {
        log.debug(uuid + " - Starting Scoped Search");

        var curProject = partSvc.currentProject;

        if (curProject)
            var curPath = curProject.liveDirectory;
        else
            var curPath = ioService.newURI(ko.places.getDirectory(), null, null).path;

        var editorViews = ko.views.manager.getAllViews();
        for (let editorView of editorViews)
        {
            var fullPath = editorView.koDoc.file ? editorView.koDoc.file.path : '';
            var path = fullPath.indexOf(curPath) === 0 ? fullPath.substr(curPath.length) : fullPath;

            if (path.toLowerCase().indexOf(query.toLowerCase()) == -1 &&
                editorView.title.toLowerCase().indexOf(query.toLowerCase()) == -1)
                continue;

            // Todo: Normalize weight?
            var weight = editorView.koDoc.fileAccessNo;
            weight += editorView.koDoc.fileLastAccessed;

            var words = query.split(/\s+/);
            for (let word of words)
            {
                if (path.indexOf(word))
                    weight += 1000;
            }

            commando.renderResult({
                id: editorView.uid.number,
                name: editorView.title,
                description: path, // todo: highlight matched portions
                icon: "moz-icon://" + path + "?size=32",
                weight: weight,
                scope: "scope-openfiles",
                data: {
                    editorView: editorView
                },
                allowMultiSelect: false
            }, uuid);
        }
    }

    this.sort = function(current, previous)
    {
        if ( ! current || ! previous) return 0;
        return previous.name.localeCompare(current.name) > 0 ? 1 : -1;
    }

    this.onSelectResult = function(selectedItems)
    {
        let data = selectedItems.slice(0)[0].resultData.data;
        window.xtk.domutils.fireEvent(
            data.editorView.parentNode._tab,
            'click'
        );
        commando.hideCommando();
    }

}).apply(module.exports);
