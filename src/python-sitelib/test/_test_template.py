
import os, types
import unittest

class FooTestCase(unittest.TestCase):
    pass
    

def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(FooTestCase)

