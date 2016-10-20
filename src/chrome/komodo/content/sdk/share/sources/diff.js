(function()
{
    const log = require("ko/logging").getLogger("sharing");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    const {Cc, Ci}  = require("chrome");
    
    var shareBtn;
    var shareMenu;
    var storeModuleNames = [];  // Check this list for the name otherwise it
                                // creates a menuitem every time a diff dialog
                                // is loaded.
    this.load = function(shareModule)
    {
        w.addEventListener("window_opened", function(e) {
            var windowPath = "chrome://komodo/content/dialogs/diff.xul";
            if( windowPath === e.detail.location.href)
            {
                e.detail.addEventListener("load", updateButton.bind(null,shareModule,e.detail));
            }
        });
    };
    
    function updateButton(shareModule, logWindow)
    {
        // $ is instaniated on the main window so pass in the log window from
        // the event
        var $view = $("#view", logWindow);
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
        
        //Create the new modules menuitem for this menu if it hasn't already
        if ( storeModuleNames.indexOf(shareModule.name) < 0 )
        {
            storeModuleNames.push(shareModule.name);
            var menuitem = require("ko/ui/menuitem").create(
            {
                attributes: {
                    label:  shareModule.name,
                    tooltiptext: shareModule.label,
                    oncommand: "require('ko/share/sources/diff').share('"+shareModule.name+"');"
                }
            });
            // Add it to the menu
            shareBtn.addMenuItem(menuitem);
        }
    }
    this.share = function(name)
    {
        // get the content from the diff view
        var content;
        var scimoz = $("#view").element().scimoz;
        if ( scimoz.selectionEmpty )
        {
            content = scimoz.text;
        } else {
            content = scimoz.selText;
        }
        // Generate a relevant title
        var title = window.document.title;
        // Has to be called on the main window as this windows require
        // doesn't know about the registered share modules
        w.require("ko/share").share(name, content, "diff", title);
    };
}).apply(module.exports);
