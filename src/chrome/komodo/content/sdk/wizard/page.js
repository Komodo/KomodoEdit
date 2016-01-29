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
        
        // should this take content too?
        this.init = function(options = {})
        {
            var element = $.create("wizardpage", options.attributes || {})
            this.element = $(element.toString());
        };
        
        /**
         * Insert a row of content to the page
         *
         * @param {object} options, the attributes to add to the row
         * @param {object} content, a DOM object to be insert into the row 
         */
        this.addRow = function(options = {}, content = {})
        {
            var row = require("ko/ui/row").create(options);
            row.element.appendChild(content);
            this.element.appendChild(row.element())
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