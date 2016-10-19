(function()
{
    const log = require("ko/logging").getLogger("sharing");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    
    var shareBtn;
    var shareMenu;
    var _shareModule;
    this.load = function(shareModule)
    {
        w.addEventListener("window_opened", function(e) {
            var diffWindowPath = "chrome://komodo/content/tail/tail.xul";
            if( diffWindowPath === e.detail.location.href)
            {
                _shareModule = shareModule;
                updateDiffButton();
            }
        });
        
    };
    
    function updateDiffButton()
    {
       var $view = $("#view");
        // Create the button if it doens't exist
        if( ! shareBtn )
        {
            shareBtn = require("ko/ui/toolbarbutton").create('Share',
                {
                    attributes:
                    {
                        type: "menu-button",
                        id: $view.element().id+"-share_menu",
                        tooltiptext:"Share code on..."
                    }
                });
            // Append the share button to the track changes panel
            $view.after(shareBtn.element);
        }
        // Create the TC menu if it doesn't exist
        // We're creating this for it's menupopup attribute.  We don't actually
        // need the menu.
        if( ! shareMenu )
        {
            shareMenu = require("ko/ui/menu").create();
        }
        
        //Create the new modules menuitem for this menu
        var menuitem = require("ko/ui/menuitem").create(
        {
            attributes: {
                label:  _shareModule.name,
                tooltiptext: _shareModule.label,
                oncommand: "require('ko/share/sources/logs').share('"+_shareModule.name+"');"
            }
        });
        // Add it to the menu
        shareBtn.addMenuItem(menuitem);

    }
    this.share = function(name)
    {
        // get the content from the diff view
        var $view = $("#view");
        console.log($view.text);
        // construct a file name
        require("ko/share").share(name, $view.text, "text"/*, title*/);
    };
}).apply(module.exports);