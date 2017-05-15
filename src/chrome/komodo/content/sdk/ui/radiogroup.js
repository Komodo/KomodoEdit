/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview col sub module for the ko/ui SDK
 *
 */

var $      = require("ko/dom");
var parent = require("./container");

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
            
            this.parseOptions(options);
            options = this.options;
            
            this.$element = $($.createElement(this.name));
            this.$element.addClass("ui-radiogroup-wrapper");
            this.element = this.$element.element();
            this.element._sdk = this;
            
            this.$formElement = $($.createElement("radiogroup", this.attributes));
            this.$formElement.addClass("ui-radiogroup");
            this.formElement = this.$formElement.element();
            this.$element.append(this.formElement);
            
            if (options.label)
            {
                this.$element.prepend(require("./label").create(options.label).element);
            }
            var radioBtns = options.options;
            if (radioBtns && Array.isArray(radioBtns))
            {
                this.addRadioItems(radioBtns);
            }
            else if (radioBtns && ! Array.isArray(radioBtns))
            {
                log.warn("Radio items must be in an array.  Failed to add menu "+
                         "items to menu.");
            }
        };
        
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };
        
        this.addRadioItems = function (items)
        {
            for (let item of items) {
                this.addRadioItem(item);
            }
        };
        
        /**
         * Add an item to the container
         *
         * @argument {string, ko/ui/obj, ko/dom/obj, DOM, Object} item item to be added
         * to the container.
         *
         * @returns {DOM Object} DOM element
         *
         * Object refers to an Options object used through this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *
         *  {
         *      attributes:
         *      {
         *          label:"itemLable",
         *          value:"itemValue // if not supplied, `label` is used as `value`
         *      }
         *  }
         *  
         */ 
        this.addRadioItem = function(item)
        {
            let element;
                if ("isSdkElement" in item)
                    element = item.element;
                else if ("koDom" in item)
                    element = item.element();
                else if ("nodeName" in item)
                    element = item;
                else
                    element = require("./radio").create(item).element;
            this.$formElement.append(element);
            return element;
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
