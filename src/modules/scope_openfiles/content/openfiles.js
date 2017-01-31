(function() {
    const log       = require("ko/logging").getLogger("commando-scope-openfiles")
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    
    const partSvc   = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);

    //log.setLevel(require("ko/logging").LOG_DEBUG);

    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");

        var curProject = partSvc.currentProject;
        var curPath, curPrefix;

        if (curProject)
        {
            curPath = curProject.liveDirectory;
            curPrefix = curProject.name.split(".")[0];
        }
        else
        {
            curPath = ko.uriparse.URIToPath(ko.places.getDirectory());
            curPrefix = _basename(curPath);
        }

        var editorViews = ko.views.manager.getAllViews();
        for (let editorView of editorViews)
        {
            let descriptionPrefix = false;
            let fullPath = editorView.koDoc.file ? editorView.koDoc.file.path : '';
            let path = fullPath;
            if (fullPath.indexOf(curPath) === 0)
            {
                path = fullPath.substr(curPath.length);
                descriptionPrefix = curPrefix;
            }

            if (path.toLowerCase().indexOf(query.toLowerCase()) == -1 &&
                editorView.title.toLowerCase().indexOf(query.toLowerCase()) == -1)
                continue;
            
            // weight can't be more than this
            // we want to leave 100 for more relevant scopes
            var totalWeight = 80;
            
            var weight = 0;
            var words = query.split(/\s+/);
            var weightPerHit = totalWeight / words.length;
            
            for (let word of words)
            {
                if (path.indexOf(word) != -1)
                    weight += weightPerHit;
            }

            commando.renderResult({
                id: editorView.uid.number,
                name: editorView.title,
                description: path, // todo: highlight matched portions
                icon: "koicon://" + path + "?size=14",
                classList: "small-icon",
                weight: weight,
                scope: "scope-openfiles",
                descriptionPrefix: descriptionPrefix,
                data: {
                    editorView: editorView
                },
                allowMultiSelect: false
            }, uuid);
        }

        onComplete();
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
    
    var _basename = function(str)
    {
        var system  = require("sdk/system");
        var sep     = system.platform == "winnt" ? "\\" : "/";
        return str.split(sep).pop();
    }

}).apply(module.exports);
