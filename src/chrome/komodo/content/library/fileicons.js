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

    var fileicons       = this;

    var init = () =>
    {
        prefs.prefObserverService.addObserver(onPrefChanged, "fileicons_presets", false);
        prefs.prefObserverService.addObserver(onPrefChanged, "fileicons_color_whitelist", false);
        prefs.prefObserverService.addObserver(onPrefChanged, "fileicons_ext_mapping", false);
    }

    var onPrefChanged = { observe: (subject, topic, data) => {
        delete fileicons.cached;

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
    }}

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

    var matchers = [
        {
            // ko-language
            pattern: /ko-language\/([a-z0-9+#\-_\. ]*)\??(?:size=(\d*)|$)/i,
            parseMatch: function(uri, match, info)
            {
                log.debug("Parsing ko-language uri");

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
        },
        {
            // Regular path
            pattern: /(.*\.([a-z0-9]*)).*?(?:size=(\d*)|$)/i,
            parseMatch: function(uri, match, info)
            {
                log.debug("Parsing default uri");

                var ext = match[2];
                info.ext = match[2].substr(0,4).toUpperCase();
                var lang = langSvc.suggestLanguageForFile(match[1]);
                if (lang)
                {
                    log.debug("Found related language: " + lang);

                    info.language = lang;
                    if (match.length == 4) info.size = match[3];

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
        }
    ];

    var parseFileInfo = function(uri)
    {
        var preset = getPreset("Unknown");
        var info = {
            ext: "?",
            language: "Unknown",
            size: 16,
            color: preset ? preset.color : randomColor({luminosity: 'dark'},"Unknown")
        };

        for (let matcher of matchers)
        {
            let match = uri.match(matcher.pattern);
            if (match) return matcher.parseMatch(uri, match, info);
        }

        return info;
    }

    this.getIconForUri = function(uri)
    {
        if ( ! ("cached" in this.getIconForUri))
            this.getIconForUri.cached = {};

        log.debug("Retrieving icon for " + uri);

        if (uri in this.getIconForUri.cached)
            return this.getIconForUri.cached[uri];

        var info = parseFileInfo(uri);
        var filename = (info.language + info.ext + info.size).replace(/\W/g, '');
        info.size = Math.round(info.size * window.devicePixelRatio);

        var file = FileUtils.getFile("ProfD", ["fileicons", filename + ".png"], true);
        if ( ! file.exists())
        {
            log.debug("Creating file: " + file.path);
            var svg = FileUtils.getFile("ProfD", ["fileicons", filename + ".svg"], true);
            
            // Read template file
            var template = FileUtils.getFile("AChrom", ["icons","default","fileicons", "template.svg"], true);

            var data = ioFile.read(template.path);

            data = data.replace(/{{ext}}/g, info.ext);
            data = data.replace(/{{color}}/g, info.color);
            data = data.replace(/{{size}}/g, info.size);

            var fontSize = (info.size / 100) * (8 - (info.ext.length || 1));
            data = data.replace(/{{font-size}}/g, fontSize);

            var textStream = ioFile.open(svg.path, "w");
            textStream.write(data);
            textStream.close();

            //var canvas = document.createElement('canvas');
            var canvas = document.getElementById('canvas-proxy').cloneNode();
            canvas.setAttribute("width", info.size);
            canvas.setAttribute("height", info.size);
            var ctx = canvas.getContext('2d');

            var img = new window.Image();
            img.onload = function() {
                ctx.drawImage(img, 0, 0);
                var dataURL = canvas.toDataURL("image/png");
                var data = window.atob( dataURL.substring( "data:image/png;base64,".length ) );
                var byteStream = ioFile.open(file.path, "wb");
                byteStream.write(data);
                byteStream.close();

                fileicons.getIconForUri.cached[uri] = ioService.newFileURI(file).spec;

                if (svg.exists())
                    ioFile.remove(svg.path);
            }
            img.src = "file://" + svg.path;

            log.debug("Returning SVG:" + svg.path);

            return svg;
        }

        log.debug("Returning PNG: " + file.path);

        this.getIconForUri.cached[uri] = ioService.newFileURI(file).spec;

        return file;
    }

    init();

}).apply(module.exports);
