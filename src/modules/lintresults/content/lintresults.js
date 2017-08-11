(function() {
    const log       = require("ko/logging").getLogger("lintresults");
    const legacy    = require("ko/windows").getMain().ko;
    const {Cc, Ci}  = require("chrome");
    const prefs     = legacy.prefs;
    const views     = require("ko/views");
    const dynamicb  = require("ko/dynamic-button");
    const editor    = require("ko/editor");
    
    var button;

    this.init = function()
    {
        button = dynamicb.register("Syntax Checking Result", {
            icon: "circle-code",
            events: ["current_view_changed", "current_view_language_changed", "workspace_restored"],
            isEnabled: this.isEnabled.bind(this),
            menuitems: this.updateMenu.bind(this),
            command: function() { ko.commands.doCommandAsync("cmd_nextLintResult"); },
            tooltip: "Jump to next syntax checking result",
            classList: "ok",
            groupOrdinal: 100
        });
        button.setCounter(0);
    }
    
    var getXulView = function(view)
    {
        view = view || views.current().get();
        if ( ! view || view.getAttribute("type") != "editor") return;
        var $ = require("ko/dom");
        return $(view);
    }
    
    var setState = function(state)
    {
        var states = ["ok", "error", "warning", "info"];
        if (states.indexOf(state) == -1)
        {
            throw new Error("Invalid state: " + state);
        }
        
        for (let s of states)
            button.element().removeClass(s);
            
        button.element().addClass(state);
    }
    
    this.isEnabled = function ()
    {
        var view = views.current().get();
        if ( ! view || view.getAttribute("type") != "editor" || ! view.lintBuffer)
            return false;
        
        var checkingEnabled = view.koDoc.getEffectivePrefs().getBooleanPref("editUseLinting");
        if ( ! checkingEnabled)
            return false;
        
        return true;
    }
    
    this.update = function ()
    {
        var view = views.current().get();
        var xv = getXulView(view);
        if (!xv || !view.prefs)
            return;
        
        if ( ! this.isEnabled())
            return;
        
        var state = "ok";
        
        var lintError = view.lintBuffer.errorString;
        if (lintError) {
            button.setCounter("?");
            setState("error");
            return;
        }
    
        var lintResults = view.lintBuffer.lintResults;
        if (!lintResults) {
            button.setCounter(0);
            setState("ok");
        } else {
            var numErrors = lintResults.getNumErrors();
            var numWarnings = lintResults.getNumWarnings();
            var numTotal = numErrors + numWarnings;
            button.setCounter(numTotal);
            if (numErrors <= 0 && numWarnings <= 0) {
                setState("ok");
            } else {
                if (numErrors > 0) {
                    setState("error");
                } else {
                    setState("warning");
                }
            }
        }
    }
    
    this.updateMenu = function ()
    {
        var items = [
            {
                label: "Check Syntax Now",
                command: function() { legacy.commands.doCommandAsync("cmd_lintNow") }
            },
            {
                label: "Jump to Next Result",
                command: function() { legacy.commands.doCommandAsync("cmd_nextLintResult") }
            },
            {
                label: "Clear Results",
                command: function() { legacy.commands.doCommandAsync("cmd_lintClearResults") }
            }
        ];
        
        var view = views.current();
        var res = view.get("lintBuffer", "lintResults");
        
        if ( ! res)
            return items;
        
        var results = {}, numResults = {};
        res.getResults(results, numResults);
        
        if ( ! numResults.value)
            return items;
        
        items.push(null);
        
        var _items = [];
        for (let i=0;i<numResults.value;i++)
        {
            let result = results.value[i];
            let prefix = result.lineStart;
            if (result.lineEnd != result.lineStart)
                prefix += "-" + result.lineEnd;
            
            var severity = "INFO";
            if (result.severity == result.SEV_WARNING)
                severity = "WARNING";
            if (result.severity == result.SEV_ERROR)
                severity = "ERROR";
            
            _items.push({
                label: prefix + ":" + result.description,
                acceltext: severity,
                command: function(result)
                {
                    var editor = require("ko/editor");
                    editor.setCursor({line: result.lineStart, ch: result.columnStart});
                }.bind(this, result),
                _lintResult: result
            })
        }
        
        _items.sort(function(a, b)
        {
            if (a._lintResult.severity < b._lintResult.severity)
                return 1;
            if (a._lintResult.severity > b._lintResult.severity)
                return 1;
            return 0;
        });
        
        var maxLength = legacy.prefs.getLong("linter-popup-max-length", 10);
        if (_items.length > maxLength)
        {
            _items = _items.slice(0, maxLength);
            _items.push({
                label: "...",
                enabled: function () { return false }
            });
        }

        return items.concat(_items);
    }
    
    this.checkForNew = function()
    {
        var view = views.current();
        var res = view.get("lintBuffer", "lintResults");
        
        if ( ! res) {
            return;
        }
        
        var results = {}, numResults = {};
        res.getResults(results, numResults);
        
        if ( ! numResults.value) {
            return;
        }
        
        var lineNo = editor.getLineNumber();
        var topResult;
        for (let i=0;i<numResults.value;i++)
        {
            let result = results.value[i];
            if (result.lineStart == lineNo || result.lineEnd == lineNo)
            {
                if ( ! topResult || topResult.severity < result.severity)
                    topResult = result;
            }
        }
        
        if (topResult)
        {
            let prefix = "Ln: " + topResult.lineStart;
            if (topResult.lineEnd != topResult.lineStart)
                prefix += "-" + topResult.lineEnd;
            
            let severity = "INFO";
            if (topResult.severity == topResult.SEV_WARNING)
                severity = "WARNING";
            if (topResult.severity == topResult.SEV_ERROR)
                severity = "ERROR";
            
            require("notify/notify").send(
                prefix + ", " + topResult.description + " (" + severity + ")",
                "lint",
                {
                    command: function(topResult)
                    {
                        var editor = require("ko/editor");
                        editor.setCursor({line: topResult.lineStart, ch: topResult.columnStart});
                    }.bind(this, topResult),
                    panel: false
            });
        }
    }
    
    this.init();

}).apply(module.exports);
