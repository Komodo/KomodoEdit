var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui listheader element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/listheader
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var listheader = require("ko/ui/listheader").create();
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listheader.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listheader]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listheader}
     */

    (function() {

        this.name = "listheader";
        
        /**
         * Create a new listheader UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listheader~Model}
         */

        this.init = this.initWithLabel;

    }).apply(this.Model);

}).apply(Module);
