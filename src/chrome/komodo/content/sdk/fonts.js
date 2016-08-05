(function() {
    
    const {Cc, Ci}  = require("chrome");
    
    var fontTypes   = ["serif","sans-serif", /*"cursive", "fantasy",*/"monospace"];
    var fontLanguages = ['x-western','x-central-euro','ja','zh-TW',
                          'zh-CN','zh-HK','ko','x-cyrillic','x-baltic','el',
                          'tr','x-unicode','x-user-def','th','he','ar',
                          'x-devanagari','x-tamil'];
    
    // Known Mono fonts are partially matched
    var knownMonoFonts = ["AnkaCoder", "6x13", "Agave",
                          "Anonymous Pro", "Anonymous", "Camingo Code",
                          "Code New Roman", "Consolas", "Courier", "Courier New",
                          "Cousine", "Creep", "Cruft", "DEC Terminal Modern",
                          "Dina", "Eco Coding", "Effects Eighty", "Envy Code B",
                          "Envy Code R", "Envy Code R", "Fifteen", "Fira Code",
                          "Fixed6x13-dotted-zero", "Fixedsys", "FreshBold",
                          "GNU Freefont", "GNU Unifont", "GNUTypewriter", "Gohu",
                          "GohuFont", "Hack", "Happy Monkey", "Hasklig", "Hermit",
                          "IBM 3270", "Inconsolata", "Inconsolata-g", "Input",
                          "Iosevka", "KaiTi", "Lekton", "Lucida Console",
                          "Lucida Sans Typewriter", "M+", "M+ 1m", "Menlo", "Meslo",
                          "Meslo LG", "Monaco", "Nanum Gothic Coding", "NotCourierSans",
                          "Nouveau IBM", "OCR A Extended", "Office Code Pro", "Operator",
                          "Panic Sans", "Pragmata Pro", "Print Char 21", "ProFont",
                          "Profont", "Proggy Clean", "Quinze", "Raize", "Roboto",
                          "Smooth Pet", "Source Code Pro", "Sudo", "TeX Gyre Cursor",
                          "Telegrama", "Terminus", "Terminus", "Triskweline",
                          "Triskweline-Code", "UW ttyp0", "VGA Font", "VT323"];
    
    var cache;
    var cacheAge = 0;
    
    this.getMonoFonts = () =>
    {
        var fonts = this.getSystemFonts();
        return fonts.filter((v) =>
        {
            for (let known of knownMonoFonts)
            {
                if (v == known)
                    return true;
                if (v.toLowerCase().indexOf("mono") > 0)
                    return true;
            }
            
            return false;
        });
    };
    
    this.getSystemFonts = () =>
    {
        var timestamp = Math.floor(Date.now() / 1000);
        if (cache && timestamp - cacheAge < 60) // refresh every 60 seconds - 1 minute
        {
            return cache;
        }
        
        var enumerator = Cc["@mozilla.org/gfx/fontenumerator;1"].createInstance().QueryInterface(Ci.nsIFontEnumerator);
        var system = require("sdk/system");
        var strFontSpecs;
        var j;
        var fontmap = {};
        var fName = "";
        for (var i=0;i<fontLanguages.length;i++) {
            for (var t = 0; t < fontTypes.length; t++ )
            {
                // build and populate the font list for the newly chosen font type
                strFontSpecs = enumerator.EnumerateFonts(fontLanguages[i],
                                                         fontTypes[t],
                                                         {});
                for (j=0; j < strFontSpecs.length; j++) {
                    fName = strFontSpecs[j];
                    if (typeof(fontmap[fName])=='undefined' ||
                        !fontmap[fName]) {
                        fontmap[fName]=fName;
                    }
                }
            }
        }
        
        if (system.platform != "Linux")
        {
            // Did we miss any?
            // Assume unrecognized fonts are proportional
            var allLanguages = enumerator.EnumerateAllFonts({});
            var lim = allLanguages.length;
            for (i = 0; i < lim; i++) {
                fName = allLanguages[i];
                if (!fName) continue;
                fontmap[fName]=fName;
            }
        }
    
        cache = Object.keys(fontmap);
        cacheAge = timestamp;
        
        return cache;
    };
    
    this.getEffectiveFont = (fontlist) =>
    {
        fontstack = fontlist.split(",");
        for (let i=0;i<fontstack.length;i++)
            fontstack[i] = fontstack[i].replace(/['"]/g, '');

        var fonts = this.getSystemFonts();

        for (let font of fontstack)
        {
            if (fonts.indexOf(font) != -1)
                return font;
        }
        
        return fontstack.slice(-1)[0];
    };
    
}).apply(module.exports);