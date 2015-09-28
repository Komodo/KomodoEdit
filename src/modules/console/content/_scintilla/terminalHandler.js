window.terminalHandler = {};
(function()
{
    
    var scintilla;
    
    this.lastWritePosition = 0;
    
    this.setScintilla = (sc) =>
    {
        scintilla = sc;
    };
    
    this.clear = () => undefined;
    
    var listeners = {};
    
    this.on = (event, listener) =>
    {
        if ( ! (event in listeners))
            listeners[event] = [];
            
        listeners[event].push(listener);
    }
    
    var _fire = () =>
    {
        var args = Array.prototype.slice.call(arguments);
        var event = args.shift();
        
        if ( ! (event in listeners))
            return;
        
        for (listener of listeners[event])
            listener.apply(null, args);
    }
    
    this.onStdinData = (value) =>
    {
        value = value.trim();
        _fire("stdin", value);
    }
    
    this.addText = (text, marker) =>
    {
        var editor = require("ko/editor").editor({}, scintilla);
        
        var eventMask = scintilla.modEventMask;
        scintilla.modEventMask = 0;
        
        editor.goLineUp();
        editor.goLineEnd();
        editor.insert("\n" + text);
        editor.setCursor(editor.getLength());
        editor.gotoLine(editor.lineCount());
        
        scintilla.modEventMask = eventMask;
    }
    
    var _moveMarker = (startMarker, startLine, marker, lastLine) =>
    {
        if (startMarker & (1 << marker) && startLine < lastLine)
        {
            scintilla.markerDelete(startLine, marker);
            scintilla.markerAdd(lastLine, marker);
        }
    }
    
    // dev/null
    this.setLanguage = (language) => undefined;
    this.startSession = () => undefined;
    this.endSession = () => undefined;
    this.hookIO = (stdin, stdout, stderr, name) => undefined;
    this.setupDebuggerRedirectIOHandles = () => undefined;
    this.acquireLock = () => undefined;
    this.releaseLock = () => undefined;
    this.proxyAddText = (length, data, name) => undefined;
    this.setAddTextCallback = (callbackHandler) => undefined;
    this.stdin = {puts: this.onStdinData.bind(this)};
    this.stdout = null;
    this.stderr = null;
    this.active = true;
    this.stdinHandler = null;
    
}).apply(window.terminalHandler);