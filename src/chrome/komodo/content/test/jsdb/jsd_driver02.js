/* -*- indent-tabs-mode: nil -*-  */

// Constants swiped from Venkman

const JSD_CTRID           = "@mozilla.org/js/jsd/debugger-service;1";
const jsdIDebuggerService = Components.interfaces.jsdIDebuggerService;
const jsdIExecutionHook   = Components.interfaces.jsdIExecutionHook;
const jsdIErrorHook       = Components.interfaces.jsdIErrorHook;
const jsdICallHook        = Components.interfaces.jsdICallHook;
const jsdIValue           = Components.interfaces.jsdIValue;
const jsdIProperty        = Components.interfaces.jsdIProperty;
const jsdIScript          = Components.interfaces.jsdIScript;
const jsdIStackFrame      = Components.interfaces.jsdIStackFrame;

const TYPE_VOID     = jsdIValue.TYPE_VOID;
const TYPE_NULL     = jsdIValue.TYPE_NULL;
const TYPE_BOOLEAN  = jsdIValue.TYPE_BOOLEAN;
const TYPE_INT      = jsdIValue.TYPE_INT;
const TYPE_DOUBLE   = jsdIValue.TYPE_DOUBLE;
const TYPE_STRING   = jsdIValue.TYPE_STRING;
const TYPE_FUNCTION = jsdIValue.TYPE_FUNCTION;
const TYPE_OBJECT   = jsdIValue.TYPE_OBJECT;

const PROP_ENUMERATE = jsdIProperty.FLAG_ENUMERATE;
const PROP_READONLY  = jsdIProperty.FLAG_READONLY;
const PROP_PERMANENT = jsdIProperty.FLAG_PERMANENT;
const PROP_ALIAS     = jsdIProperty.FLAG_ALIAS;
const PROP_ARGUMENT  = jsdIProperty.FLAG_ARGUMENT;
const PROP_VARIABLE  = jsdIProperty.FLAG_VARIABLE;
const PROP_EXCEPTION = jsdIProperty.FLAG_EXCEPTION;
const PROP_ERROR     = jsdIProperty.FLAG_ERROR;
const PROP_HINTED    = jsdIProperty.FLAG_HINTED;

const SCRIPT_NODEBUG   = jsdIScript.FLAG_DEBUG;
const SCRIPT_NOPROFILE = jsdIScript.FLAG_PROFILE;

const COLLECT_PROFILE_DATA  = jsdIDebuggerService.COLLECT_PROFILE_DATA;

const PCMAP_SOURCETEXT    = jsdIScript.PCMAP_SOURCETEXT;
const PCMAP_PRETTYPRINT   = jsdIScript.PCMAP_PRETTYPRINT;

const RETURN_CONTINUE   = jsdIExecutionHook.RETURN_CONTINUE;
const RETURN_CONT_THROW = jsdIExecutionHook.RETURN_CONTINUE_THROW;
const RETURN_VALUE      = jsdIExecutionHook.RETURN_RET_WITH_VAL;
const RETURN_THROW      = jsdIExecutionHook.RETURN_THROW_WITH_VAL;

const FTYPE_STD     = 0;
const FTYPE_SUMMARY = 1;
const FTYPE_ARRAY   = 2;

const BREAKPOINT_STOPNEVER   = 0;
const BREAKPOINT_STOPALWAYS  = 1;
const BREAKPOINT_STOPTRUE    = 2;
const BREAKPOINT_EARLYRETURN = 3;

// End venkman swipe

/*
function getLoggingMgr() {
    return {
        getLogger : function(s) {
            return {
                setLevel : function(x) {},
                    debug : function (s) { dump(s); }
            }
        }
    };
}
var ko.logging.LOG_DEBUG = 1;
dump = function(s) {};
*/

var log = ko.logging.getLogger("jsdriver");
log.setLevel(ko.logging.LOG_DEBUG);
log.debug("Loading jsd_driver02.js ...");

function Preferences() {
    this.trace = false;
}
prefs = new Preferences();

