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

    log = gLoggingMgr.getLogger(<logger_name>);
    log.debug(<message>);
    log.info(<message>);
    etc.

To turn on or off a logger, use:

    log.setLevel(LOG_DEBUG)

Loggers that we are using:

    "ko.performance": Where major bits of performance information go.
    "ko.performance.startup": Perf logging w.r.t. startup perf.

    "ko.process": information re: the process module
*/

if (typeof(ko) == 'undefined') {
    var ko = {};
}
ko.logging = {};

(function() {

var _gLoggingMgr = null;

const LOG_NOTSET = 0;
const LOG_DEBUG = 10;
const LOG_INFO = 20;
const LOG_WARN = 30;
const LOG_ERROR = 40;
const LOG_CRITICAL = 50;

this.__defineGetter__("LOG_NOTSET", function() { return LOG_NOTSET; });
this.__defineGetter__("LOG_DEBUG", function() { return LOG_DEBUG; });
this.__defineGetter__("LOG_INFO", function() { return LOG_INFO; });
this.__defineGetter__("LOG_WARN", function() { return LOG_WARN; });
this.__defineGetter__("LOG_ERROR", function() { return LOG_ERROR; });
this.__defineGetter__("LOG_CRITICAL", function() { return LOG_CRITICAL; });

// Logger wrapper objects get notified of the log levels associated with
// particular loggers.  They only make the calls to the logging system if
// those logging calls will actually be processed.

// See the 'set_logger_level' notification information

this.Logger = function Logger(logger, logger_name) {
    this._logger = logger;
    this._logger_name = logger_name;
}

this.Logger.prototype.constructor = this.Logger;

this.Logger.prototype.setLevel = function(level) {
    this._logger.setLevel(level);
}

this.Logger.prototype.getEffectiveLevel = function() {
    return this._logger.getEffectiveLevel();
}

this.Logger.prototype.debug= function(message) {
    try {
        if (this._logger.getEffectiveLevel() <= LOG_DEBUG) {
            this._logger.debug(message);
        }
    } catch(ex) {
        dump("*** Error in logger.debug: "+ex+"\n");
    }
}

this.Logger.prototype.info = function(message) {
    try {
        if (this._logger.getEffectiveLevel() <= LOG_INFO) {
            this._logger.info(message);
        }
    } catch(ex) {
        dump("*** Error in logger.info: "+ex+"\n");
    }
}

this.Logger.prototype.warn = function(message) {
    try {
        if (this._logger.getEffectiveLevel() <= LOG_WARN) {
            this._logger.warn(message);
        }
    } catch(ex) {
        dump("*** Error in logger.warn: "+ex+"\n");
    }
}

this.Logger.prototype.error = function(message) {
    try {
        if (this._logger.getEffectiveLevel() <= LOG_ERROR) {
            // I would prefer to have this be a separate log.exception(). --TM
            dump("Traceback from ERROR in '" +
                 this._logger_name + "' logger:\n    " +
                 getStack().replace('\n', '\n    ', 'g').slice(0, -4));
            this._logger.error(message);
        }
    } catch(ex) {
        dump("*** Error in logger.error: "+ex+"\n");
    }
}

this.Logger.prototype.critical = function(message) {
    try {
        if (this._logger.getEffectiveLevel() <= LOG_CRITICAL) {
            this._logger.critical(message);
        }
    } catch(ex) {
        dump("*** Error in logger.critical: "+ex+"\n");
    }
}


this.Logger.prototype.exception = function(e, message) {
    try {
        if (this._logger.getEffectiveLevel() <= LOG_ERROR) {
            var objDump = getObjectTree(e,1);
            if (typeof(e) == 'object' && 'stack' in e)
                objDump += e.stack;
            if (typeof(message)=='undefined' || !message)
                message='';
            this.error(message+'\n-- EXCEPTION START --\n'+objDump+'-- EXCEPTION END --\n');
        }
    } catch(ex) {
        dump("*** Error in logger.exception: "+ex+"\n");
        if (typeof(e) == 'object' && 'stack' in e)
            dump(e.stack + "\n");
        //dump("*** Original exception was: " + e + "\n");
        //dump("*** Original message was: " + message + "\n");
    }
}

function getStack()
{
    if (!((typeof Components == "object") &&
          (typeof Components.classes == "object")))
        return "No stack trace available.";

    var frame = Components.stack.caller;
    var str = "<top>";

    while (frame)
    {
        var name = frame.name ? frame.name : "[anonymous]";
        str += "\n" + name + "@" + frame.filename +':' + frame.lineNumber;
        frame = frame.caller;
    }

    return str+"\n";
}
this.getStack = getStack;

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
this.dumpObjectTree = function dumpObjectTree(o, recurse, compress, level)
{
    dump(this.getObjectTree(o, recurse, compress, level));
}

function getObjectTree(o, recurse, compress, level)
{
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

    s += pfx + "*\n";

    return s;
}
this.getObjectTree = getObjectTree;


function _repeatStr(str, aCount) {
   var res = "";
   while (--aCount >= 0)
     res += str;
   return res;
};

function dumpDOM(node, level, recursive) {
  if (level == undefined) {
    level = 0
  }
  if (recursive == undefined) {
    recursive = true;
  }

  dump(_repeatStr(" ", 2*level) + "<" + node.nodeName + "\n");
  var i;
  if (node.nodeType == 3) {
      dump(_repeatStr(" ", (2*level) + 4) + node.nodeValue + "'\n");
  } else {
    if (node.attributes) {
      for (i = 0; i < node.attributes.length; i++) {
        dump(_repeatStr(" ", (2*level) + 4) + node.attributes[i].nodeName + "='" + node.attributes[i].nodeValue + "'\n");
      }
    }
    if (node.childNodes.length == 0) {
      dump(_repeatStr(" ", (2*level)) + "/>\n");
    } else if (recursive) {
      dump(_repeatStr(" ", (2*level)) + ">\n");
      for (i = 0; i < node.childNodes.length; i++) {
        dumpDOM(node.childNodes[i], level + 1);
      }
      dump(_repeatStr(" ", 2*level) + "</" + node.nodeName + ">\n");
    }
  }
}
this.dumpDOM = dumpDOM;

this.dumpEvent = function dumpEvent(event)
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
}
this.strObject = function strObject(o, name)
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
this.dumpObject = function dumpObject(o, name)
{
    dump(this.strObject(o, name));
}
this.dumpView = function dumpView(view) {
    // Dump some interesting information about the current view.
    dump("\n--------------------------------------\n");
    try {
        if (view) {
            if (view.document) {
                var doc = view.document;
                var nle = doc.new_line_endings;
                var nleName = {0:"EOL_LF", 1:"EOL_CR", 2:"EOL_CRLF", 3:"EOL_MIXED", 4:"EOL_NOEOL"}[nle];
                dump("view.document.new_line_endings: "+nle+" ("+nleName+")\n");
            } else {
                dump("view.document is null\n");
            }

            var type = view.getAttribute("type");
            dump("view type: '"+type+"'\n");
            if (type == "editor") {
                var sciUtilsSvc = Components.classes["@activestate.com/koSciUtils;1"].
                                  getService(Components.interfaces.koISciUtils);
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
        log.exception(ex, "error dumping view");
    }
    dump("--------------------------------------\n");
}

this.LoggingMgr = function LoggingMgr() {
    this.LoggerMap = {}
    this.loggingSvc = Components.classes["@activestate.com/koLoggingService;1"].
                    getService(Components.interfaces.koILoggingService);

    this.getLogger = function(logger_name) {
        if (logger_name in this.LoggerMap) {
            return this.LoggerMap[logger_name];
        }
        var logger = this.loggingSvc.getLogger(logger_name);
        this.LoggerMap[logger_name] = new ko.logging.Logger(logger, logger_name);
        return this.LoggerMap[logger_name];
    }
}

// Use this function to always get the logging manager
// (which may not be a global in your namespace)
this.getLoggingMgr = function getLoggingMgr() {
    if (!_gLoggingMgr) {
        _gLoggingMgr = new ko.logging.LoggingMgr();
    }
    return _gLoggingMgr;
}

this.getLogger = function getLogger(logger_name) {
    return this.getLoggingMgr().getLogger(logger_name);
}
}).apply(ko.logging);

// Backward Compat API
var getLoggingMgr = ko.logging.getLoggingMgr;
var loggingMgr = ko.logging.LoggingMgr;
var loggerWrapper = ko.logging.Logger;
var logging_getStack = ko.logging.getStack;
var logging_dumpObjectTree = ko.logging.getObjectTree;
var logging_dumpDOM = ko.logging.dumpDOM;
var logging_dumpEvent = ko.logging.dumpEvent;
var logging_dumpObject = ko.logging.dumpObject;
var logging_dumpView = ko.logging.dumpView;

var LOG_NOTSET = 0;
var LOG_DEBUG = 10;
var LOG_INFO = 20;
var LOG_WARN = 30;
var LOG_ERROR = 40;
var LOG_CRITICAL = 50;
try {
    //XXX Whoa. Isn't this evil? This means every JS namespace has 'log'
    //    set to the root logger -- a subtle fallback for sloppy code that
    //    presumes a 'log' variable. --TM
    var log = getLoggingMgr().getLogger('');
} catch (e) {
    try {
        alert(e);
    } catch(ex) {
        // this  happens if there is no window, and getLogger failed
        dump(e+"\n");
        dump(ex+"\n");
    }
}


