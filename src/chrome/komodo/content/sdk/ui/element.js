var $ = require("ko/dom");
var Module = {};
module.exports = Module;

/**
 * Base element, do not use this directly
 *
 * @module ko/ui/element
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 */
(function() {
    
    this.Model = {};

    /**
     * This is the model all other UI elements inherit from
     * 
     * @class Model
     * @property {string}                       name            Name of the node that will be inserted
     * @property {boolean}                      isSdkElement    Identify this as a UI sdk element to other modules
     * @property {module:ko/dom~QueryObject}    $element        The ko/dom instance for this element
     * @property {Element}                      element         The main DOM element for this UI element
     * @property {object}                       options         The options passed to this UI element
     * @property {object}                       attributes      The attributes passed to this UI element
     * @property {function}                     defaultInit     The default init function, used by extending modules that want to call the default init logic
     */
    (function() {

        this.name = "element";
        
        this.isSdkElement = true;
        
        this.$element = null;
        this.element = null;
        
        this.options = {};
        this.attributes = {};
        
        /**
         * The default init option
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @param {object} [options]    An object containing the attributes to set for the element, 
         *                                      can contain an "options" property to set options for the 
         *                                      current UI module (module dependent)
         */
        this.init = function(options = {})
        {
            this.parseOptions(options);

            this.$element = $($.create(this.name, this.attributes).toString());
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();
            this.element._sdk = this;
        };

        /**
         * Parses the options object given, this splits the options from the attributes
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @param  {object} [options]
         */
        this.parseOptions = function(options)
        {
            this.attributes = Object.assign(options.attributes || options, this.attributes);
            this.options = Object.assign(options.options || {}, this.options);
        };
        
        this.defaultInit = this.init;

        /**
         * Init function that takes an attribute, value as the first options 
         * 
         * Other UI modules can make this their init function, altering the 
         * .create() arguments
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @param  {string} attribute   The attribute to set, if this is an object then it will be used as the options param
         * @param  {string} value       The value to set
         * @param  {object} [options]   An object containing attributes and options
         */
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
            this.element._sdk = this;
        };
        
        /**
         * Init function that takes a label argument
         * 
         * Other UI modules can make this their init function, altering the 
         * .create() arguments
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @param  {string|object}  label       The label value, if this is an object then it will be used as the options param
         * @param  {object}         [options]   An object containing attributes and options
         */
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
            this.element._sdk = this;
        };

        /**
         * Init function that takes an element or array of elements as the first argument
         * The given elements will be appended to the created element.
         * 
         * Other UI modules can make this their init function, altering the 
         * .create() arguments
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @param  {(Element|array|object)}   appendElement       Element(s) to be appended. This can be a DOM element, ko/dom element or 
         *                                                      even just the name of an element. See {@link addElement()} 
         *                                                      for more information.
         *                                                      If this is a simple object then it will be used as the options param 
         * @param  {object}                 [options]           An object containing attributes and options
         */
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
            this.element._sdk = this;
            
            this.addElement(appendElement);
        };
        
        /**
         * Adds the given element to the current UI element
         * 
         * This function is designed to take a variety of element "types" to be appended
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @param  {(string|object|array|mixed)}  appendElement         The element to be appended, it can be a node name, 
         *                                                              a DOM element, a ko/dom element, an object containing 
         *                                                              a "type" (nodename) property, in which case it is passed
         *                                                              to `require("ko/ui/<type>").create(<appendElement>)`,
         *                                                              or an array containing any of the types mentioned.
         * @param  {(null|string)}                [preferredType]       If this is set and the element type cannot be detected
         *                                                              the preferredType is used to initialize a ko/ui/* element
         *                                                              eg, `require("ko/ui/<preferredType>").create(<appendElement>)`
         */
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
        
        /**
         * enable the element (removes disabled attribute)
         * 
         * @memberof module:ko/ui/element~Model
         */
        this.enable = function()
        {
            this.$element.removeAttr("disabled");
        };
        
        /**
         * disable the element (adds disabled=true attribute)
         * 
         * @memberof module:ko/ui/element~Model
         */
        this.disable = function()
        {
            this.$element.attr("disabled", "true");
        };

        /**
         * Check whether attribute is disabled
         * 
         * @memberof module:ko/ui/element~Model
         * 
         * @returns {boolean}
         */
        this.disabled = function()
        {
            var disabled = this.$element.attr("disabled");
            return disabled && disabled != "false" && disabled != "0";
        };
        
        /**
         * Hides the element, this calls {@link module:ko/dom~QueryObject.hide}
         * 
         * @memberof module:ko/ui/element~Model
         */
        this.hide = function()
        {
            this.$element.hide();
        };
        
        /**
         * Shows the element, this calls {@link module:ko/dom~QueryObject.show}
         * 
         * @memberof module:ko/ui/element~Model
         */
        this.show = function()
        {
            this.$element.show();
        };
        
        /**
         * Shortcut for this.$element.on, see {@link module:ko/dom~QueryObject.on}
         * @memberof module:ko/ui/element~Model
         */
        this.on = function() { this.$element.on.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.off, see {@link module:ko/dom~QueryObject.off}
         * @memberof module:ko/ui/element~Model
         */
        this.off = function() { this.$element.off.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.once, see {@link module:ko/dom~QueryObject.once}
         * @memberof module:ko/ui/element~Model
         */
        this.once = function() { this.$element.once.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.trigger, see {@link module:ko/dom~QueryObject.trigger}
         * @memberof module:ko/ui/element~Model
         */
        this.trigger = function() { this.$element.trigger.apply(this.$element, arguments); };
        
        /**
         * Shortcut for this.$element.focus, see {@link module:ko/dom~QueryObject.focus}
         * @memberof module:ko/ui/element~Model
         */
        this.focus = function() { this.$element.focus.apply(this.$element, arguments); };
        
        /**
         * Shortcut for this.$element.addClass, see {@link module:ko/dom~QueryObject.addClass}
         * @memberof module:ko/ui/element~Model
         */
        this.addClass = function() { this.$element.addClass.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.removeClass, see {@link module:ko/dom~QueryObject.removeClass}
         * @memberof module:ko/ui/element~Model
         */
        this.removeClass = function() { this.$element.removeClass.apply(this.$element, arguments); };
        
        /**
         * Shortcut for this.$element.attr, see {@link module:ko/dom~QueryObject.attr}
         * @memberof module:ko/ui/element~Model
         */
        this.attr = function() { return this.$element.attr.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.removeAttr, see {@link module:ko/dom~QueryObject.removeAttr}
         * @memberof module:ko/ui/element~Model
         */
        this.removeAttr = function() { this.$element.removeAttr.apply(this.$element, arguments); };
        
        /**
         * Shortcut for this.$element.hide, see {@link module:ko/dom~QueryObject.hide}
         * @memberof module:ko/ui/element~Model
         */
        this.hide = function() { this.$element.hide.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.show, see {@link module:ko/dom~QueryObject.show}
         * @memberof module:ko/ui/element~Model
         */
        this.show = function() { this.$element.show.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.empty, see {@link module:ko/dom~QueryObject.empty}
         * @memberof module:ko/ui/element~Model
         */
        this.empty = function() { this.$element.empty.apply(this.$element, arguments); };

        /**
         * Shortcut for this.$element.remove, see {@link module:ko/dom~QueryObject.remove}
         * @memberof module:ko/ui/element~Model
         */
        this.remove = function() { this.$element.remove.apply(this.$element, arguments); };
        
    }).apply(this.Model);
    
    /**
     * Create a new element, the arguments are forwarded to the init function of the element
     * 
     * @name create
     * @method
     * @param {variable} arguments  The arguments are determined by the init function of the element
     * 
     * @returns {module:ko/ui/element~Model}
     */
    this.create = function () 
    {
        var ob = Object.assign({}, this.Model);
        ob.init.apply(ob, arguments);
        return ob;
    };
    
}).apply(Module);
