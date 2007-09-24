import sys
import unittest

from SilverCity.ScintillaConstants import *
from SilverCity._SilverCity import PropertySet, WordList, find_lexer_module_by_id, find_lexer_module_by_name

class PropertySetTestCase(unittest.TestCase):
    def check_construction(self):
        # No arguments
        ps = PropertySet()

        # Dictionary argument
        ps = PropertySet({'p1' : 1, 'p2' : 'two'})
        assert ps['p1'] == '1'
        assert ps['p2'] == 'two'
        assert ps['p3'] == ''
        
        class Seq:
            def __init__(self, dict = {}): self.dict = dict
            def __len__(self): return len(self, dict)
            def __setitem__(self, key, value): self.dict[key] = value
            def __getitem__(self, key): return self.dict[key]
            def __delitem__(self, key): del self.dict[key]

        # Keys must be strings
        self.assertRaises(TypeError, PropertySet, {1 : 1, 'p2' : 'two'})
                
        # Only mapping types are acceptable
        try:
            PropertySet("")
        except TypeError:
            pass
        except AttributeError:
            pass
        else:
            assert 0, "expected exception"

        # Only mapping types that implement items
        self.assertRaises(AttributeError, PropertySet, Seq({'p1' : 1, 'p2' : 'two'}))

        # Only mapping types that return sequence types from items
        class Seq2(Seq):
            def items(self): return 5            
        self.assertRaises(TypeError, PropertySet, Seq2({'p1' : 1, 'p2' : 'two'}))
                
        # Only mapping types that return sequence of 2-types from items
        class Seq2(Seq):
            def items(self): return [(5)]
            
        self.assertRaises(TypeError, PropertySet, Seq2({'p1' : 1, 'p2' : 'two'}))
        
    def check_assignment(self):
        ps = PropertySet()

        # String assignment        
        ps['p1'] = '1'
        assert ps['p1'] == '1'
        assert ps['p2'] == ''

        # Integer assignment
        ps['p2'] = 2
        assert ps['p2'] == '2'

        # Invalid key
        try:
            ps[5] == 5
        except TypeError:
            pass
        else:
            assert 0, "expected TypeError"

    def check_del(self):
        ps = PropertySet()

        ps['p1'] = '1'
        assert ps['p1'] == '1'
        del ps['p1']
        assert ps['p1'] == ''
        del ps['p2']
        assert ps['p2'] == ''

    def check_keys_and_values(self):
        ps = PropertySet()

        assert ps.keys() == []
        assert ps.values() == []
        
        ps['p1'] = '1'

        assert ps.keys() == ['p1']
        assert ps.values() == ['1']

        ps['p2'] = '2'
        
        keys = ps.keys()
        keys.sort()
        assert keys == ['p1', 'p2']

        values = ps.values()
        values.sort()
        assert values == ['1', '2']
        
class WordListTestCase(unittest.TestCase):
    def check_construction(self):
        wl = WordList()
        wl = WordList("word1 word2")

        assert wl.words == ['word1', 'word2']        
        self.assertRaises(TypeError, WordList, 'word1\0word2')
        self.assertRaises(TypeError, WordList, 5)
        wl = WordList("\n\n\n\nword1\n\n\nword2555---   ")

class LexerTestCase(unittest.TestCase):
    def check_construction(self):
        lexer = find_lexer_module_by_id(SCLEX_PYTHON)
        self.assertRaises(ValueError, find_lexer_module_by_id, 2000)

        lexer = find_lexer_module_by_name('python')
        self.assertRaises(ValueError, find_lexer_module_by_name, 'klin')

    def check_repr(self):
        # Test to make sure that this doesn't crash
        lexer = find_lexer_module_by_id(SCLEX_PYTHON)

        repr(lexer)
        repr(lexer)
        repr(lexer)
        repr(lexer)

    def check_get_wordlist_descriptions(self):
        lexer = find_lexer_module_by_id(SCLEX_PYTHON)

        assert len(lexer.get_wordlist_descriptions()) == 1
        assert lexer.get_wordlist_descriptions()[0].lower().find('keyword') != -1

        # XXX This might change over time
        lexer = find_lexer_module_by_id(SCLEX_AVE)
        self.assertRaises(ValueError, lexer.get_wordlist_descriptions)
    
    def check_get_number_of_wordlists(self):
        lexer = find_lexer_module_by_id(SCLEX_PYTHON)

        assert lexer.get_number_of_wordlists() == 1

        # XXX This might change over time
        lexer = find_lexer_module_by_id(SCLEX_AVE)
        self.assertRaises(ValueError, lexer.get_number_of_wordlists)

        
    def check_tokenize_by_style(self):
        lexer = find_lexer_module_by_id(SCLEX_PYTHON)

        list_result = lexer.tokenize_by_style("import string\n", WordList("import"), PropertySet())
        fn_result = []

        def fn(fn_result = fn_result, **keywords):
            fn_result.append(keywords)

        assert lexer.tokenize_by_style("import string\n", WordList("import"), PropertySet(), fn) == None
        
        assert list_result == fn_result
        
coreTestList = []
experimentalTestList = []

for testList, testType in [(coreTestList,'check'), (experimentalTestList,'experimental')]:
    testList.append(unittest.makeSuite(PropertySetTestCase, testType))
    testList.append(unittest.makeSuite(WordListTestCase, testType))
    testList.append(unittest.makeSuite(LexerTestCase, testType))
    
coreTests = unittest.TestSuite(coreTestList)
experimentalTests = unittest.TestSuite(experimentalTestList)

def testCore():
    runner = unittest.TextTestRunner()
    runner.run(coreTests)
    
def testExperimental():
    runner = unittest.TextTestRunner()
    runner.run(experimentalTests)
    
if __name__ == "__main__":
    if len(sys.argv) <= 1:
        testCore()
    else:
        if sys.argv[1] == '--experimental':
            testExperimental()
        else:
            print 'usage: %s [--experimental]' % sys.argv[0]
            sys.exit(1)