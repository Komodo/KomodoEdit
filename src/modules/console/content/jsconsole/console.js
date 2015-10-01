(function(window) {
    
    var ko = require("ko/windows").getMain().ko;

    function sortci(a, b) {
        return a.toLowerCase() < b.toLowerCase() ? -1 : 1;
    }

    // custom because I want to be able to introspect native browser objects *and* functions

    function stringify(o, simple, visited) {
        var json = '',
            i, vi, type = '',
            parts = [],
            names = [],
            circular = false;
        visited = visited || [];

        try {
            type = ({}).toString.call(o);
        } catch (e) { // only happens when typeof is protected (...randomly)
            type = '[object Object]';
        }

        // check for circular references
        for (vi = 0; vi < visited.length; vi++) {
            if (o === visited[vi]) {
                circular = true;
                break;
            }
        }

        if (circular) {
            json = '[circular]';
        } else if (type == '[object String]') {
            json = '"' + o.replace(/"/g, '\\"') + '"';
        } else if (type == '[object Array]') {
            visited.push(o);

            json = '[';
            for (i = 0; i < o.length; i++) {
                parts.push(stringify(o[i], simple, visited));
            }
            json += parts.join(', ') + ']';
        } else if (type == '[object Object]') {
            visited.push(o);

            json = '{';
            for (i in o) {
                names.push(i);
            }
            names.sort(sortci);
            for (i = 0; i < names.length; i++) {
                parts.push(stringify(names[i], undefined, visited) + ': ' + stringify(o[names[i]], simple, visited));
            }
            json += parts.join(', ') + '}';
        } else if (type == '[object Number]') {
            json = o + '';
        } else if (type == '[object Boolean]') {
            json = o ? 'true' : 'false';
        } else if (type == '[object Function]') {
            json = o.toString();
        } else if (o === null) {
            json = 'null';
        } else if (o === undefined) {
            json = 'undefined';
        } else if (simple == undefined) {
            visited.push(o);

            json = type + '{\n';
            for (i in o) {
                names.push(i);
            }
            names.sort(sortci);
            for (i = 0; i < names.length; i++) {
                try {
                    parts.push(names[i] + ': ' + stringify(o[names[i]], true, visited)); // safety from max stack
                } catch (e) {
                    if (e.name == 'NS_ERROR_NOT_IMPLEMENTED') {
                        // do nothing - not sure it's useful to show this error when the variable is protected
                        // parts.push(names[i] + ': NS_ERROR_NOT_IMPLEMENTED');
                    }
                }
            }
            json += parts.join(',\n') + '\n}';
        } else {
            try {
                json = o + ''; // should look like an object      
            } catch (e) {}
        }
        return json;
    }

    function cleanse(s) {
        s = s instanceof Array ? s.join(', ') : s;
        return (s || '').replace(/[<&]/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;'
            }[m];
        });
    }

    function run(cmd) {
        var rawoutput = null,
            className = 'response',
            internalCmd = internalCommand(cmd);

        if (internalCmd) {
            return ['info', internalCmd];
        } else {
            try {
                rawoutput = bufferWindow.eval(cmd);
            } catch (e) {
                rawoutput = e.message;
                className = 'error';
                
                console.exception(e);
            }
            return [className, cleanse(stringify(rawoutput))];
        }
    }

    function post(cmd, blind) {
        cmd = trim(cmd);

        if (blind === undefined) {
            history.push(cmd);
            setHistory(history);
        }

        echo(cmd);

        // order so it appears at the top
        var el = document.createElement('div'),
            li = document.createElement('li'),
            span = document.createElement('span'),
            parent = output.parentNode;

        var response = run(cmd);

        if (response !== undefined) {
            el.className = 'response';
            span.innerHTML = response[1];

            el.appendChild(span);

            li.className = response[0];
            li.innerHTML = '<span class="gutter"></span>';
            li.appendChild(el);

            appendLog(li);
            
            exec.value = '';
            cursor.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
        }
        pos = history.length;
    }

    function log(msg, className) {
        var li = document.createElement('li'),
            div = document.createElement('div');

        div.innerHTML = typeof msg === 'string' ? cleanse(msg) : msg;
        li.className = className || 'log';
        li.innerHTML = '<span class="gutter"></span>';
        li.appendChild(div);

        appendLog(li);
    }
    
    function outputElem(name, message) {
        var li = document.createElement("li");
        li.classList.add(name);
        
        var span = document.createElement("span");
        span.classList.add("gutter");
        
        var msg = document.createElement("div");
        msg.classList.add("message");
        msg.textContent = message;
        
        var timestamp = document.createElement("div");
        timestamp.classList.add("timestamp");
        var date = new Date();
        timestamp.textContent = date.getHours() + ":" + date.getMinutes() + ":" + date.getSeconds() + " " + date.getMilliseconds() + "ms";
        
        li.appendChild(timestamp);
        li.appendChild(span);
        li.appendChild(msg);
        
        if (name != "echo")
        {
            var stack = new Error().stack.split("\n")
            try {
            stack.forEach(function(level) 
            {
                if (level.indexOf("/content/jsconsole/") != -1 || level.indexOf("gre/modules/devtools/Console.jsm") != -1)
                    return;
                
                var rx = /^(?:\s*(\S*)(?:\((.*?)\))?@)?((?:\w).*?):(\d+)(?::(\d+))?\s*$/i;
                var res = rx.exec(level);
                if ( ! res) throw Error();
                
                var [,method,,file,lineno,column] = res;
                
                var source = document.createElement("a");
                source.classList.add("source");
                
                var sourceName = file.split("/").slice(-1)[0];
                if (sourceName.length > 25)
                {
                    var start = sourceName.substring(0, (25 / 2));
                    var end = sourceName.substring((sourceName.length - (25 / 2)) + 1);
                    sourceName = start + ".." + end;
                }
                source.textContent = sourceName + ":" + lineno;
                source.addEventListener("click", function()
                {
                    var koResolve = Components.classes["@activestate.com/koResolve;1"]
                                        .getService(Components.interfaces.koIResolve);
                    var uri = file;
                    try {
                        var _uri = ko.uriparse.pathToURI(koResolve.uriToPath(file));
                        if (_uri) uri = _uri;
                    } catch (e) {};
                    ko.open.URIAtLine(uri, lineno);
                });
                
                li.insertBefore(source, li.firstChild.nextSibling);
                
                throw Error();
            });
            } catch (e) {}
        }
        
        return li;
    }

    window.log = function(type, cmd) {
        var li = outputElem(type, cmd);
        appendLog(li, true);
    }

    window.info = window.log.bind(null, "info");
    
    window.warn = window.log.bind(null, "warn");
    
    function echo(cmd, type = '') {
        window.log("echo", cmd);
    }

    function appendLog(el) {
        var wrap = document.documentElement;
        var scroll = wrap.scrollTop == wrap.scrollTopMax;

        output.appendChild(el);
        
        if (scroll)
            wrap.scrollTop = wrap.scrollTopMax;
    }

    function changeView(event) {
        var which = event.which || event.keyCode;
        if (which == 38 && event.shiftKey == true) {
            body.className = '';
            cursor.focus();
            try {
                localStorage.large = 0;
            } catch (e) {}
            return false;
        } else if (which == 40 && event.shiftKey == true) {
            body.className = 'large';
            try {
                localStorage.large = 1;
            } catch (e) {}
            cursor.focus();
            return false;
        }
    }

    function internalCommand(cmd) {
        var parts = [],
            c;
        if (cmd.substr(0, 1) == ':') {
            parts = cmd.substr(1).split(' ');
            c = parts.shift();
            return (commands[c] || noop).apply(this, parts);
        }
    }

    function noop() {}

    function showhelp() {
        var commands = [
                ':clear - to clear command history',
                ':history - list command history',
                ':log - open the error log'
        ];

        // commands = commands.concat([
        //   'up/down - cycle history',
        //   'shift+up - single line command',
        //   'shift+down - multiline command', 
        //   'shift+enter - to run command in multiline mode'
        // ]);

        return commands.join('\n');
    }

    function checkTab(evt) {
        var t = evt.target,
            ss = t.selectionStart,
            se = t.selectionEnd,
            tab = "  ";


        // Tab key - insert tab expansion
        if (evt.keyCode == 9) {
            evt.preventDefault();

            // Special case of multi line selection
            if (ss != se && t.value.slice(ss, se).indexOf("\n") != -1) {
                // In case selection was not of entire lines (e.g. selection begins in the middle of a line)
                // we ought to tab at the beginning as well as at the start of every following line.
                var pre = t.value.slice(0, ss);
                var sel = t.value.slice(ss, se).replace(/\n/g, "\n" + tab);
                var post = t.value.slice(se, t.value.length);
                t.value = pre.concat(tab).concat(sel).concat(post);

                t.selectionStart = ss + tab.length;
                t.selectionEnd = se + tab.length;
            }

            // "Normal" case (no selection or selection on one line only)
            else {
                t.value = t.value.slice(0, ss).concat(tab).concat(t.value.slice(ss, t.value.length));
                if (ss == se) {
                    t.selectionStart = t.selectionEnd = ss + tab.length;
                } else {
                    t.selectionStart = ss + tab.length;
                    t.selectionEnd = se + tab.length;
                }
            }
        }

        // Backspace key - delete preceding tab expansion, if exists
        else if (evt.keyCode == 8 && t.value.slice(ss - 4, ss) == tab) {
            evt.preventDefault();

            t.value = t.value.slice(0, ss - 4).concat(t.value.slice(ss, t.value.length));
            t.selectionStart = t.selectionEnd = ss - tab.length;
        }

        // Delete key - delete following tab expansion, if exists
        else if (evt.keyCode == 46 && t.value.slice(se, se + 4) == tab) {
            evt.preventDefault();

            t.value = t.value.slice(0, ss).concat(t.value.slice(ss + 4, t.value.length));
            t.selectionStart = t.selectionEnd = ss;
        }
        // Left/right arrow keys - move across the tab in one go
        else if (evt.keyCode == 37 && t.value.slice(ss - 4, ss) == tab) {
            evt.preventDefault();
            t.selectionStart = t.selectionEnd = ss - 4;
        } else if (evt.keyCode == 39 && t.value.slice(ss, ss + 4) == tab) {
            evt.preventDefault();
            t.selectionStart = t.selectionEnd = ss + 4;
        }
    }

    function trim(s) {
        return (s || "").replace(/^\s+|\s+$/g, "");
    }

    var ccCache = {};
    var ccPosition = false;

    function getProps(cmd, filter) {
        var surpress = {}, props = [];
        
        if (!ccCache[cmd]) {
            try {
                // surpress alert boxes because they'll actually do something when we're looking
                // up properties inside of the command we're running
                surpress.alert = bufferWindow.alert;
                bufferWindow.alert = function() {};
                
                // loop through all of the properties available on the command (that's evaled)
                ccCache[cmd] = bufferWindow.eval('var _p = []; for (var k in ' + cmd + ') { _p.push(k); }; _p;').sort();

                // return alert back to it's former self
                bufferWindow.alert = surpress.alert;
            } catch (e) {
                ccCache[cmd] = [];
            }

            // if the return value is undefined, then it means there's no props, so we'll 
            // empty the code completion
            if (ccCache[cmd][0] == 'undefined') ccOptions[cmd] = [];
            ccPosition = 0;
            props = ccCache[cmd];
        } else if (filter) {
            // console.log('>>' + filter, cmd);
            for (var i = 0, p; i < ccCache[cmd].length, p = ccCache[cmd][i]; i++) {
                if (p.indexOf(filter) === 0) {
                    if (p != filter) {
                        props.push(p.substr(filter.length, p.length));
                    }
                }
            }
        } else {
            props = ccCache[cmd];
        }

        return props;
    }

    function codeComplete(event) {
        var cmd = cursor.textContent.split(/[;\s]+/g).pop(),
            parts = cmd.split('.'),
            which = whichKey(event),
            cc,
            props = [];

        if (cmd) {
            // get the command without the dot to allow us to introspect
            if (cmd.substr(-1) == '.') {
                // get the command without the '.' so we can eval it and lookup the properties
                cmd = cmd.substr(0, cmd.length - 1);

                // returns an array of all the properties from the command
                props = getProps(cmd);
            } else {
                props = getProps(parts.slice(0, parts.length - 1).join('.') || 'window', parts[parts.length - 1]);
            }
            if (props.length) {
                if (which == 9) { // tabbing cycles through the code completion
                    // however if there's only one selection, it'll auto complete
                    if (props.length === 1) {
                        ccPosition = false;
                    } else {
                        ccPosition = 0;
                        
                        if (doubleTab)
                        {
                            var cmdLet = parts.slice(parts.length -1);
                            window.log("props", cmdLet + props.join(", " + cmdLet));
                        }
                    }
                } else {
                    ccPosition = 0;
                }

                if (ccPosition === false) {
                    completeCode();
                } else {
                    // position the code completion next to the cursor
                    if (!cursor.nextSibling) {
                        cc = document.createElement('span');
                        cc.className = 'suggest';
                        exec.appendChild(cc);
                    }

                    cursor.nextSibling.innerHTML = props[ccPosition];
                    exec.value = exec.textContent;
                }

                if (which == 9) return false;
            } else {
                ccPosition = false;
            }
        } else {
            ccPosition = false;
        }

        if (ccPosition === false && cursor.nextSibling) {
            removeSuggestion();
        }

        exec.value = exec.textContent;
    }

    function removeSuggestion() {
        if (cursor.nextSibling) cursor.parentNode.removeChild(cursor.nextSibling);
    }

    window._console = {
        log: function() {
            var l = arguments.length,
                i = 0;
            for (; i < l; i++) {
                log(stringify(arguments[i], true));
            }
        },
        dir: function() {
            var l = arguments.length,
                i = 0;
            for (; i < l; i++) {
                log(stringify(arguments[i]));
            }
        },
        props: function(obj) {
            var props = [],
                realObj;
            try {
                for (var p in obj) props.push(p);
            } catch (e) {}
            return props;
        }
    };

    function showHistory() {
        var h = getHistory();
        h.shift();
        return h.join("\n");
    }

    function getHistory() {
        var prefs = require("ko/prefs");
        return JSON.parse(prefs.getString("console_history", '[""]'));
    }

    function setHistory(history) {
        var prefs = require("ko/prefs");
        prefs.setString("console_history", JSON.stringify(history));
    }


    document.addEventListener ?
        window.addEventListener('message', function(event) {
        post(event.data);
    }, false) :
        window.attachEvent('onmessage', function() {
        post(window.event.data);
    });

    var exec = document.getElementById('exec'),
        form = exec.form || {},
        output = document.getElementById('output'),
        cursor = document.getElementById('exec'),
        bufferWindow = require("ko/windows").getMain(),
        history = getHistory(),
        pos = 0,
        body = document.getElementsByTagName('body')[0],
        logAfter = null,
        sse = null,
        lastCmd = null,
        codeCompleteTimer = null,
        keypressTimer = null,
        commands = {
            help: showhelp,
            // loadjs: loadScript, 
            history: showHistory,
            clear: function() {
                setTimeout(function() {
                    output.innerHTML = '';
                }, 10);
                return 'clearing...';
            },
            log: function() {
                ko.commands.doCommandAsync('cmd_helpViewErrorLog');
                return true;
            }
        },
        fakeInput = null;

    exec.parentNode.innerHTML = '<div autofocus id="exec" autocapitalize="off" spellcheck="false"><span id="cursor" spellcheck="false" autocapitalize="off" autocorrect="off"' + ' contenteditable></span></div>';
    exec = document.getElementById('exec');
    cursor = document.getElementById('cursor');

    // tweaks to interface to allow focus
    // if (!('autofocus' in document.createElement('input'))) exec.focus();
    cursor.focus();
    output.parentNode.tabIndex = 0;

    function whichKey(event) {
        var keys = {
            38: 1,
            40: 1,
            Up: 38,
            Down: 40,
            Enter: 10,
            'U+0009': 9,
            'U+0008': 8,
            'U+0190': 190,
            'Right': 39,
            // these two are ignored
            'U+0028': 57,
            'U+0026': 55
        };
        return event.which || event.keyCode;
    }

    function setCursorTo(str) {
        str = cleanse(str);
        exec.value = str;

        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
        document.execCommand('insertHTML', false, str);
        cursor.focus();
    };

    exec.onkeyup = function(event) {
        var which = whichKey(event);

        if (which != 9 && which != 16) {
            clearTimeout(codeCompleteTimer);
            codeCompleteTimer = setTimeout(function() {
                codeComplete(event);
            }, 50);
        }
    };

    // disabled for now
    cursor.__onpaste = function(event) {
        setTimeout(function() {
            // this causes the field to lose focus - I'll leave it here for a while, see how we get on.
            // what I need to do is rip out the contenteditable and replace it with something entirely different
            cursor.innerHTML = cursor.innerText;
            // setCursorTo(cursor.innerText);
        }, 10);
    };

    function findNode(list, node) {
        var pos = 0;
        for (var i = 0; i < list.length; i++) {
            if (list[i] == node) {
                return pos;
            }
            pos += list[i].nodeValue.length;
        }
        return -1;
    }

    var doubleTab = false;
    var lastWhich = -1;
    exec.onkeydown = function(event) {
        event = event || window.event;
        var keys = {
            38: 1,
            40: 1
        },
        wide = body.className == 'large',
        which = whichKey(event);
            
        if (lastWhich == which && which == 9)
            doubleTab = true;
        lastWhich = which;

        if (typeof which == 'string') which = which.replace(/\/U\+/, '\\u');
        if (keys[which]) {
            if (event.shiftKey) {
                changeView(event);
            } else if (!wide) { // history cycle
                if (window.getSelection) {
                    window.selObj = window.getSelection();
                    var selRange = selObj.getRangeAt(0);

                    cursorPos = findNode(selObj.anchorNode.parentNode.childNodes, selObj.anchorNode) + selObj.anchorOffset;
                    var value = exec.value,
                        firstnl = value.indexOf('\n'),
                        lastnl = value.lastIndexOf('\n');

                    if (firstnl !== -1) {
                        if (which == 38 && cursorPos > firstnl) {
                            return;
                        } else if (which == 40 && cursorPos < lastnl) {
                            return;
                        }
                    }
                }

                if (which == 38) { // cycle up
                    pos--;
                    if (pos < 0) pos = 0; //history.length - 1;
                } else if (which == 40) { // down
                    pos++;
                    if (pos >= history.length) pos = history.length; //0;
                }
                if (history[pos] != undefined && history[pos] !== '') {
                    removeSuggestion();
                    setCursorTo(history[pos])
                    return false;
                } else if (pos == history.length) {
                    removeSuggestion();
                    setCursorTo('');
                    return false;
                }
            }
        } else if ((which == 13 || which == 10) && event.shiftKey == false) { // enter (what about the other one)
            removeSuggestion();
            if (event.shiftKey == true || event.metaKey || event.ctrlKey || !wide) {
                var command = exec.textContent || exec.value;
                if (command.length) post(command);
                return false;
            }
        } else if (which == 9 && wide) {
            checkTab(event);
        } else if (event.shiftKey && event.metaKey && which == 8) {
            output.innerHTML = '';
        } else if ((which == 39 || which == 35) && ccPosition !== false) { // complete code
            completeCode();
        } else if (event.ctrlKey && which == 76) {
            output.innerHTML = '';
        } else { // try code completion
            if (ccPosition !== false && which == 9) {
                codeComplete(event); // cycles available completions
                return false;
            } else if (ccPosition !== false && cursor.nextSibling) {
                removeSuggestion();
            }
        }
    };

    function completeCode(focus) {
        var tmp = exec.textContent,
            l = tmp.length;
        removeSuggestion();

        cursor.innerHTML = tmp;
        ccPosition = false;

        cursor.focus();

        var range, selection;
        range = document.createRange(); //Create a range (a range is a like the selection but invisible)
        range.selectNodeContents(cursor); //Select the entire contents of the element with the range
        range.collapse(false); //collapse the range to the end point. false means collapse to end rather than the start
        selection = window.getSelection(); //get the selection object (allows you to change selection)
        selection.removeAllRanges(); //remove any selections already made
        selection.addRange(range); //make the range you have just created the visible selection
    }

    form.onsubmit = function(event) {
        event = event || window.event;
        event.preventDefault && event.preventDefault();
        removeSuggestion();
        post(exec.textContent || exec.value);
        return false;
    };

    document.onkeydown = function(event) {
        event = event || window.event;
        var which = event.which || event.keyCode;

        if (event.shiftKey && event.metaKey && which == 8) {
            output.innerHTML = '';
            cursor.focus();
        } else if (event.target == output.parentNode && which == 32) { // space
            output.parentNode.scrollTop += 5 + output.parentNode.offsetHeight * (event.shiftKey ? -1 : 1);
        }

        return changeView(event);
    };

    exec.onclick = function() {
        cursor.focus();
    }
    if (window.location.search) {
        post(decodeURIComponent(window.location.search.substr(1)));
    } else {
        post(':help', true);
    }

    window.onpopstate = function(event) {
        setCursorTo(event.state || '');
    };

    setTimeout(function() {
        window.scrollTo(0, 0);
        window.getSelection().removeAllRanges();
    }, 500);

    getProps('window'); // cache 

    try {
        if ( !! (localStorage.large * 1)) {
            document.body.className = 'large';
        }
    } catch (e) {}


    if (document.addEventListener) document.addEventListener('deviceready', function() {
            cursor.focus();
        }, false);

    // if (iOSMobile) {
    //   document.getElementById('footer').style.display = 'none';
    //   alert('hidden');
    // }

})(this);