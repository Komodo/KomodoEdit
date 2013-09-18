/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Populate with jslint defaults
var options = {
        rhino: true,
        forin: true,
        passfail: false
};
var includePath = "";
var includeBaseName = "fulljslint.js";
var i, arg, idx, argName, argValue, isJSHint = false;
var badArgs = false;
//print("arg len: " + arguments.length + "\n");
i = 0;
var args = typeof(arguments) != "undefined" ? arguments : scriptArgs;
while (i < args.length) {
    arg = args[i];
    //print("args[" + i + "]: " + arg);
    if (arg[0] == '-') {
        if (arg == "-I") {
            includePath = args[i + 1];
            i += 1;
            //print("includePath(1: " + includePath + "\n");
        } else if (arg == "--jshint") {
            isJSHint = true;
            includeBaseName = "jshint.js";
            //options.adsafe = false; // otherwise jshint gives weird "ADsafe" warnings
        } else if (arg.indexOf("--include") == 0) {
            idx = arg.indexOf("=");
            if (idx > -1) {
                includePath = arg.substr(idx + 1);
            } else {
                print("**** Unrecognized argument(1): " + arg);
                badArgs = true;
            }
        } else if (arg.indexOf("--jslint-basename") == 0) {
            idx = arg.indexOf("=");
            if (idx > -1) {
                includeBaseName = arg.substr(idx + 1);
            } else {
                print("**** Unrecognized argument(3): " + arg);
                badArgs = true;
            }
        } else if (arg.indexOf("--jshint-basename") == 0) {
            isJSHint = true;
            idx = arg.indexOf("=");
            if (idx > -1) {
                includeBaseName = arg.substr(idx + 1);
            } else {
                print("**** Unrecognized argument(4): " + arg);
                badArgs = true;
            }
        } else {
            print("**** Unrecognized argument(2): " + arg);
            badArgs = true;
        }
        if (includePath.length > 0
                && !/[\\\/]$/.test(includePath)) {
            includePath += "/";
        }
    } else {
        idx = arg.indexOf("=");
        if (idx == -1) {
            options[arg] = true;
            //print("Set options[" + arg + "] = true;\n");
        } else {
            var val = arg.substr(idx + 1);
            try {
                val = eval(val);
            } catch(ex) {
                //print("Failed to eval ('" + val + "'\n");
            }
            options[arg.substr(0, idx)] = val;
            //print("Set options[" + arg.substr(0, idx) + "] = " + val + "\n");
        }
    }
    i += 1;
}

if (!badArgs) {
    load(includePath + includeBaseName);
    const MAIN_OBJECT = isJSHint ? JSHINT : JSLINT;
    (function(options) {
        var input = "";
        var line, lines = [];
        while (true){
            line=readline();
            if (line === null) {
                break;
            }
            lines.push(line);
        }
        if (!lines.length) {
            return; // quit(1);
        }
        var input = lines.join("\n");
        var stoppingLineRE = /Stopping\.\s*\(\d+\%\s+scanned/;
        var printedHeader = false;
        if (!MAIN_OBJECT(input, options)) {
            print("++++JSLINT OUTPUT:");  // Handler expects this line.
            printedHeader = true;
            for (var i = 0; i < MAIN_OBJECT.errors.length; i += 1) {
                var e = MAIN_OBJECT.errors[i];
                if (e) {
                    if (stoppingLineRE.test(e.reason)) {
                        // Do nothing
                    } else {
                        print('jslint error: at line ' + (e.line) + ' column ' + (e.character) + ': ' + e.reason);
                        print(e.evidence || "");
                    }
                }
            }
        }
        try {
            var jsData = MAIN_OBJECT.data();
            var unusedVars = jsData.unused;
            if (unusedVars) {
                if (unusedVars.length && !printedHeader) {
                    print("++++JSLINT OUTPUT:");  // Handler expects this line.
                    printedHeader = true;
                }
                for each (var unusedVar in unusedVars) {
                        var msg = ('jslint error: at line '
                                   + unusedVar.line
                                   + ' column 1: unused var: '
                                   + unusedVar.name);
                        if (unusedVar['function']) {
                            var funcName = unusedVar['function'];
                            // jslint likes single-quotes
                            // jshint likes double-quotes
                            // settle on one so we can fold duplicate hits
                            funcName = funcName.replace(/^[\"\']/, '').replace(/[\"\']$/, '');
                            if (!/'?anonymous'?/.test(funcName)) {
                                msg += ", defined in '" + funcName + "'";
                            }
                        }
                        print(msg);
                        print("");
                    }
            }
        } catch(ex) {
            print("++++ Error getting unusedVars: " + ex);
        }
    })(options);
}
