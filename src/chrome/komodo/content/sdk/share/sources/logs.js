(function()
{
    const koShare = require("ko/share");
    const w = require("ko/windows").getMain();
    const $ = require("ko/dom");
    const {Cc, Ci}  = require("chrome");
    
    var listening = false;
    
    this.load = function()
    {
        if (listening)
            return;
        
        listening = true;
        
        w.addEventListener("window_opened", function(e) {
            var windowPath = "chrome://komodo/content/tail/tail.xul";
            if( windowPath === e.detail.location.href)
            {
                e.detail.addEventListener("load", updateMenu.bind(null,e.detail));
            }
        });
    };
    
    function updateMenu(logWindow)
    {
        // $ is instaniated on the main window so pass in the log window from
        // the event
        var $view = $("#view", logWindow);
        var $parent = $("#bufferContextMenu", logWindow);
        
        // Create the button if it doens't exist
        var shareMenu = require("ko/ui/menu").create(
            {
                attributes:
                {
                    label: 'Share',
                    id: $view.element().id+"-share_menu",
                    tooltiptext:"Share Log .."
                }
            });
        
        $parent.append($("<menuseparator>"));
        $parent.append(shareMenu.element);
        
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
            shareMenu.addMenuItem(menuitem);
        }
    }

    function share(id, logWindow)
    {
        var content;
        var scimoz = $("#view", logWindow).element().scimoz;
        if ( scimoz.selectionEmpty )
            content = scimoz.text;
        else
            content = scimoz.selText;
        
        // Generate a relevant title
        var infoSvc = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
        var title = "Logs for Komodo " +
            infoSvc.productType + " " +
            infoSvc.version + " " +
            infoSvc.buildType + " build number " +
            infoSvc.buildNumber;
        
        koShare.share(id, content, {title: title, language: "text"});
    };
}).apply(module.exports);