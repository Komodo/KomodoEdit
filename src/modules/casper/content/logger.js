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
