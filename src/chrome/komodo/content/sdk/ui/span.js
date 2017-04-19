/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 */

var $ = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "html:span";
        this.attributes = { "xmlns:html": "http://www.w3.org/1999/xhtml" };
        
        this.init = function(value, options = {})
        {
            this.parseOptions(options);
            this.$element = $($.create(this.name, this.attributes).toString());
            this.$element.text(value);
            this.$element.addClass("ui-span");
            this.element = this.$element.element();
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

