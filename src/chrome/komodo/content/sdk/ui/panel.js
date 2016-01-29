/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author CareyH
 * @overview Page sub module for the wizard SDK module
 *
 */

/**
 * "declaration" of the Row class.  Uses the init() function as a constructor
 */
function Panel(options) { this.init(options) };
(function()
    {
        var $ = require("ko/dom");
        
        this.init = function(options = {})
        {
            var element = $.create("panel", options.attributes || {})
            this.element = $(element.toString());
        };
    }
).apply(Panel.prototype);

/**
 * Create an instance of a row object 
 *
 * @returns {Object} Row,  object which contains the koDom object of a
 * row (a.k.a hbox) element in the element property.
 */
module.exports.create = function create_panel (options)
{
    return new Panel(options);
};