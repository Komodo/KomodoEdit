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
 * Portions created by ActiveState Software Inc are Copyright (C) 2010-2011
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

const {Cc, Ci} = require("chrome");

/**
 * Wrap the Komodo global preferences (XPCOM) object.
 */

var exports = module.exports;
var prefs = Cc["@activestate.com/koPrefService;1"].
                getService(Ci.koIPrefService).prefs;
for (var name of Object.keys(prefs.__proto__)) {
    if (name == "QueryInterface") {
        continue;
    }
    if (typeof(prefs[name]) == "function") {
        exports[name] = prefs[name].bind(prefs);
    } else {
        // Wrap in a closure, so name (n) remains the same.
        (function(n) {
            Object.defineProperty(exports, n, {
                get: function() { return prefs[n]; },
                set: function(newValue) { prefs[n] = newValue; },
            });
        })(name);
    }
}

var observer =
{
    observing: {},
    observe: function(subject, topic, data)
    {
        observer.observing[topic].forEach(function(callback)
        {
            callback(subject, topic, data);
        });
    }
}

exports.onChange = function(pref, callback)
{
    if ( ! (pref in observer.observing))
    {
        observer.observing[pref] = [];
        prefs.prefObserverService.addObserver(observer, pref, false);
    }

    observer.observing[pref].push(callback);
}

exports.removeOnChange = function(pref, callback)
{
    if ( ! (pref in observer.observing)) return;

    observer.observing[pref].forEach(function(_callback, index)
    {
        if (callback == _callback)
        {
            observer.observing[pref].splice(index,1);

            if ( ! observer.observing[pref].length)
            {
                delete observer.observing[pref];
                prefs.prefObserverService.removeObserver(observer, pref, false);
                return false;
            }
        }
    });
}
