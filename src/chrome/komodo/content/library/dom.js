/*!
* Based on ki.js - jQuery-like API super-tiny JavaScript library
* https://github.com/dciccale/ki.js
*/
if (typeof module === 'undefined') module = {}; // debugging helper
module.exports = function(parent) {

    /* === MAIN CONSTRUCTION LOGIC === */

    /*
     * queryObject function (internal use)
     * query = selector, dom element or function
     */
    function queryObject(query) {
        if (query && query.nodeType)
            this._elements = [query];
        else if ('' + query === query)
            this._elements = parent.querySelectorAll(query);

        this.length = this._elements.length;
    }

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
            return new queryObject(createFlexElement(query));
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
    var createFlexElement = function(html) {
        var tmp = document.createElement("div");
        tmp.innerHTML = html;
        return tmp.firstChild;
    }

    /**
     * Manipulation helper for inserting DOM content
     *
     * @param   {Object} elems
     * @param   {string|object} insert
     * @param   {boolean} preferPrepend
     *
     * @returns {void} 
     */
    var insertIntoElem = function(elems, insert, preferPrepend)
    {
        var __insert = false
        if (typeof insert == 'string')
            __insert = createFlexElement(insert);

        return elems.each(function() {
            if (insert.koDom)
                var _insert = insert.first()
            else
                var _insert = __insert ? __insert.cloneNode(true) : insert;
                
            if (preferPrepend && this.firstChild)
                this.insertBefore(_insert, this.firstChild);
            else
                this.appendChild(_insert);
        });
    }

    /* === FUNCTION CHAIN === */

    // set query object prototype
    queryObject.prototype = {

        _elements: [],

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
        on: function(event, action) {
            return this.each(function(elem) {
                elem.addEventListener(event, action);
            })
        },

        /*
         * off method
         * event = string event type i.e 'click'
         * action = function
         * return this
         */
        off: function(event, action) {
            return this.each(function(elem) {
                elem.removeEventListener(event, action);
            })
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
        text: function(value) {
            return this.each(function() {
               this.textContent = value;
            });
        },

        /**
         * Set html content of elem
         * @param   {string|object} value String or queryObject
         */
        html: function(value) {
            this.each(function() {
                this.innerHTML = "";
            });
            return this.append(value);
        },

        /**
         * Append content to elem
         * @param   {string|object} value String or queryObject
         */
        append: function(elem) {
            insertIntoElem(this, elem);
            return this;
        },

        /**
         * Prepend content to elem
         * @param   {string|object} value String or queryObject
         */
        prepend: function(elem) {
            insertIntoElem(this, elem, true /* prepend */);
        },

        // for some reason is needed to get an array-like
        // representation instead of an object
        splice: function() { return this._elements.splice.call(arguments); },

        // Use first entry
        first: function() { return this._elements[0] }
    }

    return $;
};
