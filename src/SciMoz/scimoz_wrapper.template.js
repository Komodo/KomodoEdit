/* Copyright (c) 2009 ActiveState
   See the file LICENSE.txt for licensing information. */

/**
 * This is an XPCOM wrapper the JavaScript (npruntime) scimoz object:
 */

Components.utils.import("resource://gre/modules/XPCOMUtils.jsm");

/***********************************************************
 *              XPCOM class definition                     *
 ***********************************************************/

// Class constructor.
function koSciMozWrapper() {
    this.wrappedJSObject = this;
}

// Class definition.
koSciMozWrapper.prototype = {

    // properties required for XPCOM registration:
    classDescription: "XPCOM wrapper around the npruntime scimoz object",

    classID:          Components.ID("{487f68c7-386a-4802-8874-b0f4912e59dc}"),
    contractID:       "@activestate.com/koSciMozWrapper;1",

    _interfaces: [Components.interfaces.nsIClassInfo,
                  Components.interfaces.ISciMozLite,
                  Components.interfaces.ISciMoz,
                  Components.interfaces.nsISupportsWeakReference],
    /* see bottom of file for QI impl */

    getInterfaces: function getInterfaces(aCount) {
        aCount.value = this._interfaces.length;
        return Array.slice(this._interfaces);
    },

    getHelperForLanguage: function() null,
    implementationLanguage: Components.interfaces.nsIProgrammingLanguage.JAVASCRIPT,
    flags: Components.interfaces.nsIClassInfo.MAIN_THREAD_ONLY |
           Components.interfaces.nsIClassInfo.EAGER_CLASSINFO,

    __scimoz: null,
};

__ISCIMOZ_JS_WRAPPER_GEN__

// implement QI. This needs to happen after the generated code because that
// determines which interfaces to support (due to the _Part? interfaces).
koSciMozWrapper.prototype.QueryInterface =
    XPCOMUtils.generateQI(koSciMozWrapper.prototype._interfaces);

// Override handleTextEvent, since we use the IME helper for that
koSciMozWrapper.prototype.handleTextEvent =
    function handleTextEvent(aEvent, aBoxObject) {
        return this._IMEHelper.handleTextEvent(aEvent, aBoxObject);
    };

/**
 * Initialize the plugin wrapper.
 * @param aPlugin the plugin to wrap
 * @note This isn't an interface method; also, it overrides the stub version
 *       because that does the wrong thing completely (we don't want to just
 *       pass everything to the plugin).
 */
koSciMozWrapper.prototype.init =
    function koSciMozWrapper_init(aPlugin, aFocusElement) {
        this.__scimoz = aPlugin;
        this._IMEHelper =
            Components.classes["@activestate.com/koSciMozIMEHelper;1"]
                       .createInstance(Components.interfaces.koISciMozIMEHelper);
        this._IMEHelper.init(this, aFocusElement);
        this.__scimoz.init(this._IMEHelper);
    };

// XPCOM registration of class.
var components = [koSciMozWrapper];
const NSGetFactory = XPCOMUtils.generateNSGetFactory(components);
