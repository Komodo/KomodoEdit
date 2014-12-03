/* Copyright (c) 2009 ActiveState
   See the file LICENSE.txt for licensing information. */

/**
 * This is an XPCOM wrapper the JavaScript (npruntime) scimoz object:
 */

const {classes: Cc, interfaces: Ci, results: Cr, utils: Cu} = Components;
Cu.import("resource://gre/modules/Services.jsm");
Cu.import("resource://gre/modules/XPCOMUtils.jsm");

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

    _interfaces: [Ci.nsIClassInfo,
                  Ci.ISciMozLite,
                  Ci.ISciMoz,
                  Ci.nsISupportsWeakReference],
    /* see bottom of file for QI impl */

    getInterfaces: function getInterfaces(aCount) {
        aCount.value = this._interfaces.length;
        return Array.slice(this._interfaces);
    },

    getHelperForLanguage: function() null,
    implementationLanguage: Ci.nsIProgrammingLanguage.JAVASCRIPT,
    flags: Ci.nsIClassInfo.MAIN_THREAD_ONLY,

    __scimoz: null,

    __lastTextId: -1,
    __cachedText: null,
};

__ISCIMOZ_JS_WRAPPER_GEN__

// implement QI. This needs to happen after the generated code because that
// determines which interfaces to support (due to the _Part? interfaces).
koSciMozWrapper.prototype.QueryInterface =
    XPCOMUtils.generateQI(koSciMozWrapper.prototype._interfaces);

// setWordChars compatibility wrapper; see bug 80095 - new code should be using
// scimoz.wordChars = "xxx" instead of scimoz.setWordChars("xxx")
koSciMozWrapper.prototype.setWordChars =
    function setWordChars(aCharacters) {
        this._log.deprecated('scimoz.setWordChars() is deprecated, use scimoz.wordChars = "abc" instead');
        this.wordChars = aCharacters;
    };

// Override text to use locally cached text (for performance). Only reload the
// text when it's out-dated.
koSciMozWrapper.prototype.__defineGetter__("text", function get_text() {
    let textId = this.__scimoz.textId;
    if (textId != this.__lastTextId) {
        this.__cachedText = this.__scimoz.text;
        this.__lastTextId = textId;
    }
    return this.__cachedText;
});

// Override things dealing with pixels to return CSS pixels instead of device
// pixels; see bug 100492.  OSX is 72 DPI by default, Linux/Windows is 96.
const kDefaultDPI = Services.appinfo.OS == "Darwin" ? 72 : 96;

koSciMozWrapper.prototype.positionFromPoint = function(x, y) {
    return this.__scimoz.positionFromPoint(parseInt(x * this.logPixelsX / kDefaultDPI),
                                           parseInt(y * this.logPixelsY / kDefaultDPI));
};
koSciMozWrapper.prototype.positionFromPointClose = function(x, y) {
    return this.__scimoz.positionFromPointClose(parseInt(x * this.logPixelsX / kDefaultDPI),
                                                parseInt(y * this.logPixelsY / kDefaultDPI));
};
koSciMozWrapper.prototype.pointXFromPosition = function(pos) {
    return this.__scimoz.pointXFromPosition(pos) * kDefaultDPI / this.logPixelsX;
};
koSciMozWrapper.prototype.pointYFromPosition = function(pos) {
    return this.__scimoz.pointYFromPosition(pos) * kDefaultDPI / this.logPixelsY;
};
koSciMozWrapper.prototype.charPositionFromPoint = function(x, y) {
    return this.__scimoz.charPositionFromPoint(parseInt(x * this.logPixelsX / kDefaultDPI),
                                               parseInt(y * this.logPixelsY / kDefaultDPI));
};
koSciMozWrapper.prototype.charPositionFromPointClose = function(x, y) {
    return this.__scimoz.charPositionFromPointClose(parseInt(x * this.logPixelsX / kDefaultDPI),
                                                    parseInt(y * this.logPixelsY / kDefaultDPI));
};
koSciMozWrapper.prototype.textHeight = function(line) {
    return this.__scimoz.textHeight(line) * kDefaultDPI / this.logPixelsY;
};


XPCOMUtils.defineLazyGetter(koSciMozWrapper.prototype, "_log", function() {
    return Cu.import("chrome://komodo/content/library/logging.js", {})
             .logging
             .getLogger("scimoz.wrapper");
});


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
    };

// XPCOM registration of class.
var components = [koSciMozWrapper];
const NSGetFactory = XPCOMUtils.generateNSGetFactory(components);
