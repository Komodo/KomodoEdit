
import os
import re

BLAH = 42

def foo(strarg='1',
        intarg=2,
        variablearg=BLAH,
        getattrarg=os.curdir,
        listarg=['1', 2, BLAH],
        dictarg={1: "one", 2: "two", 3: BLAH},
        tuplearg=('1', 2, BLAH)):
    pass

def mathy(unaryaddarg=+1,
          unarysubarg=-1,
          addarg=1+2,
          subarg=1-2,
          mularg=1*2,
          divarg=1/2,
          floordivarg=1//2,
          bitorarg=1|2|3,
          bitandarg=1&2&3,
          bitxorarg=1^2^3,
          bitmixedarg=(1|BLAH)&3^4,
          ):
    pass

def lambdafuncdefaults(argsarg=lambda a, b: 'foo',
                       varargsarg=lambda *a: 'foo',
                       kwargsarg=lambda **a: 'foo',
                       defaultsarg=lambda a=1, b='2': 'foo',
                       allarg=lambda a,b=1,*c,**d: 'foo'):
    pass


# From xmlrpclib.py
def _decode(data, encoding, is8bit=re.compile("[\x80-\xff]").search):
    # decode non-ascii string (if possible)
    if unicode and encoding and is8bit(data):
        data = unicode(data, encoding)
    return data

# From tempfile.py
def TemporaryFile(mode='w+b', bufsize=-1, suffix=""):
    """Create and return a temporary file (opened read-write by default)."""

# From shutil.py
def copyfileobj(fsrc, fdst, length=16*1024):
    """copy data from file-like object fsrc to file-like object fdst"""

# From inspect.py
def joinseq(): pass
def formatargspec(args, varargs=None, varkw=None, defaults=None,
                  formatarg=str,
                  formatvarargs=lambda name: '*' + name,
                  #formatvarkw=lambda name: '**' + name,
                  #formatvalue=lambda value: '=' + repr(value),
                  join=joinseq):
    pass

# from Bastion.py
#def Bastion(object, filter = lambda name: name[:1] != '_',
#            name=None, bastionclass=BastionClass):
#    pass
#def Bastion(object, filter = lambda name: name[0:1:-1],
#            name=None, bastionclass=BastionClass):
#    pass

foo()