#! /usr/bin/env python3

try:
    foo()
    bar()
except Foo, Bar as msg:
    pass
except (Baz, Qoox) as msg:
    pass
except Exception as msg:
    pass
except:
    pass
else:
    pass

