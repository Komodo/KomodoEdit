const {classes: Cc} = Components;
Components.utils.import("resource://gre/modules/Services.jsm");

var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();

var $ = require("ko/dom").window(window);
var originalValues = {};

function OnPreferencePageOK(prefset)
{
    prefset.setString("editor-font", $("#editor-font").attr("label"));
    prefset.setString("interface-font", $("#interface-font").attr("label"));
    
    return true;
}

function OnPreferencePageSaved(prefset)
{
    var newValEditor = prefset.getString("editor-scheme");
    var newValInterface = prefset.getString("interface-scheme");
    var newValWidget = prefset.getString("widget-scheme");
    
    var newValInterfaceFontDefer = prefset.getBoolean("interface-font-defer");
    var newValInterfaceFont = prefset.getString("interface-font");
    var newValInterfaceFontSize = prefset.getString("interface-font-size");
    
    var newValEditorFontDefer = prefset.getBoolean("editor-font-defer");
    var newValEditorFont = prefset.getString("editor-font");
    var newValEditorFontSize = prefset.getLong("editor-font-size");
    var newValEditorFontSpace = prefset.getLong("editor-line-spacing");
    
    var colorscheme = require("ko/colorscheme");
    
    if (newValEditor != originalValues.editor ||
        newValEditorFontDefer != originalValues.editorFontDefer ||
        newValEditorFont != originalValues.editorFont ||
        newValEditorFontSize != originalValues.editorFontSize ||
        newValEditorFontSpace != originalValues.editorFontSpace)
    {
        colorscheme.applyEditor(newValEditor);
    }
        
    if (newValInterface != originalValues.interface ||
        newValInterfaceFontDefer != originalValues.interfaceFontDefer ||
        newValInterfaceFont != originalValues.interfaceFont ||
        newValInterfaceFontSize != originalValues.interfaceFontSize)
    {
        colorscheme.applyInterface(newValInterface);
    }
    
    if (newValWidget != originalValues.widget ||
        newValInterfaceFontDefer != originalValues.interfaceFontDefer ||
        newValInterfaceFont != originalValues.interfaceFont ||
        newValInterfaceFontSize != originalValues.interfaceFontSize)
    {
        colorscheme.applyWidgets(newValWidget);
    }
        
    updateOriginalValues(prefset);
    
    return true;
}

function OnPreferencePageLoading(prefset) {
    var sdkFonts = require("ko/fonts");
    var font = sdkFonts.getEffectiveFont(prefset.getString("editor-font"));
    
    $("#editor-font").attr("label", font);
    $("#editor-font").css("font-family", font);
    
    font = sdkFonts.getEffectiveFont(prefset.getString("interface-font"));
    $("#interface-font").attr("label", font);
    $("#interface-font").css("font-family", font);
    
    updateOriginalValues(prefset);
}

function updateOriginalValues(prefset) {
    originalValues.editor = prefset.getString("editor-scheme");
    originalValues.interface = prefset.getString("interface-scheme");
    originalValues.widget = prefset.getString("widget-scheme");
    
    originalValues.interfaceFontDefer = prefset.getBoolean("interface-font-defer");
    originalValues.interfaceFont = prefset.getString("interface-font");
    originalValues.interfaceFontSize = prefset.getString("interface-font-size");
    
    originalValues.editorFontDefer = prefset.getBoolean("editor-font-defer");
    originalValues.editorFont = prefset.getString("editor-font");
    originalValues.editorFontSize = prefset.getLong("editor-font-size");
    originalValues.editorFontSpace = prefset.getLong("editor-line-spacing");
}

