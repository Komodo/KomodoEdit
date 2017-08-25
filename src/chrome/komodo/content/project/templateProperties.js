window.templateProperties = {};
(function()
{

    var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/project/macro.properties");

    var $ = require("ko/dom").window(window);
    var prefs = require("ko/prefs");
    var log = require("ko/logging").getLogger("templateProperties");
    var legacy = require("ko/windows").getMain().ko;

    var elems = {
        dialog: () => $('#dialog-templateproperties'),
        name: () => $('#name'),
        okButton: () => $(document.documentElement.getButton('accept')),
        applyButton:  () => $(document.documentElement.getButton('extra1')),
        // the scimoz objects for each editor view in the dialog
        value: () => $("#value"),
        scimoz: () => $("#value").element().scimoz,
        errorWrapper: () => $("#error-wrapper"),
        errorMessage: () => $("#error-message"),
        ejs: () => $("#treat_as_ejs"),
        languages: () => $("#languageList"),
        default: () => $("#default"),
    };

    var tool = window.arguments[0].item;

    var onLoad = () =>
    {
        scintillaOverlayOnLoad();

        // Setup the apply button as it would be blank
        elems.applyButton().attr('label', bundle.GetStringFromName("apply"));
        elems.applyButton().attr('accesskey', bundle.GetStringFromName("applyAccessKey"));

        if (window.arguments[0].task == 'new')
        {
            elems.name().focus();
            elems.applyButton().attr('collapsed', 'true');
        }
        else
            elems.name().attr("value", tool.getStringAttribute('name'));
        this.updateTitle();
        
        elems.ejs().attr("checked", tool.getStringAttribute('treat_as_ejs'));
        elems.default().attr("checked", tool.getStringAttribute('lang_default'));
        elems.languages().element().selection = tool.getStringAttribute('language');
        
        var content = elems.value().element();
        content.scintilla.symbolMargin = false;
        content.scimoz.useTabs = prefs.getBooleanPref("useTabs");
        content.scimoz.indent = prefs.getLongPref('indentWidth');
        content.scimoz.tabWidth = prefs.getLongPref('indentWidth');
        content.initWithBuffer(tool.value, tool.getStringAttribute('language') || "Text");
        var foldStyle = prefs.getStringPref("editFoldStyle");
        if (foldStyle && foldStyle != "none")
            content.setFoldStyle(prefs.getStringPref("editFoldStyle"));
    };

    var onUnload = () =>
    {
        try {
            // The "close" method ensures the scintilla view is properly cleaned up.
            elems.value().element().close();
            scintillaOverlayOnUnload();
        } catch (e) {
            log.exception(e);
        }
    };

    this.updateTitle = () =>
    {
        var name = elems.name().value();
        if (name)
            document.title = bundle.formatStringFromName("namedProperties", [name], 1);
        else
            document.title = bundle.formatStringFromName("unnamedProperties", [tool.prettytype], 1);
    };

    this.accept = () =>
    {
        return this.apply();
    };

    this.apply = () =>
    {
        elems.errorWrapper().attr("collapsed", "true");

        tool.value = elems.scimoz().text;
        tool.setStringAttribute("name", elems.name().value());
        tool.setStringAttribute("treat_as_ejs", elems.ejs().element().checked);
        tool.setStringAttribute("lang_default", elems.default().element().checked);

        var language = elems.languages().element().selection;
        if (language == "-1")
            language = "Text";
        tool.setStringAttribute("language", language);

        var currentDefault = legacy.toolbox2.getDefaultTemplateForLanguage(language);
        if (elems.default().element().checked && currentDefault)
        {
            currentDefault.setStringAttribute("lang_default", false);
            currentDefault.save();
        }

        // If it's not new then just save
        if (window.arguments[0].task != 'new')
        {
            tool.save();
        }
        else
        {
            var parent = window.arguments[0].parent;
            var toolbox2 = opener.ko.toolbox2;
            if ( ! parent)
            {
                try
                {
                    parent = toolbox2.manager.getSelectedItem();
                } catch(ex) {}

                if ( ! parent)
                    parent = toolbox2.getStandardToolbox();
            }
            toolbox2.addNewItemToParent(tool, parent);
        }
        
        window.arguments[0].res = true;
        
        return true;
    };
    
    this.cancel = () => true;

    window.addEventListener("load", onLoad);
    window.addEventListener("unload", onUnload);

}).apply(window.templateProperties);
