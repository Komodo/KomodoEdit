#!python25.dll
# 'mk' launch stuff for Windows (see http://effbot.org/zone/exemaker.htm)
try:
    from mklib import runner
except ImportError:
    # Try in source tree layout.
    import sys
    from os.path import dirname
    sys.path.insert(0, dirname(dirname(__file__)))
    from mklib import runner
    
runner.main()

