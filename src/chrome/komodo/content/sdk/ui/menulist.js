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
                this.element.setAttribute("value", value);
                this.element.setAttribute("label", value);
            }
            
            if (value in this.element)
                return this.element.value;
            if (this.element.hasAttribute("value"))
                return this.element.getAttribute("value");
            if (this.element.hasAttribute("label"))
                return this.element.getAttribute("label");
            return "";
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
