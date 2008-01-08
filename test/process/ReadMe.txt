This is the test suite for process.py. A prerequisite for the test suite
is to build some test executables:

    nmake -f Makefile.win32         # on Windows
    make -f Makefile.linux          # on Linux, Mac OS X
    make -f Makefile.solaris        # on Solaris

The you can run the test suite:

        python test.py

At the time of this writing (Jan 2008) this is NOT integrated with Komodo's
general "bk test" full test suite. As well, a number of tests have been
broken with the significant changes made to process.py to be based on Python
2.5's subprocess module instead of using PyWin32. These need to be
investigated. -- Trent

