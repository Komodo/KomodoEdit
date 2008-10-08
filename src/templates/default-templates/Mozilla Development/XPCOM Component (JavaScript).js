/* Copyright (c) [[%date:%Y]] [[%tabstop2:MyCompany.com]]
   See the file LICENSE.txt for licensing information. */

/* module [[%tabstop1:MyJavaScriptComponent]] */

var [[%tabstop1]]Module = new Object();

const [[%tabstop1]]_CONTRACTID     = "@[[%tabstop2]]/js[[%tabstop1]];1";
const [[%tabstop1]]_CID        = Components.ID("{[[%guid]]}");

function [[%tabstop1]]()
{
}
[[%tabstop1]].prototype = {
    /* TODO: Implement the interface here */
    QueryInterface: function(iid) {
        if (!iid.equals(I[[%tabstop1]]) &&
            !iid.equals(nsISupports))
            throw Components.results.NS_ERROR_NO_INTERFACE;
        return this;
    }
}


[[%tabstop1]]Module.registerSelf =
function (compMgr, fileSpec, location, type)
{
    compMgr = compMgr.QueryInterface(Components.interfaces.nsIComponentRegistrar);
    compMgr.registerFactoryLocation([[%tabstop1]]_CID, 
                                "[[%tabstop1]] Component",
                                [[%tabstop1]]_CONTRACTID, 
                                fileSpec, 
                                location,
                                type);
}

[[%tabstop1]]Module.getClassObject =
function (compMgr, cid, iid) {
    if (!cid.equals(DIALOGPROXY_CID))
        throw Components.results.NS_ERROR_NO_INTERFACE;
    
    if (!iid.equals(Components.interfaces.nsIFactory))
        throw Components.results.NS_ERROR_NOT_IMPLEMENTED;
    
    return [[%tabstop1]]Factory;
}

[[%tabstop1]]Module.canUnload =
function(compMgr)
{
    return true;
}
    
/* factory object */
var [[%tabstop1]]Factory = new Object();

[[%tabstop1]]Factory.createInstance =
function (outer, iid) {
    if (outer != null)
        throw Components.results.NS_ERROR_NO_AGGREGATION;

    return (new [[%tabstop1]]()).QueryInterface(iid);
}

/* entrypoint */
function NSGetModule(compMgr, fileSpec) {
    return [[%tabstop1]]Module;
}

