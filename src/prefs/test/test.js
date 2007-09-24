/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/////////////////////////////////////////////////////////////
// Preference Set Test Script
// 
// Run this script using xpcshell. i.e. "xpcshell test.js"
// Scroll to the bottom to see where it starts.
/////////////////////////////////////////////////////////////

var num_errors = 0;

function logError(msg) {
	num_errors++;
	dump("TEST ERROR: " + msg + "\n");
}

// dump() with indentation.
function superdump(text, depth) {
  dump(depth + ":");
  for(var i = 0; i < depth; i++) {
	dump("  ");
  }
  dump(text);
}

// Dump a DOM node object depth-first.
function dump_dom(node, depth) {
  superdump("nodeName: " + node.nodeName + "\n", depth);
  superdump("nodeValue: " + node.nodeValue + "\n", depth);
  superdump("nodeType: " + node.nodeType + "\n", depth);
  superdump("hasChildNodes(): " + node.hasChildNodes() + "\n", depth);
  superdump("parentNode: " + node.parentNode + "\n", depth);

  if(node.hasChildNodes()) {
	var o1 = {};
	var o2 = {};
	node.getChildNodes(o1, o2);

	var nodes = o1.value;
	
	for(var i = 0; i < nodes.length; i++) {
	  var n = nodes[i];
	  dump_dom(n, depth+1);
	}
  }
}

function _check(condition, error) {
	if (!condition) {
		if (error == undefined)
			error = "<condition failed>";
		logError(error);
	}
}

function test_pref() {}
test_pref.prototype = {
  serialize: function(file) {
	file.write("  <!-- test.js: serializing test_pref object -->\n");
	file.write("  <flufmonster>\n");
	file.write("    <globble>" + this.globble + "</globble>\n");
	file.write("    <snicker>" + this.snicker + "</snicker>\n");
	file.write("  </flufmonster>\n");
  },
  QueryInterface: function(iid) {
	var KOISERIALIZABLE_IID = 
	Components.ID("{1912A0AE-D9A4-4f55-A4E0-A80DAD21396D}");
	if (!iid.equals(Components.interfaces.nsISupports) &&
		!iid.equals(KOISERIALIZABLE_IID))
	throw Components.results.NS_ERROR_NO_INTERFACE;
	return this;
  }
}

// Test the global preference service.
function testPrefService(){
	var svc = Components.classes["@activestate.com/koPrefService;1"].getService();
	var val = svc.prefs.getLongPref("screenX");
	_check(val == svc.getPrefs("global").getLongPref("screenX"), "svc.prefs appears to not be svc.getPrefs('global')");
	svc.saveState();
	svc.shutDown();
	dump("Preference set service seemed to work\n");
}

