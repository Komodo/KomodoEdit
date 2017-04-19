(function()
{
    const {Cc, Ci}  = require("chrome");
    const log = require("ko/logging").getLogger("sharing");
    const koShare = require("ko/share");
    const $ = require("ko/dom");
    
    this.load = function()
    {
        updateShareButton();
    };
    
    /**
     * Create the track changes share button and add the new module
     */
    function updateShareButton()
    {
        // check if trackchanges is enabled
        var addonMgr = Cc["@activestate.com/platform/addons/addon-manager;1"]
                        .getService(Ci.koamIAddonManager);
        addonMgr.getAddonByID("trackchanges@activestate.com", function(addon)
        {
            if (addon && addon.isActive)
            {
                addButton();
            }
        }.bind());
    }
    
    function addButton()
    {
        $("#trackChangesShareButton").remove();
        
        // Update button in track changes
        var $trackchanges = $("#changeTracker_hbox");
        
        // Create the button if it doens't exist
        var shareButton = require("ko/ui/button").create('Share',
            {
                attributes:
                {
                    type: "menu",
                    id: "trackChangesShareButton",
                    tooltiptext:"Share Changeset .."
                }
            });
        
        //Create the new modules menuitem for this menu
        for (let id in koShare.modules)
        {
            let module = koShare.modules[id];
            let menuitem = require("ko/ui/menuitem").create({
                attributes: {
                    label:  module.label
                }
            });
            
            menuitem.on("command", share.bind(this, module.name));
            
            // Add it to the menu
            shareButton.addMenuItem(menuitem);
        }
        
        // Append the share button to the track changes panel
        $trackchanges.append(shareButton.element);
    }
    
    function share(name)
    {
        var patch = require("ko/views").current().get().changeTracker.getFormattedPatch();
        var title = "Changeset of " + require("ko/views").current().basename;
        koShare.share(name, patch, {title: title, language: "diff"});
    };
    
}).apply(module.exports);