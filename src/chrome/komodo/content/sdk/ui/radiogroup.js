/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

var $      = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent); 
module.exports = Module;

// Main module (module.exports)
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "hbox";
        
        this.formElement = null;
        this.$formElement = null;
        
        this.init = function(label, options = {})
        {
            var attributes = Object.assign(options.attributes || {}, this.attributes);
            
            if (Array.isArray(options))
            {
                options = { options: options };
            }
            
            if (typeof label == "object")
            {
                options = label;
                label = null;
            }
            else if (label)
            {
                options.label = label;
            }
            
            this.options = options;
            this.attributes = attributes;
            this.$element = $($.create(this.name).toString());
            this.$element.addClass("ui-radiogroup-wrapper");
            this.element = this.$element.element();
            
            this.$formElement = $($.create("radiogroup", attributes).toString());
            this.$formElement.addClass("ui-radiogroup");
            this.formElement = this.$formElement.element();
            this.$element.append(this.formElement);
            
            if (options.label)
            {
                this.$element.prepend(require("./label").create(options.label).element);
            }
            
            if (options.options)
            {
                for (let option of options.options) {
                    let element;
                    if ("isSdkElement" in option)
                        element = option.element;
                    else if ("koDom" in option)
                        element = option.element();
                    else if ("nodeName" in option)
                        element = option;
                    else
                        element = require("./radio").create(option).element;
                    
                    this.$formElement.append(element);
                }
            }
        };
        
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        
        this.value = function(value)
        {
            if ( ! value)
            {
                return this.value;
            }
            
            var formElement = this.formElement;
            this.$formElement.children().each(function ()
            {
                var localValue = this.getAttribute("value") || this.getAttribute("label") || false;
                this.removeAttribute("selected");
                if (value == localValue)
                {
                    //formElement.selectedItem = this;
                    this.setAttribute("selected", "true");
                }
            });
        };
        
    }).apply(this.Model); 
    
}).apply(Module);
