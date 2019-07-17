var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui caption element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/caption
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var caption = require("ko/ui/caption").create();
 * caption.value("Eh yo eh, what's goin on?  Badaboom badabing.");
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/caption.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [label]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/label}
     */
    (function() {

        this.name = "caption";
        /**
         * Create a new caption UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/caption~Model}
         */
        this.init = function (value, options) { return this.initWithAttribute("label", value, options); };


    }).apply(this.Model);

}).apply(Module);
