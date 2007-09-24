#!python
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

