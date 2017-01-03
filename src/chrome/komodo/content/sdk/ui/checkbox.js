/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "checkbox";
        
        this.init = this.initWithLabel;
        
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        
        this.checked = function(value)
        {
            if (value !== undefined) {
                this.$element.attr("checked", value);
            }
            return this.element.checked;
        };
        
        this.value = function(value)
        {
            if ( ! value)
                return this.checked();
            
            if (typeof value != "boolean")
            {
                var localValue = this.attributes.value || this.attributes.label || false;
                value = value == localValue;
            }
            return this.checked(value);
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
