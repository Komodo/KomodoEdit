var parent = require("./button");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui toolbarbutton element
 * 
 * This module inherits methods and properties from the module it extends.
 * Create a toolbar .
 * 
 * @module ko/ui/toolbarbutton
 * @extends module:ko/ui/button~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var toolbarbutton = require("ko/ui/toolbarbutton").create();
 * XXX sample
 */

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/toolbarbutton.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/button~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [vbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/vbox}
     */

    (function() {
        
        this.name = "toolbarbutton";
        
        /**
         * Create a new toolbarbutton UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/toolbarbutton~Model}
         */

    }).apply(this.Model); 
    
}).apply(Module);
