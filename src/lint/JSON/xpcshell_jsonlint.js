/**
 * XPCShell linter.
 *
 * Recieves one file path on the command line and parses that using the Mozilla
 * JSON parser. Results are then output in a json array.
 */

var linter_entries = [];

function KoJSONLinter() {}

KoJSONLinter.prototype.parse = function(filepath)
{
    // Register ourself with the console service.
    let consoleSvc = Components.classes["@mozilla.org/consoleservice;1"].
            getService(Components.interfaces.nsIConsoleService);
    consoleSvc.registerListener(this);
    
    var contents = "";
    var lines = [];
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
        let (str = {}) {
          let read = 0;
          do {
            read = cstream.readString(0xFFFFFFFF, str);
            contents += str.value;
          } while (read != 0);
        }
        cstream.close(); // this closes fstream
        lines = contents.split(/\r\n|\n/);
    } catch (ex) {
        // Ignore.
    }

    // Start parsing the css file.
    let json = Components.classes["@mozilla.org/dom/json;1"].createInstance(Components.interfaces.nsIJSON);
    try {
        json.decode(contents);
    } catch (ex) {
        var regex = /^JSON.parse: (.+) at line (\d+) column (\d+)/;
        var details = regex.exec(ex.message);
        
        // Store the lint entry.
        let entry = {
            'description': details[1],
            'lineStart': parseInt(details[2], 10),
            'lineEnd': parseInt(details[2], 10),
            'columnStart': parseInt(details[3], 10),
            'columnEnd': lines[parseInt(details[2]) - 1].length,
            'severity': Components.interfaces.koILintResult.SEV_ERROR,
        };
        linter_entries.push(entry);
    }
}

// Kick off the parse.
var k = new KoJSONLinter();
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
