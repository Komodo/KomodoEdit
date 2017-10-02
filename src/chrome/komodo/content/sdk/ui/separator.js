var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui separator element
 * 
 * This module inherits methods and properties from the module it extends.
 * Quickly generate a separator for you UI.
 * 
 * 
 * @module ko/ui/separator
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var separator = require("ko/ui/separator").create();
 * var label1 = require("ko/ui/label").create("Label1");
 * var label2 = require("ko/ui/label").create("label2");
 * var panel = require("ko/ui/panel").create();
 * panel.addColumn([separator,label1,label2]);
 * panel.open();
 */

(function() {

    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the row UI element, this is what {@link model:ko/ui/separator.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL [separator]{@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/separator}
     */

    (function() {

        this.name = "separator";
        
        /**
         * Create a new separator UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/separator~Model}
         */

    }).apply(this.Model);

}).apply(Module);
