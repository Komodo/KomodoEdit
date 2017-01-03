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
    
    this.listhead = null;
    this.listcols = null;
    
    (function() {
        
        this.name = "listcols";
        
        this.addListCol = function(listcol) { return this.addElement(listcol, "listcol"); };
        
    }).apply(this.Model); 
    
}).apply(Module);

