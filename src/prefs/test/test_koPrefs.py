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
        root.getPref("child").setDouble("double", 1.23456)
        self.assertFalse(base.getPref("child").hasDoublePref("double"))
        self.assertTrue(root.getPref("child").hasPref("double"))

        base = serializePrefSet(base)
        root = serializePrefSet(root)
        root.inheritFrom = base

        self.assertTrue(root.hasPref("child"))
        self.assertAlmostEquals(root.getPref("child").getDouble("double"),
                                1.23456)
        base.getPref("child").setLong("long", 42)
        self.assertEquals(root.getPref("child").getLong("long"), 42,
                          "child pref lost its base pref")

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
        root.getPref("ordered").reset()
        self.assertTrue(root.hasPrefHere("ordered"))
        self.assertEquals(root.getPref("ordered").length, 0)

class PrefSerializeTestCase(unittest.TestCase):
    def assertXMLEqual(self, first, second, msg=None, ignore_white_space=True):
        if ignore_white_space:
            def cleanup(elem):
                for e in elem.iter():
                    if e.text is not None:
                        e.text = e.text.strip()
                    if e.tail is not None:
                        e.tail = e.tail.strip()
            cleanup(first)
            cleanup(second)
        self.assertEqual(ET.tostring(first),
                         ET.tostring(second),
                         msg=msg)

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
        self.assertEquals(root.getPref("child").getBoolean("bool"),
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
    def test_serialize_ordered(self):
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