// Test the bubbling of preferences through the "preference set tree".
// Preference sets are arranged in Komodo in a tree structure. At the root
// of the tree, the root preference set contains preference settings which are
// global across the entire application. The leaves of the tree are associated
// with particular Komodo application objects, such as editor buffers.
function testPrefBubbling() {
  dump("Testing preference bubbling...\n");

  // Create a "root" preference set.
  // In Komodo, the root preference set contains preferences which are global
  // across the entire application.
  rootPrefSet = Components.classes["@activestate.com/koPreferenceSet;1"].
	createInstance(Components.interfaces.koIPreferenceSet);

  // Add a few global preferences.
  rootPrefSet.setStringPref('text.color', 'blue');
  rootPrefSet.setStringPref('text.size', '14pt');
  rootPrefSet.setBooleanPref('only.in.parent', true);
  rootPrefSet.setDoublePref('double-val', 3.14);
  rootPrefSet.setDoublePref('long-val', 3);

  var subPrefSet = Components.classes["@activestate.com/koPreferenceSet;1"].
	     createInstance(Components.interfaces.koIPreferenceSet);

  rootPrefSet.setPref("subPrefSet", subPrefSet);
  subPrefSet.setStringPref("text.color", "cyan");

  var subOrderedSet = Components.classes["@activestate.com/koOrderedPreference;1"].
	     createInstance(Components.interfaces.koIOrderedPreference);
  rootPrefSet.setPref("subOrderedSet", subOrderedSet);
  subOrderedSet.appendStringPref("one");

  if (rootPrefSet.getStringPref('text.color') != "blue")
	  logError("text.color was wrong!");
  if (rootPrefSet.getStringPref('text.size') != '14pt')
	  logError("text.size was wrong!");
  // Ensure some type-safety - don't want to be capable of getting simple prefs
  // We now instantiate a preference set whose parent preference set in the
  // preference tree is the root preference set.
  editorPrefSet = Components.classes["@activestate.com/koPreferenceSet;1"].
	createInstance(Components.interfaces.koIPreferenceSet);
  editorPrefSet.parent = rootPrefSet;

  // Add in a preference which is also contained in the root preference set.
  // This preference will 'override' the preference in the root preference set.
  editorPrefSet.setStringPref('text.color', 'red');

  if (editorPrefSet.getStringPref('text.color') != 'red')
	  logError("editorPrefSet text.color wrong!");

  if (!editorPrefSet.getBooleanPref("only.in.parent"))
      logError("Oops.  Can't find only.in.parent!");

  // this comes from the parent.
  if(editorPrefSet.getStringPref('text.size') !=
	 rootPrefSet.getStringPref('text.size')) {
	logError("Oops. Preference bubbling did not work.");
  }
  // override it locall now.
  editorPrefSet.setStringPref('text.size', '24pt');
  if(editorPrefSet.getStringPref('text.size') ==
	 rootPrefSet.getStringPref('text.size')) {
	logError("Oops. Preference bubbling did not work after explicit set.");
  }
  dump("Preference pickling seemed to work\n");
  // Try cloning the preference set.
  clonedRoot = rootPrefSet.clone();
  if (clonedRoot.getStringPref("text.color") != rootPrefSet.getStringPref("text.color"))
	  logError("Cloned pref set differs before change!");

  rootPrefSet.setStringPref("text.color", "red");
  clonedRoot.setStringPref("text.color", "green");
  if (clonedRoot.getStringPref("text.color") != "green" || rootPrefSet.getStringPref("text.color") != "red")
	  logError("Cloned pref set differs after change!");

  // subPrefSet should be a correct copy.
  clonedSubPrefSet = clonedRoot.getPref("subPrefSet")
  if (subPrefSet.getStringPref("text.color") != clonedSubPrefSet.getStringPref("text.color"))
	  logError("cloned subPrefSet doesn't have correct values");
  subPrefSet.setStringPref("text.color", "red");
  if (subPrefSet.getStringPref("text.color") == clonedSubPrefSet.getStringPref("text.color"))
	  logError("cloned subPrefSet doesn't have correct values after change");
  // set some new values in the cloned set, and make sure they make it after update()
  clonedSubPrefSet.setBooleanPref("new.in.cloned", 1)

  // editor prefset should still be parented at the root.
  if (editorPrefSet.hasPref("text.color"))
	  editorPrefSet.deletePref("text.color");
  if (editorPrefSet.getStringPref("text.color") != rootPrefSet.getStringPref("text.color"))
    logError("editor doesn't seem correctly parented");
  // update the root with the changed version.
  rootPrefSet.update(clonedRoot);
  if (clonedRoot.getStringPref("text.color") != rootPrefSet.getStringPref("text.color"))
    logError("The update of the root pref set did not work");
  if (subPrefSet.getStringPref("text.color") != clonedSubPrefSet.getStringPref("text.color"))
	  logError("subPrefSet doesn't have correct values after root update");
  // check subPrefSet has also been updated.
  if (!subPrefSet.getBooleanPref("new.in.cloned"))
	  logError("subPrefSet doesn't have the new value added to the cloned set");
  
  dump("Preference cloning seemed to work\n");
}

