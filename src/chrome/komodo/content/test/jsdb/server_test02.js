/* -*- indent-tabs-mode: nil -*-  */

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

var log = ko.logging.getLogger("server_test02");
log.setLevel(ko.logging.LOG_DEBUG);
log.debug("are we here???");

var bserver = null;
var console;

function Console() {
    try {
        this.widget = document.getElementById("server_test_output");
        this.widget.value = "";
    } catch(ex2) {
        js_ph_dump_exception_2(ex);
    }
}

Console.prototype.addStr =
function(s) {
    if (!s || s.length == 0) {
        log.debug("addStr -- no string");
        return;
    }
    if (s[s.length - 1] != "\n") {
        s += "\n";
    }
    try {
        this.widget.value += s;
    } catch(ex2) {
        js_ph_dump_exception_2(ex);
    }
    len = this.widget.value.length
    this.widget.setSelectionRange(len, len);
};

function chomp(s) {
    if (!s || s.length == 0) {
        return s;
    }
    var idx = s.length - 1;
    var ch = s[idx];
    if (ch == "\r") {
        // OK
    } else if (ch == "\n") {
        if (idx > 0 && s[idx - 1] == "\r") {
            idx -= 1;
        }
    } else {
        return s;
    }
    return s.substr(0, idx);
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
        js_ph_dump_exception_2(ex);
    }
}

// The TCP server works mostly asynchronous.
function create_server(port, loopback_only, backlog) {
    log.debug(">> create_server");
    try {
        var socket = create_instance("@mozilla.org/network/server-socket;1",
                          "nsIServerSocket");
        socket.init(port, loopback_only, backlog);
        var listener = { 
            onSocketAccepted: accept_connection,
            onStopListening: end_connection

        };
        socket.asyncListen(listener);
        log.debug(">> waiting for connections on port " + port);
    } catch(ex) {
        js_ph_dump_exception(ex);
        log.debug("server.start failed: " + ex);
    }
    return socket;
}

function end_connection(socket, status)
{
    bserver = null;
    log.debug("onStopListening: " + status);
    
}

function accept_connection(server, client) {
    log.debug("onSocketAccepted");
    try {
        // var blocking = client.OPEN_BLOCKING;
        var blocking = 0;
        var out = client.openOutputStream(blocking, 0, 0);
        var ins = client.openInputStream(blocking, 0, 0);
        new InputPump(ins, out);
    } catch(ex) {
        log.debug("Error in onSocketAccepted:" + ex.message);
    }
}

function InputPump(input_stream, output_stream) { 
    var istream = create_instance("@mozilla.org/scriptableinputstream;1",
                       "nsIScriptableInputStream");
    istream.init(input_stream);
    this.input_stream = istream;
    this.output_stream = output_stream;
    this.buffer = "";
    var pump = create_instance("@mozilla.org/network/input-stream-pump;1",
                     "nsIInputStreamPump");
    pump.init(input_stream, -1, -1, 0, 0, true);
    pump.asyncRead(this, null);
}

// Buffer input until a full chunk is available.
InputPump.prototype = {
    onStartRequest: function(r, c) {},
    onStopRequest: function(r, c, s) {}
};

InputPump.prototype.onDataAvailable = 
function(r, c, stream, offset, count) {
    if (count > 0) {
        try {
            log.debug("About to read " + count + "bytes");
            // var inbuf = stream.read(count);
            var inbuf = this.input_stream.read(count);
            var inbuf_e = escape(inbuf)
            log.debug("Read in raw -- [" + inbuf + "](" + inbuf.length + ")");
            log.debug("Read in escaped -- [" + inbuf_e + "](" + inbuf_e.length + ")");
            var newbuf = inbuf[0].toUpperCase() + inbuf.substr(1);
            // log.debug("wrote out request " + newbuf);
            console.addStr("Read in [" + chomp(inbuf) + "], writing [" + newbuf + "<null byte>]");
            var null_byte = String.fromCharCode(0);
            // The null byte is redundant for JS -- it interprets it as
            // a string terminator.
            this.output_stream.write(newbuf + null_byte, newbuf.length + 1);
        } catch(ex) {
            js_ph_dump_exception(ex);
            log.debug("server.start failed: " + ex);
        }
    } else if (count == 0) {
        log.debug("onDataAvailable called with 0 chars");
    }
};

// And JS handlers

function serverTest_OnLoad()
{

    // alert("server_test02_OnLoad");
    log.debug("server_test02_OnLoad 2 {");

    function handleKeyDown(e) {
        if (e.keyCode == 10 || e.keyCode == 13) {
            e.preventDefault();
            e.stopPropagation();
            server_test_send();
        }
    };
    document.getElementById("server_test_command").
        addEventListener('keydown', handleKeyDown, false);
    console = new Console();
    console.addStr("Tester starting...");
    log.debug("} server_test02_OnLoad");
}

function serverTest_OnUnLoad()
{
    log.debug("server_test02_OnUnLoad {");
    if (bserver) {
        bserver.close();
    }
    bserver = null;
    log.debug("} server_test02_OnUnLoad");
}

function server_test_start()
{
    log.debug(">> BasicServer.start");
    var port;
    try {
        if (bserver) {
            log.debug("stopping old server");
            bserver.close();
        }
        log.debug(">> creating");
        port = 3335;
        var loopback_only = false;
        var backlog = -1;
        bserver = create_server(port, loopback_only, backlog);
    } catch(ex) {
        js_ph_dump_exception(ex);
        log.debug("server.start failed: " + ex);
    }
    var str = "Server started successfully. Listening to port " + port;
    console.addStr(Str);
    log.debug(str);
    log.debug("<< BasicServer.start");
}

function server_test_stop()
{
    log.debug(">> BasicServer.stop");
    if (bserver) {
        bserver.close();
        bserver = null;
    }
    log.debug("<< BasicServer.stop");
}

function server_test_send()
{
    try {
        var node = document.getElementById("server_test_command")
        var cmd = node.value;
        log.debug("Got command " + cmd);
        if (cmd[0] == "/") {
            try {
                var res = eval(cmd.substr(1));
                console.addStr(res);
            } catch(ex) {
                log.debug("Awp - error evaling ["
                          + cmd
                          + "]: "
                          + ex.message);
            }
        }
        node.select();
    } catch (ex) {
        log.debug("Awp - error " + ex);
    }
}
