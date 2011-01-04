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

/* * *
 * Contributors:
 *   Shane Caraveo <shanec@activestate.com>
 */

/**
 * xtk library contains usefull JavaScript/XPCOM/XUL functionality that
 * is not specific to Komodo
 */
var xtk = {};

/**
 * XPCOM global support to ease typing
 */

const CC = Components.classes;
const CI = Components.interfaces;

/**
 * get a reference to an XPCOM service
 *
 * @param {String} cName Components.classes string
 * @param {String} ifaceName Components.interfaces name as a string
 * @returns reference to service
 */
function CCSV(cName, ifaceName)
{
    return CC[cName].getService(CI[ifaceName]);        
};

/**
 * create an XPCOM instance
 *
 * @param {String} cName Components.classes string
 * @param {String} ifaceName Components.interfaces name as a string
 * @returns reference to instance
 */
function CCIN(cName, ifaceName)
{
    return CC[cName].createInstance(CI[ifaceName]);
};

/**
 * query an XPCOM reference for an interface
 *
 * @param {Object} cName reference to XPCOM object
 * @param {long} iface Components.interfaces element
 * @returns reference to instance with the specified interface
 */
function QI(obj, iface)
{
    return obj.QueryInterface(iface);
};

/**
 * load
 * 
 * load a JavaScript file into the global namespace or a defined namespace
 *
 * @param {String} uri uri to a JavaScript File
 * @param {Object} obj object to load the JavaScript into, if undefined loads into global namespace
 */
xtk.load = function(uri, obj) {
    const loader = CCSV("@mozilla.org/moz/jssubscript-loader;1", "mozIJSSubScriptLoader");
    loader.loadSubScript(uri, obj);
}

/**
 * include
 * 
 * include an xtk namespace
 *
 * @param {String} uri namespace to import
 */
xtk.include = function(ns) {
    if (typeof(xtk[ns]) == "undefined") {
        var filename = "chrome://xtk/content/"+ns+".js";
        this.load(filename);
    }
}
xtk.include("logging");

/**
 * importNS
 * 
 * import one namespace into another
 *
 * @param {Object} ns namespace to import INTO
 * @param {Object} ns namespace to import FROM
 */
xtk.importNS = function(to, from) {
    for (var i in from) {
        to[i] = from[i];
    }
}
