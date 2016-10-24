(function()
{
    const w = require("ko/windows").getMain();
    const koShare = require("ko/share");
    const $ = require("ko/dom");
    
    var listening = false;
    
    this.load = function()
    {
        if (listening)
            return;
        
        listening = true;
        
        w.addEventListener("window_opened", function(e) {
            var windowPath = "chrome://komodo/content/dialogs/diff.xul";
            if( windowPath === e.detail.location.href)
            {
                e.detail.addEventListener("load", updateButton.bind(null,e.detail));
            }
        });
    };
    
    function updateButton(logWindow)
    {
        // $ is instaniated on the main window so pass in the log window from
        // the event
        var $view = $("#view", logWindow);
        
        var shareBtn = require("ko/ui/button").create('Share',
            {
                attributes:
                {
                    type: "menu",
                    id: $view.element().id+"-share_menu",
                    tooltiptext:"Share Diff .."
                }
            });
        
        var properties =
        {
            attributes:
            {
                align: "center",
                pack: "center"
            }
        };
        var row = require("ko/ui/row").create(shareBtn, properties);
        
        $view.after(row.element);
        
        //Create the new modules menuitem for this menu if it hasn't already
        for (let id in koShare.modules)
        {
            let module = koShare.modules[id];
            let menuitem = require("ko/ui/menuitem").create({
                attributes: {
                    label:  module.label
                }
            });
            
            menuitem.on("command", share.bind(this, module.name, logWindow));
            
            // Add it to the menu
            shareBtn.addMenuItem(menuitem);
        }
    }
    
    var share = function(id, logWindow)
    {
        // get the content from the diff view
        var content;
        var scimoz = $("#view", logWindow).element().scimoz;
        if ( scimoz.selectionEmpty )
            content = scimoz.text;
        else
            content = scimoz.selText;
            
        koShare.share(id, content, {title: logWindow.document.title, language: "diff"});
    };
}).apply(module.exports);
