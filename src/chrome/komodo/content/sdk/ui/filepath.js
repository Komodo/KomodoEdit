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
        
        this.name = "hbox";
        this.attributes = { class: "ui-filepath" };
        
        this.init = function()
        {
            this.textbox = require("ko/ui/textbox").create();
            
            this.defaultInit.apply(this, arguments);
            
            var button = require("ko/ui/button").create("...");
            button.onCommand(() =>
            {
                var ko = require("ko/windows").getMain().ko;
                
                var type = this.options.type || "file";
                var value = this.textbox.value();
                
                var filter = this.option.filter || null;
                var filters = this.options.filters || null;

                switch (type)
                {
                    default:
                    case "file":
                        this.textbox.value(ko.filepicker.browseForFile(value, null, null, filter, filters));
                        break;
                    case "dir":
                        this.textbox.value(ko.filepicker.browseForDir(value));
                        break;
                    case "exe":
                        this.textbox.value(ko.filepicker.browseForExeFile(value));
                        break;
                    case "files":
                        this.textbox.value(ko.filepicker.browseForFiles(value));
                        break;
                    case "remote":
                        this.textbox.value(ko.filepicker.browseForRemoteDir(value));
                        break;
                }
            });
            
            this.addElement(this.textbox);
            this.addElement(button);
        };
        
        this.value = function() { return this.textbox.value.apply(this.textbox, arguments); };
        
    }).apply(this.Model);
    
}).apply(Module);
