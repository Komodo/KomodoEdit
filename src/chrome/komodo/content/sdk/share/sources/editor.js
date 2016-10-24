(function()
{
    const koShare = require("ko/share");
    const $ = require("ko/dom");
    
    var shareDynBtn;
    
    this.load = function()
    {
        updateShareMenu();
        updateDynButton();
    };
    
    function share(id)
    {
        var meta = {title: require("ko/views").current().title, language: require("ko/views").current().language || "text"};
        koShare.share(id, getContent(), meta);
    }
    
    /**
     * Creates Share menu if not created already. Add new menuitem base on name.
     * Makes sure menu locations are updated
     *
     * @argument {String}   name    name of module
     */
    function updateShareMenu()
    {
        $("#editContextShareMenu").remove();
        
        var shareMenu = require("ko/ui/menu").create(
        {
            attributes:
            {
                id: "editContextShareMenu",
                label: "Share .."
            }
        });
        
        var $editorContextMenu = $("#editorContextMenu");
        $editorContextMenu.append(shareMenu.element);
        
        shareMenu.addMenuItems(getShareMenuItems());
    }
    
    function getShareMenuItems()
    {
        var items = [];
        for (let id in koShare.modules)
        {
            let module = koShare.modules[id];
            let menuitem = require("ko/ui/menuitem").create({
                attributes: {
                    label:  module.label
                }
            });
            menuitem.on("command", share.bind(this, id));
            items.push(menuitem.element);
        }
        
        return items;
    }

    function updateDynButton()
    {
        if( ! shareDynBtn )
        {
            shareDynBtn = require("ko/dynamic-button");
            shareDynBtn.register("Share", {
                icon: "share-alt",
                tooltip: "Share Current File ..",
                events: ["current_view_changed"],
                groupOrdinal: 900,
                //classList: "scc-menu",
                menuitems: getShareMenuItems.bind(this),
                isEnabled: () => {
                    var view = require("ko/views").current().get();
                    if ( ! view.scimoz )
                    {
                        return false;
                    }
                    return true;
                }
            });   
        }
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
            locale = "You don't have a file open to post any content to Slack";
            require("notify/notify").send(locale, "slack", {priority: "info"});
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
            locale = "Your file is empty";
            require("notify/notify").send(locale, "slack", {priority: "info"});
            return content;
        }
        return content;
    }
}).apply(module.exports);
