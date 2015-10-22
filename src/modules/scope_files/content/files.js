(function() {
    const log       = require("ko/logging").getLogger("commando-scope-files");
    const commando  = require("commando/commando");
    const {Cc, Ci}  = require("chrome");
    const system    = require("sdk/system");
    const ioFile    = require("sdk/io/file");
    const $         = require("ko/dom");
    const sep       = system.platform == "winnt" ? "\\" : "/";
    const isep      = sep == "/" ? /\\/g : /\//g;
    const pathsep   = system.platform == "winnt" ? ":" : ";";

    const scope     = Cc["@activestate.com/commando/koScopeFiles;1"].getService(Ci.koIScopeFiles);
    const partSvc   = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
    const ioService = Cc["@mozilla.org/network/io-service;1"].getService(Ci.nsIIOService);
    const prefs     = require("ko/prefs");

    //log.setLevel(require("ko/logging").LOG_DEBUG);
    var activeUuid = null;

    var local = {warned: {}};

    var init = function()
    {
        $(window).on("folder_touched", require("contrib/underscore").debounce(function(e)
        {
            scope.deleteCachePath(e.detail.path);

            if (commando.getScope().handler == "scope-files/files")
            {
                commando.reSearch();
                if (commando.isOpen()) commando.focus();
            }
        }, 100));
    };

    // Shortcut cache variables.
    var shortcutsVersion = -1;
    var shortcutsCache = {};
    
    this.clearShortcutCache = function()
    {
        shortcutsVersion = -1;
    }

    var getShortcuts = function()
    {
        // Reload shortcuts when a change is detected.
        var koDoc = ko.views.manager.currentView ? ko.views.manager.currentView.koDoc : {};
        var koFile = koDoc.file || {};
        var scopeVersion = scope.shortcutsVersion + (koFile.path || "");
        if (shortcutsVersion != scopeVersion) {
            log.debug("Updating shortcut cache");

            try
            {
                shortcutsCache = JSON.parse(scope.getShortcutsAsJson());
            } catch (e)
            {
                log.exception(e);
                shortcutsCache = {};
            }
            shortcutsVersion = scopeVersion;

            var spref = prefs.getPref("scope-files-shortcuts");

            for (let x=0;x<spref.length;x++)
            {
                let [shortcut, path] = spref.getString(x).split(":");
                shortcutsCache[shortcut] = path;
            }

            if ("baseName" in koFile)
            {
                log.debug("Including koDoc.file shorcuts");
                shortcutsCache["%d"] = ioFile.basename(koFile.dirName);
                shortcutsCache["%D"] = koFile.dirName;
            }

            var url = require("sdk/url");
            var curProject = partSvc.currentProject;
            if (curProject)
            {
                log.debug("Including curProject shorcuts");
                shortcutsCache["%i"] = curProject.liveDirectory;
                shortcutsCache["%P"] = url.URL(curProject.url).path;
            }

            shortcutsCache["%w"] = url.URL(ko.places.getDirectory()).path;
        }

        if ( ! "observing" in getShortcuts)
        {
            log.debug("Adding shortcut pref observer");

            getShortcuts.observing = true;

            prefs.onChange("scope-files-shortcuts", function()
            {
                shortcutsVersion = -1;
            });
        }

        return shortcutsCache;
    }

    var parsePaths = function(query, subscope, opts)
    {
        query = query.replace(isep, sep); // force os native path separators

        log.debug("Parsing paths for query: " + query + ", and path: " + subscope.path);
        
        if (query == "") return [query, subscope, opts];
        
        var _query = query.split(sep); // Convert query to array (split by path separators)
        var recursive = _query.length >= 1 ? !! _query.slice(-1)[0].match(/^\W/) : false;
        
        // Shortcuts
        if (opts["allowShortcuts"]) {
            var shortcuts = getShortcuts();
            if (query.match(/^[\w~%_\-]+(?:\/|\\)/) && (_query[0] in shortcuts))
            {
                log.debug("Running query against shortcuts");
    
                query = query.replace(_query[0], shortcuts[_query[0]]);
                opts["allowShortcuts"] = false;
                opts["cacheable"] = false;
                return parsePaths(query, subscope, opts);
            }
        }

        // Absolute paths
        var dirname = _dirname(query);
        if (query.indexOf(sep) !== -1 && (_ioFile("exists", query) || _ioFile("exists", dirname)))
        {
            log.debug("Query is absolute");

            opts["recursive"] = recursive;
            opts["fullpath"] = true;
            opts["cacheable"] = false;
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

        var view = ko.views.manager.currentView;
        if (view && view.koDoc && view.koDoc.file)
        {
            // Relative paths
            var isRelative = query.substr(0,2) == ("." + sep) || query.substr(0,3) == (".." + sep);
            var url = require("sdk/url");
            var curProject = partSvc.currentProject;
            if (curProject)
            {
                log.debug("Including curProject shorcuts");
                shortcutsCache["%i"] = curProject.liveDirectory;
                shortcutsCache["%P"] = url.URL(curProject.url).path;
            }

            shortcutsCache["%w"] = url.URL(ko.places.getDirectory()).path;
            var curProject = partSvc.currentProject;
            
            var cwd = curProject ? curProject.liveDirectory : ko.uriparse.URIToPath(ko.places.getDirectory());
            if (opts["relativeFromCurrentView"]) {
                cwd = view.koDoc.file.dirName;
            }
            var relativePath = cwd + sep + query;
            dirname = _dirname(relativePath);
            if (isRelative && (_ioFile("exists", relativePath) || _ioFile("exists", dirname)))
            {
                log.debug("Query is relative");

                opts["recursive"] = recursive;
                opts["fullpath"] = true;
                opts["cacheable"] = false;
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

        return [query, subscope, opts]
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
            opts["cacheable"] = true;
        }
        else
        {
            return;
        }
        
        log.debug("Prepare - Path: "+ path +", Opts: " + JSON.stringify(opts));

        scope.buildCache(path, JSON.stringify(opts));
    }

    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");

        activeUuid = uuid;

        var opts = {
            "maxresults": ko.prefs.getLong("commando_search_max_results", 50),
            "allowShortcuts": ko.prefs.getBoolean("commando_allow_shortcuts", true),
            "relativeFromCurrentView": ko.prefs.getBoolean("commando_relative_from_currentview", false),
            "recursive": true,
            "usecache": true,
            "cacheable": true
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
            if ( ! ko.places || ! ko.places.manager)
            {
                log.warn("ko.places(.manager) has not yet been initialized, delaying search");
                return setTimeout(this.onSearch.bind(this, query, uuid, onComplete), 200);
            }
            
            var placesPath = ko.uriparse.URIToPath(ko.places.getDirectory());
            subscope = {name: ioFile.basename(placesPath), path: placesPath};
        }
        else
        {
            subscope.path = subscope.data.path;
            opts["cacheable"] = false;
        }

        [query, subscope, opts] = parsePaths(query, subscope, opts);

        if (query == "")
            opts["recursive"] = false;

        if ( ! opts['recursive'])
            opts["usecache"] = false;

        // Set includes/excludes.
        var opts_prefs = ((curProject && subscope.path.indexOf(curProject.liveDirectory) === 0) ?
                          curProject.prefset :
                          prefs);
        opts["excludes"] = opts_prefs.getString("import_exclude_matches");
        opts["includes"] = opts_prefs.getString("import_include_matches");

        opts["excludes"] = opts["excludes"] == "" ? [] : opts["excludes"].split(";");
        opts["includes"] = opts["includes"] == "" ? [] : opts["includes"].split(";");

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
                onComplete();
                return;
            }

            var folderIcon = "chrome://komodo/skin/images/folder-closed.png";
            if (system.platform == "darwin")
                folderIcon = "chrome://global/skin/dirListing/folder.png"
            if (system.platform == "linux")
                folderIcon = "moz-icon://stock/gtk-directory?size=16";

            var _results = [];
            var encodeURIComponent = window.encodeURIComponent;
            for (let x in results)
            {
                let entry = results[x];

                var [name, path, relativePath, type, description, weight] = entry;

                var descriptionComplex = "<html:div class=\"crop rtl\" xmlns:html=\"http://www.w3.org/1999/xhtml\">";
                descriptionComplex += "<html:span dir=\"ltr\">"+description+"</html:span></html:div>";

                _results.push({
                    id: path,
                    name: name,
                    description: relativePath,
                    icon: type == 'dir' ? folderIcon : "koicon://" + encodeURIComponent(name) + "?size=16",
                    isScope: type == 'dir',
                    weight: weight,
                    scope: "scope-files",
                    descriptionPrefix: subscope.name,
                    data: {
                        path: path,
                        type: type
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

    this.onExpandSearch = function(query, uuid, callback)
    {
        var commands = require("./commands");
        commands.onSearch(query, uuid, callback);
    }

    this.clearCache = function()
    {
        scope.emptyCache();
    }

    init();

}).apply(module.exports);
