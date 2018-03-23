var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

/**
 * ko/ui button element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/button
 * @extends module:ko/ui/element
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * // Regular button
 * var button = require("ko/ui/button").create("Click Me!");
 * button.on("click", () => console.log("Hello!"));
 * 
 * // Menu Button
 * var button = require("ko/ui/button").create("I'm a menu button", { type: "menu-button" }); // type can also be "menu"
 * button.addMenuItem({ label: "Click me!", command: () => console.log("Hello!") });
 */
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the button UI element, this is what {@link model:ko/ui/button.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~UiModelElement
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL Button, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/button}
     */
    (function() {
        
        this.name = "button";
        
        /**
         * Create a new button UI element
         * 
         * @name create
         * @method
         * @param  {string|object}  label       The label value, if this is an object then it will be used as the options param
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/button~Model}
         */
        this.init = this.initWithLabel;
        
        /**
         * Add a callback method that's used when the button is clicked
         * 
         * @example
         * button.onCommand(function() {
         *   console.log("button clicked");
         * });
         * 
         * @param   {function} callback     
         *
         * @memberof module:ko/ui/button~Model
         * @deprecated use `.on("command", callback)` instead
         */
        this.onCommand = function (callback)
        {
            this.$element.on("command", callback);
        };
        
         /**
         * Check if the button has the menu-button type set
         * 
         * @memberof module:ko/ui/button~Model
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
          * @param {array} item     Array of items to add, this calls {@link addMenuItem()} for each item
          *
          * @memberof module:ko/ui/button~Model
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
         * @param  {(Element|array|object|string)} appendElement - Element(s) to be appended. This can be a DOM element, ko/dom element or 
         *                                                      even just the name of an element. See {@link module:ko/ui/menupopup~Model.addMenuItem} 
         *                                                      for more information.
         *                                                      If this is a simple object then it will be used as the options param 
         * @memberof module:ko/ui/button~Model
         *
         * @returns {Element}   Returns {@link module:ko/dom~QueryObject}
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
            return require("ko/dom")(element);
        };
        
        /**
         * Return or set the current value of the element.
         *
         * @param {String=} [label] - label to be set
         *
         * @memberof module:ko/ui/button~Model
         * 
         * @returns {String} the value of the element
         */
        this.value = function (value)
        {
            if (value)
                this.attr("label", value);
            return this.attr("label");
        };

    }).apply(this.Model); 
    
}).apply(Module);
