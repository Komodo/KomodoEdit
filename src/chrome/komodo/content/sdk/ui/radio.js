var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui radio element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/radio
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var radio = require("ko/ui/radio").create();
 * radio.selected("true");
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/radio.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [radio]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/radio}
     */
    (function() {

        this.name = "radio";
        /**
         * Create a new radio UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/radio~Model}
         */
        this.init = this.initWithLabel;

        /**
         * Add onChange even handler
         *
         * @param {function} callback - eventhandler callback
         * @memberof module:ko/ui/radio~Model
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
         * @memberof module:ko/ui/radio~Model
         */
        this.selected = function(value)
        {
            if (typeof value != "string")
            {
                if (value)
                {
                    this.$element.attr("selected", "true");
                }
                else
                {
                    this.$element.attr("selected", "false");
                }
            }
            else if (value)
            {
                this.$element.attr("selected", value);
            }
            return this.element.selected;
        };

        /**
         * Return or set selected state
         *
         * @param {String=} [value] - value to be set
         *
         * @returns {boolean} true is selected
         * @memberof module:ko/ui/radio~Model
         */
        this.value = function(value)
        {
            if ( ! value)
                return this.selected();

            var localValue = this.attributes.value || this.attributes.label || false;
            var selected = value == localValue;
            this.selected(selected);

            return selected;
        };

    }).apply(this.Model);

}).apply(Module);
