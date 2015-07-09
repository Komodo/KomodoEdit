/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */
 
/* Komodo Less Parsing
 *
 * Defines the "koLess" namespace.
 */

var EXPORTED_SYMBOLS = ["koLess"];

var koLess = function koLess()
{
};

(function() {
    
    var self;
    var log;
    var onInit = [];
    
    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    const { Services }      =   Cu.import("resource://gre/modules/Services.jsm", {});
    const { FileUtils }     =   Cu.import("resource://gre/modules/FileUtils.jsm", {});
    const { NetUtil }       =   Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const { logging }       =   Cu.import("chrome://komodo/content/library/logging.js", {});
    const Timer             =   Cu.import("resource://gre/modules/Timer.jsm", {});

    const nsIChromeReg      =   Cc['@mozilla.org/chrome/chrome-registry;1']
                                    .getService(Ci["nsIChromeRegistry"]);
    const nsIFilePh         =   Services.io.getProtocolHandler("file")
                                    .QueryInterface(Ci.nsIFileProtocolHandler);

    const prefs             =   Cc['@activestate.com/koPrefService;1']
                                .getService(Ci.koIPrefService).prefs;

    koLess.prototype =
    {
        
        localCache: {getFile: {}, resolveFile: {}, resolveYoungestChild: {}, sheetPaths: []},
        hierarchy: null,
        initialized: false,
        initialising: false,

        /**
         * Initialize koLess,
         * this method must be idempotent as sync calls might run it multiple
         * times if it had not completed before
         *
         * @param   {bool|function} callback
         * @param   {bool} async
         *
         * @returns {Void}
         */
        init: function(callback = false, async = false)
        {
            if (callback)
            {
                onInit.push(callback);
            }

            if (this.initialising && async)
            {
                if (log)
                {
                    this.debug("Init in progress - delaying load of: " + sheet.href);
                }
                return;
            }

            this.initialising = true;
            self = this;
            log = logging.getLogger('koLess');
            //log.setLevel(10); // debug

            this.debug('Initializing koLess');
           
            // Clear the less cache if Komodo has been up/down-graded
            // or if an external lib (eg. ko.skin) has told us to
            var cacheVersion = prefs.getString('lessCachePlatVersion', '');
            var infoSvc = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
            var platVersion = infoSvc.buildPlatform + infoSvc.buildNumber;
            if (cacheVersion != platVersion)
            {
                prefs.setStringPref('lessCachePlatVersion', platVersion);
                this.cache.clear();
            }

            // Load cache hierarchy (if available)
            if (this.hierarchy === null)
            {
                this.hierarchy = {parents:{}, children: {}};

                var hierarchyCache = this.cache.getFile('hierarchy.json');
                if (hierarchyCache.exists())
                {
                    // No need to wrap this part in a try/catch, readFile takes care of that
                    this.readFile(hierarchyCache, function(data)
                    {
                        try
                        {
                            this.hierarchy = JSON.parse(data);
                            this.hierarchy.parents  = this.hierarchy.parents || {};
                            this.hierarchy.children = this.hierarchy.children || {};
                        }
                        catch (e)
                        {
                            this.cache.clear();
                            this.error(e.message);
                        }

                        this._onInit();
                    }.bind(this), async);
                    return;
                }
            }
           
            this._onInit();
        },

        _onInit: function()
        {
            this.initialized = true;

            var _callback;
            while ((_callback = onInit.pop()) !== undefined)
            {
                try
                {
                    _callback.call(this);
                }
                catch (e)
                {
                    this.exception(e, "Error calling initialization callback");
                }
            }
        },

        /**
         * Reload stylesheets in current window
         *
         * @param   {Boolean}   clearCache
         *
         * @returns {Void}
         */
        reload: function(clearCache = false)
        {
            self.warn('Reloading Skin');
            
            if (clearCache)
            {
                this.cache.clear();
            }

            // Give it some time to reload, _then_ refresh skins, in order to
            // avoid incorrect icons.  Bug 99717.
            // (The bug mainly happens when you switch away and back.)
            Services.tm.currentThread.dispatch(() => {
                Cc["@mozilla.org/chrome/chrome-registry;1"]
                  .getService(Ci.nsIXULChromeRegistry)
                  .refreshSkins();
            }, Ci.nsIEventTarget.DISPATCH_NORMAL);
        },

        _loadSheetNo: 0,
        /**
         * Load a specific stylesheet
         *
         * @param   {Element}       sheet           xml-stylesheet element
         * @param   {Function}      callback       
         * @param   {Boolean}       isInternalCall  Whether the loadSheet is called
         *                                          internally or from the compiler
         * @param   {Boolean}       async           Whether to execute this call
         *                                          asynchronously
         * @param   {Boolean}       cache           Whether to allow caching,
         *                                          if caching is disabled the callback
         *                                          will return the parsed sheet
         *
         * @returns {Void}
         */
        loadSheet: function koLess_loadSheet(sheet, callback = function() {}, isInternalCall = false, async = false, cache = true)
        {
            var threadId = this._loadSheetNo++;
            
            if ( ! this.initialized)
            {
                this.init(this.loadSheet.bind(this, sheet, callback, isInternalCall), async);
                return;
            }

            if (isInternalCall)
            {
                this.debug(threadId + " Loading: " + sheet.href);

                // Check if we can load the sheet via the file cache
                var youngest;
                var cacheFile = this.cache.getFile(sheet.href);
                if (cacheFile && cacheFile.exists())
                {
                    if (this.localCache.sheetPaths.indexOf(sheet.href) !== -1 ||
                        ((youngest = this.resolveYoungestChild(sheet.href)) &&
                         youngest.file.lastModifiedTime < cacheFile.lastModifiedTime))
                    {
                        this.debug(threadId + ' Loading from cache: ' + sheet.href);
                        this.debug(threadId + ' Returning ' + cacheFile.fileSize + ' bytes for: ' + sheet.href);
                        callback(cacheFile)
                        return;
                    }
                }
               
                this.debug(threadId + ' Loading new version ' + (async ? 'a' : '') + 'synchronously: ' + sheet.href);
            }
            else
            {
                //this.debug('Loading import: ' + sheet.href);
            }

            var uri = Services.io.newURI(sheet.href, null, null);
            // Grab the contents of the stylesheet
            this.readFile(uri, function(data)
            {
                var _parseCallback = function(e, root)
                {
                    // If we have a callback this is a call from the less parser
                    // and we should just return the data it wants.
                    if ( ! isInternalCall)
                    {
                        //this.debug('Returning: ' + sheet.href);
                        var bogus = { local: false, lastModified: null, remaining: 0 };
                        callback(e, root, data, sheet, bogus, sheet.href);
                    }
                    else // Otherwise it's an internal (koLess) call
                    {
                        try
                        {
                            var parsedCss = root.toCSS();
                        }
                        catch (ex)
                        {
                            if ("extract" in ex)
                            {
                                e = ex;
                            }
                            else
                            {
                                this.exception(e, threadId + ' Error converting less to css in ' + sheet.href);
                                return callback();
                            }
                        }

                        // Validate parsed result
                        if (e)
                        {
                            this.errorLess(e, sheet.href, threadId);
                            return callback();
                        }

                        // Write it to cache
                        try
                        {
                            var cacheFile = this.cache.writeFile(sheet.href, parsedCss, true);
                            this.localCache.sheetPaths.push(sheet.href);
                        }
                        catch (e)
                        {
                            this.exception(e, threadId + ' Error creating cache for ' + sheet.href);
                            return callback();
                        }

                        this.debug(threadId + ' Returning ' + cacheFile.fileSize + ' bytes for: ' + sheet.href);
                        callback(cacheFile);

                        // Perfect time to cache the sheet hierarchy
                        this.cache.writeFile('hierarchy.json', JSON.stringify(this.hierarchy));
                    }
                }.bind(this);
               
                // Run it through the LESS parser
                this.parse(data, _parseCallback, sheet, false);
            }.bind(this), async);
        },

        /**
         * Parse given CSS/LESS into pure CSS
         *
         * @param   {string} data
         * @param   {function} callback
         * @param   {object|undefined} sheet
         *
         * @returns {void}
         */
        parse: function(data, callback, sheet = undefined, isVirtual = true)
        {
            if ( ! sheet)
            {
                sheet = {
                    href: "file://virtual.less",
                    mime: "text/less"
                }
            }

            try
            {
                var contents = {};
                contents[sheet.href] = data;

                if (sheet instanceof less.tree.parseEnv)
                {
                    var env = new less.tree.parseEnv(sheet);
                }
                else
                {
                    var env = new less.tree.parseEnv(less);
                    env.mime = sheet.type;
                    env.sheet = sheet;
                }

                env.paths = [sheet.href.replace(/[^/]*$/, '')];
                env.contents = contents;
                env.dumpLineNumbers = false;
                env.strictImports = false;
                env.currentFileInfo = {
                    filename: sheet.href
                };

                new(less.Parser)(env).parse(data, function(e, root)
                {
                    if ( ! isVirtual) return callback(e, root);

                    try
                    {
                        var parsedCss = root.toCSS();
                    }
                    catch (ex)
                    {
                        if ("extract" in ex)
                        {
                            e = ex;
                        }
                        else
                        {
                            this.exception(e, 'Error converting less to css in ' + sheet.href);
                        }
                    }

                    // Validate parsed result
                    if (e)
                    {
                        this.errorLess(e, sheet.href);
                    }

                    callback(parsedCss);
                }.bind(this));
            }
            catch (e)
            {
                this.exception(e, ' Parsing error for ' + sheet.href + ': ' + e.message);

                if ( ! isVirtual) callback(e);
            }
        },

        /**
         * Caching functionality, takes care of both file caching and
         * variable caching
         */
        cache: {

            /**
             * Get a file through the cache
             *
             * @param   {String} fileUri
             *
             * @returns {nsIFile|Boolean}
             */
            getFile: function koLess_cache_getFile(fileUri)
            {
                if (fileUri in self.localCache.getFile)
                {
                    return self.localCache.getFile[fileUri];
                }

                var cacheUri = this.getRelativePath(fileUri);

                // Create cache pointer
                var cacheFile = FileUtils.getFile("ProfD", cacheUri, true);

                self.debug('Resolved cache for "' + fileUri + '" as "' + cacheFile.path + '"');

                self.localCache.getFile[fileUri] = cacheFile;

                return cacheFile;
            },

            _writeTimer: {},

            /**
             * Write data to cache file
             *
             * @param   {String} fileUri
             * @param   {String} data
             * @param   {Boolean} noDelay
             *
             * @returns {nsIFile|Boolean|Void}
             */
            writeFile: function(fileUri, data, noDelay = false)
            {
                if ( ! noDelay)
                {
                    if (fileUri in this._writeTimer) Timer.clearTimeout(this._writeTimer[fileUri]);
                    this._writeTimer[fileUri] = Timer.setTimeout(this.writeFile.bind(this, fileUri, data, true), 500);
                    return;
                }

                self.debug('Writing to cache for ' + fileUri);

                var file = this.getFile(fileUri);
                if ( ! file)
                {
                    return false;
                }

                try
                {
                    self.debug('Writing to ' + file.path);

                    // Open stream to file
                    var foStream = Cc["@mozilla.org/network/file-output-stream;1"].
                    createInstance(Ci.nsIFileOutputStream);
                    foStream.init(
                        file,
                        0x02 /* PR_WRONLY */ | 0x08 /* PR_CREATE_FILE */ | 0x20 /* PR_TRUNCATE */,
                        parseInt('0666', 8), 0);

                    // Use converter to ensure UTF-8 encoding
                    var converter = Cc["@mozilla.org/intl/converter-output-stream;1"].
                    createInstance(Ci.nsIConverterOutputStream);

                    // Write to file
                    converter.init(foStream, "UTF-8", 0, 0);
                    converter.writeString(data);
                    converter.close();

                    self.debug('Written to ' + file.path);

                    return file;
                }
                catch(e)
                {
                    this.error('Error when trying to write to file: ' + e.message);
                    return false;
                }
            },

            /**
             * Clear the local and file cache
             *
             * @returns {Void}
             */
            clear: function koLess_cache_clear()
            {
                self.warn('Clearing local and file cache');
                
                let observers = Services.obs.enumerateObservers("chrome-flush-caches");
                while (observers.hasMoreElements())
                {
                    let observer = observers.getNext();
                    if (observer instanceof Ci.imgICache)
                    {
                        observer.clearCache(true /*chrome*/);
                    }
                }
                Services.obs.notifyObservers(null, "chrome-flush-caches", null);

                // Reset localCache
                for (let [,k] in Iterator(Object.keys(self.localCache)))
                {
                    self.localCache[k] = k == 'sheetPaths' ? [] : {};
                }
                
                // Cleanup old caches
                this.cleanup();

                // Clear file cache
                var file = FileUtils.getFile("ProfD", ["lessCache", prefs.getString("lessCacheVersion", "0")], true);
                try
                {
                    file.remove(true);
                }
                catch (e)
                {
                    if (e.name != 'NS_ERROR_FILE_TARGET_DOES_NOT_EXIST')
                    {
                        self.warn(e, "Failed deleting lessCache folder: " + file.path + ", changing lessCache path (" + e.name + ")");

                        this.addToCleanup(prefs.getString("lessCacheVersion", "0"));
                        prefs.setString("lessCacheVersion", new Date().getTime());
                    }
                }
            },
            
            /**
             * Cleanup old caches that failed to delete at previous runtime
             *
             * @returns {Void}
             */
            cleanup: function koLess_cache_cleanup()
            {
                var cleanup = this._getCleanup();
                if ( ! cleanup.length)
                {
                    return
                }
                
                self.warn("Cleaning up " + cleanup.length + " old caches");
                
                for (let x=cleanup.length-1; x>=0; x--)
                {
                    let file = FileUtils.getFile("ProfD", ["lessCache", cleanup[x]], true);
                    
                    try
                    {
                        if (file.exists())
                        {
                            file.remove(true);
                        }
                        cleanup.splice(x,1);
                    }
                    catch (e)
                    {
                        self.warn("Failed cleaning up lessCache version '" + cleanup[x] + "', leaving for future cleanup");
                    }
                }
                
                prefs.setString("lessCacheCleanup", JSON.stringify(cleanup));
            },
            
            /**
             * Add less cache version to cleanup
             *
             * @param   {String}    version
             *
             * @returns {Void}
             */
            addToCleanup: function koLess_cache_addToCleanup(version)
            {
                var cleanup = this._getCleanup();
                cleanup.push(version);
                prefs.setString("lessCacheCleanup", JSON.stringify(cleanup));
            },
            
            /**
             * Retrieve the array of old less caches that need to be cleaned up
             *
             * @returns {Void}
             */
            _getCleanup: function koLess_cache_getCleanup()
            {
                var cleanup = [];
                var _cleanup = prefs.getString("lessCacheCleanup", "");
                if (_cleanup)
                {
                    try
                    {
                        cleanup = JSON.parse(_cleanup);
                    }
                    catch(e)
                    {
                        log.exception(e, "Failed parsing lessCacheCleanup pref");
                    }
                }
                
                return cleanup;
            },

            /**
             * Convert path to relative path, if possible
             *
             * @returns {Array}
             */
            getRelativePath: function koLess_cache_getRelativePath(filePath)
            {
                if (filePath.match(/\/|\\/))
                {
                    try
                    {
                        let _filePath = NetUtil.newURI(filePath);
                        if ((_filePath instanceof Ci.nsIFileURL))
                        {
                            let ProfD = Services.dirsvc.get("ProfD", Ci.nsIFile);
                            if (ProfD.contains(_filePath.file, true))
                            {
                                filePath = _filePath.file.getRelativeDescriptor(ProfD);
                            }

                            let AppD = Services.io.newURI("resource://app/", null, null)
                                        .QueryInterface(Ci.nsIFileURL).file;
                            if (AppD.contains(_filePath.file, true))
                            {
                                filePath = _filePath.file.getRelativeDescriptor(AppD);
                            }
                        }
                    }
                    catch (e)
                    {
                        self.error('Error while resolving relative path for ' + filePath + "\n" + e.message);
                    }
                }

                filePath = filePath.replace(/\:/g, '');
                filePath = filePath.replace(/.less$/, '.css');
                filePath = filePath.split(/\/|\\/);
                
                filePath.unshift("lessCache", prefs.getString("lessCacheVersion", "0"));
                
                return filePath;
            }

        },

        /**
         * Read a file using file uri
         *
         * @param   {nsIFile|nsIURI} fileUri
         * @param   {Function} callback     callback(String) returns file contents
         * @param   {Boolean} async
         *
         * @returns {Void}
         */
        readFile: function koLess_readFile(file, callback, async = false)
        {
            this.debug("Reading file: " + (file.spec || file.path));

            if (async)
            {
                return this.readFileAsync(file, callback);
            }

            // Grab the contents of the stylesheet
            var _success = false;
            try
            {
                var data = "";
                var fstream = NetUtil.newChannel(file, null, null).open();
                var cstream = Components.classes["@mozilla.org/intl/converter-input-stream;1"].
                              createInstance(Components.interfaces.nsIConverterInputStream);
                cstream.init(fstream, "UTF-8", 0, 0);

                let (str = {})
                {
                    let read = 0;
                    do
                    {
                        read = cstream.readString(0xffffffff, str);
                        data += str.value;
                    } while (read != 0);
                }
                cstream.close();

                _success = true;
            }
            catch (e)
            {
                this.exception(e, 'Failed reading file synchronously: ' + (file.spec || file.path) + "\n" + e.message);
            }

            if (_success)
            {
                callback(data);
            }
        },

        /**
         * Async version of readFile
         *
         * @param   {nsIFile|nsIURI} file
         * @param   {Function} callback     callback(String) returns file contents
         *
         * @returns {Void} 
         */
        readFileAsync: function koLess_readFile(file, callback)
        {
            // Grab the contents of the stylesheet
            NetUtil.asyncFetch(file, function(inputStream, status)
            {
                // Validate result
                if ( ! Components.isSuccessCode(status))
                {
                    this.error("asyncFetch failed for uri: " + file.path + " :: " + status);
                    return;
                }

                // Parse contents
                var data = NetUtil.readInputStreamToString(inputStream, inputStream.available());
                callback(data);
            }.bind(this));
        },

        /**
         * Resolve a file uri to a nsIFile. Note - if the uri points to a
         * file residing within a jar, the jar file is returned.
         *
         * @param   {String} fileUri
         *
         * @returns {nsIFile|Boolean}
         */
        resolveFile: function koLess_resolveFile(fileUri)
        {
            if (fileUri in this.localCache.resolveFile)
            {
                return this.localCache.resolveFile[fileUri];
            }

            var koResolve = Cc["@activestate.com/koResolve;1"]
                                    .getService(Ci.koIResolve);

            var filePath = koResolve.uriToPath(fileUri);
            if ( ! filePath)
            {
                return false;
            }

            try
            {
                // Create nsIFile with path
                var file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
                file.initWithPath(filePath);
            }
            catch (e)
            {
                this.exception(e, "Error loading file: " + fileUri);
                return false;
            }

            this.localCache.resolveFile[fileUri] = file;

            return file;
        },

        /**
         * Resolve the youngest child sheet (ie. youngest @import)
         *
         * @param   {String} href
         *
         * @returns {Object}
         */
        resolveYoungestChild: function koLess_resolveYoungestChild(href)
        {
            if (href in this.localCache.resolveYoungestChild)
            {
                return this.localCache.resolveYoungestChild[href];
            }

            var file = this.resolveFile(href);
            if ( ! file || ! file.exists())
            {
                return null;
            }

            var youngest = {
                file: file,
                href: href
            };
            if (this.hierarchy.children[href] != undefined)
            {
                var children = this.hierarchy.children[href];
                for (var childHref in children)
                {
                    var child = this.resolveYoungestChild(childHref);
                    if (child && child.file.lastModifiedTime > youngest.file.lastModifiedTime)
                    {
                        youngest = child;
                    }
                }
            }

            this.debug('Youngest child for "' + href + '" is "' + youngest.href + '"');

            this.localCache.resolveYoungestChild[href] = youngest;
            return youngest;
        },

        addToHierarchy: function koLess_addToHierarchy(id, pId)
        {
            if (typeof this.hierarchy.parents[id] == 'undefined') {
                this.hierarchy.parents[id] = {};
            }
            if (typeof this.hierarchy.children[pId] == 'undefined') {
                this.hierarchy.children[pId] = {};
            }

            this.hierarchy.parents[id][pId] = true;
            this.hierarchy.children[pId][id] = true;
        },

        /**
         * Log Debug Wrapper
         *
         * @param   {String} message
         *
         * @returns {Void}
         */
        debug: function koLess_debug(message)
        {
            log.debug(message);
        },

        /**
         * Log Warn Wrapper
         *
         * @param   {String} message
         *
         * @returns {Void}
         */
        warn: function koLess_warn(message)
        {
            log.warn(message);
        },

        /**
         * Log Error Wrapper
         *
         * @param   {String} message
         * @param   {Boolean} noBacktrace
         *
         * @returns {Void}
         */
        error: function koLess_error(message, noBacktrace = false)
        {
            log.error(message + "\n", noBacktrace);
        },

        /**
         * Log Exception Wrapper
         *
         * @param   {Object} exception
         * @param   {String} message
         *
         * @returns {Void}
         */
        exception: function koLess_error(exception, message = "")
        {
            log.exception(exception, message);
        },

        /**
         * Log a LESS error message, contains a LESS backtrace if available
         *
         * @param   {Object} e
         * @param   {String} href
         *
         * @returns {Void}
         */
        errorLess: function koLess_errorLess(e, href, threadId = "") {
            var error = [];

            var errorString = (
                threadId + ' There is an error in your .less file'
            ) + ' (' + (e.filename || href) + ")\n";

            if (e.message)
            {
                errorString += e.message + "\n";
            }

            var errorline = function (e, i, classname)
            {
                var template = ' - {line}: {content}' + "\n";
                if (e.extract[i]) {
                    error.push(template.replace("{line}", parseInt(e.line) + (i - 1), "g")
                                       .replace("{class}", classname, "g")
                                       .replace("{content}", e.extract[i]), "g");
                }
            };

            if (e.stack) {
                errorString += "\n" + e.stack.split('\n').slice(1).join("\n");
            } else if (e.extract) {
                errorline(e, 0, '');
                errorline(e, 1, 'line');
                errorline(e, 2, '');
                errorString += 'on line ' + e.line + ', column ' + (e.column + 1) + ':' + "\n" +
                            error.join('');
            }

            this.exception(errorString);
        }
        
    };
    
    koLess = new koLess();
    
    var subScriptLoader = Cc["@mozilla.org/moz/jssubscript-loader;1"]
                          .getService(Ci.mozIJSSubScriptLoader);
    subScriptLoader.loadSubScript("chrome://komodo/content/contrib/less.js");

}).apply();
