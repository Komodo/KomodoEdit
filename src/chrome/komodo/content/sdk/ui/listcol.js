var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui listcol element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/listcol
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @example
 * var listbox = require("ko/ui/listbox").create();
 * var listcol = require("ko/ui/listcol").create();
 * listbox.addListCol(listcol);
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listcol.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listcol]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listcol}
     */

    (function() {

        this.name = "listcol";
        
        /**
         * Create a new listcol UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listcol~Model}
         */

    }).apply(this.Model);

}).apply(Module);

