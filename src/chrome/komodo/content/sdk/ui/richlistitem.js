var parent = require("./listitem");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui richlistitem element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/richlistitem
 * @extends module:ko/ui/listitem~Model
 * @copyright (c) ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR
 * @example
 * var richlistitem = require("ko/ui/richlistitem").create("just purple");
 * var richlistbox = require("ko/ui/richlistbox").create();
 * richlistbox.addListItem(richlistitem);
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/richlistitem.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/listitem~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [richlistitem]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/richlistitem}
     */

    (function() {

        this.name = "richlistitem";
        
        /**
         * Create a new richlistitem UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/richlistitem~Model}
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

            this.defaultInit(options);

            if (label)
            {
                var labelElem = require("ko/ui/label").create(label);
                this.addElement(labelElem);
            }

            if ( ! this.attributes.value && label)
            {
                this.$element.attr("value", label);
            }
        };

    }).apply(this.Model);

}).apply(Module);
