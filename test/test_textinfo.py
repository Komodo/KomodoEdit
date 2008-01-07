#!/usr/bin/env python
# Copyright (c) 2005-2007 ActiveState Corp.

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

        # 'XXX_attrs_to_skip_for_now' is a hack until
        # textinfo._classify_from_content() is ready.
        XXX_attrs_to_skip_for_now = ["lang", "xml_version"]
        #XXX_attrs_to_skip_for_now = ["xml_version"]
        actual_ti = textinfo.textinfo_from_path(path, **opts)
        for attr in expected_ti:
            if attr in XXX_attrs_to_skip_for_now:
                continue
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
        tags += testsupport.splitall(dirname(
                    testsupport.relpath(ti_path, data_dir)))

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
        name = 'test_'+basename(data_path)
        setattr(DataTestCase, name, test_fn)

_fill_DataTestCase()


#---- mainline

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    unittest.main()

