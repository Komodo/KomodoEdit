var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui listcols element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/listcols
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var listcol = require("ko/ui/listcol").create();
 * var listcols = require("ko/ui/listcols").create();
 * listcols.addListCol(listcol);
 * var listbox = require("ko/ui/listbox").create();
 * listbox.listcols = listcols;
 */

(function() {

    this.Model = Object.assign({}, this.Model);

    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listcols.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listcols]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listcols}
     */

    (function() {

        this.name = "listcols";
        /**
         * Create a new listcols UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listcols~Model}
         */
        
        /**
         * Add list column
         *
         * @param {mixed} item  item to be added to the container.  ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                      option object refers to an Options object used throughout this SDK. The options
         *                      should contain an attributes property to assign a label at the very
         *                      least: { flex: 1 }
         *        
         *  @memberof module:ko/ui/listcols~Model
         */ 
        this.addListCol = function(listcol) { return this.addElement(listcol, "listcol"); };

    }).apply(this.Model);

}).apply(Module);
