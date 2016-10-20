/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

var parent = require("./element");
var Module = Object.assign({}, parent);
const log = require("ko/logging").getLogger("toolbarbutton");
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "toolbarbutton";
        this.init = this.initWithLabel;
        this.menupopup = null;
        
        this.onCommand = function (callback)
        {
            this.$element.on("command", callback);
        };
        
         /**
         * Check if the button has the menu-button type set
         *
         * @returns {boolean}
         */
        this.isMenuButton = function ()
        {
            if( ! this.element.type ==="menu-button" )
            {
                log.warn("Toolbarbutton must have 'type: menu-button' to use " +
                         "'addMenuItem/s' functions.");
                return false;
            }
            return true;
        };
        
         /**
          * Add items to the container
          *
          * @argument {Array[string, ko/ui/obj, ko/dom/obj, DOM, Object]} item item to be added
          * to the container.
          *
          * Basically, whatever addMenuItem can handle, this can handle it's array
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
          */ 
        this.addMenuItems = function (menuitems)
        {
            if( ! this.isMenuButton() )
            {
                return;
            }
            for (let menuitem of menuitems) {
                this.addMenuItem(menuitem);
            }
        };
        
        /**
         * Add an item to the container
         *
         * @argument {string, ko/ui/obj, ko/dom/obj, DOM, Object} item item to be added
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
         */ 
        this.addMenuItem = function (menuitem)
        {
            if( ! this.isMenuButton() )
            {
                return;
            }
            
            if ( ! this.menupopup )
            {
                this.menupopup = require("./menupopup").create();
                this.element.appendChild(this.menupopup.element);
            }
            
            var element = this.menupopup.addMenuItem(menuitem);
            
            if (element.getAttribute("selected") == "true" && "selectedItem" in this.element)
            {
                this.element.selectedItem = element;
            }
        };
    }).apply(this.Model); 
    
}).apply(Module);