Preferences.prototype._do = function(str) {
    var reo = /^\s*(\w+)\s*(.*)\s*$/.exec(str);
    var cmd, args;
    if (reo) {
        cmd = reo[1];
        args = reo[2] || "";
        var fn = "_" + cmd;
        log.debug("About to call <<" + fn + "(" + args + ")");
        var res = (this[fn])(args);
        return res;
    } else {
        log.debug("Can't eval [" + str + "]");
        return "";
    }
};

Preferences.prototype._eval = function(args) {
    var res= eval(args);
    return res;
};

Preferences.prototype._fileinfo = function(args) {
    if (args.length == 0) {
        return "Usage: /fileinfo uri[:line-num]";
    }
    var reo = /^\s*(.*):(\d+)\s*$/.exec(args);
    var uri, line_num;
    var s;
    if (reo) {
        uri = reo[1];
        line_num = parseInt(reo[2], 10);
        s = "Checking file " + uri + ":\n";
        var url_obj = jsd_obj.loaded_urls[uri][0];
        if (!url_obj) {
            s += "Not found";
        } else {
            var scripts = url_obj.scripts;
            var fnum, lnum;
            for (line_range in url_obj.scripts) {
                var a = line_range.split(":");
                fnum = parseInt(a[0], 10);
                lnum = parseInt(a[1], 10);
                if (fnum <= line_num && line_num <= lnum) {
                    var line_range_obj = url_obj.scripts[line_range];
                    s += ("In lines "
                          + line_range
                          + ", function "
                          + line_range_obj.functionName
                          + "\n");
                    var code_lines = line_range_obj.codeLines;
                    for (var i = 0; i < code_lines.length; i++) {
                        s += (pad("" + (line_range_obj.start + i), ' ', 4)
                              + "  "
                              + code_lines[i]
                              + "\n");
                    }
                }
            }
        }
    } else {
        var url_obj = jsd_obj.loaded_urls[args][0];
        s = "Checking file " + args + ":\n";
        if (!url_obj) {
            s += "Not found";
        } else {
            for (line_range in url_obj.scripts) {
                var line_range_obj = url_obj.scripts[line_range];
                s += ("In lines "
                      + line_range
                      + ", function "
                      + line_range_obj.functionName
                      + "\n");
            }
        }
    }
    log.debug("Done fileinfo thing");
    return s;
};

Preferences.prototype._help = function _help(args) {
    log.debug("Commands: eval <str>, break <file:line>, breakCall <func>");
    return "";
};

Preferences.prototype._list = function _list(args) {
    var s = "";
    if (args.length == 0) {
        for (url in jsd_obj.loaded_urls) {
            s += url + "\n";
        }
    } else {
        var targ_lc = args.toLowerCase();
        for (url in jsd_obj.loaded_urls) {
            if (url.toLowerCase().indexOf(targ_lc) > -1) {
                s += url + "\n";
            }
        }
    }
    return s;
};

Preferences.prototype._load = function _load(args) {
    if (args.length == 0) {
        return "Usage: load uri";
    }
    if (!jsd_obj.subscript_loader) {
        jsd_obj.subscript_loader = get_service("@mozilla.org/moz/jssubscript-loader;1",
                                            "mozIJSSubScriptLoader");
        if (!jsd_obj.subscript_loader) {
            return "load: Couldn't get subscript loader service";
        }
    }
    jsd_obj.sub_loaded_url = canonicalize_uri(args);
    jsd_obj.subscript_loader.loadSubScript(args, null);
    return "ok";
}

Preferences.prototype._system = function _system(args) {
    if (args.length == 0) {
        return "Usage: system uri";
    }
    if (!jsd_obj.cmd_runner) {
        jsd_obj.cmd_runner = get_service("@activestate.com/koOs;1", "koIOs");
        if (!jsd_obj.cmd_runner) {
            return "load: Couldn't get system service";
        }
    }
    var res = jsd_obj.cmd_runner.system(args);
    return res;
}
    

