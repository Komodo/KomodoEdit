/**
 * @module icons
 */
(function() {

    const {Cc, Ci, Cu}  = require("chrome");
    
    Cu.import("resource://gre/modules/NetUtil.jsm");
    Cu.import("resource://gre/modules/Services.jsm");
    Cu.import("resource://gre/modules/FileUtils.jsm");

    const langSvc   = Cc['@activestate.com/koLanguageRegistryService;1']
                        .getService(Ci.koILanguageRegistryService);
    const prefs     = Cc['@activestate.com/koPrefService;1']
                        .getService(Ci.koIPrefService).prefs;
    const ioService = Cc["@mozilla.org/network/io-service;1"]
                        .getService(Ci.nsIIOService);

    const ioFile        = require("sdk/io/file");
    const sdkQuery      = require("sdk/querystring");
    const sdkUrl        = require("sdk/url");
    const randomColor   = require("contrib/randomColor");
    const log           = require("ko/logging").getLogger("ko-fileicons");
    const timers        = require("sdk/timers");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var self = this, icons = this;

    this.handlers = {};

    this.handlers.fileicon = new function()
    {
        var init = () =>
        {
            // Clear the icon cache if Komodo has been up/down-graded
            var cacheVersion = prefs.getString('iconCacheVersion', '');
            var infoSvc = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
            var platVersion = infoSvc.buildPlatform + infoSvc.buildNumber;
            if (cacheVersion != platVersion)
            {
                prefs.setStringPref('iconCacheVersion', platVersion);
                let file = FileUtils.getFile("ProfD", ["icons"], true);

                try
                {
                    if (file.exists())
                    {
                        log.warn("Clearing icon cache");
                        file.remove(true);
                    }
                }
                catch (e)
                {
                    log.warn("Failed cleaning up icons cache, icons might not be updated properly");
                }
            }

            var onPrefChanged = { observe: (subject, topic, data) => {
                delete self.cached;

                switch (topic) {
                    case 'fileicons_presets':
                        delete getPreset.cached;
                        break;
                    case 'fileicons_color_whitelist':
                        delete isColorWhitelisted.cached;
                        break;
                    case 'fileicons_ext_mapping':
                        delete getExtMapping.cached;
                        break;
                }
            }};

            prefs.prefObserverService.addObserver(onPrefChanged, "fileicons_presets", false);
            prefs.prefObserverService.addObserver(onPrefChanged, "fileicons_color_whitelist", false);
            prefs.prefObserverService.addObserver(onPrefChanged, "fileicons_ext_mapping", false);
        }

        var getPreset = (language) =>
        {
            if ( ! ("cached" in getPreset))
            {
                getPreset.cached = {};
                var _prefs = prefs.getPref('fileicons_presets');
                for (let x=0;x<_prefs.length;x++)
                {
                    let [lang,ext,color] = _prefs.getString(x).split(":");
                    getPreset.cached[lang.toLowerCase()] = {ext: ext, color: color};
                }
            }

            if (language.toLowerCase() in getPreset.cached)
                return getPreset.cached[language.toLowerCase()];
        }

        var getExtMapping = (ext) =>
        {
            if ( ! ("cached" in getExtMapping))
            {
                getExtMapping.cached = {};
                var _prefs = prefs.getPref('fileicons_ext_mapping');
                for (let x=0;x<_prefs.length;x++)
                {
                    let [name, color, exts] = _prefs.getString(x).split(":");
                    exts = (exts||"").split(",");

                    for (let _ext in exts)
                        getExtMapping.cached[exts[_ext]] = {ext: name, color: color};
                }
            }

            if (ext.toLowerCase() in getExtMapping.cached)
                return getExtMapping.cached[ext.toLowerCase()];

            return false;
        }

        var isColorWhitelisted = (ext) =>
        {
            if ( ! ("cached" in isColorWhitelisted))
            {
                var pref = prefs.getStringPref('fileicons_color_whitelist');
                isColorWhitelisted.cached = pref.split(":");
            }

            return isColorWhitelisted.cached.indexOf(ext.toLowerCase()) !== -1;
        }

        var getInfoFromLanguage = (uri, info) =>
        {
            log.debug("Parsing info from language");

            var pattern = /ko-language\/([a-z0-9+#\-_\. ]*)\??(?:size=(\d*)|$)/i;
            var match = uri.match(pattern);
            if ( ! match) return false;

            info.language = match[1];
            if (match.length == 3 && match[2]) info.size = match[2];

            var preset = getPreset(info.language);
            if (preset)
            {
                log.debug("Matched Preset: " + info.language);
                info.ext = preset.ext;
                info.color = preset.color;
            }
            else // Get file extension from file associations
            {
                log.debug("Matching using file association");

                var langPatterns = {};
                langSvc.patternsFromLanguageName(info.language, langPatterns, {});
                if (langPatterns && langPatterns.value && langPatterns.value.length)
                {
                    log.debug("Using file association for ext");
                    info.ext = langPatterns.value[0].replace(/^\*\./, '')
                                                    .split('.').pop()
                                                    .substr(0,3).toUpperCase();
                }
                else
                {
                    log.debug("Using language name for ext");
                    info.ext = info.language.substr(0,3).toUpperCase();
                }

                log.debug("Generating color based on language");
                info.color = randomColor({luminosity: 'dark'},info.language);
            }

            return info;
        }

        var getInfo = (uri, namespace) =>
        {
            log.debug("Parsing info");

            var url = sdkUrl.URL(uri);
            var params = sdkQuery.parse(url.search.substr(1));

            var preset = getPreset("Unknown");
            var info = {
                ext: "?",
                language: "Unknown",
                size: params.size || 16,
                color: preset ? preset.color : randomColor({luminosity: 'dark'},"Unknown")
            };

            if (namespace == "language")
                return getInfoFromLanguage(uri, info);

            log.debug("Parsing info from ext");

            var pattern = /(.*\.([a-z0-9]*)).*?(?:size=(\d*)|$)/i;
            var match = uri.match(pattern);
            if ( ! match) return info;

            var ext = match[2];
            info.ext = match[2].substr(0,3).toUpperCase();
            if (match.length == 4) info.size = match[3];
            var lang = langSvc.suggestLanguageForFile(match[1]);
            if (lang)
            {
                log.debug("Found related language: " + lang);

                info.language = lang;
                var preset = getPreset(info.language);
                if (preset)
                {
                    log.debug("Using preset for color and ext");
                    info.color = preset.color;
                    info.ext = preset.ext;
                }
                else
                {
                    log.debug("Generating color based on language");
                    info.color = randomColor({luminosity: 'dark'},info.language);
                }
            }
            else
            {
                log.debug("Could not find related language");

                var extMapping = getExtMapping(ext);
                if (extMapping)
                {
                    log.debug("Setting ext and color using ext mapping");
                    info.ext = extMapping.ext.toUpperCase();
                    info.color = extMapping.color;
                }
                else if (isColorWhitelisted(ext))
                {
                    log.debug("Ext is color whitelisted, generating color based on ext");
                    info.color = randomColor({luminosity: 'dark'},info.ext);
                }
            }

            return info;
        }

        this.getIconForUri = (uri, namespace, relativePath, callback) =>
        {
            var info = getInfo(uri, namespace);
            if ( ! info) return callback(false);

            var filename = (info.language + info.ext + info.size).replace(/\W/g, '');
            info.size = Math.round(info.size * window.devicePixelRatio);

            var pngFile = FileUtils.getFile("ProfD", ["icons", "fileicons", filename + ".png"], true);
            if (pngFile.exists())
            {
                icons.getIconForUri.cached[uri] = ioService.newFileURI(pngFile).spec;
                timers.setTimeout(function() {
                    try
                    {
                        callback(pngFile);
                    } catch (e)
                    {
                        log.exception(e, "Exception in timeout for sdk/icons.handlers.fileicon.getIconForUri()");
                    }
                },0);
                return;
            }

            var svgPresetFile = FileUtils.getFile("AChrom", ["icons","default","fileicons", info.language.toLowerCase() + ".svg"], true);
            if ( ! svgPresetFile.exists())
                svgPresetFile = FileUtils.getFile("AChrom", ["icons","default","fileicons", info.ext + ".svg"], true);
                
            if (svgPresetFile.exists())
            {
                log.debug("Creating icon from SVG Preset: " + svgPresetFile.path);
                icons.createPngFromSvg(svgPresetFile.path, pngFile.path, {}, {size: info.size}, function()
                {
                    callback(pngFile);
                });
                return;
            }

            var templateFile = FileUtils.getFile("AChrom", ["icons","default","fileicons", "template.svg"], true);
            if (info.size == 16)
                info["font-size"] = "0.9";
            else
                info["font-size"] = (info.size / 100) * (8 - (info.ext.length || 1));

            var tmpSvg = pngFile.path + ".template.svg";
            icons.createIconFromTemplate(tmpSvg, templateFile.path, info, function()
            {
                icons.createPngFromSvg(tmpSvg, pngFile.path, {delete: true}, {size: info.size}, function()
                {
                    callback(pngFile);
                });
            });
        }

        init();
    }

    this.handlers.svg = new function()
    {
        this.getIconForUri = (uri, namespace, relativePath, callback) =>
        {
            var url = sdkUrl.URL(uri);
            relativePath = url.pathname.split("/").slice(3);
            if (relativePath.slice(-1)[0].substr(-4) != ".svg")
                return callback();
            namespace = relativePath.shift();
            
            // Generate unique id for query based on the params
            var params = sdkQuery.parse(url.search.substr(1));
            params.size = Math.round((params.size || 16) * window.devicePixelRatio);
            
            if ( ! ("fill" in params) &&  ! ("color" in params))
            {
                var preset = ("preset" in params) ? params.preset : 'base';
                if (preset == "hud")
                {
                    log.debug("Using hud preset");
                    
                    var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
                    var scheme = schemeService.getScheme(prefs.getString("editor-scheme"));
                    params.fill = scheme.isDarkBackground ? "#C8C8C8" : "#4B4B4B";
                }
                else if (prefs.getString("iconset-" + preset + "-defs", '-1') != '-1')
                {
                    log.debug("Using "+preset+" preset defs");
                    params.defs = prefs.getStringPref("iconset-" + preset + "-defs");
                }
                else if (prefs.getString("iconset-base-defs", '-1') != '-1')
                {
                    log.debug("Using base preset defs");
                    params.defs = prefs.getStringPref("iconset-base-defs");
                }
                else 
                {
                    if (prefs.getString("iconset-" + preset + "-color", '-1') == '-1')
                    {
                        preset = "base";
                    }
                    
                    log.debug("Using "+preset+" preset color");
                    
                    params.fill = prefs.getStringPref("iconset-" + preset + "-color");
                }
            }

            if ("color" in params)
            {
                log.debug("Using custom color");
                
                params.fill = params.color;
                delete params.color;
            }

            if ("defs" in params)
            {
                log.debug("Using custom defs");
                
                var defs = params.defs;
                var path = "chrome://komodo/skin/svg/defs/" + defs + ".xml";
                params.defs = prefs.getString("ko-svg-defs-" + defs, path);
            }
            
            var filePointer;
            try
            {
                var iconFile = FileUtils.getFile(namespace, relativePath, true);
                if (iconFile.exists())
                    filePointer = iconFile.path;
            } catch (e)
            {
                log.debug("Failed calling getFile from file path: " + relativePath.join("/"));
            }

            if ( ! filePointer)
                filePointer = namespace + "://" + relativePath.join("/");

            log.debug("Filepointer: " + filePointer);

            var id = hash(params);
            relativePath[relativePath.length-1] = id + "-" + relativePath[relativePath.length-1] + ".png";

            var savePath = ["icons", namespace].concat(relativePath);
            var pngFile = FileUtils.getFile("ProfD", savePath, true);

            if (pngFile.exists())
            {
                icons.getIconForUri.cached[uri] = ioService.newFileURI(pngFile).spec;
                timers.setTimeout(function() {
                    try
                    {
                        callback(pngFile);
                    } catch (e)
                    {
                        log.exception(e, "Exception in timeout for sdk/icons.handlers.svg.getIconForUri()");
                    }
                },0);
            }
            else
            {
                return icons.createPngFromSvg(filePointer, pngFile.path, {}, params, function()
                {
                    callback(pngFile);
                });
            }
        }
    }

    this.forceSvgAttribute = (svgData, attribute, value) =>
    {
        log.debug("Overriding svg attribute " + attribute + " to: " + value);
        svgData = unescape(encodeURIComponent(svgData));
        
        if (attribute == "scaleAuto")
        {
            var sizeFrom = svgData.match(/width="(\d+)/);
            sizeFrom = sizeFrom ? parseInt(sizeFrom[1]) : 16;
            if (value == sizeFrom) return false;
            var scale = value / sizeFrom;
            return this.forceSvgAttribute(svgData, "transform", 'scale('+scale+')');
        }

        if (attribute == "_defs")
        {
            log.debug("Injecting defs");

            if (svgData.indexOf("</defs>") !== -1)
            {
                log.debug("Injecting into existing defs");
                svgData = svgData.replace('</defs>', value + "</defs>");
            }
            else
            {
                log.debug("Creating new defs");
                svgData = svgData.replace(/(<svg[\s\S]*?>)/i, "$1<defs>" + value + "</defs>");
            }

            return svgData;
        }

        var reAttr = attribute + '="[^]*?"';
        var re = new RegExp("<svg([^]*?)" + reAttr);

        var match = svgData.match(re);
        
        var _svgData;
        if (match && match[1].indexOf(">") == -1)
            _svgData = svgData.replace(re, "<svg$1" + attribute + '="'+value+'"');
        else
            _svgData = svgData.replace("<svg", "<svg\n" + attribute + '="'+value+'"');

        if (_svgData != svgData)
        {
            log.debug("Success");
            return _svgData;
        }

        return false;
    }

    this.createIconFromTemplate = (iconPath, templatePath, vars, callback) =>
    {
        log.debug("Creating file from template: " + iconPath);
        log.debug(templatePath);

        if (("size" in vars) && ! ("scale" in vars))
            vars.scale = vars.size / 16;

        // Read and parse template
        readFile(templatePath, function(data)
        {
            for (let k in vars)
            {
                let r = new RegExp("{{"+k+"}}", "ig")
                data = data.replace(r, vars[k]);
            }

            // Save to temporary SVG file
            var textStream = ioFile.open(iconPath, "w");
            textStream.write(data);
            textStream.close();

            callback();
        });
    }

    /**
     * If using a custom size it assumes the following:
     *
     * - Svg has a root <svg> element with the attributes "width" and "height"
     * - Both width and height use the same value (ie. svg canvas is square)
     * - the root <svg> element is not using a transform attribute
     */
    this.createPngFromSvg = (svgPath, savePath, opts = {}, attrs = false, callback = false) =>
    {
        if ( ! attrs)
            return _createPngFromSvg(false, svgPath, savePath, opts, {}, callback);

        if ("defs" in attrs)
        {
            try
            {
                readFile(attrs.defs, function(data)
                {
                    delete attrs.defs;
                    attrs._defs = data;

                    this.createPngFromSvg(svgPath, savePath, opts, attrs, callback);
                }.bind(this));
                return;
            }
            catch (e)
            {
                log.exception(e);
                log.warn("Grabbing defs failed, continuing without custom defs");
            }
        }

        log.debug("Creating png: " + savePath);
        readFile(svgPath, function(svgData)
        {
            _createPngFromSvg(svgData, svgPath, savePath, opts, attrs, callback);
        });
    }

    var _createPngFromSvg = (svgData, svgPath, savePath, opts = {}, attrs = false, callback = false) =>
    {
        var dirty = false;
        if (attrs)
        {
            if ("size" in attrs)
            {
                attrs.scaleAuto = parseInt(attrs.size);
                attrs.width = parseInt(attrs.size);
                attrs.height = parseInt(attrs.size);
                attrs.viewBox = "0 0 " + attrs.size + " " + attrs.size;
                delete attrs.size;
            }

            for (let k in attrs)
            {
                log.debug("Forcing " + k);

                let _svgData = this.forceSvgAttribute(svgData, k, attrs[k]);
                if (_svgData)
                    svgData = _svgData;
            }

            dirty = true;
        }

        if (dirty && svgData)
        {
            log.debug("Saving temp svg with forced attributes");

            if (opts.delete)
                opts.deleteAlso = svgPath

            svgPath = savePath + ".forcedAttrs.svg";
            opts.delete = true;

            // Save to temporary SVG file
            var textStream = ioFile.open(svgPath, "w");
            textStream.write(svgData);
            textStream.close();
        }

        var canvas = document.getElementById('canvas-proxy').cloneNode();
        canvas.setAttribute("width", attrs.width || 16);
        canvas.setAttribute("height", attrs.height || 16);
        var ctx = canvas.getContext('2d');

        var img = new window.Image();
        img.onload = function() {
            ctx.drawImage(img, 0, 0);
            var dataURL = canvas.toDataURL("image/png");
            var data = window.atob( dataURL.substring( "data:image/png;base64,".length ) );

            log.debug("Saving PNG: " + savePath);

            var byteStream = ioFile.open(savePath, "wb");
            byteStream.write(data);
            byteStream.close();

            // Give plenty of time for any simultanious queries to finish using
            // these files, we're in no hurry to delete them
            timers.setTimeout(function()
            {
                try
                {
                    if (opts.delete)
                    {
                        log.debug("Deleting: " + svgPath);
                        ioFile.remove(svgPath);
                    }
    
                    if (opts.deleteAlso)
                    {
                        log.debug("Also deleting: " + opts.deleteAlso);
                        ioFile.remove(opts.deleteAlso);
                    }
                } catch (e)
                {
                    // Don't report errors if the file has already been deleted
                    if (e.name != "NS_ERROR_FILE_UNRECOGNIZED_PATH")
                    {
                        log.exception(e, "Exception in timeout for sdk/icons._createPngFromSvg()");
                    }
                }
            }, 1000);

            if (callback) callback();
        }
        
        img.src = "file://" + svgPath;

        return svgPath;
    }

    this.getIconForUri = (uri, callback) =>
    {
        if ( ! ("cached" in this.getIconForUri))
            this.getIconForUri.cached = {};

        log.debug("Retrieving icon for " + uri);

        if (uri in this.getIconForUri.cached) {
            log.debug("Returning cached version");
            return callback(self.getIconForUri.cached[uri]);
        }

        var namespace = "";
        var relativePath = "";
        var matched;
        var match = uri.match(/^[a-z0-9_\-]+:\/\/ko-([a-z0-9_\-]+)(\/.+$)/i);
        if (match) [matched, namespace, relativePath] = match;

        switch (namespace)
        {
            case "fileicon":
            case "language":
            default:
                try
                {
                    return self.handlers.fileicon.getIconForUri(uri, namespace, relativePath, callback);
                } catch (e)
                {
                    log.exception(e, "failed retrieving fileicon");
                    callback();
                }
                break;
            case "svg":
                try
                {
                    return self.handlers.svg.getIconForUri(uri, namespace, relativePath, callback);
                } catch (e)
                {
                    log.exception(e, "failed retrieving svg icon");
                    callback();
                }
                break;
        }
    }

    var readFile = (filePointer, callback) =>
    {
        if ((typeof filePointer) == "string" && ! filePointer.match(/^[a-z_\-]+:\/\//))
            filePointer = "file://" + filePointer;
        var path = (typeof filePointer) == "string" ? filePointer : filePointer.path;

        if (path in readFile.cache)
        {
            callback(readFile.cache[path]);
            return;
        }

        NetUtil.asyncFetch(filePointer, function(inputStream, status)
        {
            // Validate result
            if ((status & 0x80000000) != 0) // https://developer.mozilla.org/en/docs/Components.isSuccessCode
            {
                log.error("asyncFetch failed for file: " + path + " :: " + status);
                return callback();
            }

            // Parse contents
            var data = NetUtil.readInputStreamToString(inputStream, inputStream.available());
            readFile.cache[path] = data;
            callback(data);
        });
    }
    
    readFile.cache = {};

    var hash = (str) =>
    {
        if (typeof str != "string")
            str = JSON.stringify(str);

        if ( ! ("converter" in hash))
        {
            hash.converter = Cc["@mozilla.org/intl/scriptableunicodeconverter"]
                                .createInstance(Ci.nsIScriptableUnicodeConverter);
        }

        hash.converter.charset = "UTF-8";
        
        var data = hash.converter.convertToByteArray(str, {});
        var ch = Cc["@mozilla.org/security/hash;1"].createInstance(Ci.nsICryptoHash);
        ch.init(ch.MD5);
        ch.update(data, data.length);
        var res = ch.finish(false);

        function toHexString(charCode)
        {
            return ("0" + charCode.toString(16)).slice(-2);
        }

        return [toHexString(res.charCodeAt(i)) for (i in res)].join("");
    }

}).apply(module.exports);
