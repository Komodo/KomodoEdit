var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;


/**
 * ko/ui container element
 * 
 * This module inherits methods and properties from the module it extends.
 * @module ko/ui/container
 * @extends module:ko/ui/element~Model
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @example
 * var container = require("ko/ui/container").create();
 * container.addRow(require("ko/ui/button").create({ label: "Click me!", command: () => console.log("Hello!") }));
 */
(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    /**
     * The model for the container UI element, this is what {@link model:ko/ui/container.create} returns
     * 
     * @class Model
     * @extends module:ko/ui/element~Model
     * @property {string}       name        The node name of the element
     * @property {Element}      element     A XUL container, see {@link https://developer.mozilla.org/en-US/docs/Mozilla/Tech/XUL/hbox}
     */
    (function() {
        
        this.name = "box";
        
         /**
         * Create a new container UI element
         * 
         * @name create
         * @method
         * @param  {object}         [options]   An object containing attributes and options
         * 
         * @returns {module:ko/ui/container~Model}
         */
        
        this.init = this.initWithElement;
        
        /**
         * Insert a row of content to the page
         *
         * @param  {(Element|array|object|string)} appendElement - Element(s) to be appended. This can be a DOM element, ko/dom element or 
         *                                                      even just the name of an element. See {@link module:ko/ui/element~Model.addElement} 
         *                                                      for more information.
         *                                                      If this is a simple object then it will be used as the options param 
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {module:ko/ui/row~Model} 
         *
         * @memberof module:ko/ui/container~Model
         */
        this.addRow = function(appendElement, options = {})
        {
            var row = require("./row").create(appendElement, options);
            this.$element.append(row.element);
            
            return row;
        };
        
         /**
         * Insert a column of content to the page
         *
         * @param  {(Element|array|object|string)} appendElement - Element(s) to be appended. This can be a DOM element, ko/dom element or 
         *                                                      even just the name of an element. See {@link module:ko/ui/element~Model.addElement} 
         *                                                      for more information.
         *                                                      If this is a simple object then it will be used as the options param 
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {module:ko/ui/column~Model} 
         * @memberof module:ko/ui/container~Model
         */
        this.addColumn = function (appendElement, options = {})
        {
            var column = require("./column").create(appendElement, options);
            this.$element.append(column.element);
            
            return column;
        };
        
        /**
         * Insert a groupbox into the page
         *
         * @param  {(Element|array|object|string)} appendElement - Element(s) to be appended. This can be a DOM element, ko/dom element or 
         *                                                      even just the name of an element. See {@link module:ko/ui/element~Model.addElement} 
         *                                                      for more information.
         *                                                      If this is a simple object then it will be used as the options param 
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {module:ko/ui/groupbox~Model}
         * @memberof module:ko/ui/container~Model
         */
        this.addGroupbox = function (appendElement, options = {})
        {
            var groupbox = require("./groupbox").create(appendElement, options);
            this.$element.append(groupbox.element);
            
            return groupbox;
        };
        
         /**
         * Insert an element to the page
         *
         * @param  {(Element|array|object|string)} appendElement - Element(s) to be appended. This can be a DOM element, ko/dom element or 
         *                                                      even just the name of an element. See {@link module:ko/dom~QueryObject.hide} 
         *                                                      for more information.
         *                                                      If this is a simple object then it will be used as the options param 
         * @param {object} options - options to be used on element, OPTIONAL
         *
         * @memberof module:ko/ui/container~Model
         */
        this.add = function (elements)
        {
            return this.addElement(elements);
        };
        
    }).apply(this.Model);
    
}).apply(Module);