function PrefUi_OnLoad() {
    // todo: turn into UI sdk
    var populateSchemeList = (id) =>
    {
        var schemes = [];
        schemeService.getSchemeNames(schemes, {});
        
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
            
            $(`#${id} > menupopup`, window).append(menuitem);
        }
        
        var el = $(`#${id}`);
        var placeholder = $("<box/>");
        el.replaceWith(placeholder);
        
        // sort by dark scheme
        el.find("menupopup", window).children().each(function ()
        {
            if (this._isDark)
            {
                while (this.previousSibling && ! this.previousSibling._isDark) {
                    this.parentNode.insertBefore(this, this.previousSibling);
                }
            }
        });
        
        el.find("menupopup", window).children().each(function ()
        {
            if ( ! this.classList.contains('primary_menu_item')) return;
            while (this.previousSibling && ! this.previousSibling.classList.contains('primary_menu_item'))
                this.parentNode.insertBefore(this, this.previousSibling);
        });
        
        el.find(".primary_menu_item", window).last().after($("<menuseparator/>"));
        placeholder.replaceWith(el);
        //var schemeName = prefs.getString(id);
        //$(`#${id}`).element().selectedItem = $(`#${id} menuitem[label="${schemeName}"]`).element();
    };
    
    populateSchemeList("interface-scheme");
    populateSchemeList("widget-scheme");
    populateSchemeList("editor-scheme");
    
    var populateFontList = function()
    {
        var fontlistmono = $("#editor-font menu.mono menupopup");
        var fontlistall = $("#editor-font menu.all menupopup");
        fontlistall.empty();
        fontlistmono.empty();
        
        var fontlist2mono = $("#interface-font menu.mono menupopup");
        var fontlist2all = $("#interface-font menu.all menupopup");
        fontlist2all.empty();
        fontlist2mono.empty();
        
        var fonts = require("ko/fonts").getSystemFonts();
        for (let font of fonts)
        {
            let item = $("<menuitem>");
            item.attr("label", font);
            fontlistall.append(item);
            fontlist2all.append(item.clone());
        }
        
        fonts = require("ko/fonts").getMonoFonts();
        for (let font of fonts)
        {
            let item = $("<menuitem>");
            item.attr("label", font);
            item.css("font-family", font);
            fontlistmono.append(item);
            fontlist2mono.append(item.clone());
        }
        
        $("#editor-font").on("command", (e) => {
            var face = e.target.getAttribute("label");
            $("#editor-font").attr("label", face);
            $("#editor-font").css("font-family", face);
        });
        
        $("#interface-font").on("command", (e) => {
            var face = e.target.getAttribute("label");
            $("#interface-font").attr("label", face);
            $("#interface-font").css("font-family", face);
        });
    };
    
    populateFontList();
    
    parent.hPrefWindow.onpageload();
    
    setTimeout(function () {
        if ($("#link-schemes", window).attr("checked") == "true")
        {
            $("#widget-scheme, #editor-scheme", window).attr("disabled", "true");
        }
        
        if ($(".ui-hide-chrome", window).attr("checked") == "true")
        {
            $("#windowButtonPrefs", window).hide();
        }
        
        $(".ui-hide-chrome", window).on("command", () =>
        {
            var checked = $(".ui-hide-chrome", window).attr("checked");
            if (checked != "true")
                $("#windowButtonPrefs", window).show();
            else
                $("#windowButtonPrefs", window).hide();
        });
        
        $("#link-schemes", window).on("command", () =>
        {
            var checked = $("#link-schemes", window).attr("checked");
            if (checked == "true")
            {
                $("#widget-scheme, #editor-scheme", window).attr("disabled", "true");
                
                var val = $("#interface-scheme", window).attr("value");
                $(`#widget-scheme`, window).element().selectedItem = $(`#widget-scheme menuitem[label="${val}"]`, window).element();
                $(`#editor-scheme`, window).element().selectedItem = $(`#editor-scheme menuitem[label="${val}"]`, window).element();
            }
            else
                $("#widget-scheme, #editor-scheme", window).removeAttr("disabled");
        });
        
        $("#interface-scheme", window).on("command", () =>
        {
            var checked = $("#link-schemes", window).attr("checked");
            if (checked != "true") return;
            
            var val = $("#interface-scheme", window).attr("value");
            $(`#widget-scheme`, window).element().selectedItem = $(`#widget-scheme menuitem[label="${val}"]`, window).element();
            $(`#editor-scheme`, window).element().selectedItem = $(`#editor-scheme menuitem[label="${val}"]`, window).element();
        });
        
        var updateFontState = function()
        {
            if ($("#interface-font-defer", window).attr("checked") == "true")
                $("#interface-font, #interface-font-size", window).attr("disabled", "true");
            else
                $("#interface-font, #interface-font-size", window).removeAttr("disabled");
                
            if ($("#editor-font-defer", window).attr("checked") == "true")
                $("#editor-font, #editor-font-size, #editor-line-spacing", window).attr("disabled", "true");
            else
                $("#editor-font, #editor-font-size, #editor-line-spacing", window).removeAttr("disabled");
                
        };
        updateFontState();
        
        $("#interface-font-defer", window).on("command", updateFontState);
        $("#editor-font-defer", window).on("command", updateFontState);
    }, 250);
    
}