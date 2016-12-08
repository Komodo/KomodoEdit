(function() {
    
    var {Cc, Ci}  = require("chrome");
    var _ = require("contrib/underscore");
    var buttons = {};
    var $   = require("ko/dom");
    var tb  = $("#side-top-toolbar");
    var w = require("ko/windows").getMain();
    var prefs = require("ko/prefs");
    var obsvc = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);
    
    var ss = require("ko/simple-storage").get("dynamic-button");
    
    var dynamicButton = function(opts)
    {
        var button;
        var menupopup;
        var self = this;
        
        this.opts = opts;
        
        var observer =
        {
            observe: function()
            {
                self.update();
            }
        };
        
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
            button.element()._dynamicButton = this;
            
            if (typeof opts.command == "string")
            {
                button.attr("oncommand", "ko.commands.doCommandAsync('"+opts.command+"', event)");
                button.attr("observes", opts.command);
            }
            else if (opts.command)
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
                button.attr("type", opts.command ? "menu-button" : "menu");

                menupopup = $("<menupopup>");
                menupopup.on("popupshowing", (e) =>
                {
                    if (e.originalTarget != menupopup.element())
                        return;

                    this.updateMenu();
                });
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
            
            if (ss.storage.buttons[opts.id].hide)
                this.hide();
            
            groupItem.append(button);
            
            for (let event of opts.events)
            {
                if (event.indexOf("observe:") === 0)
                {
                    obsvc.addObserver(observer, event.substr(8), false);
                }
                else if (event.indexOf("pref:") === 0)
                {
                    prefs.prefObserverService.addObserver(observer, event.substr(5), false);
                }
                else
                {
                    w.addEventListener(event, this.update.bind(this, false));
                }
            }
            
            w.addEventListener("update_dynamic_buttons", this.update.bind(this, false));
            
            this.update();
        }
        
        this.hide = function()
        {
            ss.storage.buttons[opts.id].hide = true;
            button.attr("kohidden", "true");
        }
        
        this.show = function()
        {
            ss.storage.buttons[opts.id].hide = false;
            button.removeAttr("kohidden");
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
            
            // On Komodo Edit we also need to hide the toolbar element, because
            // XUL weirdness seems to make it think the parent is overflowing otherwise
            // bug #2003
            visibleChildren = false;
            var parent = button.parent();
            sel = '.dynamic-button[disabled="false"], .dynamic-button:not([disabled])';
            visibleChildren = parent.parent().find(sel).length;
            parent.parent().attr("collapsed", visibleChildren ? "false" : "true");
        };
        this.update._timer = null;
        
        this.updateMenu = (menuitems, _menupopup) =>
        {
            _menupopup = _menupopup || menupopup;

            _menupopup.empty();
            menuitems = menuitems || opts.menuitems;
            
            if (typeof menuitems == "function")
            {
                menuitems = menuitems((menuitems) =>
                {
                    this.updateMenu(menuitems, _menupopup);
                });
                if ( ! menuitems)
                {
                    let elem = $("<menuitem>");
                    elem.attr({
                        label: "Loading ..",
                        disabled: "true"
                    });
                    _menupopup.append(elem);
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
                    
                    _menupopup.append(childNode);
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
                    _menupopup.append($("<menuseparator>"));
                    continue;
                }
                
                if (menuitem instanceof window.XULElement ||
                    menuitem.koDom)
                {
                    _menupopup.append(menuitem);
                    continue;
                }
                
                menuitem = _.extend({
                    label: "unnamed",
                    name: "",
                    observes: "",
                    isEnabled: null,
                    command: null,
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
                {
                    elem = $("<menu>");

                    elem.attr({
                        label: menuitem.label,
                        class: menuitem.classList,
                        acceltext: menuitem.acceltext,
                        tooltiptext: menuitem.tooltiptext
                    });
                }
                else
                {
                    elem = $("<menuitem>");
                
                    elem.attr({
                        label: menuitem.label,
                        class: menuitem.classList,
                        image: menuitem.image,
                        acceltext: menuitem.acceltext,
                        tooltiptext: menuitem.tooltiptext,
                        value: menuitem.value,
                    });
                }
                
                if (menuitem.type)
                    elem.attr("type", menuitem.type);
                    
                if (menuitem.menuitems)
                {
                    var popup = $("<menupopup>");
                    this.updateMenu(menuitem.menuitems, popup);
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
                
                _menupopup.append(elem);
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
    

    var init = () =>
    {
        if ( ! ss.storage.buttons)
            ss.storage.buttons = {};
        console.log(ss.storage.buttons);
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
            command: null,
            menuitems: null,
            icon: icon,
            image: null,
            classList: "",
            events: ["current_place_opened", "project_opened", "workspace_restored"]
        }, opts);
        
        if ( ! ss.storage.buttons[id])
            ss.storage.buttons[id] = {};
        
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
    
    init();
    
}).apply(module.exports);