// Generic JS routines to work with Mozilla, etc.

function js_ph_dump_exception_2(ex) {
    for (p in ex) {
        log.error("==> ex[" + p + "] = " + ex[p] || "<undefined>");
    }
}

function dumpall(label, obj) {
    log.debug("things in " + label + ":\n");
    for (o in obj) {
        log.debug("obj[" + o + "] = <<" + obj[o] + ">>\n");
    }
}
          

function js_ph_dump_exception(ex) {
    try {
        var s = "";
        if (ex.name) {
            s += ex.name + ": ";
        }
        s += ex.message;
        if (ex.fileName) {
            s += "\n" + ex.fileName;
            if (ex.lineNumber) {
                s += ":" + ex.lineNumber;
            }
        } else if (ex.lineNumber) {
            s += ", line " + ex.lineNumber;
        }
        if (s.length > 0) {
            log.error(s);
        } else {
            js_ph_dump_exception_2(ex);
        }
    } catch(ex2) {
        js_ph_dump_exception_2(ex2);
    }
}

// Put all the code for setting up the debugger service here.
// First put everything up in the global space, and then refactor

// Make sure there's only one service at a time
// JS won't let us return a value on some paths in strict mode.

function JS_DBGB() {
    jsds = get_service("@mozilla.org/js/jsd/debugger-service;1",
                    "jsdIDebuggerService");
    jsds.on();
    jsds.errorHook = {onError: jsd_fh_onErrorFn};
    jsds.scriptHook = {
        onScriptCreated : jsd_sh_onScriptCreated,
        onScriptDestroyed : jsd_sh_onScriptDestroyed
    };
    jsds.breakpointHook = null;
    jsds.debuggerHook = null;
    jsds.debugHook = null;
    jsds.interruptHook = {
        onExecute : null // too much -- jsd_eh_onExecute
    };
    jsds.throwHook = null;
    jsds.topLevelHook = jsds.functionHook = {
        onCall : null // jsd_fh_onCall // this is way too wordy
    };
    this.jsds = jsds;
    this.test = "this Test passed";
    this.loaded_urls = {};
    this.loaded_urls_count = 0;
    this.subscript_loader = null;
    this.sub_loaded_url = null;
    this.cmd_runner = null;
    log.debug("Setting this.jsds to [" + jsds+ "]");
}

function URL_info() {
    this.unloading_message = false;
    this.scripts = {};  // We use a hash to map "<startline>-<endline>" to a func
}

function Line_range(functionName, baseLineNumber, lineExtent, codeLines) {
    this.functionName = functionName;
    this.start = baseLineNumber;
    this.end = baseLineNumber + lineExtent;
    this.breakpoints = [];
    this.codeLines = codeLines;
}

var did_test = false;

