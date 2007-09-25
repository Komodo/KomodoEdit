/* Copyright (c) 2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(Casper) == 'undefined') {
    var Casper = {};
}
if (typeof(Casper.Logging) == 'undefined') {
    Casper.Logging = {};
}

Casper.Logging._logs = {};
/**
 * Return an existing|new logger with the supplied name.
 * @returns {Casper.Logging.Logger}
 */
Casper.Logging.getLogger = function(name) {
    if (typeof(Casper.Logging._logs[name]) == 'undefined') {
        Casper.Logging._logs[name] = new Casper.Logging.Logger(name);
    }
    return Casper.Logging._logs[name];
}
Casper.Logging.OFF = -1;
Casper.Logging.EXCEPTION = 0;
Casper.Logging.ERROR = 1;
Casper.Logging.WARN = 2;
Casper.Logging.INFO = 3;
Casper.Logging.DEBUG = 4;


    // XXX copied from venkman-utils.js
Casper.Logging.getObjectTree = function(o, recurse, compress, level)
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
                        s += Casper.Logging.getObjectTree (o[i], recurse - 1,
                                             compress, level + 1);
                    break;

                case "string":
                    if (o[i].length > 1000)
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

Casper.Logging.Logger = function(name) {
    this.name = name;
}
Casper.Logging.Logger.constructor = Casper.Logging.Logger;
Casper.Logging.Logger.prototype = {
    level: 2,
    lastErrorMsg: null,
    setLevel: function(level) {
        this.level = level;
    },
    doDump: function(level) {
        if (this.level >= level) {
            dump(this.name+": "+this.lastErrorMsg + "\n");
        }
    },
    debug: function(str) {
        this.lastErrorMsg = str;
        this.doDump(Casper.Logging.DEBUG);
    },
    info: function(str) {
        this.lastErrorMsg = str;
        this.doDump(Casper.Logging.INFO);
    },
    warn: function(str) {
        this.lastErrorMsg = str;
        this.doDump(Casper.Logging.WARN);
    },
    error: function(str) {
        this.lastErrorMsg = str;
        this.doDump(Casper.Logging.ERROR);
    },
    exception: function(e, str) {
        if (typeof(str) == 'undefined') {
            str = Casper.Logging.getObjectTree(e, true);
        } else {
            str = str +"\n"+ Casper.Logging.getObjectTree(e, true);
        }
        this.lastErrorMsg = str;
        this.doDump(Casper.Logging.EXCEPTION);
    }
}
