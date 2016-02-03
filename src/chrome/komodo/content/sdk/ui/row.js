/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

function Row(options) { this.init(options); }

(function()
    {
        var $ = require("ko/dom");
        this.type = "hbox";
        
        this.init = function(element = {}, options = {})
        {
             // The only arg passed in might only be options
            if (!element.koDom)
            {
                options = element;
            }
            
            var columnElem = $.create(this.type, options.attributes || {})
            var $element = $(columnElem.toString());
            // if content has been provided append it to the element
            if(element && element.koDom)
            {
                $element.append(element);
            }
            this.$ = $element; // koDom object
            this.element = this.$.element(); // Actual DOM object
        };
        
        /**
         * Insert column for content
         *
         * @param {koDom} element, content to append to element on creation.
         * @param {object} options, options to be used on element, OPTIONAL
         *
         * @returns {DOM Object} ko/UI SDK object
         */
        this.addColumn = ($ = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$.koDom)
            {
                options = $;
            }
            
            var columnElem;
            // Create it with options or not
            var col = require("ko/ui/col").create(options.attributes = {});
            if($ && $.koDom)
            {
                col.$.append($);
            }
            this.$.append(col.$);
            return col;
        };
    }
).apply(Row.prototype);

/**
 * Create an instance of a row object 
 *
 * @param {koDom} element, content to append to element on creation.
 * @param {object} options, options to be used on element, OPTIONAL
 *
 * @returns {Object} Row,  object which contains the koDom object of a
 * row (a.k.a hbox) element in the element property.
 */
module.exports.create = function create_row (options)
{
    return new Row(options);
}
