var $ = require("ko/dom");
var parent = require("./listbox");
var Module = Object.assign({}, parent);
var log = require("ko/logging").getLogger("sdk/ui/richlistbox");
//log.setLevel(require("ko/logging").LOG_DEBUG);
module.exports = Module;


/**
 * ko/ui richlistbox element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/richlistbox
 * @extends module:ko/ui/listbox~Model
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var richlistbox = require("ko/ui/richlistbox").create();
 * richlistbox.addListItems(["True","Blue"]);
 */

(function() {

    this.Model = Object.assign({}, this.Model);

    this.listhead = null;
    this.listcols = null;
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/richlistbox.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/listbox~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [richlistbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/richlistbox}
     */

    (function() {

        this.name = "richlistbox";
        
        /**
         * Create a new richlistbox UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/richlistbox~Model}
         */

        this.init = function(richlistitems = [], options = {})
        {
            if ( ! Array.isArray(richlistitems) && typeof richlistitems == "object")
            {
                options = richlistitems;
                richlistitems = null;
            }

            this.parseOptions(options);
            options = this.options;

            if ("richlistitems" in options)
            {
                richlistitems = options.richlistitems;
            }

            this.$element = $($.createElement(this.name, this.attributes));
            this.element = this.$element.element();
            this.element._sdk = this;

            if (richlistitems && Array.isArray(richlistitems))
            {
                this.addListItems(richlistitems);
            }
            else if (richlistitems && ! Array.isArray(richlistitems))
            {
                log.warn("List items must be in an array.  Failed to add list "+
                         "items to listbox.");
            }
        };

        /**
         * Add items to the listbox
        *
        * @param {array} items     Array of items to add, this calls {@link addListItem()} for each item
        *
        * @memberof module:ko/ui/richlistbox~Model
        */ 
        this.addListItems = function (entries)
        {
            for (let entry of entries) {
                this.addListItem(entry);
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
         * Object refers to an Options object used through this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *
         *  {
         *      attributes:
         *      {
         *          label:"itemLable"
         *      }
         *  }
         *  @memberof module:ko/ui/richlistbox~Model
         */ 
        this.addListItem = function (item)
        {
            var element;
            if (typeof item == "string") {
                element = require("ko/ui/richlistitem").create(item).element;
            }
            else if ("isSdkElement" in item)
            {
                element = item.element;
            }
            else if ("koDom" in item)
            {
                element = item.element();
            }
            else if ("nodeName" in item)
            {
                element = item;
            }
            else
            {
                var type = item.type || "richlistitem";
                element = require('./' + type).create(item).element;
            }

            this.$element.append(element);

            if (element.getAttribute("selected") == "true" && "selectedItem" in this.element)
            {
                this.element.selectedItem = element;
            }
        };

        /**
         * Get list of selected items
         *
         * @returns {array} an array of selected items
         * @memberof module:ko/ui/richlistbox~Model
         */
        this.getSelectedItems = function()
        {
            return this.element.selectedItems;
        };
    
        /**
         * Get the selected item index in the lists
         *
         * @returns {element} the selected item
         * @memberof module:ko/ui/richlistbox~Model
         */
        this.getSelectedItem = function()
        {
            return this.element.selectedItem;
        };
        
        /**
         * Remove all items from the list
         *
         * @memberof module:ko/ui/richlistbox~Model
         */
        this.removeAllItems = function()
        {
            this.$element.empty();
        };

        /**
         * Move selection up one 
         *
         * @memberof module:ko/ui/richlistbox~Model
         */
        this.moveSelectionUp = function()
        {
            this.element.moveByOffset(-1, true, false);
        };

        /**
         * Move selection down one 
         *
         * @memberof module:ko/ui/richlistbox~Model
         */
        this.moveSelectionDown = function()
        {
            this.element.moveByOffset(1, true, false);
        };

    }).apply(this.Model);

}).apply(Module);
