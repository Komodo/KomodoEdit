(function()
{
    
    this.manager = ko.views.manager;
    
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
            language: get("koDoc", "language"),
            
            type: view ? view.getAttribute("type") : false
        }
    }
    
    this.all = this.manager.getAllViews.bind(this.manager);
    this.editors = this.manager.getAllViews.bind(this.manager, "editor");
    
    this.split = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_splittab')
    this.rotate = ko.commands.doCommandAsync.bind(ko.commands, 'cmd_rotateSplitter')
    
}).apply(module.exports);