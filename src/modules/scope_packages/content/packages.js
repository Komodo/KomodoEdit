(function() {
    const {Cc, Ci, Cu} = require("chrome");
    const log          = require("ko/logging").getLogger("commando-scope-packages");
    const commando     = require("commando/commando");
    const dialog       = require("ko/dialogs");
    const _window      = require("ko/windows").getMain();
    const toolbox      = _window.ko.toolbox2;
    const utils        = _window.ko.utils;
    const prefs        = require("ko/prefs");
    const keybindings  = _window.ko.keybindings;
    const l            = require("ko/locale");
    
    // Import the XPI addon manager as "AddonManager".
    Cu.import("resource://gre/modules/AddonManager.jsm");
    // Import the HTTP downloader as "Downloads".
    Cu.import("resource://gre/modules/Downloads.jsm");
    // Import OS-specific file management as "OS".
    Cu.import("resource://gre/modules/osfile.jsm");
    // Import asynchronous task management for downloads as "Task".
    Cu.import("resource://gre/modules/Task.jsm");
    
    /** Locale bundle. */
    const bundle = Cc["@mozilla.org/intl/stringbundle;1"].getService(Ci.nsIStringBundleService).
        createBundle("chrome://scope-packages/locale/scope-packages.properties");
    
    /** The root directory for package archives. */
    const ROOT = prefs.getString("package_api_endpoint");
    
    /** The names of the files (no extension) that lists available packages of given kind. */
    const ADDONS = "addons";
    const TOOLBOX = "toolbox";
    const MACROS = "macros";
    const SCHEMES = "schemes";
    const SKINS = "skins";
    const KEYBINDS = "keybinds";
    const LANGS = "languages";
    
    this.ADDONS = ADDONS;
    this.TOOLBOX = TOOLBOX;
    this.MACROS = MACROS;
    this.SCHEMES = SCHEMES;
    this.SKINS = SKINS;
    this.KEYBINDS = KEYBINDS;
    this.LANGS = LANGS;
    
    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    //this.onShow = function()
    //{
    //    this._getInstalledPackagesByKind.cache = {};
    //}
    //
    //this.onSearch = function(query, uuid, onComplete)
    //{
    //    var done = 0;
    //    var installed, upgradeable;
    //    this._getInstalledPackages(function(packages)
    //    {
    //        installed = packages;
    //        if (++done == 2)
    //        {
    //            this._onSearch(query, uuid, onComplete, installed, upgradeable);
    //        }
    //    }.bind(this));
    //    
    //    this._getUpgradablePackages(function(packages)
    //    {
    //        upgradeable = upgradeable;
    //        if (++done == 2)
    //        {
    //            this._onSearch(query, uuid, onComplete, installed, upgradeable);
    //        }
    //    }.bind(this));
    //}
    
    /**
     * Start Commando using the package scope and select the given category
     */
    this.openCategory = function(kind)
    {
        var kinds = this.getPackageKinds();
        if ( ! kind in kinds)
        {
            log.error("Missing category: " + kind);
            return;
        }
        
        commando.show('scope-packages');
        commando.setSubscope();
        commando.setSubscope({
            id: kind,
            name: kinds[kind].locale,
            icon: kinds[kind].icon,
            isScope: true,
            scope: "scope-packages",
            data: {},
            allowMultiSelect: false
        });
    }
    
    //this._onSearch = function(query, uuid, onComplete, installed = {}, upgradeable = {})
    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");
        
        var kinds = this.getPackageKinds();
        var subscope = commando.getSubscope();
        if ( ! subscope && query == '')
        {
            // Kind listing
            for (let kind in kinds)
            {
                if ( ! kinds.hasOwnProperty(kind)) continue;
                commando.renderResult({
                    id: kind,
                    name: kinds[kind].locale,
                    icon: kinds[kind].icon,
                    weight: kinds[kind].weight,
                    isScope: true,
                    scope: "scope-packages",
                    data: {},
                    allowMultiSelect: false
                }, uuid);
                onComplete();
            }
            return;
        }
        
        // Scoped search
        var caller = this._getAvailablePackages.bind(this);
        if (subscope)
            caller = this._getAvailablePackagesByKind.bind(this, subscope.id)
            
        caller(function(packages) {
            if ( ! packages) return onComplete();
            
            if (query.length)
                packages = commando.filter(packages, query);
            
            for (let name in packages)
            {
                if ( ! packages.hasOwnProperty(name)) continue;
                let pkg = packages[name];
                try
                {
                    //var icon = "koicon://ko-svg/chrome/icomoon/skin/circle.svg";
                    //if (pkg.name in installed)
                    //    icon = "koicon://ko-svg/chrome/icomoon/skin/checkmark-circle2.svg";
                    //if (pkg.name in upgradeable)
                    //    icon = "koicon://ko-svg/chrome/icomoon/skin/arrow-up13.svg";
                    commando.renderResult({
                        id: pkg.id,
                        name: pkg.name,
                        description: pkg.description,
                        descriptionPrefix: subscope ? undefined : kinds[pkg.kind].locale + " /",
                        scope: "scope-packages",
                        data: {
                            package: pkg,
                            //installed: pkg.name in installed,
                            //upgradeable: pkg.name in upgradeable
                        },
                        allowMultiSelect: false
                    }, uuid);
                }
                catch (e)
                {
                    log.exception(e, "Failed parsing package info");
                }
            }
            
            // If searching with a subscope there will only be one callback
            if (subscope) onComplete();
        });
    }
    
    this.onSelectResult = function()
    {
        var result = commando.getSelectedResult();
        
        require("notify/notify").send(l.get("installing", result.name), "packages", {id: "packageInstall"});
        
        commando.block();
        this._installPackage(result.data.package, function()
        {
            require("notify/notify").send(l.get("installed", result.name), "packages", {id: "packageInstall"});
            commando.unblock();
            commando.hide();
        });
    }
    
    this.sort = function(current, previous)
    {
        return previous.name.localeCompare(current.name) > 0 ? 1 : -1;
    }
    
    // Package Logic.
    
    /**
     * Helper function that repeats a function call for each package kind 
     */
    this._getPackageIterator = function(method, callback)
    {
        var total = 0;
        var kinds = this.getPackageKinds();
        for (let _kind in kinds)
        {
            if ( ! kinds.hasOwnProperty(_kind)) continue;
            total++;
        }
        
        for (let _kind in kinds)
        {
            if ( ! kinds.hasOwnProperty(_kind)) continue;
            this[method](_kind, function(results)
            {
                callback(results);
                total = total - 1;
                if (total === 0) callback();
            });
        }
    }
    
    /**
     * All package kinds supported.
     * Calling `_getAvailablePackages()` individually with each of these would
     * yield every package currently available.
     */
    this.getPackageKinds = function()
    {
        if ("__cached" in this.getPackageKinds)
            return this.getPackageKinds.__cached;
        
        var results = {};
        results[ADDONS] = {
            locale: l.get(ADDONS),
            icon: "koicon://ko-svg/chrome/icomoon/skin/plus-circle2.svg",
            weight: 10
        };
        results[MACROS] = {
            locale: l.get(MACROS),
            icon: "koicon://ko-svg/chrome/icomoon/skin/play3.svg",
            weight: 9
        };
        results[TOOLBOX] = {
            locale: l.get(TOOLBOX),
            icon: "koicon://ko-svg/chrome/icomoon/skin/briefcase3.svg",
            weight: 8
        };
        results[SCHEMES] = {
            locale: l.get(SCHEMES),
            icon: "koicon://ko-svg/chrome/icomoon/skin/text-color.svg",
            weight: 7
        };
        results[SKINS] = {
            locale: l.get(SKINS),
            icon: "koicon://ko-svg/chrome/icomoon/skin/palette.svg",
            weight: 6
        };
        results[LANGS] = {
            locale: l.get(LANGS),
            icon: "koicon://ko-svg/chrome/icomoon/skin/globe2.svg",
            weight: 5
        };
        results[KEYBINDS] = {
            locale: l.get(KEYBINDS),
            icon: "koicon://ko-svg/chrome/icomoon/skin/keyboard.svg",
            weight: 4
        };
        
        this.getPackageKinds.__cached = results;
        
        return results;
    }
    
    /**
     * Get all available packages from all kinds, this calls the callback
     * multiple times and will call it once with no arguments to indicate
     * that it is done fetching packages
     */
    this._getAvailablePackages = this._getPackageIterator.bind(this, '_getAvailablePackagesByKind');
    
    /**
     * Retrieves a dictionary of packages of the given kind that are available
     * for installing.
     * Keys are package names and values are package metadata. Package metadata
     * comes from Komodo's website:
     *     http://www.komodoide.com/json/*.json
     * where * is a kind, as described below.
     * This kind of package metadata can be passed to `_installPackage()` for
     * installing/upgrading. Useful fields are `name` and `description`.
     * @param kind The kind of package to request. (At this time, available
     *   kinds are ADDONS, TOOLBOX, MACROS, SCHEMES, SKINS, and KEYBINDS.)
     * @param callback The callback to call with the dictionary retrieved.
     */
    this._getAvailablePackagesByKind = function(kind, callback)
    {
        log.debug("Retrieving all packages for " + kind);
        
        // Check if this request is already cached and if the cache is recent
        // we don't want to be spamming the web server
        var time = Math.floor(Date.now() / 1000);
        if ( ! ("cache" in this._getAvailablePackagesByKind))
            this._getAvailablePackagesByKind.cache = {};
        var cache = this._getAvailablePackagesByKind.cache;
        if ((kind in cache) && (time - cache[kind].time) < 3600)
        {
            return callback(cache[kind].result);
        }
        
        // Not cached or cache has expired, get a fresh copy
        log.debug("Retrieving fresh copy");
        var ajax = require('ko/ajax');
        var url = ROOT + kind + '.json';
        ajax.get(url, function(code, response)
        {
            if (code != 200)
            {
                var msg = "Unable to retrieve package listing for " + kind;
                log.error(msg);
                require('notify/notify').send(msg, 'packages', {priority: 'error'});
                return;
            }
            var results = {};
            for (let pkg of JSON.parse(response))
            {
                pkg.kind = kind;
                if ( ! this._getInstallable(pkg)) continue;
                results[pkg.name] = pkg;
            }
            
            cache[kind] = {result: results, time: time};
            
            callback(results);
        }.bind(this));
    }
    
    /**
     * Get all installed packages from all kinds, this calls the callback
     * multiple times and will call it once with no arguments to indicate
     * that it is done fetching packages
     */
    this._getInstalledPackages = this._getPackageIterator.bind(this, '_getInstalledPackagesByKind');
    
    /**
     * Retrieves a dictionary of installed packages of the given kind.
     * Keys are package names and values are package metadata. Package metadata
     * contains `name`, `kind`, `description`, `version`, and `data` fields.
     * `data` is a kind-specific object. For example, for ADDONS, `data` is an
     * Addon object, for MACROS, `data` is the tool's ID in the toolbox, etc.
     * This kind of package metadata can be passed to `_uninstallPackage()` for
     * uninstalling. Useful fields are `name`, `description`, and `version`.
     * @param kind The kind of package to request. (At this time, available
     *   kinds are ADDONS, TOOLBOX, MACROS, SCHEMES, SKINS, and KEYBINDS.)
     * @param callback The callback to call with the dictionary retrieved.
     */
    this._getInstalledPackagesByKind = function(kind, callback)
    {
        log.debug("Retrieving all installed packages for " + kind);
        
        // Check if this request is already cached and if the cache is recent
        // this cache clears whenever commando shows and is just intended to reduce
        // CPU usage when someone is doing rapid subsequent searches
        var time = Math.floor(Date.now() / 1000);
        if ( ! ("cache" in this._getInstalledPackagesByKind))
            this._getInstalledPackagesByKind.cache = {};
        var cache = this._getInstalledPackagesByKind.cache;
        if ((kind in cache) && (time - cache[kind].time) < 3600)
        {
            return callback(cache[kind].result);
        }
        
        // Not cached or cache has expired, get a fresh copy
        log.debug("Retrieving fresh copy");
        switch (kind)
        {
            case ADDONS:
            case SKINS:
            case LANGS:
                // TODO: differentiate between these.
                // Retrieve installed XPIs via Mozilla's AddonManager.
                AddonManager.getAllAddons(function(aAddons)
                {
                    var packages = {};
                    for (let addon of aAddons)
                    {
                        let pkg = {};
                        pkg.name = addon.name;
                        pkg.kind = kind; // needed by _uninstallPackage()
                        pkg.description = addon.description;
                        pkg.version = addon.version;
                        pkg.data = addon; // needed by _uninstallPackage()
                        packages[pkg.name] = pkg;
                        //log.debug("Found " + pkg.name + " v" + pkg.version);
                    }
                    cache[kind] = {result: packages, time: time};
                    callback(packages);
                });
                break;
            case TOOLBOX:
            case MACROS:
                // TODO: differentiate between the two.
                // Retrieve installed toolbox items via Komodo's toolbox
                // manager.
                var view = toolbox.manager.view;
                var packages = {};
                for (let i = 0; i < view.rowCount; i++)
                {
                    // TODO: filter out default toolboxes and macros?
                    let pkg = {};
                    pkg.name = view.getTool(i).name;
                    pkg.kind = kind; // needed by _uninstallPackage()
                    pkg.data = i; // needed by _uninstallPackage()
                    packages[pkg.name] = pkg;
                    //log.debug("Found " + pkg.name);
                }
                cache[kind] = {result: packages, time: time};
                callback(packages);
                break;
            case SCHEMES:
            case KEYBINDS:
                // Retrieve installed schemes via Komodo's appropriate scheme
                // service.
                var serviceName = (kind == SCHEMES) ? 'koScintillaSchemeService' : 'koKeybindingSchemeService';
                var schemeService = Cc['@activestate.com/' + serviceName + ';1'].getService();
                var packages = {};
                var schemes = {};
                schemeService.getSchemeNames(schemes, {});
                for (let name of schemes.value)
                {
                    if ((kind == SCHEMES && !schemeService.getScheme(name).writeable) ||
                        (kind == KEYBINDS && !keybindings.manager.configurationWriteable(name)))
                    {
                        //log.debug("Scheme " + name + " is a default scheme (not writable); ignoring");
                        continue; // filter out default schemes
                    }
                    let pkg = {};
                    pkg.name = name;
                    pkg.kind = kind; // needed by _uninstallPackage()
                    packages[pkg.name] = pkg;
                    //log.debug("Found " + pkg.name);
                }
                cache[kind] = {result: packages, time: time};
                callback(packages);
                break;
            default:
                log.error("Unknown package kind: " + kind);
                return;
        }
    }
    
    /**
     * Get all upgradeable packages from all kinds, this calls the callback
     * multiple times and will call it once with no arguments to indicate
     * that it is done fetching packages
     */
    this._getUpgradablePackages = this._getPackageIterator.bind(this, '_getUpgradablePackagesByKind');
    
    /**
     * Retrieves a dictionary of upgradable packages of the given kind.
     * Keys are package names and values are package metadata. Package metadata
     * comes from Komodo's website:
     *     http://www.komodoide.com/json/*.json
     * where * is a kind, as described below.
     * This kind of package metadata can be passed to `_installPackage()` for
     * installing/upgrading.
     * @param kind The kind of package to request. (At this time, available
     *   kinds are ADDONS, TOOLBOX, MACROS, SCHEMES, SKINS, and KEYBINDS.)
     * @param callback The callback to call with the dictionary retrieved.
     */
    this._getUpgradablePackagesByKind = function(kind, callback)
    {
        this._getAvailablePackagesByKind(kind, function(available)
        {
            this._getInstalledPackagesByKind(kind, function(installed)
            {
                var upgradable = {};
                // Iterate over installed packages and check upstream to see if
                // any updates are available.
                for (let name in installed)
                {
                    let installedPkg = installed[name];
                    let upstreamPkg = available[name];
                    if (!upstreamPkg)
                    {
                        //log.debug("Installed package " + name + " does not exist upstream; ignoring.");
                        continue;
                    }
                    //log.debug("Installed package " + name + " exists upstream.");
                    // Verify the package has a release.
                    if (!(upstreamPkg.releases) || upstreamPkg.releases.length == 0)
                    {
                        //log.debug("Package has no upstream releases; ignoring.");
                        continue;
                    }
                    // Verify the package's latest release has an artifact.
                    // This is to ensure a package marked upgradable can
                    // actually download and apply an update.
                    let release = upstreamPkg.releases[0];
                    if (!(release.assets) || release.assets.length == 0)
                    {
                        //log.debug("Package has no upstream releases; ignoring.");
                        continue;
                    }
                    // Compare the versions and if the current version is not
                    // the upstream version, mark the package as upgradable.
                    // (Comparing versions is not possible due to the semantics
                    // of versioning and the fact that installedPkg cannot
                    // carry any meaningful version information.)
                    // TODO: some packages do not store version information
                    // (like macros and schemes). Figure out a more reliable way
                    // to determine whether or not updates are available.
                    if (installedPkg.version != release.name)
                    {
                        upgradable[name] = upstreamPkg;
                        //log.debug("Package has a newer version; marking as upgradable.");
                    }
                    else
                    {
                        //log.debug("Package is up to date.");
                    }
                }
                callback(upgradable);
            });
        }.bind(this));
    }
    
    /**
     * Installs the given package.
     * @param pkg A package object obtained via `_getAvailablePackages()`.
     * @param callback The callback to be called upon success.
     * @param errorCallback the Callback to be called upon failure. The first
     *   argument will be the error message.
     */
    this._installPackage = function(pkg, callback, errorCallback)
    {
        callback = callback || function() {};
        errorCallback = errorCallback || function(msg)
        {
            require('notify/notify').send(msg, 'packages', {priority: 'error'}); 
        };
        
        // Verify if the package has any installable assets
        var asset = this._getInstallable(pkg, 'asset');
        if ( ! asset)
        {
            log.info("No installable assets for package " + pkg.name + "; aborting.");
            errorCallback("No installable assets for package " + pkg.name);
            return;
        }
        
        // Determine the package's content type and act appropriately.
        log.debug("Package kind is " + pkg.kind);
        switch (pkg.kind)
        {
            case ADDONS:
            case SKINS:
            case LANGS:
                // TODO: differentiate between these and prompt for applying skin.
                // Install the XPI via Mozilla's AddonManager.
                AddonManager.getInstallForURL(asset.browser_download_url, function(aInstall)
                {
                    this._addonInstallListener.callback = callback;
                    this._addonInstallListener.errorCallback = errorCallback;
                    this._addonInstallListener.package = pkg;
                    aInstall.addListener(this._addonInstallListener);
                    aInstall.install();
                }.bind(this), asset.content_type);
                break;
            case TOOLBOX:
            case MACROS:
                // TODO: differentiate between the two.
                // Install the file via Komodo's toolbox service.
                this._downloadFile(asset.browser_download_url, function(file)
                {
                    var defaultPath = toolbox.getStandardToolbox().path;
                    log.debug("Importing " + file + " into toolbox " + defaultPath);
                    toolbox.manager.toolbox2Svc.importFiles(defaultPath, 1, [file]);
                    toolbox.manager.view.reloadToolsDirectoryView(-1); // for std toolbox
                    log.info("Package successfully installed.");
                    // TODO: prompt for running tutorials.
                    // TODO: delete temporary file.
                    callback();
                }, errorCallback);
                break;
            case SCHEMES:
                // Install the file via Komodo's color scheme service.
                this._downloadFile(asset.browser_download_url, function(file)
                {
                    log.debug("Importing " + file + " as scheme " + pkg.name);
                    var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
                    var scheme = schemeService.loadSchemeFromURI(file, pkg.name);
                    // Ask the user if the scheme should be applied immediately.
                    if (dialog.confirm(l.get("applyScheme.prompt"),
                        {
                            yes: l.get("applySchemeNow.label"),
                            no: l.get("applySchemeLater.label"),
                            response: l.get("applySchemeNow.label")
                        }))
                    {
                        schemeService.activateScheme(scheme);
                        require("notify/notify").send(l.get("schemeApplied", pkg.name), "packages", {id: "packageInstall"});
                    }
                    // TODO: delete temporary file.
                    callback();
                }, errorCallback);
                break;
            case KEYBINDS:
                // Install the file into Komodo's schemes directory and activate
                // it manually, as there is no existing service that does this.
                // TODO: eventually create a service to do so?
                var dirService = Cc['@activestate.com/koDirs;1'].getService();
                this._downloadFile(asset.browser_download_url, function(file)
                {
                    log.debug("Importing " + file + " as scheme " + pkg.name);
                    var schemeName = asset.browser_download_url.split(/\/|\./).slice(-2)[0];
                    var schemeService = Cc['@activestate.com/koKeybindingSchemeService;1'].getService();
                    // Refresh the list of known schemes.
                    schemeService.reloadAvailableSchemes();
                    keybindings.manager.reloadConfigurations(true); // refresh
                    callback(); // indicate success before potentially restarting
                    // Prompt the user to apply the new scheme.
                    if (dialog.confirm(l.get("applyKeybinds.prompt")))
                    {
                        log.debug("Applying scheme " + schemeName);
                        keybindings.manager.revertToPref(schemeName); // probably not the intended use, but it works
                        require("notify/notify").send(l.get("keybindingsApplied", pkg.name), "packages", {id: "packageInstall"});
                    }
                }, errorCallback, OS.Path.join(dirService.userDataDir, 'schemes'));
                break;
            default:
                log.debug("Unknown package kind; aborting");
        }
    }
    
    /**
     * Gets installable release or asset for the given package
     *
     * @param pkg The package object
     * @param want What do you want it to return, the 'release', 'asset' or 'url' (download url)
     *
     * @returns {boolean|object|string} returns false if nothing installable was found
     */
    this._getInstallable = function(pkg, want = 'url')
    {
        if ( ! pkg.releases || ! pkg.releases.length)
            return false;
        
        // Helper function that returns the right information, based on the 'want' param
        var result = function(release, asset)
        {
            if (want == 'release')
                return release;
            else if (want == 'asset')
                return asset;
            else
                return asset.browser_download_url;
        }
        
        // Iterate over and validate releases
        for (let release of pkg.releases)
        {
            if ( ! release.assets || ! release.assets.length)
            {
                continue;
            }
            
            // Iterate over and validate assets
            for (let asset of release.assets)
            {
                switch (pkg.kind)
                {
                    case ADDONS:
                    case SKINS:
                    case LANGS:
                        if (asset.browser_download_url.substr(-4) == '.xpi')
                            return result(release, asset);
                        break;
                    case TOOLBOX:
                    case MACROS:
                        if (asset.browser_download_url.substr(-11) == '.komodotool')
                            return result(release, asset);
                        break;
                    case SCHEMES:
                        if (asset.browser_download_url.substr(-4) == '.ksf')
                            return result(release, asset);
                        break;
                    case KEYBINDS:
                        if (asset.browser_download_url.substr(-4) == '.kkf')
                            return result(release, asset);
                        break;
                }
            }
        }

        return false;
    }
    
    /**
     * Uninstalls the given package.
     * @param pkg A package object obtained via `_getInstalledPackages()`.
     * @param callback The callback to be called upon success.
     * @param errorCallback the Callback to be called upon failure. The first
     *   argument will be the error message.
     */
    this._uninstallPackage = function(pkg, callback, errorCallback)
    {
        log.debug("Attempting to uninstall package " + pkg.name);
        switch (pkg.kind)
        {
            case ADDONS:
            case SKINS:
            case LANGS:
                // TODO: differentiate between these.
                // Uninstall the addon (XPI) package via Mozilla's AddonManager.
                var addon = pkg.data;
                if (addon.uninstall)
                {
                    log.info("Uninstalling package " + pkg.name + " v" + pkg.version);
                    addon.uninstall();
                    // Prompt for restart if necessary.
                    log.debug("Package pending operations: " + addon.pendingOperations);
                    callback(); // indicate success before potentially restarting
                    if ((addon.pendingOperations & AddonManager.PENDING_DISABLE) ||
                        (addon.pendingOperations & AddonManager.PENDING_UNINSTALL))
                    {
                        log.debug("Package requires Komodo restart.");
                        if (dialog.confirm(l.get("restartKomodoAfterUninstall.prompt"),
                            {
                                yes: l.get("restartNow.label"),
                                no: l.get("restartLater.label"),
                                response: l.get("restartLater.label")
                            }))
                        {
                            utils.restart(false);
                        }
                    }
                }
                break;
            case TOOLBOX:
            case MACROS:
                // TODO: differentiate between the two.
                // Uninstall the tool via Komodo's toolbox manager.
                log.info("Uninstalling package " + pkg.name);
                toolbox.manager.view.deleteToolAt(pkg.data);
                toolbox.manager.view.reloadToolsDirectoryView(-1); // for std toolbox
                callback();
                break;
            case SCHEMES:
            case KEYBINDS:
                // Uninstall the scheme via Komodo's appropriate scheme service.
                log.info("Uninstalling scheme " + pkg.name);
                var serviceName = (pkg.kind == SCHEMES) ? 'koScintillaSchemeService' : 'koKeybindingSchemeService';
                var schemeService = Cc['@activestate.com/' + serviceName + ';1'].getService();
                var scheme = schemeService.getScheme(pkg.name);
                // getScheme() returns the default scheme if the requested
                // scheme does not exist; ensure the correct scheme is to be
                // uninstalled.
                if (scheme.name == pkg.name)
                {
                    (pkg.kind == SCHEMES) ? scheme.remove() : keybindings.manager.deleteConfiguration(pkg.name, prefs);
                    // If the current scheme is the one being uninstalled,
                    // revert to the default scheme.
                    if (pkg.kind == SCHEMES && prefs.getStringPref('editor-scheme') == pkg.name)
                    {
                        schemeService.activateScheme(schemeService.getScheme('Default'));
                        log.debug("Reverted to Default scheme.");
                    }
                    else if (pkg.kind == KEYBINDS && prefs.getStringPref('keybinding-scheme') == pkg.name)
                    {
                        keybindings.manager.revertToPref('Default'); // probably not the intended use, but it works
                        log.debug("Reverted to Default scheme");
                    }
                }
                callback();
                break;
        }
    }
    
    /** Listener for addon (XPI) installation events. */
    this._addonInstallListener = {
        callback: null, // will be specified prior to each install
        errorCallback: null, // will be specified prior to each install
        package: null,
        /**
         * Checks for the addon's compatibility with this Komodo version.
         * If the check fails, prompts the user to abort the installation.
         */
        onInstallStarted: function(aInstall) {
            if (!aInstall.addon.isCompatible)
            {
                log.debug("Package incompatible with this Komodo version.");
                if (dialog.confirm(l.get("confirmIncompatible.prompt"),
                    {
                        yes: l.get("abortInstallation.label"),
                        no: l.get("continueAnyway.label")
                    }))
                {
                    log.info("Package installation cancelled by the user.");
                    this.errorCallback("Package installation cancelled by user.");
                    return false;
                }
            }
        },
        /**
         * Prompts the user to restart Komodo if necessary to complete the addon
         * installation.
         */
        onInstallEnded: function(aInstall, addon) {
            log.info("Package successfully installed.");
            this.callback(); // indicate success before potentially restarting
            log.debug("Package pending operations: " + addon.pendingOperations);
            if ((addon.pendingOperations & AddonManager.PENDING_ENABLE) ||
                (addon.pendingOperations & AddonManager.PENDING_INSTALL) ||
                (addon.pendingOperations & AddonManager.PENDING_UPGRADE))
            {
                log.debug("Package requires Komodo restart.");
                var locale;
                if (this.package.kind == SKINS)
                    locale = l.get("restartKomodoAfterSkinInstall.prompt", this.package.name)
                else if (this.package.kind == LANGS)
                    locale = l.get("restartKomodoAfterLangInstall.prompt", this.package.name)
                else
                    locale = l.get("restartKomodoAfterInstall.prompt");
                if (dialog.confirm(locale,
                    {
                        yes: l.get("restartNow.label"),
                        no: l.get("restartLater.label"),
                        response: l.get("restartLater.label")
                    }))
                {
                    utils.restart(false);
                }
            }
            else
            {
                if (this.package.kind == SKINS)
                {
                    if (dialog.confirm(l.get("skinInstalledOpenPrefs.prompt", this.package.name)))
                    {
                        prefs_doGlobalPrefs('appearance');
                    }
                }
            }
        },
        /** Notifies the user that installation of the addon failed. */
        onInstallFailed: function(aInstall) {
            this.errorCallback("Unable to install " + aInstall.name + ": " + aInstall.error);
        }
    }
    
    /**
     * Downloads the file from the given URL and saves it to the given directory
     * or the platform-specific temporary directory.
     * It is the caller's responsibility to remove the file after finishing with
     * it.
     * @param url The URL of the file to download.
     * @param callback The callback function to call with the downloaded file's
     *   filesystem path.
     * @param errorCallback the Callback to be called upon failure. The first
     *   argument will be the error message.
     * @param dir Optional directory to download the file to. The default value
     *   is the platform's temporary directory.
     */
    this._downloadFile = function(url, callback, errorCallback, dir)
    {
        var filename = url.match(/[^\/\\]+$/);
        var target = OS.Path.join(dir || OS.Constants.Path.tmpDir, filename);
        Task.spawn(function*()
        {
            log.debug("Downloading " + url + " to " + target);
            yield Downloads.fetch(url, target);
            return target; // passed as argument to callback
        }).then(callback, function(exception)
        {
            log.error("Error downloading " + url + ": " + exception);
            errorCallback("Error downloading " + url + ": " + exception);
        });
    }
    
}).apply(module.exports);
