window.widget = {};
(function()
{
    const _window   = require("ko/windows").getMain();
    const ko        = _window.ko;
    const log       = require("ko/logging").getLogger("runinline")
    const $         = require("ko/dom");
    const sdkConsole= require("ko/console");
    
    var terminalView, scimoz;
    
    var init = () =>
    {
        terminalView = $("#console-view", window).element();
        scimoz = terminalView.scintilla;
        
        terminalView.scintilla.symbolMargin = true;
        terminalView.init();
        terminalView.initWithTerminal(terminalHandler);
        terminalView.startSession();
        
        terminalHandler.lastWritePosition = scimoz.length;
        terminalView.setPromptMarker(ko.markers.MARKNUM_STDIN_PROMPT);
        
        terminalHandler.on("stdin", onStdin.bind(this));
    }
    
    var onStdin = (data) =>
    {
        try
        {
            console.log(data);
            var result = _window.eval(data);
        }
        catch (e)
        {
            result = e.message;
        }
        
        terminalHandler.addText(result);
    }
    
    addEventListener("load", init.bind(this), false);
    
}).apply(window.widget);