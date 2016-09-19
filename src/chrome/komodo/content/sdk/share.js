/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview - Interface to add new sharing tool to Komodo
 */

/**
 * Easily add new sharing tool to the Komodo command set and UI
 *
 * @module ko/sharing
 */
(function()
{
    const log = require("ko/logging").getLogger("sharing");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    const commands = require("ko/commands");
    
    var shareMenu; // Stores the dropdown menu that holds all the added share modules
                   // We append new modules to it in register() and update all locations
                   // that the item is attached to
    var shareModules = []; // List of attached modules.
                           // Each item looks like:
                           // {
                           //    id: id,
                           //    lable: label,
                           //    menuItem: ko/ui/menuItem
                           // }
    
    var elementIDs = ["editorContextMenu"];  
    
    /**
     * Register a new sharing tool
     * Registers the modules namespace and adds available menu items
     * The UI elements that are augmented with the Share menu are:
     *  - Editor context menu
     *  - Dynamic toolbar
     *
     *  The added
     *
     * @argument    {String}    id    used to register namespace
     * @argument    {String}    label Label for menuitems  
     */
    this.register = function (id , label)
    {
        var namespace = "ko/share/"+id;
        try
        {
            require(namespace);
        } catch(e)
        {
             log.warn(e);
             return;
        } 
        var shareModule = require(namespace);
        if ( ! shareModule.share )
        {
            log.warn("Package 'ko/share/" + id + "' appears to be missing a `share()` function." +
                     "You must provide a `share()` function to register with ko/share.");
            return;
        }
        //commands.register("share_"+id, shareModule.share.bind(this), {
        //    label: "Share kopy: Share Code via kopy.io"
        //});
        var shareCommand = function()
            {
                shareModule.share();
            };
        console.log("Creating menu");
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
        console.log("adding menu item");
        var shareMenuItem = require("ko/ui/menuitem").create(
            {
                attributes: {
                    label:  label,
                    oncommand: "require('"+namespace+"').share()"
                }
            }   
        );
        shareMenu.addMenuItem(shareMenuItem);
        shareModules.push({
            id:id,
            label: label,
            menuItem: shareMenuItem
        });
        console.log(shareMenuItem);
        updateShareMenu();
        //updateShareDynButton();
    };
    
    
    function updateShareMenu(menu)
    {
        console.log("adding to menu");
        // Add the share menu to a set list of locations which are
        // specified by their id from the Komodo UI.
        for (var i in elementIDs)
        {
            shareMenu.element.parentElement.removeChild(shareMenu.element);
            var location = $("#" + elementIDs[i]);
            if ( ! location ) {
                log.warn("Skipping element in menu update.  Does not exist: " + elementIDs[i]);
                continue;
            }
            location.append(shareMenu.$element);
        }
    }
}).apply(module.exports);