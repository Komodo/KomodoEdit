#!/usr/bin/env python
# Copyright (c) 2007-2009 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test the MochiKit cix generation."""

import os
import sys
from os.path import (join, dirname, abspath)
from glob import glob
from pprint import pprint
import unittest
import logging

import ciElementTree as ET


logging.basicConfig()
log = logging.getLogger("test_mochikit")
#log.setLevel(logging.DEBUG)


def get_tree_from_cix(version):
    cix_file = glob("%s%smochikit_v%s.cix" % (join(dirname(abspath(__file__)),
                                             "apicatalogs"),
                                         os.sep, version))[0]
    try:
        return ET.parse(cix_file).getroot()
    except:
        log.exception("Unable to load cix file: %r", cix_file)
    return None


class MochiKitBaseTests(object):
    version = None
    cix_file = None
    cix_tree = None
    scopes = None

    def _get_mochikit_scopes(self):
        if self.scopes is None:
            self.scopes = []
            for file_elem in self.cix_tree.getchildren():
                scope_elems = file_elem.getchildren()
                for scope_elem in scope_elems:
                    self.scopes.append(scope_elem)
        return self.scopes

    def test_common(self):
        """General tests for all YUI versions"""
        tree = self.cix_tree
        self.assertTrue(tree is not None)
        self.assertTrue(tree.tag == "codeintel" and
                        tree.get("version") == "2.0")
        file_elems = tree.getchildren()
        self.assertTrue(len(file_elems) >= 1)
        for file_elem in file_elems:
            self.assertTrue(file_elem.tag == "file")
            self.assertTrue(len(file_elem.getchildren()) == 1 and
                            file_elem.getchildren()[0].tag == "scope")
            scope_elems = file_elem.getchildren()
            for scope_elem in scope_elems:
                mochikit_scope = scope_elem.getchildren()[0]
                self.assertTrue(mochikit_scope.get("name") == "MochiKit",
                                "%s != MochiKit" % (mochikit_scope.get("name")))

    def _check_module_list(self, module_list):
        for module_name in module_list:
            name_split = module_name.split(".")
            for scope in self._get_mochikit_scopes():
                for name in name_split:
                    #print "Name: %r, module_name: %r" % (name, module_name, )
                    #pprint(scope.names, depth=1)
                    scope = scope.names.get(name)
                    if scope is None:
                        break
                else:
                    break
            else:
                self.fail("Could not locate module: %r" % (module_name, ))

    # Module lists come from: http://developer.yahoo.com/yui/docs/

    def test_module_base(self):
        module_list = [
                # base classes
            "MochiKit",
            "MochiKit.Async",
            "MochiKit.Base",
            "MochiKit.Color",
            "MochiKit.DateTime",
            "MochiKit.DragAndDrop",
            "MochiKit.DOM",
            "MochiKit.Format",
            "MochiKit.Iter",
            "MochiKit.Logging",
            "MochiKit.LoggingPane",
            "MochiKit.Selector",
            "MochiKit.Signal",
            "MochiKit.Sortable",
            "MochiKit.Style",
            "MochiKit.Visual",
        ]
        self._check_module_list(module_list)


class YUI_v142_TestCase(unittest.TestCase, MochiKitBaseTests):
    version = "142"
    cix_tree = get_tree_from_cix(version)

if __name__ == "__main__":
    unittest.main()
