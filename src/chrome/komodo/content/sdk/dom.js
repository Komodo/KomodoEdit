/*!
* Based on ki.js - jQuery-like API super-tiny JavaScript library
* https://github.com/dciccale/ki.js
*/
if (typeof module === 'undefined') module = {}; // debugging helper

/**
 * @module dom
 */
(function() {

    const log   = require("ko/logging").getLogger("ko-dom");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    /* === MAIN CONSTRUCTION LOGIC === */

    /**
     * $ main function
     * query = css selector, dom object, or function
     * http://www.dustindiaz.com/smallest-domready-ever
     * returns instance or executes function on ready
     */
    var $ = function(query, parent) {
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
    }

    /* === HELPER FUNCTIONS === */

    /**
     * Create element from complex string input
     *
     * @param   {String} html
     *
     * @returns {Node}
     */
    $.createElement = function(html, allowMultiple = false)
    {
        try
        {
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
     * $.create, Based on;
     * 
     * source      : http://gist.github.com/278016
     * author      : Thomas Aylott
     * site        : subtlegradient.com
     * copyright   : 2010 Thomas Aylott
     * license     : MIT
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
                if (typeof value == "string") value = value.replace(/'/g,'\\\'')
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
     * queryObject function (internal use)
     * query = selector, dom element or function
     */
    function queryObject(query, customParent)
    {
        var parent = window.document;

        this._elements = [];
        
        // Use push.apply to force array type
        if(Object.prototype.toString.call(query) === '[object Array]')
            this._elements = query.slice(0);
        else if (query && query.nodeType)
            this._elements.push.apply(this._elements, [query]);
        else if ('' + query === query)
            this._elements.push.apply(this._elements,  (customParent || parent).querySelectorAll(query));
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
         * @param {Event} event         String event type i.e 'click'
         * @param {Function} action     Function
         * 
         * @returns this
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
         * 
         * @param {Event} event     String event type i.e 'click'
         * @param {Function} action
         * 
         * @returns this
         */
        once: function(event, action)
        {
            var elems = this;
            
            var listener = function()
            {
                action.apply(this, arguments);
                this.off(event, listener);
            };
            
            this.on(event, listener);
        },

        /**
         * Remove event listener
         * 
         * @param {Event} event     String event type i.e 'click'
         * @param {Function} action 
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
         *
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
         * 
         * @param {Function} action    he function to call on each iteration
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
         * 
         * @returns this
         */
        reverse: function()
        {
            this._elements.reverse();
            return this;
        },

        /**
         * Set text content of elem
         * 
         * @param   {string} value
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
         * 
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
         * 
         * @returns this
         */
        outerHtml: function()
        {
            return this.element().outerHTML;
        },

        /**
         * Empty the contents of an element
         *
         * @returns this
         */
        empty: function()
        {
            return this.text("");
        },

        /**
         * Append content to elem
         * 
         * @param   {string|object} value String or queryObject
         *
         * @returns this
         */
        append: function(elem)
        {
            insertIntoElem(this, elem);
            return this;
        },

        /**
         * Prepend content to elem
         * 
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
         * 
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
         * 
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
         *
         * @returns {queryObject}
         */
        prev: function()
        {
            return new queryObject(this.element().previousSibling);
        },
        
        /**
         * Get the next sibling for the first element in the selection
         *
         * @returns {queryObject}
         */
        next: function()
        {
            return new queryObject(this.element().nextSibling);
        },

        /**
         * Replace matched element(s) with ..
         * 
         * @param   {Element} elem 
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
         * 
         * @returns {Element} matched element
         */
        clone: function(deep = true)
        {
            var el = this.element();
            var result = $(el.cloneNode(deep));
            
            if ("__koListeners" in el)
            {
                for (let event in el.__koListeners)
                {
                    if ( ! el.__koListeners.hasOwnProperty(event)) continue;
                    el.__koListeners[event].forEach(function(action) {
                        result.on(event, action);
                    });
                }
            }
            
            return result;
        },

        /**
         * Set / get value
         * 
         * @param   {String|Void} value
         *
         * @returns this
         */
        value: function(value)
        {
            // Todo: support different value types
            var valueKey = 'value';

            if (value === undefined)
                return this.element()[valueKey];

            return this.each(function()
            {
                this[valueKey] = value;
            });
        },

        /**
         * Retrieve parent node
         *
         * @returns {Element}   Parent node
         */
        parent: function()
        {
            return $(this.element().parentNode);
        },

        /**
         * Delete matched elements
         *
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
         *
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
         *
         * @returns this
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
         *
         * @returns {Boolean}
         */
        visible: function()
        {
            return ["","visible","initial", "inherit"].indexOf(this.element().style.visibility) != -1;
        },

        /**
         * Checks if element exists
         * 
         * @returns {Boolean}
         */
        exists: function()
        {
            return !! this.element().parentNode;
        },

        /**
         * Checks for given class 
         * 
         * @param {String}  className
         * 
         * @returns this
         */
        hasClass: function(className)
        {
            return this.element().classList.contains(className);
        },

        /**
         * Adds given class 
         * 
         * @param {String}  className
         * 
         * @returns this
         */
        addClass: function(className)
        {
            return this.each(function()
            {
                this.classList.add(className);
            });
        },

        /**
         * Remove given class
         * 
         * @param {String}  className
         * 
         * @returns this
         */
        removeClass: function(className)
        {
            return this.each(function()
            {
                this.classList.remove(className);
            });
        },

        /**
         * Set/get CSS value(s)
         * 
         * @param   {String|Object} key  
         * @param   {Mixed|Undefined} value
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
         * 
         * @param   {String|Object} key  
         * @param   {Mixed|Undefined} value
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
         * 
         * @param   {String} key
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
         * 
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
         *
         * NOTE: This function is extremely experimental 
         * 
         * @param   {Object} props   
         * @param   {Object} opts    
         * @param   {Function|Null} callback
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
            
            var frameStep = function()
            {
                frameCounter++;
                log.debug("Frame: " + frameCounter);

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
         * 
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
         *
         * @returns this
         */
        focus: function()
        {
            this.element().focus();
            return this;
        },

        /**
         * Find within current element
         *
         * @returns {queryObject}
         */
        find: function(query)
        {
            return new queryObject(query, this.element());
        },

        /**
         * Get child nodes
         * 
         * @returns {queryObject}
         */
        children: function()
        {
            return new queryObject(this.element().childNodes);
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
                this.parentNode.removeChild(this);
            });
        },

        /**
         * Get first matched element
         * 
         * @returns {queryObject}
         */
        first: function() { return new queryObject(this.element(0)); },

        /**
         * Get last matched element
         * 
         * @returns {queryObject}
         */
        last: function() { return new queryObject(this.element(-1)); },

        /**
         * Get first matched element, without wrapping it in a queryObject
         * 
         * @returns {Element}
         */
        element:  function(k) {
            return this._elements.slice(k || 0)[0] || undefined;
        }
    }

    module.exports = $;
    
})();
