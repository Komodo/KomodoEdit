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
                let [name, exts] = _prefs.getString(x).split(":");
                exts = exts.split(",");

                for (let _ext in exts)
                    getExtMapping.cached[exts[_ext]] = name;
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
                info.language = match[1];
                if (match.length == 3 && match[2]) info.size = match[2];

                var preset = getPreset(info.language);
                if (preset)
                {
                    info.ext = preset.ext;
                    info.color = preset.color;
                }
                else // Get file extension from file associations
                {
                    var langPatterns = {};
                    langSvc.patternsFromLanguageName(info.language, langPatterns, {});
                    if (langPatterns && langPatterns.value && langPatterns.value.length)
                    {
                        info.ext = langPatterns.value[0].replace(/^\*\./, '')
                                                        .split('.').pop()
                                                        .substr(0,4).toUpperCase();
                    }
                    else
                    {
                        info.ext = info.language.substr(0,4).toUpperCase();
                    }

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
                var ext = match[2];
                info.ext = match[2].substr(0,4).toUpperCase();
                var lang = langSvc.suggestLanguageForFile(match[1]);
                if (lang)
                {
                    info.language = lang;
                    if (match.length == 4) info.size = match[3];

                    var preset = getPreset(info.language);
                    if (preset)
                    {
                        info.color = preset.color;
                        info.ext = preset.ext;
                    }
                    else
                        info.color = randomColor({luminosity: 'dark'},info.language);
                }
                else
                {
                    var extMapping = getExtMapping(ext);
                    if (extMapping)
                    {
                        info.ext = extMapping.toUpperCase();
                        info.color = randomColor({luminosity: 'dark'},info.ext);
                    }
                    else if (isColorWhitelisted(ext))
                    {
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

        if (uri in this.getIconForUri.cached)
            return this.getIconForUri.cached[uri];

        var info = parseFileInfo(uri);

        var file = FileUtils.getFile("ProfD", ["fileicons", info.language + info.ext + info.size + ".svg"], true);
        if ( ! file.exists())
        {
            // Read template file
            var template = FileUtils.getFile("AChrom", ["icons","default","fileicons", "template.svg"], true);

            var data = ioFile.read(template.path);

            data = data.replace(/{{ext}}/g, info.ext);
            data = data.replace(/{{color}}/g, info.color);
            data = data.replace(/{{size}}/g, info.size);

            var fontScaleFactor = 45;
            if (info.ext.length == 3) fontScaleFactor = 40;
            if (info.ext.length == 4) fontScaleFactor = 30;
            var fontSize = Number((info.size / 100) * fontScaleFactor).toFixed(1);
            data = data.replace(/{{font-size}}/g, fontSize);

            var textStream = ioFile.open(file.path, "w");
            textStream.write(data);
            textStream.close();
        }

        this.getIconForUri.cached[uri] = ioService.newFileURI(file).spec;

        return file;
    }

    init();

}).apply(module.exports);
