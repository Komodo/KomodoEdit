/* Copyright (c) 2005-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* This is an internal test dialog to try out driving an embedded JavaScript
 * interpreter from JavaScript
 */

var log = ko.logging.getLogger("javascript_playhouse");
log.setLevel(ko.logging.LOG_DEBUG);
log.debug("are we here???");

function js_ph_dump_exception(ex) {
    for (p in ex) {
        log.error("==> ex[" + p + "] = " + ex[p] || "<undefined>");
    }
}

if ('arguments' in window) {
    try {
        var args = window.arguments;
        log.debug("Called with " + window.arguments.length + " args");
        var i;
        for (i = 0; i < window.arguments.length;  i++) {
            log.debug("args[" + i + "] = " + args[i]);
        }
    } catch (ex) {
        js_ph_dump_exception(ex);
    }
} else {
    log.debug("No args passed");
}
    
function jsPlayhouse_OnLoad()
{
    // alert("jsPlayhouse_OnLoad");
    log.debug("jsPlayhouse_OnLoad() 2 {");
    try {
        // Need this to set global ko.trace.get() or code won't work.
        var s = document.getElementById("code_buffer");
        s.value = "// Enter JavaScript code here\n";
    } catch (ex) {
        log.error("jsPlayhouse_OnLoad: error ");
        js_ph_dump_exception(ex);
    }
    log.debug("} jsPlayhouse_OnLoad");
}

function jsPlayhouse_OnUnload()
{
    log.debug("jsPlayhouse_OnUnload()");
}

function jsp_buffer_clear(node_id) {
    document.getElementById(node_id).value = "";
    log.debug("jsp_code_buffer_clear");
}

function jsp_run() {
    log.debug("jsp_run...");
    try {
        var str = document.getElementById("code_buffer").value;
        var output_element = document.getElementById("output_buffer");
        var res;
        if (str.length > 0) {
            res = eval(str);
            output_element.value = res;
        }
    } catch (ex) {
        log.debug("eval dumped exception");
        js_ph_dump_exception(ex);
    }
}

