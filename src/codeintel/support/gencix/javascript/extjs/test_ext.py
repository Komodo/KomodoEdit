#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2008
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

"""Test the Ext JS cix generation."""

import os
import sys
from os.path import (join, dirname, abspath)
from glob import glob
from pprint import pprint
import unittest
import logging

import ciElementTree as ET


logging.basicConfig()
log = logging.getLogger("test_yui")
#log.setLevel(logging.DEBUG)


def get_tree_from_cix(version):
    cix_file = glob("%s%sext_%s.cix" % (join(dirname(abspath(__file__)),
                                             "apicatalogs"),
                                        os.sep, version))[0]
    try:
        return ET.parse(cix_file).getroot()
    except:
        log.exception("Unable to load cix file: %r", cix_file)
    return None


class ExtBaseTests(object):
    version = None
    cix_file = None
    cix_tree = None

    def _get_ext_blob(self):
        return self.cix_tree.getchildren()[0].getchildren()[0]

    def _get_ext_scope(self):
        return self._get_ext_blob().names["Ext"]

    def _get_scope_for_name(self, fullname):
        name_split = fullname.split(".")
        scope = self._get_ext_blob()
        for name in name_split:
            scope = scope.names.get(name)
            self.assertTrue(scope is not None, "Could not locate variable %r"
                            ", failed at part %r" % (fullname, name))
        return scope

    def _check_module_list(self, module_list):
        ext_blob = self._get_ext_blob()
        for module_name in module_list:
            name_split = module_name.split(".")
            scope = ext_blob
            for name in name_split:
                #print "Name: %r, module_name: %r" % (name, module_name, )
                #pprint(scope.names, depth=1)
                scope = scope.names.get(name)
                self.assertTrue(scope is not None, "Could not locate module %r"
                                ", failed at part %r" % (module_name, name))

    def assert_has_variable(self, fullname, citdl=None):
        scope = self._get_scope_for_name(fullname)
        self.assertEqual(scope.tag, "variable",
                         "%r not a variable, is %r" % (fullname, scope.tag))
        if citdl is not None:
            self.assertEqual(scope.get("citdl"), citdl,
                             "%r has incorrect citdl %r != %r" % (fullname, scope.get("citdl"), citdl))

    def assert_has_scope(self, fullname):
        scope = self._get_scope_for_name(fullname)

    def assert_has_function(self, fullname):
        scope = self._get_scope_for_name(fullname)
        self.assertEqual(scope.tag, "scope",
                         "%r not a scope element, is %r" % (fullname, scope.tag))
        self.assertEqual(scope.get("ilk"), "function",
                         "%r not a function, is %r" % (fullname, scope.get("ilk")))

    def assert_has_class(self, fullname):
        scope = self._get_scope_for_name(fullname)
        self.assertEqual(scope.tag, "scope",
                         "%r not a scope element, is %r" % (fullname, scope.tag))
        self.assertEqual(scope.get("ilk"), "class",
                         "%r not a class, is %r" % (fullname, scope.get("ilk")))

    def test_common(self):
        """General tests for all Ext versions"""
        tree = self.cix_tree
        self.assertTrue(tree is not None)
        self.assertTrue(tree.tag == "codeintel" and
                        tree.get("version") == "2.0")
        self.assertTrue(len(tree.getchildren()) == 1 and
                        tree.getchildren()[0].tag == "file")
        file_elem = tree.getchildren()[0]

        self.assertTrue(len(file_elem.getchildren()) == 1 and
                        file_elem.getchildren()[0].tag == "scope")
        ext_blob = file_elem.getchildren()[0]
        self.assertTrue(ext_blob.get("name") == "ext_%s" % (self.version_undotted))
        self.assertTrue(ext_blob == self._get_ext_blob())

        ext_scope = ext_blob.names.get("Ext")
        self.assertTrue(ext_scope is not None)
        self.assertTrue(ext_scope.get("name") == "Ext")
        self.assertTrue(ext_scope == self._get_ext_scope())


    # Module lists come from: http://extjs.com/deploy/dev/docs/

    def test_ext_base_namespaces(self):
        module_list = [
                # base classes
            "Ext",
            "Ext.data",
            "Ext.dd",
            "Ext.form",
            "Ext.grid",
            "Ext.layout",
            "Ext.menu",
            #"Ext.state",   # XXX - Missing?
            "Ext.tree",
            "Ext.util",
        ]
        self._check_module_list(module_list)
            
    def test_ext_base_variables(self):
        self.assert_has_variable("Ext.BLANK_IMAGE_URL", citdl="String")
        self.assert_has_variable("Ext.isWindows")
        self.assert_has_variable("Ext.isLinux")
        self.assert_has_variable("Ext.isMac")
        self.assert_has_variable("Ext.isIE")
        self.assert_has_variable("Ext.isGecko")
        self.assert_has_variable("Ext.isSecure")

    def test_ext_base_functions_and_classes(self):
        self.assert_has_scope("Ext.addBehaviors")
        self.assert_has_scope("Ext.apply")
        self.assert_has_scope("Ext.applyIf")
        self.assert_has_scope("Ext.decode")
        self.assert_has_scope("Ext.destroy")
        self.assert_has_scope("Ext.each")
        self.assert_has_scope("Ext.encode")
        self.assert_has_scope("Ext.escapeRe")
        self.assert_has_scope("Ext.extend")
        self.assert_has_scope("Ext.fly")
        self.assert_has_scope("Ext.get")
        self.assert_has_scope("Ext.getBody")
        self.assert_has_scope("Ext.getCmp")
        self.assert_has_scope("Ext.getDoc")
        self.assert_has_scope("Ext.getDom")
        self.assert_has_scope("Ext.id")
        self.assert_has_scope("Ext.isEmpty")
        self.assert_has_scope("Ext.namespace")
        self.assert_has_scope("Ext.num")
        self.assert_has_scope("Ext.onReady")
        self.assert_has_scope("Ext.override")
        self.assert_has_scope("Ext.query")
        self.assert_has_scope("Ext.select")
        self.assert_has_scope("Ext.type")
        self.assert_has_scope("Ext.urlDecode")
        self.assert_has_scope("Ext.urlEncode")


class Ext_v20_TestCase(unittest.TestCase, ExtBaseTests):
    version = "2.0.2"
    version_major_minor = version.rsplit(".", 1)[0]
    version_undotted = version.replace(".", "")
    cix_tree = get_tree_from_cix(version_major_minor)

class Ext_v22_TestCase(Ext_v20_TestCase):
    version = "2.2"
    version_major_minor = version
    version_undotted = version.replace(".", "")
    cix_tree = get_tree_from_cix(version_major_minor)

    def test_ext_v22_namespaces(self):
        module_list = [
                # base classes
            "Ext.air",
        ]
        self._check_module_list(module_list)

    def test_ext_air_module(self):
        # New module introduced into Ext 2.2.
        self.assert_has_scope("Ext.air.DragType")
        self.assert_has_scope("Ext.air.FileProvider")
        self.assert_has_scope("Ext.air.NativeObservable")
        self.assert_has_scope("Ext.air.NativeWindow")
        self.assert_has_scope("Ext.air.NativeWindowGroup")
        self.assert_has_scope("Ext.air.NativeWindowManager")
        self.assert_has_scope("Ext.air.Sound")
        self.assert_has_scope("Ext.air.SystemMenu")

class Ext_v30_TestCase(Ext_v20_TestCase):
    version = "3.0"
    version_major_minor = version
    version_undotted = version.replace(".", "")
    cix_tree = get_tree_from_cix(version_major_minor)


if __name__ == "__main__":
    unittest.main()
