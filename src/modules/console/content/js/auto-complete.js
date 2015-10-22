/*
    JavaScript autoComplete v1.0.2
    Copyright (c) 2014 Simon Steinberger / Pixabay
    GitHub: https://github.com/Pixabay/JavaScript-autoComplete
    License: http://www.opensource.org/licenses/mit-license.php
*/

var autoComplete = (function(){
    // "use strict";
    function autoComplete(options){
        if (!document.querySelector) return;

        // helpers
        function hasClass(el, className){ return el.classList ? el.classList.contains(className) : new RegExp('\\b'+ className+'\\b').test(el.className); }

        function addEvent(el, type, handler){
            if (el.attachEvent) el.attachEvent('on'+type, handler); else el.addEventListener(type, handler);
        }
        function removeEvent(el, type, handler){
            // if (el.removeEventListener) not working in IE11
            if (el.detachEvent) el.detachEvent('on'+type, handler); else el.removeEventListener(type, handler);
        }
        function live(elClass, event, cb, context){
            addEvent(context || document, event, function(e){
                var found, el = e.target || e.srcElement;
                while (el && !(found = hasClass(el, elClass))) el = el.parentElement;
                if (found) cb.call(el, e);
            });
        }

        var o = {
            selector: 0,
            source: 0,
            minChars: 2,
            delay: 150,
            cache: 0,
            menuClass: '',
            renderItem: function (item, search){
                // escape special characters
                search = search.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                var re = new RegExp("(" + search.split(' ').join('|') + ")", "gi");
                return '<div class="autocomplete-suggestion" data-val="' + item + '">' + item.replace(re, "<b>$1</b>") + '</div>';
            },
            onSelect: function(term){},
            onReset: function(value){}
        };
        for (var k in options) { if (options.hasOwnProperty(k)) o[k] = options[k]; }

        // init
        var that = typeof o.selector == 'object' ? [o.selector] : document.querySelector(o.selector);

        // create suggestions container "sc"
        that.sc = document.createElement('div');
        that.sc.className = 'autocomplete-suggestions '+o.menuClass;

        that.setAttribute('data-sc', that.sc);
        that.autocompleteAttr = that.getAttribute('autocomplete');
        that.setAttribute('autocomplete', 'off');
        that.cache = {};
        that.last_val = '';
        
        that.getCaretPixelPos = function (offsetx, offsety)
        {
            var $node = that;
            
            offsetx = offsetx || 0;
            offsety = offsety || 0;
        
            var nodeLeft = $node.offsetLeft,
                nodeTop = $node.offsetTop;
        
            var pos = {left: 0, top: 0};
            var sel = window.getSelection();
            var range = sel.getRangeAt(0).cloneRange();
            try
            {
                range.setStart(range.startContainer, range.startOffset-1);
            } catch(e) {};
            
            var rect = range.getBoundingClientRect();
            if (range.endOffset == 0 || range.toString() === '')
            {
                // first char of line
                if (range.startContainer == $node)
                {
                    pos.top = 0;
                    pos.left = 0;
                }
                else
                {
                    pos.top = range.startContainer.offsetTop;
                    pos.left = range.startContainer.offsetLeft;
                }
            }
            else
            {
                pos.left = rect.left + rect.width + offsetx - nodeLeft;
                pos.top = rect.top + offsety - nodeTop;
            }
            return pos;
        };

        that.updateSC = function(resize, next){
            var rect = that.getBoundingClientRect();
            var pos = {
                left: that.caretX,
                top: that.caretY
            };
            that.sc.style.left = Math.round(pos.left) + rect.left + (window.pageXOffset || document.documentElement.scrollLeft) + 'px';
            that.sc.style.bottom = window.innerHeight - rect.top + (window.pageYOffset || document.documentElement.scrollTop) + 1 + 'px';
            if (!resize) {
                that.sc.style.display = 'block';
                if (!that.sc.maxHeight) { that.sc.maxHeight = parseInt((window.getComputedStyle ? getComputedStyle(that.sc, null) : that.sc.currentStyle).maxHeight); }
                if (!that.sc.suggestionHeight) that.sc.suggestionHeight = that.sc.querySelector('.autocomplete-suggestion').offsetHeight;
                if (that.sc.suggestionHeight)
                    if (next) {
                        var scrTop = that.sc.scrollTop, selTop = next.getBoundingClientRect().top - that.sc.getBoundingClientRect().top;
                        if (selTop + that.sc.suggestionHeight - that.sc.maxHeight > 0)
                            that.sc.scrollTop = selTop + that.sc.suggestionHeight + scrTop - that.sc.maxHeight;
                        else if (selTop < 0)
                            that.sc.scrollTop = selTop + scrTop;
                    }
            }
        }
        addEvent(window, 'resize', that.updateSC);
        document.body.appendChild(that.sc);

        live('autocomplete-suggestion', 'mouseleave', function(e){
            var sel = that.sc.querySelector('.autocomplete-suggestion.selected');
            if (sel) setTimeout(function(){ sel.className = sel.className.replace('selected', ''); }, 20);
        }, that.sc);

        live('autocomplete-suggestion', 'mouseover', function(e){
            var sel = that.sc.querySelector('.autocomplete-suggestion.selected');
            if (sel) sel.className = sel.className.replace('selected', '');
            this.className += ' selected';
        }, that.sc);

        live('autocomplete-suggestion', 'mousedown', function(e){
            if (hasClass(this, 'autocomplete-suggestion')) { // else outside click
                var v = this.getAttribute('data-val');
                o.onSelect(v);
                that.sc.style.display = 'none';
            }
        }, that.sc);

        that.blurHandler = function(){
            return;
            try { var over_sb = document.querySelector('.autocomplete-suggestions:hover'); } catch(e){ var over_sb = 0; }
            if (!over_sb) {
                that.last_val = that.value;
                that.sc.style.display = 'none';
                setTimeout(function(){ that.sc.style.display = 'none'; }, 350); // hide suggestions on fast input
            } else if (that !== document.activeElement) setTimeout(function(){ that.focus(); }, 20);
        };
        addEvent(that, 'blur', that.blurHandler);

        var suggest = function(data){
            var val = that.value;
            that.cache[val] = data;
            if (data.length && val.length >= o.minChars) {
                var s = '';
                for (var i=0;i<data.length;i++) s += o.renderItem(data[i], val);
                that.sc.innerHTML = s;
                
                var next = that.sc.childNodes[that.sc.childNodes.length - 1];
                next.className += ' selected';

                setTimeout(function() {
                    if (that.sc.clientHeight < that.sc.scrollHeight)
                    {
                        that.sc.scrollTop = that.sc.scrollHeight - that.sc.clientHeight;
                    }
                }, 10);
                    
                that.updateSC(0);
            }
            else
                that.sc.style.display = 'none';
        }

        that.keypressHandler = function(e){
            var key = window.event ? e.keyCode : e.which;
            // down (40), up (38)
            if ((key == 40 || key == 38) && that.sc.innerHTML && that.sc.style.display != 'none') {
                var next, sel = that.sc.querySelector('.autocomplete-suggestion.selected');
                if (!sel) {
                    next = (key == 40) ? that.sc.querySelector('.autocomplete-suggestion') : that.sc.childNodes[that.sc.childNodes.length - 1]; // first : last
                    next.className += ' selected';
                } else {
                    next = (key == 40) ? sel.nextSibling : sel.previousSibling;
                    if (next) {
                        sel.className = sel.className.replace('selected', '');
                        next.className += ' selected';
                    }
                    else { sel.className = sel.className.replace('selected', ''); o.onReset(that.last_val); next = 0; }
                }
                that.updateSC(0, next);
                e.preventDefault();
            }
            // esc
            else if (key == 27 && that.sc.style.display != 'none') {
                o.onReset(that.last_val);
                that.sc.style.display = 'none';
                e.preventDefault();
            }
            // enter
            else if (key == 13 && that.sc.style.display != 'none' && ! e.shiftKey) {
                var sel = that.sc.querySelector('.autocomplete-suggestion.selected');
                if ( ! sel) return;
                o.onSelect(sel.getAttribute('data-val'));
                setTimeout(function(){ that.sc.style.display = 'none'; }, 20);
                e.preventDefault();
                that._suppressEnter = true;
            }
            // tab
            else if (key == 9 && that.sc.style.display != 'none') {
                var completions = o.source(that.caretValue);
                e.preventDefault();
                if ( ! completions || ! completions.length) return;
                var completion = completions.slice(-1)[0];
                while (completion.length && completions.length > 1)
                {
                    var match = true;
                    for (var _completion of completions)
                    {
                        if (_completion.indexOf(completion) !== 0)
                        {
                            match = false;
                            break;
                        }
                    }
                    if (match) break;
                    completion = completion.substr(0, completion.length-1);
                }
                if (completion.length) o.onSelect(completion);
            }
        };
        addEvent(that, 'keyup', that.keypressHandler);

        that.keyupHandler = function(e){
            var key = window.event ? e.keyCode : e.which;
            if ((key < 35 || key > 40) && key != 13 && key != 27) {
                var val = that.caretValue;
                if (val.length >= o.minChars) {
                    if (val != that.last_val) {
                        that.last_val = val;
                        if (that.timer) clearTimeout(that.timer);
                        if (o.cache) {
                            if (val in that.cache) { suggest(that.cache[val]); return; }
                        }
                        that.timer = setTimeout(function(){
                            var completions = o.source(val)
                            if (completions)
                                suggest(completions);
                            else
                                that.sc.style.display = 'none';
                        }, o.delay);
                    }
                } else {
                    that.last_val = val;
                    that.sc.style.display = 'none';
                }
            }
        };
        addEvent(that, 'keyup', that.keyupHandler);

        that.focusHandler = function(e){
            that.last_val = '\n';
            that.keyupHandler(e)
        };
        if (!o.minChars) addEvent(that, 'focus', that.focusHandler);

        // public destroy method
        this.destroy = function(){
            for (var i=0; i<elems.length; i++) {
                var that = elems[i];
                removeEvent(window, 'resize', that.updateSC);
                removeEvent(that, 'blur', that.blurHandler);
                removeEvent(that, 'focus', that.focusHandler);
                removeEvent(that, 'keyup', that.keypressHandler);
                removeEvent(that, 'keyup', that.keyupHandler);
                if (that.autocompleteAttr)
                    that.setAttribute('autocomplete', that.autocompleteAttr);
                else
                    that.removeAttribute('autocomplete');
                document.body.removeChild(that.sc);
                that = null;
            }
        };
    }
    return autoComplete;
})();

(function(){
    if (typeof define === 'function' && define.amd)
        define('autoComplete', function () { return autoComplete; });
    else if (typeof module !== 'undefined' && module.exports)
        module.exports = autoComplete;
    else
        window.autoComplete = autoComplete;
})();