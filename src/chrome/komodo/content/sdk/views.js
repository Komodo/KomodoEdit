/**
 * @module views
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
     * get() - returns a propery from the currentView object
     * scintilla
     * scimoz
     * koDoc
     * file
     * language
     * 
     * @returns {Object}
     */
    this.current = function()
    {
        var view = ko.views.manager.currentView;
        
        var get = function()
        {
            var result = view;
            
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
            prefs: get("koDoc", "prefs"),
            language: get("koDoc", "language"),
            
            type: view ? view.getAttribute("type") : false
        }
    }
    
    /**
     * Retrieve all views
     *
     * @returns {Array}
     */
    this.all = this.manager.getAllViews.bind(this.manager);
    
    /**
     * Retrieve all editor views
     *
     * @returns {Array}
     */
    this.editors = this.manager.getAllViews.bind(this.manager, "editor");
    
    /**
     * Split the view
     */
    this.split = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_splittab')
    
    /**
     * Rotate the split view
     */
    this.rotate = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_rotateSplitter')
    
}).apply(module.exports);