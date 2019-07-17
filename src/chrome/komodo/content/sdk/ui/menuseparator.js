var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui menuseparator element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/menuseparator
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var menuseparator = require("ko/ui/menuseparator").create();
 * var menu = require("ko/ui/menulist").create(["pink","purple",menuseparator,"black","blue"])
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/menuseparator.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [menuseparator]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/menuseparator}
     */

    (function() {

        this.name = "menuseparator";
        
        /**
         * Create a new menuseparator UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/menuseparator~Model}
         */

    }).apply(this.Model); 
    
}).apply(Module);
