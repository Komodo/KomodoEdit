(function() {
    const {Cc, Ci, Cu} = require("chrome");
    const log          = require("ko/logging").getLogger("commando-scope-packages");
    const commando     = require("commando/commando");
    const dialog       = require("ko/dialogs");
    const toolbox      = ko.toolbox2;
    const utils        = ko.utils;
    const prefs        = ko.prefs;
    const keybindings  = ko.keybindings;
    
    /** Locale bundle. */
    const bundle = Cc["@mozilla.org/intl/stringbundle;1"].getService(Ci.nsIStringBundleService).
        createBundle("chrome://scope-packages/locale/scope-packages.properties");
    
    /** The root directory for package archives. */
    //const ROOT = "http://komodoide.com/json/";
    const ROOT = "http://dev.komodoide.com:4567/json/"; // TODO: disable
    /** The name of the file (no extension) that lists available addons. */
    const ADDONS = "addons";
    /**
     * The name of the file (no extension) that lists available toolbox items.
     */
    const TOOLBOX = "toolbox";
    /** The name of the file (no extension) that lists available macros. */
    const MACROS = "macros";
    /** The name of the file (no extension) that lists available schemes. */
    const SCHEMES = "schemes";
    /** The name of the file (no extension) that lists available skins. */
    const SKINS = "skins";
    /** The name of the file (no extension) that lists available keybindings. */
    const KEYBINDS = "keybinds";
    
    // Import the XPI addon manager as "AddonManager".
    Cu.import("resource://gre/modules/AddonManager.jsm");
    // Import the HTTP downloader as "Downloads".
    Cu.import("resource://gre/modules/Downloads.jsm");
    // Import OS-specific file management as "OS".
    Cu.import("resource://gre/modules/osfile.jsm");
    // Import asynchronous task management for downloads as "Task".
    Cu.import("resource://gre/modules/Task.jsm");
    
    log.setLevel(require("ko/logging").LOG_DEBUG);
    
    this.onSearch = function(query, uuid, onComplete)
    {
        log.debug(uuid + " - Starting Scoped Search");
        
        var subscope = commando.getSubscope();
        if (subscope) subset = subscope.data.subset || {};
        
        if (query != "" || subscope)
        {
            commando.renderResults([{
                id: "scope-shell-run-cmd",
                name: "run command",
                scope: "scope-shell",
                data: {},
                allowMultiSelect: false,
                weight: query == "" ? 100 : -1
            }], uuid);
        }
        
        this.searchSubset(subset, query, uuid, onComplete);
    }
    
    this.searchSubset = function(subset, query, uuid, callback)
    {
        if (typeof subset == 'function')
        {
            try
            {
                subset = subset(query, function(_subset)
                {
                    this.searchSubset(_subset, query, uuid, callback);
                }.bind(this));
            }
            catch (e)
            {
                log.exception(e, "Exception while searching subset");
            }
            return;
        }
            
        query = query.trim().toLowerCase();
        
        // Search within subset
        var results = [];
        var _ = require("contrib/underscore");
        _.find(subset, function(data, key) // _.each doesn't let you break out
        {
            if ( ! isNaN(key))
            {
                if (typeof data == "object")
                {
                    key = data.command;
                }
                else
                {
                    key = data;
                    data = {};
                }
            }
            
            let indexOf = key.toLowerCase().indexOf(query);
            if (query == "" || indexOf !== -1)
            {
                let command = key;
                if ("command" in data) command = data.command;
                let weight = indexOf == 0 ? 5 : 0;
                if ("weight" in data) weight = data.weight;
                let subset = data.results || {};
                let entry = _.extend({
                    id: id + key,
                    name: key,
                    scope: "scope-shell",
                    isScope: true,
                    weight: weight,
                    data: _.extend({
                        subset: subset,
                        command: command
                    }, data.data || {}),
                    allowMultiSelect: false
                }, data);
                
                if (local.hasTrailingSpace)
                {
                    commando.setSubscope(entry);
                    return true;
                }
                
                results.push(entry);
                
                return false; // continue
            }
        });
        
        commando.renderResults(results, uuid);
        
        callback();
    }
    
    this.onSelectResult = function(selectedItems)
    {
        var shell = this.getShell();
        
        var env     = shell.env;
        var command = shell.command;
        var options = shell.options;
        
        // Detect current working directory
        var partSvc = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
        options.cwd = ko.uriparse.URIToPath(ko.places.getDirectory());
        if (partSvc.currentProject)
            options.cwd = partSvc.currentProject.liveDirectory;
        
        if (options.runIn == "hud")
            require("ko/shell").exec(command, options);
        else
        {
            if ( ! ("env" in options))
            options.env = [];
            for (let k in env)
                options.env.push(k+"="+env[k]);
            options.env = options.env.join("\n");
            
            log.debug("Running command: " + command + " ("+options.env+")");
            
            ko.run.command(command, options);
        }
        
        commando.hideCommando();
    }
    
    this.sort = function(current, previous)
    {
        return previous.name.localeCompare(current.name) > 0 ? 1 : -1;
    }
    
    // Package Logic.
    
    /**
     * All package kinds supported.
     * Calling `_getAvailablePackages()` individually with each of these would
     * yield every package currently available.
     */
    this.ALL_KINDS = [ADDONS, TOOLBOX, MACROS, SCHEMES, SKINS, KEYBINDS];
    
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
    this._getAvailablePackages = function(kind, callback)
    {
        log.debug("Retrieving all packages for " + kind);
        var ajax = require('ko/ajax');
        var url = ROOT + kind + '.json';
        ajax.get(url, function(code, response)
        {
            if (code != 200)
            {
                log.error("Unable to retrieve package listing for " + kind);
                require('notify/notify').send("Unable to retrieve package listing for " + kind);
                return;
            }
            var results = {};
            for (let pkg of JSON.parse(response))
            {
                pkg.kind = kind;
                results[pkg.name] = pkg;
            }
            callback(results);
        });
    }
    
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
    this._getInstalledPackages = function(kind, callback)
    {
        log.debug("Retrieving all installed packages for " + kind);
        switch (kind)
        {
            case ADDONS:
            case SKINS: // TODO: differentiate between the two.
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
                        log.debug("Found " + pkg.name + " v" + pkg.version);
                    }
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
                    log.debug("Found " + pkg.name);
                }
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
                        log.debug("Scheme " + name + " is a default scheme (not writable); ignoring");
                        continue; // filter out default schemes
                    }
                    let pkg = {};
                    pkg.name = name;
                    pkg.kind = kind; // needed by _uninstallPackage()
                    packages[pkg.name] = pkg;
                    log.debug("Found " + pkg.name);
                }
                callback(packages);
                break;
            default:
                log.error("Unknown package kind: " + kind);
                return;
        }
    }
    
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
    this._getUpgradablePackages = function(kind, callback)
    {
        this._getAvailablePackages(kind, function(available)
        {
            this._getInstalledPackages(kind, function(installed)
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
                        log.debug("Installed package " + name + " does not exist upstream; ignoring.");
                        continue;
                    }
                    log.debug("Installed package " + name + " exists upstream.");
                    // Verify the package has a release.
                    if (!(upstreamPkg.releases) || upstreamPkg.releases.length == 0)
                    {
                        log.debug("Package has no upstream releases; ignoring.");
                        continue;
                    }
                    // Verify the package's latest release has an artifact.
                    // This is to ensure a package marked upgradable can
                    // actually download and apply an update.
                    let release = upstreamPkg.releases[0];
                    if (!(release.assets) || release.assets.length == 0)
                    {
                        log.debug("Package has no upstream releases; ignoring.");
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
                        log.debug("Package has a newer version; marking as upgradable.");
                    }
                    else
                    {
                        log.debug("Package is up to date.");
                    }
                }
                callback(upgradable);
            });
        }.bind(this));
    }
    
    /**
     * Installs the given package.
     * @param pkg A package object obtained via `_getAvailablePackages()`.
     */
    this._installPackage = function(pkg)
    {
        // Verify the package has a release.
        log.info("Attempting to install package " + pkg.name);
        if (!(pkg.releases) || pkg.releases.length == 0)
        {
            log.info("No releases for package " + pkg.name + "; aborting.");
            return;
        }
        
        // Verify the package's latest release has an artifiact.
        var release = pkg.releases[0];
        log.debug("Preparing to install version " + release.name);
        if (!(release.assets) || release.assets.length == 0)
        {
            log.info("No assets for package " + pkg.name + " v" + release.name + "; aborting.");
            return null;
        }
        
        // Determine the package's content type and act appropriately.
        var asset = release.assets[0];
        log.debug("Package kind is " + pkg.kind);
        switch (pkg.kind)
        {
            case ADDONS:
            case SKINS: // TODO: differentiate between the two and prompt for applying skin.
                // Install the XPI via Mozilla's AddonManager.
                AddonManager.getInstallForURL(asset.browser_download_url, function(aInstall)
                {
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
                });
                break;
            case SCHEMES:
                // Install the file via Komodo's color scheme service.
                this._downloadFile(asset.browser_download_url, function(file)
                {
                    log.debug("Importing " + file + " as scheme " + pkg.name);
                    var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
                    var scheme = schemeService.loadSchemeFromURI(file, pkg.name);
                    // Ask the user if the scheme should be applied immediately.
                    if (dialog.confirm(bundle.GetStringFromName("applyScheme.prompt"),
                        {
                            yes: bundle.GetStringFromName("applySchemeNow.label"),
                            no: bundle.GetStringFromName("applySchemeLater.label"),
                            response: bundle.GetStringFromName("applySchemeNow.label")
                        }))
                    {
                        schemeService.activateScheme(scheme);
                    }
                    // TODO: delete temporary file.
                });
                break;
            case KEYBINDS:
                // Install the file into Komodo's schemes directory and activate
                // it manually, as there is no existing service that does this.
                // TODO: eventually create a service to do so?
                var dirService = Cc['@activestate.com/koDirs;1'].getService();
                this._downloadFile(asset.browser_download_url, function(file)
                {
                    log.debug("Importing " + file + " as scheme " + pkg.name);
                    var schemeService = Cc['@activestate.com/koKeybindingSchemeService;1'].getService();
                    // Record existing scheme names for later use when applying
                    // the new scheme.
                    var schemes = {};
                    schemeService.getSchemeNames(schemes, {});
                    var oldSchemes = [];
                    for (let name of schemes.value)
                    {
                        oldSchemes.push(name);
                    }
                    // Refresh the list of known schemes.
                    schemeService.reloadAvailableSchemes();
                    keybindings.manager.reloadConfigurations(true); // refresh
                    // Prompt the user to apply the new scheme.
                    if (dialog.confirm(bundle.GetStringFromName("applyKeybinds.prompt"),
                        {
                            yes: bundle.GetStringFromName("applyKeybindsNow.label"),
                            no: bundle.GetStringFromName("applyKeybindsLater.label"),
                            response: bundle.GetStringFromName("applyKeybindsNow.label")
                        }))
                    {
                        // As noted in the TODO above, there is no keybinding
                        // service that imports a scheme file, reads it, and
                        // reports the name. In the interest of time, the
                        // pure-JS way is to take snapshots of known schemes
                        // before and after the import, and compare the two.
                        schemeService.getSchemeNames(schemes, {});
                        var newSchemes = [];
                        for (let name of schemes.value)
                        {
                            newSchemes.push(name);
                        }
                        var newSchemeName = newSchemes.filter(function(name)
                        {
                            return oldSchemes.indexOf(name) < 0;
                        })[0];
                        log.debug("Applying scheme " + newSchemeName);
                        keybindings.manager.revertToPref(newSchemeName); // probably not the intended use, but it works
                        utils.restart(false);
                    }
                }, OS.Path.join(dirService.userDataDir, 'schemes'));
                break;
            default:
                log.debug("Unknown package kind; aborting");
        }
    }
    
    /**
     * Uninstalls the given package.
     * @param pkg A package object obtained via `_getInstalledPackages()`.
     */
    this._uninstallPackage = function(pkg)
    {
        log.debug("Attempting to uninstall package " + pkg.name);
        switch (pkg.kind)
        {
            case ADDONS:
            case SKINS: // TODO: differentiate between the two.
                // Uninstall the addon (XPI) package via Mozilla's AddonManager.
                var addon = pkg.data;
                if (addon.uninstall)
                {
                    log.info("Uninstalling package " + pkg.name + " v" + pkg.version);
                    addon.uninstall();
                    // Prompt for restart if necessary.
                    log.debug("Package pending operations: " + addon.pendingOperations);
                    if ((addon.pendingOperations & AddonManager.PENDING_DISABLE) ||
                        (addon.pendingOperations & AddonManager.PENDING_UNINSTALL))
                    {
                        log.debug("Package requires Komodo restart.");
                        if (dialog.confirm(bundle.GetStringFromName("restartKomodoAfterUninstall.prompt"),
                            {
                                yes: bundle.GetStringFromName("restartNow.label"),
                                no: bundle.GetStringFromName("restartLater.label"),
                                response: bundle.GetStringFromName("restartLater.label")
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
                break;
        }
    }
    
    /** Listener for addon (XPI) installation events. */
    this._addonInstallListener = {
        /**
         * Checks for the addon's compatibility with this Komodo version.
         * If the check fails, prompts the user to abort the installation.
         */
        onInstallStarted: function(aInstall) {
            if (!aInstall.addon.isCompatible)
            {
                log.debug("Package incompatible with this Komodo version.");
                if (dialog.confirm(bundle.GetStringFromName("confirmIncompatible.prompt"),
                    {
                        yes: bundle.GetStringFromName("abortInstallation.label"),
                        no: bundle.GetStringFromName("continueAnyway.label")
                    }))
                {
                    log.info("Package installation cancelled by the user.");
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
            log.debug("Package pending operations: " + addon.pendingOperations);
            if ((addon.pendingOperations & AddonManager.PENDING_ENABLE) ||
                (addon.pendingOperations & AddonManager.PENDING_INSTALL) ||
                (addon.pendingOperations & AddonManager.PENDING_UPGRADE))
            {
                log.debug("Package requires Komodo restart.");
                if (dialog.confirm(bundle.GetStringFromName("restartKomodoAfterInstall.prompt"),
                    {
                        yes: bundle.GetStringFromName("restartNow.label"),
                        no: bundle.GetStringFromName("restartLater.label"),
                        response: bundle.GetStringFromName("restartLater.label")
                    }))
                {
                    utils.restart(false);
                }
            }
        },
        /** Notifies the user that installation of the addon failed. */
        onInstallFailed: function(aInstall) {
            require('notify/notify').send("Unable to install " + aInstall.name + ": " + aInstall.error);
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
     * @param dir The directory to download the file to. The default value is
     *   the platform's temporary directory.
     */
    this._downloadFile = function(url, callback, dir)
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
        });
    }
    
}).apply(module.exports);
