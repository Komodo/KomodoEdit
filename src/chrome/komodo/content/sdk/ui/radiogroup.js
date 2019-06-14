var $      = require("ko/dom");
var parent = require("./container");

var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui radiogroup element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/radiogroup
 * @extends module:ko/ui/container
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var radiogroup = require("ko/ui/radiogroup").create();
 * menupopup.addRadioItems(["red","green","blue","yellow"]);
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the menupopup UI element, this is what {@link model:ko/ui/menupopup.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL hbox, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/hbox}
     * @property {Element}      formElement     A XUL radiogroup, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/radiogroup}
     * @property {Element}      $formElement    A @module:ko/dom~QueryObject
     */
    (function() {

        this.name = "hbox";

        this.formElement = null;
        this.$formElement = null;
        /**
         * Create a new radiogroup UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/radiogroup~Model}
         */
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

        /**
         * Add onChange even handler
         *
         * @param {function} callback - eventhandler callback
         * @memberof module:ko/ui/radiogroup~Model
         * @deprecated use `.on("command", callback)` instead
         */
        this.onChange = function (callback)
        {
            this.$element.on("command", callback);
        };

        /**
         * Add multiple item to the container
         *
          @param {Array} item - item to be added to the container.  Array of items to add, this calls {@link addRadioItem()} for each item
         *
         * @memberof module:ko/ui/radiogroup~Model
         */
        this.addRadioItems = function (items)
        {
            for (let item of items) {
                this.addRadioItem(item);
            }
        };

        /**
         * Add an item to the container
         *
         * @param {(string|object|array|mixed)} item    item to be added to the container.  Can be String (label), ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                                              option object refers to an Options object used throughout this SDK. The options
         *                                              should contain an attributes property to assign a label at the very
         *                                              least: { label: "itemLabel" }
         *                      
         * @returns {Element} DOM element Object 
         *
         * @example
         * `opts` refers to an Options object used throughout this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *  {
         *      attributes:
         *      {
         *          label:"itemLable",
         *          value:"itemValue // if not supplied, `label` is used as `value`
         *      }
         *  }
         * @memberof module:ko/ui/radiogroup~Model
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

        /**
         * Return or set the current value of the element.
         *
         * @param {String=} [value] - value to be set
         *
         * @returns {String} the value of the element
         * @memberof module:ko/ui/radiogroup~Model
         */
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
