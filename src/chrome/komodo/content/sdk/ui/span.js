var $ = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;


/**
 * ko/ui span element
 * 
 * This module inherits methods and properties from the module it extends.
 * Wrap text in a span tag.
 * 
 * @module ko/ui/span
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var span = require("ko/ui/span").create();
 */

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/span.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A HTML [span]{@link https://developer.mozilla.org/en-US/docs/Web/HTML/Element/span}
     */

    (function() {
        
        this.name = "html:span";
        this.attributes = { "xmlns:html": "http://www.w3.org/1999/xhtml" };
        
        /**
         * Create a new span UI element
         * 
         * @name create
         * @method
         * @param  {value}      [String]    Text to be placed in span
         * @param  {object}     [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/span~Model}
         */

        this.init = function(value, options = {})
        {
            this.parseOptions(options);
            this.$element = $($.createElement(this.name, this.attributes));
            this.$element.text(value);
            this.$element.addClass("ui-span");
            this.element = this.$element.element();
            this.element._sdk = this;
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

