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
                tooltiptext: opts.tooltip,
                type: "button",
                disabled: "true",
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
            {
                button.addClass("icon-" + opts.icon);
            }
            else if (opts.image)
                button.attr("image", opts.image);
            
            if (opts.label)
                button.attr("label", opts.label);
                
            if (opts.ordinal)
                button.attr("ordinal", opts.ordinal);
                
            if (opts.menuitems)
            {
                button.attr("type", "menu-button");
                
                menupopup = $("<menupopup>");
                menupopup.on("popupshowing", this.updateMenu.bind(this, null));
                button.append(menupopup);
            }
            
            var groupItem = tb.find("#dynamicBtnGrp-" + opts.group);
            if ( ! groupItem.length)
            {
                groupItem = $("<toolbaritem>");
                groupItem.attr("id", "dynamicBtnGrp-" + opts.group);
                if (opts.groupOrdinal)
                    groupItem.attr("ordinal", opts.groupOrdinal);
                tb.append(groupItem);
            }
            
            if ( ! opts.isEnabled)
            {
                if (typeof opts.command == "string")
                {
                    var controller = window.controllers.getControllerForCommand(opts.command);
                    if (controller)
                    {
                        opts.isEnabled = () =>
                        {
                            return controller.isCommandEnabled(opts.command);
                        }
                    }
                }
                
                if ( ! opts.isEnabled)
                    opts.isEnabled = () => false;
            }
            
            groupItem.append(button);
            
            for (let event of opts.events)
            {
                var w = require("ko/windows").getMain();
                
                w.addEventListener(event, this.update.bind(this));
            }
            
            this.update();
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
        
            var enabled = opts.isEnabled(this);
            button.attr("disabled", enabled ? "false" : "true");
            
            var visibleChildren;
            if (button.element().parentNode.childNodes.length === 1)
                visibleChildren = enabled;
            else
            {
                var sel = '.dynamic-button[disabled="false"], .dynamic-button:not([disabled])';
                visibleChildren = button.parent().find(sel).length;
            }
                
            button.parent().attr("collapsed", visibleChildren ? "false" : "true");
        };
        this.update._timer = null;
        
        this.updateMenu = function (menuitems)
        {
            menupopup.empty();
            menuitems = menuitems || opts.menuitems;
            
            if (typeof menuitems == "function")
            {
                menuitems = menuitems(this.updateMenu.bind(this));
                if ( ! menuitems)
                {
                    let elem = $("<menuitem>");
                    elem.attr({
                        label: "Loading ..",
                        disabled: "true"
                    });
                    menupopup.append(elem);
                    return; // using callback
                }
            }
            
            if (menuitems instanceof window.XULElement)
            {
                for (let childNode of Array.slice(menuitems.childNodes)) {
                    
                    // Add stopPropagation to oncommand and command
                    let type = null;
                    if (childNode.getAttribute("oncommand"))
                        type = "oncommand";
                    if (childNode.getAttribute("command"))
                        type = "command";
                        
                    if (type)
                    {
                        let cmd = childNode.getAttribute(type);
                        
                        // Wrap with doCommand if this is just a word (command name)
                        if (cmd.match(/^[\w-]*$/))
                            cmd = "ko.commands.doCommandAsync('"+cmd+"', event)";
                            
                        childNode.setAttribute(type, cmd.replace(/[\s;]*$/g,'') + "; event.stopPropagation();");
                        childNode.removeAttribute("observes"); // observes overrides oncommand
                    }
                    
                    menupopup.append(childNode);
                }
                return;
            }
            
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
                    name: "",
                    observes: "",
                    isEnabled: null,
                    command: function() {},
                    classList: "",
                    image: null,
                    acceltext: "",
                    tooltiptext: "",
                    type: null,
                    checked: null,
                    value: -1,
                    menuitems: null
                }, menuitem);
                    
                if ( ! menuitem.isEnabled)
                {
                    if (typeof menuitem.command == "string")
                    {
                        var controller = window.controllers.getControllerForCommand(menuitem.command);
                        if (controller)
                        {
                            menuitem.isEnabled = () =>
                            {
                                return controller.isCommandEnabled(menuitem.command);
                            }
                        }
                    }
                    
                    if ( ! menuitem.isEnabled)
                        menuitem.isEnabled = () => true;
                }
                
                let elem;
                if (menuitem.menuitems)
                    elem = $("<menu>");
                else
                    elem = $("<menuitem>");
                
                elem.attr({
                    label: menuitem.label,
                    class: menuitem.classList,
                    image: menuitem.image,
                    acceltext: menuitem.acceltext,
                    tooltiptext: menuitem.tooltiptext,
                    value: menuitem.value,
                });
                
                if (menuitem.type)
                    elem.attr("type", menuitem.type);
                    
                if (menuitem.menuitems)
                {
                    var popup = $("<menupopup>").append(
                        $("<menuitem>").attr({
                            label: "Loading ..",
                            disabled: "true"
                        })
                    );
                    popup.on("popupshowing", this.updateMenu.bind(this, menuitem.menuitems));
                    elem.append(popup);
                }
                
                if (menuitem.name)
                    elem.attr("name", menuitem.name);
                    
                if (menuitem.disabled)
                    elem.attr("disabled", "true");
                    
                if (menuitem.observes)
                    elem.attr("observes", menuitem.observes);
                    
                if (menuitem.checked)
                    elem.attr("checked", menuitem.checked);
                    
                if (typeof menuitem.command == "string")
                {
                    let cmd = menuitem.command;
                    
                    // Wrap with doCommand if this is just a word (command name)
                    if (cmd.match(/^[\w-]*$/))
                        cmd = "ko.commands.doCommandAsync('"+menuitem.command+"', event)";
                        
                    elem.attr("oncommand", cmd.replace(/[\s;]*$/g,'') + "; event.stopPropagation();");
                }
                else
                    elem.on("command", function(m, event) { m.command(); event.stopPropagation(); }.bind(null, menuitem));
                
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
    }
    
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
        
        var icon = null;
        if ( ! opts.image)
            icon = opts.icon || "question4";
            
        opts = _.extend({
            id: id,
            group: id,
            label: label,
            tooltip: opts.tooltip || label,
            isEnabled: null,
            command: function() {},
            menuitems: null,
            icon: icon,
            image: null,
            classList: "",
            events: ["current_place_opened", "project_opened", "workspace_restored"]
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