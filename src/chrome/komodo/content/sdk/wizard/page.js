/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Page sub module for the wizard SDK module
 */

function Page(options) { this.init(options); }

(function()
    {
        var $ = require("ko/dom");
        this.type = "wizardpage";
        // should this take content too?
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
         * Insert a row of content to the page
         *
         * @param {koDom} element, content to append to element on creation.
         * @param {object} options, options to be used on element, OPTIONAL
         *
         * @returns {DOM Object} ko/UI SDK object
         */
        this.addRow = function($ = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$.koDom)
            {
                options = $;
            }
            
            var columnElem;
            // Create it with options or not
            var row = require("ko/ui/row").create(options.attributes = {});
            
            if($ && $.koDom)
            {
                row.$.append($);
            }
            this.$.append(row.$);
            return row;
        };
    }
).apply(Page.prototype);

/**
 * Create and return a new wizardpage DOM object
 *
 * @param {Object} options, an options object which contains an attributes object
 *   options = {attributes : {class : "myclass", width : 100, noautohide: true, width: 500, level: "floating"}}
 *
 * @return {object} wizardpage, object which contains the koDom object of a
 * wizardpage (a.k.a <wizardpage ...>) element in the element property.
 */
module.exports.create = function create_page (options)
{
    return new Page(options);
}