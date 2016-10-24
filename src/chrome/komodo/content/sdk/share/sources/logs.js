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
                e.detail.addEventListener("load", updateButton.bind(null,e.detail));
            }
        });
    };
    
    function updateButton(logWindow)
    {
        // $ is instaniated on the main window so pass in the log window from
        // the event
        var $view = $("#view", logWindow);
        // Create the button if it doens't exist
        var shareBtn = require("ko/ui/button").create('Share',
            {
                attributes:
                {
                    type: "menu",
                    id: $view.element().id+"-share_menu",
                    tooltiptext:"Share Log .."
                }
            });
        // Append the share button to the track changes panel
        var properties =
        {
            attributes:
            {
                align: "center",
                pack: "center"
            }
        };
        var row = require("ko/ui/row").create(shareBtn,properties);
        $view.after(row.element);
        
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