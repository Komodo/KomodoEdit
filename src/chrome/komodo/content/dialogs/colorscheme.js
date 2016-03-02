(function() {
    
    var $ = require("ko/dom");
    var prefs = require("ko/prefs");
    
    var Cc = Components.classes;
    var Ci = Components.interfaces;
    
    var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();
    var languageRegistry = Cc["@activestate.com/koLanguageRegistryService;1"].getService(Ci.koILanguageRegistryService);
    
    var log = require("ko/logging").getLogger("colorscheme-editor");
    
    var styleProperties =  {

        'CommonStyles': {
            locale: 'Common',
            fields: ['fore', 'back', 'bold', 'italic'],
            properties: [
                {
                    name: 'default_fixed',
                    locale: 'default font',
                    fields: ['back', 'fore', 'face', 'size', 'bold', 'italic', 'lineSpacing', 'useSelFore', 'caretLineVisible'],
                    explicit: { 'eolfilled': 0, 'hotspot': 0, 'useFixed': 1 }
                },
                { name: 'linenumbers', fields: ['back', 'fore', 'size', 'useFixed', 'bold', 'italic'] },
                { name: 'stringeol', explicit: { 'eolfilled': true } },
                
                'attribute name','attribute value','bracebad','bracehighlight',
                'classes','comments','control characters','fold markers','functions',
                'identifiers','indent guides','keywords','keywords2','numbers',
                'operators','preprocessor','regex','match_highlight','stderr',
                'stdin','stdout','strings','tags','variables'
            ]
        },
        
        'Colors': {
            fields: ['color'],
            properties: [
                'bookmarkColor','callingLineColor','caretFore','caretLineBack',
                'changeMarginDeleted','changeMarginInserted','changeMarginReplaced',
                'currentLineColor','edgeColor','foldMarginColor','selBack','selFore',
                'whitespaceColor',
            ]
        },

        'Indicators': {
            fields: ['indicator-alpha', 'indicator-color', 'indicator-draw_underneath', 'indicator-style'],
            properties: [
                'collab_local_change','collab_remote_change','collab_remote_cursor_1',
                'collab_remote_cursor_2','collab_remote_cursor_3','collab_remote_cursor_4',
                'collab_remote_cursor_5','find_highlighting','linter_error',
                'linter_warning','soft_characters','tabstop_current','tabstop_pending',
                'tag_matching','spelling_error'
            ]
        }

    };
    
    var selectedLanguage = "Python";
    var selectedScheme = schemeService.getScheme(prefs.getStringPref('editor-scheme'));
    
    var sample;
    
    var propertyValues;
    
    this.init = () =>
    {
        scintillaOverlayOnLoad();
        
        sample = $('#sample');
        sample.element().initWithBuffer("", "Text");
        
        var scimoz = sample.element().scimoz;
        for (var i=0; i <= scimoz.SC_MAX_MARGIN; i++) 
            scimoz.setMarginWidthN(i, 0);
        
        sample.on("blur", () => scimoz.caretPeriod = 0);
        sample.on("focus", () => scimoz.caretPeriod = 500);
        sample.on("click", this.onClickSample);
        
        this.populateFontList();
        this.populateSchemeList();
        
        this.loadSample();
        this.onSelectScheme();
        
        $("#languageList").on("command", this.onUpdateLanguage);
        $("#propertyList").on("select", this.onSelectProperty);
        $("#schemeslist").on("select", this.onSelectScheme);
        $("#newScheme").on("command", this.newScheme);
        $("#deleteScheme").on("command", this.deleteScheme);
        $("#ok").on("command", () =>
        {
            if (selectedScheme.writeable)
                this.saveScheme();
            this.applyScheme();
            window.close();
        });
        $("#save").on("command", this.saveScheme);
        $("#apply").on("command", this.applyScheme);
        $("#saveApply").on("command", () => { this.saveScheme(); this.applyScheme(); });
        
        for (let field in this.fields)
        {
            this.fields[field].init();
        }
    }
    
    this.populatePropertiesList = () =>
    {
        var list = $("#propertyList");
        list.empty();
        var clone = (o) => JSON.parse(JSON.stringify(o));
        
        // Populate using our static properties list
        for (let parentName in styleProperties) {
            let parent = clone(styleProperties[parentName]);
            parent.name = parentName;
            parent.locale = parent.locale || parent.name;
            delete parent.properties;
            
            for (let property of styleProperties[parentName].properties)
            {
                if (typeof property == 'string')
                {
                    property = { name: property };
                }
                
                property.parent = parent;
                property.locale = property.locale || property.name;
                
                let style = this.getBasicPropertyStyle(property);
                let item = $("<listitem>");
                item.attr("label", `${parent.locale} - ${property.locale}`);
                item.attr("name", property.name);
                if (style.color) item.css("color", style.color);
                if (style.background) item.css("background", style.background);
                item.element()._property = property;
                
                list.append(item);
            }
        }
        
        list.element().selectedIndex = 0;
        this.onSelectProperty();
    }
    
    this.populateLanguagePropertiesList = () =>
    {
        var list = $("#propertyList");
        list.empty();

        var labels = {};
        schemeService.getLanguageStyles(selectedLanguage, labels, new Object());
        for (let property of labels.value)
        {
            property = { name: property };
            property.parent = {
                name: selectedLanguage,
                fields: ['fore', 'back', 'bold', 'italic'],
                parent: { name: 'LanguageStyles'}
            };
            
            let style = this.getBasicPropertyStyle(property);
            let item = $("<listitem>");
            item.attr("label", property.name);
            item.attr("name", property.name);
            if (style.color) item.css("color", style.color);
            if (style.background) item.css("background", style.background);
            item.element()._property = property;
            
            list.append(item);
        }
        
        list.element().selectedIndex = 0;
        this.onSelectProperty();
    }
    
    this.populateFontList = () =>
    {
        var fontlistmono = $("#fontlist menu.mono menupopup");
        var fontlistall = $("#fontlist menu.all menupopup");
        fontlistall.empty();
        fontlistmono.empty();
        
        var fonts = require("ko/fonts").getSystemFonts();
        for (let font of fonts)
        {
            let item = $("<menuitem>");
            item.attr("label", font);
            fontlistall.append(item);
        }
        
        fonts = require("ko/fonts").getMonoFonts();
        for (let font of fonts)
        {
            let item = $("<menuitem>");
            item.attr("label", font);
            item.css("font-family", font);
            fontlistmono.append(item);
        }
    }
    
    this.populateSchemeList = () =>
    {
        var schemes = new Array();
        schemeService.getSchemeNames(schemes, new Object());
        
        var menuitem;
        var s, scheme;
        for (var i = 0; i < schemes.value.length; i++) {
            scheme = schemes.value[i];
            menuitem = document.createElement('menuitem');
            s = schemeService.getScheme(scheme);
            
            if (! s) continue;
            if (! s.writeable) 
                menuitem.setAttribute('class','primary_menu_item');
                
            menuitem.setAttribute('label', scheme);
            menuitem.setAttribute('id', scheme);
            menuitem.setAttribute('value', scheme);
            menuitem._isDark = s.isDarkBackground;
            
            $(menuitem).css({
                "font-family": s.getCommon("default_fixed", "face"),
                color: s.getCommon("default_fixed", "fore"),
                background: s.getCommon("default_fixed", "back")
            });
            
            $("#schemespopup").append(menuitem);
        }
        
        // sort by dark scheme
        $("#schemespopup").children().each(function ()
        {
            if (this._isDark)
            {
                while (this.previousSibling && ! this.previousSibling._isDark) {
                    this.parentNode.insertBefore(this, this.previousSibling);
                }
            }
        });
        
        $("#schemespopup").children().each(function ()
        {
            if ( ! this.classList.contains('primary_menu_item')) return;
            while (this.previousSibling && ! this.previousSibling.classList.contains('primary_menu_item'))
                this.parentNode.insertBefore(this, this.previousSibling);
        });
        
        $("#schemespopup .primary_menu_item").last().after($("<menuseparator/>"));
        
        $("#schemeslist").element().selectedItem = $(`#schemeslist menuitem[label="${selectedScheme.name}"]`).element();
    }
    
    this.selectDefaultLanguage = () =>
    {
        var p = "prefs.fontsColorsLanguages.langSpecific.lang";
        var isUsingDefault = ! prefs.hasPref(p);
        selectedLanguage = prefs.getString(p, "Python");

        // Verify the language exists
        var ok;
        try {
            let koLang = languageRegistry.getLanguage(selectedLanguage);
            ok = !!koLang;
            if (ok) {
                // The language service can return a language that has a
                // different name (i.e. "Python" when the language does not exist).
                selectedLanguage = koLang.name;
            }
        } catch(ex) {
            ok = false;
        }
        if (!ok)  selectedLanguage = "Python";
        
        if (isUsingDefault)
        {
            
            $("#languageList").element().selection = -1;
            this.populatePropertiesList();
        }
        else
        {
            $("#languageList").element().selection = selectedLanguage;
            this.populateLanguagePropertiesList();
        }
    }
    
    this.loadSample = () =>
    {
        var sampleText = languageRegistry.getLanguage(selectedLanguage).sample;
        if (! sampleText) 
            sampleText = "No sampleText for " + selectedLanguage + " available.";
            
        var view = sample.element();
        view.setBufferText(sampleText);
        view.language = selectedLanguage;
        view.anchor = sampleText.length/4;
        view.currentPos = sampleText.length/2;
    }
    
    this.onUpdateLanguage = () =>
    {
        var p = "prefs.fontsColorsLanguages.langSpecific.lang";
        var language = $("#languageList").element().selection;
        if (language == -1)
        {
            this.populatePropertiesList();
            prefs.deletePref(p);
        }
        else
        {
            selectedLanguage = language;
            this.loadSample();
            this.populateLanguagePropertiesList();
            prefs.setString(p, language);
        }
    }
    
    this.onClickSample = () =>
    {
        var scimoz = sample.element().scimoz;
        var styleno = scimoz.getStyleAt(scimoz.currentPos);
        
        var common = selectedScheme.getCommonName(selectedLanguage, styleno);
        if (! common)
            common = selectedScheme.getSpecificName(selectedLanguage, styleno);
        
        var item = $(`#propertyList listitem[name="${common}"]`);
        if ( ! item.length)
        {
            $("#languageList").element().selection = selectedLanguage;
            this.onUpdateLanguage();
            
            item = $(`#propertyList listitem[name="${common}"]`);
        }
        
        if ( ! item.length) return;
        
        $("#propertyList").element().selectedItem = item.element();
        $("#propertyList").element().ensureElementIsVisible(item.element());
        
        this.onSelectProperty();
    }
    
    this.onSelectScheme = () =>
    {
        var scheme = $("#schemeslist").element().selectedItem.getAttribute("label");
        selectedScheme = schemeService.getScheme(scheme);
        
        this.updateScintilla();
        this.selectDefaultLanguage();
        
        $("window").removeClass("primary-scheme");
        if ( ! selectedScheme.writeable)
            $("window").addClass("primary-scheme");
    }
    
    this.onSelectProperty = () =>
    {
        var selected = $("#propertyList").element().selectedItem;
        if (! selected) return;
        
        var property = selected._property;
        
        $("#propertyEditor > *[field]").hide();
        
        var fields = property.fields || property.parent.fields;
        for (let field of fields)
        {
            this.fields[field].reset();
            $(`#propertyEditor > *[field="${field}"]`).show();
        }
    }
    
    this.getSelectedProperty = () => $("#propertyList").element().selectedItem._property;
    
    this.getSelectedLanguage = () =>
    {
        var language = $("#languageList").element().selection;
        language = language == -1 ? '' : language;
        return language;
    }
    
    this.fields = {
        face: {
            init: () => {
                $("#fontlist").on("command", (e) => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    var face = e.target.getAttribute("label");
                    selectedScheme.setFont(property.name, face);
                    $("#fontlist").attr("label", face);
                    $("#fontlist").css("font-family", face);
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var face = selectedScheme.getFont(property.name);
                $("#fontlist").attr("label", face);
                $("#fontlist").css("font-family", face);
            }
        },
        size: {
            init: () => {
                $("#fontSize").on("command", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    selectedScheme.setSize(this.getSelectedLanguage(), property.name,
                                           $("#fontSize").element().selectedItem.getAttribute("value"))
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var size = selectedScheme.getSize(this.getSelectedLanguage(), property.name)
                $("#fontSize").element().selectedItem = $(`#fontSize menuitem[value="${size}"]`).element();
            }
        },
        bold: {
            init: () => {
                $("#fontBold").on("command", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    selectedScheme.setBold(this.getSelectedLanguage(), property.name,
                                           $("#fontBold").attr("checked") == "true")
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var bold = selectedScheme.getBold(this.getSelectedLanguage(), property.name)
                $("#fontBold").removeAttr("checked");
                if (bold) $("#fontBold").attr("checked", "true");
            }
        },
        italic: {
            init: () => {
                $("#fontItalic").on("command", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    selectedScheme.setItalic(this.getSelectedLanguage(), property.name,
                                           $("#fontItalic").attr("checked") == "true")
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var italic = selectedScheme.getItalic(this.getSelectedLanguage(), property.name)
                $("#fontItalic").removeAttr("checked");
                if (italic) $("#fontItalic").attr("checked", "true");
            }
        },
        fore: {
            init: () => {
                $("#fontFore").on("command", () => {
                    this.ensureWriteable();
                    this.pickColor($("#fontFore"), (color) => {
                        var property = this.getSelectedProperty();
                        selectedScheme.setFore(this.getSelectedLanguage(), property.name, color)
                        $(`#propertyList listitem[name="${property.name}"]`).css("color", color);
                        this.updateScintilla();
                    });
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var fore = selectedScheme.getFore(this.getSelectedLanguage(), property.name)
                $("#fontFore").css("background-color", fore);
                $("#fontFore").attr("color", fore);
            }
        },
        back: {
            init: () => {
                $("#fontBack").on("command", () => {
                    this.ensureWriteable();
                    this.pickColor($("#fontBack"), (color) => {
                        var property = this.getSelectedProperty();
                        selectedScheme.setBack(this.getSelectedLanguage(), property.name, color);
                        $(`#propertyList listitem[name="${property.name}"]`).css("background", color);
                        this.updateScintilla();
                    });
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var back = selectedScheme.getBack(this.getSelectedLanguage(), property.name)
                $("#fontBack").css("background-color", back);
                $("#fontBack").attr("color", back);
            }
        },
        color: {
            init: () => {
                $("#color").on("command", () => {
                    this.ensureWriteable();
                    this.pickColor($("#color"), (color) => {
                        var property = this.getSelectedProperty();
                        selectedScheme.setColor(property.name, color);
                        $(`#propertyList listitem[name="${property.name}"]`).css("background", color);
                        this.updateScintilla();
                    });
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var color = selectedScheme.getColor(property.name)
                $("#color").css("background-color", fore);
                $("#color").attr("color", fore);
            }
        },
        lineSpacing: {
            init: () => {
                $("#fontLineSpacing").on("input", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    selectedScheme.setLineSpacing(property.name, $("#fontLineSpacing").value())
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var space = selectedScheme.getLineSpacing(property.name)
                $("#fontLineSpacing").element().value = space;
            },
        },
        "indicator-style": {
            init: () => {
                $("#indicator_style_menulist").on("command", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                    selectedScheme.getIndicator(property.name, values.style, values.color,
                                                               values.alpha, values.draw_underneath);
                    values.style.value = $("#indicator_style_menulist").element().selectedItem.getAttribute("label");
                    selectedScheme.setIndicator(property.name, values.style.value, values.color.value,
                                                               values.alpha.value, values.draw_underneath.value);
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                selectedScheme.getIndicator(property.name, values.style, values.color,
                                                           values.alpha, values.draw_underneath);
                $("#indicator_style_menulist").element().selectedItem =
                    $(`#indicator_style_menulist menuitem[label="${values.style}"]`);
            }
        },
        "indicator-color": {
            init: () => {
                $("#indicator-color").on("command", () => {
                    this.pickColor($("#indicator-color"), (color) => {
                        this.ensureWriteable();
                        var property = this.getSelectedProperty();
                        var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                        selectedScheme.getIndicator(property.name, values.style, values.color,
                                                                   values.alpha, values.draw_underneath);
                        values.color.value = color;
                        selectedScheme.setIndicator(property.name, values.style.value, values.color.value,
                                                                   values.alpha.value, values.draw_underneath.value);
                        $(`#propertyList listitem[name="${property.name}"]`).css("background", color);
                        this.updateScintilla();
                    });
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                selectedScheme.getIndicator(property.name, values.style, values.color,
                                                           values.alpha, values.draw_underneath);
                $("#indicator-color").css("background-color", values.color.value);
                $("#indicator-color").attr("color", values.color);
            }
        },
        "indicator-alpha": {
            init: () => {
                $("#indicator_alpha_textbox").on("input", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                    selectedScheme.getIndicator(property.name, values.style, values.color,
                                                               values.alpha, values.draw_underneath);
                    values.alpha.value = $("#indicator_alpha_textbox").value();
                    selectedScheme.setIndicator(property.name, values.style.value, values.color.value,
                                                               values.alpha.value, values.draw_underneath.value);
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                selectedScheme.getIndicator(property.name, values.style, values.color,
                                                           values.alpha, values.draw_underneath);
                $("#indicator_alpha_textbox").element().value = values.alpha.value;
            }
        },
        "indicator-draw_underneath": {
            init: () => {
                $("#indicator_draw_underneath_checkbox").on("command", () => {
                    this.ensureWriteable();
                    var property = this.getSelectedProperty();
                    var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                    selectedScheme.getIndicator(property.name, values.style, values.color,
                                                               values.alpha, values.draw_underneath);
                    values.draw_underneath.value = $("#indicator_draw_underneath_checkbox").attr("checked") == "true";
                    selectedScheme.setIndicator(property.name, values.style.value, values.color.value,
                                                               values.alpha.value, values.draw_underneath.value);
                    this.updateScintilla();
                });
            },
            reset: () => {
                var property = this.getSelectedProperty();
                var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
                selectedScheme.getIndicator(property.name, values.style, values.color,
                                                           values.alpha, values.draw_underneath);
                $("#indicator_draw_underneath_checkbox").removeAttr("checked");
                if (values.draw_underneath.value) $("#indicator_draw_underneath_checkbox").attr("checked", "true");
            }
        },
        useSelFore: {
            init: () => {
                $("#useSelFore").on("command", () => {
                    this.ensureWriteable();
                    selectedScheme.useSelFore = $("#useSelFore").attr("checked") == "true";
                    this.updateScintilla();
                });
            },
            reset: () => {
                $("#useSelFore").removeAttr("checked");
                if (selectedScheme.useSelFore) $("#useSelFore").attr("checked", "true");
            }
        },
        caretLineVisible: {
            init: () => {
                $("#caretLineVisible").on("command", () => {
                    this.ensureWriteable();
                    selectedScheme.caretLineVisible = $("#caretLineVisible").attr("checked") == "true";
                    this.updateScintilla();
                });
            },
            reset: () => {
                $("#caretLineVisible").removeAttr("checked");
                if (selectedScheme.caretLineVisible) $("#caretLineVisible").attr("checked", "true");
            }
        },
    }
    
    this.pickColor = (button, callback) =>
    {
        var color = "#" + button.attr("color").replace(/^#/, "");
        
        var picker = null;
        var cid = prefs.getStringPref("colorpicker_cid");
        if (cid) {
            try {
                picker = Components.classes[cid]
                                   .getService(Components.interfaces.koIColorPickerAsync);
            } catch (ex) {
                log.exception(ex, "Unable to load the colorpicker with CID: " + cid);
                picker = null;
            }
        }
        if (!picker) {
            // Use the sysUtils color picker then:
            picker = Components.classes['@activestate.com/koSysUtils;1']
                               .getService(Components.interfaces.koIColorPickerAsync);
        }
        
        picker.pickColorAsync(function(newcolor) {
            if (newcolor) {
                button.css("background-color", newcolor);
                button.attr("color", newcolor);
                callback(newcolor);
            }
        }, color, 1.0, button.element().boxObject.screenX, button.element().boxObject.screenY);
    }
    
    this.getBasicPropertyStyle = (property) =>
    {
        var style = {color: null, background: null};
        var fields = property.fields || property.parent.fields;
        
        if (fields.indexOf("fore") != -1)
            style.color = selectedScheme.getFore(this.getSelectedLanguage(), property.name);
        
        if (fields.indexOf("back") != -1)
            style.background = selectedScheme.getBack(this.getSelectedLanguage(), property.name);
        
        if (fields.indexOf("indicator-color") != -1)
        {
            var values = {style: {}, color: {}, alpha: {}, draw_underneath: {}};
            selectedScheme.getIndicator(property.name, values.style, values.color,
                                                       values.alpha, values.draw_underneath);
            style.background = values.color.value;
        }
        
        if (fields.indexOf("color") != -1)
            style.background = selectedScheme.getColor(property.name);
        
        return style;
    }
    
    this.saveScheme = () =>
    {
        selectedScheme.save();
        
        if (selectedScheme.name == prefs.getString("editor-scheme"))
        {
            var observerSvc = Cc["@mozilla.org/observer-service;1"].
                                getService(Ci.nsIObserverService);
            observerSvc.notifyObservers(this, 'scheme-changed', selectedScheme.name);
        }
    }
    
    this.applyScheme = (callback) =>
    {
        var panel = $($.create("panel", {class: "scheme-apply", noautohide: true, level: "floating", width: 300},
            $.create("checkbox", {label: "Apply scheme to editor", name: "editor"})
                    ("checkbox", {label: "Apply scheme to inteface", name: "interface"})
                    ("hbox", 
                        $.create("button", {label: "Ok"})
                                ("button", {label: "Cancel"}))
        ).toString());
        
        if (prefs.getBoolean("cached.colorscheme-editor.apply.editor"))
            panel.find('checkbox[name="editor"]').attr("checked", "true");
            
        if (prefs.getBoolean("cached.colorscheme-editor.apply.interface"))
            panel.find('checkbox[name="interface"]').attr("checked", "true");
        
        panel.find('button[label="Ok"]').on("command", () => {
            var applyEditor = !! panel.find('checkbox[name="editor"]').attr("checked");
            var applyInterface = !! panel.find('checkbox[name="interface"]').attr("checked");
            
            prefs.setBoolean("cached.colorscheme-editor.apply.editor", applyEditor);
            prefs.setBoolean("cached.colorscheme-editor.apply.interface", applyInterface);
            
            if (applyEditor)
            {
                prefs.setString("editor-scheme", selectedScheme.name);
                var observerSvc = Cc["@mozilla.org/observer-service;1"].
                                    getService(Ci.nsIObserverService);
                observerSvc.notifyObservers(this, 'scheme-changed', selectedScheme.name);
            }
            
            if (applyInterface)
            {
                // ..
            }
            
            panel.element().hidePopup();
            panel.remove();
        });
        
        panel.find('button[label="Cancel"]').on("command", () =>
        {
            panel.element().hidePopup();
            panel.remove();
            return;
        });
        
        $("window").append(panel);
        var left = (document.documentElement.boxObject.width / 2) - 150;
        var top = document.documentElement.boxObject.height - 200;
        panel.element().openPopup(undefined, undefined, left, top);
    }
    
    this.newScheme = () =>
    {
        if (selectedScheme.unsaved)
        {
            var answer = ko.dialogs.yesNoCancel("Save current scheme before creating new one?");
            if (answer == "Cancel") 
                return false;
            
            if (answer == "Yes") 
                selectedScheme.save()
        }
        
        var newSchemeName;
        var schemes = {};
        schemeService.getSchemeNames(schemes, {});
        schemes = schemes.value;
        
        var _viewsBundle = Cc["@mozilla.org/intl/stringbundle;1"].
            getService(Ci.nsIStringBundleService).
            createBundle("chrome://komodo/locale/views.properties");
            
        while (1) { // while scheme name is invalid
            var msg = _viewsBundle.formatStringFromName(
                        "enterNewSchemeNameBasedOnScheme.template",
                        [selectedScheme.name], 1);
            var label = _viewsBundle.GetStringFromName("newSchemeName.label");
            
            newSchemeName = ko.dialogs.prompt(msg, label, newSchemeName);
            if (! newSchemeName) 
                return false;
            
            // Check to make sure that the name isn't already taken and that it can be written to disk.
            if (schemes.indexOf(newSchemeName) >= 0)
            {
                msg = _viewsBundle.formatStringFromName("schemeExists.template",
                                                        [newSchemeName], 1);
            }
            else if (! schemeService.schemeNameIsValid(newSchemeName))
            {
                msg = _viewsBundle.formatStringFromName("schemeNameHasInvalidCharacters.template",
                                                        [newSchemeName], 1);
            }
            else
            {
                break;
            }
            alert(msg);
        }

        var newScheme = selectedScheme.clone(newSchemeName);
        
        var menuitem = document.createElement('menuitem');
        menuitem.setAttribute('label', newSchemeName);
        menuitem.setAttribute('id', newSchemeName);
        menuitem.setAttribute('value', newSchemeName);
        
        $("#schemespopup").append(menuitem);
        $("#schemeslist").element().selectedItem = menuitem;
        
        this.onSelectScheme();
        
        return true;
    }
    
    this.deleteScheme = () =>
    {
        var name = selectedScheme.name
        if (ko.dialogs.yesNo("Are you sure you want to delete the scheme '" + name +"'?  This action cannot be undone.") == 'No') {
            return;
        }
        selectedScheme.remove();
        selectedScheme = schemeService.getScheme('Default');
        var oldScheme = prefs.getStringPref('editor-scheme');
        if (oldScheme == name) {
            // Delete the pref and inherit the global one again
            prefs.deletePref('editor-scheme');
            oldScheme = prefs.getStringPref('editor-scheme');
        }
        
        // need to remove it from the popup
        $(`#schemeslist menuitem[label="${name}"]`).remove();
        $("#schemeslist").element().selectedItem = $(`#schemeslist menuitem[label="${oldScheme}"]`).element();
        
        selectedScheme = schemeService.getScheme(oldScheme);
        this.onSelectScheme();
    }
    
    this.ensureWriteable = () =>
    {
        if (selectedScheme.writeable) 
            return true;
        
        if (! this.newScheme())
        {
            return false;
        }
        
        return true;
    }
    
    this.updateScintilla = () =>
    {
        var scintilla = sample.element().scimoz;
        var encoding = 'unused';
        var alternateType = false;
        selectedScheme.applyScheme(scintilla, selectedLanguage, encoding, alternateType);
    }
    
    this.destroy = () =>
    {
        try
        {
            if (! selectedScheme.unsaved && selectedScheme.isDirty) {
                selectedScheme.revert();
            }
            schemeService.purgeUnsavedSchemes();
            
            sample.element().close();
            scintillaOverlayOnUnload();
        }
        catch (e)
        {
            log.error(e);
        }
    }
    
    $(window).on("load", this.init);
    $(window).on("unload", this.destroy);
    
    
})();