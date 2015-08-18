/**
 * @module console
 */
(function() {

    var addObs = false;
    if (typeof(require) === "function")
    {
        // This is being loaded as a jetpack module
        var { Cc, Ci, Cu } = require("chrome");
        module.exports = this;
    }
    else
    {
        // This is being loaded in a JS component or a JS module
        var { classes: Cc, interfaces: Ci, utils: Cu } = Components;
        this.EXPORTED_SYMBOLS = ["console"];
        this.console = this;
        addObs = true;
    }

    Cu.import("resource://gre/modules/Services.jsm");
    
    const {ConsoleAPI}  = Cu.import("resource://gre/modules/devtools/Console.jsm");
    const console       = new ConsoleAPI({innerID: "koConsoleWrapper"});
    const {logging}     = Cu.import("chrome://komodo/content/library/logging.js", {});
    const log           = logging.getLogger("console");
    const obs           = Cc["@mozilla.org/observer-service;1"].getService(Ci.nsIObserverService);
    log.setLevel(logging.LOG_DEBUG);

    /**
     * Alias for console.log
     */
    this.debug = console.debug;
    
    /**
     * Output an error, see [https://developer.mozilla.org/en-US/docs/Web/API/Console/error]
     */
    this.error = console.error;
    
    /**
     * Alias for console.error
     */
    this.exception = console.exception;
    
    /**
     * Output informative data, see [https://developer.mozilla.org/en-US/docs/Web/API/Console/info]
     */
    this.info = console.info;
    
    /**
     * Start a timer, see [https://developer.mozilla.org/en-US/docs/Web/API/Console/time]
     */
    this.time = console.time;
    
    /**
     * End a timer, see [https://developer.mozilla.org/en-US/docs/Web/API/Console/timeEnd]
     */
    this.timeEnd = console.timeEnd;
    
    /**
     * Outputs a stack trace
     */
    this.trace = console.trace;
    
    /**
     * Outputs a warning message, see [https://developer.mozilla.org/en-US/docs/Web/API/Console/warn]
     */
    this.warn = console.warn;

    if (addObs)
    {
        obs.addObserver(
        {
            observe: function(aMessage, aTopic)
            {
                aMessage = aMessage.wrappedJSObject;
                
                // This causes logs not to work from a component context
                //if (aMessage.innerID != console.innerID)
                //    return;
    
                var args = aMessage.arguments;
                var data = args.map(function(arg)
                {
                    return stringify(arg, true);
                }).join(" ");
                
                var details = null;
                var severity = Ci.koINotification.SEVERITY_INFO;
                switch (aMessage.level)
                {
                    case "info":
                        log.info(data);
                        break;
                    case "warn":
                        log.warn(data);
                        severity = Ci.koINotification.SEVERITY_WARNING;
                        break;
                    case "error":
                        log.error(data);
                        severity = Ci.koINotification.SEVERITY_ERROR;
                        break;
                    case "exception":
                        log.exception(data);
                        severity = Ci.koINotification.SEVERITY_ERROR;
                        break;
                    default:
                        if (aMessage.level == "timeEnd")
                            details = "'" + aMessage.timer.name + "' " + aMessage.timer.duration + "ms";
                        if (aMessage.level == "time")
                            details = "'" + aMessage.timer.name + "' @ " + (new Date());
                        if (aMessage.level == "trace")
                            details = "trace" + "\n" + formatTrace(aMessage.stacktrace);
                        log.debug(details || data);
                        break;
                }
                
                try
                {
                    ko.notifications.add("console." + aMessage.level + ": " + data, ["console", aMessage.level], Date.now(),
                         {severity: severity, notify: true, details: details});
                }
                catch (e)
                {
                    log.exception(e);
                }
            }
        }, "console-api-log-event", false);
    }

    /**
     * Outputs general logging information, see [https://developer.mozilla.org/en-US/docs/Web/API/Console/log]
     */
    this.log = () =>
    {
        // Todo: Localize and add documentation link
        ko.dialogs.alert(
            "Console messages are send to the Notifications pane, stdout and \
            Komodo's pystderr.log, for more information please check our documentation.",
            null, "Info on Console Messages", "consoleMessages"
        );

        return console.log.apply(console, arguments);
    }

    /**
     * A single line stringification of an object designed for use by humans
     *
     * @param {any} aThing
     *        The object to be stringified
     * @param {boolean} aAllowNewLines
     * @return {string}
     *        A single line representation of aThing, which will generally be at
     *        most 80 chars long
     *
     * Taken from resource://gre/modules/devtools/Console.jsm
     */
    var stringify = (aThing, aAllowNewLines) =>
    {
        if (aThing === undefined)
            return "undefined";

        if (aThing === null)
            return "null";

        if (typeof aThing == "object")
        {
            let type = getCtorName(aThing);
            if (aThing instanceof Ci.nsIDOMNode && aThing.tagName)
                return debugElement(aThing);

            type = (type == "Object" ? "" : type + " ");
            let json;
            try
            {
                json = JSON.stringify(aThing);
            }
            catch (ex) // Can't use a real ellipsis here, because cmd.exe isn't unicode-enabled
            {
                json = "{" + Object.keys(aThing).join(":..,") + ":.., " + "}";
            }
            return type + json;
        }

        if (typeof aThing == "function")
            return aThing.toString().replace(/\s+/g, " ");

        let str = aThing.toString();
        if ( ! aAllowNewLines)
            str = str.replace(/\n/g, "|");

        return str;
    }
    this._stringify = stringify;
    
    /**
     * Utility to extract the constructor name of an object.
     * Object.toString gives: "[object ?????]"; we want the "?????".
     *
     * @param {object} aObj
     *        The object from which to extract the constructor name
     * @return {string}
     *        The constructor name
     *
     * Taken from resource://gre/modules/devtools/Console.jsm
     */
    function getCtorName(aObj) {
        if (aObj === null)
        {
            return "null";
        }
        if (aObj === undefined)
        {
            return "undefined";
        }
        if (aObj.constructor && aObj.constructor.name)
        {
            return aObj.constructor.name;
        }
        
        // If that fails, use Objects toString which sometimes gives something
        // better than 'Object', and at least defaults to Object if nothing better
        return Object.prototype.toString.call(aObj).slice(8, -1);
    }
    this._getCtorName = getCtorName;

    /**
     * Take the output from parseStack() and convert it to nice readable
     * output
     *
     * @param {object[]} aTrace
     *        Array of trace objects as created by parseStack()
     * @return {string} Multi line report of the stack trace
     *
     * Taken from resource://gre/modules/devtools/Console.jsm
     */
    var formatTrace = (aTrace) =>
    {
        let reply = "";
        aTrace.forEach(function(frame) {
            reply += fmt(frame.filename, 20, 20, {
                truncate: "start"
            }) + " " +
                fmt(frame.lineNumber, 5, 5) + " " +
                fmt(frame.functionName, 75, 0, {
                truncate: "center"
            }) + "\n";
        });
        return reply;
    }
    this._formatTrace = formatTrace;

    /**
     * String utility to ensure that strings are a specified length. Strings
     * that are too long are truncated to the max length and the last char is
     * set to "_". Strings that are too short are padded with spaces.
     *
     * @param {string} aStr
     *        The string to format to the correct length
     * @param {number} aMaxLen
     *        The maximum allowed length of the returned string
     * @param {number} aMinLen (optional)
     *        The minimum allowed length of the returned string. If undefined,
     *        then aMaxLen will be used
     * @param {object} aOptions (optional)
     *        An object allowing format customization. Allowed customizations:
     *          'truncate' - can take the value "start" to truncate strings from
     *             the start as opposed to the end or "center" to truncate
     *             strings in the center.
     *          'align' - takes an alignment when padding is needed for MinLen,
     *             either "start" or "end".  Defaults to "start".
     * @return {string}
     *        The original string formatted to fit the specified lengths
     *
     * Taken from resource://gre/modules/devtools/Console.jsm
     */
    var fmt = (aStr, aMaxLen, aMinLen, aOptions) =>
    {
        if (aMinLen == null) {
            aMinLen = aMaxLen;
        }
        if (aStr == null) {
            aStr = "";
        }
        if (aStr.length > aMaxLen) {
            if (aOptions && aOptions.truncate == "start") {
                return "_" + aStr.substring(aStr.length - aMaxLen + 1);
            } else if (aOptions && aOptions.truncate == "center") {
                let start = aStr.substring(0, (aMaxLen / 2));

                let end = aStr.substring((aStr.length - (aMaxLen / 2)) + 1);
                return start + "_" + end;
            } else {
                return aStr.substring(0, aMaxLen - 1) + "_";
            }
        }
        if (aStr.length < aMinLen) {
            let padding = Array(aMinLen - aStr.length + 1).join(" ");
            aStr = (aOptions && aOptions.align === "end") ? padding + aStr : aStr + padding;
        }
        return aStr;
    }
    this._fmt = fmt;
    
    /**
     * Create a simple debug representation of a given element.
     *
     * @param {nsIDOMElement} aElement
     *        The element to debug
     * @return {string}
     *        A simple single line representation of aElement
     *
     * Taken from resource://gre/modules/devtools/Console.jsm
     */
    var debugElement = function(aElement)
    {
        return "<" + aElement.tagName +
            (aElement.id ? "#" + aElement.id : "") +
            (aElement.className && aElement.className.split ?
                "." + aElement.className.split(" ").join(" .") :
                "") +
            ">";
    }
    this._debugElement = debugElement;
    
    /**
     * parseUri helper, taken from https://github.com/mozilla/addon-sdk/blob/master/lib/toolkit/loader.js
     * This is also accessible under `require("toolkit/loader")`, but this
     * is bugged in the current version of Mozilla
     */
    var parseURI = function(uri)
    {
        return String(uri).split(" -> ").pop();
    }
    this._parseURI = parseURI;

    /**
     * parseStack helper, based on https://github.com/errwischt/stacktrace-parser/blob/master/lib/stacktrace-parser.js
     * License: https://github.com/errwischt/stacktrace-parser/blob/master/README.md#license
     * The version available in the mozilla SDK doesnt properly parse filenames
     * 
     */
    function parseStack(stackString)
    {
        var UNKNOWN_FUNCTION = '<unknown>';
        
        var rx = /^(?:\s*(\S*)(?:\((.*?)\))?@)?((?:\w).*?):(\d+)(?::(\d+))?\s*$/i,
            lines = stackString.split('\n'),
            stack = [],
            parts;
        
        for (var i = 0, j = lines.length; i < j; ++i)
        {
            if ((parts = rx.exec(lines[i])))
            {
                // Redundant values are for backwards/forwards compatibility
                stack.push({
                    'file': parts[3],
                    'fileName': parts[3],
                    'methodName': parts[1] || UNKNOWN_FUNCTION,
                    'name': parts[1] || UNKNOWN_FUNCTION,
                    'lineNumber': +parts[4],
                    'column': parts[5] ? +parts[5] : null,
                    'columnNumber': parts[5] ? +parts[5] : null
                });
            }
            else
            {
                continue;
            }
        }
        
        return stack;
    }
    this._parseStack = parseStack;

})();
