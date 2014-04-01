/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2013
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */

const {classes: Cc, interfaces: Ci, utils: Cu} = Components;
Cu.import("resource://komodo-jstest/JSTest.jsm");
const {logging} = Cu.import("chrome://komodo/content/library/logging.js", {});
const log = logging.getLogger("test.prefs.js");

/**
 * Preference Set Tests
 */
function PrefsTestCase() {
}

PrefsTestCase.prototype = new TestCase();

/**
 * Test the global preference service.
 */
PrefsTestCase.prototype.test_service = function() {
  var svc = Cc["@activestate.com/koPrefService;1"].getService();
  var val = svc.prefs.getLongPref("screenX");
  this.assertEquals(val,
		    svc.getPrefs("global").getLongPref("screenX"),
		    "svc.prefs appears to not be svc.getPrefs('global')");
  svc.saveState();
  log.info("Preference set service seemed to work");
};

// Test the bubbling of preferences through the "preference set tree".
// Preference sets are arranged in Komodo in a tree structure. At the root
// of the tree, the root preference set contains preference settings which are
// global across the entire application. The leaves of the tree are associated
// with particular Komodo application objects, such as editor buffers.
PrefsTestCase.prototype.test_bubbling = function() {
  log.info("Testing preference bubbling...");

  // Create a "root" preference set.
  // In Komodo, the root preference set contains preferences which are global
  // across the entire application.
  var rootPrefSet = Cc["@activestate.com/koPreferenceRoot;1"]
                      .createInstance(Ci.koIPreferenceSet);

  // Add a few global preferences.
  rootPrefSet.setStringPref('text.color', 'blue');
  rootPrefSet.setStringPref('text.size', '14pt');
  rootPrefSet.setBooleanPref('only.in.parent', true);
  rootPrefSet.setDoublePref('double-val', 3.14);
  rootPrefSet.setDoublePref('long-val', 3);

  var subPrefSet = Cc["@activestate.com/koPreferenceSet;1"]
		     .createInstance(Ci.koIPreferenceSet);

  rootPrefSet.setPref("subPrefSet", subPrefSet);
  subPrefSet.setStringPref("text.color", "cyan");

  var subOrderedSet = Cc["@activestate.com/koOrderedPreference;1"]
			.createInstance(Ci.koIOrderedPreference);
  rootPrefSet.setPref("subOrderedSet", subOrderedSet);
  subOrderedSet.appendStringPref("one");

  this.assertEquals(rootPrefSet.getStringPref('text.color'), "blue",
		    "unexpected text.color");
  this.assertEquals(rootPrefSet.getStringPref('text.size'), '14pt',
		    "unexpected text.size");
  // Ensure some type-safety - don't want to be capable of getting simple prefs
  // We now instantiate a preference set whose parent preference set in the
  // preference tree is the root preference set.
  var editorPrefSet = Cc["@activestate.com/koPreferenceRoot;1"]
			.createInstance(Ci.koIPreferenceRoot);
  editorPrefSet.inheritFrom = rootPrefSet;

  // Add in a preference which is also contained in the root preference set.
  // This preference will 'override' the preference in the root preference set.
  editorPrefSet.setStringPref('text.color', 'red');

  this.assertEquals(editorPrefSet.getStringPref('text.color'), 'red',
		    "unexpected editorPrefSet text.color");

  this.assertTrue(editorPrefSet.getBooleanPref("only.in.parent"),
		  "can't find only.in.parent");

  // this comes from the parent.
  this.assertEquals(editorPrefSet.getStringPref('text.size'),
		    rootPrefSet.getStringPref('text.size'),
		    "preference bubbling did not work");

  // override it locally now.
  editorPrefSet.setStringPref('text.size', '24pt');
  this.assertNotEquals(editorPrefSet.getStringPref('text.size'),
		       rootPrefSet.getStringPref('text.size'),
		       "preference bubbling did not work after explicit set");
  log.info("Preference pickling seemed to work");
  // Try cloning the preference set.
  var clonedRoot = rootPrefSet.clone();
  this.assertEquals(clonedRoot.getStringPref("text.color"),
		    rootPrefSet.getStringPref("text.color"),
		    "cloned pref set differs before change");

  rootPrefSet.setStringPref("text.color", "red");
  clonedRoot.setStringPref("text.color", "green");
  this.assertEquals(clonedRoot.getStringPref("text.color"), "green",
		    "cloned pref set differs after change");
  this.assertEquals(rootPrefSet.getStringPref("text.color"), "red",
		    "cloned pref set differs after change");

  // subPrefSet should be a correct copy.
  var clonedSubPrefSet = clonedRoot.getPref("subPrefSet");
  this.assertEquals(subPrefSet.getStringPref("text.color"),
		    clonedSubPrefSet.getStringPref("text.color"),
		    "cloned subPrefSet doesn't have correct values");
  subPrefSet.setStringPref("text.color", "red");
  this.assertNotEquals(subPrefSet.getStringPref("text.color"),
		       clonedSubPrefSet.getStringPref("text.color"),
		       "cloned subPrefSet doesn't have correct values after change");
  // set some new values in the cloned set, and make sure they make it after update()
  clonedSubPrefSet.setBooleanPref("new.in.cloned", 1)

  // editor prefset should still be parented at the root.
  if (editorPrefSet.hasPref("text.color")) {
    editorPrefSet.deletePref("text.color");
  }
  this.assertEquals(editorPrefSet.getStringPref("text.color"),
		    rootPrefSet.getStringPref("text.color"),
		    "editor doesn't seem correctly parented");
  // update the root with the changed version.
  rootPrefSet.update(clonedRoot);
  this.assertEquals(clonedRoot.getStringPref("text.color"),
		    rootPrefSet.getStringPref("text.color"),
		    "the update of the root pref set did not work");
  this.assertEquals(subPrefSet.getStringPref("text.color"),
		    clonedSubPrefSet.getStringPref("text.color"),
		    "subPrefSet doesn't have correct values after root update");
  // check subPrefSet has also been updated.
  this.assertTrue(subPrefSet.getBooleanPref("new.in.cloned"),
		  "subPrefSet doesn't have the new value added to the cloned set");

  log.info("Preference cloning seemed to work");
};

