window.app = {};
(function() {
    
    var prefs = require("ko/prefs");
    var win = require("ko/windows").getMain();
    var elem = {
        statusbar: document.getElementById("statusbar"),
        input: document.getElementById("input"),
        inputMock: document.getElementById("input-mock"),
        console: document.getElementById("output").parentNode,
        output: document.getElementById("output")
    }
    
    var history = JSON.parse(prefs.getString("console_history", "[]"));
    var historyPos = -1;
    
    var charWidth = elem.inputMock.offsetWidth;
    var charHeight = elem.inputMock.offsetHeight / 2;
    
    this.init = function()
    {
        elem.input.addEventListener("select", this.updateCaretPos.bind(this));
        elem.input.addEventListener("click", this.updateCaretPos.bind(this));
        elem.input.addEventListener("change", this.updateCaretPos.bind(this));
        elem.input.addEventListener("keyup", this.updateCaretPos.bind(this));
        
        elem.input.addEventListener("keypress", this.onKeyNav.bind(this));
        
        new autoComplete({
            selector: "#input",
            menuClass: "hud",
            source: this.autoComplete.bind(this),
            onSelect: this.onSelectCompletion.bind(this),
            onReset: this.onResetCompletion.bind(this)
        });
    }
    
    this.updateCaretPos = function()
    {
        var text = elem.input.value.substr(0, elem.input.selectionStart);
        var lines = text.split(/\n/g);
        var caretValue = lines.slice(-1)[0];
        
        var left = caretValue.length * charWidth - elem.input.scrollLeft;
        var top = lines.length * charHeight - elem.input.scrollTop;
        elem.input.caretX = left;
        elem.input.caretY = top;
        elem.input.caretValue = caretValue;
        elem.input.caretLine = lines.length;
        elem.input.lines = elem.input.value.split(/\n/g).length;
        
        var scroll = Math.abs(elem.console.scrollTop - elem.console.scrollTopMax) < 5; // 5 pixel margin of error
        
        var rows = elem.input.lines > 5 ? 5 : elem.input.lines;
        if (rows == 1 && elem.input.scrollLeft) rows = 2;
        var maxHeight = 5 * 1.5;
        var height = rows * 1.5;
        elem.input.style.height = height + "rem";
        elem.input.rows = rows;

        var updateHeight = () =>
        {
            if (height < maxHeight && elem.input.scrollTopMax)
            {
                rows++;
                height = rows * 1.5;
                elem.input.style.height = height + "rem";
                updateHeight();
            }
        };
        updateHeight();
        
        if (scroll) elem.console.scrollTop = elem.console.scrollTopMax;
    }
    
    this.onKeyNav = function(e)
    {
        switch (e.keyCode)
        {
            case 38:
            case 40:
                if (elem.input.sc.style.display == 'block')
                {
                    e.preventDefault();
                    return; // autocomplete will handle this
                }
                if (e.keyCode == 38 && elem.input.caretLine == 1)
                {
                    var his = history.slice(++historyPos, historyPos+1)[0];
                    if (his)
                        elem.input.value = his;
                    else
                        historyPos--;
                        
                    e.preventDefault();
                    e.stopPropagation();
                }
                
                if (e.keyCode == 40 && elem.input.caretLine == elem.input.lines)
                {
                    var his = history.slice(--historyPos, historyPos+1)[0];
                    if (his && historyPos > -1)
                        elem.input.value = his;
                    else
                    {
                        elem.input.value = "";
                        historyPos = -1;
                    }
                    
                    e.preventDefault();
                    e.stopPropagation();
                }
                break;
            case 13: // enter
                if ( ! e.shiftKey)
                {
                    e.preventDefault();
                    
                    if (elem.input.sc.style.display == 'block') return; // autocomplete will handle this
                    setTimeout(function()
                    {
                        if (elem.input._suppressEnter)
                        {
                            elem.input._suppressEnter = false;
                            return;
                        }
                        
                        this.execute();
                    }.bind(this), 0);
                }
                
                setTimeout(this.updateCaretPos.bind(this), 10);
                break;
            case 9:
                if (elem.input.caretValue.trim() == "" && elem.input.selectionStart == elem.input.selectionEnd)
                {
                    var start = elem.input.selectionStart;
                    var value = elem.input.value;
                    elem.input.value = value.substr(0,start) + "    " + value.substr(start);
                    elem.input.selectionStart = elem.input.selectionEnd = start + 4;
                    
                }
                e.preventDefault();
                break;
        }
    }
    
    this.execute = function()
    {
        var input = elem.input.value;
        
        if (input == "/clear")
        {
            elem.output.innerHTML = "";
            this.print("output", "Console Cleared", true);
        }
        else if (input == "/windows")
        {
            var windows = require("ko/windows").getAll();
            var li = document.createElement("li");
            li.classList.add("output");
            
            var wrap = document.createElement("div");
            wrap.classList.add("message");
            li.appendChild(wrap);
            
            var w, a, l;
            for (w of windows)
            {
                l = document.createElement("li");
                a = document.createElement("a");
                l.appendChild(a);
                
                var title = w.document.title || "unnamed";
                
                a.textContent = `${w.location.href} (${title})`;
                a.addEventListener("click", function(w) {
                    win = w;
                    this.print("output", `Selected window: ${w.location.href}`, true);
                }.bind(this, w));
                
                wrap.appendChild(l);
            }
            
            this.printLi(li);
        }
        else
        {
            this.print("input", input, true);
            
            var result;
            try
            {
                result = win.eval(input);
            }
            catch (e)
            {
                this.print("exception", e);
                result = false;
            }
            
            if (result !== undefined) this.print("output", result);
        }

        if (input.trim()) {
            history.unshift(input);
            history = history.slice(0, 50);
            historyPos = -1;
            prefs.setString("console_history", JSON.stringify(history));
        }
        
        elem.input.value = "";
    }
    
    this.print = function(type, data, dontFormat)
    {
        var li = document.createElement("li");
        li.classList.add(type);
        
        var dataType = _getType(data);
        
        if ( ! dontFormat)
        {
            data = this.formatData(data, type);
        }
        else
            data = document.createTextNode(data);
        
        var message = document.createElement("div");
        message.classList.add("message");
        if ( ! dontFormat) message.classList.add("type-" + dataType);
        message.appendChild(data);
        
        li.appendChild(message);
        
        this.printLi(li);
    }
    
    this.formatData = function(data, type)
    {
        switch (type)
        {
            case "exception":
                return this.formatException(data);
                break;
            default:
                return this.formatComplex(data);
                break;
        }
    }
    
    this.formatException = function(ex)
    {
        var data = document.createElement("label");
        var checkbox = document.createElement("input");
        checkbox.setAttribute("type", "checkbox");
        data.appendChild(checkbox);
        
        var message = document.createElement("div");
        message.classList.add("ex-message");
        message.textContent = ex.message;
        data.appendChild(message);

        var traceStart = document.createElement("div");
        message.classList.add("ex-trace-start");
        traceStart.textContent = "  Stack Trace:";
        data.appendChild(traceStart);

        if (ex.stack)
        {
            var trace = document.createElement("ul");
            var stack = ex.stack.split(/\n/g);
            stack.forEach(function(frame) {
                if (frame.indexOf(ex.message) !== -1) return;
                var li = document.createElement("li");
                li.textContent = "    " + frame.trim();
                trace.appendChild(li);
            });
            data.appendChild(trace);
        }
        
        return data;
    }
    
    this.formatComplex = function(aThing) 
    {
        var nonIterable = ["function", "undefined", "null", "boolean", "string", "float", "number"];
        var type = _getType(aThing);
        
        var li = document.createElement("li");
        li.classList.add("complex-format");
        li.classList.add("type-" + type);
        
        var typeIndicator = document.createElement("div");
        typeIndicator.textContent = _ucFirst(type) + " ";
        typeIndicator.classList.add("type-indicator");
        li.appendChild(typeIndicator);

        if ((typeof aThing == "object") && nonIterable.indexOf(type) == -1)
        {
            try
            {
                var start = '{', end = '}';
                if (type == "array") start = '[', end = ']';
                
                var wrap = document.createElement("label");
                var checkbox = document.createElement("input");
                checkbox.setAttribute("type", "checkbox");
                wrap.appendChild(checkbox);
                
                var inner = document.createElement("div");
                
                if (type == "element")
                    inner.appendChild(this.formatElement(aThing));
                else
                {
                    
                    var innerStr = start;
                    var children = [], len = 0, childType, childValue, hasMore = false;
                    for (var k of Object.getOwnPropertyNames(aThing))
                    {
                        if (++len == 5)
                        {
                            hasMore = true;
                            break;
                        }
                        
                        if ( ! aThing.hasOwnProperty(k)) continue;
                        childType = _getType(aThing[k]);
                        if (["undefined", "null", "boolean", "string", "float", "number"].indexOf(childType) != -1)
                            childValue = JSON.stringify(aThing[k]);
                        else
                            childValue = _ucFirst(childType)
                        childValue = _ellipsis(childValue, 10);
                        children.push(k + ": " + childValue);
                    }
                    
                    if (hasMore) children.push("..");
                    innerStr += children.join(", ") + end;
                    inner.textContent = innerStr;
                }
                wrap.appendChild(inner);
                li.appendChild(wrap);
                
                checkbox.addEventListener("click", function()
                {
                    if (checkbox.__initialized)
                    {
                        li.getElementsByTagName("ul")[0].style.display = checkbox.checked ? "block" : "none";
                        return;
                    }
                    checkbox.__initialized = true;
                    
                    var ul = document.createElement("ul"), subLi;
                    _keysSorted(aThing, false).forEach(function(k)
                    {
                        var proto = false;
                        if ( ! aThing.hasOwnProperty(k)) proto = true;
                        try
                        {
                            subLi = this.formatComplex(aThing[k])
                        }
                        catch (e)
                        {
                            subLi = document.createElement("li");
                            subLi.appendChild(document.createTextNode("<inaccessible>"));
                        }
                        if (proto) subLi.classList.add("prototype");
                        var key = document.createElement("span");
                        key.classList.add("object-key");
                        key.textContent = k + ": ";
                        subLi.insertBefore(key, subLi.firstChild);
                        ul.appendChild(subLi);
                    }.bind(this));
                    
                    li.appendChild(ul);
                }.bind(this));
                
                return li;
            }
            catch (e)
            {}
        }
        
        try
        {
            var str;
            if (aThing === null)
                str = "" // The type gives all the information needed
            else
                str = aThing.toString();
             
            var _str = _ellipsis(str, 50);
            if (str != _str)
            {
                if (type == "string") _str = `"${_str}"`;
                var label = document.createElement("label");
                var checkbox = document.createElement("input");
                checkbox.setAttribute("type", "checkbox");
                label.appendChild(checkbox);
                
                var elem = document.createElement("div");
                elem.textContent = _str;
                label.appendChild(elem);
                
                elem = document.createElement("div");
                elem.classList.add("expanded");
                elem.textContent = str;
                label.appendChild(elem);
                
                li.appendChild(label);
            }
            else
            {
                if (type == "string") str = '"' + str + '"';
                li.appendChild(document.createTextNode(str));
            }
        }
        catch (e)
        {
            li.appendChild(document.createTextNode("<inaccessible>"));
        }
        
        return li
    }
    
    this.formatElement = function(element)
    {
        return document.createTextNode("<" + element.tagName +
            (element.id ? "#" + element.id : "") +
            (element.className && element.className.split ?
                "." + element.className.split(" ").join(" .") :
                "") +
            ">");
    }
    
    this.onInteract = function()
    {
    }
    
    this.printLi = function(li)
    {
        var timestamp = document.createElement("div");
        timestamp.classList.add("timestamp");
        
        var date = new Date();
        var hours = ("0" + date.getHours()).substr(-2),
            minutes = ("0" + date.getMinutes()).substr(-2),
            seconds = ("0" + date.getSeconds()).substr(-2),
            milliseconds = ("00" + date.getMilliseconds()).substr(-3);
        timestamp.textContent = hours + ":" + minutes + ":" + seconds + " " + milliseconds + "ms";
        
        li.appendChild(timestamp);
        
        var scroll = Math.abs(elem.console.scrollTop - elem.console.scrollTopMax) < 5; // 5 pixel margin of error
        elem.output.appendChild(li);
        if (scroll) elem.console.scrollTop = elem.console.scrollTopMax;
    }
    
    this.focus = function()
    {
        elem.input.focus();
    }
    
    this.autoComplete = function(input)
    {
        input = input.split(".");
        var scope = input.slice(0,input.length-1).join(".");
        var pattern = input.slice(-1)[0].toLowerCase();
        
        var completions = [];
        for (var completion of this.completions(scope))
        {
            if (completion.toLowerCase().indexOf(pattern)===0)
                completions.push(completion);
        }
        
        if (completions.length === 1 && completions[0] == pattern)
            return false;
        
        completions.reverse();
        return completions;
    }
    
    this.onSelectCompletion = function(val)
    {
        var input = elem.input.caretValue.split(".");
        var scope = input.slice(0,input.length-1).join(".");
        if (scope.length) scope += ".";
        
        var start = elem.input.selectionStart - elem.input.caretValue.length;
        var value = elem.input.value;
        
        var completion = scope + val;
        elem.input.value = value.substr(0,start) + completion + value.substr(start + elem.input.caretValue.length);
        elem.input.selectionStart = start + completion.length;
        
        this.focus();
    }
    
    this.onResetCompletion = function(val)
    {
        elem.input.value = val;
        this.focus();
    }
    
    this.completions = function(scope)
    {
        if (scope == "") scope = "window";
        if ( ! scope.match(/^[\w\s\.\[\]]+$/)) return [];
        try
        {
            win._consoleKeysSorted = _keysSorted;
            return win.eval('_consoleKeysSorted(' + scope + ')');
        } catch (e) {}
        return [];
    }
    
    var _getType = function(ob)
    {
        var type = typeof ob;
        
        if (Array.isArray(ob)) type = "array";
        else if ((ob instanceof HTMLElement || ob instanceof XULElement) && ob.tagName) type = "element";
        else if (ob instanceof Error) type = "exception";
        else if (ob === null) type = 'null';
        else if (typeof ob == "object")
        {
            if (ob.constructor && ob.constructor.name)
                type = ob.constructor.name;
            else
                type = Object.prototype.toString.call(ob).slice(8, -1);
        }
        
        return type.toLowerCase();
    }
    
    var _ucFirst = function(str)
    {
        str = str.toString();
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    var _obProperties = function(ob, full = true)
    {
        var keys = Object.getOwnPropertyNames(ob);
        
        var k
        for (k in ob) 
            keys.push(k);
        
        if ( ! full)
        {
            keys.push("constructor");
            keys.push("prototype");
        }
        else
        {
            keys = keys.concat(keys, Object.getOwnPropertyNames(ob.constructor));
            keys = keys.concat(keys, Object.getOwnPropertyNames(Object.prototype));
        }
        
        keys = keys.concat(keys, Object.getOwnPropertyNames(Object));
            
        var _keys = [];
        var _processed = {};
        
        var k;
        for (k of keys)
        {
            if (k in _processed) continue;
            
            _processed[k] = true;
            _keys.push(k);
        }
        
        return _keys;
    }
    
    var _keysSorted = function(ob, full = true)
    {
        if (Array.isArray(ob))
            return Object.getOwnPropertyNames(ob).sort(function(a,b){return a - b});
        else
        {
            var keys = _obProperties(ob, full);
            return keys.sort();
        }
    }
    
    var _ellipsis = function (str, length = 50)
    {
        if (str.length <= length && ! str.match(/\n/))
            return str;
        
        str = str.replace(/\n/g, " ");
        if (str.length > length)
        {
            str = str.substr(0,length);
            str += " .."
        }
        
        return str;
    }
    
    this.init();
    
}).apply(window.app);
