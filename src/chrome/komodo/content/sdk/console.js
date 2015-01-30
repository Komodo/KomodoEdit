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

    this.debug = console.debug;
    this.error = console.error;
    this.exception = console.exception;
    this.info = console.info;
    this.time = console.time;
    this.timeEnd = console.timeEnd;
    this.trace = console.trace;
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

})();