// Test preference deserialization.
PrefsTestCase.prototype._test_pref_deserialization = function (filename, prefset_cmp) {
  // Create a preference set. In the "real world", this object would be
  // owned by some Komodo component, like the project manager.

  var factory = Cc["@activestate.com/koPreferenceSetObjectFactory;1"]
                  .getService();

  var prefset = factory.deserializeFile(filename);

  this.assertTrue(prefset instanceof Ci.koIPreferenceRoot,
		  "deserialized file is not root");
  this.assertEquals(prefset.getStringPref('foo'),
		    prefset_cmp.getStringPref("foo"),
		    "serialized 'foo' was wrong");
  this.assertEquals(prefset.getLongPref('answer'),
		    prefset_cmp.getLongPref("answer"),
		    "serialized 'answer' was wrong");
  this.assertEquals(prefset.getBooleanPref('boolean'),
		    prefset_cmp.getBooleanPref("boolean"),
		    "serialized 'boolean' was wrong");
  this.assertLess(Math.abs(prefset.getDoublePref('pi') -
			   prefset_cmp.getDoublePref("pi")),
		  0.0001,
		  "serialized 'pi' was wrong");
  this.assertTrue(prefset.getBooleanPref('true'),
		  "serialized 'true' was wrong");
  this.assertFalse(prefset.getBooleanPref('false'),
		   "serialized 'false' was wrong");
  // Dump the ordered pref set
  var subPrefs = prefset.getPref("Numbers");
  this.assertEquals(subPrefs.length, 3,
		    "too many serialized numbers");
  this.assertEquals(subPrefs.getStringPref(0), "Zero",
		    "serialized number Zero was wrong");
  this.assertEquals(subPrefs.getStringPref(1), "One",
		    "serialized number One was wrong");
  this.assertEquals(subPrefs.getStringPref(2), "Two",
		    "serialized number Two was wrong");
}

// Test preference serialization.
PrefsTestCase.prototype._make_serialization_prefset = function (filename, prefset_cmp) {
  var prefset = Cc["@activestate.com/koPreferenceRoot;1"]
		  .createInstance(Ci.koIPreferenceRoot);
  prefset.id = 'root';

  // Add a couple of basic preferences.
  prefset.setStringPref('foo', 'bar');
  prefset.setLongPref('answer', 42);
  prefset.setDoublePref('pi', 3.14159265);
  prefset.setBooleanPref('true', 1);
  prefset.setBooleanPref('false', 0);
  prefset.setBooleanPref('boolean', 0);

  // Add an ordered pref set.
  var orderedPrefSet = Cc["@activestate.com/koOrderedPreference;1"]
                         .createInstance();
  orderedPrefSet.id = "Numbers";
  orderedPrefSet.appendStringPref("One");
  orderedPrefSet.appendStringPref("Two");
  orderedPrefSet.insertStringPref(0, "Zero");
  prefset.setPref(orderedPrefSet.id, orderedPrefSet);

  // Add a sub-preference-set.
  var subprefset = Cc["@activestate.com/koPreferenceSet;1"]
		     .createInstance(Ci.koIPreferenceSet);
  subprefset.setStringPref('active', 'state');
  subprefset.setStringPref('inactive', 'state');
  subprefset.id = 'subprefset';
  prefset.setPref(subprefset.id, subprefset);

  return prefset;
}

PrefsTestCase.prototype.test_serialization = function() {
  var prefset = this._make_serialization_prefset();
  var tempFileFactory = Cc['@activestate.com/koFileService;1']
                          .getService(Ci.koIFileService);
  var tempFilepath = tempFileFactory.makeTempName("preftest");
  prefset.serializeToFile(tempFilepath);
  this._test_pref_deserialization(tempFilepath, prefset);
  log.info("Preference serialization/deserialization seemed to work");
};

