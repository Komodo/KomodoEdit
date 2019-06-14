var $ = require("ko/dom");
var parent = require("./column");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui list element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/list
 * @extends module:ko/ui/column~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var list = require("ko/ui/list").create();
 * lists.addEntries(["blue","purple","pink"]);
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/list.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/column~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [vbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/vbox}
     */

    (function() {
        
        /**
         * Create a new list UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/list~Model}
         */

        this.init = function(entries, options = {})
        {
            this.parseOptions(options);

            this.$element = $($.createElement(this.name, this.attributes));
            this.$element.addClass("ui-list");
            this.element = this.$element.element();

            this.addEntries(entries);
        };
        
        /**
         * Add items to the list
        *
        * @param {array} items     Array of items to add, this calls {@link addEntry()} for each item
        *
        * @memberof module:ko/ui/list~Model
        */ 
        this.addEntries = function (entries)
        {
            for (let entry of entries) {
                this.addEntry(entry);
            }
        };
        
        /**
         * Add an item to the container
         *
         * @param {mixed} item  item to be added to the container.  Can be String (label), ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                      option object refers to an Options object used throughout this SDK. The options
         *                      should contain an attributes property to assign a label at the very
         *                      least: { label: "itemLabel" }
         * 
         * @memberof module:ko/ui/list~Model
         * 
         */ 
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
