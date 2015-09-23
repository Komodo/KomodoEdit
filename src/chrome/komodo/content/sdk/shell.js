/**
 * @module shell
 */
(function() {
    
    const {Cc, Ci, Cu}  = require("chrome");
    const prefs         = ko.prefs;

    const log           = require("ko/logging").getLogger("ko-shell");
    //log.setLevel(require("ko/logging").LOG_DEBUG);
    
    /**
     * Get the current working directory, based on the places pane
     * 
     * @returns {String}
     */
    this.getCwd = function()
    {
        // Detect current working directory
        var partSvc = Cc["@activestate.com/koPartService;1"].getService(Ci.koIPartService);
        var cwd = ko.uriparse.URIToPath(ko.places.getDirectory());
        if (partSvc.currentProject)
            cwd = partSvc.currentProject.liveDirectory;
            
        return cwd;
    }
    
    /**
     * Get the configured environment variables
     * 
     * @returns {Object}
     */
    this.getEnv = function()
    {   
        var env = {};
        var koEnviron = Cc["@activestate.com/koUserEnviron;1"].getService();
        var keys = koEnviron.keys();
        for (let key of keys)
            env[key] = koEnviron.get(key);
        
        return env;
    }
    
    /**
     * Look up the location of the given executable
     * 
     * @param   {String} command
     * @param   {Object} env    
     * 
     * @returns {String|Boolean}
     */
    this.lookup = function(command, env)
    {
        var ioFile = require("sdk/io/file");
        
        var isExecutable = function(str)
        {
            try
            {
                let file = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsILocalFile);
                file.initWithPath(str);
                
                if (file.isFile() && file.isExecutable())
                    return true;
            }
            catch (e) {}
            
            return false;
        }
        
        if (isExecutable(command))
            return command;
        
        env = env || this.getEnv();
        let commands = [command];
        if (require("sdk/system").platform == "WINNT" && "PATHEXT" in env)
        {
            var pathExt = env.PATHEXT.split(/;|:/);
            for (let ext of pathExt)
                commands.push(command + ext);
        }
        
        var paths = (env.PATH || "").split(/;|:/);
        for (let path of paths)
        {
            for (let cmd of commands)
            {
                let _path = ioFile.join(path, cmd);
                if (isExecutable(_path))
                    return _path;
            }
        }
        
        return false;
    }
    
    /**
     * Run a shell command
     * 
     * @param   {String} binary     Executable
     * @param   {Array} args  
     * @param   {Object} opts       cwd, env, ..
     * 
     * @returns {Process}
     */
    this.run = function(binary, args, opts)
    {
        var _opts = {
            cwd: this.getCwd(),
            env: this.getEnv()
        };
        
        var _ = require("contrib/underscore");
        _opts = _.extend(_opts, opts);
        
        binary = this.lookup(binary) || binary;
        
        var proc = require("sdk/system/child_process");
        var process = proc.spawn(binary, args, _opts);
        
        return process;
    }
    
    /**
     * Alias for run
     */
    this.spawn = this.run;
    
    /**
     * Execute an encoded command
     * 
     * @param   {String} command 
     * @param   {Object} opts           Can contain: runIn: hud to show the output in a hud window
     * @param   {Function} callback
     * 
     * @returns {Process}
     */
    this.exec = function(command, opts, callback)
    {
        var _opts = {
            cwd: this.getCwd(),
            env: this.getEnv()
        };
        
        var _ = require("contrib/underscore");
        _opts = _.extend(_opts, opts);
        
        // Prepare platform command
        var platform = require("sdk/system").platform
        var file, cmdArgs;
        
        if (opts.argv)
        {
            file = command;
            cmdArgs = opts.argv;
        }
        else
        {
            if (platform.indexOf('win') === 0)
            {
                file = 'C:\\Windows\\System32\\cmd.exe';
                cmdArgs = ['/s', '/c', command];
            }
            else
            {
                file = '/bin/sh';
                cmdArgs = ['-c', command];
            }
        }
      
        // Undocumented option from node being able to specify shell
        if (_opts && _opts.shell)
            file = _opts.shell;
      
        var proc = require("sdk/system/child_process");
        var process = proc.execFile(file, cmdArgs, _opts, callback);
        
        if ("runIn" in opts && opts.runIn == "hud")
            showOutputInHud(process, opts.readable || command);
        
        return process;
    }
    
    /**
     * Show output for the given process in a HUD window
     * 
     * @param   {Process} process
     * @param   {String} command        The (humanly readable) command that was used to start this process
     */
    var showOutputInHud = function(process, command)
    {
        var running = true;
        
        // Create the output panel
        var $ = require("ko/dom");
        var hud =
        $($.create("panel", {class: "hud shell-output", noautohide: true, width: 500, level: "floating"},
            $.create("textbox", {multiline: true, rows: 15, readonly: true, style: "max-width: 490px"})
                    ("button", {label: "stop"})
        ).toString());
        
        // Append command name if given
        if (command)
            hud.prepend($.create("label", {value: "$ " + command}).toString());
        
        // Append to DOM
        $("#komodoMainPopupSet").append(hud);
        
        // Center the panel on the editor
        var elem = hud.element();
        var bo = document.getElementById('komodo-editor-vbox');
        bo = bo ? bo.boxObject : document.documentElement.boxObject;
        var left = (bo.x + (bo.width / 2)) - (elem.width / 2);
        elem.openPopup(undefined, undefined, left, 100);
        
        // Show stdout and stderr data the same way, leave to user to interpret
        var onData = function(data)
        {
            var textbox = hud.find("textbox");
            var elem = document.getAnonymousNodes(textbox.element())[0].childNodes[0];
            var isAtBottom = elem.scrollTop == elem.scrollTopMax;
            
            textbox.value(textbox.value() + data);
            
            if (isAtBottom)
                elem.scrollTop = elem.scrollTopMax;
            
            focus();
        }
        
        var hudElem = hud.element();
        var textboxElem = hud.find("textbox");
        
        // XUL panel focus is buggy as hell, so we have to get crafty
        var focus = function(times=0, timer = 10)
        {
            window.focus();
            hudElem.focus();
            textboxElem.focus();
    
            if (document.activeElement.nodeName != "html:input")
            {
                log.debug("Can't grab focus, retrying");
                timer = 100;
            }
    
            if (times < 10)
            {
                window.setTimeout(focus.bind(this, ++times), timer);
            }
        }
        
        process.stdout.on('data', onData);
        process.stderr.on('data', onData);
        
        // Command finished executing
        process.on('close', function (code, signal)
        {
            running = false;
            hud.removeAttr("noautohide");
            hud.find("button").attr("label", "close");
            
            // Indicate that something went wrong if status code isnt 0
            if (code != 0)
            {
                var textbox = hud.find("textbox");
                textbox.value(textbox.value() + "\n" + "FAIL: " + (code || signal));
            }
            
            focus();
        });
        
        // Stop process or hide panel when button is clicked
        hud.find("button").on("click", function()
        {
            if (running)
                process.kill("SIGTERM");
            else
                hud.element().hidePopup();
        });

        // Destroy panel and force focus on editor when its hidden
        var showing = true;
        hud.on("popuphidden", function(e)
        {
            showing = false;
            hud.remove();
            
            var view = ko.views.manager.currentView;
            if (view && view.getAttribute("type") != "editor")
                view.scintilla.focus();
        });
        
        // We need to manually handle hiding the panel because XUL panels are a
        // buggy mess
        // Hide when a mouse click is made outside the panel
        var hideOnClick = function(e)
        {
            if (running) return; // Unless the command is still running
            $("#komodo_main").off(hideOnClick);
            if ( ! showing) return;
            
            var target = e.originalTarget || e.target;
            while((target=target.parentNode) && target !== hud.element() && target.nodeName != "dialog");
            if ( ! target) hud.element().hidePopup();
        };
        $("#komodo_main").on("click", hideOnClick);
        
        // Hide panel when escape is pressed
        hud.on("keydown", function(e)
        {
            if (running || e.keyCode != window.KeyEvent.DOM_VK_ESCAPE) return;
            hud.element().hidePopup();
        });
    }
    this._showOutputInHud = showOutputInHud;
    
    /**
     * Parses table information into a JS array
     *
     * Example:
     *
     * FOO      BAR
     * val1a    val2a
     * val1b    val2a
     *
     * Results in:
     *
     * [
     *   {FOO: val1a, BAR: val2a},
     *   {FOO: val1b, BAR: val2b}
     * ]
     * 
     * @returns {Array}
     */
    this.parseTable = function(output)
    {
        var lines = output.split(/\n|\r/);
        var headers = false, result = [];
        for (let line of lines)
        {
            if ( ! line.trim().length) continue;
            if ( ! headers)
            {
                let linebits = line.split(/\s{2,}/);
                for (let entry of linebits)
                {
                    if ( ! entry.match(/^[A-Z ]+$/))
                        break;
                    
                    headers = headers || [];
                    
                    var rx = new RegExp(entry + "\\s+");
                    var match = line.match(rx);
                    var iof = line.indexOf(entry);
                    
                    headers.push({
                        name: entry.trim(),
                        indexStart: iof,
                        length: match ? match.pop().length : undefined
                    })
                }
            }
            else
            {
                let entry = {};
                for (let header of headers)
                {
                    entry[header.name] = line.substr(header.indexStart, header.length).trim();
                }
                result.push(entry);
            }
        }
        
        return result;
    }

}).apply(module.exports)