/* Copyright (c) [[%date:%Y]] [[%tabstop2:MyCompany.com]]
   See the file LICENSE.txt for licensing information. */

Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

/***********************************************************
 *              XPCOM class definition                     *
 ***********************************************************/

// Class constructor.
function [[%tabstop1:MyComponent]]() {
    // If you only need to access your component from Javascript, uncomment the
    // following line:
    //this.wrappedJSObject = this;
}

// Class definition.
[[%tabstop1]].prototype = {
    
    // properties required for XPCOM registration:
    classDescription: "[[%tabstop1]] XPCOM Component",
    
    classID:          Components.ID("{[[%guid]]}"),
    contractID:       "@[[%tabstop:mozilla.org/[[%tabstop1]]]];1",
    
    // QueryInterface implementation, e.g. using the generateQI helper (remove argument if skipped steps above)
    QueryInterface: XPCOMUtils.generateQI([Components.interfaces.nsI[[%tabstop1]]]),
    
    [[%tabstop:// TODO: Implement the interface here, define the function(s) exposed
    //       by your interface.
    [[%tabstop:hello]]: function() {
        [[%tabstop:return "Hello World!";]]
    },]]

};

// XPCOM registration of class.
var components = [[[%tabstop1]]];
function NSGetModule(compMgr, fileSpec) {
    return XPCOMUtils.generateModule(components);
}
