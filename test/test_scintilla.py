#!/usr/bin/env python
# Copyright (c) 2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test the patched version of Scintilla.iface to ensure
there are no collisions in the list of styles.  See bug
http://bugs.activestate.com/show_bug.cgi?id=70645 for an
example of a situation this test is designed to detect.
"""

import os
import sys
import re
from os.path   import join, dirname, abspath

import unittest
from testlib import TestFailed

class IfaceTestCase(unittest.TestCase):
    def test_scintilla_iface(self):
        matches = {}
        ignores = {'SCE_XML_PROLOG':1, 'SCE_UDL_UPPER_BOUND':1 }
        hit_ptn = re.compile(r'\s*val (SCE_([A-Z]+)_.*?)\s*=\s*(\d+)')
        line_num = 0
        msgs = []
        filename = join(dirname(dirname(abspath(__file__))), 'src', 'scintilla',
                        'include', 'Scintilla.iface')
        for line in open(filename, 'r'):
            line_num += 1
            m = hit_ptn.match(line)
            if not m: continue
            lang = m.group(2)
            fullname = m.group(1)
            val = m.group(3)
            if not matches.has_key(lang): matches[lang] = {}
            if matches[lang].has_key(val):
                if not ignores.get(fullname, False):
                    msgs.append("Collision at line %d: language %s: %s and %s = %s" % \
                          (line_num, lang, matches[lang][val], fullname, val))
            else:
                matches[lang][val] = fullname
        if len(msgs) > 0:
            msgs.insert(0, "%d collision%s in file %s:" % (len(msgs),
                        len(msgs) > 1 and "s" or "", filename))
            raise TestFailed("\n".join(msgs))

