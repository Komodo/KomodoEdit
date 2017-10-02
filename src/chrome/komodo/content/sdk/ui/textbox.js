var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;


/**
 * ko/ui textbox element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/textbox
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var textbox = require("ko/ui/textbox").create({width:200});
 * var panel = require("ko/ui/panel").create();
 * panel.addColumn(textbox);
 * panel.open();
 */

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/textbox.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [textbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/textbox}
     */

    (function() {
        
        this.name = "textbox";
        
        /**
         * Create a new textbox UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/textbox~Model}
         */

        this.onChange = function (callback)
        {
            this.$element.on("input", callback);
        };
        
        
        /**
         * Set or return the current text
         *
         * @param {String} [value] the string to be set as the text
         * @memberof module:ko/ui/textbox~Model
         */
        this.value = function(value)
        {
            // Set the value attribute, because who likes logic, right XUL?
            var attr = "value";
            if ("type" in this.attributes && this.attributes.type == "number")
                attr = "valueNumber";
                
            if (value)
            {
                this.$element.attr("value", value);
                if ("accessibleType" in this.element)
                    this.element[attr] = value;
            }
            return this.element[attr];
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

