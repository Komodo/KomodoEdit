var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui label element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/label
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var label = require("ko/ui/label").create();
 * label.value("I really like labels.")
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/label.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [label]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/label}
     */

    (function() {

        this.name = "label";
        
        /**
         * Create a new label UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/label~Model}
         */

        this.init = function (value, options) { return this.initWithAttribute("value", value, options); };
        
        /**
         * Return or set selected state
         *
         * @param {String=} [value] - value to be set
         *
         * @returns {String} The set value
         * @memberof module:ko/ui/label~Model
         */
        this.value = function(value)
        {
            if (value !== undefined)
            {
                this.element.setAttribute("value", value);
                this.element.value = value;
            }

            return this.element.value || this.element.getAttribute("value");
        };

    }).apply(this.Model);

}).apply(Module);
