const {classes: Cc} = Components;
Components.utils.import("resource://gre/modules/Services.jsm");

var schemeService = Cc['@activestate.com/koScintillaSchemeService;1'].getService();

var $ = require("ko/dom");
var originalValues = {};

function OnPreferencePageOK()
{
    var editorValue = $(`#editor-scheme`, window).attr("value");
    var interfaceValue = $(`#interface-scheme`, window).attr("value");
    var widgetValue = $(`#widget-scheme`, window).attr("value");
    
    var colorscheme = require("ko/colorscheme");
    
    if (editorValue != originalValues.editor)
        colorscheme.applyEditor($(`#editor-scheme`, window).attr("value"));
        
    if (interfaceValue != originalValues.interface)
        colorscheme.applyInterface($(`#interface-scheme`, window).attr("value"));
    
    if (widgetValue != originalValues.widget)
        colorscheme.applyWidgets($(`#widget-scheme`, window).attr("value"));
    
    return true;
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
        
        originalValues.editor = $(`#editor-scheme`, window).attr("value");
        originalValues.interface = $(`#interface-scheme`, window).attr("value");
        originalValues.widget = $(`#widget-scheme`, window).attr("value");
    }, 250);
    
}