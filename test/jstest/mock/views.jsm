ko.views = {
    get manager() this,
};
(function() {

const { classes: Cc, interfaces: Ci, utils: Cu } = Components;

/**
 * Create a new mock scimoz
 * @param aText {String} The text to prefill
 */
function SciMozMock(aText) {
    this.text = aText || "";
    this.currentPos = this.anchor = 0;
}
this.SciMozMock = SciMozMock;

SciMozMock.prototype.charPosAtPosition =
    function SciMozMock_charPosAtPosition(pos)
        pos < 0 ? this.currentPos : pos;

SciMozMock.prototype.gotoPos =
    function SciMozMock_gotoPos(pos)
        this.currentPos = pos;

SciMozMock.prototype.ensureVisibleEnforcePolicy =
    function SciMozMock_ensureVisibleEnforcePolicy()
        void(0);

SciMozMock.prototype.hideSelection =
    function SciMozMock_hideSelection(aHide)
        void(0);

SciMozMock.prototype.lineFromPosition =
    function SciMozMock_lineFromPosition(pos)
        (this.text.substr(0, pos).match(/\n/g) || []).length;

SciMozMock.prototype.setSelection =
SciMozMock.prototype.setSel =
    function SciMozMock_setSel(start, end) {
        if (end < 0) end = this.text.length;
        if (start < 0) start = end;
        [this.anchor, this.currentPos] = [start, end];
    };

Object.defineProperty(SciMozMock.prototype, "selText", {
    get: function() this.text.substring(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "selectionStart", {
    get: function() Math.min(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

Object.defineProperty(SciMozMock.prototype, "selectionEnd", {
    get: function() Math.max(this.anchor, this.currentPos),
    enumerable: true, configurable: true});

SciMozMock.prototype.positionAtChar =
    function SciMozMock_positionAtChar(charPos)
        charPos;

SciMozMock.prototype.chooseCaretX =
    function SciMozMock_chooseCaretX()
        void(0);

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
}
this.ViewMock = ViewMock;

}).apply(ko.views);

ko.views.currentView = new ko.views.ViewMock();
