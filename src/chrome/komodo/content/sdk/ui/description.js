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
        
        this.name = "description";
        
        this.init = function (value, options)
        {
            if (typeof value == "object")
            {
                options = value;
                value = null;
            }

            this.defaultInit(options);

            if (value)
            {
                this.element.textContent = value;
            }
        };
        
        this.value = function(value)
        {
            if (value)
                this.$element.text(value);
            return this.$element.text();
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

