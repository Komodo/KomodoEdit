/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

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

var log = ko.logging.getLogger("client_test02");
log.setLevel(ko.logging.LOG_DEBUG);
log.debug("are we here???");

// Hold our basic client in this var

var bclient = null;
var transportService = null;
var ostream = null;  //  stream to write to
var console;

var NS_OK = 0;

function Console() {
    try {
        this.widget = document.getElementById("client_test_output");
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

// The TCP server works mostly asynchronously.
function connect_to_server(host, port) {
    log.debug(">> connect_to_server");
    try {
        if (ostream) {
            ostream.close(NS_OK);
        }
        var transport = transportService.createTransport(null, 0,
                                                         host, port, null);
        if (!transport) {
            console.addStr("Can't connect to " + host + ":" + port);
            return null;
        }
        ostream = transport.openOutputStream(0,0,0);
        var raw_istream = transport.openInputStream(0,0,0);
        var istream = create_instance("@mozilla.org/scriptableinputstream;1",
                                      "nsIScriptableInputStream");
        istream.init(raw_istream);

        function expand(s) {
            var s1 = '';
            var re = /([\x00-\x1f])/;
            for (var i = 0; i < s.length; i++) {
                s1 += s[i].replace(re, "<" + RegExp['$1'].charCodeAt(0) + ">");
            }
            return s1;
        };

        function build_command_object(s) {
            /* Return a hash of
             * {
               cmd : command-name,
               -x : option,
               _data : <data if given>
               };
            */
            var cmd_hash = {};
            try {
                console.addStr("build_command_object -- working with " + s);
                s1 = s.replace(/^\s+/, '');
                // command match
                if (s1.match(/^([\w_]+)\s*/)) {
                    cmd_hash['cmd'] = RegExp.$1;
                    s2 = RegExp.leftContext;
                    console.addStr("qqq -- got cmd " + RegExp.$1);
                } else {
                    console.addStr("Can't find a property in cmd [" + s + "]");
                    return false;
                }
                while (s2.length > 0) {
                    if (s2.match(/^(-\w)\s*"((?:\\.|[^\"])*)"\s*/)) {
                        cmd_hash[RegExp.$1] = RegExp.$2;
                        console.addStr("qqq -- option [" + RegExp.$1 + "] = <<" + RegExp.$2 + ">>");
                        s2 = RegExp.leftContext;
                    } else if (s2.match(/^(-\w)\s*([\S]+)\s*/)) {
                        cmd_hash[RegExp.$1] = RegExp.$2;
                        console.addStr("qqq -- option [" + RegExp.$1 + "] = <<" + RegExp.$2 + ">>");
                        s2 = RegExp.leftContext;
                    } else {
                        console.addStr("qqq -- no options left in <<" + s2 + ">>");
                        break;
                    }
                }
                if (s2.match(/(.+)\s*$/)) {
                    cmd_hash._data = RegExp.$1;
                    console.addStr("qqq -- data <<" + RegExp.$1 + ">>");
                }
            } catch (ex) {
                log.debug(ex);
            }
            return cmd_hash;
        };
                

        var data_listener = {
            onStartRequest: function(request, context) {
                console.addStr("Got data_listener.onStartRequest");
            },
            onStopRequest: function(request, context, status){
                console.addStr("Got data_listener.onStopRequest");
                istream.close(NS_OK);
                ostream.close(NS_OK);
                ostream = null;
            },
            onDataAvailable: function(request, context, inputStream, offset, count){
                console.addStr("Got data_listener.onDataAvailable(" + count + ",[" + offset + "])");
                var buf = istream.read(count);
                var cbuf = expand(buf);
                log.debug("Read back raw -- [" + buf + "](" + buf.length + ")");
                var buf_e = escape(buf);
                log.debug("Read in escaped -- [" + buf_e + "](" + buf_e.length + ")");
                console.addStr("Received back <<" + buf + ">> (" + cbuf + ")");
                var cmd_obj = build_command_object(buf);
                if (cmd_obj) {
                    console.addStr("Got back a command-obj");
                }
            }
        };
        var pump = create_instance("@mozilla.org/network/input-stream-pump;1",
                                   "nsIInputStreamPump");
        pump.init(raw_istream, -1, -1, 0, 0, false);
        pump.asyncRead(data_listener, null);
        console.addStr("Connected to " + host + ":" + port);
        log.debug("<< connect_to_server");
        return transport;
    } catch(ex) {
        js_ph_dump_exception(ex);
        log.debug("connect.start failed: " + ex);
    }
    return null;
}

// And JS handlers

function clientTest_OnLoad()
{
    // alert("client_test02_OnLoad");
    log.debug("client_test02_OnLoad 2 {");
    try {
        transportService =
            get_service("@mozilla.org/network/socket-transport-service;1",
                        "nsISocketTransportService");
        console = new Console();
        console.addStr("Tester starting...");

        function handleKeyDown(e) {
            if (e.keyCode == 10 || e.keyCode == 13) {
                e.preventDefault();
                e.stopPropagation();
                client_test_send();
            }
        };
        document.getElementById("client_test_command").
            addEventListener('keydown', handleKeyDown, false);
        log.debug("} clientTest_OnLoad");
    } catch(ex) {
        js_ph_dump_exception(ex);
        console = null;
        log.debug("clientTest_OnLoad failed: " + ex);
    }
}

function clientTest_OnUnLoad()
{
    log.debug("client_test02_OnUnLoad {");
    if (bclient) {
        bclient.close(NS_OK);
    }
    bclient = null;
    log.debug("} client_test02_OnUnLoad");
}

function client_test_start()
{
    log.debug(">> BasicClient.start");
    try {
        var port;
        if (bclient) {
            log.debug("stopping old client");
            bclient.close(NS_OK);
        }
        log.debug(">> creating");
        try {
            port = parseInt(document.getElementById("client_test_port").value);
            log.debug(" Using port " + port);
        } catch(ex) {
            log.debug(ex);
        }
        if (!port) {
            port = 3335;
        }
        var host = document.getElementById("client_test_host").value;
        if (host.length == 0) {
            host = "localhost";
        }
        bclient = connect_to_server(host, port);
    } catch(ex) {
        js_ph_dump_exception(ex);
        log.debug("client.start failed: " + ex);
    }
    if (bclient) {
        var str = "Connected successfully to " + host + ":" + port;
        console.addStr(Str);
        log.debug(str);
    } else {
        var str = "Failed to connect to " + host + ":" + port;
        console.addStr(Str);
        log.debug(str);
    }
    log.debug("<< BasicClient.start");
}

function client_test_stop()
{
    log.debug(">> BasicClient.stop");
    if (bclient) {
        bclient.close(NS_OK);
        bclient = null;
    }
    log.debug("<< BasicClient.stop");
}

function client_test_send()
{
    try {
        var node = document.getElementById("client_test_command")
        var cmd = node.value;
        log.debug("Got command " + cmd);
        if (cmd[0] == "/") {
            try {
                eval(cmd.substr(1));
            } catch(ex) {
                log.debug("Awp - error evaling ["
                          + cmd
                          + "]: "
                          + ex.message);
            }
        } else if (ostream) {
            cmd2 = (cmd[0] == '*') ? unescape(cmd) : cmd;
            console.addStr("writing out [" + cmd2 + "]");
            ostream.write(cmd2, cmd2.length);
        } else {
            console.addStr("not connected to anyone");
        }
        node.select();
    } catch (ex) {
        log.debug("Awp - error " + ex);
    }
}
