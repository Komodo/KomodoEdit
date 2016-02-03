/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Page sub module for the wizard SDK module
 */

function Page($element = {}, options = {}) { this.init($element = {}, options = {}); }

(function()
    {
        var $ = require("ko/dom");
        this.type = "wizardpage";
        // should this take content too?
        this.init = function($element = {}, options = {})
        {
             // The only arg passed in might only be options
            if (!$element.koDom)
            {
                options = $element;
            }
            
            var newElem = $.create(this.type, options.attributes || {})
            var $newElem = $(newElem.toString());
            // if content has been provided append it to the element
            if($element && $element.koDom)
            {
                $newElem.append($element);
            }
            this.$ = $newElem; // koDom object
            this.element = this.$.element; // Actual DOM object
        };
        
        /**
         * Insert a row of content to the page
         *
         * @param {koDom} element, content to append to element on creation.
         * @param {object} options, options to be used on element, OPTIONAL
         *
         * @returns {DOM Object} ko/UI SDK object
         */
        this.addRow = function($element = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$element.koDom)
            {
                options = $element;
            }
            
            // Create it with options or not
            var element = require("ko/ui/row").create(options.attributes = {});
            
            if($element && $element.koDom)
            {
                element.$.append($element);
            }
            this.$.append(element.$);
            return element;
        };
        
         /**
         * Insert a column of content to the page
         *
         * @param {koDom} element, content to append to element on creation.
         * @param {object} options, options to be used on element, OPTIONAL
         *
         * @returns {DOM Object} ko/UI SDK object
         */
        this.addColumn = function($element = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$element.koDom)
            {
                options = $element;
            }
            
            // Create it with options or not
            var element = require("ko/ui/col").create(options.attributes = {});
            
            if($element && $element.koDom)
            {
                element.$.append($element);
            }
            this.$.append(element.$);
            return element;
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
module.exports.create = function create_page ($element = {}, options = {})
{
    return new Page($element = {}, options = {});
}