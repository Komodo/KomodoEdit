(function()
{
    const {Cc, Ci}  = require("chrome");
    const log = require("ko/logging").getLogger("sharing");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    
    var shareButton;
    var trackChanges; // boolean: is trackchanges addon enabled?
    var blah = 0;

    this.load = function(shareModule)
    {
        updateShareButton(shareModule);
    };
    
    /**
     * Create the track changes share button and add the new module
     */
    function updateShareButton(shareModule)
    {
        // check if trackchanges is enabled
        var addonMgr = Cc["@activestate.com/platform/addons/addon-manager;1"]
                        .getService(Ci.koamIAddonManager);
        addonMgr.getAddonByID("trackchanges@activestate.com", function(addon)
        {
            if (addon && addon.isActive)
            {
                trackChanges = true;
                addBtn();
            }
        }.bind());
        
        function addBtn()
        {
            if (trackChanges)
            {
                // Update button in track changes
                var $trackchanges = $("#changeTracker_hbox");
                // Create the button if it doens't exist
                if( ! shareButton )
                {
                    shareButton = require("ko/ui/toolbarbutton").create('Share',
                        {
                            attributes:
                            {
                                type: "menu-button",
                                id: $trackchanges.element().id+"-share_menu",
                                tooltiptext:"Share code on..."
                            }
                        });
                    // Append the share button to the track changes panel
                    $trackchanges.append(shareButton.element);
                }
                
                //Create the new modules menuitem for this menu
                var menuitem = require("ko/ui/menuitem").create(
                {
                    attributes: {
                        label:  shareModule.name,
                        tooltiptext: shareModule.label,
                        oncommand: "require('ko/share/sources/trackchanges').share('"+shareModule.name+"');"
                    }
                });
                // Add it to the menu
                shareButton.addMenuItem(menuitem);
             }
        }
    }
    
    this.share = function(name)
    {
        var patch;
        var title;
        try
        {
            patch = require("ko/views").current().get().changeTracker.getFormattedPatch();
            title = require("ko/views").current().filename + " Changes.";
        }
        catch (e)
        {
            log.exception(e);
            var errorMsg = "Sharing failed, exception occured: " + e.message;
            require("notify/notify").interact(errorMsg, "sharing", {priority: "error"});
            return;
        }
        require("ko/share").share(name, patch, "diff", title);
    };
    
}).apply(module.exports);