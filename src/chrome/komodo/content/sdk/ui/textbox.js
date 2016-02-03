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
function Textbox(options) { this.init(options); }

(function()
    {
        var $ = require("ko/dom");
        this.type = "textbox.js";
        
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
    }
).apply(Textbox.prototype);

/**
 * Create an instance of a row object 
 *
 * @returns {Object} Textbox,  object which contains the koDom object of a
 * row (a.k.a hbox) element in the element property.
 */
module.exports.create = function create_row (options)
{
    return new Textbox(options);
}
