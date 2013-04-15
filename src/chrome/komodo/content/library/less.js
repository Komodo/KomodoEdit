/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */
 
/* Komodo Less Parsing
 *
 * Defines the "ko.less" namespace.
 */
if (typeof ko == 'undefined')
{
    var ko = {};
}

if ( ! ("less" in ko))
{
    ko.less = function()
    {
        this.init();
    };
}

(function() {
    
    var self;
    var log;
    
    const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    const { Services }      =   Cu.import("resource://gre/modules/Services.jsm", {});
    const { FileUtils }     =   Cu.import("resource://gre/modules/FileUtils.jsm", {});
    const { NetUtil }       =   Cu.import("resource://gre/modules/NetUtil.jsm", {});
    const { logging }       =   Cu.import("chrome://komodo/content/library/logging.js", {});
    
    const nsIChromeReg      =   Cc['@mozilla.org/chrome/chrome-registry;1']
                                    .getService(Ci["nsIChromeRegistry"]);
    const nsIFilePh         =   Services.io.getProtocolHandler("file")
                                    .QueryInterface(Ci.nsIFileProtocolHandler);
    
    ko.less.prototype =
    {
        
        sheets: {},
        hierarchy: null,
        
        localCache: {getFile: {}, resolveFile: {}, resolveYoungestChild: {}, sheetPaths: {}},
        
        initialized: false,
        timer: Date.now(),
        
        /**
         * Initialize library
         * 
         * @returns {Void} 
         */
        init: function ko_less_init() 
        {
            self = this;

            log = logging.getLogger('ko.less');
            //log.setLevel(ko.logging.LOG_DEBUG);
            
            this.debug('Initializing ko.less');
            
            // Load cache hierarchy (if available)
            if (this.hierarchy === null)
            {
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
                        
                        this.init();
                    }.bind(this));
                    return;
                }
                else
                {
                    this.hierarchy = {parents: {}, children: {}};
                }
            }
            
            this.initialized = true;

            // Clear the less cache if Komodo has been up/down-graded
            // or if an external lib (eg. ko.skin) has told us to
            var cacheVersion    = ko.prefs.getString('lessCacheVersion', '');
            var platVersion     = Services.prefs.getCharPref("extensions.lastPlatformVersion");
            if (typeof _lessClearCache != 'undefined' || cacheVersion != platVersion)
            {
                ko.prefs.setStringPref('lessCacheVersion', platVersion);
                this.cache.clear();
            }

            // Let the less loaders know wer're ready
            xtk.domutils.fireEvent(window, 'ko.less.initialized');
            
            this.load();
        },
        
        /**
         * Reload stylesheets in current window
         *
         * @param {Boolean} full    Whether to clear the file and local cache
         * 
         * @returns {Void} 
         */
        reload: function ko_less_reload(full = false)
        {
            this.debug('Reloading known stylesheets');
            this.timer = Date.now();
            
            if (full)
            {
                this.cache.clear();
            }
            
            for (let href in this.sheets)
            {
                if ( ! this.sheets.hasOwnProperty(href))
                {
                    continue;
                }
                
                // Only load the first sheet, then iterate through duplicates
                // and use results from the first one to load them
                this.loadSheet(this.sheets[href][0], false, true);
            }
        },
        
        /**
         * Load up stylesheets for the current window
         * 
         * @returns {Void} 
         */
        load: function ko_less_load(_window = window)
        {
            this.debug('Loading ' + window.document.title);
            this.loadSheets(_window);
        },
        
        /**
         * Load current windows less stylesheets
         * 
         * @returns {Void} 
         */
        loadSheets: function ko_less_loadSheets(_window = window)
        {
            var childNodes = Array.slice(_window.document.childNodes);
            var attrMatch = /([a-z]*)=("|')([a-z0-9:/_.-]*)\2/.source;
            
            for (let [i, child] in Iterator(childNodes))
            {
                // Parse stylesheet attributes from nodeValue
                if (child.nodeName != 'xml-stylesheet' ||
                    ! child.nodeValue.match(/type=('|")stylesheet\/less\1/))
                {
                    continue;
                }
                
                var re = new RegExp(attrMatch, "gi"), match;
                while ((match = re.exec(child.nodeValue)))
                {
                    child[match[1]] = match[3];
                }
                
                if ( ! (child.href in this.sheets))
                {
                    this.sheets[child.href] = [];
                }
                
                if ( ! ("_isLoaded" in child))
                {
                    this.sheets[child.href].push(child);
                    child._isLoaded = true;
                }
                
                this.loadSheet(child);
            }
        },
        
        /**
         * Load a specific stylesheet
         * 
         * @param   {Element}       sheet           xml-stylesheet element
         * @param   {Function}      callback        If no callback is provided
         *                                          this will be considered an
         *                                          internal call, and the results
         *                                          will be injected into the DOM
         * @paran   {Boolean}       loadDuplicates  If true, loads all sheets
         *                                          with the same url in other
         *                                          windows
         * 
         * @returns {Void} 
         */
        loadSheet: function ko_less_loadSheet(sheet, callback = false, loadDuplicates = false)
        {
            var isInternalCall = typeof callback != "function";
            
            if (isInternalCall)
            {
                // Check if we can load the sheet via the localCache
                if (sheet.href in this.localCache.sheetPaths)
                {
                    this.debug('Loading from local cache: ' + sheet.href);
                    
                    var loadHref = this.localCache.sheetPaths[sheet.href];
                    this.injectSheet(loadHref, sheet);
                    
                    if (loadDuplicates)
                    {
                        this._loadDupeSheets(sheet, loadHref);
                    }
                    
                    return;
                }
                
                // Check if we can load the sheet via the file cache
                var cacheFile = this.cache.getFile(sheet.href);
                if (cacheFile && cacheFile.exists())
                {
                    var youngest = this.resolveYoungestChild(sheet.href);
                    
                    if (youngest && youngest.file.lastModifiedTime < cacheFile.lastModifiedTime)
                    {
                        this.debug('Loading from file cache: ' + sheet.href);
                        
                        var cacheUri = NetUtil.newURI(cacheFile).spec;
                        this.localCache.sheetPaths[sheet.href] = cacheUri;
                        this.injectSheet(cacheUri, sheet);
                        
                        if (loadDuplicates)
                        {
                            this._loadDupeSheets(sheet, cacheUri);
                        }
                        
                        return;
                    }
                }
            }
            
            this.debug('Loading new version: ' + sheet.href);
            
            // Grab the contents of the stylesheet
            this.readFile(sheet.href, function(data)
            {
                var _parseCallback = function(e, root)
                {
                    // Validate parsed result
                    if (e)
                    {
                        return this.errorLess(e, sheet.href);
                    }

                    // If we have a callback this is a call from the less parser
                    // and we should just return the data it wants.
                    if ( ! isInternalCall)
                    {
                        var bogus = { local: false, lastModified: null, remaining: 0 };
                        callback(e, root, data, sheet, bogus, sheet.href);
                    }
                    else // Otherwise it's an internal (ko.less) call
                    {
                        try
                        {
                            var parsedCss = root.toCSS();
                        }
                        catch (e)
                        {
                            if ("extract" in e)
                            {
                                return this.errorLess(e, sheet.href);
                            }
                            else
                            {
                                return this.exception(e,'Error converting less to css in ' + sheet.href);
                            }
                        }

                        // Write it to cache
                        try
                        {
                            var cacheFile = this.cache.writeFile(sheet.href, parsedCss, true);
                            var cacheUri = NetUtil.newURI(cacheFile).spec;
                        }
                        catch (e)
                        {
                            return this.exception(e, 'Error creating cache for ' + sheet.href);
                        }

                        this.localCache.sheetPaths[sheet.href] = cacheUri;
                        this.injectSheet(cacheUri, sheet);

                        if (loadDuplicates)
                        {
                            this._loadDupeSheets(sheet, cacheUri);
                        }
                    }
                };

                // Run it through the LESS parser
                try
                {
                    var contents = {};
                    contents[sheet.href] = data;
                    
                    new(less.Parser)({
                        optimization: less.optimization,
                        paths: [sheet.href.replace(/[^/]*$/, '')],
                        mime: sheet.type,
                        filename: sheet.href,
                        sheet: sheet,
                        contents: contents,
                        dumpLineNumbers: less.dumpLineNumbers
                    }).parse(data, _parseCallback.bind(this));
                }
                catch (e)
                {
                    this.error('Parsing error for ' + sheet.href + ': ' + e.message);
                }
                
            }.bind(this));
        },
        
        /**
         * Load duplicate sheets
         * 
         * @param   {Object} sheet    
         * @param   {String} loadHref 
         * 
         * @returns {Void} 
         */
        _loadDupeSheets: function ko_less_loadDupeSheets(sheet, loadHref)
        {
            if ( ! (sheet.href in this.sheets))
            {
                return;
            }
            
            for (let [,dupeSheet] in Iterator(this.sheets[sheet.href]))
            {
                if (dupeSheet == sheet)
                {
                    continue;
                }
                
                this.injectSheet(loadHref, dupeSheet);
            }
        },
        
        /**
         * Inject a sheet into XUL using the given filePath
         * 
         * @param   {String} fileUri
         * @param   {Object} sheet    
         * 
         * @returns {Void} 
         */
        injectSheet: function ko_less_injectSheet(fileUri, sheet)
        {
            var cssSheet = sheet.previousSibling || {};
            var ts = Math.round(Date.now() / 1000);
            
            if (cssSheet._lessParent == sheet)
            {
                // Replace existing sheet href with updated url and timestamp
                fileUri = fileUri + '?t=' + ts;
                cssSheet.nodeValue = cssSheet.nodeValue.replace(/(href=").*?"/i, 'href="' + fileUri + '"');
            }
            else
            {
                cssSheet = window.document.createProcessingInstruction(
                            'xml-stylesheet', 'type="text/css" href="' + fileUri + '"');
                cssSheet._lessParent = sheet;
                sheet.parentNode.insertBefore(cssSheet, sheet);
            }
            
            var time = Date.now();
            this.debug('Loaded ' + (time - this.timer) + 'ms after init: ' + fileUri);
            
            // Perfect time to cache the sheet hierarchy
            this.cache.writeFile('hierarchy.json', JSON.stringify(this.hierarchy));
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
            getFile: function ko_less_cache_getFile(fileUri)
            {
                if (fileUri in self.localCache.getFile)
                {
                    return self.localCache.getFile[fileUri];
                }
                
                var cacheUri = fileUri;
                
                // Convert path to relative path, if possible
                if (cacheUri.match(/\/|\\/))
                {
                    try
                    {
                        let _cacheUri = NetUtil.newURI(cacheUri);
                        if ((_cacheUri instanceof Ci.nsIFileURL))
                        {
                            let ProfD = Services.dirsvc.get("ProfD", Ci.nsIFile);
                            if (ProfD.contains(_cacheUri.file, true))
                            {
                                cacheUri = _cacheUri.file.getRelativeDescriptor(ProfD);
                            }

                            let AppD = Services.io.newURI("resource://app/", null, null)
                                        .QueryInterface(Ci.nsIFileURL).file;
                            if (AppD.contains(_cacheUri.file, true))
                            {
                                cacheUri = _cacheUri.file.getRelativeDescriptor(AppD);
                            }
                        }
                    }
                    catch (e)
                    {
                        self.error('Error while resolving relative path for ' + cacheUri + "\n" + e.message);
                    }
                }

                cacheUri = cacheUri.replace(/\:/g, '');
                
                cacheUri = cacheUri.split(/\/|\\/);
                cacheUri.unshift("lessCache");
                
                // Create cache pointer
                var cacheFile = FileUtils.getFile("ProfD", cacheUri, true);
                
                self.debug('Resolved cache for "' + fileUri + '" as "' + cacheFile.path + '"');
                
                self.localCache.getFile[fileUri] = cacheFile;
                
                return cacheFile;
            },
            
            _writeTimer: null,
            
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
                    clearTimeout(this._writeTimer);
                    this._writeTimer = setTimeout(this.writeFile.bind(this, fileUri, data, true), 500);
                    return;
                }

                self.debug('Writing to ' + fileUri);
                
                var file = this.getFile(fileUri);
                
                if ( ! file)
                {
                    return false;
                }
                
                try
                {
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
                    
                    self.debug('Written to ' + fileUri);
                    
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
            clear: function ko_less_cache_clear()
            {
                self.warn('Clearing local and file cache');
                
                // Reset localCache
                for (let [,k] in Iterator(Object.keys(self.localCache)))
                {
                    self.localCache[k] = {};
                }
                
                // Clear file cache
                FileUtils.getFile("ProfD", ["lessCache"], true).remove(true);
            }
            
        },
        
        /**
         * Read a file using file uri, basically a shortcut for NetUtil.asyncFetch
         * 
         * @param   {String} fileUri  
         * @param   {Function} callback 
         * 
         * @returns {Void} 
         */
        readFile: function ko_less_readFile(fileUri, callback)
        {
            // Grab the contents of the stylesheet
            try
            {
                NetUtil.asyncFetch(fileUri, function(inputStream, status)
                {
                    // Validate result
                    if ( ! Components.isSuccessCode(status))
                    {
                        this.error("asyncFetch failed for uri: " + fileUri + " :: " + status);
                        return;
                    }
                    
                    // Parse contents
                    var data = NetUtil.readInputStreamToString(inputStream, inputStream.available());
                    
                    callback.call(this, data);
                }.bind(this));
            }
            catch (e)
            {
                this.error('Failed reading file: ' + fileUri + "\n" + e.message);
            }
        },
        
        /**
         * Resolve a file uri to a nsIFile. Note - if the uri points to a
         * file residing within a jar, the jar file is returned.
         * 
         * @param   {String} fileUri 
         * 
         * @returns {nsIFile|Boolean} 
         */
        resolveFile: function ko_less_resolveFile(fileUri)
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
            
            // Create nsIFile with path
            var file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
            file.initWithPath(filePath);
            
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
        resolveYoungestChild: function ko_less_resolveYoungestChild(href)
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
        
        /**
         * Log Debug Wrapper
         * 
         * @param   {String} message 
         * 
         * @returns {Void} 
         */
        debug: function ko_less_debug(message)
        {
            var time = Date.now();
            log.debug('ko.less {' + (time - this.timer) + '}: ' + message);
        },
        
        /**
         * Log Warn Wrapper
         *
         * @param   {String} message
         *
         * @returns {Void}
         */
        warn: function ko_less_warn(message)
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
        error: function ko_less_error(message, noBacktrace = false)
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
        exception: function ko_less_error(exception, message = "")
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
        errorLess: function ko_less_errorLess(e, href) {
            var error = [];
            
            var errorString = (
                e.message ||
                'There is an error in your .less file'
            ) + ' (' + (e.filename || href) + ")\n";
            
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
            
            this.error(errorString, (e.stack || e.extract));
        }
        
    };
    
    if (("less" in window) && "initialized" in window.less)
    {
        ko.less = new ko.less();
    }
    else
    {
        window.addEventListener('lessLoaded', function()
        {
            if ( ! ("initialized" in ko.less) || ! ko.less.initialized)
            {
                ko.less = new ko.less(); 
            }
        });
    }
    
}).apply();
