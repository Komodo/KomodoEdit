var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui description element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/description
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var  = require("ko/ui/description").create();
 * description.value("Oh no!!  Pizza the Hut!!");
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/description.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element   A XUL [description]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/description}
     */

    (function() {

        this.name = "description";
        
        /**
         * Create a new description UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/description~Model}
         */

        this.init = function (value, options)
        {
            if (typeof value == "object")
            {
                options = value;
                value = null;
            }

            this.defaultInit(options);

            if (value)
            {
                this.element.textContent = value;
            }
        };
        
        /**
         * Return or set selected state
         *
         * @param {String=} [value] - value to be set
         *
         * @returns {String} The set value
         * @memberof module:ko/ui/description~Model
         */
        this.value = function(value)
        {
            if (value)
                this.$element.text(value);
            return this.$element.text();
        };

    }).apply(this.Model);

}).apply(Module);
