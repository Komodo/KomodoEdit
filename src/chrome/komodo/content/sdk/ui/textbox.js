/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author NathanR, CareyH
 * @overview Row sub module for the ko/ui SDK
 *
 */

/**
 * "declaration" of the Row class.  Uses the init() function as a constructor
 */
function Textbox($element = {}, options = {}) { this.init($element, options); }

(function()
    {
        var $ = require("ko/dom");
        this.type = "textbox";
        
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
    }
).apply(Textbox.prototype);

/**
 * Create an instance of a Textbox object 
 *
 * @returns {Object} Textbox,  object which contains the koDom object
 */
module.exports.create = function textbox_create($element = {}, options = {})
{
    return new Textbox($element, options);
}
