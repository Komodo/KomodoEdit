# This is a comment

"""This is a module doc string.

Blah.
"""
from __future__ import print_function

import os, sys
import xml.sax
import time as timelib
from shutil import rmtree, copytree
from shutil import copy2 as copy

def func_no_args():
    "func_no_args doc"
    pass

def func_one_arg(a):
    import string
    pass

def func_default_arg(a=None):
    pass

def func_args(*args):
    def subfunc():
        "this is my subfunc"
        pass
    subfunc()

def func_complex_args(a, b=None, c="foo", *args, **kwargs):
    pass

class ClassNoBase:
    "class docstring"
    def __init__(self):
        "constructor docstring"
        pass
    def plain_method(self, a):
        def foobar():
            pass
        import math
    def _protected_method(self, a):
        pass
    def __private_method(self, a):
        pass

class ClassOneBase(ClassNoBase):
    "class docstring"
    def __init__(self):
        "constructor docstring"
        pass
    def plain_method_2(self, a):
        pass
    def _protected_method(self, a):
        pass
    def __private_method(self, a):
        pass

print("hi")
func_args("foo", "bar", "blam")
print("bye")

