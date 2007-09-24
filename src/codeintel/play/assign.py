# Python script to help develop/test the type inteferencing functionality
# of pythoncile.py.

from time import *
from traceback import print_exception
import sys, os

def myfunc(a, b=1, *args, **kwargs):
    """myfunc shows many argument attributes"""
    import time
    c = 3.14159
    c = "trentm"

class Foo(Base):
    """class Foo is a helper for type inferencing work"""
    import re
    classvar = 1
    def __init__(self):
        self.classvar = 3
        self.postclassvar = 4
    postclassvar = 1
    def setInstanceVar(self, value):
        self.instancevar = value
    def getInstanceVar(self):
        return self.instancevar
    def bar(self):
        import xml as XML
        return 43
    def bar_user(self):
        b = self.bar
        a = b
        c = self

myglobal = [1,2,3]


#---- simple assignments
bar = 1; bar = "trent"
foo, bar = 1, 2
Foo.bar.spam = 4L
Foo.blam.spam = 5 # we bail on this because Foo.blam doesn't exist
bar[1:2] = "foo" # we bail on this because it is too hard
[foo, Foo.bar.spam] = 1L, 2
key1, key2 = {'one':1, 'two':2}
foo, bar, blam = sys.exc_info() # bail on this, too hard for now
bar[1] = 1

#---- try to cover remaining types and operations
L = []
D = {}
T = (1,2)
ADD_S = "trent" + "e" + "mick"
MUL_IS = 3*"trent"
MUL_SI = "trent"*3
MUL_FI = 3.0*3
MUL_IF = 3*3.0
MUL_II = 3*3
DIV = 1/2
FLOOR = 3//2
FFLOOR = 3.0//2
MOD = 3.14 % 3
OR = 1 or "two"
AND = 1 and "two"
ORAND = 1 and (2.0 or "three")
LC = [i for i in range(4)]
NOT = not 1
POWER_II = 2**3
POWER_IL = 2**3L
POWER_LI = 2L**3
POWER_FF = 2.0**3.0
POWER_IF = 2**3.0
POWER_LF = 2L**3.0
POWER_IC = 2**3j
POWER_CF = 2j**3.0
RSHIFT = 4>>2
LSHIFT = 4>>2
BACKQUOTE = `[1,2]`
BITAND = 42 & 0xf0
BITOR  = 42 | 0xf0
BITXOR = 42 ^ 0xf0
COMPARE1 = 1 > 2
COMPARE2 = 1 == 2
COMPARE3 = 1 < 2
COMPARE4 = 1 <= 2
COMPARE5 = 1 >= 2
COMPARE6 = 1 <> 2
COMPARE7 = 1 != 2
INVERT = ~1
LSLICE = [1,2,3][1:2]
TSLICE = (1,2,3)[1:2]
UNARYADD = +2
UNARYSUB = -2


#---- more complex assignments
# do NOT find 'UNDEFINED' in locals/globals,
# types=type(resolve(UNDEFINED, assign))
spam = UNDEFINED
DEFINED = 1         # types=int
eggs = DEFINED      # find 'DEFINED' in locals, types=int
# find 'Foo' in locals , notice that it is of type 'class',
# types=type(call(assign.Foo))
f = Foo()
# do NOT find 'max', types=type(call(resolve(max, assign)))
MAX = max(1, 5)
# can NOT resolve sys.exc_info, type(call(resolve(sys.exc_info, assign)))
EXCINFO = sys.exc_info()
# resolve Foo.getInstanceVar, XXX Don't handle return yet,
# type(call(assign.Foo.getInstanceVar))
FOO = Foo.getInstanceVar()

NONE = None # do NOT find 'None', types=type(None scope assign.py)
# do NOT find 'sys', types=type(sys.version_info scope assign.py)
ver = sys.version_info
cv = Foo.classvar
# notice "' '" is a str literal, types=type(call(str.join scope assign.py))
name = ' '.join(["trent", "mick"])
#??? Do we just drop the ball at this point because building on an already
#    delayed evaluation can get out of hand? Do we take shortcuts with
#    __builtins__? Even if so, that doesn't solve the general problem.
#    Answer: bail for now and see how well things work out.
name = name.capitalize()


#---- Gotcha's found in the stdlib
# CITDL would be something like: assign os.popen CALL read GETATTR CALL
# But don't have GETATTR, so punt.
stuff = os.popen("pick %s 2>/dev/null" % `seq`).read()
# From mimify.py
newline = ('=%02x' % ord('F')).upper()
# From pyclbr.py
_getnext = re.compile(r"""...""", re.VERBOSE | re.DOTALL | re.MULTILINE).search

def foo(a, (b,c)=(1,2), *args, **kwargs):
    pass
bar = lambda a, (b, c), *args, **kwargs: cmp(a, b)

