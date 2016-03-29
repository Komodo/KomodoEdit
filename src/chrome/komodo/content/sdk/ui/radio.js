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
        
        this.name = "radio";
        
        this.init = this.initWithLabel;
        
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        
        this.selected = function(value)
        {
            if (value)
            {
                this.$element.attr("selected", value);
            }
            return this.element.selected;
        };
        
        this.value = function(value)
        {
            if ( ! value)
                return this.selected();
            
            var localValue = this.attributes.value || this.attributes.label || false;
            var selected = value == localValue;
            this.selected(selected);
            
            return selected;
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
