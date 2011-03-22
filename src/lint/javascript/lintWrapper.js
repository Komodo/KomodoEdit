// Populate with jslint defaults
var options = {
        rhino: true,
        forin: true,
        passfail: false
};
var includePath = "";
var i, arg, idx, argName, argValue;
//print("arg len: " + arguments.length + "\n");
i = 0;
while (i < arguments.length) {
    arg = arguments[i];
    //print("arguments[" + i + "]: " + arg + "\n");
    if (arg[0] == '-' && includePath.length == 0) {
        if (arg == "-I") {
            includePath = arguments[i + 1];
            i += 1;
            //print("includePath(1: " + includePath + "\n");
        } else {
            idx = arg.indexOf("=");
            if (idx > -1) {
                argName = arg.substr(0, idx);
                if (argName == "--include") {
                    includePath = arg.substr(idx + 1);
                    //print("includePath(2): " + includePath + "\n");
                }
            }
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

load(includePath + "fulljslint.js");
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
    if (!JSLINT(input, options)) {
        print("++++JSLINT OUTPUT:");  // Handler expects this line.
        for (var i = 0; i < JSLINT.errors.length; i += 1) {
            var e = JSLINT.errors[i];
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

})(options);
