README for codeintel
====================


Building
--------

There are two ways to build and use the codeintel system.

1. Using it in the Komodo environment. Unless you are working directly on the
   guts of codeintel, this is for you. To build codeintel you just use the
   normal Komodo build system. See Komodo-devel/README.txt for details.

2. Independent codeintel usage: called a "local build". This is useful for
   playing with codeintel stuff outside of Komodo (for the test suite, for
   codeintel-specific development). For a local build, follow the
   instructions below.


Requirements for building:
- A C compiler. You need to one used to build your Python installation. If
  you are using Python 2.4 or later, than means you need VS.NET (aka VC 7).
  If you are using Python 2.3 or earlier, then you need VC6.
- A Python installation against which to build.
- Source for SilverCity and Scintilla in a source repository.
  If you can access crimper normally then the build script will go and get
  them from there automatically (typically from
  "\\crimper\apps\Komodo\support\codeintel").
- "patch" on your path
- Other little tools like:
    unzip
    tar


To build on Windows::

    bin\setenv.bat
    python Makefile.py all

To build on Un*x platforms::

    . bin/setenv.sh
    python Makefile.py all

If you need to update generated files
(if the Scintilla constants have changed,
for example), run

    python Makefile.py distclean all


Running the Test Suite
----------------------

Once you've setup your environment and made a local build of codeintel (see
above) you can run the test suite in the "test" subdirectory.

To run the whole test suite::

    cd test2
    python test.py

Individual test modules can be run::

    python test.py test_misc

Or directly:

    python test_misc.py

Some test modules provide additional scoping. For example "test_cile.py" is
responsible for testing all the CILEs (the CodeIntel Language Engines, i.e.
the language-specific scanners). Say you are working on just the Ruby CILE
and just want to run those tests::

    python test_cile.py Ruby
    python test_cile.py scan_inputs\resolve.rb

    
    python ci2.py test RHTMLTestCase -- Just RHTML
    python ci2.py test -- all tests


Updating udl-based lexers
-------------------------

    python Makefile.py distclean_udl_lexers udl_lexers
   

Troubleshooting
---------------

It just works! :)

