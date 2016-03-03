(function() {
    
    var _ = require("contrib/underscore");
    var buttons = {};
    var $   = require("ko/dom");
    var tb  = $("#side-top-toolbar");
    
    var dynamicButton = function(opts)
    {
        var button;
        var menupopup;
        
        this.init = function()
        {
            button = $("<toolbarbutton>");
            button.attr({
                id: "dynamicBtn-" + opts.id,
                tooltip: opts.tooltip,
                type: "button",
                collapsed: "true",
                class: "dynamic-button " + opts.classList
            });
            
            if (typeof opts.command == "string")
            {
                button.attr("oncommand", "ko.commands.doCommandAsync('"+opts.command+"', event)");
                button.attr("observes", opts.command);
            }
            else
                button.on("command", opts.command);
            
            if (opts.icon)
                button.addClass("icon-" + opts.icon);
            else if (opts.image)
                button.attr("image", opts.image);
            
            if (opts.label)
                button.attr("label", opts.label);
                
            if (opts.menuitems)
            {
                button.attr("type", "menu-button");
                
                menupopup = $("<menupopup>");
                menupopup.on("popupshowing", this.updateMenu.bind(this));
                button.append(menupopup);
            }
            
            var groupItem = tb.find("#dynamicBtnGrp-" + opts.group);
            if ( ! groupItem.length)
            {
                groupItem = $("<toolbaritem>");
                groupItem.attr("id", "dynamicBtnGrp-" + opts.group);
                tb.append(groupItem);
            }
            
            groupItem.append(button);
            this.update();
        }
        
        this.update = function()
        {
            button.attr("collapsed", opts.isEnabled() ? "false" : "true");
        }
        
        this.updateMenu = function ()
        {
            menupopup.empty();
            var menuitems = opts.menuitems;
            
            if (typeof menuitems == "function")
                menuitems = menuitems();
                
            if ( ! Array.isArray(menuitems))
            {
                throw new Error("menuitems are not in the form of an array");
            }
            
            for (let menuitem of menuitems)
            {
                if (menuitem === null)
                {
                    menupopup.append($("<menuseparator>"));
                    continue;
                }
                
                menuitem = _.extend({
                    label: "unnamed",
                    isEnabled: function() { return true },
                    command: function() {},
                    classList: "",
                    image: null,
                    acceltext: ""
                }, menuitem);
                
                let elem = $("<menuitem>");
                elem.attr({
                    label: menuitem.label,
                    class: menuitem.classList,
                    image: menuitem.image,
                    acceltext: menuitem.acceltext,
                    disabled: menuitem.isEnabled() ? "false" : "true"
                });
                elem.on("command", menuitem.command);
                
                menupopup.append(elem);
            }
        }
        
        this.setLabel = function(value)
        {
            if (value === undefined)
                button.removeAttr("label")
            else
            button.attr("label", value);
        }
        
        this.setCounter = function(value)
        {
            if (value === undefined)
                button.removeAttr("counter")
            else
                button.attr("counter", value);
        }
        
        this.unregister = function ()
        {
            button.remove();
        }
        
        this.element = function ()
        {
            return button;
        }
        
        this.init();
    }
    
    this.init = function()
    {
        var w = require("ko/windows").getMain();
        
        w.addEventListener('current_view_changed', this.update.bind(this));
        w.addEventListener('view_document_attached', this.update.bind(this));
        w.addEventListener('current_view_language_changed', this.update.bind(this));
        w.addEventListener('workspace_restored', this.update.bind(this));
        w.addEventListener('project_opened', this.update.bind(this));
    }
    
    this.update = function(now = false)
    {
        var w = require("ko/windows").getMain();
        if (now !== true)
        {
            w.clearTimeout(this.update._timer);
            this.update._timer = w.setTimeout(this.update.bind(this, true), 250);
            return;
        }
        
        for (let k in buttons) {
            buttons[k].update();
        }
    }
    this.update._timer = null;
    
    this.register = function(label, opts)
    {
        if ((typeof label) == "object")
        {
            opts = label;
            label = opts.label || opts.id;
        }
        
        var id = (opts.id || label).replace(/\W+/g, "");
        
        if (id in buttons)
        {
            throw new Error("A dynamic button with id " + id + " already exists");
        }
        
        var icon = null
        if ( ! opts.image)
            icon = opts.icon || "question4";
            
        opts = _.extend({
            id: id,
            group: id,
            label: label,
            tooltip: opts.tooltip || label,
            isEnabled: function() { return false },
            command: function() {},
            menuitems: null,
            icon: icon,
            image: null,
            classList: ""
        }, opts);
        
        buttons[id] = new dynamicButton(opts);
        return buttons[id];
    }
    
    this.unregister = function()
    {
        if ( ! (id in buttons))
        {
            throw new Error("A dynamic button with id " + id + " does not exist");
        }
        
        buttons[id].unregister();
    }
    
    this.init();
    
}).apply(module.exports);