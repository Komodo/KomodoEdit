/*!
* Based on ki.js - jQuery-like API super-tiny JavaScript library
* https://github.com/dciccale/ki.js
*/
if (typeof module === 'undefined') module = {}; // debugging helper
(function() {

    const log   = require("ko/logging").getLogger("ko-dom");
    //log.setLevel(require("ko/logging").LOG_DEBUG);

    /* === MAIN CONSTRUCTION LOGIC === */

    /*
     * $ main function
     * query = css selector, dom object, or function
     * http://www.dustindiaz.com/smallest-domready-ever
     * returns instance or executes function on ready
     */
    var $ = function(query, parent) {
        parent = parent || window.document;

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
            return new queryObject(query, parent)
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

    /*
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
         * once method
         * event = string event type i.e 'click'
         * action = function
         * return this
         */
        once: function(event, action)
        {
            var elems = this;
            
            var listener = function()
            {
                action.apply(this, arguments);
                elems.each(function()
                {
                    this.removeEventListener(event, listener);
                });
            };
            
            return this.each(function()
            {
                this.addEventListener(event, listener);
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

        /*
         * Reverse the element array
         */
        reverse: function(action) {
            this._elements.reverse();
            return this;
        },

        /**
         * Set text content of elem
         * @param   {string} value
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
         * @param   {string|object} value String or queryObject
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
         */
        outerHtml: function()
        {
            return this.element().outerHTML;
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

        replaceWith: function(elem)
        {
            if ("koDom" in elem) elem = elem.element();
            return this.element().parentNode.replaceChild(elem, this.element());
        },

        clone: function()
        {
            return $(this.element().cloneNode(true));
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
                return this.element()[valueKey];

            return this.each(function()
            {
                this[valueKey] = value;
            });
        },

        parent: function()
        {
            return $(this.element().parentNode);
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

        exists: function()
        {
            return !! this.element().parentNode;
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
        
        removeAttr: function(key)
        {
            return this.each(function()
            {
                this.removeAttribute(key);
            });
        },

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
         */
        focus: function()
        {
            this.element().focus();
            return this;
        },

        /**
         * Find within current element
         */
        find: function(query)
        {
            return new queryObject(query, this.element());
        },

        children: function()
        {
            return new queryObject(this.element().childNodes);
        },

        remove: function()
        {
            this.each(function()
            {
                this.parentNode.removeChild(this);
            });
        },

        // for some reason is needed to get an array-like
        // representation instead of an object
        splice: function() { return this._elements.splice.call(arguments); },

        // Use first entry
        first: function() { return new queryObject(this.element(0)); },

        last: function() { return new queryObject(this.element(-1)); },

        element:  function(k) {
            return this._elements.slice(k || 0)[0] || undefined;
        }
    }

    module.exports = $;
    
})();
