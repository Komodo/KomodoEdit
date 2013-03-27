#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# Author:
#   Eric Promislow (EricP@ActiveState.com)

"""test pythonVersionUtils.py"""

import sys
import os
import re
from os.path import dirname, join, abspath, basename, splitext, exists
import unittest
from pprint import pprint, pformat
from glob import glob

from testlib import TestError
from testsupport import indent, dedent

top_dir = dirname(dirname(abspath(__file__)))
sys.path.insert(0, join(top_dir, "src", "python-sitelib"))
import pythonVersionUtils

#---- test cases

class Python2TestCase(unittest.TestCase):
    def test_py2_print_code(self):
        code= """\
print 1
print >>sys.stderr, 'yap'
print
print 1,2
print 1,2,
"""
        #code_lines = code.splitlines()
        #for line in code_lines:
        #    self.assertTrue(not pythonVersionUtils.isPython3(line),
        #                    "Expected %s to be python2, but it isn't" % line)
        #    scores = pythonVersionUtils.getScores(line)
        #    self.assertEqual(scores, (1,0),
        #        "Expected score of (1,0) for code '%s', got %s" % (line,scores))
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (5,0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))
        
    def test_py3_print_code(self):
        code= """\
print('yap', file=sys.stderr)
print(1, 2, sep=' ')
"""
        #code_lines = code.splitlines()
        #for line in code_lines:
        #    self.assertTrue(pythonVersionUtils.isPython3(line),
        #                    "Expected %s to be python3, but it isn't" % line)
        #    scores = pythonVersionUtils.getScores(line)
        #    exp_scores = (0, 1)
        #    self.assertEqual(scores, exp_scores,
        #        "Expected score of %r for code '%s', got %s" % (exp_scores, line, scores))
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (0, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))
        
    def test_py2_strings(self):
        code= """\
a = u'PapayaWhip'
b = ur'PapayaWhipFoo'
c = a <> b
d = `1`
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (5, 0) # each backquote counts as 1
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))
        
    def test_py2_num_literals(self):
        code= """\
a = 10L + 0xFEEL + 034
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (3, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))

    def test_py3_num_literals(self):
	# Both Python 2.7 and Python 3 support this syntax.
        code= """\
a = 0o34
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (0, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))
    
    def test_py2_exec(self):
        code= """\
exec codeString
exec codeString in a_global_namespace
exec codeString in a_global_namespace, a_local_namespace
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (3, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))

    def test_py3_exec(self):
        code= """\
exec(codeString)
exec(codeString, a_global_namespace)
exec(codeString, a_global_namespace, a_local_namespace)
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (0, 0) # neutral
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))

    def test_py2_except(self):
        code = """
try:
    import mymodule
except ImportError, e:
    pass
# sep
try:
    import mymodule
except (RuntimeError, ImportError), e:
    pass
print('neutral')
raise MyException, 'error message'
print('neutral')
raise MyException # ok both ways
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (3, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))

    def test_py3_except(self):
        code= """\
try:
    import mymodule
except ImportError as e:
    pass
#...
try:
    import mymodule
except (RuntimeError, ImportError) as e:
    pass
"""
        scores = pythonVersionUtils.getScores(code)
	# This form is supported in Python 2.6, but not 2.5
        exp_scores = (0, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))

    def test_py2_stdlib_methods(self):
        code= """\
v1 = sys.exc_type
v2 = 	sys.exc_value
v3 = sys.exc_traceback
v4 = os.getcwdu()
"""
        scores = pythonVersionUtils.getScores(code)
        exp_scores = (4, 0)
        self.assertEqual(scores, exp_scores,
            "Expected score of %r for code %s, got %s" % (exp_scores, code, scores))
        
#---- mainline

if __name__ == "__main__":
    import logging
    logging.basicConfig()
    unittest.main()

