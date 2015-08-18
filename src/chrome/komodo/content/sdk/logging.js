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

// koLogging.js

// JS interface to the logging system.

/* This should be available in all JS code in Komodo.

Usage:

    log = require("ko/logging").getLogger(<logger_name>);
    log.debug(<message>);
    log.info(<message>);
    etc.

For backwards compatibility, it is also possible to use:

    log = ko.logging.getLogger(<logger_name>);

To turn on or off a logger, use:

    log.setLevel(ko.logging.LOG_DEBUG);

Alternatively, on the command line used to launch komodo,

    komodo --raw -log logger_name:DEBUG
*/

/**
 * @module logging
 */
(function() {

if (typeof(require) === "function") {
    // This is being loaded as a jetpack module
    // (This is now the preferred way to load this)
    var { Cc, Ci, Cu } = require("chrome");
    exports.__method__ = "require"; // For unit testing
} else {
    // This is being loaded in a JS component or a JS module; export a "logging"
    // object with the desired API.
    var { classes: Cc, interfaces: Ci, utils: Cu } = Components;
    // Note that Cu.getGlobalForObject({}) gives us the wrong global...
    this.EXPORTED_SYMBOLS = ["logging"];
    this.logging = this.exports = {};
}

var _gLoggingMgr = null;
var _gSeenDeprectatedMsg = {};
var _gLoggers = {};

/**
 * Logging level - none
 */
const LOG_NOTSET = 0;

/**
 * Logging level - Debug
 */
const LOG_DEBUG = 10;

/**
 * Logging level - Info
 */
const LOG_INFO = 20;

/**
 * Logging level - Warn
 */
const LOG_WARN = 30;

/**
 * Logging level - Error
 */
const LOG_ERROR = 40;

/**
 * Logging level - Critical
 */
const LOG_CRITICAL = 50;

Object.defineProperty(exports, "LOG_NOTSET", {value: LOG_NOTSET, enumerable: true});
Object.defineProperty(exports, "LOG_DEBUG", {value: LOG_DEBUG, enumerable: true});
Object.defineProperty(exports, "LOG_INFO", {value: LOG_INFO, enumerable: true});
Object.defineProperty(exports, "LOG_WARN", {value: LOG_WARN, enumerable: true});
Object.defineProperty(exports, "LOG_ERROR", {value: LOG_ERROR, enumerable: true});
Object.defineProperty(exports, "LOG_CRITICAL", {value: LOG_CRITICAL, enumerable: true});

// Logger wrapper objects get notified of the log levels associated with
// particular loggers.  They only make the calls to the logging system if
// those logging calls will actually be processed.  This is mainly to avoid
// having to pass possibly large strings to Python.

// See the 'set_logger_level' notification information

const Logger = exports.Logger = function(logger, logger_name) {
    this._logger = logger;
    this._logger_name = logger_name;
};

Logger.prototype = {
    constructor: Logger,
    // Add level defines to the logger prototype, for ease of access.
    NOTSET: LOG_NOTSET,
    DEBUG: LOG_DEBUG,
    INFO: LOG_INFO,
    WARN: LOG_WARN,
    ERROR: LOG_ERROR,
    CRITICAL: LOG_CRITICAL,
};

/**
 * Set the logging level for the current logger, eg. logging.LOG_DEBUG
 * 
 * @param   {Long} level
 */
Logger.prototype.setLevel = function(level) {
    this._logger.setLevel(level);
};

Object.defineProperty(Logger.prototype, "level", {
    get: function() {
        if (!this._logger) {
            return LOG_NOTSET;
        }
        return this._logger.level;
    },
    enumerable: true,
});

Logger.prototype.getEffectiveLevel = function() {
    return this._logger.getEffectiveLevel();
};

Logger.prototype.isEnabledFor = function(level) {
    return this._logger.isEnabledFor(level);
};

/**
 * Log a debug message
 * 
 * @param   {String} message
 */
Logger.prototype.debug = function(message) {
    try {
        if (this.isEnabledFor(LOG_DEBUG)) {
            this._logger.debug(message);
        }
    } catch(ex) {
        dump("*** Error in logger.debug: "+ex+"\n");
    }
}

/**
 * Log an info message
 * 
 * @param   {String} message
 */
Logger.prototype.info = function(message) {
    try {
        if (this.isEnabledFor(LOG_INFO)) {
            this._logger.info(message);
        }
    } catch(ex) {
        dump("*** Error in logger.info: "+ex+"\n");
    }
}

/**
 * Log a warning message
 * 
 * @param   {String} message
 */
Logger.prototype.warn = function(message) {
    try {
        if (this.isEnabledFor(LOG_WARN)) {
            this._logger.warn(message);
        }
    } catch(ex) {
        dump("*** Error in logger.warn: "+ex+"\n");
    }
}

Logger.prototype.warning = function(message) {
    this.deprecated("for js log warnings use 'log.warn', not 'log.warning'");
    this.warn(message);
};

/**
 * Log a deprecation warning message. This will also log the stack trace
 * to show where the deprecated code was being called from.
 *
 * Note: This is not a core Python logging function, it's just used from
 *       JavaScript code to warn about Komodo JavaScript API deprecations.
 *
 * @param {string} message  The deprecation warning message.
 * @param {boolean} reportDuplicates  Optional, when set to false it only logs
 *        the first occurance of the deprecation message.
 * @param {Number} stacklevel The number of frames to skip reporting
 */
Logger.prototype.deprecated = function(message, reportDuplicates=false,
                                       stacklevel=0)
{
    try {
        if (this.isEnabledFor(LOG_WARN)) {
            if (reportDuplicates || !(message in _gSeenDeprectatedMsg)) {
                _gSeenDeprectatedMsg[message] = true;
                // Skip the deprecated() line
                stacklevel = (parseInt(stacklevel) || 0) + 1;
                this.warn(message + "\n" + getStack(null, stacklevel, 4));
            }
        }
    } catch(ex) {
        dump("*** Error in logger.deprecationWarning: "+ex+"\n");
    }
}

/**
 * Mark global var/function as being deprecated with an alternative. All calls
 * to the item will be logged with a one-off warning.
 *
 * @param deprecatedName {string}  The global variable name that is deprecated
 * @param replacementName {string}  The new replacement code (an expression to eval)
 * @param logger {Logger}  The logger to use (from ko.logging.getLogger), or null to use the default
 * @param global {Object} The global to attach to.
 * @note This doesn't work when used with Components.utils.import
 */
exports.globalDeprecatedByAlternative = function(deprecatedName, replacementName, logger, global) {
    if (global === undefined) {
        // No global given (the signature of globalDeprecatedByAlternative
        // changed in Komodo 9.0.0a1): warn now, since we can't actually attach
        // the global variable getter.
        if (!logger) {
            logger = getLogger("");
        }
        logger.deprecated("globalDeprecatedByAlternative: can't added deprecated " +
                          "getter for " + deprecatedName + ": global not provided.\n\t" +
                          "Use " + replacementName + " instead.", false, 1);
        return;
    }
    Object.defineProperty(global, deprecatedName, {get:
         function() {
            // Get the caller of the deprecated item - 2 levels up.
            var shortStack = "    " + getStack().split("\n")[2];
            var marker = deprecatedName + shortStack;
            if (!(marker in _gSeenDeprectatedMsg)) {
                _gSeenDeprectatedMsg[marker] = true;
                if (!logger) {
                    logger = getLogger("");
                }
                logger.warn("DEPRECATED: "
                                           + deprecatedName
                                           + ", use "
                                           + replacementName
                                           + "\n"
                                           + shortStack
                                           + "\n"
                                           );
            }
            return eval(replacementName);
        }, enumerable: true, configurable: true});
};

/**
 * Mark object property as being deprecated with an alternative. All gets
 * to the item will be logged with a one-off warning.
 *
 * @param object {Object} The object on which the deprecated property exists
 * @param deprecatedName {string}  The global variable name that is deprecated
 * @param replacementName {string}  An expression to get the replacement; |this| is the object
 * @param logger {Logger}  The logger to use (from ko.logging.getLogger), or null to use the default
 */
exports.propertyDeprecatedByAlternative =
function(object, deprecatedName, replacementName, logger) {
    Object.defineProperty(object, deprecatedName, {
        get: function() {
            // Get the caller of the deprecated item - 2 levels up.
            var shortStack = "    " + getStack().split("\n")[2];
            var marker = deprecatedName + shortStack;
            if (!(marker in _gSeenDeprectatedMsg)) {
                _gSeenDeprectatedMsg[marker] = true;
                if (!logger) {
                    logger = getLogger("");
                }
                logger.warn("DEPRECATED: "
                                           + object
                                           + "."
                                           + deprecatedName
                                           + ", use "
                                           + replacementName.replace(/\bthis\b/g, object)
                                           + "\n"
                                           + shortStack
                                           + "\n"
                                           );
            }
            return (function() eval(replacementName)).call(object);
        }
    });
};

/**
 * Log an error message
 * 
 * @param   {String} message    
 * @param   {Boolean} noTraceback       Whether to log a backtrace
 */
Logger.prototype.error = function(message, noTraceback=false) {
    try {
        if (this.isEnabledFor(LOG_ERROR)) {
            if (!noTraceback) {
                message = String(message).replace(/\n$/, "") +
                          "\nTraceback from ERROR in '" +
                          this._logger_name + "' logger:\n" +
                          getStack(null, 0, 4);
            }
            this._logger.error(message);
            
            if (!noTraceback) {
                this.report(new Error(String(message)), "", "ERROR");
            }
        }
    } catch(ex) {
        dump("*** Error in logger.error: "+ex+"\n");
    }
};

/**
 * Log a critical message
 * 
 * @param   {String} message
 */
Logger.prototype.critical = function(message) {
    try {
        if (this.isEnabledFor(LOG_CRITICAL)) {
            this._logger.critical(message);
        }
        
        this.report(new Error(message), "", "CRITICAL");
    } catch(ex) {
        dump("*** Error in logger.critical: "+ex+"\n");
    }
};

/**
 * Log an exception
 * 
 * @param   {Exception} e      
 * @param   {String} message
 */
Logger.prototype.exception = function(e, message="") {
    try {
        if (this.isEnabledFor(LOG_ERROR)) {
            var objDump = getObjectTree(e,1);
            if (typeof(e) == 'object' && 'stack' in e && e.stack) {
                objDump += '+ stack\n    ' +
                           e.stack.toString().replace('\n', '\n    ', 'g').slice(0, -4);
            }
            if (!message)
                message='';
            this.error(message+'\n' +
                       '-- EXCEPTION START --\n' +
                       e + '\n' +
                       objDump +
                       '-- EXCEPTION END --',
                       true /* noTraceback */);
            
            this.report(e, message);
        }
    } catch(ex) {
        dump("*** Error in logger.exception: "+ex+"\n");
        if (typeof(e) == 'object' && 'stack' in e && e.stack)
            dump(e.stack + "\n");
        //dump("*** Original exception was: " + e + "\n");
        //dump("*** Original message was: " + message + "\n");
    }
}

Logger.prototype.report = function(e, message, level = "EXCEPTION") {
    var prefs = require("ko/prefs");
    
    if ( ! prefs.getBooleanPref("analytics_enabled", false)) {
        return;
    }
    
    var view = require("ko/views").current();
    var i = Cc["@activestate.com/koInfoService;1"].getService(Ci.koIInfoService);
    
    message = level + " :: " + e.name + " :: " + message + " :: " + e.message;
    
    var payload = {
        apiKey: prefs.getString("bugsnag_key"),
        notifier: {
            name: "Komodo-JS",
            version: "1.0"
        },
        events: [{
                context: level + "::" + e.fileName + ":" + e.lineNumber,
                app: {
                    type: i.productType,
                    version: i.version,
                    build: i.buildNumber,
                    releaseStage: i.buildFlavour
                },
                device: {
                    platform: i.buildPlatform,
                    release: i.osRelease
                },
                metaData: {
                    state: {
                        numViews: ko.views.manager.getAllViews().length,
                        language: view.language,
                        size: view.scimoz.length
                    }
                },
                exceptions: [{
                        payloadVersion: "2",
                        errorClass: message,
                        message: message,
                        stacktrace: e.stack ? require("ko/console")._parseStack(e.stack) : null
                    }
                ],
                user: {
                    id: prefs.getString('analytics_ga_uid', "")
                }
            }
        ]
    }
    
    require("ko/ajax").request({
        url: "https://notify.bugsnag.com",
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

const getStack = exports.getStack = function(ex=null, skipCount=0, indentWidth=0)
{
    if (!ex) {
        ex = Error();
        skipCount += 1;
    }
    var frames = ex.stack.split("\n");
    var padding = "";
    for (var i=0; i < indentWidth; i++) {
        padding += " ";
    }
    var stack = padding + frames.slice(skipCount).join("\n" + padding);
    // Remove the last padding item.
    if (padding) {
        stack = stack.slice(0, -(padding.length));
    }
    return stack;
}

exports.dumpStack = function() {
    dump("Stack:\n" + getStack(null, 0, 4));
}

/* XXX copied from venkman-utils.js
 * Dumps an object in tree format, recurse specifiec the the number of objects
 * to recurse, compress is a boolean that can uncompress (true) the output
 * format, and level is the number of levels to intitialy indent (only useful
 * internally.)  A sample dumpObjectTree (o, 1) is shown below.
 *
 * + parent (object)
 * + users (object)
 * | + jsbot (object)
 * | + mrjs (object)
 * | + nakkezzzz (object)
 * | *
 * + bans (object)
 * | *
 * + topic (string) 'ircclient.js:59: nothing is not defined'
 * + getUsersLength (function) 9 lines
 * *
 */
exports.dumpObjectTree = function(o, recurse, compress, level)
{
    dump(getObjectTree(o, recurse, compress, level));
}

const getObjectTree = exports.getObjectTree = function(o, recurse, compress, level) {
    var s = "";
    var pfx = "";

    if (typeof recurse == "undefined")
        recurse = 0;
    if (typeof level == "undefined")
        level = 0;
    if (typeof compress == "undefined")
        compress = true;

    for (var i = 0; i < level; i++)
        pfx += (compress) ? "| " : "|  ";

    var tee = (compress) ? "+ " : "+- ";

    if (typeof(o) != 'object') {
        s += pfx + tee + i + " (" + typeof(o) + ") " + o + "\n";
    } else
    for (i in o)
    {
        var t;
        try
        {
            t = typeof o[i];

            switch (t)
            {
                case "function":
                    var sfunc = String(o[i]).split("\n");
                    if (sfunc[2] == "    [native code]")
                        sfunc = "[native code]";
                    else
                        sfunc = sfunc.length + " lines";
                    s += pfx + tee + i + " (function) " + sfunc + "\n";
                    break;

                case "object":
                    s += pfx + tee + i + " (object) " + o[i] + "\n";
                    if (!compress)
                        s += pfx + "|\n";
                    if ((i != "parent") && (recurse))
                        s += getObjectTree(o[i], recurse - 1,
                                             compress, level + 1);
                    break;

                case "string":
                    if (o[i].length > 200)
                        s += pfx + tee + i + " (" + t + ") " +
                            "'" + o[i].substr(0, 100) + "'..." +
                            o[i].length + " chars\n";
                    else
                        s += pfx + tee + i + " (" + t + ") '" + o[i] + "'\n";
                    break;

                default:
                    s += pfx + tee + i + " (" + t + ") " + o[i] + "\n";
            }
        }
        catch (ex)
        {
            s += pfx + tee + i + " (exception) " + ex + "\n";
        }

        if (!compress)
            s += pfx + "|\n";

    }

    s += pfx;

    return s;
}

const dumpDOM = exports.dumpDOM = function(node, level=0, recursive=true) {
  dump(" ".repeat(2*level) + "<" + node.nodeName + "\n");
  var i;
  if (node.nodeType == 3) {
      dump(" ".repeat((2*level) + 4) + node.nodeValue + "'\n");
  } else {
    if (node.attributes) {
      for (i = 0; i < node.attributes.length; i++) {
        dump(" ".repeat((2*level) + 4) +
             node.attributes[i].nodeName +
             "='" +
             node.attributes[i].nodeValue +
             "'\n");
      }
    }
    if (node.childNodes.length == 0) {
      dump(" ".repeat(2*level) + "/>\n");
    } else {
      dump(" ".repeat(2*level) + ">\n");
      if (recursive) {
        for (i = 0; i < node.childNodes.length; i++) {
          dumpDOM(node.childNodes[i], level + 1);
        }
      } else {
        dump(" ".repeat(2*level + 2) + "...\n");
      }
      dump(" ".repeat(2*level) +
           "</" + node.nodeName + ">\n");
    }
  }
}

exports.dumpEvent = function(event)
{
    dump('-EVENT DUMP--------------------------\n');
    dump('type:           '+event.type+'\n');
    dump('eventPhase:     '+event.eventPhase+'\n');
    if ('charCode' in event) {
        dump("charCode: "+event.charCode+"\n");
        if (event[name])
            dump("str(charCode):  '"+String.fromCharCode(event.charCode)+"'\n");
    }
    if ('target' in event) {
        dump("target: "+event.target+"\n");
        if (event.target && 'nodeName' in event.target) {
            dump("target.nodeName: "+event.target.nodeName+'\n');
            dump("target.id: "+event.target.getAttribute('id')+'\n');
        }
    }
    if ('currentTarget' in event) {
        dump("currentTarget: "+event.currentTarget+"\n");
        if (event.currentTarget && 'nodeName' in event.currentTarget) {
            dump("currentTarget.nodeName: "+event.currentTarget.nodeName+'\n');
            dump("currentTarget.id: "+event.currentTarget.getAttribute('id')+'\n');
        }
    }
    if ('originalTarget' in event) {
        dump("originalTarget: "+event.originalTarget+"\n");
        if (event.originalTarget && 'nodeName' in event.originalTarget) {
            dump("originalTarget.nodeName: "+event.originalTarget.nodeName+'\n');
            dump("originalTarget.id: "+event.originalTarget.getAttribute('id')+'\n');
        }
    }
    var names = [
        'bubbles',
        'cancelable',
        'detail',
        'button',
        'keyCode',
        'isChar',
        'shiftKey',
        'altKey',
        'ctrlKey',
        'metaKey',
        'clientX',
        'clientY',
        'screenX',
        'screenY',
        'layerX',
        'layerY',
        'isTrusted',
        'timeStamp',
        'currentTargetXPath',
        'targetXPath',
        'originalTargetXPath'
                ];
    for (var i in names) {
        if (names[i] in event) {
            dump(names[i]+": "+event[names[i]]+"\n");
        }
    }
    dump('-------------------------------------\n');
};

const strObject = exports.strObject = function(o, name)
{
    var s = "";
    if (typeof(name) == 'undefined') name = 'Object';
    for (var x in o) {
        try {
            s += name+'[' + x + '] = '+ o[x] + '\n';
        } catch (e) {
            s += name+'[' + x + '] = <error>\n';
        }
    }
    return s;
}
exports.dumpObject = function(o, name)
{
    dump(strObject(o, name));
}


/** Based on snippet by "Amos Batto", http://stackoverflow.com/a/11315561/490321 **/
const dumpMixed = exports.dumpMixed =
function(v, maxRecursion=2, parentProperties=true, recursionLevel=0)
{
    recursionLevel = (typeof recursionLevel !== 'number') ? 0 : recursionLevel;

    var vType = typeof v;
    var out = vType;

    switch (vType)
    {
	case "number":
        case "boolean":
            out += ": " + v;
            break;
        case "string":
            out += "(" + v.length + '): "' + v + '"';
            break;
        case "object":
            if (v !== null && recursionLevel >= maxRecursion) return '(max recursion) ...';
            
            if (v == window) {
                out = "<window>";
            }
            else if (v == document) {
                out = "<document>";
            }
            else if (v === null) {
                out = "null";
            }
            else if (Object.prototype.toString.call(v) === '[object Array]') {
                out = 'array(' + v.length + '): {\n';
                for (var i = 0; i < v.length; i++) {
                    out += '   '.repeat(recursionLevel) + "   [" + i + "]:  " +
                        dumpMixed(v[i], maxRecursion, parentProperties, recursionLevel + 1) + "\n";
                }
                out += '   '.repeat(recursionLevel) + "}";
            }
            else { //if object
                var sContents = "{\n";
                var cnt = 0;
                for (var member in v)
                {
                    if (parentProperties || v.hasOwnProperty(member)) {
                        //No way to know the original data type of member, since JS
                        //always converts it to a string and no other way to parse objects.
                        try {
                            sContents += '   '.repeat(recursionLevel) + "   " + member +
                                ":  " + dumpMixed(v[member], maxRecursion, parentProperties, recursionLevel + 1) + "\n";
                        } catch(e) {
                            sContents += "<error parsing value: "+e.message+">";
                        }
                        cnt++;
                    }
                }
                sContents += '   '.repeat(recursionLevel) + "}";
                out += "(" + cnt + "): " + sContents;
            }
            break;
	default:
            out += ": " + vType;
            break;
    }
	
    if (recursionLevel == 0)
    {
            dumpImportant(out, "Mixed Dump");
    }
    
    return out;
}

const dumpString = exports.dumpString = function(string)
{
	dump("\n" + string + "\n");
}

const dumpImportant = exports.dumpImportant = function(string, name="IMPORTANT")
{
	dumpString("--[START "+name+"]------------------------------------");
	dump(string);
	dumpString("--[END  "+name+"]------------------------------------");
}

exports.dumpView = function(view) {
    // Dump some interesting information about the current view.
    dump("\n--------------------------------------\n");
    try {
        if (view) {
            if (view.koDoc) {
                var doc = view.koDoc;
                var nle = doc.new_line_endings;
                var nleName = {0:"EOL_LF", 1:"EOL_CR", 2:"EOL_CRLF", 3:"EOL_MIXED", 4:"EOL_NOEOL"}[nle];
                dump("view.koDoc.new_line_endings: "+nle+" ("+nleName+")\n");
            } else {
                dump("view.koDoc is null\n");
            }

            var type = view.getAttribute("type");
            dump("view type: '"+type+"'\n");
            if (type == "editor") {
                var sciUtilsSvc = Cc["@activestate.com/koSciUtils;1"]
                                    .getService(Ci.koISciUtils);
                var language = view.scintilla.language;
                dump("language: "+language+"\n");
                var scimoz = view.scimoz;
                dump("number of style bits: "+scimoz.styleBits+"\n");
                var styleMask = (1 << scimoz.styleBits) - 1;
                dump("style mask: "+styleMask+"\n");
                dump("current cursor position: "+scimoz.currentPos+"\n");
                var styleByte = scimoz.getStyleAt(scimoz.currentPos);
                dump("    style byte: "+styleByte+"\n");
                var styleNum = styleByte & styleMask;
                var styleName = sciUtilsSvc.styleNameFromNum(language,
                                                             styleNum);
                dump("    lexical style: "+styleNum+" ("+styleName+")\n");
            }

            var scimoz = view.scimoz;
            dump("view.scimoz: "+scimoz+"\n");
            if (scimoz) {
                dump("view.scimoz.currentPos: "+scimoz.currentPos+"\n");
                dump("view.scimoz.anchor: "+scimoz.anchor+"\n");
            }
        } else {
            dump("view is null\n");
        }
    } catch(ex) {
        getLogger("").exception(ex, "error dumping view");
    }
    dump("--------------------------------------\n");
}

exports.setGlobalLevel = function(level) {
    require("notify/notify").send("Setting global logging level,\
                                  do not use this unless you know what you're doing",
            "dev", {priority: "warning"})
    
    for (let k in _gLoggers)
    {
        getLogger(k).setLevel(level);
    }
}

const LoggingMgr = exports.LoggingMgr = function() {
    this.LoggerMap = {}
    this.loggingSvc = Cc["@activestate.com/koLoggingService;1"]
                        .getService(Ci.koILoggingService);

    this.getLogger = function(logger_name) {
        if (!(logger_name in this.LoggerMap)) {
            var logger = this.loggingSvc.getLogger(logger_name);
            this.LoggerMap[logger_name] = new Logger(logger, logger_name);
        }
        return this.LoggerMap[logger_name];
    }
}

// Use this function to always get the logging manager
// (which may not be a global in your namespace)
const getLoggingMgr = exports.getLoggingMgr = function() {
    if (!_gLoggingMgr) {
        _gLoggingMgr = new LoggingMgr();
    }
    return _gLoggingMgr;
}

/**
 * Retrieve the given logger
 * 
 * @param   {String} logger_name
 * 
 * @returns {Logger}
 */
const getLogger = exports.getLogger = function(logger_name) {
    _gLoggers[logger_name] = true;
    return getLoggingMgr().getLogger(logger_name);
}

})();
