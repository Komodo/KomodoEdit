var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui menuitem element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/menuitem
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var menuitem = require("ko/ui/menuitem").create();
 * XXX sample
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/menuitem.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element  XXX   A XUL [vbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/vbox}
     */

    (function() {

        this.name = "menuitem";
        
        /**
         * Create a new menuitem UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/menuitem~Model}
         */

        this.init = function(label, options = {})
        {
            if (label && typeof label == "object")
            {
                options = label;
                label = null;
            }

            if (options.label)
            {
                label = options.label;
            }

            this.initWithLabel(label, options);

            if ( ! this.attributes.value && label)
            {
                this.$element.attr("value", label);
            }
        };

    }).apply(this.Model);

}).apply(Module);
