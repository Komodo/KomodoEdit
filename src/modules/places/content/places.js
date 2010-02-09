// Copyright (c) 2000-2010 ActiveState Software Inc.
// See the file LICENSE.txt for licensing information.

/* Places -- projects v2
 *
 * Defines the "ko.places" namespace.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
ko.places = {};

var gPlacesViewMgr = null;

(function() {

// Yeah, not really a class per se, but it acts like one, so
// give it an appropriate name.
function viewMgrClass() {
};

viewMgrClass.prototype = {
  focus: function() {
        dump("places: viewMgr.focus()\n");
    },
  updateView: function() {
        dump("places: viewMgr.updateView()\n");
    },
  __ZIP__: null
};  

this.onLoad = function places_onLoad() {
    dump(">> ko.places.onLoad\n");
    this.viewMgr = gPlacesViewMgr = new viewMgrClass();
    dump("<< ko.places.onLoad, gPlacesViewMgr:" + gPlacesViewMgr + "\n");
};

this.onUnload = function places_onUnload() {
};

}).apply(ko.places);
