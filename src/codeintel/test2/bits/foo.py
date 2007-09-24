
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

