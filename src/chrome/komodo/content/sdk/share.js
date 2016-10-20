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
    
    var sources =
    [
        require("ko/share/sources/editor"),
        require("ko/share/sources/trackchanges"),
        require("ko/share/sources/logs"),
        require("ko/share/sources/diff"),
    ];
    var shareModules = {}; // List of attached modules.
                           // Each item looks like:
                           // {
                           //    slack:
                           //    {
                           //       name: name,
                           //       namespace: path,
                           //       label: label,
                           //    }
                           // }
    require("notify/notify").categories.register("Share",
    {
        label: "Komodo Share"
    });
    /**
     * Register a new sharing tool
     * Registers the modules namespace and adds available menu items
     * The UI elements that are augmented with the Share menu are:
     *  - Editor context menu
     *  - Dynamic toolbar
     *  - trackchanges button
     *  - diff dialogs
     *  - RX generator?
     *  - logs dialog
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
        
        shareModules[name] = {
            name: name,
            namespace: namespace,
            label: label
        };
        // Create cmd for the function
        require("ko/commands").register("share_file_on_"+name,
            this.share.bind(this, name),
            {
                label: name+": Share Code on your "+name
            }); 
        // Update the various sources.
        for ( let source of sources )
        {
            source.load(shareModules[name]);
        }
    };
    
   
    /**
     * Share content on specified moduel
     *
     * @argument {String}   name module name to share on
     * @argument {Object} source an object holding all information needed for
     * sharing content
     */
    this.share = function(name, content = null, filetype = null, title = null)
    {
        content = content ? content : getContent();
        title = title ? title : getFilename();
        filetype = filetype ? filetype : getFileLangName();
        require(shareModules[name].namespace).share(content, title, filetype);
    };

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
        if ( view && view.scimnoz && view.scimoz.selectionEmpty ) {
            filename = view.filename;
        } else {
            let viewTitlesplit = view.title.split(".");
            let name = viewTitlesplit.shift() + "-snippet";
            // support multi ext. filenames common in templating
            let extension = viewTitlesplit.join(".");
            // Filter out empty string if this file had no extension
            filename = [name,extension].filter(function(e){return e;}).join(".");
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
        var locale;
        if ( ! view.scimoz )
        {
            locale = "You don't have a file open to post any content to Slack.";
            require("notify/notify").interact(locale, "slack", {priority: "info"});
            return "";
        }
        // Get whole file or get selection
        var content;
        if ( view.scimoz.selectionEmpty )
        {
            content = view.scimoz.text;
        } else {
            content = view.scimoz.selText;
        }
        if(  "" === content )
        {
            locale = "You're file is empty.  You don't want to share that.  Don't be weird.";
            require("notify/notify").interact(locale, "slack", {priority: "info"});
            return content;
        }
        return content;
    }
    
}).apply(module.exports);