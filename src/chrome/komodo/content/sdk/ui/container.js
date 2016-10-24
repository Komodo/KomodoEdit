/**
 * @copyright (c) 2016 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 */

var parent = require("./element");
var Module = Object.assign({}, parent);
module.exports = Module;

(function() {
    
    this.Model = Object.assign({}, this.Model);
    
    (function() {
        
        this.name = "box";
        
        this.init = this.initWithElement;
        
        /**
         * Insert a row of content to the page
         *
         * @param {koDom} appendElement     content to append to element on creation.
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {object} ko/UI SDK object
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
         * @param {koDom} appendElement     content to append to element on creation.
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {object} ko/UI SDK object
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
         * @param {koDom} appendElement     content to append to groupbox on creation.
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {object} ko/UI SDK object
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
         * @param {koDom} appendElement     content to append to element on creation.
         * @param {object} options          options to be used on element, OPTIONAL
         *
         * @returns {object} ko/UI SDK object
         */
        this.add = function (elements)
        {
            return this.addElement(elements);
        };
        
    }).apply(this.Model);
    
}).apply(Module);
