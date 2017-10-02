var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui checkbox element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/checkbox
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var checkbox = require("ko/ui/checkbox").create();
 * checkbox.checked("true");
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/checkbox.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [checkbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/checkbox}
     */
    (function() {

        this.name = "checkbox";
        /**
         * Create a new checkbox UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/checkbox~Model}
         */
        this.init = this.initWithLabel;
        
        /**
         * Add onChange even handler
         *
         * @param {function} callback - eventhandler callback
         * @memberof module:ko/ui/checkbox~Model
         * @deprecated use `.on("command", callback)` instead
         */
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        /**
         * return or set the selected state
         *
         * @param {String=} [value] - "true" or "false" to be selected or not
         *
         * @returns {boolean} true is selected
         * @memberof module:ko/ui/checkbox~Model
         */
        this.checked = function(value)
        {
            if (value !== undefined) {
                this.$element.attr("checked", value);
            }

            var val = this.$element.attr("checked");
            if ( ! val)
                return false;

            return ["false", "0"].indexOf(val) == -1;
        };
        /**
         * Return or set selected state
         *
         * @param {String=} [value] - value to be set
         *
         * @returns {boolean} true is selected
         * @memberof module:ko/ui/checkbox~Model
         */
        this.value = function(value)
        {
            if ( ! value)
                return this.checked();

            if (typeof value != "boolean")
            {
                var localValue = this.attributes.value || this.attributes.label || false;
                value = value == localValue;
            }
            return this.checked(value);
        };

    }).apply(this.Model);

}).apply(Module);
