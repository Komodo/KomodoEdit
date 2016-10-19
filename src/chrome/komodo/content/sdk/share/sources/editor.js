(function()
{
    const log = require("ko/logging").getLogger("sharing");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    
    var shareMenu;
    var shareDynBtn;
    var _shareModule;
    
    this.load = function(shareModule)
    {
        _shareModule = shareModule;
        updateEditorMenus(shareModule);
    };
    
    
    function updateEditorMenus()
    {
        createMenuitem();
        updateShareMenu();
        updateDynButton();
    }
    
    /**
     * Create a menuitem
     *
     * @argument {String} name  name of the module
     */
    function createMenuitem()
    {
        var menuitem = require("ko/ui/menuitem").create(
        {
            attributes: {
                label:  _shareModule.name,
                tooltiptext: _shareModule.label,
                oncommand: "require('ko/share').share('"+_shareModule.name+"');"
            }
        });
        return menuitem;
    }
    
    /**
     * Creates Share menu if not created already. Add new menuitem base on name.
     * Makes sure menu locations are updated
     *
     * @argument {String}   name    name of module
     */
    function updateShareMenu()
    {
        if( ! shareMenu )
        {
            shareMenu = require("ko/ui/menu").create(
            {
                attributes:
                {
                    label: "Share..."
                }
            });
        }
        
        _shareModule.menuitem = createMenuitem();
        shareMenu.addMenuItem(_shareModule.menuitem);
        var $editorContextMenu = $("#editorContextMenu");
        $editorContextMenu.append(shareMenu.$element);
    }
    
    function updateDynButton()
    {
        if( ! shareDynBtn )
        {
            shareDynBtn = require("ko/dynamic-button");
            shareDynBtn.register("Share", {
                icon: "cloud",
                tooltip: "Share content on...",
                events: ["current_view_changed",
                         "current_place_opened",
                         "file_saved"],
                //classList: "scc-menu",
                menuitems: updateDynamicMenu.bind(this),
                isEnabled: () => {
                    var view = require("ko/views").current().get();
                    if ( ! view.scimoz )
                    {
                        return false;
                    }
                    return true;
                }
            });   
        }
    }
    function updateDynamicMenu() {
        return shareMenu.menupopup.element.cloneNode(true);
    }
}).apply(module.exports);
