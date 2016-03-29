/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

var parent = require("./menu");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "menulist";
        
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        
        this.value = function(value)
        {
            if (value)
            {
                var element = this.element;
                this.$element.children().each(function ()
                {
                    var localValue = this.getAttribute("value") || this.getAttribute("label") || false;
                    this.removeAttribute("selected");
                    if (value == localValue)
                    {
                        element.selectedItem = this;
                        element.value = value;
                        this.setAttribute("selected", "true");
                    }
                });
            }
            
            return this.element.value || this.element.getAttribute("label");
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
