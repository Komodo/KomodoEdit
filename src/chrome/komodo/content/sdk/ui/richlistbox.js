/**
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 */

var $ = require("ko/dom");
var parent = require("./listbox");
var Module = Object.assign({}, parent);
var log = require("ko/logging").getLogger("sdk/ui/richlistbox");
//log.setLevel(require("ko/logging").LOG_DEBUG);
module.exports = Module;

// Main module (module.exports)
(function() {

    this.Model = Object.assign({}, this.Model);

    this.listhead = null;
    this.listcols = null;

    (function() {

        this.name = "richlistbox";

        this.init = function(richlistitems = [], options = {})
        {
            if ( ! Array.isArray(richlistitems) && typeof richlistitems == "object")
            {
                options = richlistitems;
                richlistitems = null;
            }

            if ("richlistitems" in options)
            {
                richlistitems = options.richlistitems;
            }

            this.options = options;
            this.$element = $($.create(this.name, options.attributes || {}).toString());
            this.element = this.$element.element();

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

        this.addListItems = function (entries)
        {
            for (let entry of entries) {
                this.addListItem(entry);
            }
        };

          /**
         * Add an item to the container
         *
         * @argument {ko/ui/obj | ko/dom/obj | DOM | Object} item item to be added
         * to the container.
         *
         * Object refers to an Options object used through this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *
         *  {
         *      attributes:
         *      {
         *          label:"itemLabel"
         *      }
         *  }
         */
        this.addListItem = function (item)
        {
            var element;
            if ("isSdkElement" in item)
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

        this.getSelectedItems = function()
        {
            return this.element.selectedItems;
        };

        this.getSelectedItem = function()
        {
            return this.element.selectedItem;
        };

        this.removeAllItems = function()
        {
            this.$element.empty();
        };

        this.moveSelectionUp = function()
        {
            this.element.moveByOffset(-1, true, false);
        };

        this.moveSelectionDown = function()
        {
            this.element.moveByOffset(1, true, false);
        };

    }).apply(this.Model);

}).apply(Module);

