(function() {
    const log       = require("ko/logging").getLogger("commando-scope-openfiles");
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const legacy    = require("ko/windows").getMain().ko;
    
    const partSvc   = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
    
    this.isDirty = () => true;
    
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
            curPath = legacy.uriparse.URIToPath(legacy.places.getDirectory());
            curPrefix = _basename(curPath);
        }

        // Convert query to lowercase words
        let words = query.toLowerCase().split(/\s+/);

        var editorViews = legacy.views.manager.getAllViews();
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

            // Lowercase path and title
            let pathLower = path.toLowerCase();
            let titleLower = editorView.title.toLowerCase();

            // Find the trailing slash
            let pathSlashPos = pathLower.lastIndexOf("/");

            // weight can't be more than this
            // we want to leave 100 for more relevant scopes
            var totalWeight = 80;
            
            var weight = 0;
            var weightPerFilenameHit = totalWeight / words.length;
            var weightPerHit = 0.9 * weightPerFilenameHit;
            var noMatch = false;
            for (let word of words)
            {
                let pathIdx = pathLower.indexOf(word);
                if (pathIdx != -1)
                {
                    // Weight after the final slash more
                    weight += (pathIdx > pathSlashPos) ? weightPerFilenameHit : weightPerHit;
                }
                else if (titleLower.indexOf(word) != -1)
                    weight += weightPerHit;
                else
                {
                    noMatch = true;
                    break;
                }
            }
            if (noMatch)
                continue;

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
        commando.hide();
    }
    
    var _basename = function(str)
    {
        var system  = require("sdk/system");
        var sep     = system.platform == "winnt" ? "\\" : "/";
        return str.split(sep).pop();
    }

}).apply(module.exports);
