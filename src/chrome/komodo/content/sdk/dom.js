/**
 * @copyright (c) 2017 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 */

if (typeof module === 'undefined') module = {}; // debugging helper

/**
 * @module ko/dom
 * @description this module is meant to be "mostly" backwards compatible with jquery
 */

(function() {

    const log   = require("ko/logging").getLogger("ko-dom");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    if ( ! window)
    {
        var window = require("ko/windows").getMain();
        var document = window.document;
    }

    /* === MAIN CONSTRUCTION LOGIC === */

     /**
      * @class Constructor
      *
      * @description These methods live on the exported function, you can access them like so:
      *
      * ```require("ko/dom").methodName(..)```
      */

     /**
      * @constructor module:ko/dom
      * 
      * @param {string} query       CSS query to use as the selector
      * @param {element} parent     The parent element (can be the window)
      * @example
      * var $ = require("ko/dom");
      * $(".foo").text("bar");
      *
      * @returns {module:ko/dom~QueryObject}
      */
    var $ = function(query, parent)
    {
        if (query instanceof window.ChromeWindow && parent) // Allow for the parent to be bound
        {
            var _query = parent;
            parent = query;
            query = _query;
        }

        parent = parent || window.document;

        if (("document" in parent) && parent.constructor.toString().indexOf("Window()") !== -1)
        {
            parent = parent.document;
        }

        if ((typeof query) == "object" && ("koDom" in query))
        {
            return query;
        }
        else if (/^f/.test(typeof query))
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
            return new queryObject(query, parent);
    };

    /**
     * Get a ko/dom instance for the given window
     * 
     * @name window
     * @method
     * @memberof module:ko/dom~Constructor
     * 
     * @param {Window} w    Window reference
     * 
     * @example
     * var $ = require("ko/dom").window(myWindow);
     * $(".foo").text("bar");
     * 
     * @returns {module:ko/dom} Returns a ko/dom instance for the given window
     */
    $.window = (w) =>
    {
        // Return bound version of $
        var bound = $.bind(null, w);
        for (let prop in $)
        {
            if ( ! ($.hasOwnProperty(prop)))
                continue;
            bound[prop] = $[prop];
        }
        return bound;
    };

    /* === HELPER FUNCTIONS === */

    /**
     * Create element from complex string input
     * 
     * @name createElement
     * @method
     * @memberof module:ko/dom~Constructor
     *
     * @param   {String} html                   HTML string, must validate properly (no syntax errors), can also be just the nodename
     * @param   {Bool|Object} allowMultiple     boolean or object, if object then this is taken as an object of attributes to assign to the element
     *
     * @returns {Node}
     */
    $.createElement = function(html, allowMultiple = false)
    {
        try
        {
            if (typeof html == "string" && typeof allowMultiple == "object")
            {
                var attributes = allowMultiple;
                var node = document.createElement(html);

                for (let k in attributes)
                {
                    if ( ! attributes.hasOwnProperty(k))
                    {
                        continue;
                    }

                    node.setAttribute(k, attributes[k]);
                }

                return node;
            }
            else if (typeof html == "string" && html.match(/^\w+$/))
            {
                return document.createElement(html);
            }

            var parsed = (/^<(\w+)\s*\/?>(?:<\/\1>|)$/).exec(html);
            if (parsed) {
                return document.createElement(parsed[1]);
            }

            var tmp = document.createElement("div");
            tmp.innerHTML = html;
            if (allowMultiple)
            {
                var x  = [].slice.call(tmp.childNodes);
                return [].slice.call(tmp.childNodes);
            }
            else
                return tmp.firstChild;
        }
        catch (e)
        {
            log.exception(e, "Failed injecting HTML: " + html);
            return false;
        }
    }

    /**
     * Quickly create DOM structure 
     * Based on: {@link http://gist.github.com/278016}
     * 
     * Example usage:
     * 
     * ```
     * 	$.create('A href=#' , {class: "foo"}, $.create('IMG src="http://bit.ly/WinAylott"')
     *    ('BR')
	 *    ('' ,"View larger image") )
     * ```
     * 
     * @name create
     * @method
     * @memberof module:ko/dom~Constructor
     * 
     * @param {string} selector                     The element definition
     * @param {object|string|undefined} attributes  Attributes to add to the element, if content is undefined and this is a string then the value of attributes will be used as the content param
     * @param {string|undefined} content            Content to append
     * 
     * @returns {module:ko/dom~Constructor.create} Returns instance of this function, so you can chain calls
     * 
     * @author Thomas Aylott (original author)
     * @copyright 2010 Thomas Aylott
     * @license MIT
     **/
    $.create = function (selector, attributes, content, output = '')
    {
        if (content === undefined && ((typeof attributes == "function") || typeof attributes == 'string'))
        {
            content = attributes;
            attributes = undefined;
        }

        if (typeof content == "function")
        {
            content = content.toString();
        }

        if (attributes)
        {
            for (let key in attributes)
            {
                if ( ! attributes.hasOwnProperty(key)) continue;
                let value = attributes[key];
                if (typeof value == "string") value = $.escape(value)
                selector += " " + key + "='"+value+"'";
            }
        }

        output += '<' + selector + '>';
        output += ''+ ( content||'' );
        output += '</' + selector .split (' ')[0] + '>';

        var BS = function(selector, attributes, content) {
            return $.create(selector, attributes, content, output);
        };

        BS.toString = function () { return output; }

        BS.finalize = function()
        {
            return new queryObject($.createElement(output, true /* Allow Multiple */));
        }

        return BS;
    };

    /**
     * Escape given string (html entities encode)
     * 
     * @name escape
     * @method
     * @memberof module:ko/dom~Constructor
     *
     * @param   {String} str    The input string
     *
     * @returns {String}
     */
    $.escape = function(str)
    {
        str = str.replace(/[\u00A0-\u9999<>\&]/gim, function(i) {
           return '&#'+i.charCodeAt(0)+';';
        });
        str = str.replace(/'/g,'&#39;');
        str = str.replace(/"/g,'&quot;');
        return str;
    }

    /**
     * Manipulation helper for inserting DOM content
     *
     * @param   {Object} elems          Element
     * @param   {string|object} insert  HTML string or object to be inserted
     * @param   {object} opts           {where: prepend|after|before}
     *
     * @returns {void}
     */
    var insertIntoElem = function(elems, insert, opts)
    {
        opts = opts || {};

        if (typeof insert == "object" && insert.koDom)
            insert.each(function() { insertIntoElem(elems, this, opts); });

        var __insert = false
        if (typeof insert == 'string')
            __insert = $.createElement(insert);

        if ( ! elems.koDom)
            elems = $(elems);

        return elems.each(function()
        {
            if (typeof insert == "object" && insert.koDom)
                var _insert = insert.element()
            else
                var _insert = __insert ? __insert.cloneNode(true) : insert;

            if (("where" in opts) && opts.where == "prepend" && this.firstChild)
                this.insertBefore(_insert, this.firstChild);
            else if (("where" in opts) && opts.where == "after")
            {
                if (this.nextSibling)
                    this.parentNode.insertBefore(_insert, this.nextSibling);
                else
                    this.parentNode.appendChild(_insert);
            }
            else if (("where" in opts) && opts.where == "before")
                this.parentNode.insertBefore(_insert, this);
            else
                this.appendChild(_insert);
        });
    }

    /* === FUNCTION CHAIN === */

    /**
     * @class QueryObject
     */
    function queryObject(query, customParent)
    {
        var parent = window.document;

        this._elements = [];

        if (query && typeof query == "object" && ! (query instanceof window.ChromeWindow) && query.length)
            query = Array.prototype.slice.call(query);

        // Use push.apply to force array type
        if(Object.prototype.toString.call(query) === '[object Array]')
            this._elements = query.slice(0);
        else if (query && query.nodeType)
            this._elements.push.apply(this._elements, [query]);
        else if ('' + query === query)
        {
            try
            {
                this._elements.push.apply(this._elements,  (customParent || parent).querySelectorAll(query));
            }
            catch (e)
            {
                log.exception(e, `Invalid selector: ${query}`);
            }
        }
        else if ((query != null && query === query.window) ||
                 (query != null && query.window && query == query.window.document))
            this._elements.push(query);

        this.length = this._elements.length;
    }


    // set query object prototype
    queryObject.prototype = {

        // default length
        length: 0,

        // Identify as special DOM element
        koDom: true,

        /**
         * Add event handler
         * 
         * @memberof module:ko/dom~QueryObject
         * @param {Event} event         String event type i.e 'click'
         * @param {Function} action     Function
         *
         * @returns {this}
         */
        on: function(event, action)
        {
            this.off(event, action); // Prevent duplicate event listeners

            return this.each(function()
            {
                if ( ! ("__koListeners" in this))
                    this.__koListeners = {};
                if ( ! (event in this.__koListeners))
                    this.__koListeners[event] = [];
                this.__koListeners[event].push(action);

                this.addEventListener(event, action);
            });
        },

        /**
         * Add an event listener which only receives a callback once
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param {Event} event         String event type i.e 'click'
         * @param {Function} action     Callback function
         *
         * @returns {this}
         */
        once: function(event, action)
        {
            var elems = this;

            var listener = () =>
            {
                try
                {
                    action.apply(this, arguments);
                }
                catch (e)
                {
                    log.exception(e, "once callback failed");
                }

                this.off(event, listener);
            };

            this.on(event, listener);
        },

        /**
         * Remove event listener
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param {Event} event         String event type i.e 'click'
         * @param {Function} action     Callback function
         *
         * @returns this
         */
        off: function(event, action)
        {
            return this.each(function()
            {
                if (("__koListeners" in this) && (event in this.__koListeners))
                {
                    this.__koListeners[event].filter(function(value) {
                        return value != action;
                    });
                }

                this.removeEventListener(event, action);
            });
        },

        /**
         * Trigger an event
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        trigger: function(type, params)
        {
            var evt = new window.CustomEvent(type, {
                bubbles: true,
                cancelable: true,
                detail: params
            });

            return this.each(function()
            {
                this.dispatchEvent(evt);
            });
        },

        /**
         * Iterate over matched elements
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param {Function} action    The function to call on each iteration
         *
         * @returns this
         */
        each: function(action)
        {
            for (var k in this._elements)
            {
                if ( ! this._elements.hasOwnProperty(k)) continue;
                if (action.call(this._elements[k], k) === false) break;
            }
            return this;
        },

        /**
         * Reverse the element array
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        reverse: function()
        {
            this._elements.reverse();
            return this;
        },

        /**
         * Set text content of elem
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {string} value      The value
         *
         * @returns this
         */
        text: function(value)
        {
            if (value === undefined)
                return this.element().textContent;

            return this.each(function()
            {
               this.textContent = value;
            });
        },

        /**
         * Set html content of elem
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {string|object} value String or queryObject
         *
         * @returns this
         */
        html: function(value)
        {
            if (value === undefined)
                return this.element().innerHTML;

            this.each(function()
            {
                this.innerHTML = value ? value : "";
            });

            return this;
        },

        /**
         * Get outer html of elem
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        outerHtml: function()
        {
            return this.element().outerHTML;
        },

        /**
         * Empty the contents of an element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        empty: function()
        {
            return this.text("");
        },

        /**
         * Append content to elem
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {element} elem
         *
         * @returns this
         */
        append: function(elem)
        {
            insertIntoElem(this, elem);
            return this;
        },

        /**
         * Append elem to another element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {element} elem
         *
         * @returns this
         */
        appendTo: function(elem)
        {
            insertIntoElem(elem, this);
            return this;
        },

        /**
         * Prepend content to elem
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {string|object} value String or queryObject
         *
         * @returns this
         */
        prepend: function(elem)
        {
            insertIntoElem(this, elem, {where: "prepend"});
            return this;
        },

        /**
         * Insert content after element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {string|object} value String or queryObject
         *
         * @returns this
         */
        after: function(elem)
        {
            insertIntoElem(this, elem, {where: "after"});
            return this;
        },

        /**
         * Insert content before element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {string|object} value String or queryObject
         *
         * @returns this
         */
        before: function(elem)
        {
            insertIntoElem(this, elem, {where: "before"});
            return this;
        },

        /**
         * Get the previous sibling for the first element in the selection
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {queryObject}
         */
        prev: function()
        {
            var elem = this.element();
            return new queryObject(elem ? elem.previousSibling : null);
        },

        /**
         * Get the next sibling for the first element in the selection
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {queryObject}
         */
        next: function()
        {
            var elem = this.element();
            return new queryObject(elem ? this.element().nextSibling : null);
        },

        /**
         * Replace matched element(s) with ..
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {Element} elem  The element
         *
         * @returns {Element} returns replaced element
         */
        replaceWith: function(elem)
        {
            if ("koDom" in elem) elem = elem.element();
            return this.element().parentNode.replaceChild(elem, this.element());
        },

        /**
         * Clone matched element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {Element} matched element
         */
        clone: function(deep = true, events = true)
        {
            var cloned = [];

            this.each(function() {
                var el = this;
                var result = $(el.cloneNode(deep));

                if ("__koListeners" in el && events)
                {
                    for (let event in el.__koListeners)
                    {
                        if ( ! el.__koListeners.hasOwnProperty(event)) continue;
                        el.__koListeners[event].forEach(function(action) {
                            result.on(event, action);
                        });
                    }
                }

                cloned.push(result.element());
            });

            return new queryObject(cloned);
        },

        /**
         * Set / get value
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {String|Void} value  The value
         *
         * @returns this
         */
        value: function(value)
        {
            // Todo: support different value types
            var valueKey = 'value';

            // Using property
            if (valueKey in this.element())
            {
                if (value === undefined)
                    return this.element()[valueKey];

                return this.each(function()
                {
                    this[valueKey] = value;
                });
            }
            // Using attribute
            else
            {
                if (value === undefined)
                    return this.attr(valueKey);

                return this.attr(valueKey, value);
            }
        },

        /**
         * Retrieve parent node
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {Element}   Parent node
         */
        parent: function()
        {
            return $(this.element().parentNode);
        },

        /**
         * Delete matched elements
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        delete: function()
        {
            return this.each(function()
            {
                this.parentNode.removeChild(this);
            });
        },

        /**
         * Makes element visible by setting the visibility attribute
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        show: function()
        {
            return this.each(function()
            {
                this.style.visibility = "visible";
            });
        },

        /**
         * Makes element invisible by setting the visibility attribute
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        hide: function()
        {
            return this.each(function()
            {
                this.style.visibility = "collapse";
            });
        },

        fadeIn: function(callback)
        {
            this.each(function()
            {
                this.style.opacity = 0;
                this.style.visibility = "visible";
            });

            this.animate( { opacity: 1 },
                {
                    start: {opacity: 0},
                    duration: 200
                },
                callback
            );
        },

        fadeOut: function(callback)
        {
            this.each(function()
            {
                this.style.opacity = 1;
                this.style.visibility = "visible";
            });

            this.animate( { opacity: 0 },
                {
                    start: {opacity: 1},
                    duration: 200
                },
                function()
                {
                    this.hide();
                    if (callback) callback();
                }.bind(this)
            );
        },

        /**
         * Check if element is visible
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {Boolean}
         */
        visible: function()
        {
            var el = this.element();
            var w = el.ownerDocument.defaultView;

            if ( ! w) return false;

            if ( ! el) return false;

            while (el && (el instanceof w.HTMLElement || el instanceof w.XULElement))
            {
                let v = w.getComputedStyle(el, null).getPropertyValue("visibility");
                let d = w.getComputedStyle(el, null).getPropertyValue("display");

                if (v == "hidden" || v == "collapse" || d == "none")
                    return false;

                el = el.parentNode;
            }

            return true;
        },

        /**
         * Checks if element exists
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {Boolean}
         */
        exists: function()
        {
            return !! this.element().parentNode;
        },

        /**
         * Checks for given class
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param {String}  className   The class name
         *
         * @returns this
         */
        hasClass: function(className)
        {
            return this.element().classList.contains(className);
        },

        /**
         * Adds given class
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param {String}  className   The class name
         *
         * @returns this
         */
        addClass: function()
        {
            var args = arguments;
            return this.each(function()
            {
                this.classList.add.apply(this.classList, args);
            });
        },

        /**
         * Remove given class
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param {String}  className   The class name
         *
         * @returns this
         */
        removeClass: function()
        {
            var args = arguments;
            return this.each(function()
            {
                this.classList.remove.apply(this.classList, args);
            });
        },

        /**
         * Set/get CSS value(s)
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {String|Object} key         The CSS property name, or an object with css properties/values
         * @param   {Mixed|Undefined} value     The CSS property value, or undefined if first arg was an object
         *
         * @returns this
         */
        css: function(key, value)
        {
            var pxRules = ["width", "height", "top", "left", "bottom", "right", "font-size"];

            if ((typeof key) == 'string' && value === undefined)
            {
                value = this.element().style[key];

                if (pxRules.indexOf(key) != -1 && value.indexOf("px") == (value.length-2))
                    value = value.substring(0, value.length-2);

                return value;
            }

            if (pxRules.indexOf(key) != -1 && ! isNaN(value))
                value = value + "px";

            var rules = {};
            if (value !== undefined)
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
         * Set/get attributes
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {String|Object} key         The attribute key
         * @param   {Mixed|Undefined} value     The attribute value, or empty if you just want to retrieve it
         *
         * @returns this
         */
        attr: function(key, value)
        {
            if ((typeof key) == 'string' && value === undefined)
            {
                return this.element().getAttribute(key);
            }

            var attrs = {};
            if (value !== undefined)
                attrs[key] = value;
            else
                attrs = key;

            return this.each(function()
            {
                for (let k in attrs)
                {
                    this.setAttribute(k, attrs[k]);
                }
            });
        },

        /**
         * Remove Attribute
         * @method
         * @memberof module:ko/dom~QueryObject
         * @param   {String} key    The attribute key
         *
         * @returns this
         */
        removeAttr: function(key)
        {
            return this.each(function()
            {
                this.removeAttribute(key);
            });
        },

        /**
         * Get a unique ID for the matched element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {String}
         */
        uniqueId: function()
        {
            var self = this;
            this.uniqueId.uuid = this.uniqueId.uuid || 0;

            this.each(function()
            {
                if (this.id) return;
                this.id = "_uuid-" + self.uniqueId.uuid++;
            });

            return this.element().id;
        },

        /**
         * Animate certain properties on the matched elements
         * @method
         * @memberof module:ko/dom~QueryObject
         * NOTE: This function is extremely experimental
         *
         * @param   {Object} props     The properties to animate
         * @param   {Object} opts      Options
         * @param   {Function|Null}    callback
         *
         * @returns this
         */
        animate: function(props, opts = {}, callback = null)
        {
            if ((typeof opts) == 'function')
            {
                callback = opts;
                opts = {};
            }
            else if ((typeof opts) == 'number')
            {
                opts = {duration: opts};
            }

            var _ = require("contrib/underscore");
            opts = _.extend(
            {
                fps: 30,
                duration: 400,
                complete: callback || function() {},
                start: {}
            }, opts);

            var frameCounter    = 0,
                frameCount      = Math.ceil((opts.fps / 1000) * opts.duration) || 1,
                interval        = opts.duration / frameCount;

            log.debug("Animation starting with " + frameCount + " frames at an interval of " + interval);

            var styles = {};
            this.uniqueId();
            this.each(function()
            {
                let computed = window.getComputedStyle(this);
                styles[this.id] = {};
                for (var prop in props)
                {
                    let value = props[prop];
                    if (prop in opts.start)
                    {
                        styles[this.id][prop] = opts.start[prop];
                    }
                    else if (prop in computed)
                    {
                        styles[this.id][prop] = parseInt(computed[prop].replace(/px$/));
                    }
                    else
                    {
                        switch (prop)
                        {
                            case 'panelX':
                                styles[this.id][prop] = parseInt(this.popupBoxObject.screenX);
                                break;
                            case 'panelY':
                                styles[this.id][prop] = parseInt(this.popupBoxObject.screenY);
                                break;
                            default:
                                styles[this.id][prop] = NaN;
                                break;
                        }
                    }

                    if ( ! isNaN(styles[this.id][prop]))
                        styles[this.id][prop + "::Increments"] = (value - styles[this.id][prop]) / frameCount;
                };
            });

            this._animComplete = opts.complete;

            var frameStep = () =>
            {
                frameCounter++;
                log.debug("Frame: " + frameCounter);
                if ( ! this.exists()) return;

                try
                {

                    this.each(function()
                    {
                        for (var prop in props)
                        {
                            let style = styles[this.id];
                            let currentValue = style[prop];
                            let increment = style[prop + "::Increments"];

                            if (isNaN(currentValue))
                                continue;

                            let newValue = frameCounter == frameCount ?
                                            props[prop] : currentValue + increment;

                            log.debug("Setting " + prop + " to " + newValue);

                            switch (prop)
                            {
                                case 'panelX':
                                    this.moveTo(newValue, this.popupBoxObject.screenY);
                                    break;
                                case 'panelY':
                                    this.moveTo(this.popupBoxObject.screenX, newValue);
                                    break;
                                default:
                                    this.style[prop] = newValue;
                                    break;
                            }

                            styles[this.id][prop] = newValue;
                        };
                    });

                } catch (e)
                {
                    log.exception(e, "Something went wrong while animating a frame, stopping animation");
                    this.stop();
                }

                if (frameCounter == frameCount)
                {
                    this.stop();
                }
                else
                {
                    this._animTimer = window.setTimeout(frameStep.bind(this), interval);
                }

            }

            this._animTimer = window.setTimeout(frameStep.bind(this), interval);
        },

        /**
         * Stop any running animations
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        stop: function()
        {
            if ("_animTimer" in this)
            {
                window.clearTimeout(this._animTimer);
                delete this._animTimer;

                if ("_animComplete" in this)
                {
                    this._animComplete();
                    delete this._animComplete;
                }
            }

            return this;
        },

        /**
         * Focus on element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns this
         */
        focus: function()
        {
            this.element().focus();
            return this;
        },

        /**
         * Find within current element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {queryObject}
         */
        find: function(query)
        {
            return new queryObject(query, this.element());
        },

        findAnonymous: function(attr, value)
        {
            var childNodes = function (el)
            {
                var children = [];
                var _children = document.getAnonymousNodes(el);
                if (_children) children = Array.prototype.slice.call(_children);

                if (el.childNodes.length)
                {
                    children = children.concat(Array.prototype.slice.call(el.childNodes))
                }

                return children;
            }

            var children = childNodes(this.element());

            if ( ! children) return new queryObject([]);

            var child = children.shift();
            var matched = [];
            while (child)
            {
                if (child instanceof window.XULElement)
                {
                    if (child.getAttribute(attr) == value)
                    {
                        matched.push(child);
                        if (attr == "anonid") return new queryObject(child);
                    }

                    let _children = childNodes(child);
                    if (_children) children = children.concat(_children);
                }
                child = children.shift();
            }

            return new queryObject(matched);
        },

        /**
         * Get child nodes
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {queryObject}
         */
        children: function()
        {
            return new queryObject(this.element().childNodes);
        },

        /**
         * Get number of child nodes
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {int}
         */
        childCount: function()
        {
            return this.element().childNodes.length;
        },

        /**
         * Remove matched elements
         *
         * @returns {Void}
         */
        remove: function()
        {
            this.each(function()
            {
                if (this.parentNode)
                    this.parentNode.removeChild(this);
            });
        },

        /**
         * Virtualizes the given element, this essentially takes it out of the DOM
         * and allows you to make modifications to it without forcing DOM updates
         *
         * This element will not be selectable using DOM queries nor will it be
         * able to use any sort of parent/sibling queries, until unvirtualized.
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {this}
         */
        virtualize: function() {
            this.each(function() {
                this._virtualizedPlaceholder = $.createElement("<box/>");
                this.parentNode.replaceChild(this._virtualizedPlaceholder, this);
            });

            return this;
        },

        /**
         * Un-virtualizes the element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {this}
         */
        unvirtualize: function() {
            this.each(function() {
                if ( ! this._virtualizedPlaceholder)
                    return;

                this._virtualizedPlaceholder.parentNode.replaceChild(this, this._virtualizedPlaceholder);
            });

            return this;
        },

        /**
         * Get first matched element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {queryObject}
         */
        first: function() { return new queryObject(this.element(0)); },

        /**
         * Get last matched element
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {queryObject}
         */
        last: function() { return new queryObject(this.element(-1)); },

        /**
         * Get first matched element, without wrapping it in a queryObject
         * @method
         * @memberof module:ko/dom~QueryObject
         * @returns {Element}
         */
        element:  function(k) {
            return this._elements.slice(k || 0)[0] || undefined;
        }
    }

    module.exports = $;

})();
