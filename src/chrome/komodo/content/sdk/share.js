/**
 * @copyright (c) 2016 ActiveState Software Inc.
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
    //  Append list IDs to append the share menu to.
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
     * @argument    {String}    namespace    namespace/path used to require your module that implements your share library
     * @argument    {String}    label Label for menuitems  
     */
    this.register = function (namespace , label)
    {
        if( ! w.require.exists(namespace))
        {
            log.warn(namespace + " not in require path.  Try adding your addon " +
                     "to the path:"+
                     "\n`window.require.setRequirePath('myAddon/', 'chrome://myAddon/content');`");
            return;
        }
        
        var shareModule = require(namespace); 
        if ( ! shareModule.share )
        {
            log.warn("Package '"+ namespace + "' appears to be missing a " +
                     "`share()` function.  You must provide a `share()` " +
                     "function to register your lib with `require('ko/share')`");
            return;
        }

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
            namespace:namespace,
            label: label,
            menuItem: shareMenuItem
        });
        updateShareMenu();
        //updateShareDynButton();
    };
    
    
    function updateShareMenu()
    {
        console.log("adding to menu");
        // Add the share menu to a set list of locations which are
        // specified by their id from the Komodo UI.
        for (var elementID of elementIDs)
        {
            shareMenu.element.parentElement.removeChild(shareMenu.element);
            let location = $("#" + elementID);
            if ( ! location ) {
                log.warn("Skipping element in menu update.  Does not exist: " + elementID);
                continue;
            }
            location.append(shareMenu.$element);
        }
    }
}).apply(module.exports);