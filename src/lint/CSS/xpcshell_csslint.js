
/**
 * XPCShell linter.
 *
 * Recieves one file path on the command line and parses that using the Mozilla
 * CSS parser. Results are then output in a json array.
 */

var linter_entries = [];

function KoCSSLinter() {
}

KoCSSLinter.prototype.readlines = function(filepath)
{
    try {
        var file = Components.classes["@mozilla.org/file/local;1"].
               createInstance(Components.interfaces.nsILocalFile);
        file.initWithPath(filepath);
        var fstream = Components.classes["@mozilla.org/network/file-input-stream;1"].
                      createInstance(Components.interfaces.nsIFileInputStream);
        var cstream = Components.classes["@mozilla.org/intl/converter-input-stream;1"].
                      createInstance(Components.interfaces.nsIConverterInputStream);
        fstream.init(file, -1, 0, 0);
        cstream.init(fstream, "UTF-8", 0, 0); // you can use another encoding here if you wish
        // Read the string.
        var contents = "";
        let (str = {}) {
          let read = 0;
          do {
            read = cstream.readString(0xFFFFFFFF, str);
            contents += str.value;
          } while (read != 0);
        }
        cstream.close(); // this closes fstream
        // Split into lines.
        this.lines = contents.split(/\r\n|\n/);
    } catch (ex) {
        this.lines = [];
    }
}

KoCSSLinter.prototype.parse = function(filepath)
{
    // Register ourself with the console service.
    let consoleSvc = Components.classes["@mozilla.org/consoleservice;1"].
            getService(Components.interfaces.nsIConsoleService);
    consoleSvc.registerListener(this);

    this.readlines(filepath);

    // Start parsing the css file.
    let parser = Components.classes["@activestate.com/koCSSParser;1"].createInstance(Components.interfaces.koICSSParser);
    parser.parseFile(filepath);
}

/**
 * @param nsIConsoleMessage message
 */
KoCSSLinter.prototype.observe = function(message)
{
    message = message.QueryInterface(Components.interfaces.nsIScriptError);

    //dump(message.errorMessage + "  " +
    //     message.sourceName + "  " +
    //     message.sourceLine + "  " +
    //     message.lineNumber + "  " +
    //     message.flags +
    //     "\n");

    let desc = message.errorMessage;
    if (desc.endsWith(" Declaration dropped.")) {
        // We are just a syntax checker - not actually applying.
        desc = desc.substr(0, desc.length - (" Declaration dropped.".length));
    }

    let severity = message.flags;
    if (severity & Components.interfaces.nsIScriptError.errorFlag) {
        severity = Components.interfaces.koILintResult.SEV_ERROR;
    } else {
        severity = Components.interfaces.koILintResult.SEV_WARNING;
    }

    // Guess the end of the error by finding a word boundary.
    var columnStart = message.columnNumber;
    var line = this.lines[message.lineNumber-1].substr(columnStart-1);
    var columnEnd = line.length;
    var linesplit = line.split(/\b/);
    if (linesplit.length > 1) {
        columnEnd = columnStart + linesplit[0].length;
        if (columnEnd <= columnStart) {
            columnEnd = line.length;
        }
    }

    // Store the lint entry.
    let entry = {
        'description': desc,
        'lineStart': message.lineNumber,
        'lineEnd': message.lineNumber,
        'columnStart': columnStart,
        'columnEnd': columnEnd,
        'severity': severity,
    };
    linter_entries.push(entry);
}

// Kick off the parse.
var k = new KoCSSLinter();
k.parse(arguments[0]);

// Process pending Mozilla events in order to receive the observer
// notifications, based on Mozilla xpcshell test class here:
// http://mxr.mozilla.org/mozilla-central/source/testing/xpcshell/head.js#75
var currentThread = Components.classes["@mozilla.org/thread-manager;1"]
                    .getService().currentThread;
while (currentThread.hasPendingEvents()) {
    currentThread.processNextEvent(true);
}

// Write out all lint entries into a json string.
dump(JSON.stringify(linter_entries) + "\n");
