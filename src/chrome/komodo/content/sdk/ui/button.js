/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

/**
 * ko/ui button element
 *
 * Inherits from {ko/ui/element}
 *
 * @module ko/ui/button
 */
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "button";
        
        /**
         * `var button = require("ko/ui/button").create("Button Label", { attributes: { tooltiptext: "tooltip" } });`
         *
         * Uses {ko/ui/element}.initWithLabel
         * 
         * @param {String|Object} label    If this is an object it will be used as the options param
         * @param {Object} options         { attributes: .. }
         */
        function create() {}
        
        this.init = this.initWithLabel;
        
        /**
         * ```
         * button.onCommand(function() {
         *   console.log("button clicked");
         * });
         * ```
         *
         * Add a callback method that's used when the button is clicked
         * 
         * @param   {Type} callback Description
         */
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
            if(this.element.getAttribute("type") != "menu-button" && this.element.getAttribute("type") != "menu")
            {
                var log = require("ko/logging").getLogger("ko/ui/button");
                log.warn("button must have 'type: menu-button' to use " +
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
        
        this.value = function (label)
        {
            if (label)
                this.attr("label", label);
            return this.attr("label");
        };

    }).apply(this.Model); 
    
}).apply(Module);
