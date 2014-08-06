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
    const randomColor   = require("contrib/randomColor");
    const log           = require("ko/logging").getLogger("ko-fileicons");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    var self = icons    = this;

    this.handlers = {};

    this.handlers.fileicon = new function()
    {
        var init = () =>
        {
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
                    exts = exts.split(",");

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
                                                    .substr(0,4).toUpperCase();
                }
                else
                {
                    log.debug("Using language name for ext");
                    info.ext = info.language.substr(0,4).toUpperCase();
                }

                log.debug("Generating color based on language");
                info.color = randomColor({luminosity: 'dark'},info.language);
            }

            return info;
        }

        var getInfo = (uri, namespace) =>
        {
            log.debug("Parsing info");

            var preset = getPreset("Unknown");
            var info = {
                ext: "?",
                language: "Unknown",
                size: 16,
                color: preset ? preset.color : randomColor({luminosity: 'dark'},"Unknown")
            };

            if (namespace == "language")
                return getInfoFromLanguage(uri, info);

            log.debug("Parsing info from ext");

            var pattern = /(.*\.([a-z0-9]*)).*?(?:size=(\d*)|$)/i;
            var match = uri.match(pattern);
            if ( ! match) return false;

            var ext = match[2];
            info.ext = match[2].substr(0,4).toUpperCase();
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

        this.getIconForUri = (uri, namespace) =>
        {
            var info = getInfo(uri, namespace);
            if ( ! info) return false;

            var filename = (info.language + info.ext + info.size).replace(/\W/g, '');
            info.size = Math.round(info.size * window.devicePixelRatio);

            var pngFile = FileUtils.getFile("ProfD", ["icons", "fileicons", filename + ".png"], true);
            if (pngFile.exists())
            {
                icons.getIconForUri.cached[uri] = ioService.newFileURI(pngFile).spec;
                return pngFile;
            }

            var svgPresetFile = FileUtils.getFile("AChrom", ["icons","default","fileicons", info.language.toLowerCase() + ".svg"], true);
            if (svgPresetFile.exists())
            {
                log.debug("Creating icon from SVG Preset: " + svgPresetFile.path);
                icons.createPngFromSvg(svgPresetFile.path, pngFile.path, {size: info.size, forceSize: true});
                return svgPresetFile;
            }

            var templateFile = FileUtils.getFile("AChrom", ["icons","default","fileicons", "template.svg"], true);
            info["font-size"] = (info.size / 100) * (8 - (info.ext.length || 1));

            var tmpSvg = pngFile.path + ".template.svg";
            icons.createIconFromTemplate(tmpSvg, templateFile.path, info);
            icons.createPngFromSvg(tmpSvg, pngFile.path, {size: info.size, delete: true});

            return "file://" + tmpSvg;
        }

        init();
    }

    this.handlers["app-svg"] = new function()
    {
        this.getIconForUri = (uri, namespace, relativePath) =>
        {
            if (relativePath.substr(-3) != "svg")
                return false;
            
            relativePath = relativePath.split("/");
            var iconFile = FileUtils.getFile("AChrom", relativePath, true);
            if ( ! iconFile.exists)
                return false;

            var savePath = ["icons", "app-svg"].concat(relativePath);
            var pngFile = FileUtils.getFile("ProfD", savePath, true);

            if (pngFile.exists())
            {
                icons.getIconForUri.cached[uri] = ioService.newFileURI(pngFile).spec;
                return pngFile;
            }
            else
            {
                // Todo: Handle size and scaling
                icons.createPngFromSvg(iconFIle.path, pngFile.path);
                return iconFile.path;
            }
        }
    }

    this.forceSvgSize = (svgData, size = 16) =>
    {
        var sizeFrom = svgData.match(/width="(\d+)/);
        sizeFrom = sizeFrom ? parseInt(sizeFrom[1]) : 16;

        if (size == sizeFrom) return false;
        
        var scale = size / sizeFrom;
        svgData = svgData.replace('width="'+sizeFrom+'"', 'width="'+size+'"');
        svgData = svgData.replace('height="'+sizeFrom+'"', 'height="'+size+'"' + "\n" + 
                                                            'transform="scale('+scale+')"');

        return svgData;
    }

    this.createIconFromTemplate = (iconPath, templatePath, vars) =>
    {
        log.debug("Creating file from template: " + iconPath);

        if (("size" in vars) && ! ("scale" in vars))
            vars.scale = vars.size / 16;

        // Read and parse template
        var data = ioFile.read(templatePath);
        for (let k in vars)
        {
            let r = new RegExp("{{"+k+"}}", "ig")
            data = data.replace(r, vars[k]);
        }

        // Save to temporary SVG file
        var textStream = ioFile.open(iconPath, "w");
        textStream.write(data);
        textStream.close();
    }

    /**
     * If using a custom size it assumes the following:
     *
     * - Svg has a root <svg> element with the attributes "width" and "height"
     * - Both width and height use the same value (ie. svg canvas is square)
     * - the root <svg> element is not using a transform attribute
     */
    this.createPngFromSvg = (svgPath, savePath, opts = {}, callback = false) =>
    {
        log.debug("Creating png: " + savePath);

        if (opts.size && opts.forceSize)
        {
            log.debug("Attempting to force size to " + opts.size);

            var svgData = ioFile.read(svgPath);
            svgData = this.forceSvgSize(svgData, opts.size);
            
            if (svgData)
            {
                log.debug("Saving temp svg with forced size");

                svgPath = savePath + ".forceSize.svg";
                opts.delete = true;

                // Save to temporary SVG file
                var textStream = ioFile.open(svgPath, "w");
                textStream.write(svgData);
                textStream.close();
            }
        }

        var canvas = document.getElementById('canvas-proxy').cloneNode();
        canvas.setAttribute("width", opts.size);
        canvas.setAttribute("height", opts.size);
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

            if (opts.delete)
            {
                log.debug("Deleting: " + svgPath);
                ioFile.remove(svgPath);
            }

            if (callback) callback();
        }
        
        img.src = "file://" + svgPath;
    }

    this.getIconForUri = (uri) =>
    {
        if ( ! ("cached" in this.getIconForUri))
            this.getIconForUri.cached = {};

        log.debug("Retrieving icon for " + uri);

        if (uri in this.getIconForUri.cached)
            return this.getIconForUri.cached[uri];

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
                return this.handlers.fileicon.getIconForUri(uri, namespace, relativePath);
                break;
            case "app-svg":
                return this.handlers["app-svg"].getIconForUri(uri, namespace, relativePath);
                break;
        }
    }

}).apply(module.exports);