function jsd_sh_onScriptCreated(jsdScript) {
    try {
        if (!did_test) {
            var things = [['jsd_obj', jsd_obj],
                          ['this', this]];
            for (var i in things) {
                var t = things[i];
                log.debug("Testing " + t[0] + " = " + t[1]);
                try {
                    log.debug(t[1].test);
                } catch(ex) {
                    log.debug("Test failed");
                }
            }
            did_test = true;
        }
        var url = jsdScript.fileName;
        var be_verbose = true; // true || (url == "chrome://komodo/content/views.js");
        if (be_verbose) {
            log.debug("jsd_sh_onScriptCreated " + url);
        }
        var url_obj;
        var baseLineNumber;
        var functionName = jsdScript.functionName;
        if (be_verbose) {
            if (functionName) {
                log.debug("got function name of " + functionName);
            }
        }
        var lineExtent;
        var line_range_str;
        var script_info;
        var is_new = false;
        if (url in jsd_obj.loaded_urls) {
            url_obj = jsd_obj.loaded_urls[url][0];
            // log.debug("and we have " + url_obj.unloading_message);
        } else {
            url_obj = new URL_info;
            jsd_obj.loaded_urls[url] = [url_obj, jsd_obj.loaded_urls_count];
            jsd_obj.loaded_urls_count += 1;
            is_new = true;
            // log.debug("First time seeing url " + url);
        }
        if (be_verbose) log.debug("got url obj");
        try {
            baseLineNumber = jsdScript.baseLineNumber;
            lineExtent = jsdScript.lineExtent;
            line_range_str = baseLineNumber + ":" + (baseLineNumber + lineExtent);
            if (be_verbose) {
                log.debug("line range of " + line_range_str);
            }
        } catch(ex) {
            log.debug(ex);
            baseLineNumber = 0;
            lineExtent = 0;
            line_range_str = "none";
        }
        if (be_verbose) log.debug("got line range");

        if (line_range_str in url_obj.scripts)  {
            script_info = url_obj.scripts[line_range_str];
            if (be_verbose) {
                log.debug("got script_info obj");
            }
        } else {
            if (be_verbose)
                log.debug("First time seeing line range " + line_range_str + " in url " + url);
            if (be_verbose) {
                log.debug("need a new range of " + line_range_str);
            }
            var functionSource;
            if (!jsdScript.isValid) {
                log.debug("This script isn't currently valid");
                functionSource = "";
            } else {
                var can_url = canonicalize_uri(url);
                if (jsd_obj.sub_loaded_url) {
                    log.debug("sub_loaded_url = ["
                              + jsd_obj.sub_loaded_url
                              + "], curr url = ["
                              + url
                              + "] ==> ["
                              + can_url
                              + "], ==: "
                              + (can_url == jsd_obj.sub_loaded_url ? "yes" : "no"));
                }
                if (jsd_obj.sub_loaded_url
                    && canonicalize_uri(url) == jsd_obj.sub_loaded_url) {
                    // get the source by reading the url
                    jsd_obj.sub_loaded_url = null;
                    if (true || be_verbose)
                        log.debug("Nulling jsd_obj.sub_loaded_url");
                    if (url.indexOf("file:/") == 0) {
                        var url2 = /^file:\/+(.*)/.exec(url)[1];
                        try {
                            if (!jsd_obj.cmd_runner) {
                                jsd_obj.cmd_runner = get_service("@activestate.com/koOs;1", "koIOs");
                            }
                            if (!jsd_obj.cmd_runner) {
                                functionSource = "";
                                log.debug("Couldn't get cmd runner");
                            } else {
                                var raw_functionSource = jsd_obj.cmd_runner.readfile(url2);
                                var raw_lines = raw_functionSource.split("\n");
                                var raw_lines_2 = raw_lines.slice(baseLineNumber - 1, baseLineNumber + lineExtent);
                                functionSource = raw_lines_2.join("\n");
                                if (be_verbose)
                                    log.debug("Working with functionSource = " + functionSource);
                            }
                        } catch(ex2) {
                            js_ph_dump_exception(ex2);
                            functionSource = "";
                        }
                    } else {
                        log.debug("Have to read an http url of " + url);
                        functionSource = "";
                    }
                } else {
                    try {
                        functionSource = jsdScript.functionSource;
                        log.debug("functionSource = <<" + functionSource + ">>");
                    } catch(ex2) {
                        functionSource = pad("", "?\n", lineExtent * 2);
                        js_ph_dump_exception(ex2);
                    }
                }
            }
            script_info = new Line_range(functionName, baseLineNumber,
                                         baseLineNumber + lineExtent,
                                         functionSource.split("\n"));
            url_obj.scripts[line_range_str] = script_info;
            is_new = true;
            if (be_verbose) {
                log.debug("got it");
            }
        }
        if (is_new) {
            log.debug("First time loading script " + url + "\n        lines " + line_range_str);
            if (functionName) {
                log.debug("   function " + functionName);
            }
            if (functionSource) {
                log.debug("   functionSource <<\n" + functionSource + "\n>>");
            }
        }
        if (be_verbose) {
            log.debug("finished jsd_sh_onScriptCreated.");
        }
    } catch(ex2) {
        js_ph_dump_exception(ex2);
    }
}

