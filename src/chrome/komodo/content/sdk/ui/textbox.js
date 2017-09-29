/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 */

var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "textbox";
        
        this.onChange = function (callback)
        {
            this.$element.on("input", callback);
        };
        
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

