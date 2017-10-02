var parent = require("./element");
var Module = Object.assign({}, parent);
var $ = require("ko/dom");
var log = require("ko/logging").getLogger("sdk/ui/menu");
//log.setLevel(require("ko/logging").LOG_DEBUG);
module.exports = Module;

/**
 * ko/ui menu element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/menu
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var menu = require("ko/ui/menu").create();
 * menupopup.addMenuItem({ label: "Click me!", command: () => console.log("Hello!") });
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the menu UI element, this is what {@link model:ko/ui/menu.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL menu, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/menu}
     * @property {model:ko/ui/menupopup~Model}        menupopup   A XUL menu, see {@link model:ko/ui/menupopup~Model}
     */
    (function() {

        this.name = "menu";
        this.menupopup = null;
        
        /**
         * Create a new menu UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/menu~Model}
         */
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
        
        /**
         * Add items to the menu
        *
        * @param {array} items     Array of items to add, this calls {@link addMenuItem()} for each item
        *
        * @memberof module:ko/ui/menu~Model
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
         * @memberof module:ko/ui/menu~Model
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
