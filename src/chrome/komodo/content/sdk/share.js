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
    
    var shareMenu;
    var shareDynBtn;
    var moduleNames = [] // Store the name of each of the modules
                         // Mainly to avoid using Object.keys() to iterate over
                         // the sharedModules object.
    var shareModules = {}; // List of attached modules.
                           // Each item looks like:
                           // {
                           //    slack:
                           //    {
                           //       namespace: path,
                           //       label: label,
                           //       menuItem: ko/ui/menuItem
                           //    }
                           // }
    //  Append list IDs to append the share menu to.
    var elementIDs = ["editorContextMenu"];  
    
    /**
     * Register a new sharing tool
     * Registers the modules namespace and adds available menu items
     * The UI elements that are augmented with the Share menu are:
     *  - Editor context menu
     *  - Dynamic toolbar
     * Modules share function should take (content, filename, fileType)
     *
     *  The added
     *
     * @argument    {String}    name        name of the module
     * @argument    {String}    namespace   namespace/path used to require your module that implements your share library
     * @argument    {String}    label       Label for menuitems  
     */
    this.register = function (name, namespace, label)
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
        
        moduleNames.push(name);
        shareModules[name] = {
            namespace: namespace,
            label: label
        }

        updateShareMenu(name);
        //updateShareDynButton();
    };
    
    /**
     * Share content on specified moduel
     *
     * @argument {String}   name module name to share on
     */
    this.share = function(name)
    {
        var moduleObject = getModule(name);
        var content = getContent();
        var filename = getFilename();
        var fileType = getFileLangName();
        require(moduleObject.namespace).share(content, filename, fileType);
    }
    
    /**
     * Get the module to use
     */
    var getModule = function(name)
    {
        return shareModules[name];
    }
    
    function updateShareMenu(name)
    {
        var module = getModule(name);
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
                label:  name,
                tooltiptext: module.label,
                oncommand: "require('ko/share').share('"+name+"');"
            }
        });
        shareMenu.addMenuItem(shareMenuItem);
        module.menuItem = shareMenuItem;
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
    
    /**
     * Get or create a file name to be displayed.
     * Takes the file name if nothing selected
     * Inserts `-snippet` before extension if
     *
     * @returns {String}    filename    name of file with "-snippet" appended
     *                                  if only sending selection.
     */
    function getFilename()
    {
        var view = require("ko/views").current().get();
        var filename;
        if ( view.scimoz.selectionEmpty ) {
            filename = view.title;
        } else {
            let viewTitlesplit = view.title.split(".");
            let name = viewTitlesplit.shift() + "-snippet";
            // support multi ext. filenames common in templating
            let extension = viewTitlesplit.join(".");
            // Filter out empty string if this file had no extension
            filename = [name,extension].filter(function(e){return e}).join(".");
        }
        return filename;
    }
    /**
     * Get the currently open files languages name
     * Defaults to "text"
     */
    function getFileLangName()
    {
        var view = require("ko/views").current().get();
        return view.koDoc.language || "text";
    }
 
    /**
     * Get content to post to Slack
     * 
     */
    function getContent()
    {
        var view = require("ko/views").current().get();
        if ( ! view.scimoz )
        {
            var locale = "You don't have a file open to post any content to Slack.";
            require("notify/notify").interact(locale, "slack", {priority: "info"});
            return "";
        }
        // Get whole file or get selection
        if ( view.scimoz.selectionEmpty ) {
            var content = view.scimoz.text;
        } else {
            var content = view.scimoz.selText;
        }
        if( content == "" )
        {
            var locale = "You're file is empty.  You don't want to share that.  Don't be weird.";
            require("notify/notify").interact(locale, "slack", {priority: "info"});
            return content;
        }
        return content;
    };
    
}).apply(module.exports);