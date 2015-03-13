# Copyright (c) 2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""
Tests for the preferences service
"""
import logging
import os
import tempfile
import unittest
from xml.etree import ElementTree as ET

from xpcom import COMException
from xpcom.components import classes as Cc, interfaces as Ci
from xpcom import nsError as Cr
from xpcom.client import Component
from xpcom.server import UnwrapObject

from testlib import tag

log = logging.getLogger("test.koprefs")

def _deserializePrefString(content):
    fd, path = tempfile.mkstemp(suffix=".xml")
    try:
        os.write(fd, content)
        os.close(fd)
        return (Cc["@activestate.com/koPreferenceSetObjectFactory;1"]
                    .getService()
                    .deserializeFile(path))
    finally:
        os.remove(path)

def _serializePrefToString(prefset):
    fd, path = tempfile.mkstemp(suffix=".xml")
    os.close(fd)
    try:
        prefset.serializeToFile(path)
        return file(path).read()
    finally:
        os.remove(path)

def prettify_tree(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            prettify_tree(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
    return elem

class PrefsCloneTestCase(unittest.TestCase):
    """Test that cloning prefs actually gives new prefs (bug 98861)"""
    _children = {"string": "hello",
                 "long": 42,
                 "double": 3.14159,
                 "boolean": False}

    def _run_test(self, old, getter, deleter, val, desc):
        self.assertEqual(getter(old),
                         val,
                         "pref %s was not set correctly (expected %s got %s)" % (
                            desc, val, getter(old)))
        new = old.clone()
        self.assertEqual(getter(new),
                         val,
                         "clone failed for %s" % (desc,))
        deleter(new)
        with self.assertRaises(COMException) as raiser:
            getter(new)
        self.assertEqual(raiser.exception.errno, Cr.NS_ERROR_UNEXPECTED)
        self.assertEqual(getter(old),
                         val,
                         "%s deleted on clone" % (desc,))

    def test_unordered_simple(self):
        for typ, val in self._children.items():
            old = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
            getattr(old, "set%sPref" % (typ.title()))("test_pref", val)
            getter = lambda pref: getattr(pref, "get%sPref" % (typ.title()))("test_pref")
            deleter = lambda pref: pref.deletePref("test_pref")
            self._run_test(old, getter, deleter, val, "unordered/%s" % (typ,))

    def test_unordered_unordered(self):
        old = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        child = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        child.setLongPref("child_pref", 42)
        old.setPref("test_pref", child)
        getter = lambda pref: pref.getPref("test_pref").getLongPref("child_pref")
        deleter = lambda pref: pref.deletePref("test_pref")
        self._run_test(old, getter, deleter, 42, "unordered/unordered")

    def test_unordered_ordered(self):
        old = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        child = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        child.appendLongPref(42)
        old.setPref("test_pref", child)
        getter = lambda pref: pref.getPref("test_pref").getLongPref(0)
        deleter = lambda pref: pref.deletePref("test_pref")
        self._run_test(old, getter, deleter, 42, "unordered/ordered")

    def test_ordered_simple(self):
        for typ, val in self._children.items():
            old = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
            getattr(old, "append%sPref" % (typ.title()))(val)
            getter = lambda pref: getattr(pref, "get%sPref" % (typ.title()))(0)
            deleter = lambda pref: pref.deletePref(0)
            self._run_test(old, getter, deleter, val, "ordered/%s" % (typ,))

    def test_ordered_string(self):
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        child = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        child.appendString("hello")
        base.setPref("child", child)
        prefset = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        prefset.inheritFrom = base
        self.assertEquals(prefset.getPref("child").length, 1)
        clone = prefset.clone()
        self.assertEquals(clone.getPref("child").length, 1)

    def test_ordered_unordered(self):
        old = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        child = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        child.setLongPref("child_pref", 42)
        old.appendPref(child)
        getter = lambda pref: pref.getPref(0).getLongPref("child_pref")
        deleter = lambda pref: pref.getPref(0).deletePref("child_pref")
        self._run_test(old, getter, deleter, 42, "ordered/unordered")

    def test_ordered_ordered(self):
        old = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        child = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        child.appendLongPref(42)
        old.appendPref(child)
        getter = lambda pref: pref.getPref(0).getLongPref(0)
        deleter = lambda pref: pref.deletePref(0)
        self._run_test(old, getter, deleter, 42, "ordered/ordered")

    def test_invalid_update(self):
        prefset = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        ordered = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        with self.assertRaises(COMException) as cm:
            prefset.update(ordered)
        self.assertEquals(cm.exception.errno, Cr.NS_ERROR_INVALID_ARG)
        with self.assertRaises(COMException) as cm:
            ordered.update(prefset)
        self.assertEquals(cm.exception.errno, Cr.NS_ERROR_INVALID_ARG)

class PrefSetTestCase(unittest.TestCase):
    """Testing preference set behaviour"""

    def test_child_lookup_in_container(self):
        """Looking up preferences in child prefsets should not attempt to look
        at its container
        """
        prefset = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()

        prefset.setPref("child",
                        Cc["@activestate.com/koPreferenceSet;1"].createInstance())
        prefset.setLong("long", 1)
        with self.assertRaises(COMException) as cm:
            prefset.getPref("child").getLongPref("long")
        self.assertEquals(cm.exception.errno, Cr.NS_ERROR_UNEXPECTED)
        self.assertFalse(prefset.getPref("child").hasLongPref("long"))
        self.assertTrue(prefset.hasLongPref("long"))

    def test_serialize_parent(self):
        """Test that serializing/unserializing prefs will still have parent set
        """
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        child = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()

        def serializePrefSet(prefset):
            path = tempfile.mktemp(suffix=".xml")
            prefset.serializeToFile(path)
            try:
                result = (Cc["@activestate.com/koPreferenceSetObjectFactory;1"]
                            .getService()
                            .deserializeFile(path))
            finally:
                os.remove(path)
                try:
                    os.remove(path + "c")
                except OSError as ex:
                    import errno
                    if ex.errno != errno.ENONET:
                        raise
            try:
                result.QueryInterface(Ci.koIPreferenceRoot)
            except COMException as ex:
                if ex.errno == Cr.NS_ERROR_NO_INTERFACE:
                    self.fail("Unserialized from file but not a root")
                raise
            def check_for_shadow_prefs(pref):
                for name, (child, typ) in pref.prefs.items():
                    if typ != "object":
                        continue
                    child = UnwrapObject(child)
                    self.assertFalse(getattr(child, "_is_shadow", False),
                                     "Child %s is a shadow pref" % (name,))
                    check_for_shadow_prefs(child)
            check_for_shadow_prefs(UnwrapObject(result))
            return result

        root.inheritFrom = base
        base.setPref("child", child)

        base.getPref("child").setLong("long", 68)
        self.assertEquals(root.getPref("child").getLong("long"),
                          base.getPref("child").getLong("long"))
        uroot = UnwrapObject(root)
        self.assertTrue(uroot.getPref("child")._is_shadow)
        # Once root.child is assigned a value, child becomes unshadowed.
        root.getPref("child").setDouble("double", 1.23456)
        self.assertFalse(base.getPref("child").hasDoublePref("double"))
        self.assertTrue(root.getPref("child").hasPref("double"))
        self.assertTrue(root.getPref("child").hasPrefHere("double"))
        self.assertFalse(uroot.getPref("child")._is_shadow)

        base = serializePrefSet(base)
        root = serializePrefSet(root)
        root.inheritFrom = base  # reset inheritFrom after serialization

        self.assertTrue(root.hasPrefHere("child"))
        self.assertAlmostEquals(root.getPref("child").getDouble("double"),
                                1.23456)
        base.getPref("child").setLong("long", 42)
        self.assertTrue(root.hasPrefHere("child"))
        long_value = root.getPref("child").getLong("long")
        self.assertEquals(long_value, 68,
                          "child pref lost its base pref, expected 42, got %r"
                          % (long_value,))

    def test_inheritance(self):
        """Test the use of prefset.inheritFrom"""
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root.inheritFrom = base

        child = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        base.setPref("child", child)
        child.setLong("long", 12345)

        root.setString("string", "this is a string")
        self.assertTrue(base.hasPrefHere("child"))
        self.assertFalse(root.hasPrefHere("child"))

        self.assertEquals(base.getPrefIds(), ["child"])
        self.assertEquals(base.getAllPrefIds(), ["child"])
        self.assertEquals(root.getPrefIds(), ["string"])
        self.assertEquals(root.getAllPrefIds(), ["child", "string"]) # sorted

        self.assertEquals(root.getPref("child").container, root)

        self.assertFalse(root.getPref("child").hasPrefHere("long"))
        self.assertFalse(root.hasPrefHere("child"))
        root.getPref("child").setLong("long", 54321)
        self.assertTrue(root.hasPrefHere("child"))
        self.assertTrue(root.getPref("child").hasPrefHere("long"))
        self.assertEquals(base.getPref("child").getLong("long"), 12345)

        root.reset()
        self.assertEquals(base.getAllPrefIds(), root.getAllPrefIds())

        self.assertTrue(base.hasPrefHere("child"))
        self.assertFalse(root.hasPrefHere("child"))

    def test_ordered_inheritance(self):
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        ordered = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        ordered.id = "test_ordered_inheritance"
        ordered.appendLong(1)
        base.setPref("ordered", ordered)
        root.inheritFrom = base

        root.getPref("ordered").QueryInterface(Ci.koIOrderedPreference)
        self.assertEquals(base.getPref("ordered").getLong(0), 1)
        self.assertEquals(root.getPref("ordered").getLong(0), 1)
        self.assertEquals(base.getPref("ordered").length, 1)
        self.assertEquals(root.getPref("ordered").length, 1)

        base.getPref("ordered").appendLong(2)
        self.assertEquals(base.getPref("ordered").length, 2)
        self.assertEquals(root.getPref("ordered").length, 2)
        self.assertEquals(base.getPref("ordered").getLong(0), 1)
        self.assertEquals(base.getPref("ordered").getLong(1), 2)
        self.assertEquals(root.getPref("ordered").getLong(0), 1)
        self.assertEquals(root.getPref("ordered").getLong(1), 2)

        root.getPref("ordered").appendLong(3) # detaches
        self.assertEquals(base.getPref("ordered").length, 2)
        self.assertEquals(root.getPref("ordered").length, 3)
        self.assertEquals(root.getPref("ordered").getLong(0), 1)
        self.assertEquals(root.getPref("ordered").getLong(1), 2)
        self.assertEquals(root.getPref("ordered").getLong(2), 3)
        with self.assertRaises(COMException) as cm:
            # The base should not have the appnded pref
            base.getPref("ordered").getPrefType(2)
        self.assertEquals(cm.exception.errno, Cr.NS_ERROR_INVALID_ARG,
                          "Unexpected exception %s" % (cm.exception,))

        # ordered pref reset just clears it...
        o = root.getPref("ordered")
        o.reset()
        self.assertTrue(root.hasPrefHere("ordered"))
        self.assertEquals(o.length, 0)
        self.assertEquals(root.getPref("ordered").length, 0)

        # Add new ordered prefs and check again.
        o.appendLong(9)
        self.assertEquals(base.getPref("ordered").length, 2)
        self.assertEquals(base.getPref("ordered").getLong(0), 1)
        self.assertEquals(base.getPref("ordered").getLong(1), 2)
        self.assertEquals(root.getPref("ordered").length, 1)
        self.assertEquals(root.getPref("ordered").getLong(0), 9)
        self.assertEquals(o.length, 1)
        self.assertEquals(o.getLong(0), 9)

    def test_ordered_reset(self):
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        ordered = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        ordered.id = "test_ordered_inheritance"
        ordered.appendLong(1)
        ordered.appendLong(2)
        base.setPref("ordered", ordered)
        root.inheritFrom = base

        # ordered pref reset just clears it...
        o = root.getPref("ordered")
        o.reset()
        self.assertTrue(root.hasPrefHere("ordered"))
        self.assertEquals(o.length, 0)
        self.assertEquals(root.getPref("ordered").length, 0)
        self.assertEquals(base.getPref("ordered").length, 2)

        # Add new ordered prefs and check again.
        o.appendLong(9)
        self.assertEquals(base.getPref("ordered").length, 2)
        self.assertEquals(base.getPref("ordered").getLong(0), 1)
        self.assertEquals(base.getPref("ordered").getLong(1), 2)
        self.assertEquals(root.getPref("ordered").length, 1)
        self.assertEquals(root.getPref("ordered").getLong(0), 9)
        self.assertEquals(o.length, 1)
        self.assertEquals(o.getLong(0), 9)

    @tag("bug106386")
    def test_preference_cache(self):
        """Ensure viewStateMRU (a koPrefCache) works as intended"""
        # Create the preference cache and original prefset.
        pref_cache = Cc["@activestate.com/koPrefCache;1"].createInstance()
        prefs = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        prefs.id = "test_preference_cache"
        pref_cache.setPref(prefs)

        # Add ordered preference to the prefset.
        openedfiles = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        openedfiles.appendString("file1")
        openedfiles.appendString("file2")
        prefs.setPref("openedfiles", openedfiles)

        # Check the prefs through the base preference cache instance.
        prefs_try2 = pref_cache.getPref("test_preference_cache")
        openedfiles_2 = prefs_try2.getPref("openedfiles")
        self.assertEqual(openedfiles_2.length, 2)
        self.assertEqual(openedfiles_2.getString(0), "file1")
        self.assertEqual(openedfiles_2.getString(1), "file2")

        # Set different ordered preference on the prefset.
        openedfiles_2 = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        openedfiles_2.appendString("file1")
        openedfiles_2.appendString("file2")
        openedfiles_2.appendString("file3")
        prefs_try2.setPref("openedfiles", openedfiles_2)

        # Check the prefs (again) through the base preference cache instance.
        prefs_try3 = pref_cache.getPref("test_preference_cache")
        openedfiles_3 = prefs_try3.getPref("openedfiles")
        self.assertEqual(openedfiles_3.length, 3)
        self.assertEqual(openedfiles_3.getString(0), "file1")
        self.assertEqual(openedfiles_3.getString(1), "file2")
        self.assertEqual(openedfiles_3.getString(2), "file3")

class PrefSerializeTestCase(unittest.TestCase):
    def assertXMLEqual(self, first, second, msg=None, ignore_white_space=True):
        if first is None and second is None:
            return True
        if ignore_white_space:
            def cleanup(elem):
                for e in elem.iter():
                    if e.text is not None:
                        e.text = e.text.strip()
                    if e.tail is not None:
                        e.tail = e.tail.strip()
            cleanup(first)
            cleanup(second)
        if (first is None and second is not None) or (second is None and first is not None):
            self.fail("unequal elements: first %r, second %r" % (first, second))
        first_string = ET.tostring(prettify_tree(first, level=2))
        second_string = ET.tostring(prettify_tree(second, level=2))
        if not msg:
            msg = 'xml is not equal'
        msg += "\nfirst_string:\n" + first_string + \
               "\nsecond_string:\n" + second_string
        if first_string != second_string:
            # Could be xml ordering - try reparsing to ensure consistent ordering.
            first_string = _serializePrefToString(_deserializePrefString(first_string))
            second_string = _serializePrefToString(_deserializePrefString(second_string))
        self.assertEqual(first_string, second_string, msg=msg)

    def assertSerializesTo(self, pref_root, expected_xml, msg=None):
        """Assert that the given preference root will serialize to the given
        XML.
            @param pref_root {PrefSet}
            @param expected_xml {str}
            @param msg {str or None}
        """
        path = tempfile.mktemp(suffix=".xml")
        pref_root.serializeToFile(path)

        try:
            xml = ET.parse(path).getroot()
        except ET.ParseError:
            xml = None
        finally:
            os.remove(path)
            try:
                os.remove(path + "c")
            except OSError as ex:
                import errno
                if ex.errno != errno.ENONET:
                    raise

        expected = ET.fromstring(expected_xml)
        self.assertXMLEqual(xml, expected)

    def test_serialize_shadow_pref(self):
        """Check that shadow prefs don't get serialized (as they have no data);
        but that prefs that do have data are."""
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root.inheritFrom = base
        child = Cc["@activestate.com/koPreferenceSet;1"].createInstance()

        base.setPref("child", child)
        child.setBoolean("bool", True)
        base.setLong("long", 987654321)
        root.setLong("long", 123456789)
        self.assertEquals(base.getPref("child").getBoolean("bool"),
                          root.getPref("child").getBoolean("bool"))

        self.assertSerializesTo(root, """
            <preference-set>
                <long id="long">123456789</long>
            </preference-set>""")

        root.setPref("child", base.getPref("child")) # force set
        self.assertSerializesTo(root, """
            <preference-set>
                <preference-set id="child">
                    <boolean id="bool">1</boolean>
                </preference-set>
                <long id="long">123456789</long>
            </preference-set>""")

    @tag("bug104645")
    def test_serialize_shadow_ordered(self):
        """Check that shadow ordered prefs don't get serialized"""
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        ordered = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        ordered.id = "test_ordered_inheritance_shadowing"
        ordered.appendLong(1)
        base.setPref("test_ordered_inheritance_shadowing", ordered)
        root.inheritFrom = base

        o = root.getPref("test_ordered_inheritance_shadowing")
        self.failIf(root.hasPrefHere("test_ordered_inheritance_shadowing"),
                    "Root gained an ordered preference after getting from global")

        self.assertSerializesTo(root, """
            <preference-set/>""")

        o.appendLong(2)
        self.assertTrue(root.hasPrefHere("test_ordered_inheritance_shadowing"),
                        "Modified ordered prefs should not be shadowed")

        self.assertSerializesTo(root, """
            <preference-set>
                <ordered-preference id="test_ordered_inheritance_shadowing">
                    <long id="">1</long>
                    <long id="">2</long>
                </ordered-preference>
            </preference-set>""")

    @tag("bug105438")
    def test_pickle_serialization(self):
        """Check that shadow ordered prefs don't get serialized"""
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        ordered = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        ordered.id = "test_ordered_inheritance_shadowing"
        ordered.appendLong(1)
        base.setPref("test_ordered_inheritance_shadowing", ordered)
        root.inheritFrom = base

        o = root.getPref("test_ordered_inheritance_shadowing")
        self.failIf(root.hasPrefHere("test_ordered_inheritance_shadowing"),
                    "Root gained an ordered preference after getting from parent")

        self.assertSerializesTo(root, """
            <preference-set/>""")

        from tempfile import mkstemp
        (fd, pickleFilename) = mkstemp(".tmp", "koPickle_")
        os.close(fd)
        try:
            root.serializeToFileFast(pickleFilename)
            import pickle
            uroot = pickle.loads(open(pickleFilename, "rb").read())
            self.assertSerializesTo(uroot, """
            <preference-set/>""")
        finally:
            os.remove(pickleFilename)

    def test_serialize_empty_prefsets(self):
        """Ensure empty preferences sets are serialized correctly"""
        base = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        child = Cc["@activestate.com/koPreferenceSet;1"].createInstance()
        child.id = "child"
        base.setPref("child", child)
        orderedchild = Cc["@activestate.com/koOrderedPreference;1"].createInstance()
        orderedchild.id = "ordered"
        base.setPref("ordered", orderedchild)
        root.inheritFrom = base

        self.assertSerializesTo(root, """
            <preference-set/>""")
        self.assertSerializesTo(base, """
            <preference-set>
                <preference-set id="child" />
                <ordered-preference id="ordered" />
            </preference-set>""")

    @tag("bug105850")
    def test_formatter_modify_prefs(self):
        """Ensure formatters can properly change their preferences."""
        pref_string = """
          <preference-set id="default">
            <preference-set id="{a5b90f01-8d7b-4006-8b44-e59ea21c968d}">
              <string id="formatter_name">generic</string>
              <string id="lang">Python</string>
              <string id="name">Reindent</string>
              <preference-set id="genericFormatterPrefs">
                <string id="arguments">"%(path:komodoPythonLibDir)/reindent.py" -i %(pref:indentWidth)</string>
                <string id="executable">%(python)</string>
              </preference-set>
            </preference-set>
          </preference-set>
        """
        base = _deserializePrefString(pref_string)
        root = Cc["@activestate.com/koPreferenceRoot;1"].createInstance()
        root.inheritFrom = base

        # Change prefs and save.
        uuid = "{a5b90f01-8d7b-4006-8b44-e59ea21c968d}"
        reindent = root.getPref(uuid)
        reindent.setString("name", "Reindenta")
        root.setPref(uuid, reindent)

        # We should end up with a full copy of these prefs on the root.
        result_pref_string = pref_string.replace("Reindent", "Reindenta")
        self.assertSerializesTo(root, result_pref_string)
