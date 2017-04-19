/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 */

var parent = require("./button");
var Module = Object.assign({}, parent);
module.exports = Module;

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.attributes = {
            type: "menu",
            class: "ui-button ui-interpolation-button rightarrow-button"
        };
        
        this.init = function()
        {
            this.defaultInit.apply(this, arguments);
            
            this.addMenuItems([
                { attributes: { label: "%% : escaped percent sign", value: "%%" } },
                { attributes: { label: "%f : file base name", value: "%f" } },
                { attributes: { label: "%F : file path", value: "%F" } },
                { attributes: { label: "%d : directory base name of file", value: "%d" } },
                { attributes: { label: "%D : directory path of file", value: "%D" } },
                { attributes: { label: "%b : file base name without extension", value: "%b" } },
                { attributes: { label: "%i : project base directory", value: "%i" } },
                { attributes: { label: "%P : path of the active project file", value: "%P" } },
                { attributes: { label: "%p : directory path of the active project file", value: "%p" } },
                { type: "menuseparator" },
                { attributes: { label: "%L : current line number", value: "%L" } },
                { attributes: { label: "%l : current line text", value: "%l" } },
                { attributes: { label: "%s : selection", value: "%s" } },
                { attributes: { label: "%S : URL-escaped selection", value: "%S" } },
                { attributes: { label: "%w : selection or word under cursor", value: "%w" } },
                { attributes: { label: "%W : URL-escaped selection or word under cursor", value: "%W" } },
                { type: "menuseparator" },
                { attributes: { label: "%(browser) : configured browser", value: "%(browser)" } },
                { type: "menuseparator" },
                { attributes: { label: "%(ask:QUESTION:DEFAULT) : ask for user input", value: "%(ask:QUESTION:DEFAULT)" } },
                { attributes: { label: "%(askpass:Password) : ask for password", value: "%(askpass:Password)" }  }
            ]);
            
            this.on("command", (e) =>
            {
                this.$element.trigger("select", e.target.value);
                
                var prev = this.$element.prev();
                if (prev.element().nodeName == "textbox" &&
                    prev.attr("readonly") != "true" &&
                    prev.attr("disabled") != "true")
                {
                    prev.element().value += e.target.value;
                }
            });
        };
        
    }).apply(this.Model);
    
}).apply(Module);
