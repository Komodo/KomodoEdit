(function() {
    
    var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"]
                    .getService(Components.interfaces.nsIWindowMediator);

    var w = wm.getMostRecentWindow('Komodo');
    var require = w.require;
    var $ = require("ko/dom");
    
    elems = {
        mainTb: $("#main-toolbar", window),
        secondTb: $("#second-toolbar", window)
    }
    
    this.init = function ()
    {
        this.populateList("main");
        this.populateList("second");
        
        window.onConfirmDialog = function() {};
    }
    
    this.populateList = function(which = "main")
    {
        var el = elems[which + "Tb"];
        $("#"+which+"-toolboxrow toolbaritem", w).each(function() {
            
            var listitem = $("<richlistitem>");
            listitem.attr("ishidden", this.getAttribute("kohidden"));
            el.append(listitem)
            
            var children = $(this).children().clone();
            children.each(function() {
                var wrapper = $("<vbox><button/></vbox>");
                
                wrapper.attr("ishidden", this.getAttribute("kohidden"));
                
                this.removeAttribute("kohidden");
                this.removeAttribute("observes");
                this.removeAttribute("oncommand");
                this.removeAttribute("onclick");
                this.removeAttribute("disabled");
                this.removeAttribute("checked");
                
                wrapper.prepend(this);
                listitem.append(wrapper);
            });
            
            listitem.append("<separator>");
            listitem.append("<button class='move'/>");
            listitem.append("<button class='toggle'/>");
        });
    }
    
    window.addEventListener("load", this.init.bind(this));
    
})();