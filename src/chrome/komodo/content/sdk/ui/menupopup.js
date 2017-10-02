var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

/**
 * ko/ui menupopup element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/menupopup
 * @extends module:ko/ui/element
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var menupopup = require("ko/ui/menupopup").create();
 * menupopup.addMenuItem({ label: "Click me!", command: () => console.log("Hello!") });
 */
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the menupopup UI element, this is what {@link model:ko/ui/menupopup.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL Menupopup, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/menupopup}
     */
    (function() {
        
        this.name = "menupopup";

        /**
         * Create a new menupopup UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/menupopup~Model}
         */

        
        /**
         * Add items to the menupopup
        *
        * @param {array} item     Array of items to add, this calls {@link addMenuItem()} for each item
        *
        * @memberof module:ko/ui/menupopup~Model
        */ 
        this.addMenuItems = function (menuitems)
        {
            for (let menuitem of menuitems) {
                this.addMenuItem(menuitem);
            }
        };
        
        /**
         * Add an item to the container
         *
         * @param {mixed} item  item to be added to the container.  Can be String (label), ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                      option object refers to an Options object used throughout this SDK. The options
         *                      should contain an attributes property to assign a label at the very
         *                      least: { label: "itemLabel" }
         * 
         * 
         * @returns {Element}   Returns the inserted element, may be a ko/ui/element, ko/dom element or DOM element
         * @memberof module:ko/ui/menupopup~Model
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
         * Add a {@link module:ko/ui/menuseparator}
         * 
         * @memberof module:ko/ui/menupopup~Model
         */
        this.addSeparator = function()
        {
            this.$element.append(require("ko/ui/menuseparator").create().element);
        };
        
        /**
         * Removes the given menuitem
         *
         * @param {mixed} item  menuitem to be removed to the container, see {@link addMenuItem()} for type info
         * 
         * @memberof module:ko/ui/menupopup~Model
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
        
        /**
         * Open the menupopup
         * 
         * @memberof module:ko/ui/menupopup~Model
         */
        this.open = function() { this.element.openPopup.apply(this.element, arguments); };

        /**
         * Hide/close the menupopup
         * 
         * @memberof module:ko/ui/menupopup~Model
         */
        this.hide = function() { this.element.hidePopup.apply(this.element, arguments); };

    }).apply(this.Model); 
    
}).apply(Module);
