var $ = require("ko/dom");
var parent = require("./element");
var Module = Object.assign({}, parent);
var log = require("ko/logging").getLogger("sdk/ui/listbox");
//log.setLevel(require("ko/logging").LOG_DEBUG);
module.exports = Module;


/**
 * ko/ui listbox element
 * 
 * This module inherits methods and properties from the module it extends.
 *
 * @module ko/ui/listbox
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var panel = require("ko/ui/panel").create();
 * var listbox = require("ko/ui/listbox").create();
 * panel.addColumn(listbox);
 * listbox.addListHeader("Good food");
 * listbox.addListCol({width:200});
 * listbox.addListItem("Still pizza");
 * panel.open()
 */

(function() {

    this.Model = Object.assign({}, this.Model);

    this.listhead = null;
    this.listcols = null;
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listbox.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listbox]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listbox}
     * @property {Element}      listhead    {@link module:ko/ui/listhead~Model}
     * @property {Element}      listcols    {@link module:ko/ui/listcols~Model}
     */

    (function() {

        this.name = "listbox";
        
        /**
         * Create a new listbox UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listbox~Model}
         */
        this.init = function(listitems = [], options = {})
        {
            if ( ! Array.isArray(listitems) && typeof listitems == "object")
            {
                options = listitems;
                listitems = null;
            }

            this.parseOptions(options);
            options = this.options;

            if ("listitems" in options)
            {
                listitems = options.listitems;
            }

            this.$element = $($.createElement(this.name, this.attributes));
            this.$element.addClass("ui-" + this.name);
            this.element = this.$element.element();

            if (listitems && Array.isArray(listitems))
            {
                this.addListItems(listitems);
            }
            else if (listitems && ! Array.isArray(listitems))
            {
                log.warn("List items must be in an array.  Failed to add list "+
                         "items to listbox.");
            }

            if ("listheaders" in options)
            {
                this.addListHeaders(options.listheaders);
            }

            if ("listcols" in options)
            {
                this.addListCols(options.listcols);
            }
        };
        
        /**
         * Add items to the listbox
        *
        * @param {array} items     Array of items to add, this calls {@link addListItem()} for each item
        *
        * @memberof module:ko/ui/listbox~Model
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
         *  @memberof module:ko/ui/listbox~Model
         */ 
        this.addListItem = function (item)
        {
            var element;
            if (typeof item == "string") {
                element = require("ko/ui/listitem").create(item).element;
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
                var type = item.type || "listitem";
                element = require('./' + type).create(item).element;
            }

            this.$element.append(element);

            if (element.getAttribute("selected") == "true" && "selectedItem" in this.element)
            {
                this.element.selectedItem = element;
            }
        };

       /**
        * Add list headers to the listbox
        *
        * @param {array} items     Array of items to add, this calls {@link addListHeader()} for each item
        *
        * @memberof module:ko/ui/listbox~Model
        */ 
        this.addListHeaders = function(listheaders)
        {
            for (let listhead of listheaders)
            {
                this.addListHeader(listhead);
            }
        };
        
        /**
         * Add list header
         *
         * @param {mixed} item  item to be added to the container.  Can be String (label), ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                      option object refers to an Options object used throughout this SDK. The options
         *                      should contain an attributes property to assign a label at the very
         *                      least: { label: "itemLabel" }
         *        
         *  @memberof module:ko/ui/listbox~Model
         */ 
        this.addListHeader = function(header)
        {
            if ( ! this.listhead)
            {
                this.listhead = require("./listhead").create();
                this.$element.append(this.listhead.$element);
            }

            this.listhead.addListHeader.apply(this.listhead, arguments);
        };
        
        /**
        * Add list columns to the listbox
        *
        * @param {array} items     Array of items to add, this calls {@link addListCol()} for each item
        *
        * @memberof module:ko/ui/listbox~Model
        */ 
        this.addListCols = function(listcols)
        {
            for (let listcol of listcols)
            {
                this.addListCol(listcol);
            }
        };
        
        /**
         * Add list column
         *
         * @param {mixed} item  Calls @module:ko/ui/listcols~Model.addListCol
         *        
         *  @memberof module:ko/ui/listbox~Model
         */ 
        this.addListCol = function()
        {
            if ( ! this.listcols)
            {
                this.listcols = require("./listcols").create();
                this.$element.append(this.listcols.$element);
            }

            this.listcols.addListCol.apply(this.listcols, arguments);
        };
        
        /**
         * Set the selected item index in the lists
         *
         * @param {integer} index   The index of the item to be selected
         * @memberof module:ko/ui/listbox~Model
         */
        this.setSelectedIndex = function(index)
        {
            this.element.selectedIndex = index;
        };

        /**
         * Get list of selected items
         *
         * @returns {array} an array of selected items
         * @memberof module:ko/ui/listbox~Model
         */
        this.getSelectedItems = function()
        {
            return this.element.selectedItems;
        };
        
        /**
         * Get the selected item index in the lists
         *
         * @returns {element} the selected item
         * @memberof module:ko/ui/listbox~Model
         */
        this.getSelectedItem = function()
        {
            return this.element.selectedItem;
        };
        
        /**
         * Remove all items from the list
         *
         * @memberof module:ko/ui/listbox~Model
         */
        this.removeAllItems = function()
        {
            if ( ! this.element.removeItemAt)
            {
                this.$element.empty();
                return;
            }

            var rows = this.element.getRowCount();
            for ( let i = 0; i < rows; i++ )
            {
                this.element.removeItemAt(0);
            }
        };
        
        /**
         * Get the value/label of the selected item
         *
         * @returns {String} the value or label of the selected item
         * @memberof module:ko/ui/listbox~Model
         */
        this.value = function()
        {
            var item = this.getSelectedItem();
            if ( ! item)
                return "";

            return item.hasAttribute("value") ? item.getAttribute("value") : item.getAttribute("label");
        };

    }).apply(this.Model);

}).apply(Module);
