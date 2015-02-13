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

from xpcom import components
from xpcom.server import UnwrapObject

from testlib import tag, TestFailed

class IfaceTestCase(unittest.TestCase):
    def test_scintilla_iface(self):
        matches = {}
        ignores = {'SCE_XML_PROLOG':1}
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
                if lang == "UDL" and fullname.endswith("_UPPER_BOUND"):
                    continue # ignore upper bounds, they _should_ overlap
                if not ignores.get(fullname, False):
                    msgs.append("Collision at line %d: language %s: %s and %s = %s" % \
                          (line_num, lang, matches[lang][val], fullname, val))
            else:
                matches[lang][val] = fullname
        if len(msgs) > 0:
            msgs.insert(0, "%d collision%s in file %s:" % (len(msgs),
                        len(msgs) > 1 and "s" or "", filename))
            raise TestFailed("\n".join(msgs))

class SciMozHeadlessContext(object):
    def __init__(self):
        self._sm = components.classes["@activestate.com/ISciMozHeadless;1"]. \
                        createInstance(components.interfaces.ISciMoz)
    def __enter__(self):
        return self._sm
    def __exit__(self, exc_type, exc_value, traceback):
        """Mark as closed, so ~SciMoz() doesn't show stderr messages."""
        try:
            self._sm.markClosed()
        except Exception:
            pass
        self._sm = None

class ScintillaHeadless(unittest.TestCase):
    def test_scintilla_headless(self):
        with SciMozHeadlessContext() as sm:
            text = "def foo():\n    pass\n"
            sm.text = text
            sm.lexer = sm.SCLEX_PYTHON
            sm.colourise(0, sm.length)
            #from binascii import hexlify
            #print '\n\nsm.text: %r\n' % (sm.text, )
            from binascii import hexlify
            styledText = sm.getStyledText(0, sm.length)
            self.assertEqual(styledText[0::2], text)
            self.assertEqual(hexlify(styledText[1::2]),
                             "0b0b0b"      # 'def'
                             "00"          # ' '
                             "0b0b0b"      # 'foo'
                             "0a0a0a"      # '():'
                             "0000000000"  # '\n    '
                             "0b0b0b0b"    # 'pass'
                             "00"          # '\n'
                             )

    def test_selText(self):
        with SciMozHeadlessContext() as sm:
            text = "def foo():\n    pass\n"
            sm.text = text

            sm.currentPos = currentPos = 8
            sm.anchor = anchor = 4
            self.assertEqual(sm.selText, text[anchor:currentPos])

            sm.currentPos = currentPos = 8
            sm.anchor = anchor = 20
            self.assertEqual(sm.selText, text[currentPos:anchor])

    def test_getStyleRange(self):
        with SciMozHeadlessContext() as sm:
            text = "def foo():\n    pass\n"
            sm.text = text
            sm.lexer = sm.SCLEX_PYTHON
            sm.colourise(0, sm.length)
            expected_styles = (
                       [0xb] * len('def')  +
                       [0x0] * len(' ')    +
                       [0xb] * len('foo')  +
                       [0xa] * len('():')  +
                       [0x0] * len('\n')   +
                       [0x0] * len('    ') +
                       [0xb] * len('pass') +
                       [0x0] * len('\n')
                      )

            # Test getStyleRange method.
            styles = sm.getStyleRange(0, sm.length)
            self.assertEqual(styles, expected_styles)
            # Test getStyleRange method with a partial range.
            styles = sm.getStyleRange(5, 10)
            self.assertEqual(styles, expected_styles[5:10])

    def _extractStyles(self, text):
        text2 = re.sub(r'(\s+)', r'<0>\1', text)
        parts = re.split(r'<(\d+)>', text2)[1:]
        styleParts = [int(x) for x in parts[0::2]]
        textParts = parts[1::2]
        finalText = "".join(textParts)
        expected_parts = [[stylePart] * len(textPart)
                          for (stylePart, textPart)
                          in zip(styleParts, textParts)]
        return finalText, reduce(lambda x,y:x + y, expected_parts, [])

    def test_checkCPP11Keywords(self):
        # bug 101299: verify some of the new C++11 keywords
        with SciMozHeadlessContext() as sm:
            text = """\
<5>thread_local <5>int <11>i <10>= <4>0<10>;
<5>struct <5>alignas<10>(<4>16<10>) <11>sse_t
<10>{
   <5>float <11>sse_data<10>[<4>4<10>];
   <5>void <11>foo<10>() <5>noexcept<10>(<5>true<10>) <10>{};
<10>};
<5>int <11>main <10>{
  <11>cout <10><< <5>alignof<10>(<11>sse_t<10>);
<10>}""".replace('\r', '')
            text, expected_styles = self._extractStyles(text)
            sm.text = text
            lexerSvc = (components.classes["@activestate.com/koLanguageRegistryService;1"].
                getService(components.interfaces.koILanguageRegistryService).
                getLanguage("C++").
                getLanguageService(components.interfaces.koILexerLanguageService))
            lexerSvc.setCurrent(sm)
            sm.colourise(0, len(sm.text))

            # Test getStyleRange method.
            styles = sm.getStyleRange(0, sm.length)
            self.maxDiff = None
            self.assertEqual(expected_styles, styles)

    @tag("bug80493")
    def test_unicode_replacetarget(self):
        with SciMozHeadlessContext() as sm:
            text = """\
This is a plain ASCII line of text.
But this one is more styl\xc3\xa9e.
""".replace('\r', '')
            # Convert to unicode string.
            utext = text.decode("utf8")
            # Add/replace the text using replaceTarget.
            sm.targetStart = 0
            sm.targetEnd = 0
            # Try with byte length argument (length should get ignored).
            sm.text = ""
            sm.replaceTarget(len(text), utext)
            self.assertEqual(sm.text, utext)
            self.assertEqual(sm.length, len(text))   # byte length!
            # Try with character length argument (length should get ignored).
            sm.text = ""
            sm.replaceTarget(len(utext), utext)
            self.assertEqual(sm.text, utext)
            self.assertEqual(sm.length, len(text))   # byte length!
            # Try with just the string argument.
            sm.text = ""
            sm.replaceTarget(utext)
            self.assertEqual(sm.text, utext)
            self.assertEqual(sm.length, len(text))   # byte length!
