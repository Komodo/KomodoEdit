window.app = {};
(function() {
    
    var win = require("ko/windows").getMain();
    var elem = {
        statusbar: document.getElementById("input").parentNode,
        input: document.getElementById("input"),
        console: document.getElementById("output").parentNode,
        output: document.getElementById("output")
    }
    
    this.init = function()
    {
        new autoComplete({
            selector: "#input",
            menuClass: "hud",
            source: this.autoComplete.bind(this),
            onSelect: this.onSelectCompletion.bind(this),
            onReset: this.onResetCompletion.bind(this)
        });
        
        elem.input.addEventListener("keydown", this.onKeyNav.bind(this));
        elem.input.addEventListener("paste", this.onPaste.bind(this));
    }
    
    this.onKeyNav = function(e)
    {
        switch (e.keyCode)
        {
            case 13: // enter
                if ( ! e.shiftKey)
                {
                    setTimeout(function()
                    {
                        if (elem.input._suppressEnter)
                        {
                            elem.input._suppressEnter = false;
                            return;
                        }
                        
                        this.execute();
                        elem.console.scrollTop = elem.console.scrollHeight - elem.console.clientHeight;
                    }.bind(this), 0);
                    
                    e.preventDefault();
                }
                break;
        }
    }
    
    this.onPaste = function(e)
    {
        var text = e.clipboardData.getData("text/plain");
        document.execCommand("insertText", false, text);
        e.preventDefault();
    };
    
    this.execute = function()
    {
        var input = elem.input.textContent;
        this.print("input", input, true);
        
        try
        {
            var result = win.eval(input);
        }
        catch (e)
        {
            this.print("exception", e);
            result = false;
        }
        
        if (result) this.print("output", result);
        
        elem.input.textContent = "";
    }
    
    this.print = function(type, data, dontFormat)
    {
        var li = document.createElement("li");
        li.classList.add(type);
        
        var dataType = _getType(data);
        
        if ( ! dontFormat)
        {
            data = this.formatData(data, dataType);
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
        var stack = ex.stack.split(/\n/g);
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
        
        var trace = document.createElement("ul");
        stack.forEach(function(frame) {
            if (frame.indexOf(ex.message) !== -1) return;
            var li = document.createElement("li");
            li.textContent = "    " + frame.trim();
            trace.appendChild(li);
        });
        data.appendChild(trace);
        
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
                    for (var k in aThing)
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
                    _keysSorted(aThing).forEach(function(k)
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
                        subLi.insertBefore(document.createTextNode(k + ": "), subLi.firstChild);
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
                
            if (str.length > 50 || str.match(/\n/))
            {
                var _str = str.replace(/\n/g, " ");
                if (_str.length > 50)
                {
                    _str = _str.substr(0,50);
                    if (type == "string") _str += '"';
                    _str += " .."
                }
                
                var label = document.createElement("label");
                var checkbox = document.createElement("input");
                checkbox.setAttribute("type", "checkbox");
                label.appendChild(checkbox);
                
                var elem = document.createElement("div");
                elem.textContent = _str;
                label.appendChild(elem);
                
                elem = document.createElement("div");
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
        timestamp.textContent = date.getHours() + ":" + date.getMinutes() + ":" + date.getSeconds() + " " + date.getMilliseconds() + "ms";
        
        li.appendChild(timestamp);
        
        var scroll = elem.console.clientHeight < elem.console.scrollHeight;
        elem.output.appendChild(li);
        if (scroll) elem.scrollTop = elem.scrollHeight - elem.clientHeight;
    }
    
    this.focus = function()
    {
        elem.input.focus();
        
        // Force selection to be at end of line
        var range = document.createRange();
        range.selectNodeContents(elem.input);
        range.collapse(false);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    }
    
    this.autoComplete = function(input, suggest)
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
        
        completions.reverse()
        return completions;
    }
    
    this.onSelectCompletion = function(val)
    {
        var input = elem.input.textContent.split(".");
        var scope = input.slice(0,input.length-1).join(".");
        if (scope.length) scope += ".";
        
        elem.input.textContent = scope + val;
        this.focus();
    }
    
    this.onResetCompletion = function(val)
    {
        elem.input.textContent = val;
        this.focus();
    }
    
    this.completions = function(scope)
    {
        if (scope == "") scope = "window";
        try
        {
            return win.eval('var _p = []; for (var k in ' + scope + ') { _p.push(k); }; _p;').sort();
        } catch (e) {}
        return [];
    }
    
    var _getType = function(ob)
    {
        var type = typeof ob;
        
        if (Array.isArray(ob)) type = "array";
        else if (ob instanceof HTMLElement && ob.tagName) type = "element";
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
    
    var _keysSorted = function(ob)
    {
        var keys = [];
        for (var k in ob)
            keys.push(k);
            
        if (Array.isArray(ob))
            return keys.sort(function(a,b){return a - b});
        else
            return keys.sort();
    }
    
    this.init();
    
}).apply(window.app);