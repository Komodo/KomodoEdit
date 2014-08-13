(function() {
    const log       = require("ko/logging").getLogger("commando-scope-files");
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const system    = require("sdk/system");
    const ioFile    = require("sdk/io/file");
    const sep       = system.platform == "winnt" ? "\\" : "/";
    const isep      = sep == "/" ? /\\/g : /\//g;

    const scope     = Cc["@activestate.com/commando/koScopeFiles;1"].getService(Ci.koIScopeFiles);
    const partSvc   = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
    const ioService = Cc["@mozilla.org/network/io-service;1"].getService(Ci.nsIIOService);
    const prefs     = ko.prefs;

    //log.setLevel(require("ko/logging").LOG_DEBUG);
    var activeUuid = null;

    var local = {warned: {}};

    var getShortcuts = function()
    {
        if ( ! ("cached" in getShortcuts))
        {
            getShortcuts.cached =
            {
                "~":    system.pathFor("Home")
            };

            try
            {
                var xmlData = ioFile.open("~/.go/shortcuts.xml").read();
                var parser = new window.DOMParser();
                var xmlDom = parser.parseFromString(xmlData, "text/xml");
                var children = xmlDom.firstChild.children;
                for (var i = 0; i < children.length; i++)
                {
                    var child = children[i];
                    getShortcuts.cached[child.getAttribute("name")] = child.getAttribute("value");
                }
            }
            catch (e)
            {
                log.warn("Could not read gotool shortcuts.xml: " + e.message);
            }
        }

        return getShortcuts.cached;
    }

    var getShortcut = function(key)
    {
        var shortcuts = getShortcuts();
        return shortcuts[key] || false;
    }

    var parsePaths = function(query, subscope, opts)
    {
        query = query.replace(isep, sep); // force os native path separators
        
        if (query == "") return [query, subscope, opts];
        
        var _query = query.split(sep); // Convert query to array (split by path separators)
        var recursive = _query.length >= 1 ? !! _query.slice(-1)[0].match(/^\W/) : false;
        
        // Shortcuts
        var shortcuts = getShortcuts();
        if (query.match(/^[\w~%_\-]+(?:\/|\\)/) && (_query[0] in shortcuts))
        {
            log.debug("Running query against shortcuts");

            opts["recursive"] = recursive;
            subscope.path = shortcuts[_query[0]];
            subscope.name = _query[0];
            query = _query.slice(1);
            return [query, subscope, opts];
        }

        // Absolute paths
        var dirname = _dirname(query);
        log.debug(dirname);
        if (_ioFile("exists", query) || _ioFile("exists", dirname))
        {
            log.debug("Query is absolute");

            opts["recursive"] = recursive;
            opts["fullpath"] = true;
            subscope.name = "";

            if (query.substr(-1) == sep)
            {
                subscope.path = query;
                query = "";
            }
            else
            {
                subscope.path = dirname;
                query = ioFile.basename(query);
            }
            
            if (subscope.path.substr(-1) != sep) 
                subscope.path = subscope.path + sep
                
            return [query, subscope, opts];
        }

        // Relative paths
        var isRelative = query.substr(0,2) == ("." + sep) || query.substr(0,3) == (".." + sep);
        var relativePath = subscope.path + sep + query;
        dirname = _dirname(relativePath);
        if (isRelative && (_ioFile("exists", relativePath) || _ioFile("exists", dirname)))
        {
            log.debug("Query is relative");

            opts["recursive"] = recursive;
            opts["fullpath"] = true;
            subscope.name = "";

            if (query.substr(-1) == sep)
            {
                subscope.path = relativePath;
                query = "";
            }
            else
            {
                subscope.path = dirname;
                query = ioFile.basename(relativePath);
            }
            
            if (subscope.path.substr(-1) != sep) 
                subscope.path = subscope.path + sep

            return [query, subscope, opts];
        }

        return [query, subscope, opts];
    }

    // Call ioFile and return false instead of exceptions
    var _ioFile = function(fn)
    {
        try
        {
            return ioFile[fn].apply(ioFile, Array.prototype.slice.call(arguments, 1));
        }
        catch (e)
        {
            return false;
        }
    }
    
    var _basename = function(str)
    {
        return str.split(sep).pop();
    }
    
    var _dirname = function(str)
    {
        str = str.split(sep);
        str.pop();
        return str.join(sep);
    }

    this.prepare = function()
    {
        var opts = {};
        var curProject = partSvc.currentProject;
        if (curProject)
        {
            var path = curProject.liveDirectory;
            opts["excludes"] = curProject.prefset.getString("import_exclude_matches");
            opts["includes"] = curProject.prefset.getString("import_include_matches");

            opts["excludes"] = opts["excludes"] == "" ? [] : opts["excludes"].split(";");
            opts["includes"] = opts["includes"] == "" ? [] : opts["includes"].split(";");
        }
        else
        {
            return;
        }
        
        log.debug("Prepare - Path: "+ path +", Opts: " + JSON.stringify(opts));

        scope.buildCache(path, JSON.stringify(opts));
    }

    this.onShow = function()
    {
        commando.search("");
    }

    this.onSearch = function(query, uuid)
    {
        log.debug(uuid + " - Starting Scoped Search");

        activeUuid = uuid;

        var opts = {
            "maxresults": ko.prefs.getLong("commando_search_max_results", 100)
        }

        // Detect directory to search in
        var curProject = partSvc.currentProject;
        var subscope = commando.getSubscope();
        if ( ! subscope && curProject)
        {
            subscope = {name: curProject.name.split(".")[0], path: curProject.liveDirectory};
        }
        else if ( ! subscope)
        {
            var placesPath = ko.uriparse.URIToPath(ko.places.getDirectory());
            subscope = {name: ioFile.basename(placesPath), path: placesPath};
        }
        else
        {
            subscope.path = subscope.data.path;
        }

        [query, subscope, opts] = parsePaths(query, subscope, opts);

        if (query == "")
            opts["recursive"] = false;

        // Set includes/excludes, if relevant
        if (curProject && subscope.path.indexOf(curProject.liveDirectory) === 0)
        {
            opts["excludes"] = curProject.prefset.getString("import_exclude_matches");
            opts["includes"] = curProject.prefset.getString("import_include_matches");

            opts["excludes"] = opts["excludes"] == "" ? [] : opts["excludes"].split(";");
            opts["includes"] = opts["includes"] == "" ? [] : opts["includes"].split(";");
        }

        opts["weightMatch"] = prefs.getBoolean('commando_files_weight_multiplier_match', 30);
        opts["weightHits"] = prefs.getBoolean('commando_files_weight_multiplier_hits', 20);
        opts["weightDepth"] = prefs.getBoolean('commando_files_weight_multiplier_depth', 10);

        var _opts = JSON.stringify(opts);
        log.debug(uuid + " - Query: "+ query +", Path: "+ subscope.path +", Opts: " + _opts);

        scope.search(query, uuid, subscope.path, _opts, function(status, results)
        {
            if (activeUuid != uuid)
            {
                if ( ! (uuid in local.warned))
                {
                    log.debug(uuid + " - No longer the active search, don't pass result");
                    local.warned[uuid] = true;
                }
                return; // Don't waste any more time on past search queries
            }

            if (results == "done") // search complete
            {
                // Since python is multi-threaded, results might still be processed
                // Todo: find proper solution
                window.setTimeout(function()
                {
                    commando.onSearchComplete("scope-files", uuid);
                }, 100)
                return;
            }

            var _results = [];
            for (let x in results)
            {
                let entry = results[x];

                var [name, path, type, description, weight] = entry;

                description = "<html:em class=\"subscope\">"+subscope.name+"</html:em><html:div class=\"crop\"><html:span dir=\"ltr\">" + description + "</html:span></html:div>";

                _results.push({
                    id: path,
                    name: name,
                    description: description,
                    icon: type == 'dir' ? "chrome://komodo/skin/images/folder-32.png" : "koicon://" + path + "?size=32",
                    isScope: type == 'dir',
                    weight: weight,
                    scope: "scope-files",
                    classList: "subscope-crop",
                    data: {
                        path: path
                    },
                    allowMultiSelect: type != 'dir'
                });
            }

            commando.renderResults(_results, uuid);
        });
    }

    this.sort = function(current, previous)
    {
        if ( ! current || ! previous) return 0;
        return previous.name.localeCompare(current.name) > 0 ? 1 : -1;
    }

    this.onSelectResult = function(selectedItems)
    {
        log.debug("Opening Files");

        var uris = []
        for (let item in selectedItems)
        {
            item = selectedItems[item];
            // Todo be a bit more intelligent
            uris.push(ko.uriparse.pathToURI(item.resultData.data.path));
        }

        log.debug("Opening files: " + uris.join(", "));

        ko.open.multipleURIs(uris);

        commando.hideCommando();
    }

}).apply(module.exports);