PrefsTestCase.prototype.test_cloned_serialization = function() {
  var prefset = this._make_serialization_prefset();
  var tempFileFactory = Cc['@activestate.com/koFileService;1']
			  .getService(Ci.koIFileService);
  var tempFilepath = tempFileFactory.makeTempName("preftest");
  prefset.clone().serializeToFile(tempFilepath);
  this._test_pref_deserialization(tempFilepath, prefset);

  // Try again, with a cloned/updated prefset
  prefset = this._make_serialization_prefset();
  var new_prefset = prefset.clone()
  // change some values
  new_prefset.setBooleanPref("boolean", 1);
  new_prefset.setStringPref('foo', 'spam');
  new_prefset.setLongPref('answer', 666);

  prefset.update(new_prefset)
  tempFilepath = tempFileFactory.makeTempName("preftest");
  prefset.serializeToFile(tempFilepath);
  this._test_pref_deserialization(tempFilepath, new_prefset);
  log.info("Cloned preference serialization/deserialization seemed to work");
};

PrefsTestCase.prototype.test_cache = function() {
  cache = Cc["@activestate.com/koPrefCache;1"].createInstance();
  const kCacheMaxLength = 9;
  cache.max_length = kCacheMaxLength;
  this.assertEquals(cache.max_length, kCacheMaxLength);
  prefs = new Array();
  for (let i = 0; i < 10; i++) {
    var pref = Cc["@activestate.com/koPreferenceSet;1"].createInstance();
    pref.id = "Pref " + i;
    pref.setLongPref("number", i);
    var op = Cc["@activestate.com/koOrderedPreference;1"].createInstance();
    op.appendLongPref(i);
    op.id = "ordered";
    pref.setPref(op.id, op);
    prefs[prefs.length] = pref;
    cache.setPref(pref);
    if (i < cache.max_length) {
      this.assertEquals(cache.length, i + 1,
			"Should have the same number of elts" +
			"- expect " + i + ", but got " + cache.length);
    }
    this.assertEquals(cache.max_length, kCacheMaxLength);
    this.assertLessEqual(cache.length, cache.max_length,
			 "Too many items in cache");
  }

  if (log.getEffectiveLevel() <= logging.LOG_DEBUG) {
    let ids = [];
    let e = cache.enumPreferences();
    while (e.hasMoreElements()) {
      ids.push(e.getNext().id);
    }
    log.debug("cache keys: " + ids.join(", "));
  }

  // item 0 should have been popped
  this.assertFalse(cache.hasPref(prefs[0].id),
		   "Should not have element 0 in the cache");
  this.assertTrue(cache.hasPref(prefs[1].id),
		  "Should have element 1 in the cache");
  // re-add element 1, and ensure it is at the top.
  var pref_add = prefs[1];
  cache.setPref(pref_add);
  var enumer = cache.enumPreferences();
  var pref_look = enumer.getNext();
  this.assertEquals(pref_look.getLongPref("number"),
		    pref_add.getLongPref("number"),
		    "Last item didn't move to the front");
  var index_expect = 9;
  var indexes_found = 1; // already have the first.
  while (enumer.hasMoreElements()) {
    pref_look = enumer.getNext();
    this.assertEquals(pref_look.getLongPref("number"),
		      index_expect,
		      "Got the wrong preference from the cache - was " +
			pref_look.getLongPref("number") + ", but expected " +
			index_expect);
    index_expect -= 1;
    indexes_found += 1;
  }
  this.assertEquals(indexes_found,
		    cache.max_length,
		    "Didn't enumerate all the items");

  // Dump the preferences to a file.
  var tempFileFactory = Cc['@activestate.com/koFileService;1']
                          .getService(Ci.koIFileService);
  var tempFilepath = tempFileFactory.makeTempName("preftest");
  cache.serializeToFile(tempFilepath);
  var factory = Cc["@activestate.com/koPreferenceSetObjectFactory;1"].getService();
  new_cache = factory.deserializeFile(tempFilepath);

  // Now check the deserialized version is the same as the original.
  var enumer_orig = cache.enumPreferences();
  var enumer_new = new_cache.enumPreferences();
  while (enumer_orig.hasMoreElements()) {
    this.assertTrue(enumer_new.hasMoreElements(),
		    "One enumerator has more elements, but not the other");
    pref_orig = enumer_orig.getNext();
    pref_new = enumer_new.getNext();
    this.assertEquals(pref_orig.id,
		      pref_new.id,
		      "The enumerators were not in synch (id)");
    this.assertEquals(pref_orig.getLongPref("number"),
		      pref_new.getLongPref("number"),
		      "The enumerators were not in synch (number)");
  }
  this.assertFalse(enumer_new.hasMoreElements(),
		   "Orig enumerator exhausted before the new one");
  log.info("Preference set cache seemed to work");
};

const JS_TESTS = ["PrefsTestCase"];