// The JS engine spends a lot of time loading and unloading
// scripts, so we can ignore most of these events.

function jsd_sh_onScriptDestroyed(jsdScript) {
    var be_verbose = (url == "chrome://komodo/content/views.js");
    try {
        var url = jsdScript.fileName;
        if (be_verbose) log.debug("jsd_sh_onScriptDestroyed " + url);
        if (url in jsd_obj.loaded_urls) {
            url_obj = jsd_obj.loaded_urls[url][0];
            if (! url_obj) {
                log.debug("Trying to unload " + url + ", but never loaded it");
            } else if (!url_obj.unloading_message) {
                log.debug("First time unloading script " + url);
                url_obj.unloading_message = true;
            }
        }
    } catch(ex2) {
        js_ph_dump_exception(ex2);
    }
    if (be_verbose) log.debug("finished jsd_sh_onScriptDestroyed.");
}

function testAndLog(pred, comment) {
    if (!pred) {
        log.debug(comment);
    }
    return pred;
}

// jsdStackFrame frame
// jsdIExecutionHookType type
// Object retval
function jsd_eh_onExecute(frame, type, rv) {
    var hookReturn = RETURN_CONTINUE;
    var fname;
    // if (!jsdb.initialized)
    // return hookReturn;
    if (!testAndLog(!("frames" in console),
                    "Execution hook called while stopped") ||
        frame.isNative ||
        !testAndLog(frame.script, "Execution hook called with no script") ||
        !testAndLog(!(frame.script.flags & SCRIPT_NODEBUG),
                    "Stopped in a script marked as don't debug") ||
        !testAndLog((isURLDBGP(fname = frame.script.fileName) ||
                     !isURLFiltered(fname)),
                    "stopped in a filtered URL")) {
        return hookReturn;
    }
    
    // Build the array of frames by walking the call stack
    var frames = new Array();
    var prevFrame = frame;
    while (prevFrame) {
        frames.push(prevFrame);
        prevFrame = prevFrame.callingFrame;
    }
    hookReturn = debugTrap(frames, type, rv);
    return hookReturn;
}

function debugTrap(frames, type, rv) {
    var frame = frames[0];
    var retcode = jsdIExecutionHook.RETURN_CONTINUE;
    
    // This is what venkman's debug_trap and perl-dbgp's debug_command do
    function get_src(frame) {
        if (!frame || !frame.script) {
            return "<unknown script>";
        }
        var s = frame.script.fileName ? "File " + frame.script.fileName : "<unknown>";
        s += "Line " + frame.line;
        return s;
    };
    
    switch (type) {
    case jsdIExecutionHook.TYPE_BREAKPOINT:
        var str = "Got a breakpoint in " + get_src(frame);            
        log.debug(str);
        break;
    case jsdIExecutionHook.TYPE_DEBUG_REQUESTED:
        log.debug("DEBUG_REQUESTED");
        break;
    case jsdIExecutionHook.TYPE_DEBUGGER_KEYWORD:
        log.debug("hit debugger keyword");
        break;
    case jsdIExecutionHook.TYPE_THROW:
        log.debug("handling a throw of some kind");
        retcode = jsdIExecutionHook.RETURN_CONTINUE_THROW;
        break;    
    case jsdIExecutionHook.TYPE_INTERRUPTED:
        if (!frame) {
            log.debug("onExecute -- debugTrap -- no frame");
            return retcode
        } else if (!frame.script) {
            log.debug("onExecute -- debugTrap -- no frame.script");
            return retcode
        }
        var fname = frame.script.fileName;
        var funcName = frame.script.functionName;
        var line = frame.line;
        var str2 = ("TYPE_INTERRUPTED: file "
                    + fname
                    + ", line #"
                    + line
                    + ", function "
                    + funcName || "<anonymous>"
                    + " frame # " + frames.length
                    );
        log.debug("onExecute -- debugTrap -- " + str2);
        var pc = frame.pc;
        var pc_line = frame.script.pcToLine(frame.pc, PCMAP_SOURCETEXT);
        if (pc_line != line) {
            log.debug("frame says line " + line + ", pc " + pc + " => " + pc_line);
        }
        break;
    default:
        log.debug("onExecute -- debugTrap -- got type " + type);
    }
    return retcode;

}

