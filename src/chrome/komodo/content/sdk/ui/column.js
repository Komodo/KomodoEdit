/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 */


var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "vbox";
        
    }).apply(this.Model);
    
}).apply(Module);
