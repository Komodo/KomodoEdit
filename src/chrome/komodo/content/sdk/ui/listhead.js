var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui listhead element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/listhead
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var listhead = require("ko/ui/listhead").create("Software GoodNess");
 * var listcol = require("ko/ui/listcol").create({flex:1});
 * var listcols = require("ko/ui/listcols").create();
 * listcols.addListCol(listcol);
 * var listbox = require("ko/ui/listbox").create();
 * listbox.listhead = listhead;
 * listbox.listcols = listcols;
 */

(function() {

    this.Model = Object.assign({}, this.Model);

    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listhead.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listhead]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listhead}
     */

    (function() {

        this.name = "listhead";
        
        /**
         * Create a new listhead UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listhead~Model}
         */
        
        /**
         * Add list column
         *
         * @param {mixed} item  item to be added to the container.  String, ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                      option object refers to an Options object used throughout this SDK. The options
         *                      should contain an attributes property to assign a label at the very
         *                      least: { label: "Text" }
         *        
         *  @memberof module:ko/ui/listhead~Model
         */ 
        this.addListHeader = function(listheader) { return this.addElement(listheader, "listheader"); };

    }).apply(this.Model);

}).apply(Module);
