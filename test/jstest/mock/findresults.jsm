(function ko_findresults() {

var { classes: Cc, interfaces: Ci, utils: Cu } = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
Cu.import("resource://komodo-jstest/mock/mock.jsm", {})
  .import(ko, "logging", "TreeBoxObject");
let log = ko.logging.getLogger("findresults.mock");

function FindResultsTab(aId) {
    this.id = aId;
    this._locked = false;
    this._shown = false;
    this.inProgress = false;
    this.view = Cc["@activestate.com/koFindResultsView;1"]
                  .createInstance(Ci.koIFindResultsView);
    this.view.id = this.id;
    this.treeBoxObject = new ko.TreeBoxObject(this.view);
    this.view.setTree(this.treeBoxObject);
    this._reset();
}

FindResultsTab.prototype._reset = function FindResultsTab__reset() {
    this.view.Clear();
    this.success = false;
    this.numResults = -1;
    this.numFiles = -1;
    this.numFilesSearched = -1;
    this.journalId = "<No journal id>";
};

FindResultsTab.prototype.configure =
function FindResultsTab_configure(aPattern, aPatternAlias, aReplacement,
                                  aContext, aOptions, aSupportsUndo)
{
    this.context_ = aContext; // this is public, but "context" is a xpidl keyword
    this._pattern = aPattern;
    this._patternAlias = aPatternAlias;
    this._replacement = aReplacement;
    this._options = aOptions;
    this._supportsUndo = !!aSupportsUndo;
    this._desc = undefined;
    this._important = false;
};

Object.defineProperty(FindResultsTab.prototype, "locked", {
    get: function() this._locked,
    configurable: true, enumerable: true,
});

FindResultsTab.prototype.setDescription = function FindResultsTab_setDescription(aDesc, aImportant) {
    this._desc = aDesc;
    this._important = aImportant;
    var marker = aImportant ? "***" : "";
    log.debug("setDescription: " + [marker, aDesc, marker].join(" ").replace(/^ | $/g, ""));
};

FindResultsTab.prototype.searchStarted = function FindResultsTab_searchStarted() {
    log.debug("searchStarted(" + this.id + ")");
    this.inProgress = true;
    this._reset();
};

FindResultsTab.prototype.searchFinished =
function FindResultsTab_searchFinished(aSuccess, aNumResults, aNumFiles, aNumFilesSearched, aJournalId) {
    log.debug("searchFinished(" + this.id + "): " + Array.slice(arguments));
    this.success = aSuccess;
    this.numResults = aNumResults;
    this.numFiles = aNumFiles;
    this.numFilesSearched = aNumFilesSearched;
    this.journalId = aJournalId;
    this.inProgress = false;
};

FindResultsTab.prototype.show = function FindResultsTab_show(aFocus) {
    log.debug("Showing tab " + this.id);
    for each (let tab in ko.findresults._tabs) {
        tab._shown = false;
    }
    this._shown = true;
};

ko.findresults = {
    _tabs: [],
    getTab: function ko_findresults_getTab(aPreferred) {
        if ((aPreferred in this._tabs) && !this._tabs[aPreferred].locked) {
            return this._tabs[aPreferred];
        }
        for each (tab in this._tabs) {
            if (!tab.locked) {
                return tab;
            }
        }
        return this.create(this._tabs.length);
    },
    create: function ko_findresults_create(aId) {
        if (typeof(aId) == "undefined") {
            TestCase.fail("Attempting to create find result with no id");
        }
        if (aId in this._tabs) {
            TestCase.fail("Attempting to create find result id " + aId +
                          ", which already exists");
        }
        log.debug("ko.findresults.create: creating new tab " + aId);
        return this._tabs[aId] = new FindResultsTab(aId);
    },
};

})();
