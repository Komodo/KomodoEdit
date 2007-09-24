/**
 * Copyright (c) 2006,2007 ActiveState Software Inc.
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
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
 * @param cName {String} Components.classes string
 * @param ifaceName {String} Components.interfaces name as a string
 * @returns reference to service
 */
function CCSV(cName, ifaceName)
{
    return CC[cName].getService(CI[ifaceName]);        
};

/**
 * create an XPCOM instance
 *
 * @param cName {String} Components.classes string
 * @param ifaceName {String} Components.interfaces name as a string
 * @returns reference to instance
 */
function CCIN(cName, ifaceName)
{
    return CC[cName].createInstance(CI[ifaceName]);
};

/**
 * query an XPCOM reference for an interface
 *
 * @param cName {Object} reference to XPCOM object
 * @param iface {long} Components.interfaces element
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
 * @param uri {String} uri to a JavaScript File
 * @param obj {Object} object to load the JavaScript into, if undefined loads into global namespace
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
 * @param uri {String} namespace to import
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
 * @param ns {Object} namespace to import INTO
 * @param ns {Object} namespace to import FROM
 */
xtk.importNS = function(to, from) {
    for (var i in from) {
        to[i] = from[i];
    }
}
