/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 */

var parent = require("./container");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "groupbox";
        
        this.init = function (appendElement = null, options = {})
        {
            if (appendElement && "caption" in appendElement)
            {
                options = appendElement;
                appendElement = null;
            }
            
            this.initWithElement(appendElement, options);
            
            if ("caption" in options)
            {
                this.$element.prepend(require("./caption").create(options.caption).element);
            }
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

