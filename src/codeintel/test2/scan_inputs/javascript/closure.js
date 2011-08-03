/* Copyright (c) 2005-2006 ActiveState Software Inc.

/* Use this sample to explore editing JavaScript with Komodo. */

var systemInfo = {
    system: 1,

    /* Should interpret platform as a variable and not as a function
     * Why? Because it's a closure, ends with "}()"
     * @type string - Force type to be a string using the docTag
     */
    platform: function() {
            var ua = navigator.userAgent.toLowerCase();
            if (ua.indexOf("windows") != -1 || ua.indexOf("win32") != -1) {
                    return "windows";
            } else if (ua.indexOf("macintosh") != -1) {
                    return "mac";
            } else {
                    return false;
            }
    }(),

    version: 4.0
}

Event = {}
// Base should end up with the object contents in the return statement
Event.Base = function(event) {
    var listener = null;
    // Return an object
    return {
        theevent: event,
        EVENT_TYPE: 1,
        SCOPE: 2
    }
}();

