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
        
        this.name = "html:ul";
        this.attributes = { "xmlns:html": "http://www.w3.org/1999/xhtml" };
        
        this.init = function(entries, options = {})
        {
            this.parseOptions(options);

            this.$element = $($.create(this.name, this.attributes).toString());
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
            
            var entryWrapper = $("<li>").append(element);
            this.$element.append(entryWrapper);
        };
        
    }).apply(this.Model); 
    
}).apply(Module);

