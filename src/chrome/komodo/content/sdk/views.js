/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Easily interface with Komodo's views (tabs/editors)
 *
 * @module ko/views
 */
(function()
{
    
    /**
     * Access the view manager (see ko.views.manager)
     */
    this.manager = ko.views.manager;
    
    /**
     * Access the current (active) view (see ko.views.manager.currentView)
     *
     * Returns an object containing:
     *
     * get() - returns a propery from the currentView object, possible properties:
     *
     *  - scintilla
     *  - scimoz
     *  - koDoc
     *  - file
     *  - filePath
     *  - prefs
     *  - language
     *  - type
     *
     * For example:
     * 
     * ```
     * require("ko/views").current().get("language")
     * ```
     * 
     * gets the language for the current view
     * 
     * @returns {Object}
     */
    this.current = function()
    {
        var view = ko.views.manager.currentView;
        
        /**
         * Get a property
         * 
         * @returns {Mixed} 
         */
        var get = function()
        {
            var result = view;
            
            if (!arguments.length) return view;
            
            for (let x=0; x<arguments.length;x++)
            {
                if ( ! result || ! (arguments[x] in result))
                {
                    return false;
                }
                
                result = result[arguments[x]];
            }
            
            return result;
        }
        
        return {
            get: get,
            
            scintilla: get("scintilla"),
            scimoz: get("scimoz"),
            koDoc: get("koDoc"),
            file: get("koDoc", "file"),
            filePath: get("koDoc", "file", "path"),
            url: get("koDoc", "file", "URI"),
            prefs: get("koDoc", "prefs"),
            language: get("koDoc", "language"),
            
            type: view ? view.getAttribute("type") : false
        }
    }
    
    /**
     * Retrieve all views
     *
     * @function all
     *
     * @returns {Array}
     */
    this.all = this.manager.getAllViews.bind(this.manager);
    
    /**
     * Retrieve all editor views
     *
     * @function editors
     *
     * @returns {Array}
     */
    this.editors = this.manager.getAllViews.bind(this.manager, "editor");
    
    /**
     * Split the view
     *
     * @function split
     */
    this.split = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_splittab')
    
    /**
     * Rotate the split view
     *
     * @function rotate
     */
    this.rotate = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_rotateSplitter')
    
}).apply(module.exports);