const DEBUG = 0;

const JSLIB_CONTRACTID   = "@mozilla.org/jslib;1";
const JSLIB_CID          = Components.ID("{c3366882-5f84-4ad3-88a9-79c90b37cd2e}");

const IO_SERV_CONTRACTID   = "@mozilla.org/network/io-service;1";

const nsISupports           = Components.interfaces.nsISupports;
const nsIFactory            = Components.interfaces.nsIFactory;
const nsIClassInfo          = Components.interfaces.nsIClassInfo;
const mozIJSLib             = Components.interfaces.mozIJSLib;
const mozIJSSubScriptLoader = Components.interfaces.mozIJSSubScriptLoader;
const nsIDOMChromeWindow    = Components.interfaces.nsIDOMChromeWindow;
const nsIDOMWindow          = Components.interfaces.nsIDOMWindow;

function jsLib () {}

// init
jsLib.prototype.init = 
function (aContext)
{
  try 
  {
    if ("JS_LIB_LOADED" in aContext) return;

    // ensure context is a chrome window
    if (!(aContext instanceof nsIDOMChromeWindow) && 
        !(aContext instanceof nsIDOMWindow)) 
    {
      debug("Not an nsIDOMChromeWindow");
      return;
    }

    var docURI = aContext.location;
    if (!/^chrome:\/\/|codetab:/.test(docURI)) 
    {
      debug("ACCESS ERROR: ["+docURI+"]\n");
      debug("does not have privileges to access jslib dom object \n");
      return;
    }

    const JSLIB_PATH = "chrome://jslib/content/jslib.js";

    var loader = Components.classes["@mozilla.org/moz/jssubscript-loader;1"];
        loader = loader.getService(mozIJSSubScriptLoader);

    loader.loadSubScript(JSLIB_PATH, aContext.wrappedJSObject || aContext);

  } catch (e) { debug(e); }
}

// property of nsIClassInfo
jsLib.prototype.flags = nsIClassInfo.DOM_OBJECT;

// property of nsIClassInfo
jsLib.prototype.classDescription = "jslib";

// method of nsIClassInfo
jsLib.prototype.getInterfaces = function (count) 
{
    var interfaceList = [mozIJSLib, nsIClassInfo];
    count.value = interfaceList.length;
    return interfaceList;
}

// method of nsIClassInfo
jsLib.prototype.getHelperForLanguage = function (count) { return null; }

jsLib.prototype.QueryInterface =
function (iid) 
{
    if (!iid.equals(mozIJSLib)    &&
        !iid.equals(nsIClassInfo) &&
        !iid.equals(nsISupports))
        throw Components.results.NS_ERROR_NO_INTERFACE;
    return this;
}

var libraryModule = new Object;

libraryModule.registerSelf =
function (compMgr, fileSpec, location, type)
{
    // debug("registering (all right -- a JavaScript module!)");
    compMgr = compMgr.QueryInterface(Components.interfaces.nsIComponentRegistrar);

    compMgr.registerFactoryLocation(JSLIB_CID, 
                                    "jsLib Library Component",
                                    JSLIB_CONTRACTID, 
                                    fileSpec, 
                                    location,
                                    type);

    const CATMAN_CONTRACTID = "@mozilla.org/categorymanager;1";
    const nsICategoryManager = Components.interfaces.nsICategoryManager;
    var catman = Components.classes[CATMAN_CONTRACTID].
                            getService(nsICategoryManager);

    const JAVASCRIPT_GLOBAL_PROPERTY_CATEGORY = "JavaScript global property";
    catman.addCategoryEntry(JAVASCRIPT_GLOBAL_PROPERTY_CATEGORY,
                            "jslib",
                            JSLIB_CONTRACTID,
                            true,
                            true);
}

libraryModule.getClassObject =
function (compMgr, cid, iid) {
    if (!cid.equals(JSLIB_CID))
        throw Components.results.NS_ERROR_NO_INTERFACE;
    
    if (!iid.equals(Components.interfaces.nsIFactory))
        throw Components.results.NS_ERROR_NOT_IMPLEMENTED;
    
    return libraryFactory;
}

libraryModule.canUnload =
function(compMgr)
{
    // debug("Unloading component.");
    return true;
}
    
/* factory object */
var libraryFactory = new Object;

libraryFactory.createInstance =
function (outer, iid) 
{
    // debug("CI: " + iid);
    if (outer != null)
        throw Components.results.NS_ERROR_NO_AGGREGATION;

    return (new jsLib()).QueryInterface(iid);
}

/* entrypoint */
function NSGetModule(compMgr, fileSpec) { return libraryModule; }

/* static functions */
var debug;
if (DEBUG)
    debug = function (s) { dump("-*- jsLib component: " + s + "\n"); }
else
    debug = function (s) {}

