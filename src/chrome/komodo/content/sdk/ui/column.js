var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;
/**
 * ko/ui column element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/column
 * @extends module:ko/ui/container~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var column = require("ko/ui/column").create();
 * column.addRow(require("ko/ui/button").create("Click Me"));
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/column.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [vbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/vbox}
     */
    (function() {

        this.name = "vbox";
        /**
         * Create a new column UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/column~Model}
         */
    }).apply(this.Model);

}).apply(Module);