// Test preference deserialization.
function testPrefDeserialization(filename, prefset_cmp) {
  // Create a preference set. In the "real world", this object would be
  // owned by some Komodo component, like the project manager.

  var factory = Components.classes["@activestate.com/koPreferenceSetObjectFactory;1"].
	getService();

  factory.deserializeFile(filename);

  if (prefset.getStringPref('foo') != prefset_cmp.getStringPref("foo"))
    logError("serialized 'foo' was wrong");
  if (prefset.getLongPref('answer') != prefset_cmp.getLongPref("answer"))
    logError("serialized 'answer' was wrong");
  if (prefset.getBooleanPref('boolean') != prefset_cmp.getBooleanPref("boolean"))
    logError("serialized 'boolean' was wrong");
  if (Math.abs(prefset.getDoublePref('pi')-prefset_cmp.getDoublePref("pi")) > 0.0001)
    logError("serialized 'pi' was wrong");
  if (!prefset.getBooleanPref('true'))
    logError("serialized 'true' was wrong");
  if (prefset.getBooleanPref('false'))
    logError("serialized 'false' was wrong");
  // Dump the ordered pref set
  var subPrefs = prefset.getPref("Numbers");
  if (subPrefs.length != 3)
    logError("Too many serialized numbers");
  if (subPrefs.getStringPref(0) != "Zero")
    logError("serialized number Zero was wrong");
  if (subPrefs.getStringPref(1) != "One")
    logError("serialized number One was wrong");
  if (subPrefs.getStringPref(2) != "Two")
    logError("serialized number Two was wrong");
}

// Test preference serialization.
function _makeSerializationPrefset() {
  prefset = Components.classes["@activestate.com/koPreferenceSet;1"].
	createInstance(Components.interfaces.koIPreferenceSet);
  prefset.id = 'root';

  // Add a couple of basic preferences.
  prefset.setStringPref('foo', 'bar');
  prefset.setLongPref('answer', 42);
  prefset.setDoublePref('pi', 3.14159265);
  prefset.setBooleanPref('true', 1);
  prefset.setBooleanPref('false', 0);
  prefset.setBooleanPref('boolean', 0);

  // Add an ordered pref set.
  orderedPrefSet = Components.classes["@activestate.com/koOrderedPreference;1"].createInstance();
  orderedPrefSet.id = "Numbers";
  orderedPrefSet.appendStringPref("One");
  orderedPrefSet.appendStringPref("Two");
  orderedPrefSet.insertStringPref(0, "Zero");

  prefset.setPref(orderedPrefSet.id, orderedPrefSet);
/***
  // Add a custom preference.
  // The test_pref object supports the koIPreference interface.
  var glorb = new test_pref();
  glorb.globble = "bar";
  glorb.snicker = "baz";
  glorb.prefName = "flufmonster";
  prefset.setPref(glorb.id, glorb);
***/
  // Add a sub-preference-set.
  var subprefset = Components.classes["@activestate.com/koPreferenceSet;1"].
	createInstance(Components.interfaces.koIPreferenceSet);
  subprefset.setStringPref('active', 'state');
  subprefset.setStringPref('inactive', 'state');
  subprefset.id = 'subprefset';
  prefset.setPref(subprefset.id, subprefset);
  return prefset;
}

function testPrefSerialization() {
  prefset = _makeSerializationPrefset();
  tempFileFactory = Components.classes['@activestate.com/koTempFileFactory;1'].getService();
  tempFile = tempFileFactory.MakeTempFile("preftest", "w");
  prefset.serialize(tempFile);
  var path = tempFile.file.path;
  tempFile.close();
  testPrefDeserialization(path, prefset);
  dump("Preference serialization/deserialization seemed to work\n");
}

