# Copyright (c) 2013 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""
Tests for the preferences service
"""
from xpcom import COMException
from xpcom.components import classes as Cc, interfaces as Ci
from xpcom import nsError as Cr
from xpcom.server import UnwrapObject

import logging
import unittest

log = logging.getLogger("test.koprefs")

class TestKoPrefsClone(unittest.TestCase):
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
        self.assertEqual(raiser.exception.errno, Cr.NS_ERROR_FAILURE)
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
