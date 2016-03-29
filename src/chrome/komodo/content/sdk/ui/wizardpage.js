/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Page sub module for the wizard SDK module
 */

var parent = require("./container");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        // Set the element name
        this.name = "wizardpage";
        this.attributes = { style: "overflow: -moz-hidden-unscrollable" };
        
        // .. that's it, all the rest is handled by the parent(s)
        
    }).apply(this.Model); // extend parent Model
    
}).apply(Module);