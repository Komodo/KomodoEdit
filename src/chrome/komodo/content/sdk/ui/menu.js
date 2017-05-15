/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

var parent = require("./element");
var Module = Object.assign({}, parent);
var $ = require("ko/dom");
var log = require("ko/logging").getLogger("sdk/ui/menu");
//log.setLevel(require("ko/logging").LOG_DEBUG);
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "menu";
        this.menupopup = null;
        
        this.init = function(menuitems = [], options = {})
        {
            if ( ! Array.isArray(menuitems) && typeof menuitems == "object")
            {
                options = menuitems;
                menuitems = null;
            }
            
            this.parseOptions(options);
            options = this.options;

            if ("menuitems" in options)
            {
                menuitems = options.menuitems;
            }
            
            this.$element = $($.createElement(this.name, this.attributes));
            this.element = this.$element.element();
            this.$element.addClass("ui-" + this.name);
            this.element._sdk = this;
            
            if (menuitems && Array.isArray(menuitems))
            {
                this.addMenuItems(menuitems);
            }
            else if (menuitems && ! Array.isArray(menuitems))
            {
                log.warn("Menu items must be in an array.  Failed to add menu "+
                         "items to menu.");
            }
        };
        
        this.entries = function() { this.addMenuItems.apply(this, arguments); };
        
        this.addMenuItems = function (menuitems)
        {
            for (let menuitem of menuitems) {
                this.addMenuItem(menuitem);
            }
        };
        
        /**
         * Add an item to the container
         *
         * @argument {ko/ui/obj|ko/dom/obj|DOM|Object} item item to be added
         * to the container.
         *
         * Object refers to an Options object used through this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *
         *  {
         *      attributes:
         *      {
         *          label:"itemLable"
         *      }
         *  }
         *
         *
         * 
         */ 
        this.addMenuItem = function (menuitem)
        {
            if ( ! this.menupopup )
            {
                this.menupopup = require("./menupopup").create();
                this.$element.append(this.menupopup.element);
            }
            
            var element;
            if (typeof menuitem == "string") {
                element = require("ko/ui/menuitem").create(menuitem).element;
            }
            else if ("isSdkElement" in menuitem)
            {
                element = menuitem.element;
            }
            else if ("koDom" in menuitem)
            {
                element = menuitem.element();
            }
            else if ("nodeName" in menuitem)
            {
                element = menuitem;
            }
            else
            {
                var type = menuitem.type || "menuitem";
                
                if ("menuitems" in menuitem)
                {
                    type = "menu";
                }
                
                element = require('./' + type).create(menuitem).element;
            }
            
            this.menupopup.addMenuItem(element);
            var $element = $(element);
            // Don't set if it's already set.
            if ( $element.attr("tooltiptext") === "" )
            {
                $element.attr("tooltiptext", $(element).attr("label") );
            }
            
            if (element.getAttribute("selected") == "true" && "selectedItem" in this.element)
            {
                this.element.selectedItem = element;
            }
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
