(function()
{
    const {Cc, Ci}  = require("chrome");
    const log = require("ko/logging").getLogger("sharing");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    
    var trkChngshareBtn;
    var trkChngshareMenu;
    var trackChanges;
    var _shareModule;
    var blah = 0;

    this.load = function(shareModule)
    {
        blah++;
        console.log("we've registered " + blah + " modules");
        console.log("module name: " + shareModule.name);
        _shareModule = shareModule;
        updateTrckChngsShareButton();
    };
    
    /**
     * Create the track changes share button and add the new module
     */
    function updateTrckChngsShareButton()
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
                if( ! trkChngshareBtn )
                {
                    trkChngshareBtn = require("ko/ui/toolbarbutton").create('Share',
                        {
                            attributes:
                            {
                                type: "menu-button",
                                id: $trackchanges.element().id+"-share_menu",
                                tooltiptext:"Share code on..."
                            }
                        });
                    // Append the share button to the track changes panel
                    $trackchanges.append(trkChngshareBtn.element);
                }
                
                // Create the TC menu if it doesn't exist
                // We're creating this for it's menupopup attribute.  We don't actually
                // need the menu.
                if( ! trkChngshareMenu )
                {
                    trkChngshareMenu = require("ko/ui/menu").create();
                }
                
                //Create the new modules menuitem for this menu
                var menuitem = require("ko/ui/menuitem").create(
                {
                    attributes: {
                        label:  _shareModule.name,
                        tooltiptext: _shareModule.label,
                        oncommand: "require('ko/share/sources/trackchanges').changeTrackerShare('"+_shareModule.name+"');"
                    }
                });
                // Add it to the menu
                trkChngshareBtn.addMenuItem(menuitem);
             }
        }
    }
    
    this.changeTrackerShare = function(name)
    {
        var patch;
        var title;
        var view = require("ko/views").current().get();
        try
        {
            patch = view.changeTracker.getFormattedPatch();
            title = view.filename + " Changes.";
        }
        catch (e)
        {
            log.exception(e);
            var errorMsg = "Sharing failed, exception occured: " + e.message;
            require("notify/notify").interact(errorMsg, "sharing", {priority: "error"});
            return;
        }
        require("ko/share").share(_shareModule.name, patch, "diff", title);
    };
    
}).apply(module.exports);