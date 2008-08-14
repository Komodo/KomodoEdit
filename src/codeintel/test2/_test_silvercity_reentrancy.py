#!python
#
# Grr. I can't get this to crash anymore. :)
#

import sys
import time
import random
import threading
from hashlib import md5
from os.path import dirname, join, abspath

#from codeintel2.lang_php import PHPLexer
from codeintel2.lang_javascript import JavaScriptLexer
from codeintel2.lang_html import HTMLLexer
from codeintel2.lang_mason import MasonLexer
from codeintel2.lang_smarty import SmartyLexer
from codeintel2.udl import UDLLexer

import SilverCity
import SilverCity.Lexer
from SilverCity import ScintillaConstants


#---- globals

test_dir = dirname(abspath(__file__))
content_from_lang = {
    #"php": open(join(test_dir, "scan_inputs", "php5_sample.php")).read(),
    #"php": open(r"C:\trentm\tmp\Config.php").read(),
    "php": open(join(test_dir, "bits", "lexer_reentrancy", "Config.php")).read(),
    "html": open(join(test_dir, "..", "..", "..", "contrib", "komododoc", "en-US", "prefs.html")).read(),
    "mason": open(join(test_dir, "scan_inputs", "mason-js-test02.mason.html"), 'r').read(),
    "python": """
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
}



class PHPLexer(UDLLexer):
    lang = "PHP"


class PythonLexer(SilverCity.Lexer.Lexer):
    lang = "Python"
    def __init__(self):
        self._properties = SilverCity.PropertySet()
        self._lexer = SilverCity.find_lexer_module_by_id(ScintillaConstants.SCLEX_PYTHON)
        self._keyword_lists = [
            SilverCity.WordList(SilverCity.Keywords.python_keywords),
            SilverCity.WordList(""), # hilighted identifiers
        ]


class MyThread(threading.Thread):
    def __init__(self, lexer, content):
        threading.Thread.__init__(self)
        self.lexer = lexer
        self.content = content
    def run(self):
        time.sleep(random.random())
        tokens = list( self.lexer.tokenize_by_style(self.content) )
        print "%15s tokens md5: %s" % (self.lexer.__class__.__name__, md5(repr(tokens)).hexdigest())

def doit():
    lexers = []
    
    print "_test_silvercity_reentrancy ..."
    
    threads = []
    pick_me = True
    for i in range(20):
        if pick_me:
            #content = content_from_lang["html"]
            #lexer = HTMLLexer()
            #content = content_from_lang["mason"]
            #lexer = MasonLexer()
            content = content_from_lang["php"]
            lexer = HTMLLexer()
        else:
            content = content_from_lang["php"]
            lexer = PHPLexer()
        t = MyThread(lexer, content)
        threads.append(t)
        t.start()
        pick_me = not pick_me
    
    for t in threads:
        t.join()


doit()
