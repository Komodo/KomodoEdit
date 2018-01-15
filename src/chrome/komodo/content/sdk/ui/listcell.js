var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui listcell element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/listcell
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @example
 * // You shouldnt' be using this directly.  List item instead.  This listitem wraps list cell
 * var listitem = require("ko/ui/listitem").create();
 * listitem.addListCell("A Cell")
 * var listbox = require("ko/ui/listbox").create();
 * listbox.addListItem(listitem);
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listcell.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listcell]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listcell}
     */

    (function() {

        this.name = "listcell";
        
        /**
         * Create a new listcell UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listcell~Model}
         */

        this.init = this.initWithLabel;

    }).apply(this.Model);

}).apply(Module);

