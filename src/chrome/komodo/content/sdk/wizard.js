function Wizard(options) { this.init(options); }
(function()
    {
       const $ = require("ko/dom");
   
       this.init = function(options = {})
       {
           var element = $.create("wizard", options.attributes || {});
           this.element = $(element.toString());
       }
   
       /**
        * Append a new wizardpage to the wizard and return it
        *
        * @param {object} options, options for the page
        * @param {object} content, content to be added to the page when created
        *
        * @returns {Page} the page object created.
        */
       this.addPage = function(options = {}, content = {})
       {
           var page = require("ko/wizard/page").create(options);
           page.element.append(content);
           this.element.append(page.element);
           return page;
       };
   }
).apply(Wizard.prototype);


/**
 * Create and return a new wizard DOM object
 *
 * @param {Object} options, an options object which contains an attributes object
 *   options = {attributes : {class : "myclass", width : 100, noautohide: true, width: 500, level: "floating"}}
 *
 * @return {object} Wizard, object which contains the koDom object of a
 * wizard (a.k.a <wizard>) element in the element property.
 */
//NOTE allow to accept a Page DOM object or Page module object
// same for addPage
//  Add similar functionality for other UI-ish SDKs

module.exports.create = function(options)
{
    return new Wizard(options);
}
