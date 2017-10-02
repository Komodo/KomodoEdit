var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui row element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/row
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var row = require("ko/ui/row").create();
 * row.addColumn(require("ko/ui/row").create());
 */
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/row.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL hbox, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/hbox}
     */
    (function() {
        
        this.name = "hbox";
        
         /**
         * Create a new row UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/row~Model}
         */
        
    }).apply(this.Model);
    
}).apply(Module);
