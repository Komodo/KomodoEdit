var parent = require("./container");
var Module = Object.assign({}, parent);
module.exports = Module;

/**
 * ko/ui groupbox element
 * 
 * This module inherits methods and properties from the module it extends.
 * 
 * @module ko/ui/groupbox
 * @extends module:ko/ui/container~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var groupbox = require("ko/ui/groupbox").create();
 * groupbox.addRow(require("ko/ui/button").create({ label: "Click me!", command: () => console.log("Hello!") }))
 */
(function() {

    this.Model = Object.assign({}, this.Model);
    /**
     * The model for the groupbox UI element, this is what {@link model:ko/ui/groupbox.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/container~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL groupbox, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/caption}
     */
    (function() {

        this.name = "groupbox";
        
        /**
         * Create a new conatiner UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/groupbox~Model}
         */
        this.init = function (appendElement = null, options = {})
        {
            if (appendElement && "caption" in appendElement)
            {
                options = appendElement;
                appendElement = null;
            }

            this.initWithElement(appendElement, options);

            if ("caption" in options)
            {
                this.$element.prepend(require("./caption").create(options.caption).element);
            }
        };

    }).apply(this.Model);

}).apply(Module);
