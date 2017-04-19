/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview - Interface to add new sharing tool to Komodo
 */

/**
 * Easily add new sharing tool to the Komodo command set and UI
 *
 * @module ko/share
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
    this.modules = shareModules;
    
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
        for (let source of sources)
        {
            source.load();
        }
    };
    
   
    /**
     * Share content on specified moduel
     *
     * @argument {String}   name        module name to share on
     * @argument {string}   content     content to share
     * @argument {object}   meta        (optional) additional meta information
     *    example meta obj:
     *    {
     *        title: "myfile.js",
     *        language: "javascript"
     *    }
     *    This is passed to the submodules `share` function to do with what it
     *    pleases
     */
    this.share = function(name, content, meta = null)
    {
        require(shareModules[name].namespace).share(content, meta);
    };
    
}).apply(module.exports);