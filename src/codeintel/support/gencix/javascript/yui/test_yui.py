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

"""Test the YUI cix generation."""

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


def get_tree_from_cix(yui_version):
    cix_file = glob("%s%syui_v%s.cix" % (join(dirname(abspath(__file__)),
                                             "apicatalogs"),
                                         os.sep, yui_version))[0]
    try:
        return ET.parse(cix_file).getroot()
    except:
        log.exception("Unable to load cix file: %r", cix_file)
    return None


class YUIBaseTests(object):
    version = None
    cix_file = None
    cix_tree = None

    def _get_yui_scope(self):
        return self.cix_tree.getchildren()[0].getchildren()[0]

    def _get_yahoo_scope(self):
        return self._get_yui_scope().names["YAHOO"]

    def test_common(self):
        """General tests for all YUI versions"""
        tree = self.cix_tree
        self.assertTrue(tree is not None)
        self.assertTrue(tree.tag == "codeintel" and
                        tree.get("version") == "2.0")
        self.assertTrue(len(tree.getchildren()) == 1 and
                        tree.getchildren()[0].tag == "file")
        file_elem = tree.getchildren()[0]

        self.assertTrue(len(file_elem.getchildren()) == 1 and
                        file_elem.getchildren()[0].tag == "scope")
        yui_scope = file_elem.getchildren()[0]
        self.assertTrue(yui_scope.get("name") == "yui")
        self.assertTrue(yui_scope == self._get_yui_scope())

        yahoo_scope = yui_scope.names.get("YAHOO")
        self.assertTrue(yahoo_scope is not None)
        self.assertTrue(yahoo_scope.get("name") == "YAHOO")
        self.assertTrue(yahoo_scope == self._get_yahoo_scope())

    def _check_module_list(self, module_list):
        yui_scope = self._get_yui_scope()
        for module_name in module_list:
            name_split = module_name.split(".")
            scope = yui_scope
            for name in name_split:
                #print "Name: %r, module_name: %r" % (name, module_name, )
                #pprint(scope.names, depth=1)
                scope = scope.names.get(name)
                self.assertTrue(scope is not None, "Could not locate module %r"
                                ", failed at part %r" % (module_name, name))
                

    # Module lists come from: http://developer.yahoo.com/yui/docs/

    def test_module_base(self):
        module_list = [
                # base classes
            "YAHOO",
            "YAHOO.env",
            #"YAHOO.env.ua", # XXX - not in 2.2?
            "YAHOO.lang",
            #"YAHOO_config", # XXX - missing?
        ]
        self._check_module_list(module_list)
            
    def test_module_animation(self):
        module_list = [
            "YAHOO.util.Anim",
            "YAHOO.util.AnimMgr",
            "YAHOO.util.Bezier",
            "YAHOO.util.ColorAnim",
            "YAHOO.util.Easing",
            "YAHOO.util.Motion",
            "YAHOO.util.Scroll",
        ]
        self._check_module_list(module_list)

    def test_module_autocomplete(self):
        module_list = [
            "YAHOO.widget.AutoComplete",
            "YAHOO.widget.DataSource",
            "YAHOO.widget.DS_JSArray",
            "YAHOO.widget.DS_JSFunction",
            #"YAHOO.widget.DS_ScriptNode", # XXX - not in 2.2?
            "YAHOO.widget.DS_XHR",
        ]
        self._check_module_list(module_list)

    def test_module_button(self):
        module_list = [
            # XXX - button and buttongroup is missing, not being scanned?
            "YAHOO.widget.Button",
            "YAHOO.widget.ButtonGroup",
        ]
        self._check_module_list(module_list)

    def test_module_calendar(self):
        module_list = [
            # calendar
            "YAHOO.widget.Calendar",
            "YAHOO.widget.Calendar2up",
            "YAHOO.widget.Calendar_Core",
            "YAHOO.widget.CalendarGroup",
            #"YAHOO.widget.CalendarNavigator", # XXX - not in 2.2?
            "YAHOO.widget.DateMath",
        ]
        self._check_module_list(module_list)

    # ...

    def test_module_menu(self):
        module_list = [
            "YAHOO.widget.ContextMenu",
            "YAHOO.widget.ContextMenuItem",
            "YAHOO.widget.Menu",
            "YAHOO.widget.MenuBar",
            "YAHOO.widget.MenuBarItem",
            "YAHOO.widget.MenuItem",
            "YAHOO.widget.MenuManager",
        ]
        self._check_module_list(module_list)

    # ...

    def test_module_tabview(self):
        module_list = [
            "YAHOO.widget.Tab",
            "YAHOO.widget.TabView",
        ]
        self._check_module_list(module_list)


class YUI_v22_TestCase(unittest.TestCase, YUIBaseTests):
    version = "2.2"
    cix_tree = get_tree_from_cix(version)


class YUI_v23_TestCase(unittest.TestCase, YUIBaseTests):
    version = "2.3"
    cix_tree = get_tree_from_cix(version)


class YUI_v24_TestCase(unittest.TestCase, YUIBaseTests):
    version = "2.4"
    cix_tree = get_tree_from_cix(version)

    def test_module_charts(self):
        # charts - new in 2.4
        module_list = [
            "YAHOO.widget.Axis",
            "YAHOO.widget.BarChart",
            "YAHOO.widget.BarSeries",
            "YAHOO.widget.CartesianChart",
            "YAHOO.widget.CartesianSeries",
            "YAHOO.widget.CategoryAxis",
            "YAHOO.widget.Chart",
            "YAHOO.widget.ColumnChart",
            "YAHOO.widget.ColumnSeries",
            "YAHOO.widget.FlashAdapter",
            "YAHOO.widget.LineChart",
            "YAHOO.widget.LineSeries",
            "YAHOO.widget.NumericAxis",
            "YAHOO.widget.PieChart",
            "YAHOO.widget.PieSeries",
            "YAHOO.widget.Series",
            "YAHOO.widget.TimeAxis",
        ]
        self._check_module_list(module_list)

    def test_module_json(self):
        # json - new in 2.4
        module_list = [
            "YAHOO.lang.JSON",
        ]
        self._check_module_list(module_list)

    def test_module_profiler(self):
        # profiler - new in 2.4
        module_list = [
            "YAHOO.tool.Profiler",
        ]
        self._check_module_list(module_list)

class YUI_v25_TestCase(YUI_v24_TestCase):
    version = "2.5"
    cix_tree = get_tree_from_cix(version)

    def test_module_cookie(self):
        # cookie utility - new in 2.5
        module_list = [
            "YAHOO.util.Cookie",
        ]
        self._check_module_list(module_list)

    def test_module_imagecropper(self):
        # image cropper - new in 2.5
        module_list = [
            "YAHOO.widget.ImageCropper",
        ]
        self._check_module_list(module_list)

    def test_module_layout(self):
        # layout - new in 2.5
        module_list = [
            "YAHOO.widget.Layout",
        ]
        self._check_module_list(module_list)

    def test_module_profiler(self):
        # profiler - new in 2.4
        # profiler viewer - new in 2.5
        module_list = [
            "YAHOO.tool.Profiler",
            "YAHOO.widget.ProfilerViewer",
        ]
        self._check_module_list(module_list)

    def test_module_resize(self):
        # uploader - new in 2.5
        module_list = [
            "YAHOO.util.Resize",
        ]
        self._check_module_list(module_list)

    def test_module_uploader(self):
        # uploader - new in 2.5
        module_list = [
            "YAHOO.widget.Uploader",
        ]
        self._check_module_list(module_list)


if __name__ == "__main__":
    unittest.main()
