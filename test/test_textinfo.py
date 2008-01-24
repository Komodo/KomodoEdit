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
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
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

"""test src/python-sitelib/textinfo.py"""

import sys
import os
from os.path import dirname, join, abspath, basename, splitext, exists
import unittest
from pprint import pprint, pformat
from glob import glob
import doctest

top_dir = dirname(dirname(abspath(__file__)))
sys.path.insert(0, join(top_dir, "util"))
sys.path.insert(0, join(top_dir, "contrib", "simplejson"))
sys.path.insert(0, join(top_dir, "src", "python-sitelib"))

import simplejson
from testlib import TestError
import testsupport

import textinfo



#---- test cases

class DocTestCase(unittest.TestCase):
    def test_doctests(self):
        suite = doctest.DocTestSuite(textinfo)
        for test in suite:
            test.runTest()

class DataTestCase(unittest.TestCase):
    def _test_one_file(self, path, opts, expected_ti):
        #print "_test_one_file", path, expected_ti

        actual_ti = textinfo.textinfo_from_path(path, **opts)
        for attr in expected_ti:
            self.assert_(hasattr(actual_ti, attr),
                "unexpected textinfo for '%s': expected '%s' attr, but "
                "there isn't one on %r" % (path, attr, actual_ti))
            self.assertEqual(
                getattr(actual_ti, attr), expected_ti[attr],
                "unexpected '%s' for '%s': expected %r, got %r"
                % (attr, path, expected_ti[attr], getattr(actual_ti, attr)))

def _fill_DataTestCase():
    data_dir = abspath(join(dirname(__file__), "textinfo_data"))

    for ti_path in testsupport.paths_from_path_patterns([data_dir],
                    recursive=True, includes=["*.textinfo"]):
        try:
            info = simplejson.loads(open(ti_path, 'rb').read())
        except ValueError, ex:
            raise TestError("error reading JSON in `%s': %s" % (ti_path, ex)) 
        data_path = testsupport.relpath(splitext(ti_path)[0], os.getcwd())

        # Tags.
        tags = []
        tags_path = data_path + ".tags"
        if exists(tags_path):
            for line in open(tags_path):
                if "#" in line:
                    line = line[:line.index('#')].strip()
                tags += line.split()

        # Options.
        opts = {}
        opts_path = data_path + ".opts"
        if exists(opts_path):
            try:
                opts = simplejson.loads(open(opts_path, 'rb').read())
            except ValueError, ex:
                raise TestError("error reading JSON in `%s': %s"
                                % (opts_path, ex)) 
            # The names of keyword args for a function call must be
            # strings.
            opts = dict((str(k), v) for k,v in opts.items())

        test_fn = lambda self, path=data_path, opts=opts, info=info: \
            self._test_one_file(path, opts, info)
        if tags:
            test_fn.tags = tags

        name = 'test_%s/%s' % (basename(dirname(data_path)),
                               basename(data_path))
        setattr(DataTestCase, name, test_fn)

_fill_DataTestCase()


#---- mainline

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    unittest.main()

