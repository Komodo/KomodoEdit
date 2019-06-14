var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui listitem element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/listitem
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var listitem = require("ko/ui/listitem").create("An Item");
 * var listbox = require("ko/ui/listbox").create();
 * listbox.addListItem(listitem);
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/listitem.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [listcell]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/listcell}
     */

    (function() {

        this.name = "listitem";
        
        /**
         * Create a new listitem UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/listitem~Model}
         */

        this.init = function(label, options = {})
        {
            if (label && typeof label == "object")
            {
                options = label;
                label = null;
            }

            if (options.label)
            {
                label = options.label;
            }

            this.initWithLabel(label, options);

            if ( ! this.attributes.value && label)
            {
                this.$element.attr("value", label);
            }
        };

        /**
         * Add a list cell to the container
         *
         * @param {mixed} item  item to be added to the container.  Can be String (label), ko/ui/<elem>, ko/dom element, DOM element, option object.
         *                      option object refers to an Options object used throughout this SDK. The options
         *                      should contain an attributes property to assign a label at the very
         *                      least: { label: "itemLabel" }
         * @example
         * Object refers to an Options object used through this SDK. The options
         * should contain an attributes property to assign a label at the very
         * least:
         *
         *  listcell =
         *  {
         *      attributes:
         *      {
         *          label:"itemLable"
         *      }
         *  }
         *  @memberof module:ko/ui/listitem~Model
         */ 
        this.addListCell = function(listcell)
        {
            return this.addElement(listcell, "listcell");
        };

    }).apply(this.Model);

}).apply(Module);