function pad(val, padChar, len) {
    while (val.length < len) {
        val = "" + padChar + val;
    }
    return val;
}


// jsdIStackFrame frame, jsdICallHookType type
function jsd_fh_onCall(frame, type) {
    if (type == jsdICallHook.TYPE_TOPLEVEL_START
        || type == jsdICallHook.TYPE_TOPLEVEL_END) {
        // We don't care about finishing a top-level script
        // log.debug("Doing a top-level end");
        return;
    } else {
        var s = ("onCall(file: " + (frame.script.fileName || "unknown")
                 + ", type " + type);
        if (type == jsdICallHook.TYPE_FUNCTION_CALL ||
            type == jsdICallHook.TYPE_FUNCTION_RETURN) {
            s += ", function " + (frame.functionName || "<anonymous>");
        } else {
            s += " top-level thing";
        }
        var script = frame.script;
        s += (", lines "
              + script.baseLineNumber
              + " - "
              + (script.baseLineNumber + script.lineExtent));
        var pc = frame.pc;
        if (pc > script.lineExtent* 100) {
            // log.debug("Skipping invalid pc of 0x" + pad(pc.toString(16), '0', 4));
        } else  {
            s += ", line " + frame.line;
        }
        log.debug(s);
    }
}
    
function jsd_fh_onErrorFn(message, fileName, line, pos,
                       flags, errnum, exc) {
    log.error("Error at file "
              + fileName
              + ", line "
              + line
              + " -- " + message);
    return true;
}

var jsd_obj;

// Some JS handlers

function jsdriver_OnLoad() {
    // alert("jsdriver_OnLoad");
    log.debug("jsdriver_OnLoad 2 {");
    try {
        function handleKeyDown(e) {
            if (e.keyCode == 10 || e.keyCode == 13) {
                e.preventDefault();
                e.stopPropagation();
                jsdriver_send();
            }
        };
        document.getElementById("jsdriver_command").
            addEventListener('keydown', handleKeyDown, false);
        log.debug("} jsdriver_OnLoad");
    } catch(ex) {
        js_ph_dump_exception(ex);
    }
}

function jsdriver_OnUnLoad() {
    log.debug("jsdriver_OnUnLoad {");
    jsdriver_stop();
    log.debug("} jsdriver_OnUnLoad");
}

function jsdriver_start() {
    log.debug(">> jsdriver.start");
    try {
        if (jsd_obj) {
            jsd_obj.jsds.on();
            return;
        }
        jsd_obj = new JS_DBGB();
    } catch(ex) {
        js_ph_dump_exception(ex);
        log.debug("jsdriver.start failed: " + ex);
    }
    log.debug("<< jsdriver.start");
}

function jsdriver_stop() {
    log.debug(">> jsdriver.stop");
    if (jsd_obj) {
        jsd_obj.jsds.off();
    }
    log.debug("<< jsdriver.stop");
}

function jsdriver_send() {
    try {
        var node = document.getElementById("jsdriver_command")
        var cmd = node.value;
        log.debug("Got command " + cmd);
        try {
            if (cmd[0] == "/") {
                cmd = cmd.substr(1);
            }
            var res = prefs._do(cmd);
            if (typeof res != "undefined") {
                log.debug("eval(" + cmd + ") => " + res);
            } else {
                log.debug("eval(" + cmd + ") => is undefined");
            }
        } catch(ex) {
            log.debug("Awp - error evaling ["
                      + cmd
                      + "]: " + ex);
        }
        node.select();
    } catch (ex2) {
        log.debug("Awp - error " + ex2);
    }
}

log.debug("Done loading jsd_driver02.js.");
