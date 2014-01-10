ko.views = {
    get manager() this,
    get topView() this.currentView,
};
(function() {

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import("resource://gre/modules/XPCOMUtils.jsm");
let logging = Cu.import("chrome://komodo/content/library/logging.js", {}).logging;
let log = logging.getLogger("views.mock");

/**
 * Create a new mock KoDoc
 * @note The parameters are all optional, and use a dictionary.
 * @param text {String} The text to pre-fill
 * @param url {String} The
 */
function KoDocMock(aParams) {
    if (typeof(aParams) == "undefined") {
        aParams = {};
    }
    this.displayPath = aParams.displayPath ||
        Cc["@mozilla.org/uuid-generator;1"]
          .getService(Ci.nsIUUIDGenerator)
          .generateUUID()
          .number;
}

/**
 * Create a mock <scintilla> element
 */
function ScintillaMock(aView) {
    this._view = aView;
}

Object.defineProperty(ScintillaMock.prototype, "scimoz", {
    get: function() this._view.scimoz,
    configurable: true, enumerable: true,
});


XPCOMUtils.defineLazyGetter(ScintillaMock.prototype, "scheme",
    function() Cc['@activestate.com/koScintillaSchemeService;1']
                 .getService(Ci.koIScintillaSchemeService)
                 .getScheme("Default"));

/**
 * Create a new mock view
 * @note The parameters are all optional, and use a dictionary.
 * @param text {String} The text to pre-fill
 */
function ViewMock(aParams) {
    if (typeof(aParams) == "undefined") {
        aParams = {};
    }
    this.uid = Cc["@mozilla.org/uuid-generator;1"]
                 .getService(Ci.nsIUUIDGenerator)
                 .generateUUID()
                 .number;
    this.koDoc = new KoDocMock({});
    this.scimoz = Cc['@activestate.com/ISciMozHeadless;1']
		 .createInstance(Ci.ISciMoz);
    this.scimoz.text = aParams.text || "";
    this.scintilla = new ScintillaMock(this);
}
this.ViewMock = ViewMock;

ViewMock.prototype.getViews = function ViewMock_getViews(aRecurse)
    [this];

function ViewBookmarkableMock(aParams) {
    ViewMock.apply(this, Array.slice(arguments));
    this.removeAllBookmarks();
}
this.ViewBookmarkableMock = ViewBookmarkableMock;

ViewBookmarkableMock.prototype = Object.create(ViewMock.prototype);
ViewBookmarkableMock.prototype.QueryInterface =
    XPCOMUtils.generateQI([Ci.koIBookmarkableView]);


ViewBookmarkableMock.prototype.addBookmark =
function ViewBookmarkableMock_addBookmark(aLineNo) {
    log.debug("ViewBookmarkable: addBookmark: " + aLineNo);
    this._bookmarks[aLineNo] = true;
}

ViewBookmarkableMock.prototype.removeBookmark =
function ViewBookmarkableMock_removeBookmark(aLineNo) {
    log.debug("ViewBookmarkable: removeBookmark: " + aLineNo);
    delete this._bookmarks[aLineNo];
}

ViewBookmarkableMock.prototype.removeAllBookmarks =
function ViewBookmarkableMock_removeAllBookmarks() {
    log.debug("ViewBookmarkable: removeAllBookmarks");
    this._bookmarks = {};
}

ViewBookmarkableMock.prototype.hasBookmark =
function ViewBookmarkableMock_hasBookmark(aLineNo)
    Object.hasOwnProperty.call(this._bookmarks, aLineNo);

Object.defineProperty(ViewBookmarkableMock.prototype, "bookmarks", {
    get: function() Object.keys(this._bookmarks).map(function(n) parseInt(n, 10)),
    configurable: true, enumerable: true,
});

}).apply(ko.views);

ko.views.currentView = new ko.views.ViewMock();
