/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Page sub module for the wizard SDK module
 */

function Page($element = {}, options = {}) { this.init($element, options); }

(function()
    {
        var $ = require("ko/dom");
        var log = require("ko/logging").getLogger("ko-wizard-page");
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
            this.$elem = $newElem; // koDom object
            this.element = this.$elem.element.bind(this.$elem); // Actual DOM object
        };
        
        /**
         * Insert a row of content to the page
         *
         * @param {koDom} element, content to append to element on creation.
         * @param {object} options, options to be used on element, OPTIONAL
         *
         * @returns {DOM Object} ko/UI SDK object
         */
        this.addRow = function page_addRow($element = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$element.koDom)
            {
                options = $element;
            }
            
            // Create it with options or not
            var element = require("ko/ui/row").create(options.attributes || {});
            
            if($element && $element.koDom)
            {
                element.$elem.append($element);
            }
            else
            {
                log.warn("$element has no koDom property.  Make sure you're psasing in a koDom object.")
            }
            this.$elem.append(element.$elem);
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
        this.addColumn = function page_addColumn($element = {}, options = {})
        {
            // The only arg passed in might only be options
            if (!$element.koDom)
            {
                options = $element;
            }
            
            // Create it with options or not
            var element = require("ko/ui/col").create(options.attributes || {});
            
            if($element && $element.koDom)
            {
                element.$elem.append($element);
            }
            this.$elem.append(element.$elem);
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
module.exports.create = function page_create($element = {}, options = {})
{
    return new Page($element, options);
}