function testClonedPrefSerialization() {
  prefset = _makeSerializationPrefset();
  tempFileFactory = Components.classes['@activestate.com/koTempFileFactory;1'].getService();
  tempFile = tempFileFactory.MakeTempFile("preftest", "w");
  prefset.clone().serialize(tempFile);
  var path = tempFile.file.path;
  tempFile.close();
  testPrefDeserialization(path, prefset);

  // Try again, with a cloned/updated prefset  
  prefset = _makeSerializationPrefset();
  tempFileFactory = Components.classes['@activestate.com/koTempFileFactory;1'].getService();
  tempFile = tempFileFactory.MakeTempFile("preftest", "w");
  new_prefset = prefset.clone()
  // change some values
  new_prefset.setBooleanPref("boolean", 1);
  new_prefset.setStringPref('foo', 'spam');
  new_prefset.setLongPref('answer', 666);

  prefset.update(new_prefset)
  prefset.serialize(tempFile);
  var path = tempFile.file.path;
  tempFile.close();
  testPrefDeserialization(path, new_prefset);
  dump("Cloned preference serialization/deserialization seemed to work\n");
}

function testPreferenceSetCache() {
	cache = Components.classes["@activestate.com/koPrefCache;1"].createInstance();
	cache.max_length = 9;
	_check(cache.max_length == 9);
	prefs = new Array();
	for (var i=0;i<10;i++) {
		var pref= Components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
		pref.id = "Pref " + i;
		pref.setLongPref("number", i);
		var op = Components.classes["@activestate.com/koOrderedPreference;1"].createInstance();
		op.appendLongPref(i);
		op.id = "ordered"
		pref.setPref(op.id, op)
		prefs[prefs.length] = pref;
		cache.setPref( pref );
		if (i < cache.max_length)
			_check(cache.length == i+1, "Should have the same number of elts - expect " + i + ", but got " + cache.length);
	}

	// item 0 should have been popped
	_check(!cache.hasPref(prefs[0].id), "Should not have element 0 in the cache");
	_check(cache.hasPref(prefs[1].id), "Should have element 1 in the cache");
	// re-add element 1, and ensure it is at the top.
	var pref_add = prefs[1];
	cache.setPref(pref_add);
	var enumer = cache.enumPreferences();
	var pref_look = enumer.getNext();
	if (pref_look.getLongPref("number") != pref_add.getLongPref("number"))
		logError("Last item didn't move to the front");
	var index_expect = 9;
	var indexes_found = 1; // already have the first.
	while (enumer.hasMoreElements()) {
		pref_look = enumer.getNext();
		_check(pref_look.getLongPref("number")== index_expect, "Got the wrong preference from the cache - was " + pref_look.getLongPref("number") + ", but expected " + index_expect);
		index_expect -= 1;
		indexes_found += 1;
	}
	_check (indexes_found == cache.max_length, "Didn't enumerate all the items");

	// Dump the preferences to a file.
	tempFileFactory = Components.classes['@activestate.com/koTempFileFactory;1'].getService();
	tempFile = tempFileFactory.MakeTempFile("preftest", "w");
	cache.serialize(tempFile);
	var path = tempFile.file.path;
	tempFile.close();

	var factory = Components.classes["@activestate.com/koPreferenceSetObjectFactory;1"].getService();
	new_cache = factory.deserializeFile(path);

	// Now check the deserialized version is the same as the original.
	var enumer_orig = cache.enumPreferences();
	var enumer_new = new_cache.enumPreferences();
	while (enumer_orig.hasMoreElements()) {
		_check( enumer_new.hasMoreElements(), "One enumerator has more elements, but not the other");
		pref_orig = enumer_orig.getNext();
		pref_new = enumer_new.getNext();
		_check(pref_orig.id == pref_new.id, "The enumerators were not in synch (id)");
		_check(pref_orig.getLongPref("number")== pref_new.getLongPref("number"), "The enumerators were not in synch (number)");
	}
	_check(!enumer_new.hasMoreElements(), "Orig enumerator exhausted before the new one");

	dump("Preference set cache seemed to work\n");
}

dump("Beginning preference set test suite...\n");

testPrefService();
testPreferenceSetCache();
testPrefBubbling();
testPrefSerialization();
testClonedPrefSerialization();

if (num_errors) {
	dump("**** Found " + num_errors + " errors in the test\n");
}