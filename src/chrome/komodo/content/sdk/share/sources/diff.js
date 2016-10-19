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
            var diffWindowPath = "chrome://komodo/content/dialogs/diff.xul";
            if( diffWindowPath === e.detail.location.href)
            {
                console.log("it's loading something in a diff....even though it's not open.")
                _shareModule = shareModule;
                updateDiffButton();
            }
        });
        
    };
    
    function updateDiffButton()
    {
       var $diffView = $("#view");
        // Create the button if it doens't exist
        if( ! shareBtn )
        {
            shareBtn = require("ko/ui/toolbarbutton").create('Share',
                {
                    attributes:
                    {
                        type: "menu-button",
                        id: "diff-"+$diffView.element().id+"-share_menu",
                        tooltiptext:"Share code on..."
                    }
                });
            // Append the share button to the track changes panel
            $diffView.after(shareBtn.element);
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
                oncommand: "require('ko/share/sources/diff').diffShare('"+_shareModule.name+"');"
            }
        });
        // Add it to the menu
        shareBtn.addMenuItem(menuitem);

    }
    this.diffShare = function(name)
    {
        // get the content from the diff view
        var $diffView = $("#view");
        console.log($diffView.text);
        // construct a file name
        require("ko/share").share(name, $diffView.text, "diff"/*, title*/);
    };
}).apply(module.exports);