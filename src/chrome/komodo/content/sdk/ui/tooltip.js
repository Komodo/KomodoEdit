var parent = require("./panel");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui tooltip element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/tooltip
 * @extends module:ko/ui/panel~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @example
 * var tooltip = require("ko/ui/tooltip").create();
 * XXX sample
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/tooltip.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/panel~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [tooltip]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/tooltip}
     */

    (function() {

        this.name = "tooltip";
        
        /**
         * Create a new tooltip UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/tooltip~Model}
         */

    }).apply(this.Model);

}).apply(Module);
