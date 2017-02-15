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
        
        this.name = "label";
        
        this.init = function (value, options) { return this.initWithAttribute("value", value, options); };
        
        this.value = function(value)
        {
            if (value !== undefined)
            {
                this.element.setAttribute("value", value);
                this.element.value = value;
            }

            return this.element.value || this.element.getAttribute("value");
        };

    }).apply(this.Model); 
    
}).apply(Module);

