#!/usr/bin/env python
# coding=utf-8
# Copyright (c) 2005-2013 ActiveState Corp.
# Author:
#   Eric Promislow (EricP@ActiveState.com)

"""test difflibex.py"""

import sys
import os
from os.path import dirname, join, abspath, basename, splitext, exists
import unittest
import codecs
from pprint import pformat
import itertools
import time

from testlib import TestError

try:
    import difflibex
except ImportError:
    top_dir = dirname(dirname(abspath(__file__)))
    sys.path.insert(0, join(top_dir, "src", "python-sitelib"))
    import difflibex
    del sys.path[0]

#---- test cases

class SplitOpcodesTestCase(unittest.TestCase):
    def _do_tests(self, ondisk, inmemory):
        trec = ('replace', 0, len(ondisk), 0, len(inmemory))
        return difflibex.split_opcodes(trec, ondisk, inmemory)
        
    def test_repl_insert(self):
        ondisk = [
            'abc\n',
        ]
        inmemory = [
            'abc1\n',
            'def\n',
        ]
        fixedTuples = self._do_tests(ondisk, inmemory)
        self.assertListEqual(fixedTuples,
                             [('replace', 0, 1, 0, 1),
                                ('insert', 1, 1, 1, 2)])
        
    def test_repl_delete(self):
        ondisk = [
            'abc\n',
            'def\n',
        ]
        inmemory = [
            'abc1\n',
        ]
        fixedTuples = self._do_tests(ondisk, inmemory)
        self.assertListEqual(fixedTuples,
                             [('replace', 0, 1, 0, 1),
                                ('delete', 1, 2, 1, 1)])
        
    def test_ins_repl_delete(self):
        ondisk = [
            'abc has cows\n',
            'def\n'
        ]
        inmemory = [
            'ghi\n',
            'abc1 has cows\n',
        ]
        fixedTuples = self._do_tests(ondisk, inmemory)
        self.assertListEqual(fixedTuples,
                             [('insert', 0, 0, 0, 1),
                                ('replace', 0, 1, 1, 2),
                                ('delete', 1, 2, 2, 2)])
        
    def test_del_repl_ins2(self):
        ondisk = [
            'zurich\n',
            'abc has cows\n',
            'definelitey here is a house\n'
        ]
        inmemory = [
            'abc1 has cows\n',
            'definitely here is a house\n',
            'windhoek festivals\n'
        ]
        fixedTuples = self._do_tests(ondisk, inmemory)
        self.assertListEqual(fixedTuples,
                             [('delete', 0, 1, 0, 0),
                                ('replace', 1, 2, 0, 1),
                                ('replace', 2, 3, 1, 2),
                                ('insert', 3, 3, 2, 3)],
                             "problems:\n" + pformat(fixedTuples) + "\n")
        
    def test_del_repl_ins(self):
        ondisk = [
            'zurich has dogs',
            'abc has cows\n',
            'def\n'
        ]
        inmemory = [
            'ghi\n',
            'abc1 has cows\n',
        ]
        fixedTuples = self._do_tests(ondisk, inmemory)
        self.assertListEqual(fixedTuples,
                             [('delete', 0, 1, 0, 0),
                                ('insert', 1, 1, 0, 1),
                                ('replace', 1, 2, 1, 2),
                                ('delete', 2, 3, 2, 2)],
                             "problems:\n" + pformat(fixedTuples) + "\n")
        
    def test_pydiff_example(self):
        ondisk = [
            'The Way that can be told of is not the eternal Way;\r\n',
            'The name that can be named is not the eternal name.\r\n',
            'The Nameless is the origin of Heaven and Earth;\r\n',
            'The Named is the mother of all things.\r\n',
            '  so we may see their subtlety,\r\n',
            '  so we may see their outcome.\r\n',
            'And let there always be being,\r\n',
            'The two are the same,\r\n',
            'But cheese after they are produced,\r\n',
            '  they have different names.\r\n',
        ]
        inmemory = [
            'The Nameless is the origin of Heaven and Earth;\r\n',
            'The named is the mother of all things.\r\n',
            '\r\n',
            'Therefore let there always be non-being,\r\n',
            '  so we may see their subtlety,\r\n',
            'And let there always be being,\r\n',
            '  so we may see their outcome.\r\n',
            'The two are the same,\r\n',
            'But after they are produced,\r\n',
            '  they have different names.\r\n',
            'They both may be called deep and profound.\r\n',
            'Deeper and more profound,\r\n',
            'The door of all subtleties!\r\n',
        ]
        trec = ('replace', 0, len(ondisk), 0, len(inmemory))
        t1 = time.time()
        fixedTuples = difflibex.split_opcodes(trec, ondisk, inmemory)
        t2 = time.time()
        et1 = t2 - t1
        self.assertListEqual(fixedTuples,
                             [('delete', 0, 1, 0, 0),
                              ('delete', 1, 2, 0, 0), ('equal', 2, 3, 0, 1), ('replace', 3, 4, 1, 2),
                              ('insert', 4, 4, 2, 4), ('equal', 4, 5, 4, 5), ('insert', 5, 5, 5, 6),
                              ('equal', 5, 6, 6, 7), ('delete', 6, 7, 7, 7), ('equal', 7, 8, 7, 8),
                              ('replace', 8, 9, 8, 9), ('equal', 9, 10, 9, 10), ('insert', 10, 10, 10, 13)])
        # Now verify that the caching is working with a second lookup of the same values
        t1 = time.time()
        fixedTuples2 = difflibex.split_opcodes(trec, ondisk, inmemory)
        t2 = time.time()
        # et2 should be time to look up a hash entry
        # et1 show time spent calculating the diff, should be at least 10 times slower
        # than doing a hash lookup and returning a reference.
        et2 = t2 - t1 
        self.assertEqual(fixedTuples, fixedTuples2)
        self.assertGreater(et1 / 10.0, et2, "first time wasn't fast enough: et1:%g, et2:%g" % (et1, et2))
        
    def test_diff_strings(self):
        a = '        var minimap = this.minimap;'
        b = '        var miniffffmap = minimap;'
        tuples = difflibex.SequenceMatcher(a=a, b=b).get_opcodes()
        self.assertListEqual(tuples,
                             [('equal', 0, 16, 0, 16), ('insert', 16, 16, 16, 20),
                              ('equal', 16, 22, 20, 26), ('delete', 22, 27, 26, 26),
                              ('equal', 27, 35, 26, 34)],
                             "Problem with %s" % (tuples,))
        
    def test_opcode_hash_culling(self):
        # Verify that the hash for difflibex.split_opcodes stores only the 1000
        # most recent entries.
        a = ["string1"]
        b_prefix = "string2_"
        import string
        a10 = string.ascii_lowercase[:10]
        first_time = None
        first_hashes = []
        for c1, c2, c3 in itertools.product(a10, a10, a10):
            b = [b_prefix, c1, c2, c3]
            h = difflibex._get_hash_for_arrays(a, b)
            first_hashes.append(h)
            if first_time is None:
                first_time = difflibex._split_opcodes_diffs[h]['time']
        self.assertEqual(len(difflibex._split_opcodes_diffs), 1000)
        
        # Verify that if there N opcodes in the hash set at time first_time,
        # that if we add another hash to it now, one of those first N will be removed.
        # Make sure that if, on very fast computers, all 1000 nodes were processed at
        # the same time, the next node goes in later.
        time.sleep(0.001)
        num_with_first_time = len([x for x in difflibex._split_opcodes_diffs.values() if x['time'] == first_time])
        h = difflibex._get_hash_for_arrays(a, [b_prefix, c1, c2, string.ascii_lowercase[11]])
        self.assertEqual(len(difflibex._split_opcodes_diffs), 1000)
        num_with_first_time_after = len([x for x in difflibex._split_opcodes_diffs.values() if x['time'] == first_time])
        self.assertEqual(num_with_first_time - 1, num_with_first_time_after)
        # Now try draining the old ones
        b10 = string.ascii_lowercase[10:20]
        for c1, c2, c3 in itertools.product(b10, b10, b10):
            b = [b_prefix, c1, c2, c3]
            h = difflibex._get_hash_for_arrays(a, b)
        # And verify all but the most recent are removed
        for h in first_hashes:
            self.assertFalse(h in difflibex._split_opcodes_diffs)
        
#---- mainline

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    unittest.main()
