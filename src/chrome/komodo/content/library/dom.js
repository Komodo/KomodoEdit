/*!
* Based on ki.js - jQuery-like API super-tiny JavaScript library
* https://github.com/dciccale/ki.js
*/
if (typeof module === 'undefined') module = {}; // debugging helper
(function(parent) {

    /* === MAIN CONSTRUCTION LOGIC === */

    /*
     * $ main function
     * a = css selector, dom object, or function
     * http://www.dustindiaz.com/smallest-domready-ever
     * returns instance or executes function on ready
     */
    var $ = function(query) {
        if (/^f/.test(typeof query))
        {
            if (/c/.test(parent.readyState))
                return query();
            else
                return $(parent).on('DOMContentLoaded', query);
        }
        else if (/^</.test(query))
        {
            return new queryObject($.createElement(query));
        }
        else
            return new queryObject(query)
    }

    /* === HELPER FUNCTIONS === */

    /**
     * Create element from complex string input
     *
     * @param   {String} html
     *
     * @returns {Node}
     */
    $.createElement = function(html)
    {
        var tmp = document.createElement("div");
        tmp.innerHTML = html;
        return tmp.firstChild;
    }

    /**
     * Manipulation helper for inserting DOM content
     *
     * @param   {Object} elems
     * @param   {string|object} insert
     * @param   {object} opts {where: prepend|after|before}
     *
     * @returns {void} 
     */
    var insertIntoElem = function(elems, insert, opts)
    {
        opts = opts || {};

        var __insert = false
        if (typeof insert == 'string')
            __insert = $.createElement(insert);

        return elems.each(function()
        {
            if (insert.koDom)
                var _insert = insert.first()
            else
                var _insert = __insert ? __insert.cloneNode(true) : insert;
                
            if (opts.where == "prepend" && this.firstChild)
                this.insertBefore(_insert, this.firstChild);
            else if (opts.where == "after")
            {
                if (this.nextSibling)
                    this.parentNode.insertBefore(_insert, this.nextSibling);
                else
                    this.parentNode.appendChild(_insert);
            }
            else if (opts.where == "before")
                this.parentNode.insertBefore(_insert, this);
            else
                this.appendChild(_insert);
        });
    }

    /* === FUNCTION CHAIN === */

    /*
     * queryObject function (internal use)
     * query = selector, dom element or function
     */
    function queryObject(query, customParent)
    {
        this._elements = [];
        
        // Use push.apply to force array type
        if (query && query.nodeType)
            this._elements.push.apply(this._elements, [query]);
        else if ('' + query === query)
            this._elements.push.apply(this._elements,  (customParent || parent).querySelectorAll(query));
    }

    // set query object prototype
    queryObject.prototype = {

        // default length
        length: 0,

        // Identify as special DOM element
        koDom: true,

        /*
         * on method
         * event = string event type i.e 'click'
         * action = function
         * return this
         */
        on: function(event, action)
        {
            return this.each(function()
            {
                this.addEventListener(event, action);
            });
        },

        /*
         * off method
         * event = string event type i.e 'click'
         * action = function
         * return this
         */
        off: function(event, action)
        {
            return this.each(function()
            {
                this.removeEventListener(event, action);
            });
        },

        /*
         * each method
         * use native forEach to iterate collection
         * action = the function to call on each iteration
         */
        each: function(action) {
            for (var k in this._elements)
            {
                if ( ! this._elements.hasOwnProperty(k)) continue;
                if (action.call(this._elements[k], k) === false) break;
            }
            return this;
        },

        /**
         * Set text content of elem
         * @param   {string} value
         */
        text: function(value)
        {
            if (value === undefined)
                return this.first().textContent;

            return this.each(function()
            {
               this.textContent = value;
            });
        },

        /**
         * Set html content of elem
         * @param   {string|object} value String or queryObject
         */
        html: function(value)
        {
            if (value === undefined)
                return this.first().innerHTML;

            this.each(function()
            {
                this.innerHTML = "";
            });
            return this.append(value);
        },

        /**
         * Get outer html of elem
         */
        outerHtml: function()
        {
            return this.first().outerHTML;
        },

        /**
         * Empty the contents of an element
         */
        empty: function()
        {
            return this.text("");
        },

        /**
         * Append content to elem
         * @param   {string|object} value String or queryObject
         */
        append: function(elem)
        {
            insertIntoElem(this, elem);
            return this;
        },

        /**
         * Prepend content to elem
         * @param   {string|object} value String or queryObject
         */
        prepend: function(elem)
        {
            insertIntoElem(this, elem, {where: "prepend"});
        },

        /**
         * Insert content after element
         * @param   {string|object} value String or queryObject
         */
        after: function(elem)
        {
            insertIntoElem(this, elem, {where: "after"});
            return this;
        },

        /**
         * Insert content before element
         * @param   {string|object} value String or queryObject
         */
        before: function(elem)
        {
            insertIntoElem(this, elem, {where: "before"});
            return this;
        },

        /**
         * Set / get value
         * @param   {String|Void} value
         */
        value: function(value)
        {
            // Todo: support different value types
            var valueKey = 'value';

            if (value === undefined)
                return this.first()[valueKey];

            return this.each(function()
            {
                this[valueKey] = value;
            });
        },

        /**
         * Delete element
         */
        delete: function()
        {
            return this.each(function()
            {
                this.parentNode.removeChild(this);
            });
        },

        /**
         * Makes element visible
         */
        show: function()
        {
            return this.each(function()
            {
                this.style.visibility = "visible";
            });
        },

        /**
         * Makes element invisible
         */
        hide: function()
        {
            return this.each(function()
            {
                this.style.visibility = "collapse";
            });
        },

        /**
         * Check if element is visible
         */
        visible: function()
        {
            return ["","visible","initial", "inherit"].indexOf(this.element().style.visibility) != -1;
        },

        addClass: function(className)
        {
            return this.each(function()
            {
                this.classList.add(className);
            });
        },

        removeClass: function(className)
        {
            return this.each(function()
            {
                this.classList.remove(className);
            });
        },

        css: function(key, value)
        {
            var rules = {};
            if (value)
                rules[key] = value;
            else
                rules = key;

            return this.each(function()
            {
                for (let k in rules)
                {
                    this.style[k] = rules[k];
                }
            });
        },

        /**
         * Focus on element
         */
        focus: function()
        {
            this.first().focus();
            return this;
        },

        /**
         * Find within current element
         */
        find: function(query)
        {
            return new queryObject(query, this.element());
        },

        // for some reason is needed to get an array-like
        // representation instead of an object
        splice: function() { return this._elements.splice.call(arguments); },

        // Use first entry
        first: function() { return this.element(0); },

        last: function() { return this.element(-1); },

        element:  function(k) { return this._elements.slice(k || 0)[0]; }
    }

    module.exports = $;
    
})(window.document);
