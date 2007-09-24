/* Copyright (c) 2006 [[%ask2:Domain Name:MyCompany.com]]
   See the file LICENSE.txt for licensing information. */

/* module [[%ask1:Component Name:MyJavaScriptComponent]] */

var [[%ask1]]Module = new Object();

const [[%ask1]]_CONTRACTID     = "@[[%ask2]]/js[[%ask1]];1";
const [[%ask1]]_CID        = Components.ID("{[[%guid]]}");

function [[%ask1]]()
{
}
[[%ask1]].prototype = {


    /* TODO: Implement the interface here */
    

    QueryInterface: function(iid) {
        if (!iid.equals(i[[%ask1]]) &&
            !iid.equals(nsISupports))
            throw Components.results.NS_ERROR_NO_INTERFACE;
        return this;
    }
}


[[%ask1]]Module.registerSelf =
function (compMgr, fileSpec, location, type)
{
    compMgr = compMgr.QueryInterface(Components.interfaces.nsIComponentRegistrar);
    compMgr.registerFactoryLocation([[%ask1]]_CID, 
                                "[[%ask1]] Component",
                                [[%ask1]]_CONTRACTID, 
                                fileSpec, 
                                location,
                                type);
}

[[%ask1]]Module.getClassObject =
function (compMgr, cid, iid) {
    if (!cid.equals(DIALOGPROXY_CID))
        throw Components.results.NS_ERROR_NO_INTERFACE;
    
    if (!iid.equals(Components.interfaces.nsIFactory))
        throw Components.results.NS_ERROR_NOT_IMPLEMENTED;
    
    return [[%ask1]]Factory;
}

[[%ask1]]Module.canUnload =
function(compMgr)
{
    return true;
}
    
/* factory object */
var [[%ask1]]Factory = new Object();

[[%ask1]]Factory.createInstance =
function (outer, iid) {
    if (outer != null)
        throw Components.results.NS_ERROR_NO_AGGREGATION;

    return (new [[%ask1]]()).QueryInterface(iid);
}

/* entrypoint */
function NSGetModule(compMgr, fileSpec) {
    return [[%ask1]]Module;
}

