from mklib import include, Task

include('a/Makefile.py', ns='a')
include('docs/Makefile.py', ns='docs')
include('support/make_support.py')

class all(Task):
    default = True
class clean(Task):
    pass
class foo(Task):
    pass

