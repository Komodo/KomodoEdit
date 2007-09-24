The Black build tool.

Installation:

    - unpack the file into some directory
    - put that directory on your PATH
    - on windows: compile bk.cpp -> bk.exe via "nmake -f makefile.win"

Usage:

    - see the test/... files, they give some starter examples
    - The command line interface to black is "bk ...". Just type "bk help" to
      get an introduction.
    - "bk" operates on a Blackfile, which denotes a project root.
      The Blackfile on which to operate is determined as follows:
       1. If "-f <blackfile>" is specified, that is used.
       2. Else if a Blackfile.py is found in an ancestral directory, then
          that is used.
       3. Else if the BLACKFILE_FALLBACK environment variable is defined,
          then that is used.
      See "test/test_findblackfile.py" for test cases.


