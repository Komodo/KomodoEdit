var parent = require("./menu");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui menulist element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/menulist
 * @extends module:ko/ui/menu
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var menulist = require("ko/ui/menulist").create();
 * menupopup.addMenuItem({ label: "Click me!", command: () => console.log("Hello!") });
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    
    
    /**
     * The model for the menulist UI element, this is what {@link model:ko/ui/menulist.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/menu~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL menulist, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/menulist}
     */
    (function() {

        this.name = "menulist";
        
        /**
         * Create a new menupopup UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         *
         * @returns {module:ko/ui/menulist~Model}
         */
        
        /**
         * Assign an onchange or onCommand eventhandler
         *
         * @param {Function} callback - The event handler.
         * @memberof module:ko/ui/menulist~Model
         */
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        
         /**
         * Return or set the current value of the element.
         *
         * @param {String=} [value] - value to be set
         *
         * @returns {String} the value of the element
         * @memberof module:ko/ui/menulist~Model
         */
        this.value = function(value)
        {
            if (value)
            {
                if ("value" in this.element)
                {
                    this.element.value = value;
                }

                this.element.setAttribute("value", value);
                this.element.setAttribute("label", value);
            }

            if ("value" in this.element && this.element.value)
                return this.element.value;
            if (this.element.hasAttribute("value") && this.element.getAttribute("value"))
                return this.element.getAttribute("value");
            if (this.element.hasAttribute("label"))
                return this.element.getAttribute("label");
            return "";
        };

    }).apply(this.Model);

}).apply(Module);
