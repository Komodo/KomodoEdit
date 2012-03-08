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
 * Create a new mock scimoz
 * @param aText {String} The text to prefill
 */
function SciMozMock(aText) {
    this.text = aText || "";
    this.currentPos = this.anchor = 0;
    this.eOLMode = Ci.ISciMoz.SC_EOL_LF;
}
this.SciMozMock = SciMozMock;

SciMozMock.prototype.charPosAtPosition =
    function SciMozMock_charPosAtPosition(pos)
        pos < 0 ? this.currentPos : pos;

SciMozMock.prototype.chooseCaretX =
    function SciMozMock_chooseCaretX()
        void(0);

SciMozMock.prototype.ensureVisibleEnforcePolicy =
    function SciMozMock_ensureVisibleEnforcePolicy()
        void(0);

SciMozMock.prototype.getLineEndPosition =
    function SciMozMock_getLineEndPosition(aLine) {
        let lines = this.text.match(new RegExp("(?:[^\n]*\n){" + (aLine + 1) + "}", "m")) || [""];
        let lastLine = lines.pop().replace(/\n$/, "");
        return lines.reduce(function(n, s) n + s.length, 0) + lastLine.length;
    };

SciMozMock.prototype.getTextRange =
    function SciMozMock_getTextRange(aStart, aEnd)
        this.text.substring(aStart, aEnd);

SciMozMock.prototype.gotoPos =
    function SciMozMock_gotoPos(pos)
        this.currentPos = pos;

SciMozMock.prototype.hideSelection =
    function SciMozMock_hideSelection(aHide)
        void(0);

SciMozMock.prototype.lineFromPosition =
    function SciMozMock_lineFromPosition(pos)
        (this.text.substr(0, pos).match(/\n/g) || []).length;

SciMozMock.prototype.positionAtChar =
    function SciMozMock_positionAtChar(start, charoffset)
        start + charoffset;

SciMozMock.prototype.positionFromLine =
    function SciMozMock_positionFromLine(aLine)
        this.text.match(new RegExp("(?:[^\n]*\n){" + aLine + "}", "m"))
            .reduce(function(n, s) n + s.length, 0);

Object.defineProperty(SciMozMock.prototype, "selectionEnd", {
    get: function() Math.max(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "selectionStart", {
    get: function() Math.min(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "selText", {
    get: function() this.text.substring(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

SciMozMock.prototype.setSelection =
SciMozMock.prototype.setSel =
    function SciMozMock_setSel(start, end) {
        if (end < 0) end = this.text.length;
        if (start < 0) start = end;
        log.debug("setSelection: [" + start + "," + end + "] = " +
                  this.getTextRange(start, end));
        [this.anchor, this.currentPos] = [start, end];
    };


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

/**
 * Create a new mock view
 * @note The parameters are all optional, and use a dictionary.
 * @param text {String} The text to pre-fill
 */
function ViewMock(aParams) {
    if (typeof(aParams) == "undefined") {
        aParams = {};
    }
    this.scimoz = new SciMozMock(aParams.text || "");
    this.uid = Cc["@mozilla.org/uuid-generator;1"]
                 .getService(Ci.nsIUUIDGenerator)
                 .generateUUID()
                 .number;
    this.koDoc = new KoDocMock({});
    this.scimoz = new SciMozMock();
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
