/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "menupopup";
        
        /**
         * Add an item to the container
         *
         * @argument {string, ko/ui/obj, ko/dom/obj, DOM, Object} item item to be added
         * to the container.
         *
         * @returns {DOM Object} DOM element
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
         */ 
        this.addMenuItem = function(menuitem)
        {
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
            this.$element.append(element);
            return element;
        };
        
        /**
         * Remove all elements in the menupopup
         */
        this.empty = function()
        {
            this.$element.empty();
        };
        
        /**
         * Remove an item from the list
         *
         * @argument @argument {ko/ui/obj, ko/dom/obj, DOM} item item to be removed
         * to the container.
         */
        this.removeItem = function(item)
        {
            if ("isSdkElement" in item)
            {
                this.element.removeChild(item.element);
            }
            else if ("koDom" in item)
            {
               this.element.removeChild(item.element());
            }
            else if ("nodeName" in item)
            {
                this.element.removeChild(item);
            }
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
