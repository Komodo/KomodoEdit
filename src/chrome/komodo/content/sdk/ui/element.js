/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 */

var $ = require("ko/dom");
var Module = {};
module.exports = Module;

(function() {
    
    this.Model = {};
    (function() {
        this.name = "element";
        
        this.isSdkElement = true;
        
        this.$element = null;
        this.element = null;
        
        this.options = {};
        this.attributes = {};
        
        this.init = function(options = {})
        {
            this.parseOptions(options);

            this.$element = $($.create(this.name, this.attributes).toString());
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();
        };

        this.parseOptions = function(options)
        {
            this.attributes = Object.assign(options.attributes || options, this.attributes);
            this.options = Object.assign(options.options || {}, this.options);
        };
        
        this.defaultInit = this.init;

        this.initWithAttribute = function(attribute, value, options = {})
        {
            if (typeof attribute == "object")
                options = attribute;
            else if (typeof value == "object")
                options = value;
                
            this.parseOptions(options);

            if (typeof attribute != "object" && typeof value != "object")
                this.attributes[attribute] = value;
            
            this.$element = $($.create(this.name, this.attributes).toString());
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();
        };
        
        this.initWithLabel = function(label, options = {})
        {
            if (label && typeof label == "object")
            {
                options = label;
                label = null;
            }

            this.parseOptions(options);
            options = this.options;
            
            if (options.label)
            {
                label = options.label;
            }
            
            if (typeof label == "string")
            {
                this.attributes.label = label;
            }

            this.$element = $($.create(this.name, this.attributes).toString());
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();
        };

        this.initWithElement = function(appendElement = null, options = {})
        {
            if ( ! Array.isArray(appendElement) && appendElement)
            {
                if ("isSdkElement" in appendElement || "koDom" in appendElement ||
                    "nodeName" in appendElement || ("type" in appendElement && ! ("attributes" in appendElement)))
                {
                    appendElement = [appendElement];
                } 
                else
                {
                    options = appendElement;
                    appendElement = null;
                }
            }
            
            this.parseOptions(options);
            this.$element = $($.createElement(this.name, this.attributes));
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();
            
            this.addElement(appendElement);
        };
        
        this.addElement = function(appendElement, preferredType = null)
        {
            var elements = [];
            
            if ( ! appendElement)
                return;
            
            if ( ! Array.isArray(appendElement))
                appendElement = [appendElement];
            
            for (let _element of appendElement)
            {
                if ( ! _element && ! preferredType)
                    continue;

                if (( ! _element || typeof _element == "string") && preferredType)
                {
                    elements.push(require('./' + preferredType).create(_element).element);
                }
                else if ("isSdkElement" in _element)
                {
                    elements.push(_element.element);
                }
                else if ("koDom" in _element)
                {
                    elements.push(_element.element());
                }
                else if ("nodeName" in _element)
                {
                    elements.push(_element);
                }
                else if ("type" in _element)
                {
                    elements.push(require('./' + _element.type).create(_element).element);
                }
                else if (preferredType)
                {
                    elements.push(require('./' + preferredType).create(_element).element);
                }
            }
            
            for (let element of elements) {
                this.$element.append(element);
            }
        };
        
        this.enable = function()
        {
            this.$element.removeAttr("disabled");
        };
        
        this.disable = function()
        {
            this.$element.attr("disabled", "true");
        };

        this.disabled = function()
        {
            var disabled = this.$element.attr("disabled");
            return disabled && disabled != "false" && disabled != "0";
        };
        
        this.hide = function()
        {
            this.$element.hide();
        };
        
        this.show = function()
        {
            this.$element.show();
        };
        
        this.on = function() { this.$element.on.apply(this.$element, arguments); };
        this.off = function() { this.$element.off.apply(this.$element, arguments); };
        this.once = function() { this.$element.once.apply(this.$element, arguments); };
        this.trigger = function() { this.$element.trigger.apply(this.$element, arguments); };
        
        this.focus = function() { this.$element.focus.apply(this.$element, arguments); };
        
        this.addClass = function() { this.$element.addClass.apply(this.$element, arguments); };
        this.removeClass = function() { this.$element.removeClass.apply(this.$element, arguments); };
        
        this.attr = function() { return this.$element.attr.apply(this.$element, arguments); };
        this.removeAttr = function() { this.$element.removeAttr.apply(this.$element, arguments); };
        
        this.hide = function() { this.$element.hide.apply(this.$element, arguments); };
        this.show = function() { this.$element.show.apply(this.$element, arguments); };

        this.empty = function() { this.$element.empty.apply(this.$element, arguments); };
        this.remove = function() { this.$element.remove.apply(this.$element, arguments); };
        
    }).apply(this.Model);
    
    this.create = function () 
    {
        var ob = Object.assign({}, this.Model);
        ob.init.apply(ob, arguments);
        return ob;
    };
    
}).apply(Module);
