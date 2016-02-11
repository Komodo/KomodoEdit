(function() {
    
    var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                    .getService(Components.interfaces.nsIWindowMediator);

    var w = wm.getMostRecentWindow('Komodo');
    var ko = w.ko;
    var require = w.require;
    var $ = require("ko/dom");
    var prefs = require("ko/prefs");
    
    var self = this;
    
    var elems = {
        mainTb: $("#main-toolbar", window),
        secondTb: $("#second-toolbar", window)
    }
    
    var checkboxes = [
        {
            elem: $("#show-chrome", window),
            checked: function() ! prefs.getBoolean("ui.hide.chrome"),
            onToggle: function() prefs.setBoolean("ui.hide.chrome", ! this.elem.element().checked)
        },
        {
            elem: $("#show-menubar", window),
            checked: function() $("#toolbar-menubar", w).attr("autohide") == "false",
            onToggle: function() ko.commands.doCommandAsync("cmd_toggleMenubar")
        },
        {
            elem: $("#show-tabs", window),
            checked: function() $("#topview").hasClass('showTabs'),
            onToggle: function() ko.openfiles.toggleTabBar() // todo: Move out of ko.openfiles
        },
        {
            elem: $("#show-toolbar", window),
            checked: function() $("#main-toolboxrow-wrapper", w).attr("collapsed") != "true",
            onToggle: function() ko.uilayout.setToolbarsVisibility(this.elem.element().checked, 'main-toolboxrow-wrapper')
        },
        {
            elem: $("#show-side-toolbar", window),
            checked: function() $("#toolbox_side", w).attr("collapsed") != "true",
            onToggle: function() ko.uilayout.setToolbarsVisibility(this.elem.element().checked, 'toolbox_side')
        },
        {
            elem: $("#show-notification", window),
            checked: function() $("#middle-toolboxrow", w).attr("kohidden") != "true",
            onToggle: function() $("#middle-toolboxrow", w).attr("kohidden", this.elem.element().checked ? "false" : "true")
        }
    ];
    
    var menus = [
        {
            elem: $("#toolbar-mode", window),
            value: function() $("#toolbox_main", w).attr("_mode"),
            onChange: function() {
                var menu = this;
                var mode = menu.elem.element().value;
                var realMode = mode;
                var toolbox = $("#toolbox_main");
                toolbox.attr("mode", mode);
                toolbox.attr("_mode", realMode);
                w.document.persist(toolbox.attr("id"), "mode");
                w.document.persist(toolbox.attr("id"), "_mode");
                
                if (mode == "text") mode = "full";
                $("#main-toolboxrow-wrapper toolbar").each(function() {
                    var el = $(this);
                    el.attr("mode", mode);
                    el.attr("_mode", realMode);
                    w.document.persist(el.attr("id"), "mode");
                    w.document.persist(el.attr("id"), "_mode");
                    self.updateToolbarViewState();
                });
            }
        },
        {
            elem: $("#side-toolbar-mode", window),
            value: function() $("#toolbox_side", w).attr("_mode"),
            onChange: function() {
                var menu = this;
                var mode = menu.elem.element().value;
                var realMode = mode;
                var toolbox = $("#toolbox_side");
                toolbox.attr("mode", mode);
                toolbox.attr("_mode", realMode);
                w.document.persist(toolbox.attr("id"), "mode");
                w.document.persist(toolbox.attr("id"), "_mode");
                
                if (mode == "text") mode = "full";
                $("#toolbox_side toolbar").each(function() {
                    var el = $(this);
                    el.attr("mode", mode);
                    el.attr("_mode", realMode);
                    w.document.persist(el.attr("id"), "mode");
                    w.document.persist(el.attr("id"), "_mode");
                    self.updateToolbarViewState();
                });
            }
        }
    ];
    
    this.init = function ()
    {
        this.populateList("main");
        this.populateList("second");
        
        for (let checkbox of checkboxes)
        {
            checkbox.elem.attr("checked", checkbox.checked() ? "true" : "false");
            checkbox.elem.on("command", checkbox.onToggle.bind(checkbox));
        }
        
        for (let menu of menus)
        {
            let selected = menu.elem.find('menuitem[value="'+menu.value()+'"]');
            menu.elem.element().selectedItem = selected.element();
            menu.elem.on("command", menu.onChange.bind(menu));
        }
        
        window.onConfirmDialog = function() {};
    }
    
    this.populateList = function(which = "main")
    {
        var el = elems[which + "Tb"];
        $("#"+which+"-toolboxrow toolbaritem:not(.custom-toolbar)", w).each(function() {
            
            var listitem = $("<hbox class='list-item'/>");
            listitem.attr("ishidden", this.getAttribute("kohidden"));
            listitem._originalElement = this;
            el.append(listitem)
            
            $(this).children().each(function() {
                var el = $(this).clone(true, false);
                
                var wrapper = $("<vbox><button/></vbox>");
                wrapper._originalElement = this;
                
                wrapper.attr("ishidden", el.attr("kohidden"));
                
                el.removeAttr("kohidden");
                el.removeAttr("observes");
                el.removeAttr("oncommand");
                el.removeAttr("onclick");
                el.removeAttr("disabled");
                el.removeAttr("checked");
                
                wrapper.prepend(el);
                listitem.append(wrapper);
                
                wrapper.find("button").on("click", self.hideElem.bind(self, wrapper));
            });
            
            listitem.append("<separator>");
            listitem.append("<button class='move'/>");
            listitem.append("<button class='toggle'/>");
            
            listitem.find("button.toggle").on("click", self.hideElem.bind(self, listitem));
        });
    }
    
    this.hideElem = function(el)
    {
        var hide = ! (el.attr("ishidden") == "true");
        hide = hide ? "true" : "false";
        
        el.attr("ishidden", hide);
        el._originalElement.setAttribute("kohidden", hide);
        
        el._originalElement.ownerDocument.persist(el._originalElement.id, "kohidden");
        
        this.updateToolbarViewState();
    }
    
    this.updateToolbarViewState = function ()
    {
        // Update hidden / visible state of toolbar items
        // and set relevant ancestry classes
        ko.uilayout._updateToolbarViewStates(elems.mainTb.element());
        ko.uilayout._updateToolbarViewStates(elems.secondTb.element());

        // make the overflow button rebuild the next time it's open
        elems.mainTb.element().dirty = true;
        elems.secondTb.element().dirty = true;
    }
    
    w.addEventListener("komodo-post-startup", this.init.bind(this));
    
})();