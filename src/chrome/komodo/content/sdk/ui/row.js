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
function Row(options) { this.init(options); }

(function()
    {
        var $ = require("ko/dom");
        
        this.init = function(options = {})
        {
            var element = $.create("hbox", options.attributes || {})
            this.element = $(element.toString());
        };
    }
).apply(Row.prototype);

/**
 * Create an instance of a row object 
 *
 * @returns {Object} Row,  object which contains the koDom object of a
 * row (a.k.a hbox) element in the element property.
 */
module.exports.create = function create_row (options)
{
    return new Row(options);
}
