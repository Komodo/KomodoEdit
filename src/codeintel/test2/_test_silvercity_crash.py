#!python

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

#
# Grr. I can't get this to crash anymore. :)
#

import sys
import time
import random

import SilverCity
import SilverCity.Lexer
from SilverCity import ScintillaConstants


class PythonLexer(SilverCity.Lexer.Lexer):
    lang = "Python"
    def __init__(self):
        self._properties = SilverCity.PropertySet()
        self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_PYTHON)
        self._keyword_lists = [
            SilverCity.WordList(SilverCity.Keywords.python_keywords)
        ]




content = """
import sys
import os
import bar

b = bar.Bar()
b.bar()

class Foo:
    "blather"
    def __init__(self, yada):
        pass
    def bar(self):
        pass

sys.path    # should have path in completion list
f = Foo()
f.bar()

print "this is ", os.path.abspath(__file__)

print (sys
.path)
"""

content = open("ci2.py", 'r').read()
lexers = []

print "_test_silvercity_crash...",
for i in range(1000):
    start = time.time()
    time.sleep(random.random())
    end = time.time()
    sys.stdout.write("%.3fs " % (end-start))
    lexer = PythonLexer()
    tokens = lexer.tokenize_by_style(content)
    lexers.append(lexer)
print "ok"

