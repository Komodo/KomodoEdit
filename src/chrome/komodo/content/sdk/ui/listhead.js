/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview listhead sub module for the ko/ui SDK
 */

var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    this.listhead = null;
    this.listcols = null;
    
    (function() {
        
        this.name = "listhead";
        
        this.addListHeader = function(listheader) { return this.addElement(listheader, "listheader"); };
        
    }).apply(this.Model); 
    
}).apply(Module);

