/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 */

var $ = require("ko/dom");
var parent = require("./column");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.init = function(entries, options = {})
        {
            this.parseOptions(options);

            this.$element = $($.createElement(this.name, this.attributes));
            this.$element.addClass("ui-list");
            this.element = this.$element.element();
            
            this.addEntries(entries);
        };
        
        this.addEntries = function (entries)
        {
            for (let entry of entries) {
                this.addEntry(entry);
            }
        };
        
        this.addEntry = function (entry)
        {
            var element;
            if ("isSdkElement" in entry)
            {
                element = entry.element;
            }
            else if ("koDom" in entry)
            {
                element = entry.element();
            }
            else if ("nodeName" in entry)
            {
                element = entry;
            }
            else
            {
                return;
            }
            
            this.addRow(element);
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

