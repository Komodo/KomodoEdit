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
    
    var warnedRestart = false;
    var checkboxes = [
        {
            elem: $("#show-chrome", window),
            checked: function() ! prefs.getBoolean("ui.hide.chrome"),
            onToggle: function() {
                prefs.setBoolean("ui.hide.chrome", ! this.elem.element().checked);
                ko.uilayout.updateToolboxVisibility();
                
                if (require("sdk/system").platform == 'darwin' && ! warnedRestart) {
                    alert('Please restart Komodo in order for window decoration changes to take effect');
                    
                    warnedRestart = true;
                    setTimeout(function() {
                        warnedRestart = false;
                    }, 300000);
                }
            }
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
        
        this.updateToolbarViewState();
    }
    
    this.populateList = function(which = "main")
    {
        var el = elems[which + "Tb"];
        $("#"+which+"-toolboxrow toolbaritem:not(.custom-toolbar)", w).each(function() {
            
            var listitem = $("<hbox class='list-item'/>");
            listitem.attr("ishidden", this.getAttribute("kohidden"));
            listitem.element()._originalElement = this;
            el.append(listitem)
            
            $(this).children().each(function() {
                var el = $(this).clone(true, false);
                
                var wrapper = $("<vbox><button/></vbox>");
                wrapper.element()._originalElement = this;
                
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
        el.element()._originalElement.setAttribute("kohidden", hide);
        
        el.element()._originalElement.ownerDocument.persist(el.element()._originalElement.id, "kohidden");
        
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
        
        $(".list-item", window).each(function()
        {
            var allHidden = true;
            for (let child of this.childNodes)
            {
                if (child.nodeName != "vbox")
                    continue;
                
                if (child.getAttribute("ishidden") != "true")
                    allHidden = false;
            }
            
            if (allHidden)
            {
                this.setAttribute("ishidden", "true");
                this._originalElement.setAttribute("kohidden", "true");
                this._originalElement.ownerDocument.persist(this._originalElement.id, "kohidden");
            }
        });
    }
    
    w.addEventListener("komodo-post-startup", this.init.bind(this));
    
})();